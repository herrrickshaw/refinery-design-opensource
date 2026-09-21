import math

import numpy as np
import pytest

from refinery_design.assay import INF, Slate, available_crudes, load_crude
from refinery_design.properties import api_from_density

ALL = available_crudes()


def test_eight_published_assays_are_bundled():
    assert len(ALL) == 8
    assert {"bakken", "dalia", "cold_lake_blend", "upper_zakum"} <= set(ALL)


def test_unknown_crude_raises_helpfully():
    with pytest.raises(KeyError, match="available"):
        load_crude("nonexistent")


@pytest.mark.parametrize("key", ALL)
def test_tbp_curve_is_monotonic_and_consistent(key):
    c = load_crude(key)
    assert np.all(np.diff(c.tbp[:, 0]) > 0)
    assert np.all(np.diff(c.tbp[:, 1]) >= -1e-9) and np.all(np.diff(c.tbp[:, 2]) >= -1e-9)
    assert c.cum_wt(-100) == 0.0 and c.cum_wt(INF) == 1.0
    # mass % distilled runs ahead of volume % for the light ends, behind for heavy
    assert c.cum_vol(100) > c.cum_wt(100)


@pytest.mark.parametrize("key", ALL)
def test_contiguous_cuts_sum_to_one(key):
    c = load_crude(key)
    edges = [-50.0, 36.1, 150.0, 250.0, 370.0, 550.0, INF]
    cuts = [c.cut(a, b) for a, b in zip(edges[:-1], edges[1:])]
    assert sum(x.wt_frac for x in cuts) == pytest.approx(1.0, abs=1e-9)
    assert sum(x.vol_frac for x in cuts) == pytest.approx(1.0, abs=1e-9)
    # mass-balance identity: crude density = sum(cut mass)/sum(cut volume)
    mass = sum(x.wt_frac for x in cuts)
    vol = sum(x.wt_frac / x.density_kg_m3 for x in cuts if x.density_kg_m3)
    assert mass / vol == pytest.approx(c.density_kg_m3, rel=1e-6)


@pytest.mark.parametrize("key", ALL)
def test_tbp_derived_cut_density_agrees_with_reported_assay_cuts(key):
    """Independent cross-check: density implied by the TBP yields vs. the
    density the assay itself reports for each narrow cut."""
    c = load_crude(key)
    checked = 0
    for a in c._narrow_cuts():
        rho = a.get("density")
        # From 65 C up only: the lightest assay cut is defined inconsistently
        # between assays (Cold Lake's "C5-65" yield lumps in the C4- gas).
        if rho is None or not math.isfinite(a["hi"]) or a["hi"] <= a["lo"] + 20 or a["lo"] < 65:
            continue
        got = c.cut(a["lo"], a["hi"]).density_kg_m3
        assert got == pytest.approx(rho * 1000.0, rel=0.02), (a["lo"], a["hi"])
        checked += 1
    assert checked >= 5


def test_crude_types_are_classified_as_expected():
    assert load_crude("bakken").classification() == {
        "gravity": "light", "sulfur": "sweet", "acidity": "low-TAN", "character": "paraffinic"}
    cl = load_crude("cold_lake_blend").classification()
    assert (cl["gravity"], cl["sulfur"], cl["acidity"]) == ("heavy", "sour", "high-TAN")
    assert load_crude("dalia").classification()["acidity"] == "high-TAN"
    assert load_crude("upper_zakum").classification()["sulfur"] == "sour"


def test_heavier_crude_yields_more_vacuum_residue():
    by_api = sorted(ALL, key=lambda k: load_crude(k).api)  # heavy -> light
    vr = [load_crude(k).cut(550, INF).wt_frac for k in by_api]
    assert vr[0] > vr[-1] * 3
    assert vr[0] == max(vr)


def test_sulfur_and_metals_concentrate_in_the_residue():
    c = load_crude("cold_lake_blend")
    naphtha, vgo, vr = c.cut(36.1, 150), c.cut(370, 550), c.cut(550, INF)
    assert naphtha.sulfur_wt < vgo.sulfur_wt < vr.sulfur_wt
    assert vr.mcr_wt > 10 * (vgo.mcr_wt or 0.001)
    assert vr.v_ppm > 100 and vr.ni_ppm > 50


def test_cut_outside_the_curve_is_empty():
    c = load_crude("bakken")
    x = c.cut(-200, -100)
    assert x.wt_frac == 0.0 and x.density_kg_m3 is None


# --- slates --------------------------------------------------------
def test_single_crude_slate_equals_the_crude():
    c = load_crude("dalia")
    s = Slate([(c, 1.0)])
    a, b = c.cut(370, 550), s.cut(370, 550)
    assert b.wt_frac == pytest.approx(a.wt_frac) and b.density_kg_m3 == pytest.approx(a.density_kg_m3)
    assert s.api == pytest.approx(api_from_density(c.density_kg_m3))


def test_blend_properties_are_exact_mass_and_volume_averages():
    a, b = load_crude("bakken"), load_crude("cold_lake_blend")
    s = Slate([(a, 0.7), (b, 0.3)])
    assert s.density_kg_m3 == pytest.approx(0.7 * a.density_kg_m3 + 0.3 * b.density_kg_m3)
    wa = 0.7 * a.density_kg_m3 / s.density_kg_m3
    assert s.sulfur_wt == pytest.approx(wa * a.sulfur_wt + (1 - wa) * b.sulfur_wt)
    assert b.api < s.api < a.api
    # residue yield by volume blends linearly
    assert s.cut(550, INF).vol_frac == pytest.approx(0.7 * a.cut(550, INF).vol_frac + 0.3 * b.cut(550, INF).vol_frac)


def test_slate_fractions_are_normalised_and_validated():
    a, b = load_crude("bakken"), load_crude("dalia")
    s = Slate([(a, 3), (b, 1)])
    assert s.components[0][1] == pytest.approx(0.75)
    with pytest.raises(ValueError):
        Slate([])
    with pytest.raises(ValueError):
        Slate([(a, 0.0)])
