import pytest

from refinery_design import crude_sourcing as cs
from refinery_design import petchem_prices as pp
from refinery_design import trade
from refinery_design.assay import available_crudes


def test_ppac_basket_and_import_data():
    assert cs.basket_usd_bbl("2025-26") == 70.99 and cs.basket_usd_bbl("2026-04") == 114.48
    assert cs.crude_import("2025-26")["usd_million"] == 123379 and cs.crude_import("2025-26")["mmt"] == 245.8
    assert cs.implied_rs_per_usd("2025-26") == pytest.approx(88.5, abs=0.1)
    assert cs.implied_rs_per_usd("2018-19") == pytest.approx(70.0, abs=0.1)


def test_2026_shock_is_visible_in_the_basket_and_costs_about_21_billion():
    m = [cs.basket_usd_bbl(f"2026-0{i}") for i in range(1, 7)]
    assert m[2] > 1.6 * m[1] and m[5] < m[2]                       # Feb -> Mar jump, June easing
    s = cs.shock_extra_bill_usd_bn()
    assert s["total_usd_bn"] == pytest.approx(21.2, abs=0.3)
    assert s["per_month_usd_bn"]["2026-04"] > s["per_month_usd_bn"]["2026-06"]


def test_realised_import_price_sits_below_the_basket_in_most_years():
    gaps = {y: cs.realised_vs_basket(y)["gap_usd_bbl"] for y in ("2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26")}
    assert sum(g < 0 for g in gaps.values()) == 7
    assert min(gaps, key=gaps.get) == "2023-24" and gaps["2023-24"] == pytest.approx(-4.91, abs=0.02)
    assert cs.realised_vs_basket("2023-24")["gap_usd_bn"] == pytest.approx(-8.43, abs=0.05)


def test_value_of_a_basis_point_and_the_grid():
    assert cs.value_of_one_bp_usd_m() == pytest.approx(12.34, abs=0.02)
    assert cs.value_of_one_bp_usd_m(share_switched=0.25) == pytest.approx(3.085, abs=0.01)
    g = {(r["share_switched"], r["bps_saved"]): r["usd_million_per_year"] for r in cs.local_currency_grid()}
    assert g[(0.10, 25)] == pytest.approx(0.10 * 25 * 12.34, abs=0.5)
    assert g[(0.25, 0)] == 0.0 and g[(0.25, -25)] < 0 < g[(0.25, 25)]      # the negative side exists: pass-through


def test_partner_feasibility_ranks_uae_first_and_russia_last():
    p = cs.partner_feasibility()
    assert p[0]["country"] == "UAE" and p[-1]["country"] == "Russia"
    assert cs.self_financing_ratio("UAE") > 0.5 > 0.4 > cs.self_financing_ratio("Saudi Arabia") > cs.self_financing_ratio("Iraq") > cs.self_financing_ratio("Russia")
    assert cs.rupee_recycling_gap_usd_bn("Russia") == pytest.approx(50.88, abs=0.01)


def test_rupee_settlement_has_grown_and_is_a_meaningful_scale():
    r = cs._raw()["rupee_settled"]["fy_rs_crore"]
    assert r["2023-24"] < r["2024-25"] < r["2025-26"]
    assert cs.rupee_settled_share_of_crude_bill() == pytest.approx(0.157, abs=0.01)
    assert cs._raw()["supplier_objections"]["fy2022_23_psu_rupee_settled_crude"] == 0
    assert cs._raw()["supplier_objections"]["confidence"] == "medium"


def test_urals_is_at_a_premium_in_the_live_snapshot_and_history_is_recorded():
    snap = pp.crude_snapshot()
    u = cs.urals_regime(snap["urals"], snap["brent"])
    assert u["regime"] == "premium" and u["urals_minus_brent"] == pytest.approx(3.98, abs=0.01)
    assert any(h["usd_bbl"] < 0 for h in u["history"]) and any(h["usd_bbl"] > 0 for h in u["history"])


def test_rebased_trade_deck_keeps_cracks_and_moves_crude():
    d = trade.RebasedTradeDeck("2025-26", 102.47)
    assert d.crude_usd_bbl == 102.47
    k = trade.trade_implied_cracks("2025-26")
    gasoline_bbl = d.product_usd_t("gasoline_range") * 0.158987 * 745.0 / 1000.0
    assert gasoline_bbl - 102.47 == pytest.approx(k["gasoline_crack"], abs=0.05)
    assert d.product_usd_t("lpg") / d.product_usd_t("gasoline_range") < 0.9
    assert d.crude_usd_t() == pytest.approx(102.47 / (0.158987 * 0.870), rel=1e-4)


def test_crude_relative_values_rank_light_sweet_above_heavy_at_light_favouring_prices():
    deck = trade.RebasedTradeDeck("2025-26", 100.0)
    rows = cs.crude_relative_values(deck, throughput_bpd=100_000)
    by = {r["key"]: r for r in rows}
    assert len(rows) == len(available_crudes())
    assert by["azeri_btc"]["value_vs_reference_usd_bbl"] == pytest.approx(0.0, abs=1e-9)
    assert by["bakken"]["net_realisation_usd_bbl"] > by["cold_lake_blend"]["net_realisation_usd_bbl"] + 5
    assert by["cold_lake_blend"]["fcc_flags"] >= 1      # flags are screening notes (heavy feed: hot regenerator; very clean feed: cold one)
    assert rows[0]["net_realisation_usd_bbl"] >= rows[-1]["net_realisation_usd_bbl"]


def test_russia_news_is_recorded_with_its_conflicts_and_low_confidence():
    n = cs.russia_news()
    assert n["confidence"] == "low-medium"
    v = n["volumes_mbpd"]
    assert v["2026-07"] > v["2026-08"] > v["2026-09_first_14_days"]
    assert n["august_fall_pct"] == pytest.approx(100 * (2.82 - 2.08) / 2.82, abs=0.5)
    assert n["share_of_india_crude_pct"]["2026-07"] > n["share_of_india_crude_pct"]["2026-08"] > 40
    lo, hi = cs.russia_discount_range()
    assert lo < -9 and hi > 0                      # from a >$10 discount to a first-ever premium
    reports = {r["period"]: r["usd_bbl"] for r in n["discount_to_brent_reports"]}
    assert reports["2026-07"] < -5 and reports["2026-08"] >= 0           # the two reports that conflict
    assert "NOT found" in n["payment_currency_for_russian_crude"]         # never claimed
    assert n["freight_usd_bbl"]["Novorossiysk to India west coast (Suezmax)"] - n["freight_usd_bbl"]["Baltic ports"] == 7.0


def test_august_2026_bill_and_price_arithmetic():
    b = cs.russia_news()["august_2026_import_bill"]
    assert b["usd_bn"] / b["vs_aug_2025_usd_bn"] - 1 == pytest.approx(0.182, abs=0.005)
    assert b["avg_usd_bbl"] / b["avg_usd_bbl_aug_2025"] - 1 == pytest.approx(0.305, abs=0.01)
    # The article's own numbers reconcile only to ~7% (19 MMT x 7.33 bbl/t x $90.19 = $12.6 bn vs $11.7 bn reported) - a
    # discrepancy inside the source (rounding or units), recorded rather than forced.
    assert b["volume_mmt"] * 7.33 * b["avg_usd_bbl"] / 1000 == pytest.approx(b["usd_bn"], rel=0.09)


def test_landed_advantage_sign_convention():
    assert cs.russian_landed_advantage_usd_bbl(-10.0) == 10.0
    assert cs.russian_landed_advantage_usd_bbl(-10.0, 7.0) == 3.0
    assert cs.russian_landed_advantage_usd_bbl(+4.0) == -4.0
