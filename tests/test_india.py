import pytest

from refinery_design import india


def test_cht_table_integrity_matches_the_published_totals():
    rows = india.refineries()
    assert len(rows) == 19
    cap = {}
    for r in rows:
        cap[r["company"]] = cap.get(r["company"], 0.0) + r["capacity_mmtpa"]
    assert cap["IOCL"] + cap["CPCL"] == pytest.approx(80.75, abs=1e-6)   # "Total IOCL Group"
    assert cap["HPCL"] == pytest.approx(24.5) and cap["BPCL"] == pytest.approx(35.3)
    assert sum(cap.values()) == pytest.approx(158.6, abs=0.05)           # "Total PSU"


def test_paradip_and_jamnagar_style_lookups():
    assert india.nci("Paradip") == 10.6 and india.nci("Panipat") == 10.5
    with pytest.raises(KeyError):
        india.nci("Nagapattinam")     # under approval - no NCI published


def test_company_nci_is_capacity_weighted():
    w = india.company_nci()
    assert w["MRPL"] == pytest.approx(9.46) and w["CPCL"] == pytest.approx(10.8)
    assert 9.0 < w["IOCL"] < 10.0 and w["BPCL"] > w["IOCL"]


def test_ppac_grm_lookups_and_gaps():
    assert india.grm_usd_bbl("IOCL", "2022-23") == 19.52
    assert india.grm_usd_bbl("CPCL", "2019-20") == -1.18       # a negative-margin year
    assert india.grm_usd_bbl("RIL", "2021-22") is None
    assert india.distillate_yield_pct("Paradip", "2019-20") == 80.7
    assert india.distillate_yield_pct("Bina", "2020-21") is None


def test_fuel_and_loss_reference_values():
    assert india.paradip_fuel_loss_pct("2022-23") == 10.0
    assert india.psu_fuel_loss_pct() == pytest.approx(8.93, abs=0.05)


def test_indian_basket_formula_per_ppac_note():
    # 75.62% x mean(Oman, Dubai) + 24.38% Brent Dated
    assert india.indian_basket_usd_bbl(90.0, 94.0, 100.0) == pytest.approx(0.7562 * 92.0 + 0.2438 * 100.0)
    assert india.indian_basket_usd_bbl(80.0, 80.0, 80.0) == pytest.approx(80.0)


def test_grm_vs_complexity_is_positive_but_weak_in_the_psu_data():
    """PPAC GRM vs CHT NCI across five companies: the sign agrees with 'complexity earns margin',
    the strength does not support strong claims (n = 5, |r| well below 0.6)."""
    for yr in (None, "2021-22", "2022-23"):
        f = india.grm_nci_fit(yr)
        assert f["n"] == 5 and f["slope_usd_bbl_per_nci"] > 0
        assert abs(f["r"]) < 0.6
