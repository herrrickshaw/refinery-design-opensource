"""External validation against IndianOil's Paradip refinery (see docs/VALIDATION.md)."""
import pytest

from refinery_design.benchmarks import REPORTED_NCI, paradip_nci


def test_paradip_nelson_index_lands_near_the_reported_12_2():
    assert paradip_nci("1998", 1.0, True) == pytest.approx(REPORTED_NCI, rel=0.10)
    assert paradip_nci("older", 1.0, True) == pytest.approx(REPORTED_NCI, rel=0.10)


def test_paradip_index_is_bracketed_by_reasonable_readings():
    """The published unit list is incomplete and partly ambiguous, so the honest
    result is a range: only the unambiguous units must fall well short of the
    reported value, and the full reading must sit close to it."""
    minimal = paradip_nci("1998", 0.6, False)
    full = paradip_nci("1998", 1.0, True)
    assert minimal < 0.70 * REPORTED_NCI
    assert minimal < full < REPORTED_NCI * 1.05
    assert paradip_nci("older", 1.0, True) > full     # older, higher coking factor


def test_one_blend_parameter_reproduces_both_paradip_unit_loadings():
    """Fit the coker/CDU ratio (27.3%) with a single blend fraction; the FCC/CDU
    ratio (28.0%) is then an independent prediction from the assays."""
    from refinery_design.benchmarks import paradip_blend_fit
    f = paradip_blend_fit()
    assert f["vr_wt_frac"] == pytest.approx(f["coker_to_cdu"], abs=1e-6)     # the fitted quantity
    assert f["vgo_wt_frac"] == pytest.approx(f["fcc_to_cdu"], abs=0.02)      # the prediction, +-2 points
    assert 0.2 < f["heavy_fraction_vol"] < 0.7
    assert 24.0 < f["api"] < 31.0 and f["sulfur_wt"] > 2.0    # a medium-heavy, high-sulfur basket
