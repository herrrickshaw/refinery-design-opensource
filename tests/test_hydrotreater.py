import pytest

from refinery_design.hydrotreater import SERVICES, hydrotreat, required_lhsv


@pytest.mark.parametrize("svc", list(SERVICES))
def test_reference_operating_point_is_recovered(svc):
    s = SERVICES[svc]
    assert required_lhsv(s, s.ref_s_in_wt, s.ref_s_out_ppm) == pytest.approx(s.ref_lhsv)


def test_deeper_desulfurisation_needs_more_catalyst():
    d = SERVICES["diesel"]
    assert required_lhsv(d, 1.0, 10.0) < required_lhsv(d, 1.0, 50.0) < required_lhsv(d, 1.0, 500.0)
    assert required_lhsv(d, 2.0, 10.0) < required_lhsv(d, 0.5, 10.0)  # more sulfur in -> lower LHSV


def test_product_sulfur_must_be_below_feed():
    with pytest.raises(ValueError):
        required_lhsv(SERVICES["diesel"], 0.001, 100.0)


def test_hydrogen_stoichiometry():
    r = hydrotreat(100_000.0, 850.0, sulfur_wt_in=1.0, product_sulfur_ppm=10.0, service="diesel", h2_loss_frac=0.0)
    s_removed = 100_000 * (0.01 - 10e-6)
    assert r.sulfur_removed_kg_h == pytest.approx(s_removed)
    assert r.h2_chemical_kg_h == pytest.approx(3.0 * s_removed / 32.06 * 2.016)
    assert r.h2s_kg_h == pytest.approx(s_removed / 32.06 * 34.08)
    assert r.h2_makeup_kg_h == pytest.approx(r.h2_chemical_kg_h)


def test_makeup_includes_losses_and_nitrogen():
    a = hydrotreat(1e5, 850.0, 1.0, 10.0, h2_loss_frac=0.0)
    b = hydrotreat(1e5, 850.0, 1.0, 10.0, h2_loss_frac=0.25, nitrogen_ppm_in=500.0)
    assert b.h2_makeup_kg_h > a.h2_makeup_kg_h * 1.33
    # 1 wt% S in diesel: 0.265 kmol S/m3 x 3 mol H2/mol S = 17.8 Nm3/m3 (~100 scf/bbl)
    assert a.h2_makeup_Nm3_m3 == pytest.approx(17.8, rel=0.02)


def test_reactor_volume_is_flow_over_lhsv():
    r = hydrotreat(85_000.0, 850.0, 1.0, 10.0)
    assert r.reactor_volume_m3 == pytest.approx((85_000 / 850.0) / r.lhsv_1_h)
    assert r.catalyst_t == pytest.approx(r.reactor_volume_m3 * 0.7)
    assert r.feed_bpd == pytest.approx(85_000 / 850.0 * 24 / 0.158987, rel=1e-4)


def test_custom_service_and_extra_saturation_hydrogen():
    from refinery_design.hydrotreater import HydrotreaterService
    svc = HydrotreaterService("custom", 0.5, 50.0, 2.0, 1.5)
    base = hydrotreat(1e5, 850.0, 0.5, 50.0, service=svc)
    more = hydrotreat(1e5, 850.0, 0.5, 50.0, service=svc, extra_h2_Nm3_m3=20.0)
    assert more.h2_chemical_kg_h > base.h2_chemical_kg_h
