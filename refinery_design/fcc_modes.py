"""FCC secondary modes of operation: shifting the FCC away from gasoline, and what that does to the gas plant.

Why: ethanol at 20% displaces refinery petrol (see ``ethanol.py``); the FCC is the gasoline machine, so the lever
is to run it in a mode that makes less gasoline and more distillate or LPG/propylene.

Modes
-----
* ``gasoline``         base case (the calibrated model).
* ``distillate``       riser ~11 degC cooler + gasoline end point -50 degF (``rundown.distillate_mode``).
* ``lpg_zsm5``         ZSM-5 additive: propylene x1.5 (6 -> 9 wt% of feed, FCC literature) taken from gasoline.
* ``high_severity``    riser +20 degC (model) plus ZSM-5.
* ``propylene``        propylene-mode: 16.2 wt% of feed (implied by Paradip's PP plant / FCC feed), taken from gasoline/LCO.

The gas plant (from "Mitigating FCC gas plant impacts when increasing reactor LPG yields", Process Consulting
Services, PTQ Q2 2023, Digital Refining) is the real constraint.  Facts used, all read from that paper's text and figures:

* wet-gas flow rate (WGFR) rises with reactor propylene yield: Figure 8, 34,500 -> 39,700 -> 44,300 ICFM at 7.5 /
  10.3 / 13.1 wt% C3= (constant dry gas, 130 F, 3.5 psig) = **+5.1% per +1 wt% propylene**;
* WGFR falls with receiver temperature (Figure 10: 130 -> 115 F cuts 34,500 -> 30,200 ICFM, ~0.8%/F; the text's rule
  of thumb is ~1%/F) and with receiver pressure (Figure 9, 13.1 wt% C3=: 44,300 / 36,000 / 30,000 ICFM at 3.5 / 6.5 / 9.5 psig);
* a pressure-drop table (nozzle coke 2-4 psi, trays -> packing 2-4, fin-fan bundles 2-5, meter 1-2 psi) lists the
  cheap debottlenecking moves; absorber C3= recovery today is typically 95-99% (85-90% historically), operated at
  >=98% (<=3 mol% C3= in off-gas); debutanised-gasoline recycle must rise (example 5 -> 25 kb/d);
* ZSM-5 cracks mid-boiling gasoline to LPG, raises WGFR, and cuts the liquid going to the absorber, lowering C3= recovery;
* "Increasing reactor LPG yields at the expense of gasoline increases profitability due to product differential values"
  - the paper's own conclusion - but only if the incremental LPG can be compressed, condensed and recovered.

Not from the paper (my extrapolation, flagged in the code): the dry-gas term in the WGFR estimate, the propylene share of
incremental LPG (60%), and the modes' yield shifts other than propylene.  Absolute compressor capacity is unit-specific and
is NOT modelled: the check reports the *ratio* to the base case and what it takes to bring it back to 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from . import petrochemical as pc
from .fcc import FccFeed, FccOperation, PRODUCT_DENSITY_KG_M3, fcc_operate
from .rundown import distillate_mode

PCS_WGFR_PCT_PER_WT_PROPYLENE = 100.0 * (44_300.0 / 34_500.0 - 1.0) / (13.1 - 7.5)     # Fig. 8 -> ~5.1
PCS_WGFR_PCT_PER_F_RECEIVER = 100.0 * (1.0 - 30_200.0 / 34_500.0) / 15.0                 # Fig. 10, 130 -> 115 F -> ~0.83
PCS_RULE_OF_THUMB_PCT_PER_F = 1.0                                                          # the paper's text
PCS_RECEIVER_PRESSURE_RATIO = [(3.5, 1.0), (6.5, 36_000.0 / 44_300.0), (9.5, 30_000.0 / 44_300.0)]  # Fig. 9
PCS_DELTA_P_OPTIONS_PSI = {"eliminate feed nozzle coke": (2, 4), "main column trays to packing": (2, 4), "air fin-fan bundles": (2, 5),
                           "eliminate wet gas flow meter": (1, 2)}
PROPYLENE_SHARE_OF_INCREMENTAL_LPG = 0.60    # assumption (not in the paper)
DRY_GAS_MW, PROPYLENE_MW = 23.0, 42.08      # dry gas incl. H2S, approximate


@dataclass(frozen=True)
class GasPlantCheck:
    wgfr_ratio: float
    receiver_temp_drop_F: float | None          # to bring WGFR back to 1.0 by temperature alone
    receiver_pressure_needed_psig: float | None  # to bring it back by pressure alone (from a 3.5 psig base); None if beyond Fig. 9
    within_paper_range: bool
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FccModeResult:
    name: str
    yields_wt_pct: dict
    propylene_wt_pct: float
    gasoline_vol_pct_of_feed: float
    gasoline_change_t_y: float
    lpg_change_t_y: float
    lco_change_t_y: float
    gas_plant: GasPlantCheck


def _propylene_wt(yields: dict) -> float:
    return pc.PROPYLENE_SHARE_OF_LPG * yields["lpg"]


def wgfr_ratio(base: dict, new: dict, propylene_new_wt: float | None = None, propylene_base_wt: float | None = None) -> float:
    """Wet-gas flow ratio (new / base) at unchanged receiver pressure and temperature.

    Propylene term is the paper's Figure 8 slope.  The dry-gas term is an extrapolation: dry gas does not condense at the
    receiver, so each wt% adds moles in proportion to 1/MW relative to propylene.
    """
    pn = _propylene_wt(new) if propylene_new_wt is None else propylene_new_wt
    pb = _propylene_wt(base) if propylene_base_wt is None else propylene_base_wt
    slope = PCS_WGFR_PCT_PER_WT_PROPYLENE / 100.0
    dry = (new["dry_gas"] - base["dry_gas"]) * slope * (PROPYLENE_MW / DRY_GAS_MW)
    return 1.0 + (pn - pb) * slope + dry


def gas_plant_check(ratio: float, base_receiver_psig: float = 3.5) -> GasPlantCheck:
    notes = ["absorber C3= recovery must stay >= 98% (<= 3 mol% C3= in off-gas): expect more debutanised-gasoline recycle "
             "(the paper's example went 5 -> 25 kb/d)"]
    if ratio <= 1.0:
        return GasPlantCheck(ratio, None, None, True, ["no extra wet-gas load"])
    dt = (1.0 - 1.0 / ratio) / (PCS_WGFR_PCT_PER_F_RECEIVER / 100.0)
    ps, rs = zip(*PCS_RECEIVER_PRESSURE_RATIO)
    need_ratio = 1.0 / ratio
    if need_ratio < min(rs):
        p_need, inside = None, False
    else:
        p_need = float(np.interp(need_ratio, rs[::-1], ps[::-1])) + (base_receiver_psig - 3.5)
        inside = True
    if ratio > 1.15:
        notes.append("wet-gas load >15% above base: check compressor curve (surge/stonewall), driver power, HP-receiver condensing "
                     "and stripper/absorber loading - a compressor or driver change may be unavoidable")
    notes.append("cheap first: pressure survey; nozzle coke, trays -> packing, fin-fan/CW bundles (2-5 psi each), "
                 "receiver temperature (~0.8-1% WGFR per F)")
    return GasPlantCheck(ratio, dt, p_need, inside, notes)


def _to_mode(name, base_yields, yields, propylene_wt, feed: FccFeed, feed_t_y: float, check_dry=True) -> FccModeResult:
    ratio = wgfr_ratio(base_yields, yields, propylene_new_wt=propylene_wt)
    rho = PRODUCT_DENSITY_KG_M3["gasoline"]
    return FccModeResult(
        name=name, yields_wt_pct={k: v for k, v in yields.items() if k != "total"}, propylene_wt_pct=propylene_wt,
        gasoline_vol_pct_of_feed=100.0 * (yields["gasoline"] / 100.0 / rho) / (1.0 / feed.density_kg_m3),
        gasoline_change_t_y=(yields["gasoline"] - base_yields["gasoline"]) / 100.0 * feed_t_y,
        lpg_change_t_y=(yields["lpg"] - base_yields["lpg"]) / 100.0 * feed_t_y,
        lco_change_t_y=(yields["lco"] - base_yields["lco"]) / 100.0 * feed_t_y, gas_plant=gas_plant_check(ratio))


def modes(feed: FccFeed, op: FccOperation, stream_hours: float = 8400.0) -> list[FccModeResult]:
    """All modes for one feed/operation, with gasoline, LPG and LCO changes (t/y) and the gas-plant check."""
    feed_t_y = op.feed_rate_kg_s * 3600.0 * stream_hours / 1000.0
    base = fcc_operate(feed, op)
    b = {k: v for k, v in base.yields_wt_pct.items() if k != "total"}
    out = [_to_mode("gasoline", b, b, _propylene_wt(b), feed, feed_t_y)]

    d = distillate_mode(feed, op)
    yd = {k: v for k, v in d["yields_wt_pct"].items() if k != "total"}
    out.append(_to_mode("distillate", b, yd, _propylene_wt(yd), feed, feed_t_y))

    def zsm5(y):
        y = dict(y)
        prop0 = _propylene_wt(y)
        d_prop = (pc.ZSM5_MULTIPLIER - 1.0) * prop0
        d_lpg = d_prop / PROPYLENE_SHARE_OF_INCREMENTAL_LPG
        y["lpg"] += d_lpg
        y["gasoline"] -= d_lpg
        return y, prop0 + d_prop

    y1, p1 = zsm5(b)
    out.append(_to_mode("lpg_zsm5", b, y1, p1, feed, feed_t_y))

    hot = fcc_operate(feed, replace(op, riser_outlet_C=op.riser_outlet_C + 20.0))
    yh = {k: v for k, v in hot.yields_wt_pct.items() if k != "total"}
    y2, p2 = zsm5(yh)
    out.append(_to_mode("high_severity", b, y2, p2, feed, feed_t_y))

    target = pc.PROPYLENE_WT["propylene_mode"]
    y3 = dict(yh)
    d_prop = max(0.0, target - _propylene_wt(y3))
    d_lpg = d_prop / PROPYLENE_SHARE_OF_INCREMENTAL_LPG
    off_g = 0.7
    y3["lpg"] += d_lpg
    y3["gasoline"] -= off_g * d_lpg
    y3["lco"] -= (1 - off_g) * d_lpg
    if y3["gasoline"] < 0 or y3["lco"] < 0:
        raise ValueError("propylene-mode shift exceeds the gasoline/LCO available")
    out.append(_to_mode("propylene", b, y3, target, feed, feed_t_y))
    return out
