from dataclasses import replace

import pytest

from refinery_design import rundown as rd
from refinery_design.assay import load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.fcc import FccFeed, FccOperation, fcc_operate
from refinery_design.flowsheet import refine

REF = FccFeed("ref VGO", density_kg_m3=928.7, mabp_C=460.0, sulfur_wt=0.5, ccr_wt=0.3)
OP = FccOperation(feed_rate_kg_s=100.0)
R = fcc_operate(REF, OP)


def test_lco_slope_matches_the_digital_refining_case():
    """~5 vol% LCO for a 430 -> 380 degF gasoline end-point cut; the article's range is 4-6 vol%."""
    assert rd.LCO_GAIN_VOL_PCT_OF_FEED_PER_C * (50 / 1.8) == pytest.approx(5.0)


def test_rundown_streams_add_up_and_carry_the_sulfur():
    streams = rd.rundown(R)
    assert sum(s.wt_pct_of_feed for s in streams) == pytest.approx(100.0, abs=1e-6)
    by = {s.name: s for s in streams}
    assert by["FCC gasoline"].sulfur_ppm == pytest.approx(R.gasoline_sulfur_ppm)
    assert by["slurry (DCO)"].sulfur_ppm == pytest.approx(2 * by["LCO"].sulfur_ppm)
    # sulfur in LCO + slurry reproduces the distribution's LCO/slurry share
    s_liq = (by["LCO"].sulfur_ppm * by["LCO"].wt_pct_of_feed + by["slurry (DCO)"].sulfur_ppm * by["slurry (DCO)"].wt_pct_of_feed) / 100.0 / 1e6
    assert s_liq == pytest.approx(R.sulfur_distribution["LCO_slurry"], rel=1e-6)


def test_gasoline_end_point_shift_moves_heavy_naphtha_into_lco_and_conserves_mass():
    g = rd.gasoline_end_point_shift(R, 50 / 1.8)
    y = g["yields_wt_pct"]
    assert g["moved_vol_pct_of_feed"] == pytest.approx(5.0)
    assert y["gasoline"] < R.yields_wt_pct["gasoline"] and y["lco"] > R.yields_wt_pct["lco"]
    assert y["gasoline"] + y["lco"] == pytest.approx(R.yields_wt_pct["gasoline"] + R.yields_wt_pct["lco"])
    assert sum(v for k, v in y.items() if k != "total") == pytest.approx(100.0, abs=1e-6)
    with pytest.raises(ValueError):
        rd.gasoline_end_point_shift(R, -5.0)
    with pytest.raises(ValueError, match="more than the gasoline"):
        rd.gasoline_end_point_shift(R, 500.0)


def test_distillate_mode_gains_lco_at_the_cost_of_gasoline_and_conversion():
    d = rd.distillate_mode(REF, OP)
    assert d["lco_gain_wt_pct"] > 4.0 and d["gasoline_loss_wt_pct"] > 0
    assert d["cooler_riser"].conversion_wt_pct < d["base"].conversion_wt_pct       # cooler riser converts less
    assert d["yields_wt_pct"]["gasoline"] < d["base"].yields_wt_pct["gasoline"]


def test_model_yields_sit_inside_digital_refining_ranges():
    # FCC propylene: conventional 3-5%, high-severity 15-28% (article 1001081)
    from refinery_design import petrochemical as pc
    from refinery_design.grm import PriceDeck
    lo, hi = rd.PROPYLENE_RANGE_WT["conventional"]
    o = pc.build_option(paradip_model_refinery(), PriceDeck(80.0), "conventional")
    assert lo <= o.propylene_wt_pct_of_fcc_feed <= hi
    hs_lo, hs_hi = rd.PROPYLENE_RANGE_WT["high_severity"]
    assert hs_lo <= pc.PARADIP_IMPLIED_PROPYLENE_WT <= hs_hi
    # FCC gasoline sulfur 1,000-2,000 ppm is the typical band for a ~0.6-1.2 wt% S feed
    a, b = rd.FCC_GASOLINE_SULFUR_TYPICAL_PPM
    for s_wt in (0.6, 0.9, 1.2):
        ppm = fcc_operate(replace(REF, sulfur_wt=s_wt), OP).gasoline_sulfur_ppm
        assert a * 0.95 <= ppm <= b * 1.0, (s_wt, ppm)


def test_light_sweet_flowsheet_reproduces_the_us_style_pool_shares():
    """Digital Refining (search summary): FCC ~20 vol% of the gasoline pool, LCO ~5% of the diesel pool.
    A light-sweet Bakken slate lands near both; heavier baskets sit well above."""
    light = rd.pool_shares(refine(load_crude("bakken"), 200_000))
    assert 15 <= light["fcc_gasoline_vol_pct_of_gasoline_pool"] <= 35
    assert 3 <= light["lco_vol_pct_of_diesel_pool"] <= 8
    heavy = rd.pool_shares(paradip_model_refinery())
    assert heavy["fcc_gasoline_vol_pct_of_gasoline_pool"] > 1.5 * light["fcc_gasoline_vol_pct_of_gasoline_pool"]


def test_pool_shares_needs_an_fcc():
    from refinery_design.flowsheet import RefineryConfig
    with pytest.raises(ValueError, match="no FCC"):
        rd.pool_shares(refine(load_crude("bakken"), 100_000, RefineryConfig(fcc=False)))
