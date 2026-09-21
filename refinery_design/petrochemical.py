"""Petrochemical additions to a refinery: is propylene -> polypropylene worth it?

Three ways to make propylene from the refinery's own FCC, each feeding a
polypropylene (PP) unit:

* ``conventional``    - recover the propylene already in the FCC LPG
  (~6 wt% of FCC feed; FCC literature).
* ``zsm5``            - a ZSM-5 additive on the FCC catalyst (propylene > 9 wt%
  at 10-20 wt% additive loading; FCC literature).
* ``propylene_mode``  - a dedicated light-olefin FCC (Paradip's INDMAX-type unit).
  Published capacities imply ~16 wt% (its 680 kt/y PP plant is 16.2% of its
  4.2 Mt/y FCC feed); the FCC literature quotes >20 wt% for propylene-mode units.

What is real and what is an assumption
--------------------------------------
Real: the FCC feed, LPG yield and product pools from the flowsheet; the PP-plant
capex anchor (IndianOil Paradip: 680 kt/y for Rs 3,150 crore, converted at
PPAC's FY2018-19 Rs 69.89/$) scaled by the six-tenths rule; the propylene
yields above.  **Assumptions (unsourced, exposed as parameters):** the split of
propylene-mode propylene between forgone gasoline and forgone LCO, PP
conversion opex, the hurdle rate and plant life.  **Not available: petrochemical
prices** - none of the accessible feeds carries propylene or PP.  The decision
metric is therefore the *break-even PP price*: what PP must sell for so the
option pays its capital back, to be compared with the reader's own price view.

The Nelson index (`complexity.py`) has no factor for polymer units, so none of
these options moves it - complexity is blind to petrochemical integration.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .flowsheet import RefineryResult
from .grm import GrmResult, PriceDeck, gross_refining_margin  # noqa: F401  (re-exported for convenience)

PARADIP_PP_CAPEX_INR_CRORE = 3150.0     # OGJ/IOCL: 680 kt/y polypropylene plant, Paradip
PARADIP_PP_KTPA = 680.0
PARADIP_FCC_MTPA = 4.2
FX_INR_PER_USD_FY2018_19 = 69.89        # PPAC Table 4.12
PARADIP_PP_CAPEX_USD = PARADIP_PP_CAPEX_INR_CRORE * 1e7 / FX_INR_PER_USD_FY2018_19   # ~ $451 M
PARADIP_IMPLIED_PROPYLENE_WT = PARADIP_PP_KTPA / (PARADIP_FCC_MTPA * 1000.0) * 100.0   # 16.2 wt% of FCC feed
SCALE_EXPONENT = 0.6                    # six-tenths rule (Peters & Timmerhaus)
PROPYLENE_WT = {"conventional": 6.0, "zsm5": 9.0, "propylene_mode": PARADIP_IMPLIED_PROPYLENE_WT}   # wt% of FCC feed
REFERENCE_FCC_LPG_WT = 17.8            # this repo's reference FCC case (docs/VALIDATION.md)
PROPYLENE_SHARE_OF_LPG = PROPYLENE_WT["conventional"] / REFERENCE_FCC_LPG_WT   # ~0.34: propylene tracks the LPG the unit makes
ZSM5_MULTIPLIER = PROPYLENE_WT["zsm5"] / PROPYLENE_WT["conventional"]           # 9 / 6


def capital_recovery_factor(rate: float, years: int) -> float:
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def pp_capex_usd(pp_t_per_year: float) -> float:
    """PP-plant capex scaled from Paradip by the six-tenths rule."""
    return PARADIP_PP_CAPEX_USD * (pp_t_per_year / (PARADIP_PP_KTPA * 1000.0)) ** SCALE_EXPONENT


@dataclass(frozen=True)
class PetchemAssumptions:
    stream_hours: float = 8400.0
    pp_yield_t_per_t_propylene: float = 0.98
    pp_opex_usd_t: float = 100.0                 # PP conversion cost - assumption
    fcc_extra_opex_usd_t_propylene: float = 0.0  # additive / severity cost on incremental propylene - assumption
    hurdle_rate: float = 0.12                    # assumption
    life_years: int = 20                         # assumption
    offset_from_gasoline: float = 0.7            # propylene-mode: share of the extra propylene taken from gasoline (rest from LCO)
    fcc_revamp_capex_usd: float = 0.0            # zsm5 ~ additive only; propylene_mode: supply your own


@dataclass(frozen=True)
class PetchemOption:
    name: str
    propylene_wt_pct_of_fcc_feed: float
    propylene_t_y: float
    pp_t_y: float
    incremental_propylene_t_y: float
    forgone_value_usd_y: float            # fuel-pool value of what the propylene displaces
    forgone_by_pool_t_y: dict
    capex_pp_usd: float
    capex_fcc_usd: float
    opex_usd_y: float
    crude_bbl_y: float
    warnings: list[str] = field(default_factory=list)
    nci_change: float = 0.0

    @property
    def capex_usd(self) -> float:
        return self.capex_pp_usd + self.capex_fcc_usd


def build_option(result: RefineryResult, deck: PriceDeck, mode: str, a: PetchemAssumptions = PetchemAssumptions()) -> PetchemOption:
    """Size a propylene -> PP option on a flowsheet result that has an FCC."""
    if mode not in PROPYLENE_WT:
        raise ValueError(f"mode must be one of {list(PROPYLENE_WT)}")
    if result.fcc is None:
        raise ValueError("no FCC in this flowsheet - propylene cannot be recovered")
    vgo_kg_h = result.distillation.stream("vgo").mass_kg_h
    fcc_feed_t_y = vgo_kg_h * a.stream_hours / 1000.0
    lpg_t_y = fcc_feed_t_y * result.fcc.yields_wt_pct["lpg"] / 100.0
    # propylene already in the FCC LPG scales with the LPG this feed actually makes
    base_t_y = PROPYLENE_SHARE_OF_LPG * lpg_t_y
    warnings: list[str] = []
    if mode == "conventional":
        prop_t_y = base_t_y
        incremental = prop_t_y
        forgone = {"lpg": prop_t_y}
    elif mode == "zsm5":
        prop_t_y = ZSM5_MULTIPLIER * base_t_y
        incremental = prop_t_y - base_t_y
        forgone = {"lpg": base_t_y, "gasoline_range": incremental}
    else:
        prop_t_y = fcc_feed_t_y * PROPYLENE_WT["propylene_mode"] / 100.0
        incremental = prop_t_y - base_t_y
        if incremental < 0:
            raise ValueError("propylene-mode yield is below what the FCC already makes")
        forgone = {"lpg": base_t_y, "gasoline_range": a.offset_from_gasoline * incremental,
                   "middle_distillate": (1 - a.offset_from_gasoline) * incremental}
        warnings.append("propylene-mode yield is Paradip-implied (PP capacity / FCC feed), assumed achievable on this feed; "
                        "FCC revamp capex is NOT included unless supplied")
    pp_t_y = prop_t_y * a.pp_yield_t_per_t_propylene
    if pp_t_y < 150_000:
        warnings.append(f"PP capacity {pp_t_y/1000:.0f} kt/y is far below Paradip's 680 kt/y anchor - "
                        "scale economics of the six-tenths rule are unreliable this small")
    forgone_value = sum(t * deck.product_usd_t(p) for p, t in forgone.items())
    opex = pp_t_y * a.pp_opex_usd_t + incremental * a.fcc_extra_opex_usd_t_propylene
    crude_bbl_y = result.throughput_bpd * a.stream_hours / 24.0
    capex_fcc = a.fcc_revamp_capex_usd if mode == "propylene_mode" else 0.0
    return PetchemOption(mode, 100.0 * prop_t_y / fcc_feed_t_y,
                         prop_t_y, pp_t_y, incremental, forgone_value, forgone, pp_capex_usd(pp_t_y), capex_fcc,
                         opex, crude_bbl_y, warnings)


@dataclass(frozen=True)
class PetchemEvaluation:
    option: PetchemOption
    pp_price_usd_t: float
    margin_usd_y: float
    grm_uplift_usd_bbl: float
    capital_charge_usd_y: float
    net_usd_y: float
    simple_payback_years: float | None
    breakeven_pp_price_usd_t: float


def evaluate(option: PetchemOption, pp_price_usd_t: float, a: PetchemAssumptions = PetchemAssumptions()) -> PetchemEvaluation:
    """Incremental margin, GRM uplift and break-even PP price for ``option``."""
    revenue = option.pp_t_y * pp_price_usd_t
    margin = revenue - option.forgone_value_usd_y - option.opex_usd_y
    crf = capital_recovery_factor(a.hurdle_rate, a.life_years)
    charge = option.capex_usd * crf
    breakeven = (option.forgone_value_usd_y + option.opex_usd_y + charge) / option.pp_t_y
    payback = option.capex_usd / margin if margin > 0 and option.capex_usd > 0 else None
    return PetchemEvaluation(option, pp_price_usd_t, margin, margin / option.crude_bbl_y, charge,
                             margin - charge, payback, breakeven)


def breakeven_grid(result: RefineryResult, deck: PriceDeck, pp_prices: list[float],
                   a: PetchemAssumptions = PetchemAssumptions()) -> dict:
    """Evaluate all three modes over a range of PP prices."""
    out = {}
    for mode in PROPYLENE_WT:
        opt = build_option(result, deck, mode, a)
        out[mode] = {"option": opt, "evals": [evaluate(opt, p, a) for p in pp_prices]}
    return out


def affordable_fcc_capex_usd(option: PetchemOption, pp_price_usd_t: float, a: PetchemAssumptions = PetchemAssumptions()) -> float:
    """Most the FCC-side revamp (or new propylene-mode unit) can cost before the option stops
    covering its capital charge at ``pp_price_usd_t`` - the number to hold a licensor quote against."""
    crf = capital_recovery_factor(a.hurdle_rate, a.life_years)
    margin = option.pp_t_y * pp_price_usd_t - option.forgone_value_usd_y - option.opex_usd_y
    return max(0.0, (margin - option.capex_pp_usd * crf) / crf)
