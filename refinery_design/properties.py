"""Petroleum-fraction property helpers.

Same discipline as the sibling design repos: textbook correlations only,
each cited, and CoolProp (peer-reviewed equations of state) wherever it
covers the fluid - here for the ideal-gas heat capacities of hydrocarbon
vapour (n-dodecane as the representative alkane), steam, air and flue-gas
components.

Conventions: SI unless a name says otherwise (``_C`` degrees Celsius,
``_K`` kelvin, ``_bpd`` barrels/day).  Densities are at 15 degC.
"""
from __future__ import annotations

import math
from functools import lru_cache

import CoolProp.CoolProp as CP
import numpy as np
from scipy.integrate import simpson

R_UNIVERSAL = 8.314462618  # J/mol-K
BBL_M3 = 0.158987294928    # US oil barrel, m3
WATER_DENSITY_15C = 999.0  # kg/m3 (API gravity reference, ~60 degF)


# --------------------------------------------------------------------
# Gravity / characterisation
# --------------------------------------------------------------------
def sg_from_api(api: float) -> float:
    """Specific gravity (60/60 degF) from API gravity.  API = 141.5/SG - 131.5."""
    return 141.5 / (api + 131.5)


def api_from_sg(sg: float) -> float:
    return 141.5 / sg - 131.5


def density_from_api(api: float) -> float:
    """kg/m3 at ~15 degC."""
    return sg_from_api(api) * WATER_DENSITY_15C


def api_from_density(density_kg_m3: float) -> float:
    return api_from_sg(density_kg_m3 / WATER_DENSITY_15C)


def watson_k(mabp_K: float, sg: float) -> float:
    """Watson / UOP characterisation factor K = (1.8*Tb)^(1/3) / SG.

    Tb is the mean average boiling point in kelvin (the formula wants
    Rankine, hence 1.8*Tb).  Watson & Nelson, Ind. Eng. Chem. 25, 880
    (1933).  ~12.5+ paraffinic, ~11.5-12 intermediate, <~11.5
    naphthenic/aromatic - the usual reading of the scale.
    """
    return (1.8 * mabp_K) ** (1.0 / 3.0) / sg


def sg_from_watson_k(mabp_K: float, k: float) -> float:
    return (1.8 * mabp_K) ** (1.0 / 3.0) / k


def riazi_daubert_mw(tb_K: float, sg: float) -> float:
    """Molecular weight of a petroleum fraction from Tb (K) and SG.

    Riazi & Daubert, Hydrocarbon Processing 66(3), 1987 (the widely used
    two-parameter form):
        M = 42.965 exp(2.097e-4 Tb - 7.78712 SG + 2.08476e-3 Tb SG)
                  Tb^1.26007 SG^4.98308
    """
    return (42.965 * math.exp(2.097e-4 * tb_K - 7.78712 * sg + 2.08476e-3 * tb_K * sg)
            * tb_K ** 1.26007 * sg ** 4.98308)


# --------------------------------------------------------------------
# Thermal properties
# --------------------------------------------------------------------
def liquid_cp_kJ_kgK(sg: float, k_watson: float, T_C: float) -> float:
    """Liquid petroleum heat capacity, kJ/kg-K.

    Watson-Nelson form (as reproduced in Gary & Handwerk and Riazi):
        cp [Btu/lb-degF] = (0.6811 - 0.308 SG + (0.000815 - 0.000306 SG) T_F)
                           * (0.055 K + 0.35)
    """
    t_f = T_C * 1.8 + 32.0
    cp_btu = (0.6811 - 0.308 * sg + (0.000815 - 0.000306 * sg) * t_f) * (0.055 * k_watson + 0.35)
    return cp_btu * 4.1868


def latent_heat_kJ_kg(tb_K: float, mw: float) -> float:
    """Latent heat at the normal boiling point.

    Fishtine / Kistiakowsky form (Reid, Prausnitz & Poling, "The
    Properties of Gases and Liquids"):  dHvb = Tb (8.75 + 1.987 ln Tb)
    cal/mol, valid for non-polar hydrocarbons.
    """
    cal_per_mol = tb_K * (8.75 + 1.987 * math.log(tb_K))
    return cal_per_mol * 4.184 / mw  # J/mol / (g/mol) = kJ/kg


def vapour_cp_kJ_kgK(T_C: float) -> float:
    """Ideal-gas heat capacity of hydrocarbon vapour, kJ/kg-K.

    Per-kilogram ideal-gas cp of the n-alkane family is nearly
    independent of chain length above ~C8, so n-dodecane's CoolProp
    ideal-gas cp (Lemmon & Huber 2004 EOS) stands in for a cracked or
    distilled vapour.
    """
    return _cp0_mass("Dodecane", round(T_C + 273.15, 1)) / 1000.0


@lru_cache(maxsize=4096)
def _cp0_mass(fluid: str, T_K: float) -> float:
    return CP.PropsSI("Cp0mass", "T", T_K, "P", 101325.0, fluid)


@lru_cache(maxsize=4096)
def _cp0_molar(fluid: str, T_K: float) -> float:
    return CP.PropsSI("Cp0molar", "T", T_K, "P", 101325.0, fluid)


_GAS_FLUIDS = {
    "N2": "Nitrogen", "O2": "Oxygen", "CO2": "CarbonDioxide", "CO": "CarbonMonoxide",
    "H2O": "Water", "SO2": "SulfurDioxide", "Air": "Air",
}
GAS_MW = {"N2": 28.0134, "O2": 31.998, "CO2": 44.0095, "CO": 28.0101, "H2O": 18.0153,
          "SO2": 64.066, "Air": 28.9586}


def gas_sensible_enthalpy_kJ_kmol(species: str, T_K: float, T_ref_K: float = 298.15) -> float:
    """Ideal-gas sensible enthalpy above ``T_ref_K``, kJ/kmol (CoolProp Cp0)."""
    fluid = _GAS_FLUIDS[species]
    if T_K == T_ref_K:
        return 0.0
    grid = np.linspace(T_ref_K, T_K, 33)  # Simpson, 32 panels
    cp = np.array([_cp0_molar(fluid, round(float(t), 1)) for t in grid])
    return float(simpson(cp, x=grid))  # J/mol == kJ/kmol


def steam_enthalpy_kJ_kg(T_C: float, P_kPa_abs: float) -> float:
    """Superheated-steam enthalpy (IAPWS-95 via CoolProp)."""
    return CP.PropsSI("Hmass", "T", T_C + 273.15, "P", P_kPa_abs * 1000.0, "Water") / 1000.0


# --------------------------------------------------------------------
# Viscosity blending
# --------------------------------------------------------------------
def refutas_vbi(nu_cSt: float) -> float:
    """Refutas viscosity blending index: 14.534 ln(ln(nu + 0.8)) + 10.975."""
    return 14.534 * math.log(math.log(nu_cSt + 0.8)) + 10.975


def refutas_nu(vbi: float) -> float:
    return math.exp(math.exp((vbi - 10.975) / 14.534)) - 0.8


def blend_viscosity_cSt(nu_cSt: list[float], mass_frac: list[float]) -> float:
    """Mass-weighted Refutas blend of kinematic viscosities at one temperature."""
    total = sum(mass_frac)
    vbi = sum(w / total * refutas_vbi(n) for n, w in zip(nu_cSt, mass_frac))
    return refutas_nu(vbi)


# --------------------------------------------------------------------
# Crude classification conventions
# --------------------------------------------------------------------
def gravity_class(api: float) -> str:
    """Light / medium / heavy at the US DOE-EIA breakpoints (31.1, 22.3 API)."""
    if api >= 31.1:
        return "light"
    if api >= 22.3:
        return "medium"
    if api >= 10.0:
        return "heavy"
    return "extra-heavy"


def sulfur_class(sulfur_wt: float) -> str:
    """Sweet at <= 0.5 wt% S, sour above (the common trading convention)."""
    return "sweet" if sulfur_wt <= 0.5 else "sour"


def acid_class(tan_mgKOH_g: float) -> str:
    """'high-TAN' from ~0.5 mgKOH/g (literature threshold spans 0.5-1.0)."""
    return "high-TAN" if tan_mgKOH_g >= 0.5 else "low-TAN"


def k_class(k: float) -> str:
    if k >= 12.0:
        return "paraffinic"
    if k >= 11.5:
        return "intermediate"
    return "naphthenic/aromatic"
