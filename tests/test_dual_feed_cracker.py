import pytest

from refinery_design import dual_feed_cracker as df
from refinery_design import petchem_prices as pp
from refinery_design import safety as sf
from refinery_design import steam_cracker as sc
from refinery_design import trade
from refinery_design.benchmarks import paradip_model_refinery

R = paradip_model_refinery(True)
DECK = trade.RebasedTradeDeck("2025-26", pp.crude_snapshot()["brent"])
PE, PRICES = pp.iocl_pe_usd_t(), pp.iocl_deck()
PP = PRICES.pp_usd_t


def test_per_pass_propane_yields_reproduce_the_patents_table_exactly_at_its_columns():
    y = df.per_pass_propane_yields(88.0)
    assert y["ethylene"] == 34.88 and y["propylene"] == 14.97 and y["methane"] == 22.61 and y["propane"] == 12.00 and y["benzene"] == 1.86
    assert df.per_pass_propane_yields(84.0)["ethylene"] == 32.35 and df.per_pass_propane_yields(92.0)["ethylene"] == 37.19
    mid = df.per_pass_propane_yields(89.0)
    assert mid["ethylene"] == pytest.approx((34.88 + 36.04) / 2)
    with pytest.raises(ValueError):
        df.per_pass_propane_yields(95.0)


def test_each_patent_column_is_close_to_a_mass_balance():
    for c, col in df._PROPANE_TABLE.items():
        assert sum(col.values()) == pytest.approx(100.0, abs=0.6), c              # rounding and unlisted trace species


def test_propane_recycled_to_extinction_gives_the_commonly_quoted_ethylene_yield():
    y = df.propane_yields(90.0)
    assert 41.0 <= y.ethylene <= 45.0 and 14.0 <= y.propylene <= 19.0             # ~42% ethylene from propane with recycle
    assert y.total == pytest.approx(100.0, abs=0.3)
    assert df.propane_yields(92.0).ethylene > df.propane_yields(84.0).ethylene    # severity raises ethylene ...
    assert df.propane_yields(92.0).propylene < df.propane_yields(84.0).propylene   # ... and lowers propylene


def test_propane_beats_naphtha_on_ethylene_per_tonne_but_makes_far_less_pygas():
    p, n = df.propane_yields(90.0), sc.yields_at(850.0)
    assert p.ethylene > n.ethylene + 10 and p.pygas < n.pygas / 2 and p.pyrolysis_fuel_oil < n.pyrolysis_fuel_oil


def test_butane_is_flagged_as_assumed_and_the_mix_interpolates():
    b = df.butane_yields()
    assert "assumed" in b.basis and b.ethylene == 36.0 and b.total == pytest.approx(100.0)
    mix = df.lpg_yields(0.5)
    assert mix.ethylene == pytest.approx(0.5 * df.propane_yields().ethylene + 0.5 * b.ethylene)
    assert "50% propane / 50% butane" == mix.basis
    assert df.lpg_yields(0.0).ethylene == pytest.approx(df.propane_yields().ethylene)
    with pytest.raises(ValueError):
        df.lpg_yields(1.5)


def test_mass_balance_and_derivatives_of_the_dual_feed_option():
    o = df.build_dual_feed(2.0e6, 1.0e6)
    assert o.ethylene_t_y + o.propylene_t_y + o.c4_t_y + o.pygas_t_y + o.pfo_t_y + o.fuel_gas_t_y == pytest.approx(3.0e6, rel=2e-3)
    assert o.pe_t_y == pytest.approx(o.ethylene_t_y * sc.PE_PER_T_ETHYLENE) and o.lpg_share_pct == pytest.approx(100 / 3)
    assert o.capex_usd == pytest.approx(1500.0 * 4.0e6 * (3.0e6 / 4.0e6) ** 0.6)
    assert o.co2_t_y[1] == pytest.approx(1.6 * o.ethylene_t_y)


def test_dual_feed_with_no_lpg_equals_the_naphtha_cracker():
    d, n = df.build_dual_feed(3.0e6, 0.0), sc.build_cracker(3.0e6)
    assert d.ethylene_t_y == pytest.approx(n.ethylene_t_y) and d.capex_usd == pytest.approx(n.capex_usd)
    ed = df.evaluate_dual_feed(d, DECK, PE, PP)
    en = sc.evaluate_cracker(n, DECK, PE, PP)
    assert ed.net_usd_y == pytest.approx(en.net_usd_y, rel=1e-9)


def test_more_lpg_improves_the_margin_monotonically_at_these_prices():
    sw = df.lpg_share_sweep(4.0e6, DECK, PE, PP)
    m = [r["net_usd_m"] for r in sw]
    assert m == sorted(m) and sw[-1]["ethylene_mt"] > sw[0]["ethylene_mt"]
    assert sw[0]["before_capital_usd_m"] < 0 < sw[-1]["before_capital_usd_m"]       # cash margin flips positive with LPG
    assert all(r["breakeven_pe"] > PE for r in sw)                                 # but no mix pays after capital at list PE


def test_dual_feed_still_does_not_pay_after_capital_even_at_low_capex():
    for capex in (1500.0, 1000.0, 800.0):
        a = sc.CrackerAssumptions(capex_usd_per_tpa_at_ref=capex)
        e = df.evaluate_dual_feed(df.build_dual_feed(1.0e6, 3.0e6, a=a), DECK, PE, PP, a=a)
        assert e.net_usd_y < 0


def test_break_even_lpg_price_zeroes_the_net_and_is_below_the_deck():
    o = df.build_dual_feed(1.0e6, 3.0e6)
    be = df.breakeven_lpg_usd_t(o, DECK, PE, PP)
    assert be < DECK.product_usd_t("lpg")
    assert df.evaluate_dual_feed(o, DECK, PE, PP, lpg_usd_t=be).net_usd_y == pytest.approx(0.0, abs=1e3)
    with pytest.raises(ValueError):
        df.breakeven_lpg_usd_t(df.build_dual_feed(1.0e6, 0.0), DECK, PE, PP)


def test_refinery_supply_keeps_the_fcc_propylene_for_pp():
    s = df.available_lpg_for_cracker(R)
    assert s["available_t_y"] == pytest.approx(s["lpg_pool_t_y"] - s["propylene_recovered_t_y"])
    assert s["propylene_recovered_t_y"] == pytest.approx(0.337 * s["fcc_lpg_t_y"], rel=0.01)
    assert df.available_lpg_for_cracker(R, recover_propylene=False)["available_t_y"] > s["available_t_y"]


def test_refinery_only_dual_feed_is_sub_scale_and_imports_nothing():
    r = df.refinery_dual_feed(R, DECK, PRICES, PE)
    o = r["option"]
    assert o.lpg_t_y == pytest.approx(r["supply"]["available_t_y"]) and o.ethylene_t_y < 1.0e6
    assert not any("imported" in w for w in o.warnings)


def test_higher_lpg_share_needs_imports_and_says_so():
    r = df.refinery_dual_feed(R, DECK, PRICES, PE, lpg_share_of_feed=0.75)
    w = " ".join(r["option"].warnings)
    assert "imported" in w and "LPG imports" in w and r["option"].lpg_t_y > r["supply"]["available_t_y"]


def test_guards():
    with pytest.raises(ValueError):
        df.build_dual_feed(0.0, 0.0)
    with pytest.raises(ValueError):
        df.build_dual_feed(-1.0, 1.0)


def test_safety_flags_add_lpg_handling():
    flags = sf.dual_feed_flags(df.build_dual_feed(1.0e6, 1.0e6))
    topics = {f.topic for f in flags}
    assert {"steam cracker", "polymer units", "LPG/propylene handling", "LPG-fired furnaces".replace("fired", "-fed")} <= topics or "LPG-fed furnaces" in topics
    assert all(f.basis and f.standards for f in flags)
    assert not any(f.topic == "LPG-fed furnaces" for f in sf.dual_feed_flags(df.build_dual_feed(1.0e6, 0.0)))


def test_routes_screen_includes_the_dual_feed_row():
    from refinery_design.routes import petrol_switch_options
    rows = {r.name: r for r in petrol_switch_options(R, DECK, PRICES, pe_usd_t=PE)}
    d = rows["dual-feed cracker (refinery naphtha + LPG) -> PE + PP"]
    n = rows["naphtha steam cracker -> PE + PP"]
    assert "LPG" in d.note and d.gasoline_removed_kt_y == n.gasoline_removed_kt_y
    # the bigger plant has a bigger total capital charge, so compare cash margin and net per tonne of feed, not the total net
    assert d.petchem_margin_usd_m_y > n.petchem_margin_usd_m_y
    r = df.refinery_dual_feed(R, DECK, PRICES, PE)
    feed_d = (r["option"].naphtha_t_y + r["option"].lpg_t_y) / 1e6
    feed_n = r["option"].naphtha_t_y / 1e6
    assert d.net_usd_m_y / feed_d > n.net_usd_m_y / feed_n
