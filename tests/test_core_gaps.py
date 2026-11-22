"""Offline tests for the small public surfaces and error paths the main suites left untouched.

Everything here is pure arithmetic, bundled data, or monkeypatched stubs.  No CoolProp mixture output is asserted.
"""
import math
from types import SimpleNamespace

import pytest

from refinery_design import assay, complexity, ethanol, fcc, fcc_modes, grm, petrochemical, safety, steam_cracker, trade
from refinery_design.assay import INF, Cut, Slate, _limit, barrels_to_kg, load_crude
from refinery_design.companies import bpcl, core, hpcl, nayara
from refinery_design.distillation import Stream
from refinery_design.fcc import FccFeed, FccOperation
from refinery_design.flowsheet import refine
from refinery_design.grm import PriceDeck
from refinery_design.properties import WATER_DENSITY_15C, api_from_density


# --------------------------------------------------------------------- assay
def _cut(density):
    return Cut("x", 100.0, 200.0, 0.1, 0.12, density, 150.0)


def test_cut_api_and_sg_follow_density():
    c = _cut(850.0)
    assert c.sg == pytest.approx(850.0 / WATER_DENSITY_15C)
    assert c.api == pytest.approx(api_from_density(850.0))
    assert c.api == pytest.approx(141.5 / c.sg - 131.5)


def test_cut_without_density_reports_none_not_zero():
    c = _cut(None)
    assert c.api is None and c.sg is None


@pytest.fixture
def dalia():
    c = load_crude("dalia")
    c.whole = dict(c.whole)  # private copy: the loader hands out a fresh dict each time, but be explicit
    return c


def test_crude_optional_whole_properties_default_to_zero_when_missing_or_null(dalia):
    for key, attr in (("ni_ppm", "ni_ppm"), ("v_ppm", "v_ppm"), ("mcr_wt", "mcr_wt")):
        dalia.whole.pop(key, None)
        assert getattr(dalia, attr) == 0.0
        dalia.whole[key] = None
        assert getattr(dalia, attr) == 0.0
        dalia.whole[key] = 3.5
        assert getattr(dalia, attr) == 3.5


def test_crude_pour_point_is_passed_through_including_none(dalia):
    dalia.whole["pour_C"] = -12.0
    assert dalia.pour_C == -12.0
    dalia.whole.pop("pour_C")
    assert dalia.pour_C is None


def test_mean_tb_of_an_empty_range_is_the_midpoint():
    c = load_crude("dalia")
    start = float(c.tbp[0, 0])
    # nothing distils below the first assay point, so the mass-weighting is degenerate and the midpoint is returned
    assert c.mean_tb_C(start - 200.0, start - 100.0) == pytest.approx(0.5 * (start + (start - 100.0)))


def test_mean_tb_lies_inside_a_populated_range():
    c = load_crude("dalia")
    tb = c.mean_tb_C(150.0, 250.0)
    assert 150.0 < tb < 250.0


@pytest.mark.parametrize("raw, expected", [
    ("IBP", -50.0), ("ibp", -50.0), ("  Fbp ", INF), ("C4", 36.1), ("c5", 36.1), (123, 123.0), (4.5, 4.5),
])
def test_limit_parses_named_boundaries(raw, expected):
    assert _limit(raw, True) == expected


def test_limit_rejects_unknown_names():
    with pytest.raises(ValueError, match="unrecognised cut limit"):
        _limit("C6", False)


def test_slate_whole_properties_are_mass_averages():
    a, b = load_crude("dalia"), load_crude("bakken")
    s = Slate([(a, 1.0), (b, 3.0)])
    wa = 0.25 * a.density_kg_m3
    wb = 0.75 * b.density_kg_m3
    wa, wb = wa / (wa + wb), wb / (wa + wb)
    for attr in ("ni_ppm", "v_ppm", "mcr_wt"):
        assert getattr(s, attr) == pytest.approx(wa * getattr(a, attr) + wb * getattr(b, attr))
    # a one-crude slate reproduces the crude
    one = Slate([(a, 5.0)])
    for attr in ("ni_ppm", "v_ppm", "mcr_wt"):
        assert getattr(one, attr) == pytest.approx(getattr(a, attr))


def test_barrels_to_kg_is_linear_in_volume_and_density():
    assert barrels_to_kg(1.0, 1000.0) == pytest.approx(158.987294928)
    assert barrels_to_kg(10.0, 870.0) == pytest.approx(10.0 * 870.0 * 0.158987294928)
    assert barrels_to_kg(0.0, 870.0) == 0.0


# --------------------------------------------------------------- companies
def test_companies_are_unique_and_in_first_seen_order():
    names = core.companies()
    assert len(names) == len(set(names))
    assert names[:3] == ["IOCL", "BPCL", "HPCL"]
    assert set(names) == {r["company"] for r in core.refineries()}


def test_refinery_lookup_by_id_and_unknown_id():
    assert core.refinery("BPCL/Mumbai")["company"] == "BPCL"
    with pytest.raises(KeyError):
        core.refinery("Nowhere/Refinery")


def test_utilisation_table_skips_refinery_years_with_neither_number():
    rows = core.utilisation_table()
    total_pairs = len(core.refineries()) * len(core.years())
    both_missing = sum(1 for r in core.refineries() for fy in core.years()
                       if core.throughput(r["id"], fy) is None and core.capacity(r["id"], fy) is None)
    assert both_missing > 0  # the data does have gaps, otherwise this test proves nothing
    assert len(rows) == total_pairs - both_missing
    assert all(r["throughput_mmt"] is not None or r["capacity_mmtpa"] is not None for r in rows)


def test_fcc_changes_filters_by_company_prefix_not_substring():
    all_changes = core.fcc_changes()
    assert len(all_changes) == 20
    iocl = core.fcc_changes(company="IOCL")
    assert iocl and all(e["refinery"].startswith("IOCL/") for e in iocl)
    # "CP" must not match "CPCL/..." because the filter requires the "/" separator
    assert core.fcc_changes(company="CP") == []


def test_fcc_changes_filters_by_refinery_and_since_is_inclusive():
    one = core.fcc_changes(refinery_id="IOCL/Mathura")
    assert one and {e["refinery"] for e in one} == {"IOCL/Mathura"}
    assert core.fcc_changes(since=2026) and all(e["year"] >= 2026 for e in core.fcc_changes(since=2026))
    years = sorted({e["year"] for e in core.fcc_changes()})
    boundary = years[3]
    assert min(e["year"] for e in core.fcc_changes(since=boundary)) == boundary
    assert len(core.fcc_changes(since=boundary + 1)) < len(core.fcc_changes(since=boundary))


def test_fcc_changes_are_sorted_by_year_then_refinery():
    out = core.fcc_changes()
    assert out == sorted(out, key=lambda e: (e["year"], e["refinery"]))


def test_fcc_changes_returns_copies():
    first = core.fcc_changes()[0]
    first["event"] = "tampered"
    assert core.fcc_changes()[0]["event"] != "tampered"


@pytest.mark.parametrize("mod, name", [(bpcl, "BPCL"), (hpcl, "HPCL"), (nayara, "Nayara")])
def test_company_modules_wrap_the_core_rollup(mod, name):
    assert mod.NAME == name
    assert mod.refineries() == core.refineries(name)
    assert mod.summary() == core.company_rollup(name, "2025-26")
    assert mod.summary("2022-23") == core.company_rollup(name, "2022-23")


# ---------------------------------------------------------------- complexity
def test_nelson_ignores_an_explicit_cdu_entry():
    base = complexity.nelson_complexity(100.0, {"fcc": 30.0})
    assert base == pytest.approx(1.0 + 6.0 * 0.3)
    assert complexity.nelson_complexity(100.0, {"cdu": 100.0, "fcc": 30.0}) == base
    assert complexity.nelson_complexity(100.0, {}) == 1.0


def test_nelson_vintages_differ_on_thermal_and_lubes():
    units = {"thermal": 20.0, "lubes": 10.0}
    assert complexity.nelson_complexity(100.0, units, "1998") == pytest.approx(1.0 + 2.75 * 0.2 + 60.0 * 0.1)
    assert complexity.nelson_complexity(100.0, units, "older") == pytest.approx(1.0 + 5.0 * 0.2 + 10.0 * 0.1)


def test_nelson_rejects_unknown_units():
    with pytest.raises(KeyError, match="unknown unit"):
        complexity.nelson_complexity(100.0, {"flux_capacitor": 5.0})


# -------------------------------------------------------------- distillation
def test_stream_exposes_its_cut_fractions_and_density():
    c = Cut("diesel", 250.0, 370.0, 0.21, 0.23, 840.0, 310.0)
    s = Stream("diesel", c, 1000.0, 50.0)
    assert (s.wt_frac, s.vol_frac, s.density_kg_m3) == (0.21, 0.23, 840.0)


# ------------------------------------------------------------------- ethanol
def test_ebp_returns_a_defensive_copy():
    first = ethanol.ebp()
    assert first
    first["__tamper__"] = 1
    assert "__tamper__" not in ethanol.ebp()
    assert ethanol.ebp() == ethanol.ebp()


# ----------------------------------------------------------------------- fcc
def test_fcc_result_summary_formats_the_headline_numbers():
    res = fcc.FccResult(
        feed=SimpleNamespace(name="VGO-1"), operation=None, regen_temperature_C=701.4, cat_to_oil=6.789,
        conversion_wt_pct=72.34, yields_wt_pct={"gasoline": 45.55, "lpg": 18.04, "dry_gas": 3.21, "lco": 15.5, "slurry": 6.0},
        yields_vol_pct={}, coke_wt_pct=5.678, delta_coke_wt_pct=0.8, heat_balance_kJ_per_kg_feed={}, riser={}, regenerator={},
        flue_gas={}, sulfur_distribution={}, gasoline_sulfur_ppm=0.0)
    assert res.summary() == ("VGO-1: conv 72.3 wt%, C/O 6.79, Tregen 701 C, coke 5.68 wt%, "
                             "gasoline 45.5, LPG 18.0, dry gas 3.2, LCO 15.5, slurry 6.0")


def _checks(**over):
    args = dict(t_regen=700.0, co=6.0, conv=75.0, coke=5.0, dcoke=1.0,
                feed=SimpleNamespace(ni_ppm=0.5, v_ppm=0.5, ccr_wt=0.5),
                riser={"exit_velocity_m_s": 20.0}, regen={"dense_bed_height_m": 8.0})
    args.update(over)
    return fcc._checks(args["feed"], None, args["t_regen"], args["co"], args["conv"], args["coke"],
                       args["riser"], args["regen"], args["dcoke"])


def test_fcc_checks_are_silent_inside_every_envelope():
    assert _checks() == []


@pytest.mark.parametrize("v", [15.0, 30.0])
def test_riser_exit_velocity_envelope_edges_are_inclusive(v):
    assert _checks(riser={"exit_velocity_m_s": v}) == []


@pytest.mark.parametrize("v, shown", [(14.9, "15 m/s"), (30.1, "30 m/s")])
def test_riser_exit_velocity_outside_the_band_is_flagged(v, shown):
    (msg,) = _checks(riser={"exit_velocity_m_s": v})
    assert msg == f"riser exit velocity {v:.0f} m/s outside ~15-30 m/s"


@pytest.mark.parametrize("d, flagged", [(0.4, False), (1.6, False), (0.39, True), (1.61, True)])
def test_delta_coke_band_edges(d, flagged):
    out = _checks(dcoke=d)
    assert bool(out) is flagged
    if flagged:
        assert out == [f"delta coke {d:.2f} wt% outside the usual ~0.4-1.6 band"]


@pytest.mark.parametrize("co, flagged", [(4.0, False), (10.0, False), (3.9, True), (10.1, True)])
def test_cat_to_oil_band_edges(co, flagged):
    assert bool(_checks(co=co)) is flagged


@pytest.mark.parametrize("t, flagged", [(660.0, False), (760.0, False), (659.9, True), (760.1, True)])
def test_regenerator_temperature_edges(t, flagged):
    assert bool(_checks(t_regen=t)) is flagged


def test_feed_metals_and_ccr_thresholds_are_strict():
    ok = SimpleNamespace(ni_ppm=2.5, v_ppm=2.5, ccr_wt=1.5)
    assert _checks(feed=ok) == []
    metals = SimpleNamespace(ni_ppm=2.5, v_ppm=2.6, ccr_wt=1.5)
    assert len(_checks(feed=metals)) == 1 and "Ni+V 5.1 ppm" in _checks(feed=metals)[0]
    ccr = SimpleNamespace(ni_ppm=0.0, v_ppm=0.0, ccr_wt=1.6)
    assert len(_checks(feed=ccr)) == 1 and "CCR 1.6 wt%" in _checks(feed=ccr)[0]


def test_dense_bed_height_edges():
    assert _checks(regen={"dense_bed_height_m": 12.0}) == [] and _checks(regen={"dense_bed_height_m": 4.0}) == []
    assert "> 12 m" in _checks(regen={"dense_bed_height_m": 12.1})[0]
    assert "shallow (< 4 m)" in _checks(regen={"dense_bed_height_m": 3.9})[0]


# ----------------------------------------------------------------- fcc_modes
REF = FccFeed("ref VGO", density_kg_m3=928.7, mabp_C=460.0, sulfur_wt=0.5, ccr_wt=0.3)
OP = FccOperation(feed_rate_kg_s=100.0)


def test_propylene_mode_that_overdraws_gasoline_and_lco_is_rejected(monkeypatch):
    monkeypatch.setitem(petrochemical.PROPYLENE_WT, "propylene_mode", 60.0)
    with pytest.raises(ValueError, match="exceeds the gasoline/LCO available"):
        fcc_modes.modes(REF, OP)


@pytest.mark.parametrize("target", [35.0])
def test_propylene_mode_is_rejected_as_soon_as_either_gasoline_or_lco_runs_out(monkeypatch, target):
    # at 35 wt% only one of the two pools has gone negative (LCO is the smaller and takes 30% of the offset);
    # the guard is an OR, so this must still raise
    monkeypatch.setitem(petrochemical.PROPYLENE_WT, "propylene_mode", target)
    with pytest.raises(ValueError, match="exceeds the gasoline/LCO available"):
        fcc_modes.modes(REF, OP)


def test_propylene_mode_just_inside_the_available_pools_is_accepted(monkeypatch):
    monkeypatch.setitem(petrochemical.PROPYLENE_WT, "propylene_mode", 30.0)
    out = fcc_modes.modes(REF, OP)
    assert out[-1].name == "propylene"
    assert out[-1].yields_wt_pct["gasoline"] >= 0 and out[-1].yields_wt_pct["lco"] >= 0


# ----------------------------------------------------------------- flowsheet
def test_middle_distillate_yield_property_matches_the_pool():
    r = refine(load_crude("upper_zakum"), 200_000)
    assert r.middle_distillate_yield_wt_pct == r.pools_wt_pct()["middle_distillate"]
    assert 0.0 < r.middle_distillate_yield_wt_pct < 100.0


# ----------------------------------------------------------------------- grm
def _stub_grm(monkeypatch, slope, intercept=3.0):
    monkeypatch.setattr(grm, "gross_refining_margin",
                        lambda result, deck, loss: SimpleNamespace(grm_usd_bbl=intercept + slope * deck.cracks_usd_bbl["x"]))


DECK_X = PriceDeck(80.0, cracks_usd_bbl={"x": 1.0})


def test_calibration_that_cannot_move_the_margin_is_rejected(monkeypatch):
    _stub_grm(monkeypatch, 0.0)
    with pytest.raises(ValueError, match="does not respond to the cracks"):
        grm.calibrate_deck(None, DECK_X, 10.0)


def test_calibration_tolerance_is_1e_minus_9(monkeypatch):
    _stub_grm(monkeypatch, 5e-10)
    with pytest.raises(ValueError):
        grm.calibrate_deck(None, DECK_X, 10.0)
    _stub_grm(monkeypatch, 2e-9)
    d = grm.calibrate_deck(None, DECK_X, 3.000000004)
    assert d.cracks_usd_bbl["x"] == pytest.approx(2.0)


def test_calibration_scales_cracks_linearly_and_labels_the_deck(monkeypatch):
    _stub_grm(monkeypatch, 4.0, intercept=1.0)  # grm = 1 + 4 s
    d = grm.calibrate_deck(None, DECK_X, 9.0)
    assert d.cracks_usd_bbl["x"] == pytest.approx(2.0)
    assert d.label == "calibrated to 9.00 $/bbl"
    assert d.crude_usd_bbl == 80.0


# ------------------------------------------------------------ petrochemical
def test_propylene_mode_below_what_the_fcc_already_makes_is_rejected(monkeypatch):
    from refinery_design.benchmarks import paradip_model_refinery

    r = paradip_model_refinery()
    monkeypatch.setitem(petrochemical.PROPYLENE_WT, "propylene_mode", 0.01)
    with pytest.raises(ValueError, match="below what the FCC already makes"):
        petrochemical.build_option(r, PriceDeck(80.0), "propylene_mode")


# -------------------------------------------------------------------- safety
def _flags(t):
    return [f for f in safety.fcc_flags(SimpleNamespace(regen_temperature_C=t)) if f.topic == "FCC regenerator temperature"]


def test_cold_regenerator_raises_a_watch_flag():
    (f,) = _flags(640.0)
    assert f.level == "watch" and "640 C is cold" in f.message
    assert f.basis == "repo heuristic" and f.standards


def test_hot_regenerator_raises_an_action_flag():
    (f,) = _flags(780.0)
    assert f.level == "action" and "780 C is above 760 C" in f.message


@pytest.mark.parametrize("t", [660.0, 700.0, 760.0])
def test_regenerator_temperature_flag_edges_are_inclusive_of_the_safe_band(t):
    assert _flags(t) == []


def test_slide_valve_info_flag_is_always_present():
    out = safety.fcc_flags(SimpleNamespace(regen_temperature_C=700.0))
    assert [f.level for f in out] == ["info"]
    assert out[0].topic == "FCC reactor-regenerator isolation"


# -------------------------------------------------------------- steam_cracker
class _NoNaphthaDeck:
    def product_usd_t(self, pool):
        if pool == "naphtha":
            raise KeyError(pool)
        return {"gasoline_range": 777.0}[pool]


def test_naphtha_price_prefers_explicit_then_deck_then_gasoline_range():
    assert steam_cracker.resolve_naphtha_usd_t(_NoNaphthaDeck(), 123.0) == 123.0
    assert steam_cracker.resolve_naphtha_usd_t(_NoNaphthaDeck(), 0.0) == 0.0  # an explicit zero is a value, not "missing"
    assert steam_cracker.resolve_naphtha_usd_t(_NoNaphthaDeck(), None) == 777.0
    assert steam_cracker.resolve_naphtha_usd_t(SimpleNamespace(product_usd_t=lambda p: {"naphtha": 640.0}[p]), None) == 640.0


def test_naphtha_price_falls_back_when_the_deck_lacks_the_method():
    class Odd:
        def product_usd_t(self, pool):
            if pool == "naphtha":
                raise AttributeError(pool)
            return 555.0

    assert steam_cracker.resolve_naphtha_usd_t(Odd(), None) == 555.0


def test_overfilled_yield_slate_is_rejected(monkeypatch):
    bad = SimpleNamespace(fuel_gas_and_other=-0.1)
    monkeypatch.setattr(steam_cracker, "yields_at", lambda coil: bad)
    with pytest.raises(ValueError, match="over-fills the mass balance"):
        steam_cracker.build_cracker(1_000_000.0)


def test_a_slate_that_exactly_fills_the_mass_balance_is_accepted(monkeypatch):
    real = steam_cracker.yields_at(850.0)

    class Exact:
        fuel_gas_and_other = 0.0

        def __getattr__(self, name):
            return getattr(real, name)

    monkeypatch.setattr(steam_cracker, "yields_at", lambda coil: Exact())
    opt = steam_cracker.build_cracker(1_000_000.0)
    assert opt.naphtha_t_y == 1_000_000.0


def test_nonpositive_naphtha_feed_is_rejected():
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError, match="must be positive"):
            steam_cracker.build_cracker(bad)


def test_cracker_yields_are_clamped_to_the_cited_bands():
    assert steam_cracker.yields_at(780.0).ethylene == 20.0
    assert steam_cracker.yields_at(900.0).ethylene == 31.0
    assert steam_cracker.yields_at(820.0).propylene == 16.0
    with pytest.raises(ValueError):
        steam_cracker.yields_at(779.9)
    with pytest.raises(ValueError):
        steam_cracker.yields_at(900.1)


# --------------------------------------------------------------------- trade
def test_trade_deck_crude_price_is_the_observed_import_unit_value():
    deck = trade.TradeDeck("2022-23")
    assert deck.crude_usd_t() == trade.unit_value_usd_t("imports", "crude", "2022-23")
    assert deck.crude_usd_t() > 0
    assert deck.product_usd_t("naphtha") == trade.unit_value_usd_t("exports", "naphtha", "2022-23")
    assert deck.product_usd_t("slurry") == deck.product_usd_t("vacuum_residue") == trade.unit_value_usd_t("imports", "fuel_oil", "2022-23")
    with pytest.raises(KeyError):
        deck.product_usd_t("unobtainium")


def test_trade_deck_crude_density_changes_the_barrel_price_not_the_tonne_price():
    light, heavy = trade.TradeDeck("2022-23", 800.0), trade.TradeDeck("2022-23", 950.0)
    assert light.crude_usd_t() == heavy.crude_usd_t()
    assert light.crude_usd_bbl < heavy.crude_usd_bbl
    assert light.crude_usd_bbl == pytest.approx(light.crude_usd_t() * 0.158987294928 * 800.0 / 1000.0)


def test_module_surface_sanity():
    assert math.isinf(assay.INF) and assay.available_crudes()
