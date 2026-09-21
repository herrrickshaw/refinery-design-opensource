"""Naphtha steam cracker: naphtha -> ethylene (+ propylene, C4, pygas, fuel oil) -> PE / PP.

What is cited and what is not
-----------------------------
* **Cited (search summaries of the literature; ranges, not a table):** naphtha ethylene yield ~22 wt% at 820 degC and
  ~27 wt% at 850 degC coil-outlet temperature (Chem. Eng. J. 2024 abstract); whole naphtha may give 23-30 wt%
  ethylene, 13-16 wt% propylene, 6-7 wt% butadiene, and under 5 wt% pyrolysis fuel oil; higher severity favours
  ethylene and benzene, lower severity propylene, C4 and liquids (Wikipedia, "Steam cracking"); 1-1.6 t CO2 per t
  ethylene; derivative intensities 0.92-1.01 t ethylene per t PE and 0.6 t per t MEG (Digital Refining).
* **Assumptions (no accessible source; exposed in ``CrackerYields``):** other C4 4 wt%, pygas 17 wt%, pyrolysis fuel
  oil 4 wt%, and fuel gas (H2, CH4, ethane etc.) as the balance - so the balance lump is large (~26-29 wt%) because the
  cited ethylene yields are once-through.  Cracker opex ($100/t naphtha), PE-plant opex, hurdle rate and plant life.
* **Capex anchors:** (a) $1,600 per tpa of naphtha input for a new world-scale naphtha cracker (Thunder Said Energy, via
  a search summary - cracker only); (b) BPCL Bina, Rs 49,000 crore (~$6 bn, OGJ) for a 1.2 Mt/y dual-feed cracker plus
  1.15 Mt/y PE, 0.55 Mt/y PP, aromatics and a 7.8 -> 11 MMTPA refinery expansion - an *upper bound* on cracker plus
  derivatives.  The default is $1,500/tpa of feed at a 4 Mt reference scale for cracker + derivatives, scaled by the
  six-tenths rule.
* Co-products are valued conservatively: pygas at the gasoline-range price, C4s (incl. butadiene) at the LPG price,
  pyrolysis fuel oil at the fuel-oil price, fuel gas as furnace fuel (no revenue).  Butadiene and benzene premia are
  therefore missing.

Not modelled: furnace kinetics or coking, energy integration, ethane/propane recycle, separation train design, MEG.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .petrochemical import capital_recovery_factor

ETHYLENE_PER_T_PE = 0.965        # midpoint of 0.92-1.01 (Digital Refining)
PE_PER_T_ETHYLENE = 1.0 / ETHYLENE_PER_T_PE
CO2_T_PER_T_ETHYLENE = (1.0, 1.6)
BINA_TOTAL_USD_BN = 6.0          # OGJ: Rs 49,000 crore, "nearly $6 billion" (cracker + PE + PP + aromatics + refinery expansion)
BINA_ETHYLENE_MT = 1.2
THUNDER_SAID_USD_PER_TPA = 1600.0
REF_FEED_T = 4.0e6
DEFAULT_CAPEX_USD_PER_TPA = 1500.0


@dataclass(frozen=True)
class CrackerYields:
    """Yield slate, wt% of naphtha feed.  ``fuel_gas_and_other`` is the balance."""
    coil_outlet_C: float
    ethylene: float
    propylene: float
    butadiene: float = 6.0                 # cited 6-7 wt% (low end)
    other_c4: float = 4.0                  # assumption
    pygas: float = 17.0                    # assumption
    pyrolysis_fuel_oil: float = 4.0        # assumption (cited < 5)

    @property
    def fuel_gas_and_other(self) -> float:
        return 100.0 - (self.ethylene + self.propylene + self.butadiene + self.other_c4 + self.pygas + self.pyrolysis_fuel_oil)


def yields_at(coil_outlet_C: float = 850.0) -> CrackerYields:
    """Yield slate versus severity: ethylene 22 wt% at 820 C and 27 wt% at 850 C (cited), extended linearly and held to the
    cited 20-31 wt% band; propylene falls from 16 wt% at 820 C by 1 wt% per 30 C (cited 13-16 range, direction cited)."""
    if not 780.0 <= coil_outlet_C <= 900.0:
        raise ValueError("coil outlet temperature outside the 780-900 C range this interpolation is meant for")
    eth = min(31.0, max(20.0, 22.0 + (5.0 / 30.0) * (coil_outlet_C - 820.0)))
    prop = min(16.0, max(13.0, 16.0 - (1.0 / 30.0) * (coil_outlet_C - 820.0)))
    return CrackerYields(coil_outlet_C, eth, prop)


@dataclass(frozen=True)
class CrackerAssumptions:
    stream_hours: float = 8400.0
    capex_usd_per_tpa_at_ref: float = DEFAULT_CAPEX_USD_PER_TPA
    ref_feed_t: float = REF_FEED_T
    scale_exponent: float = 0.6
    cracker_opex_usd_t_naphtha: float = 100.0    # assumption
    pe_opex_usd_t: float = 100.0                 # assumption
    pp_opex_usd_t: float = 100.0                 # assumption
    pp_yield_t_per_t_propylene: float = 0.98
    hurdle_rate: float = 0.12
    life_years: int = 20


@dataclass(frozen=True)
class CrackerOption:
    naphtha_t_y: float
    yields: CrackerYields
    ethylene_t_y: float
    propylene_t_y: float
    pe_t_y: float
    pp_t_y: float
    c4_t_y: float
    pygas_t_y: float
    pfo_t_y: float
    fuel_gas_t_y: float
    capex_usd: float
    co2_t_y: tuple
    world_scale_fraction: float          # ethylene / 1 Mt
    petrochemical_intensity_pct: float | None = None
    warnings: list[str] = field(default_factory=list)


def build_cracker(naphtha_t_y: float, coil_outlet_C: float = 850.0, a: CrackerAssumptions = CrackerAssumptions(),
                  crude_t_y: float | None = None) -> CrackerOption:
    """Size a naphtha cracker + PE (from ethylene) + PP (from propylene) on ``naphtha_t_y``."""
    if naphtha_t_y <= 0:
        raise ValueError("naphtha_t_y must be positive")
    y = yields_at(coil_outlet_C)
    if y.fuel_gas_and_other < 0:
        raise ValueError("yield slate over-fills the mass balance")
    t = lambda w: naphtha_t_y * w / 100.0
    eth, prop = t(y.ethylene), t(y.propylene)
    capex = a.capex_usd_per_tpa_at_ref * a.ref_feed_t * (naphtha_t_y / a.ref_feed_t) ** a.scale_exponent
    warnings = []
    if eth < 500_000:
        warnings.append(f"ethylene {eth/1e6:.2f} Mt/y is sub-scale (new Indian crackers are 1.2-1.5 Mt/y): the six-tenths "
                        "rule understates the diseconomy of scale and integration with a nearby cracker or a mixed LPG feed would be needed")
    return CrackerOption(
        naphtha_t_y, y, eth, prop, eth * PE_PER_T_ETHYLENE, prop * a.pp_yield_t_per_t_propylene, t(y.butadiene + y.other_c4),
        t(y.pygas), t(y.pyrolysis_fuel_oil), t(y.fuel_gas_and_other), capex,
        (eth * CO2_T_PER_T_ETHYLENE[0], eth * CO2_T_PER_T_ETHYLENE[1]), eth / 1.0e6,
        None if crude_t_y is None else 100.0 * (naphtha_t_y + 0.0) / crude_t_y, warnings)


@dataclass(frozen=True)
class CrackerEvaluation:
    revenue_usd_y: float
    revenue_by_product_usd_y: dict
    naphtha_cost_usd_y: float
    opex_usd_y: float
    capital_charge_usd_y: float
    net_usd_y: float
    margin_before_capital_usd_y: float
    margin_per_t_naphtha_usd: float
    breakeven_pe_usd_t: float
    breakeven_naphtha_usd_t: float


def evaluate_cracker(opt: CrackerOption, deck, pe_usd_t: float, pp_usd_t: float, naphtha_usd_t: float | None = None,
                     a: CrackerAssumptions = CrackerAssumptions()) -> CrackerEvaluation:
    """Economics against a price deck (anything with ``product_usd_t(pool)``) and observed PE / PP prices.

    ``naphtha_usd_t`` defaults to the deck's naphtha price if it has one, else its gasoline-range price (what the naphtha
    would otherwise earn in the petrol/reformer pool).
    """
    if naphtha_usd_t is None:
        try:
            naphtha_usd_t = deck.product_usd_t("naphtha")
        except (KeyError, AttributeError):
            naphtha_usd_t = deck.product_usd_t("gasoline_range")
    rev = {"polyethylene": opt.pe_t_y * pe_usd_t, "polypropylene": opt.pp_t_y * pp_usd_t,
           "C4 incl. butadiene (at LPG value)": opt.c4_t_y * deck.product_usd_t("lpg"),
           "pygas (at gasoline-range value)": opt.pygas_t_y * deck.product_usd_t("gasoline_range"),
           "pyrolysis fuel oil (at fuel-oil value)": opt.pfo_t_y * deck.product_usd_t("slurry")}
    revenue = sum(rev.values())
    feed_cost = opt.naphtha_t_y * naphtha_usd_t
    opex = opt.naphtha_t_y * a.cracker_opex_usd_t_naphtha + opt.pe_t_y * a.pe_opex_usd_t + opt.pp_t_y * a.pp_opex_usd_t
    charge = opt.capex_usd * capital_recovery_factor(a.hurdle_rate, a.life_years)
    before = revenue - feed_cost - opex
    other = revenue - rev["polyethylene"]
    be_pe = (feed_cost + opex + charge - other) / opt.pe_t_y
    be_naphtha = (revenue - opex - charge) / opt.naphtha_t_y
    return CrackerEvaluation(revenue, rev, feed_cost, opex, charge, before - charge, before, before / opt.naphtha_t_y, be_pe, be_naphtha)


def bina_check(a: CrackerAssumptions = CrackerAssumptions()) -> dict:
    """Compare the model's capex with BPCL Bina's disclosed total (upper bound: it also includes a refinery expansion)."""
    feed_low, feed_high = BINA_ETHYLENE_MT * 1e6 / 0.33, BINA_ETHYLENE_MT * 1e6 / 0.27      # naphtha/LPG feed for 1.2 Mt ethylene
    model = lambda f: a.capex_usd_per_tpa_at_ref * a.ref_feed_t * (f / a.ref_feed_t) ** a.scale_exponent
    return {"feed_low_t": feed_low, "feed_high_t": feed_high, "model_capex_usd_bn": (model(feed_low) / 1e9, model(feed_high) / 1e9),
            "bina_total_usd_bn": BINA_TOTAL_USD_BN, "bina_usd_per_tpa_of_feed": (BINA_TOTAL_USD_BN * 1e9 / feed_high, BINA_TOTAL_USD_BN * 1e9 / feed_low),
            "thunder_said_cracker_only_usd_bn": (THUNDER_SAID_USD_PER_TPA * feed_low / 1e9, THUNDER_SAID_USD_PER_TPA * feed_high / 1e9)}
