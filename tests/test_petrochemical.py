from dataclasses import replace

import pytest

from refinery_design import petrochemical as pc
from refinery_design.assay import load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.complexity import nelson_complexity
from refinery_design.flowsheet import RefineryConfig, refine
from refinery_design.grm import PriceDeck, calibrate_deck

R = paradip_model_refinery()
DECK = calibrate_deck(R, PriceDeck(79.18), 11.25)


def test_capex_anchor_and_scaling():
    assert pc.PARADIP_PP_CAPEX_USD == pytest.approx(3150e7 / 69.89, rel=1e-9)     # ~ $451 M
    assert pc.pp_capex_usd(680_000) == pytest.approx(pc.PARADIP_PP_CAPEX_USD)
    assert pc.pp_capex_usd(340_000) == pytest.approx(pc.PARADIP_PP_CAPEX_USD * 0.5 ** 0.6)
    assert pc.pp_capex_usd(340_000) / 340_000 > pc.PARADIP_PP_CAPEX_USD / 680_000     # economies of scale


def test_paradip_implies_a_propylene_mode_yield_of_16_percent():
    assert pc.PARADIP_IMPLIED_PROPYLENE_WT == pytest.approx(16.19, abs=0.01)
    assert pc.PROPYLENE_WT["conventional"] < pc.PROPYLENE_WT["zsm5"] < pc.PROPYLENE_WT["propylene_mode"]


def test_options_are_ordered_by_propylene_and_pp_capacity():
    o = {m: pc.build_option(R, DECK, m) for m in pc.PROPYLENE_WT}
    assert o["conventional"].pp_t_y < o["zsm5"].pp_t_y < o["propylene_mode"].pp_t_y
    assert o["zsm5"].propylene_t_y == pytest.approx(1.5 * o["conventional"].propylene_t_y)
    assert o["propylene_mode"].propylene_wt_pct_of_fcc_feed == pytest.approx(16.19, abs=0.05)
    assert o["conventional"].capex_pp_usd < o["zsm5"].capex_pp_usd < o["propylene_mode"].capex_pp_usd
    # conventional recovery only displaces LPG; the others also displace gasoline / LCO
    assert set(o["conventional"].forgone_by_pool_t_y) == {"lpg"}
    assert "gasoline_range" in o["zsm5"].forgone_by_pool_t_y
    assert "middle_distillate" in o["propylene_mode"].forgone_by_pool_t_y


def test_propylene_tracks_the_lpg_the_fcc_makes():
    light = refine(load_crude("bakken"), 200_000)     # high-LPG feed
    heavy = refine(load_crude("cold_lake_blend"), 200_000)
    assert pc.build_option(light, DECK, "conventional").propylene_t_y / light.distillation.stream("vgo").mass_kg_h > \
        pc.build_option(heavy, DECK, "conventional").propylene_t_y / heavy.distillation.stream("vgo").mass_kg_h


def test_evaluation_is_linear_in_pp_price_and_breakeven_zeroes_the_net():
    opt = pc.build_option(R, DECK, "zsm5")
    e1, e2 = pc.evaluate(opt, 1000.0), pc.evaluate(opt, 1200.0)
    assert e2.margin_usd_y - e1.margin_usd_y == pytest.approx(opt.pp_t_y * 200.0)
    at_be = pc.evaluate(opt, e1.breakeven_pp_price_usd_t)
    assert at_be.net_usd_y == pytest.approx(0.0, abs=1.0)
    assert e1.grm_uplift_usd_bbl == pytest.approx(e1.margin_usd_y / opt.crude_bbl_y)


def test_displacing_fuel_products_raises_the_breakeven_when_fuel_margins_are_strong():
    # same crude price, hotter light-product cracks (so LPG, priced off crude, does not move)
    cool, hot = calibrate_deck(R, PriceDeck(79.18), 11.25), calibrate_deck(R, PriceDeck(79.18), 19.52)
    be = lambda d, m: pc.evaluate(pc.build_option(R, d, m), 1000.0).breakeven_pp_price_usd_t
    assert be(hot, "propylene_mode") > be(cool, "propylene_mode") + 50    # gasoline/LCO displaced
    assert be(hot, "conventional") == pytest.approx(be(cool, "conventional"), abs=1.0)   # LPG price unchanged


def test_affordable_fcc_capex_is_monotone_in_pp_price():
    opt = pc.build_option(R, DECK, "propylene_mode")
    lo, hi = pc.affordable_fcc_capex_usd(opt, 1000.0), pc.affordable_fcc_capex_usd(opt, 1300.0)
    assert 0.0 <= lo < hi
    assert pc.affordable_fcc_capex_usd(opt, 500.0) == 0.0
    assert any("FCC revamp capex is NOT included" in w for w in opt.warnings)


def test_petrochemical_units_do_not_move_the_nelson_index():
    """The factor table has no polymer/PP entry, so integration is invisible to complexity."""
    opt = pc.build_option(R, DECK, "propylene_mode")
    assert opt.nci_change == 0.0
    base = R.complexity()
    assert nelson_complexity(R.feed_kg_h, {"vacuum": 1.0, "fcc": 1.0, "thermal": 1.0}) == \
        nelson_complexity(R.feed_kg_h, {"vacuum": 1.0, "fcc": 1.0, "thermal": 1.0})
    assert base > 1.0


def test_guard_rails():
    with pytest.raises(ValueError, match="mode"):
        pc.build_option(R, DECK, "steam_cracker")
    no_fcc = refine(load_crude("bakken"), 200_000, RefineryConfig(fcc=False))
    with pytest.raises(ValueError, match="no FCC"):
        pc.build_option(no_fcc, DECK, "conventional")
    small = refine(load_crude("bakken"), 20_000)
    assert any("far below Paradip" in w for w in pc.build_option(small, DECK, "conventional").warnings)


def test_capital_recovery_factor():
    assert pc.capital_recovery_factor(0.12, 20) == pytest.approx(0.13388, abs=1e-4)


def test_grid_covers_all_modes():
    g = pc.breakeven_grid(R, DECK, [900.0, 1100.0])
    assert set(g) == set(pc.PROPYLENE_WT) and all(len(v["evals"]) == 2 for v in g.values())
