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


def test_order_1p5_lhsv_hand_value():
    # diesel reference 1.0 wt% -> 10 ppm at LHSV 1.5, n = 1.5
    # f(a,b) = (b^-0.5 - a^-0.5)/0.5: f_ref = (316.228 - 10)/0.5 = 612.456
    # 0.5 wt% -> 50 ppm: f = (141.421 - 14.142)/0.5 = 254.558 -> LHSV = 1.5 x 612.456/254.558 = 3.6089
    assert required_lhsv(SERVICES["diesel"], 0.5, 50.0) == pytest.approx(3.60893, rel=1e-5)


def test_first_order_lhsv_hand_value():
    # naphtha: n = 1, ref ln(500/0.5) x 5 = 34.539; 0.02 wt% (200 ppm) -> 1 ppm: ln(200) = 5.2983 -> 6.51882
    assert required_lhsv(SERVICES["naphtha"], 0.02, 1.0) == pytest.approx(6.51882, rel=1e-5)


def test_hydrogen_demand_hand_values():
    # 100 t/h diesel, 850 kg/m3, 1 wt% S -> 10 ppm: S removed 1000 - 1 = 999 kg/h
    # H2 chem = 3 x 999/32.06 = 93.481 kmol/h x 2.016 = 188.458 kg/h; makeup /0.75 = 251.277 kg/h
    # q = 117.647 m3/h -> 251.277/2.016 x 22.414 / 117.647 = 23.746 Nm3/m3; V = 117.647/1.5 = 78.431 m3
    r = hydrotreat(100_000.0, 850.0, 1.0, 10.0, "diesel")
    assert r.sulfur_removed_kg_h == pytest.approx(999.0)
    assert r.h2_chemical_kg_h == pytest.approx(188.458, rel=1e-5)
    assert r.h2_makeup_kg_h == pytest.approx(251.277, rel=1e-5)
    assert r.h2_makeup_Nm3_m3 == pytest.approx(23.746, rel=1e-4)
    assert r.reactor_volume_m3 == pytest.approx(78.4314, rel=1e-5)
    assert r.h2s_kg_h == pytest.approx(999.0 * 34.08 / 32.06, rel=1e-9)
