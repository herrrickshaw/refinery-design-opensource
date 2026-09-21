import pytest

from refinery_design.assay import Slate, available_crudes, load_crude
from refinery_design.distillation import distill

ALL = available_crudes()


@pytest.mark.parametrize("key", ALL)
def test_material_balance_closes(key):
    r = distill(load_crude(key), 200_000)
    assert r.mass_closure == pytest.approx(1.0, abs=1e-9)
    assert sum(s.flow_bpd for s in r.streams.values()) == pytest.approx(200_000, rel=1e-9)


@pytest.mark.parametrize("key", ALL)
def test_sulfur_balance_closes_to_a_few_percent(key):
    """Sulfur in the six cuts vs sulfur in the crude - independent check that
    the cut-property weighting is consistent with the whole-crude assay."""
    c = load_crude(key)
    r = distill(c, 200_000)
    s_out = sum(s.sulfur_kg_h for s in r.streams.values())
    s_in = r.feed_kg_h * c.sulfur_wt / 100.0
    assert s_out == pytest.approx(s_in, rel=0.01)


def test_crude_type_drives_the_slate():
    light = distill(load_crude("bakken"), 100_000)
    heavy = distill(load_crude("cold_lake_blend"), 100_000)
    assert light.stream("naphtha").wt_frac > 2 * heavy.stream("naphtha").wt_frac
    assert heavy.stream("vacuum_residue").wt_frac > 4 * light.stream("vacuum_residue").wt_frac
    assert heavy.stream("vacuum_residue").cut.sulfur_wt > 3.0


def test_raising_the_naphtha_end_point_moves_material_out_of_kerosene():
    c = load_crude("qua_iboe")
    a, b = distill(c, 1e5, naphtha_end_C=140), distill(c, 1e5, naphtha_end_C=180)
    assert b.stream("naphtha").wt_frac > a.stream("naphtha").wt_frac
    assert b.stream("kerosene").wt_frac < a.stream("kerosene").wt_frac
    assert b.mass_closure == pytest.approx(1.0)


def test_cut_points_must_increase():
    with pytest.raises(ValueError, match="increase"):
        distill(load_crude("bakken"), 1e5, naphtha_end_C=260)
    with pytest.raises(ValueError):
        distill(load_crude("bakken"), 1e5, vgo_end_C=300)


@pytest.mark.parametrize("key", ALL)
def test_furnace_duty_is_in_a_plausible_band_and_scales_linearly(key):
    a, b = distill(load_crude(key), 100_000), distill(load_crude(key), 200_000)
    assert 40 < a.furnace_duty_MW < 130          # ~100 kbpd crude heater
    assert b.furnace_duty_MW == pytest.approx(2 * a.furnace_duty_MW, rel=1e-9)


def test_lighter_crude_needs_more_vaporisation():
    assert distill(load_crude("bakken"), 1e5).vaporised_wt_frac > distill(load_crude("kearl"), 1e5).vaporised_wt_frac


def test_hotter_coil_outlet_needs_more_duty_and_bad_input_raises():
    c = load_crude("upper_zakum")
    assert distill(c, 1e5, coil_outlet_C=370).furnace_duty_MW > distill(c, 1e5, coil_outlet_C=350).furnace_duty_MW
    with pytest.raises(ValueError):
        distill(c, 1e5, preheat_C=400, coil_outlet_C=360)


def test_slate_feed_is_supported():
    s = Slate([(load_crude("bakken"), 0.5), (load_crude("cold_lake_blend"), 0.5)])
    r = distill(s, 150_000)
    assert r.mass_closure == pytest.approx(1.0)
    assert "Bakken" in r.feed_name and "Cold Lake" in r.feed_name
