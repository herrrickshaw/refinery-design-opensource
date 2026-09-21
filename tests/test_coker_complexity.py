import pytest

from refinery_design.coker import delayed_coker
from refinery_design.complexity import NELSON_FACTORS, nelson_complexity


def test_gary_handwerk_yields():
    r = delayed_coker(100_000.0, ccr_wt=20.0)
    y = r.yields_wt_pct
    assert y["coke"] == pytest.approx(32.0)
    assert y["gas"] == pytest.approx(7.8 + 0.144 * 20.0)
    assert sum(y.values()) == pytest.approx(100.0)
    assert y["naphtha"] < y["gas_oil"]


def test_more_carbon_residue_means_more_coke_and_less_liquid():
    lo, hi = delayed_coker(1e5, 10.0), delayed_coker(1e5, 25.0)
    assert hi.coke_kg_h > lo.coke_kg_h
    assert hi.naphtha_kg_h + hi.gas_oil_kg_h < lo.naphtha_kg_h + lo.gas_oil_kg_h


def test_out_of_range_ccr_rejected_and_drum_scales_with_coke():
    with pytest.raises(ValueError):
        delayed_coker(1e5, 60.0)
    a, b = delayed_coker(1e5, 15.0), delayed_coker(2e5, 15.0)
    assert b.drum_volume_m3 == pytest.approx(2 * a.drum_volume_m3)
    assert a.drum_volume_m3 == pytest.approx(a.coke_kg_h * 18 / (800 * 0.75))


def test_nelson_simple_refinery_by_hand():
    # 100 kbpd CDU + 50 kbpd vacuum + 30 kbpd FCC + 20 kbpd coker (1998 factors)
    nci = nelson_complexity(100.0, {"vacuum": 50.0, "fcc": 30.0, "thermal": 20.0})
    assert nci == pytest.approx(1.0 + 2.0 * 0.5 + 6.0 * 0.3 + 2.75 * 0.2)
    old = nelson_complexity(100.0, {"thermal": 20.0}, factors="older")
    assert old == pytest.approx(1.0 + 5.0 * 0.2)


def test_nelson_unknown_unit_raises_and_hydroskimmer_is_one():
    with pytest.raises(KeyError, match="unknown unit"):
        nelson_complexity(100.0, {"warp_drive": 10.0})
    assert nelson_complexity(100.0, {}) == 1.0
    assert set(NELSON_FACTORS["1998"]) == set(NELSON_FACTORS["older"])
