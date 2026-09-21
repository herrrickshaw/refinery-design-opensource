"""Refinery rundowns: what leaves the FCC fractionator, and how cut points and severity shift it.

Facts from Digital Refining (https://www.digitalrefining.com), read while building this module:

* "Maximising distillate production from the FCC unit" (article 1000218): the most common change is
  moving cut points - reducing the gasoline end point moves heavy gasoline into LCO; **+4-6 vol% LCO**,
  one refiner **~5 vol% for 430 -> 380 degF**; distillate mode also runs the riser **10-30 degF cooler**.
* "FCC product fractionation for maximum LCO" (1001415): LCO end point held at 640 degF (338 degC),
  flash point 130 degF (54 degC); reducing the naphtha end point "simply shifts heavy naphtha into the
  LCO product".
* "Refining/petrochemical integration - FCC gasoline to petrochemicals" (1001081): conventional FCC
  propylene **3-5%**, high-severity FCC **15-28%**; typical FCC gasoline sulfur **1,000-2,000 ppm**;
  50-70% aromatics in high-severity cracked naphtha.
* A search summary of Digital Refining material (not a fetched page): FCC ~20 vol% of the gasoline
  pool, LCO ~5% of the diesel pool, LCO cetane ~20 vs 40-60 for straight-run distillate.

The slope below is the only new model input; everything else reuses the FCC model.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .fcc import FccFeed, FccKinetics, FccOperation, FccResult, PRODUCT_DENSITY_KG_M3, fcc_operate
from .flowsheet import RefineryResult

LCO_GAIN_VOL_PCT_OF_FEED_PER_C = 5.0 / ((430.0 - 380.0) / 1.8)   # ~0.18 vol% per degC (range 4-6 vol% per 50 degF)
HEAVY_NAPHTHA_DENSITY_KG_M3 = 780.0                              # assumption
PROPYLENE_RANGE_WT = {"conventional": (3.0, 5.0), "high_severity": (15.0, 28.0)}
FCC_GASOLINE_SULFUR_TYPICAL_PPM = (1000.0, 2000.0)
LCO_SULFUR_TO_SLURRY_RATIO = 2.0                                 # assumption: slurry concentrates sulfur ~2x LCO


@dataclass(frozen=True)
class RundownStream:
    name: str
    wt_pct_of_feed: float
    vol_pct_of_feed: float | None
    density_kg_m3: float | None
    sulfur_ppm: float | None = None
    note: str = ""


def rundown(result: FccResult, propylene_share_of_lpg: float = 6.0 / 17.8) -> list[RundownStream]:
    """The FCC rundown streams with volumes, densities and sulfur (ppm)."""
    y, feed = result.yields_wt_pct, result.feed
    feed_v = 1.0 / feed.density_kg_m3
    vol = lambda k: 100.0 * (y[k] / 100.0) / PRODUCT_DENSITY_KG_M3[k] / feed_v
    s = result.sulfur_distribution
    s_liq = s["LCO_slurry"]
    lco_kg, sl_kg = y["lco"] / 100.0, y["slurry"] / 100.0
    lco_s = s_liq / (lco_kg + LCO_SULFUR_TO_SLURRY_RATIO * sl_kg) * 1e6 if (lco_kg + sl_kg) > 0 else None
    return [
        RundownStream("dry gas (H2-C2, incl. H2S)", y["dry_gas"], None, None, note="to fuel gas / amine + SRU"),
        RundownStream("LPG (C3/C4)", y["lpg"], vol("lpg"), PRODUCT_DENSITY_KG_M3["lpg"],
                      note=f"propylene ~{100*propylene_share_of_lpg:.0f}% of LPG = {y['lpg']*propylene_share_of_lpg:.1f} wt% of feed"),
        RundownStream("FCC gasoline", y["gasoline"], vol("gasoline"), PRODUCT_DENSITY_KG_M3["gasoline"], result.gasoline_sulfur_ppm,
                      "olefinic; needs post-treatment at BS-VI sulfur"),
        RundownStream("LCO", y["lco"], vol("lco"), PRODUCT_DENSITY_KG_M3["lco"], lco_s, "low cetane (~20): hydrotreat/blend"),
        RundownStream("slurry (DCO)", y["slurry"], vol("slurry"), PRODUCT_DENSITY_KG_M3["slurry"],
                      None if lco_s is None else lco_s * LCO_SULFUR_TO_SLURRY_RATIO, "black oil / carbon-black feed"),
        RundownStream("coke (burned)", y["coke"], None, None, note="regenerator fuel; SO2 from feed sulfur"),
    ]


def gasoline_end_point_shift(result: FccResult, shift_C: float) -> dict:
    """Effect of lowering the FCC gasoline end point by ``shift_C`` on gasoline/LCO yield (wt%, vol%).

    Volume-for-volume transfer of heavy naphtha into LCO at the literature slope (~0.18 vol% of feed per
    degC).  Sulfur and octane consequences are not modelled.
    """
    if shift_C < 0:
        raise ValueError("shift_C is a reduction in end point and must be >= 0")
    feed = result.feed
    moved_vol_pct = LCO_GAIN_VOL_PCT_OF_FEED_PER_C * shift_C
    moved_wt_pct = moved_vol_pct / 100.0 * HEAVY_NAPHTHA_DENSITY_KG_M3 / feed.density_kg_m3 * 100.0
    if moved_wt_pct > result.yields_wt_pct["gasoline"]:
        raise ValueError("end-point shift moves more than the gasoline made")
    y = dict(result.yields_wt_pct)
    y["gasoline"] -= moved_wt_pct
    y["lco"] += moved_wt_pct
    return {"moved_vol_pct_of_feed": moved_vol_pct, "moved_wt_pct_of_feed": moved_wt_pct, "yields_wt_pct": y}


def distillate_mode(feed: FccFeed, op: FccOperation, gasoline_end_shift_C: float = 50.0 / 1.8, rot_drop_C: float = 11.0,
                    kin: FccKinetics = FccKinetics()) -> dict:
    """Distillate mode: riser ``rot_drop_C`` cooler (literature: 10-30 degF = 5.6-16.7 degC) plus a gasoline
    end-point reduction.  Returns base and distillate-mode yields and the LCO gain."""
    base = fcc_operate(feed, op, kin)
    cool = fcc_operate(feed, replace(op, riser_outlet_C=op.riser_outlet_C - rot_drop_C), kin)
    shifted = gasoline_end_point_shift(cool, gasoline_end_shift_C)
    y = shifted["yields_wt_pct"]
    return {"base": base, "cooler_riser": cool, "yields_wt_pct": y,
            "lco_gain_wt_pct": y["lco"] - base.yields_wt_pct["lco"],
            "gasoline_loss_wt_pct": base.yields_wt_pct["gasoline"] - y["gasoline"]}


def pool_shares(result: RefineryResult) -> dict:
    """FCC's share of the gasoline-range and diesel-range pools (vol%) in a flowsheet result.

    Reference point (US-style, search summary): FCC ~20 vol% of the gasoline pool, LCO ~5% of the diesel pool.
    A heavy-sour Indian basket with a light-ends-poor crude unit is expected to sit well above both.
    """
    if result.fcc is None:
        raise ValueError("no FCC in this flowsheet")
    S = result.distillation.streams
    vgo_t = S["vgo"].mass_kg_h
    y = result.fcc.yields_wt_pct
    rho = PRODUCT_DENSITY_KG_M3
    fcc_gasoline_m3 = vgo_t * y["gasoline"] / 100.0 / rho["gasoline"]
    lco_m3 = vgo_t * y["lco"] / 100.0 / rho["lco"]
    naphtha_m3 = S["naphtha"].mass_kg_h / S["naphtha"].density_kg_m3
    diesel_m3 = (S["kerosene"].mass_kg_h / S["kerosene"].density_kg_m3
                 + S["diesel"].mass_kg_h / S["diesel"].density_kg_m3)
    coker_naphtha_m3 = coker_go_m3 = 0.0
    if result.coker is not None:
        coker_naphtha_m3 = result.coker.naphtha_kg_h / 730.0
        coker_go_m3 = result.coker.gas_oil_kg_h / 900.0
    gasoline_pool = naphtha_m3 + fcc_gasoline_m3 + coker_naphtha_m3
    diesel_pool = diesel_m3 + lco_m3 + coker_go_m3
    return {"fcc_gasoline_vol_pct_of_gasoline_pool": 100.0 * fcc_gasoline_m3 / gasoline_pool,
            "lco_vol_pct_of_diesel_pool": 100.0 * lco_m3 / diesel_pool}
