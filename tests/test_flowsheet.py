import pytest

from refinery_design.assay import Slate, available_crudes, load_crude
from refinery_design.flowsheet import RefineryConfig, refine

ALL = available_crudes()


@pytest.mark.parametrize("key", [k for k in ALL if k != "cold_lake_blend"])
def test_whole_refinery_mass_balance_closes(key):
    r = refine(load_crude(key), 200_000)
    assert r.mass_closure == pytest.approx(1.0, abs=1e-9)


def test_heavy_crude_gives_less_light_product_and_more_coke():
    light, heavy = refine(load_crude("bakken"), 200_000), refine(load_crude("kearl"), 200_000)
    assert heavy.mass_closure == pytest.approx(1.0, abs=1e-9)
    assert light.light_product_yield_wt_pct > heavy.light_product_yield_wt_pct + 15
    assert heavy.pools_wt_pct()["petcoke"] > 10 * light.pools_wt_pct()["petcoke"]


def test_removing_the_coker_leaves_vacuum_residue():
    cfg = RefineryConfig(coker=False)
    r = refine(load_crude("upper_zakum"), 200_000, cfg)
    assert r.mass_closure == pytest.approx(1.0, abs=1e-9)
    assert r.pools_wt_pct()["vacuum_residue"] > 15
    assert r.black_oil_yield_wt_pct > refine(load_crude("upper_zakum"), 200_000).black_oil_yield_wt_pct * 4


def test_removing_the_fcc_lowers_light_products():
    a = refine(load_crude("dalia"), 200_000)
    b = refine(load_crude("dalia"), 200_000, RefineryConfig(fcc=False))
    assert b.mass_closure == pytest.approx(1.0, abs=1e-9)
    assert b.fcc is None
    assert a.pools_wt_pct()["gasoline_range"] > b.pools_wt_pct()["gasoline_range"]


def test_complexity_rises_with_conversion_units():
    full = refine(load_crude("dalia"), 200_000).complexity()
    no_coker = refine(load_crude("dalia"), 200_000, RefineryConfig(coker=False)).complexity()
    skimming = refine(load_crude("dalia"), 200_000, RefineryConfig(fcc=False, coker=False)).complexity()
    assert full > no_coker > skimming > 1.0


def test_slate_runs_through_the_flowsheet():
    s = Slate([(load_crude("bakken"), 0.6), (load_crude("upper_zakum"), 0.4)])
    r = refine(s, 250_000)
    assert r.mass_closure == pytest.approx(1.0, abs=1e-9)
    assert r.fcc is not None and r.coker is not None


def test_unhealthy_fcc_conditions_are_surfaced_as_warnings():
    r = refine(load_crude("cold_lake_blend"), 200_000)
    assert any("FCC:" in w for w in r.warnings)


def test_vgo_hydrotreating_helps_a_heavy_sour_slate_but_does_not_cure_it():
    s = load_crude("cold_lake_blend")
    raw = refine(s, 200_000)
    treated = refine(s, 200_000, RefineryConfig(vgo_hydrotreat=True))
    assert treated.mass_closure == pytest.approx(1.0, abs=1e-9)
    assert treated.fcc.conversion_wt_pct > raw.fcc.conversion_wt_pct + 7
    assert treated.fcc.regen_temperature_C < raw.fcc.regen_temperature_C - 30
    assert treated.fcc.gasoline_sulfur_ppm < raw.fcc.gasoline_sulfur_ppm / 8
    assert any('catalyst cooler' in w for w in treated.warnings)   # heaviest crudes still need more than pretreat
    ht = treated.vgo_hydrotreater
    assert ht is not None and ht.h2_makeup_kg_h > 0 and ht.reactor_volume_m3 > 0 and ht.s_out_ppm < ht.s_in_ppm / 5
    assert raw.vgo_hydrotreater is None
