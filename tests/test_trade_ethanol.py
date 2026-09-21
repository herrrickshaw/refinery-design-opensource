import pytest

from refinery_design import ethanol, india, trade
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.grm import gross_refining_margin


# ---- PPAC data integrity ------------------------------------------------------------------------
def test_parsed_trade_totals_agree_with_ppacs_printed_totals():
    printed_imp = [43.2, 39.0, 44.6, 48.7, 50.9, 46.2]
    printed_exp = [56.8, 62.8, 61.0, 62.6, 65.1, 61.4]
    for i, y in enumerate(trade.years()):
        imp = sum(trade.trade_qty_mmt("imports", k, y) for k in trade._raw()["trade_usd_bn_and_mmt"]["imports"] if k != "crude")
        exp = sum(trade.trade_qty_mmt("exports", k, y) for k in trade._raw()["trade_usd_bn_and_mmt"]["exports"])
        assert imp == pytest.approx(printed_imp[i], abs=0.4) and exp == pytest.approx(printed_exp[i], abs=0.4)


def test_key_ppac_values():
    assert trade.trade_qty_mmt("exports", "petrol", "2025-26") == 16.7 and trade.trade_qty_mmt("imports", "lpg", "2025-26") == 21.3
    assert trade.consumption_mmt("ms", "2025-26") == 42.6 and trade.production_mmt("ms", "2025-26") == 49.8
    assert trade.import_dependence_pct("lpg", "2025-26") == pytest.approx(64.2, abs=0.2)
    assert trade.net_export_mmt("naphtha", "2022-23") == pytest.approx(4.8, abs=0.05)         # a net naphtha exporter


def test_unit_values_and_the_small_flow_guard():
    assert trade.unit_value_usd_t("exports", "diesel", "2022-23") == pytest.approx(1014, abs=3)
    with pytest.raises(ValueError, match="too small"):
        trade.unit_value_usd_t("imports", "petrol", "2025-26")


# ---- petrol exports rose while domestic blend rose --------------------------------------------
def test_petrol_exports_grew_as_ethanol_displaced_domestic_petrol():
    ex = [trade.trade_qty_mmt("exports", "petrol", y) for y in ("2022-23", "2023-24", "2024-25", "2025-26")]
    assert ex == sorted(ex) and ex[-1] - ex[0] > 3.0
    assert trade.production_mmt("ms", "2025-26") - trade.production_mmt("ms", "2022-23") > 6.0


def test_ppac_balance_gap_is_the_ethanol_blended():
    """Consumption (blended) minus production + imports - exports should be about the ethanol at PPAC's blend."""
    for y, blend in (("2022-23", 0.1158), ("2025-26", 0.1999)):
        b = trade.petrol_balance(y)
        expected = b["consumption"] * ethanol.ethanol_mass_share(blend)
        assert b["implied_ethanol_mmt"] == pytest.approx(expected, abs=1.0), y
    assert trade.petrol_balance("2022-23")["implied_ethanol_share_pct"] < trade.petrol_balance("2025-26")["implied_ethanol_share_pct"]


# ---- ethanol maths ------------------------------------------------------------------------------
def test_ethanol_mass_share_and_displacement():
    assert ethanol.ethanol_mass_share(0.0) == 0.0
    assert ethanol.ethanol_mass_share(0.20) == pytest.approx(0.2093, abs=1e-3)
    assert ethanol.ethanol_mass_share(0.12) == pytest.approx(0.126, abs=1e-3)
    assert ethanol.refinery_petrol_mmt(42.6, 0.20) == pytest.approx(33.68, abs=0.02)
    assert ethanol.petrol_displaced_mmt(42.6, 0.20) == pytest.approx(8.92, abs=0.02)
    assert ethanol.blend_step_freed_mmt(42.6, 0.12, 0.20) == pytest.approx(3.54, abs=0.02)
    with pytest.raises(ValueError):
        ethanol.ethanol_mass_share(1.0)


def test_tender_arithmetic_matches_reported_numbers():
    # 60.6 bn litres at 20% = 1,212 crore litres (the ESY 2026-27 expected demand)
    assert ethanol.ethanol_crore_litres(60.6, 0.20) == pytest.approx(1212.0)
    t = ethanol.tender()["esy_2025_26_cycle1"]
    assert t["offers_crore_litres"] == pytest.approx(t["sugarcane_offers"] + t["grain_offers"], abs=0.01)
    assert t["offers_crore_litres"] / t["requirement_crore_litres"] == pytest.approx(1.69, abs=0.01)
    assert ethanol.tender()["esy_2026_27_expected"]["confidence"] == "low"


def test_scenarios_are_monotonic():
    s = ethanol.ms_scenarios(42.6)
    assert [r["refinery_petrol_mmt"] for r in s] == sorted([r["refinery_petrol_mmt"] for r in s], reverse=True)
    assert s[0]["displaced_mmt"] == 0.0


# ---- observed-price deck: independent check on the GRM layer ------------------------------------
def test_trade_implied_cracks_agree_with_the_grm_calibrated_cracks():
    """Cracks calibrated from reported IOCL GRMs (docs/VALIDATION.md s6) vs cracks implied by observed trade prices."""
    fy2223, fy2122 = trade.trade_implied_cracks("2022-23"), trade.trade_implied_cracks("2021-22")
    assert fy2223["diesel_crack"] == pytest.approx(43.4, abs=2.0)         # calibrated: 43.4
    assert fy2223["gasoline_crack"] == pytest.approx(26.0, abs=4.0)       # calibrated: 26.0
    assert fy2122["gasoline_crack"] == pytest.approx(17.4, abs=2.0)       # calibrated: 17.4
    assert abs(fy2122["diesel_crack"] - 29.0) > 10                        # the year they DISAGREE (documented)
    for y in trade.years()[1:]:
        c = trade.trade_implied_cracks(y)
        assert 0.55 < c["lpg_frac_of_crude"] < 0.85 and 0.75 < c["fuel_oil_frac_of_crude"] < 1.0


def test_flowsheet_at_observed_prices_reproduces_reported_grm_without_calibration():
    r = paradip_model_refinery(True)
    grm = {y: gross_refining_margin(r, trade.TradeDeck(y)).grm_usd_bbl for y in ("2022-23", "2023-24", "2025-26")}
    lo = {"2022-23": 12.09, "2023-24": 9.08, "2025-26": 8.79}     # lowest of IOCL/BPCL/HPCL/CPCL reported GRM
    hi = {"2022-23": 20.24, "2023-24": 14.14, "2025-26": 11.74}
    for y in grm:
        assert lo[y] - 2.0 <= grm[y] <= hi[y] + 2.0, (y, grm[y])
    assert grm["2022-23"] == pytest.approx(19.52, abs=1.5)                # IOCL FY22-23
    # the year it misses is reported, not hidden: FY2024-25 comes out low
    low = gross_refining_margin(r, trade.TradeDeck("2024-25")).grm_usd_bbl
    assert low < 4.8 - 2.0


# ---- NRL --------------------------------------------------------------------------------------------
def test_nrl_is_flagged_non_comparable_and_excluded_from_the_fit():
    assert "NRL" in india.NON_COMPARABLE and "excise" in india.NRL_CAVEAT and "domestic" in india.NRL_CAVEAT
    others = [india.grm_usd_bbl(c, "2022-23") for c in ("IOCL", "BPCL", "HPCL", "CPCL", "MRPL")]
    assert india.grm_usd_bbl("NRL", "2022-23") > 1.7 * max(others)
    assert india.grm_usd_bbl("NRL", "2025-26") == 29.20
    assert india.grm_nci_fit()["n"] == 5                       # NRL not among the default companies
