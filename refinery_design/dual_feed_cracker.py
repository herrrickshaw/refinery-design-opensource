"""Dual-feed cracker: naphtha + LPG (propane/butane) -> ethylene, propylene, PE, PP.

Why: India's new crackers (IOCL Paradip 1.5 Mt/y "dual-feed", BPCL Bina 1.2 Mt/y ethylene) are dual-feed, and a
single-feed naphtha cracker does not pay here (``steam_cracker.py``).  LPG cracks to far more ethylene per tonne than naphtha
(~42% vs ~27%) - but India imports 64% of its LPG (PPAC: 21.3 Mt in FY2025-26), so every tonne cracked is a tonne of cooking-gas
supply that must be replaced by an import.  The economics are therefore priced at the deck's LPG (import-parity) price.

Sources
-------
* **Propane (real industrial data):** US patent 5,990,370 (BP Chemicals), Table 1, "KG Dedicated Propane Cracking Yields" at
  84-92% per-pass propane conversion (Kinneil gas cracker, coil outlet 823-832 C, steam/hydrocarbon 0.30, inlet 2-3 barg, ~1 s),
  read from the patent page images.  Table 2 (ethane, 50-65% conversion) gives the ethane-recycle selectivity used here
  (ethylene 0.80, hydrogen 0.053, methane 0.073 per tonne converted at 60% conversion).  Unconverted propane and ethane are
  recycled to extinction - the standard arrangement, and the patent's own (its process recycles residual ethane and propane).
* **Butane: NOT verified.**  Two search summaries conflict (~46% ethylene + 20% propylene vs 32-40% ethylene and 53-57% total
  olefins).  The butane slate below takes the conservative source's ethylene midpoint (36 wt%) and assumes the rest; treat the
  butane fraction as low-confidence.  ``butane_fraction`` defaults to 0.5, an assumption (Indian LPG grades and FCC LPG vary).
* Naphtha slate, PE/PP factors, capex and prices: ``steam_cracker.py``.  Dual-feed itself: IOCL Paradip is described as a
  "dual-feed naphtha cracker" and BPCL Bina as a dual-feed cracker; no feed-split percentages were found in any source, so the
  split is a variable here, not a fact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import steam_cracker as sc
from .petrochemical import capital_recovery_factor

# US 5,990,370 Table 1: per-pass yields, wt% of propane fed, by pure-propane conversion (%)
_PROPANE_TABLE = {
    84: dict(hydrogen=1.50, methane=20.72, ethane=3.03, ethylene=32.35, acetylene=0.15, propane=16.00, propylene=16.34, c3_acet=0.33,
             butadiene=1.94, iso_butene=0.05, n_butane=0.04, iso_butane=0.08, butene1=1.04, butene2=0.44, benzene=1.61, other_gasoline=3.08, fuel_oil=1.10),
    86: dict(hydrogen=1.54, methane=21.67, ethane=3.14, ethylene=33.72, acetylene=0.32, propane=14.00, propylene=15.65, c3_acet=0.35,
             butadiene=2.07, iso_butene=0.05, n_butane=0.04, iso_butane=0.06, butene1=0.96, butene2=0.45, benzene=1.74, other_gasoline=3.17, fuel_oil=1.10),
    88: dict(hydrogen=1.59, methane=22.61, ethane=3.25, ethylene=34.88, acetylene=0.49, propane=12.00, propylene=14.97, c3_acet=0.37,
             butadiene=2.19, iso_butene=0.05, n_butane=0.03, iso_butane=0.05, butene1=0.89, butene2=0.45, benzene=1.86, other_gasoline=3.25, fuel_oil=1.10),
    90: dict(hydrogen=1.63, methane=23.55, ethane=3.36, ethylene=36.04, acetylene=0.66, propane=10.00, propylene=14.29, c3_acet=0.39,
             butadiene=2.31, iso_butene=0.05, n_butane=0.03, iso_butane=0.04, butene1=0.82, butene2=0.46, benzene=1.98, other_gasoline=3.33, fuel_oil=1.10),
    92: dict(hydrogen=1.67, methane=24.49, ethane=3.46, ethylene=37.19, acetylene=0.82, propane=8.00, propylene=13.61, c3_acet=0.41,
             butadiene=2.43, iso_butene=0.05, n_butane=0.02, iso_butane=0.03, butene1=0.75, butene2=0.46, benzene=2.10, other_gasoline=3.41, fuel_oil=1.10),
}
_C4_KEYS = ("butadiene", "iso_butene", "n_butane", "iso_butane", "butene1", "butene2")
ETHANE_SELECTIVITY = dict(ethylene=0.80, hydrogen=0.053, methane=0.073)   # patent Table 2, 60% conversion, per t converted
BUTANE_ETHYLENE_WT = 36.0     # midpoint of the conservative cited range (32-40) - low confidence
INDIA_LPG_IMPORT_MT_FY2526 = 21.3


def per_pass_propane_yields(conversion_pct: float = 90.0) -> dict:
    """Per-pass propane cracking yields interpolated between the patent's columns (84-92% conversion)."""
    if not 84.0 <= conversion_pct <= 92.0:
        raise ValueError("propane conversion must be within the patent's 84-92% range")
    keys = sorted(_PROPANE_TABLE)
    lo = max(k for k in keys if k <= conversion_pct)
    hi = min(k for k in keys if k >= conversion_pct)
    w = 0.0 if hi == lo else (conversion_pct - lo) / (hi - lo)
    return {k: (1 - w) * _PROPANE_TABLE[lo][k] + w * _PROPANE_TABLE[hi][k] for k in _PROPANE_TABLE[lo]}


@dataclass(frozen=True)
class LpgYields:
    """Overall yields, wt% of LPG fed, with unconverted propane and ethane recycled to extinction."""
    ethylene: float
    propylene: float
    c4: float                 # butadiene + butenes + butanes
    pygas: float              # benzene + other gasoline
    pyrolysis_fuel_oil: float
    fuel_gas_and_other: float  # hydrogen, methane, acetylenes and the ethane-recycle remainder
    basis: str = "propane"

    @property
    def total(self) -> float:
        return self.ethylene + self.propylene + self.c4 + self.pygas + self.pyrolysis_fuel_oil + self.fuel_gas_and_other


def propane_yields(conversion_pct: float = 90.0) -> LpgYields:
    y = per_pass_propane_yields(conversion_pct)
    keep = 1.0 - y["propane"] / 100.0                     # propane recycled to extinction
    scale = lambda v: v / keep
    ethane = scale(y["ethane"])                            # then ethane recycled: converted with the patent's Table 2 selectivity
    ethylene = scale(y["ethylene"]) + ETHANE_SELECTIVITY["ethylene"] * ethane
    hydrogen = scale(y["hydrogen"]) + ETHANE_SELECTIVITY["hydrogen"] * ethane
    methane = scale(y["methane"]) + ETHANE_SELECTIVITY["methane"] * ethane
    remainder = ethane * (1.0 - sum(ETHANE_SELECTIVITY.values()))
    c4 = sum(scale(y[k]) for k in _C4_KEYS)
    pygas = scale(y["benzene"]) + scale(y["other_gasoline"])
    fuel_oil = scale(y["fuel_oil"])
    fuel_gas = hydrogen + methane + scale(y["acetylene"]) + scale(y["c3_acet"]) + remainder
    return LpgYields(ethylene, scale(y["propylene"]), c4, pygas, fuel_oil, fuel_gas)


def butane_yields() -> LpgYields:
    """ASSUMED butane slate (ethylene at the conservative cited midpoint; the rest assumed) - low confidence."""
    eth, prop, c4, pyg, pfo = BUTANE_ETHYLENE_WT, 17.0, 5.0, 8.0, 1.5
    return LpgYields(eth, prop, c4, pyg, pfo, 100.0 - (eth + prop + c4 + pyg + pfo), basis="butane (assumed)")


def lpg_yields(butane_fraction: float = 0.5, propane_conversion_pct: float = 90.0) -> LpgYields:
    if not 0.0 <= butane_fraction <= 1.0:
        raise ValueError("butane_fraction must be in [0, 1]")
    p, b = propane_yields(propane_conversion_pct), butane_yields()
    mix = lambda a, c: (1 - butane_fraction) * a + butane_fraction * c
    return LpgYields(mix(p.ethylene, b.ethylene), mix(p.propylene, b.propylene), mix(p.c4, b.c4), mix(p.pygas, b.pygas),
                     mix(p.pyrolysis_fuel_oil, b.pyrolysis_fuel_oil), mix(p.fuel_gas_and_other, b.fuel_gas_and_other),
                     f"{100*(1-butane_fraction):.0f}% propane / {100*butane_fraction:.0f}% butane")


@dataclass(frozen=True)
class DualFeedOption:
    naphtha_t_y: float
    lpg_t_y: float
    naphtha_yields: sc.CrackerYields
    lpg_yields: LpgYields
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
    lpg_share_pct: float
    warnings: list[str] = field(default_factory=list)


def build_dual_feed(naphtha_t_y: float, lpg_t_y: float, naphtha_coil_C: float = 850.0, butane_fraction: float = 0.5,
                    a: sc.CrackerAssumptions = sc.CrackerAssumptions(), refinery_lpg_t_y: float | None = None) -> DualFeedOption:
    """Size a dual-feed cracker + PE + PP.  ``refinery_lpg_t_y`` (if given) is the LPG the refinery itself can supply; the excess
    is imported and flagged."""
    if naphtha_t_y < 0 or lpg_t_y < 0 or naphtha_t_y + lpg_t_y <= 0:
        raise ValueError("feeds must be non-negative and not both zero")
    ny, ly = sc.yields_at(naphtha_coil_C), lpg_yields(butane_fraction)
    t = lambda feed, w: feed * w / 100.0
    eth = t(naphtha_t_y, ny.ethylene) + t(lpg_t_y, ly.ethylene)
    prop = t(naphtha_t_y, ny.propylene) + t(lpg_t_y, ly.propylene)
    total = naphtha_t_y + lpg_t_y
    capex = a.capex_usd_per_tpa_at_ref * a.ref_feed_t * (total / a.ref_feed_t) ** a.scale_exponent
    warnings = []
    if eth < 500_000:
        warnings.append(f"ethylene {eth/1e6:.2f} Mt/y is sub-scale (new Indian crackers are 1.2-1.5 Mt/y)")
    if refinery_lpg_t_y is not None and lpg_t_y > refinery_lpg_t_y:
        extra = lpg_t_y - refinery_lpg_t_y
        warnings.append(f"{extra/1e3:,.0f} kt/y of the LPG feed must be imported ({100*extra/(INDIA_LPG_IMPORT_MT_FY2526*1e6):.1f}% "
                        f"of India's FY2025-26 LPG imports); every tonne cracked is a tonne of cooking-gas supply to replace")
    if lpg_t_y > 0 and butane_fraction > 0:
        warnings.append("butane yields are assumed (low confidence); propane yields are from US 5,990,370 Table 1")
    return DualFeedOption(
        naphtha_t_y, lpg_t_y, ny, ly, eth, prop, eth * sc.PE_PER_T_ETHYLENE, prop * a.pp_yield_t_per_t_propylene,
        t(naphtha_t_y, ny.butadiene + ny.other_c4) + t(lpg_t_y, ly.c4), t(naphtha_t_y, ny.pygas) + t(lpg_t_y, ly.pygas),
        t(naphtha_t_y, ny.pyrolysis_fuel_oil) + t(lpg_t_y, ly.pyrolysis_fuel_oil),
        t(naphtha_t_y, ny.fuel_gas_and_other) + t(lpg_t_y, ly.fuel_gas_and_other), capex,
        (eth * sc.CO2_T_PER_T_ETHYLENE[0], eth * sc.CO2_T_PER_T_ETHYLENE[1]), 100.0 * lpg_t_y / total, warnings)


@dataclass(frozen=True)
class DualFeedEvaluation:
    revenue_usd_y: float
    revenue_by_product_usd_y: dict
    feed_cost_usd_y: float
    opex_usd_y: float
    capital_charge_usd_y: float
    net_usd_y: float
    margin_before_capital_usd_y: float
    margin_per_t_feed_usd: float
    breakeven_pe_usd_t: float


def evaluate_dual_feed(opt: DualFeedOption, deck, pe_usd_t: float, pp_usd_t: float, naphtha_usd_t: float | None = None,
                       lpg_usd_t: float | None = None, a: sc.CrackerAssumptions = sc.CrackerAssumptions()) -> DualFeedEvaluation:
    """Economics on ``deck``: naphtha at its trade/naphtha price (else gasoline-range), LPG at the deck's LPG (import-parity) price."""
    if naphtha_usd_t is None:
        try:
            naphtha_usd_t = deck.product_usd_t("naphtha")
        except (KeyError, AttributeError):
            naphtha_usd_t = deck.product_usd_t("gasoline_range")
    lpg_usd_t = deck.product_usd_t("lpg") if lpg_usd_t is None else lpg_usd_t
    rev = {"polyethylene": opt.pe_t_y * pe_usd_t, "polypropylene": opt.pp_t_y * pp_usd_t,
           "C4 incl. butadiene (at LPG value)": opt.c4_t_y * deck.product_usd_t("lpg"),
           "pygas (at gasoline-range value)": opt.pygas_t_y * deck.product_usd_t("gasoline_range"),
           "pyrolysis fuel oil (at fuel-oil value)": opt.pfo_t_y * deck.product_usd_t("slurry")}
    revenue = sum(rev.values())
    feed_cost = opt.naphtha_t_y * naphtha_usd_t + opt.lpg_t_y * lpg_usd_t
    total = opt.naphtha_t_y + opt.lpg_t_y
    opex = total * a.cracker_opex_usd_t_naphtha + opt.pe_t_y * a.pe_opex_usd_t + opt.pp_t_y * a.pp_opex_usd_t
    charge = opt.capex_usd * capital_recovery_factor(a.hurdle_rate, a.life_years)
    before = revenue - feed_cost - opex
    other = revenue - rev["polyethylene"]
    be_pe = (feed_cost + opex + charge - other) / opt.pe_t_y
    return DualFeedEvaluation(revenue, rev, feed_cost, opex, charge, before - charge, before, before / total, be_pe)


def lpg_share_sweep(total_feed_t: float, deck, pe_usd_t: float, pp_usd_t: float, shares=(0.0, 0.25, 0.5, 0.75, 1.0),
                    butane_fraction: float = 0.5, a: sc.CrackerAssumptions = sc.CrackerAssumptions()) -> list[dict]:
    """Same total feed, varying LPG share: the dual-feed flexibility question."""
    out = []
    for s in shares:
        o = build_dual_feed(total_feed_t * (1 - s), total_feed_t * s, butane_fraction=butane_fraction, a=a)
        e = evaluate_dual_feed(o, deck, pe_usd_t, pp_usd_t, a=a)
        out.append({"lpg_share": s, "ethylene_mt": o.ethylene_t_y / 1e6, "before_capital_usd_m": e.margin_before_capital_usd_y / 1e6,
                    "net_usd_m": e.net_usd_y / 1e6, "margin_per_t_feed": e.margin_per_t_feed_usd, "breakeven_pe": e.breakeven_pe_usd_t})
    return out


def breakeven_lpg_usd_t(opt: DualFeedOption, deck, pe_usd_t: float, pp_usd_t: float, naphtha_usd_t: float | None = None,
                        a: sc.CrackerAssumptions = sc.CrackerAssumptions()) -> float:
    """LPG price at which the dual-feed cracker's net (after capital) is zero, other prices fixed.  Net is linear in the LPG price."""
    if opt.lpg_t_y <= 0:
        raise ValueError("no LPG in this feed")
    p0 = deck.product_usd_t("lpg")
    e = evaluate_dual_feed(opt, deck, pe_usd_t, pp_usd_t, naphtha_usd_t, p0, a)
    return p0 + e.net_usd_y / opt.lpg_t_y


def available_lpg_for_cracker(result, hours: float = 8400.0, recover_propylene: bool = True) -> dict:
    """LPG the refinery can supply as cracker feed: its LPG pool (crude LPG + FCC LPG) less the FCC propylene recovered for PP
    (cracking already-made propylene would waste it).  Saturated C3/C4 only."""
    from .petrochemical import PROPYLENE_SHARE_OF_LPG

    pool = result.pools_kg_h["lpg"] * hours / 1000.0
    fcc_lpg = 0.0 if result.fcc is None else result.distillation.stream("vgo").mass_kg_h * hours / 1000.0 * result.fcc.yields_wt_pct["lpg"] / 100.0
    propylene = PROPYLENE_SHARE_OF_LPG * fcc_lpg if recover_propylene else 0.0
    return {"lpg_pool_t_y": pool, "fcc_lpg_t_y": fcc_lpg, "propylene_recovered_t_y": propylene, "available_t_y": max(0.0, pool - propylene)}


def refinery_dual_feed(result, deck, prices, pe_usd_t: float, lpg_share_of_feed: float | None = None, hours: float = 8400.0,
                       butane_fraction: float = 0.5, a: sc.CrackerAssumptions = sc.CrackerAssumptions()) -> dict:
    """Dual-feed cracker on the refinery's own straight-run naphtha and available LPG (no imports), or at a given LPG share of
    the resulting feed (LPG above what the refinery can supply is imported and flagged)."""
    naphtha = result.distillation.stream("naphtha").mass_kg_h * hours / 1000.0
    avail = available_lpg_for_cracker(result, hours)
    if lpg_share_of_feed is None:
        lpg = avail["available_t_y"]
    else:
        lpg = naphtha * lpg_share_of_feed / (1.0 - lpg_share_of_feed)
    opt = build_dual_feed(naphtha, lpg, butane_fraction=butane_fraction, a=a, refinery_lpg_t_y=avail["available_t_y"])
    ev = evaluate_dual_feed(opt, deck, pe_usd_t, prices.pp_realised_usd_t, a=a)
    return {"option": opt, "evaluation": ev, "supply": avail}
