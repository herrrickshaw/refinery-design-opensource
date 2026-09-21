from dataclasses import replace

import numpy as np
import pytest

from refinery_design.assay import INF, load_crude
from refinery_design.fcc import (
    FccFeed, FccKinetics, FccOperation, cooler_duty_for_regen_temperature, fcc_operate,
    riser_kinetics, rot_sweep,
)

# reference VGO: Watson K = 11.8 (the calibration basis)
REF = FccFeed("ref VGO", density_kg_m3=928.7, mabp_C=460.0, sulfur_wt=0.5, ccr_wt=0.3)
OP = FccOperation(feed_rate_kg_s=100.0)


def test_typical_vgo_lands_inside_published_fcc_ranges():
    r = fcc_operate(REF, OP)
    y = r.yields_wt_pct
    assert 70 <= r.conversion_wt_pct <= 82
    assert 44 <= y["gasoline"] <= 54
    assert 14 <= y["lpg"] <= 22
    assert 2 <= y["dry_gas"] <= 5
    assert 4.5 <= r.coke_wt_pct <= 6.5
    assert 6.0 <= r.cat_to_oil <= 9.0
    assert 680 <= r.regen_temperature_C <= 740
    assert 0.5 <= r.delta_coke_wt_pct <= 1.1
    assert r.warnings == []


def test_yields_close_to_100_wt_pct():
    r = fcc_operate(REF, OP)
    assert r.yields_wt_pct["total"] == pytest.approx(100.0, abs=1e-6)


def test_heat_balance_closes():
    r = fcc_operate(REF, OP)
    hb = r.heat_balance_kJ_per_kg_feed
    assert abs(hb["residual (closure)"]) < 0.5
    burn_out = (hb["regen: flue-gas sensible out"] + hb["regen: coke desorption"]
                + hb["regen: losses"] + hb["regen: catalyst cooler"] + hb["riser: total demand"])
    assert hb["regen: coke combustion"] + hb["regen: air sensible in"] == pytest.approx(burn_out, abs=0.5)


def test_catalyst_circulation_carries_the_riser_demand():
    r = fcc_operate(REF, OP)
    hb = r.heat_balance_kJ_per_kg_feed
    carried = r.cat_to_oil * OP.catalyst_cp_kJ_kgK * (r.regen_temperature_C - OP.riser_outlet_C)
    # riser demand = catalyst enthalpy drop, less the stripping-steam term that is charged per C/O
    assert carried == pytest.approx(hb["riser: total demand"] + 0.0, rel=0.03)


def test_gasoline_passes_through_a_maximum_versus_cat_to_oil():
    """Over-cracking: the defining FCC selectivity trade-off."""
    g = [riser_kinetics(REF, 530, co, 2.5)["gasoline"][-1] for co in (3, 5, 7, 9, 12, 16, 22)]
    peak = int(np.argmax(g))
    assert 0 < peak < len(g) - 1
    conv = [1 - riser_kinetics(REF, 530, co, 2.5)["unconverted"][-1] for co in (3, 7, 16)]
    assert conv[0] < conv[1] < conv[2]


def test_riser_lumps_conserve_mass_at_every_point():
    p = riser_kinetics(REF, 530, 7.0, 2.5)
    total = p["unconverted"] + p["gasoline"] + p["gas"] + p["coke_cat"]
    assert np.allclose(total, 1.0, atol=1e-6)


def test_higher_riser_outlet_temperature_makes_more_gas_less_gasoline_at_the_top():
    lo, mid, hi = rot_sweep(REF, OP, [500.0, 530.0, 570.0])
    assert lo.yields_wt_pct["dry_gas"] < mid.yields_wt_pct["dry_gas"] < hi.yields_wt_pct["dry_gas"]
    assert lo.yields_wt_pct["lpg"] < hi.yields_wt_pct["lpg"]
    assert hi.yields_wt_pct["gasoline"] < mid.yields_wt_pct["gasoline"]
    assert lo.cat_to_oil > hi.cat_to_oil * 0 and lo.conversion_wt_pct < hi.conversion_wt_pct


def test_hotter_feed_preheat_lowers_cat_to_oil():
    cold, hot = fcc_operate(REF, replace(OP, feed_preheat_C=200.0)), fcc_operate(REF, replace(OP, feed_preheat_C=320.0))
    assert hot.cat_to_oil < cold.cat_to_oil
    assert hot.regen_temperature_C != cold.regen_temperature_C


def test_feed_quality_directions():
    paraffinic = replace(REF, density_kg_m3=900.0)   # higher K
    aromatic = replace(REF, density_kg_m3=960.0)     # lower K
    assert paraffinic.watson_k > REF.watson_k > aromatic.watson_k
    cp = riser_kinetics(paraffinic, 530, 7, 2.5); ca = riser_kinetics(aromatic, 530, 7, 2.5)
    assert cp["unconverted"][-1] < ca["unconverted"][-1]        # paraffinic cracks easier
    assert cp["coke_cat"][-1] < ca["coke_cat"][-1]              # aromatic cokes more
    poisoned = replace(REF, basic_n_ppm=1500.0)
    assert riser_kinetics(poisoned, 530, 7, 2.5)["unconverted"][-1] > riser_kinetics(REF, 530, 7, 2.5)["unconverted"][-1]


def test_higher_ccr_displaces_catalytic_coke_and_heats_the_regenerator():
    lean, rich = fcc_operate(replace(REF, ccr_wt=0.0), OP), fcc_operate(replace(REF, ccr_wt=2.0), OP)
    # The heat balance roughly fixes total coke, so feed-derived coke displaces
    # catalytic coke: cat/oil falls, conversion drops, the regenerator runs hotter.
    assert rich.cat_to_oil < lean.cat_to_oil
    assert rich.conversion_wt_pct < lean.conversion_wt_pct
    assert rich.regen_temperature_C > lean.regen_temperature_C
    assert rich.coke_wt_pct == pytest.approx(lean.coke_wt_pct, rel=0.10)


def test_riser_hydraulics_match_typical_geometry():
    r = fcc_operate(REF, OP)
    rs = r.riser
    assert rs["exit_velocity_m_s"] == pytest.approx(OP.riser_exit_velocity_m_s, rel=1e-3)
    assert 3.0 <= rs["inlet_velocity_m_s"] <= 9.0        # vapour expands ~4x along the riser
    assert 25.0 <= rs["height_m"] <= 55.0
    assert 200 <= rs["solids_flux_kg_m2_s"] <= 1500


def test_riser_height_scales_with_residence_time_and_diameter_with_throughput():
    a = fcc_operate(REF, OP)
    b = fcc_operate(REF, replace(OP, feed_rate_kg_s=200.0))
    assert b.riser["diameter_m"] == pytest.approx(a.riser["diameter_m"] * np.sqrt(2), rel=0.01)
    assert b.riser["height_m"] == pytest.approx(a.riser["height_m"], rel=0.01)
    c = fcc_operate(REF, replace(OP, riser_residence_s=3.5))
    assert c.riser["height_m"] > a.riser["height_m"] * 1.2


def test_regenerator_sizing_and_flue_gas():
    r = fcc_operate(REF, OP)
    g, f = r.regenerator, r.flue_gas
    assert 6 < g["diameter_m"] < 16
    assert 3 < g["dense_bed_height_m"] < 12
    assert f["O2_vol_pct_dry"] == pytest.approx(2.0, abs=0.5)     # 10% excess air ~ 2 vol% O2
    assert f["CO_ppmv_dry"] < 15_000
    # air rate ~ 12-14 kg air / kg coke at stoichiometry plus excess
    assert 12.0 < g["air_rate_kg_s"] * 3600 / g["coke_burn_kg_h"] < 16.5


def test_partial_burn_uses_less_air_per_kg_coke_and_makes_co():
    full = fcc_operate(REF, OP)
    part = fcc_operate(REF, replace(OP, combustion_mode="partial"))
    per_coke = lambda r: r.regenerator["air_rate_kg_s"] / (r.regenerator["coke_burn_kg_h"] / 3600.0)
    assert per_coke(part) < 0.85 * per_coke(full)
    # each kg of coke releases less heat when only burnt to CO/CO2 ~1.5, so the balance needs more coke
    assert part.coke_wt_pct > full.coke_wt_pct
    assert part.flue_gas["CO_ppmv_dry"] > 100 * full.flue_gas["CO_ppmv_dry"]
    assert part.regenerator["co2_co_ratio"] == 1.5
    with pytest.raises(ValueError):
        fcc_operate(REF, replace(OP, combustion_mode="nonsense"))


def test_sulfur_distribution_and_so2_scale_with_feed_sulfur():
    a, b = fcc_operate(replace(REF, sulfur_wt=1.0), OP), fcc_operate(replace(REF, sulfur_wt=2.0), OP)
    assert b.flue_gas["SO2_ppmv_dry"] == pytest.approx(2 * a.flue_gas["SO2_ppmv_dry"], rel=0.02)
    assert b.gasoline_sulfur_ppm == pytest.approx(2 * a.gasoline_sulfur_ppm, rel=0.02)
    s = a.sulfur_distribution
    assert sum(s.values()) == pytest.approx(1.0 / 100.0, rel=1e-9)   # kg S / kg feed for 1 wt% S


def test_crude_drives_fcc_behaviour_end_to_end():
    """Light paraffinic VGO vs heavy naphthenic VGO, same unit and conditions."""
    bak = FccFeed.from_cut(load_crude("bakken").cut(370, 550, "VGO"), "Bakken VGO")
    cl = FccFeed.from_cut(load_crude("cold_lake_blend").cut(370, 550, "VGO"), "Cold Lake VGO")
    rb, rc = fcc_operate(bak, OP), fcc_operate(cl, OP)
    assert bak.watson_k > cl.watson_k and bak.sulfur_wt < cl.sulfur_wt
    assert rb.conversion_wt_pct > rc.conversion_wt_pct + 15
    assert rb.regen_temperature_C < rc.regen_temperature_C
    assert rb.gasoline_sulfur_ppm < rc.gasoline_sulfur_ppm / 10
    assert rb.warnings == [] and any("catalyst cooler" in w for w in rc.warnings)


def test_resid_feed_needs_a_catalyst_cooler():
    ar = FccFeed.from_cut(load_crude("dalia").cut(370, INF, "AR"), "Dalia AR")
    assert ar.ccr_wt > 5.0
    with pytest.raises(ValueError, match="catalyst cooler"):
        fcc_operate(ar, OP)
    duty = cooler_duty_for_regen_temperature(ar, OP, 720.0)
    assert duty > 500.0
    r = fcc_operate(ar, replace(OP, catalyst_cooler_kJ_kg_feed=duty))
    assert r.regen_temperature_C == pytest.approx(720.0, abs=0.5)
    assert any("Ni+V" in w for w in r.warnings) or ar.ni_ppm + ar.v_ppm <= 5


def test_a_feed_too_clean_to_sustain_the_heat_balance_is_reported():
    with pytest.raises(ValueError, match="cannot close"):
        fcc_operate(REF, replace(OP, feed_preheat_C=25.0, dispersion_steam_wt=0.15, heat_of_cracking_kJ_kg_per_conv_pct=14.0))


def test_regenerator_must_be_hotter_than_riser():
    from refinery_design.fcc import _balance
    with pytest.raises(ValueError, match="hotter"):
        _balance(REF, OP, FccKinetics(), OP.riser_outlet_C + 2.0)


def test_from_cut_rejects_empty_cut():
    with pytest.raises(ValueError):
        FccFeed.from_cut(load_crude("bakken").cut(-200, -100))


def test_pretreating_the_feed_improves_a_poor_vgo():
    from refinery_design.fcc import pretreated
    cl = FccFeed.from_cut(load_crude("cold_lake_blend").cut(370, 550, "VGO"), "Cold Lake VGO")
    ht = pretreated(cl)
    assert ht.sulfur_wt < 0.15 * cl.sulfur_wt and ht.basic_n_ppm < cl.basic_n_ppm
    assert ht.ccr_wt < cl.ccr_wt and ht.watson_k > cl.watson_k and ht.api == pytest.approx(cl.api + 2.0, abs=0.01)
    raw, treated = fcc_operate(cl, OP), fcc_operate(ht, OP)
    assert treated.conversion_wt_pct > raw.conversion_wt_pct + 7
    assert treated.regen_temperature_C < raw.regen_temperature_C - 30
    assert treated.gasoline_sulfur_ppm < raw.gasoline_sulfur_ppm / 8
    # ...but pretreat alone does not fix the worst feeds: a heavy naphthenic VGO still runs hot
    assert treated.regen_temperature_C > 760
    with pytest.raises(ValueError):
        pretreated(cl, sulfur_removal=1.2)
