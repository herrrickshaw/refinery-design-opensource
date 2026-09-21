"""External validation against IndianOil's Paradip refinery (see docs/VALIDATION.md).

Reference values: CHT (MoPNG) NCI 10.6 (OGJ 2025 survey); PPAC distillate yield
79.2-80.8% (Ready Reckoner Table 4.8); OGJ unit capacities.
"""
import pytest

from refinery_design.benchmarks import (
    IOC_COMMISSIONING_NCI, PARADIP_PPAC_DISTILLATE_PCT, REPORTED_NCI, paradip_model_refinery, paradip_nci,
)


def test_reference_is_the_chi_survey_value_not_the_commissioning_claim():
    assert REPORTED_NCI == 10.6 and IOC_COMMISSIONING_NCI == 12.2


def test_paradip_nci_full_readings_bracket_the_cht_value():
    """The published unit list is partial and partly ambiguous; counting every listed unit
    gives a range that must straddle CHT's 10.6."""
    readings = [paradip_nci(f, v, True) for f in ("1998", "older") for v in (0.6, 1.0)]
    assert min(readings) <= REPORTED_NCI <= max(readings)
    for r in readings:
        assert r == pytest.approx(REPORTED_NCI, rel=0.13)


def test_only_the_unambiguous_units_fall_well_short():
    assert paradip_nci("1998", 0.6, False) < 0.75 * REPORTED_NCI
    assert paradip_nci("1998", 0.6, False) < paradip_nci("1998", 1.0, True)
    assert paradip_nci("older", 1.0, True) > paradip_nci("1998", 1.0, True)


def test_one_blend_parameter_reproduces_both_paradip_unit_loadings():
    """Fit the coker/CDU ratio (27.3%) with a single blend fraction; the FCC/CDU
    ratio (28.0%) is then an independent prediction from the assays."""
    from refinery_design.benchmarks import paradip_blend_fit
    f = paradip_blend_fit()
    assert f["vr_wt_frac"] == pytest.approx(f["coker_to_cdu"], abs=1e-6)     # the fitted quantity
    assert f["vgo_wt_frac"] == pytest.approx(f["fcc_to_cdu"], abs=0.02)      # the prediction, +-2 points
    assert 0.2 < f["heavy_fraction_vol"] < 0.7
    assert 24.0 < f["api"] < 31.0 and f["sulfur_wt"] > 2.0    # a medium-heavy, high-sulfur basket


def test_modelled_light_product_yield_matches_ppacs_paradip_distillate_yield():
    """PPAC reports 79.2-80.8% 'distillate' for Paradip (definition not stated); the flowsheet's
    LPG + gasoline-range + middle-distillate yield on the fitted basket must land inside +-2 points."""
    lo, hi = min(PARADIP_PPAC_DISTILLATE_PCT.values()), max(PARADIP_PPAC_DISTILLATE_PCT.values())
    for ht in (False, True):
        y = paradip_model_refinery(ht).light_product_yield_wt_pct
        assert lo - 2.0 <= y <= hi + 2.0
