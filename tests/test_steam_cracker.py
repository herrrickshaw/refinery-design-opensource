import pytest

from refinery_design import petchem_prices as pp
from refinery_design import steam_cracker as sc
from refinery_design import trade


def test_yield_slate_matches_the_cited_ethylene_points_and_ranges():
    assert sc.yields_at(820).ethylene == pytest.approx(22.0) and sc.yields_at(850).ethylene == pytest.approx(27.0)
    for t in (800, 820, 850, 880):
        y = sc.yields_at(t)
        assert 20 <= y.ethylene <= 31 and 13 <= y.propylene <= 16 and 6 <= y.butadiene <= 7
        assert y.pyrolysis_fuel_oil < 5                              # cited: under 5 wt%
        assert y.fuel_gas_and_other > 0
        total = y.ethylene + y.propylene + y.butadiene + y.other_c4 + y.pygas + y.pyrolysis_fuel_oil + y.fuel_gas_and_other
        assert total == pytest.approx(100.0)
    assert sc.yields_at(880).ethylene > sc.yields_at(820).ethylene and sc.yields_at(880).propylene < sc.yields_at(820).propylene
    with pytest.raises(ValueError):
        sc.yields_at(950)


def test_ethylene_derivative_intensities():
    assert 0.92 <= sc.ETHYLENE_PER_T_PE <= 1.01
    assert sc.PE_PER_T_ETHYLENE == pytest.approx(1.036, abs=0.001)
    o = sc.build_cracker(3.0e6, 850.0)
    assert o.pe_t_y == pytest.approx(o.ethylene_t_y * sc.PE_PER_T_ETHYLENE) and o.pp_t_y == pytest.approx(o.propylene_t_y * 0.98)
    assert o.co2_t_y[0] == pytest.approx(o.ethylene_t_y) and o.co2_t_y[1] == pytest.approx(1.6 * o.ethylene_t_y)


def test_mass_balance_of_the_cracker_slate():
    o = sc.build_cracker(2.0e6, 850.0)
    assert o.ethylene_t_y + o.propylene_t_y + o.c4_t_y + o.pygas_t_y + o.pfo_t_y + o.fuel_gas_t_y == pytest.approx(o.naphtha_t_y)


def test_capex_scales_by_six_tenths_and_matches_bina_order_of_magnitude():
    small, big = sc.build_cracker(1.0e6), sc.build_cracker(4.0e6)
    assert big.capex_usd == pytest.approx(1500.0 * 4.0e6)
    assert small.capex_usd / 1.0e6 > big.capex_usd / 4.0e6                    # economies of scale
    b = sc.bina_check()
    lo, hi = b["model_capex_usd_bn"]
    assert 0.8 * b["bina_total_usd_bn"] < lo < 1.2 * b["bina_total_usd_bn"] and hi < 1.2 * b["bina_total_usd_bn"] + 0.6


def test_sub_scale_warning_and_guards():
    assert any("sub-scale" in w for w in sc.build_cracker(1.0e6).warnings)
    assert not sc.build_cracker(4.0e6).warnings
    with pytest.raises(ValueError):
        sc.build_cracker(0)


def test_economics_reconcile_and_break_evens_zero_the_net():
    o = sc.build_cracker(3.0e6)
    d = trade.RebasedTradeDeck("2025-26", pp.crude_snapshot()["brent"])
    pe, ppp = pp.iocl_pe_usd_t(), pp.iocl_deck().pp_usd_t
    e = sc.evaluate_cracker(o, d, pe, ppp)
    assert e.net_usd_y == pytest.approx(e.margin_before_capital_usd_y - e.capital_charge_usd_y)
    assert e.revenue_usd_y == pytest.approx(sum(e.revenue_by_product_usd_y.values()))
    at_be = sc.evaluate_cracker(o, d, e.breakeven_pe_usd_t, ppp)
    assert at_be.net_usd_y == pytest.approx(0.0, abs=1e3)
    at_bn = sc.evaluate_cracker(o, d, pe, ppp, naphtha_usd_t=e.breakeven_naphtha_usd_t)
    assert at_bn.net_usd_y == pytest.approx(0.0, abs=1e3)


def test_cracker_does_not_pay_at_september_2026_prices_on_these_assumptions():
    """The finding to report, not hide: naphtha is priced off $102 crude, PE at IOCL's list, co-products conservative."""
    o = sc.build_cracker(3.0e6)
    d = trade.RebasedTradeDeck("2025-26", pp.crude_snapshot()["brent"])
    e = sc.evaluate_cracker(o, d, pp.iocl_pe_usd_t(), pp.iocl_deck().pp_usd_t)
    assert e.margin_before_capital_usd_y < 0 and e.net_usd_y < 0
    assert e.breakeven_pe_usd_t > 1.5 * pp.iocl_pe_usd_t()
    assert e.breakeven_naphtha_usd_t < d.product_usd_t("naphtha")


def test_more_severity_and_cheaper_naphtha_help():
    d = trade.RebasedTradeDeck("2025-26", 102.47)
    pe, ppp = pp.iocl_pe_usd_t(), pp.iocl_deck().pp_usd_t
    hi = sc.evaluate_cracker(sc.build_cracker(3.0e6, 880.0), d, pe, ppp)
    lo = sc.evaluate_cracker(sc.build_cracker(3.0e6, 820.0), d, pe, ppp)
    assert hi.net_usd_y > lo.net_usd_y                                       # PE is worth more than the propylene it displaces
    cheap = sc.evaluate_cracker(sc.build_cracker(3.0e6), d, pe, ppp, naphtha_usd_t=500.0)
    dear = sc.evaluate_cracker(sc.build_cracker(3.0e6), d, pe, ppp, naphtha_usd_t=900.0)
    assert cheap.net_usd_y > dear.net_usd_y


def test_pe_price_deck():
    assert pp.iocl_pe_inr_per_mt("hdpe_raffia_010E52") == 141856 and pp.iocl_pe_inr_per_mt("lldpe_film_010F18S", "2026-01-01") == 95209
    assert pp.iocl_pe_change_pct() == pytest.approx(42.1, abs=0.1) and pp.iocl_pe_change_pct("lldpe_film_010F18S") == pytest.approx(44.6, abs=0.1)
    assert pp.iocl_pe_usd_t() == pytest.approx(141856 / 95.82)
    assert pp.iocl_pe_usd_t(realisation=0.9) == pytest.approx(0.9 * 141856 / 95.82)
    for g in pp.PE_GRADES:
        a, b, c = (pp.iocl_pe_inr_per_mt(g, d) for d in ("2026-01-01", "2026-03-01", "2026-09-11"))
        assert a < b < c
