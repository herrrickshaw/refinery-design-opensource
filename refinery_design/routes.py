"""Options for a refinery whose petrol outlet is shrinking (ethanol blending), and a screen of what each earns.

The screen sizes, for one flowsheet result and one price deck:

* how much gasoline-range product each option removes (kt/y) - to compare with what the E12 -> E20 step displaces;
* the fuel-only margin change (sell what the FCC now makes as LPG / LCO instead of gasoline);
* the petrochemical margin where the option feeds a PP or PE/PP unit, before and after a capital charge;
* the gas-plant load ratio for FCC modes (Process Consulting Services paper, see ``fcc_modes``).

Every margin is against the SAME deck; LCO is valued at ``lco_discount`` x diesel (low cetane, needs hydrotreating - its
cost is not included).  Baseline (row 0) is exporting the surplus petrol, which is what India has actually been doing:
PPAC shows petrol exports rising from 13.1 to 16.7 Mt between FY2022-23 and FY2025-26.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import ethanol
from . import petrochemical as pc
from . import steam_cracker as sc
from .fcc_modes import modes
from .flowsheet import RefineryResult
from .petchem_prices import PetchemPriceDeck


@dataclass(frozen=True)
class RouteRow:
    name: str
    gasoline_removed_kt_y: float
    fuel_margin_usd_m_y: float           # change vs the base FCC mode (fuel products only)
    petchem_margin_usd_m_y: float | None  # before capital
    capital_charge_usd_m_y: float | None
    net_usd_m_y: float | None
    wgfr_ratio: float | None
    note: str


def displaced_by_blend_step(result: RefineryResult, ms_mmt: float, from_blend: float = 0.12, to_blend: float = 0.20) -> float:
    """Gasoline-range volume (kt/y) this refinery would need to place elsewhere when the national blend rises, assuming it
    supplies the domestic market pro rata: its gasoline-range pool x (fraction of refinery petrol no longer needed)."""
    pool_kt = result.pools_kg_h["gasoline_range"] * 8400.0 / 1e6
    frac = ethanol.blend_step_freed_mmt(ms_mmt, from_blend, to_blend) / ethanol.refinery_petrol_mmt(ms_mmt, from_blend)
    return pool_kt * frac


def petrol_switch_options(result: RefineryResult, deck, prices: PetchemPriceDeck, pe_usd_t: float | None = None,
                          a: pc.PetchemAssumptions = pc.PetchemAssumptions(), lco_discount: float = 0.90,
                          cracker: sc.CrackerAssumptions = sc.CrackerAssumptions()) -> list[RouteRow]:
    if result.fcc is None:
        raise ValueError("this flowsheet has no FCC")
    hours = a.stream_hours
    crf = pc.capital_recovery_factor(a.hurdle_rate, a.life_years)
    lpg, gas, mid = deck.product_usd_t("lpg"), deck.product_usd_t("gasoline_range"), deck.product_usd_t("middle_distillate")
    lco = lco_discount * mid
    feed, op = result.fcc.feed, result.fcc.operation
    ms = modes(feed, op, hours)
    base = ms[0]
    feed_t_y = op.feed_rate_kg_s * 3600.0 * hours / 1000.0
    rows = [RouteRow("export the surplus petrol (baseline)", 0.0, 0.0, None, None, 0.0, None,
                     "what India is doing now: petrol exports 13.1 -> 16.7 Mt FY22-23 to FY25-26 (PPAC)")]
    for m in ms[1:]:
        d_gas, d_lpg, d_lco = m.gasoline_change_t_y, m.lpg_change_t_y, m.lco_change_t_y
        fuel = (d_gas * gas + d_lpg * lpg + d_lco * lco) / 1e6
        g = m.gas_plant
        note = {"distillate": "LCO needs hydrotreating (cetane ~20); no gas-plant penalty (WGFR falls)",
                "lpg_zsm5": "cheap gas-plant moves may suffice",
                "high_severity": "compressor/driver and absorber changes likely",
                "propylene": "beyond the PCS paper's 7.5-13.1 wt% range: a dedicated propylene-mode unit and gas plant, not a tweak"}[m.name]
        rows.append(RouteRow(f"FCC {m.name}: sell LPG/LCO", -d_gas / 1e3, fuel, None, None, fuel, g.wgfr_ratio, note))
        if m.name != "distillate":
            d_prop_t = (m.propylene_wt_pct - base.propylene_wt_pct) / 100.0 * feed_t_y
            if d_prop_t > 0:
                pp_t = d_prop_t * a.pp_yield_t_per_t_propylene
                margin = (pp_t * prices.pp_realised_usd_t - d_prop_t * lpg - pp_t * a.pp_opex_usd_t) / 1e6
                charge = pc.pp_capex_usd(pp_t) * crf / 1e6
                rows.append(RouteRow(f"FCC {m.name} + PP unit", -d_gas / 1e3, fuel + margin, margin, charge, fuel + margin - charge, g.wgfr_ratio,
                                     f"{pp_t/1e3:.0f} kt/y PP from the incremental propylene; FCC-side capex not included"))
    naphtha_t_y = result.pools_kg_h and result.distillation.stream("naphtha").mass_kg_h * hours / 1000.0
    if pe_usd_t is not None and naphtha_t_y > 0:
        o = sc.build_cracker(naphtha_t_y, 850.0, cracker, crude_t_y=result.feed_kg_h * hours / 1000.0)
        e = sc.evaluate_cracker(o, deck, pe_usd_t, prices.pp_realised_usd_t, a=cracker)
        rows.append(RouteRow("naphtha steam cracker -> PE + PP", naphtha_t_y / 1e3, 0.0, e.margin_before_capital_usd_y / 1e6,
                             e.capital_charge_usd_y / 1e6, e.net_usd_y / 1e6, None,
                             f"{o.ethylene_t_y/1e6:.2f} Mt/y ethylene" + (" (sub-scale)" if o.warnings else "")))
    return rows
