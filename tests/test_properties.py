import math

import pytest

from refinery_design import properties as P


def test_api_sg_roundtrip():
    for api in (10.0, 22.3, 31.1, 44.0):
        assert P.api_from_sg(P.sg_from_api(api)) == pytest.approx(api)
    assert P.sg_from_api(10.0) == pytest.approx(1.0, abs=1e-3)  # API 10 == water


def test_watson_k_of_alkane_is_about_13():
    # n-hexadecane: Tb 560 K, SG 0.773 -> K ~ 13.0 (the paraffinic end of the scale)
    assert P.watson_k(560.0, 0.7733) == pytest.approx(13.0, abs=0.1)


def test_riazi_daubert_mw_hexadecane_within_a_few_percent():
    assert P.riazi_daubert_mw(560.0, 0.7733) == pytest.approx(226.4, rel=0.05)


def test_latent_heat_of_hexane_matches_nist():
    # n-hexane: 28.9 kJ/mol at 341.9 K = 335 kJ/kg (NIST)
    assert P.latent_heat_kJ_kg(341.9, 86.18) == pytest.approx(335.0, rel=0.04)


def test_liquid_cp_in_plausible_band_and_rises_with_temperature():
    lo, hi = P.liquid_cp_kJ_kgK(0.85, 11.8, 100.0), P.liquid_cp_kJ_kgK(0.85, 11.8, 300.0)
    assert 1.9 < lo < hi < 3.4


def test_vapour_cp_of_hydrocarbon_at_riser_temperature():
    assert 3.0 < P.vapour_cp_kJ_kgK(530.0) < 3.8


def test_steam_enthalpy_matches_steam_tables():
    # 250 C, 400 kPa abs: h ~ 2964 kJ/kg (IAPWS)
    assert P.steam_enthalpy_kJ_kg(250.0, 400.0) == pytest.approx(2964.0, abs=8.0)


def test_gas_sensible_enthalpy_matches_janaf():
    # CO2 H(1000 K)-H(298) = 33.4 kJ/mol; N2 = 21.5 kJ/mol
    assert P.gas_sensible_enthalpy_kJ_kmol("CO2", 1000.0) == pytest.approx(33_400, rel=0.02)
    assert P.gas_sensible_enthalpy_kJ_kmol("N2", 1000.0) == pytest.approx(21_460, rel=0.02)
    assert P.gas_sensible_enthalpy_kJ_kmol("N2", 298.15) == 0.0


def test_refutas_blend_is_between_components_and_idempotent():
    assert P.blend_viscosity_cSt([20.0, 20.0], [1, 1]) == pytest.approx(20.0)
    v = P.blend_viscosity_cSt([5.0, 500.0], [0.5, 0.5])
    assert 5.0 < v < 500.0
    assert v < 252.5  # log-type blending is below the linear mean


def test_classification_breakpoints():
    assert P.gravity_class(31.1) == "light" and P.gravity_class(31.0) == "medium"
    assert P.gravity_class(22.3) == "medium" and P.gravity_class(22.2) == "heavy"
    assert P.gravity_class(9.9) == "extra-heavy"
    assert P.sulfur_class(0.5) == "sweet" and P.sulfur_class(0.51) == "sour"
    assert P.acid_class(0.5) == "high-TAN" and P.acid_class(0.49) == "low-TAN"
    assert P.k_class(12.1) == "paraffinic" and P.k_class(11.6) == "intermediate"
    assert P.k_class(11.2) == "naphthenic/aromatic"
