import pytest

from refinery_design import safety as sf
from refinery_design.assay import Slate, load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.fcc_modes import modes
from refinery_design.flowsheet import RefineryConfig, refine
from refinery_design.steam_cracker import build_cracker

R = paradip_model_refinery(True)


def test_official_oisd_list_is_loaded_with_editions():
    s = sf.all_standards()
    assert len(s) == 105
    assert s["OISD-STD-116"]["edition"] == "Jun, 2025" and "Petrochemical Complexes" in s["OISD-STD-116"]["title"]
    assert s["OISD-STD-118"]["title"] == "Layouts for Oil and Gas Installations"
    assert "Safety Instrumentation" in s["OISD-STD-152"]["title"] and s["OISD-STD-152"]["edition"] == "Jun, 2024"
    assert "hydrogen" in s["OISD-STD-241"]["title"]
    assert "Fired Process Furnace" in s["OISD-STD-111"]["title"]


def test_a_correction_the_list_forced_oisd_154_is_training_not_fired_heaters():
    assert "Training" in sf.standard("OISD-STD-154")["title"]
    assert "Fired" in sf.standard("OISD-STD-111")["title"] and "Inspection of Fired Heaters" == sf.standard("OISD-STD-133")["title"]


def test_every_mapped_standard_exists_in_the_official_list():
    known = sf.all_standards()
    for element, d in sf.DESIGN_MAP.items():
        assert d["oisd"] and d["check"] and d["basis"], element
        for n in d["oisd"]:
            assert n in known, (element, n)


def test_keyword_sanity_of_the_mapping():
    dm = sf.DESIGN_MAP
    assert "OISD-STD-241" in dm["hydrotreater_hydrogen"]["oisd"] and "OISD-STD-241" in dm["steam_cracker"]["oisd"]
    assert "OISD-STD-144" in dm["lpg_propylene_storage"]["oisd"] and "OISD-STD-236" in dm["lpg_propylene_storage"]["oisd"]
    assert "OISD-STD-152" in dm["fcc_reactor_regenerator"]["oisd"] and "OISD-STD-178" in dm["fcc_gas_plant"]["oisd"]
    assert "OISD-STD-112" in dm["fcc_reactor_regenerator"]["oisd"]              # pyrophoric substances
    assert "no OISD standard specific" in dm["delayed_coker"]["check"]
    assert "NOT verified" in dm["lpg_propylene_storage"]["check"]


def test_high_tan_crudes_are_flagged_and_light_sweet_are_not():
    assert sf.crude_corrosion_flags(load_crude("bakken").as_slate()) == []
    for k in ("dalia", "cold_lake_blend", "kearl"):
        flags = sf.crude_corrosion_flags(load_crude(k).as_slate())
        assert any(f.topic == "crude corrosivity" for f in flags), k
    hot = [f for f in sf.crude_corrosion_flags(load_crude("kearl").as_slate()) if f.topic == "crude corrosivity"][0]
    assert hot.level == "action" and "232" in hot.message and "316/317L" in hot.message and "not a reliable predictor" in hot.message
    assert "OISD-STD-111" in hot.standards


def test_sour_service_flag_follows_sulfur():
    assert any(f.topic == "sour service" for f in sf.crude_corrosion_flags(load_crude("upper_zakum").as_slate()))
    assert not any(f.topic == "sour service" for f in sf.crude_corrosion_flags(load_crude("azeri_btc").as_slate()))


def test_blend_tan_flag_appears_as_heavy_crude_is_added():
    base, heavy = load_crude("azeri_btc"), load_crude("cold_lake_blend")
    lo = sf.crude_corrosion_flags(Slate([(base, 0.95), (heavy, 0.05)]))
    hi = sf.crude_corrosion_flags(Slate([(base, 0.5), (heavy, 0.5)]))
    assert len([f for f in hi if f.topic == "crude corrosivity"]) >= len([f for f in lo if f.topic == "crude corrosivity"])
    assert any(f.topic == "crude corrosivity" for f in hi)


def test_fcc_and_gas_plant_flags():
    ms = modes(R.fcc.feed, R.fcc.operation)
    flags = sf.fcc_flags(R.fcc, ms)
    assert any("slide valves" in f.message for f in flags)
    gp = {f.topic: f for f in flags if f.topic.startswith("FCC gas plant")}
    assert "FCC gas plant (propylene)" in gp and gp["FCC gas plant (propylene)"].level == "action" and "beyond" in gp["FCC gas plant (propylene)"].message
    assert "FCC gas plant (high_severity)" in gp and gp["FCC gas plant (high_severity)"].level == "watch"
    assert "FCC gas plant (distillate)" not in gp and "FCC gas plant (lpg_zsm5)" not in gp      # <= +15%
    assert all("OISD-STD-178" in f.standards for f in gp.values())


def test_hot_regenerator_is_an_action_flag_and_cold_a_watch():
    hot = refine(load_crude("cold_lake_blend"), 100_000)
    assert any(f.level == "action" and f.topic == "FCC regenerator temperature" for f in sf.fcc_flags(hot.fcc))


def test_review_aggregates_everything_and_every_flag_has_a_basis():
    cr = build_cracker(3.0e6)
    flags = sf.refinery_review(R, modes(R.fcc.feed, R.fcc.operation), cr, R.distillation and load_crude("cold_lake_blend").as_slate())
    topics = {f.topic for f in flags}
    assert {"crude corrosivity", "hydrotreater", "LPG/propylene handling", "delayed coker", "steam cracker", "polymer units"} <= topics
    for f in flags:
        assert f.basis and f.standards and f.level in {"action", "watch", "info"}
        assert all(n in sf.all_standards() for n in f.standards)


def test_review_without_optional_parts():
    r = refine(load_crude("bakken"), 100_000, RefineryConfig(fcc=False, coker=False))
    flags = sf.refinery_review(r)
    assert {f.topic for f in flags} == {"LPG/propylene handling"}
