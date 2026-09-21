"""Fluid catalytic cracking: riser reactor + regenerator, heat-balanced.

What is modelled
----------------
* **Riser kinetics** - a 4-lump scheme (feed/unconverted, gasoline, gas,
  coke) in the family of Weekman & Nace (AIChE J. 16, 1970, 3-lump) and
  Lee, Chen, Huang & Pan (Can. J. Chem. Eng. 67, 1989, 4-lump):
  second-order feed cracking, first-order gasoline over-cracking,
  Arrhenius temperatures, exponential catalyst decay with time on stream.
  Rate constants here are **calibrated to reproduce typical published
  yield ranges, not fitted to plant data** (see docs/VALIDATION.md); the
  scheme's structure, not its constants, is the literature-grounded part.
* **Heat balance** - the classic FCC coupling: the regenerator's coke burn
  must supply the riser's heat demand (feed heating + vaporisation + the
  endothermic reactions + steam), the air/flue-gas sensible heat, coke
  desorption and losses.  Catalyst circulation (cat/oil) follows from the
  riser demand and the regenerator-riser temperature difference; coke
  make follows from the kinetics; the regenerator temperature is the
  unknown that closes the loop (Sadeghbeigi, "Fluid Catalytic Cracking
  Handbook"; Gary & Handwerk, "Petroleum Refining").
* **Sizing** - riser diameter/height from the vapour molar expansion
  along the reaction coordinate; regenerator diameter/bed height from
  superficial velocity and catalyst residence time; air rate, flue-gas
  composition and SO2 from feed sulfur.
* **Crude linkage** - the feed is built from a crude's VGO (or
  residue) cut, so sulfur, carbon residue, nitrogen, metals and
  characterisation factor all flow from the assay.

Deliberate simplifications (flagged, not hidden): isothermal riser at the
outlet temperature; no catalyst slip; ideal gas; no ZSM-5 or Ecat-metals
model; feed-quality effects on activity/selectivity are *directional
heuristics* (paraffinic feed cracks easier, basic nitrogen poisons acid
sites, aromatic feed makes more coke) with illustrative magnitudes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from .assay import Cut
from .properties import (
    GAS_MW, R_UNIVERSAL, WATER_DENSITY_15C, gas_sensible_enthalpy_kJ_kmol, latent_heat_kJ_kg,
    liquid_cp_kJ_kgK, riazi_daubert_mw, steam_enthalpy_kJ_kg, vapour_cp_kJ_kgK, watson_k,
    api_from_density, BBL_M3,
)

# Standard enthalpies of formation (NIST-JANAF), kJ/mol
DHF_CO2, DHF_CO, DHF_H2O_G = -393.51, -110.53, -241.83
MW_C, MW_H = 12.011, 1.008

# Typical product densities, kg/m3 (used only for volume-% yields)
PRODUCT_DENSITY_KG_M3 = {"lpg": 550.0, "gasoline": 745.0, "lco": 940.0, "slurry": 1040.0}

# Molecular weights used in the riser vapour-expansion calculation
MW_GASOLINE, MW_GAS_LUMP = 105.0, 38.0


_trapz = getattr(np, "trapezoid", None) or np.trapz


# --------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------
@dataclass(frozen=True)
class FccFeed:
    """FCC charge stock.  Build from an assay cut with :meth:`from_cut`."""

    name: str
    density_kg_m3: float
    mabp_C: float
    sulfur_wt: float
    ccr_wt: float
    basic_n_ppm: float = 0.0
    ni_ppm: float = 0.0
    v_ppm: float = 0.0

    @property
    def sg(self) -> float:
        return self.density_kg_m3 / WATER_DENSITY_15C

    @property
    def api(self) -> float:
        return api_from_density(self.density_kg_m3)

    @property
    def watson_k(self) -> float:
        return watson_k(self.mabp_C + 273.15, self.sg)

    @property
    def mw(self) -> float:
        return riazi_daubert_mw(self.mabp_C + 273.15, self.sg)

    @classmethod
    def from_cut(cls, cut: Cut, name: str | None = None) -> "FccFeed":
        """Feed from a crude/slate cut (VGO 370-550 for a VGO FCC, 370+ for a resid FCC).

        Micro carbon residue (ASTM D4530) is taken as equal to Conradson
        carbon (ASTM D189); the two agree closely (D4530 notes this).
        """
        if cut.density_kg_m3 is None or cut.tb_mean_C is None:
            raise ValueError("cut has no material - nothing to crack")
        return cls(
            name=name or f"{cut.name} ({cut.lo_C:g}-{cut.hi_C:g} C)",
            density_kg_m3=cut.density_kg_m3, mabp_C=cut.tb_mean_C,
            sulfur_wt=cut.sulfur_wt or 0.0, ccr_wt=cut.mcr_wt or 0.0,
            basic_n_ppm=cut.basic_n_ppm or 0.0, ni_ppm=cut.ni_ppm or 0.0, v_ppm=cut.v_ppm or 0.0,
        )


def pretreated(
    feed: FccFeed, sulfur_removal: float = 0.90, basic_n_removal: float = 0.60,
    ccr_removal: float = 0.30, metals_removal: float = 0.90, api_gain: float = 2.0,
) -> FccFeed:
    """FCC feed after a VGO hydrotreater (feed pretreat).

    Removal fractions and the API gain (aromatic saturation) are
    *illustrative* moderate-severity values, not licensor data; override to
    match a real unit.  Sizing of the hydrotreater itself is in
    :mod:`refinery_design.hydrotreater`.
    """
    for name, v in (("sulfur_removal", sulfur_removal), ("basic_n_removal", basic_n_removal),
                    ("ccr_removal", ccr_removal), ("metals_removal", metals_removal)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")
    sg_new = 141.5 / (feed.api + api_gain + 131.5)
    return replace(
        feed, name=f"{feed.name} (hydrotreated)", density_kg_m3=sg_new * WATER_DENSITY_15C,
        sulfur_wt=feed.sulfur_wt * (1 - sulfur_removal), basic_n_ppm=feed.basic_n_ppm * (1 - basic_n_removal),
        ccr_wt=feed.ccr_wt * (1 - ccr_removal), ni_ppm=feed.ni_ppm * (1 - metals_removal),
        v_ppm=feed.v_ppm * (1 - metals_removal),
    )


@dataclass(frozen=True)
class FccKinetics:
    """4-lump kinetic constants at 500 degC, per unit cat/oil, 1/s (mass-fraction basis).

    Calibrated to typical published yield ranges (see module docstring);
    override to fit a real unit.
    """

    k_gasoline: float = 0.14243 # feed -> gasoline, 2nd order
    k_gas: float = 0.01662      # feed -> gas (LPG + dry gas)
    k_coke: float = 0.01147     # feed -> coke
    k_g_gas: float = 0.01573    # gasoline -> gas, 1st order
    k_g_coke: float = 0.00072   # gasoline -> coke
    ea_kJ_mol: tuple[float, float, float, float, float] = (60.0, 75.0, 60.0, 80.0, 60.0)
    decay_alpha_1_s: float = 0.30  # catalyst activity exp(-alpha*t)
    t_ref_K: float = 773.15


@dataclass(frozen=True)
class FccOperation:
    feed_rate_kg_s: float
    riser_outlet_C: float = 530.0
    feed_preheat_C: float = 250.0
    riser_residence_s: float = 2.5
    riser_outlet_P_kPa_g: float = 200.0
    dispersion_steam_wt: float = 0.02          # kg steam / kg feed
    stripping_steam_kg_per_t_cat: float = 2.5
    steam_C: float = 250.0
    steam_P_kPa_abs: float = 400.0
    regen_P_kPa_g: float = 220.0
    air_inlet_C: float = 180.0
    combustion_mode: str = "full"              # "full" or "partial"
    excess_air_frac: float | None = None       # default: 0.10 full, 0.0 partial
    co2_co_ratio: float | None = None          # default: 200 full, 1.5 partial
    catalyst_cp_kJ_kgK: float = 1.13           # ~0.27 Btu/lb-F
    catalyst_activity: float = 1.0             # 1 = fresh-equilibrium reference
    heat_of_cracking_kJ_kg_per_conv_pct: float = 5.6  # ~420 kJ/kg feed at 75 wt% conversion
    coke_hydrogen_wt_frac: float = 0.06
    coke_desorption_kJ_kg: float = 2300.0
    regen_heat_loss_frac: float = 0.015        # of coke combustion heat
    catalyst_cooler_kJ_kg_feed: float = 0.0    # heat removed by a catalyst cooler
    ccr_to_coke: float = 1.0                   # kg coke per kg CCR (>=1 above ~50% conversion)
    lco_frac_of_unconverted: float = 0.70
    riser_exit_velocity_m_s: float = 20.0
    regen_superficial_velocity_m_s: float = 0.9
    regen_catalyst_residence_min: float = 5.0
    regen_bed_density_kg_m3: float = 550.0
    sulfur_to_h2s: float = 0.40                # fraction of feed S (FCC literature: 35-45%)
    sulfur_to_coke: float = 0.04               # 2-5%
    sulfur_to_gasoline: float = 0.08           # 2-10%


# --------------------------------------------------------------------
# Riser kinetics
# --------------------------------------------------------------------
def _feed_factors(feed: FccFeed, activity: float) -> tuple[float, float]:
    """(crackability multiplier on feed-cracking rates, coke-selectivity multiplier).

    Directional heuristics, illustrative magnitudes: paraffinic feed
    (high Watson K) cracks easier and cokes less; aromatic feed the
    reverse; basic nitrogen neutralises acid sites.
    """
    k = feed.watson_k
    crack = min(1.4, max(0.6, 1.0 + 0.5 * (k - 11.8)))
    coke = min(1.6, max(0.7, 1.0 + 0.6 * (11.8 - k)))
    n_pen = 1.0 / (1.0 + 4.0e-4 * feed.basic_n_ppm)
    return crack * n_pen * activity, coke


def _arrh(k_ref: float, ea_kJ: float, T_K: float, T_ref: float) -> float:
    return k_ref * math.exp(-ea_kJ * 1000.0 / R_UNIVERSAL * (1.0 / T_K - 1.0 / T_ref))


def riser_kinetics(
    feed: FccFeed, riser_outlet_C: float, cat_to_oil: float, residence_s: float,
    kin: FccKinetics = FccKinetics(), activity: float = 1.0, n_points: int = 60,
) -> dict:
    """Integrate the 4-lump riser.  Returns yields (kg/kg feed) and the time profile."""
    T = riser_outlet_C + 273.15
    crack, cokef = _feed_factors(feed, activity)
    ea = kin.ea_kJ_mol
    k1 = _arrh(kin.k_gasoline, ea[0], T, kin.t_ref_K) * crack
    k2 = _arrh(kin.k_gas, ea[1], T, kin.t_ref_K) * crack
    k3 = _arrh(kin.k_coke, ea[2], T, kin.t_ref_K) * crack * cokef
    k4 = _arrh(kin.k_g_gas, ea[3], T, kin.t_ref_K) * crack
    k5 = _arrh(kin.k_g_coke, ea[4], T, kin.t_ref_K) * crack * cokef

    def rhs(t, y):
        y1, y2, y3, y4 = y
        phi = math.exp(-kin.decay_alpha_1_s * t) * cat_to_oil
        r_feed = (k1 + k2 + k3) * y1 * y1 * phi
        return [-r_feed,
                k1 * y1 * y1 * phi - (k4 + k5) * y2 * phi,
                k2 * y1 * y1 * phi + k4 * y2 * phi,
                k3 * y1 * y1 * phi + k5 * y2 * phi]

    t_eval = np.linspace(0.0, residence_s, n_points)
    sol = solve_ivp(rhs, (0.0, residence_s), [1.0, 0.0, 0.0, 0.0], t_eval=t_eval,
                    method="LSODA", rtol=1e-8, atol=1e-10)
    y = sol.y
    return {"t": sol.t, "unconverted": y[0], "gasoline": y[1], "gas": y[2], "coke_cat": y[3]}


# --------------------------------------------------------------------
# Heat balance pieces
# --------------------------------------------------------------------
def _gas_lump_split(riser_outlet_C: float) -> float:
    """LPG share of the (LPG + dry-gas) lump; falls as thermal cracking rises with ROT."""
    return min(0.95, max(0.60, 0.86 - 0.0010 * (riser_outlet_C - 500.0)))


def _riser_heat_demand(feed: FccFeed, op: FccOperation, conv_pct: float, cat_to_oil: float) -> dict:
    """Heat the riser must draw from the catalyst, kJ per kg feed."""
    rot = op.riser_outlet_C
    P_abs = op.riser_outlet_P_kPa_g + 101.325
    tb = feed.mabp_C + 273.15
    dhv_mol = tb * (8.75 + 1.987 * math.log(tb)) * 4.184  # J/mol
    inv_t = 1.0 / tb - R_UNIVERSAL * math.log(P_abs / 101.325) / dhv_mol
    t_vap_C = min(1.0 / inv_t - 273.15, rot)
    cp_l = liquid_cp_kJ_kgK(feed.sg, feed.watson_k, 0.5 * (op.feed_preheat_C + t_vap_C))
    q_liq = cp_l * (t_vap_C - op.feed_preheat_C)
    q_vap = latent_heat_kJ_kg(tb, feed.mw)
    q_sup = vapour_cp_kJ_kgK(0.5 * (t_vap_C + rot)) * (rot - t_vap_C)
    q_rxn = op.heat_of_cracking_kJ_kg_per_conv_pct * conv_pct
    h_out = steam_enthalpy_kJ_kg(rot, P_abs)
    h_in = steam_enthalpy_kJ_kg(op.steam_C, op.steam_P_kPa_abs)
    q_disp = op.dispersion_steam_wt * (h_out - h_in)
    q_strip = (op.stripping_steam_kg_per_t_cat / 1000.0) * cat_to_oil * (h_out - h_in)
    return {"feed_liquid_heating": q_liq, "feed_vaporisation": q_vap, "vapour_superheat": q_sup,
            "reaction": q_rxn, "dispersion_steam": q_disp, "stripping_steam": q_strip}


def _burn(coke_kg_per_kg_feed: float, op: FccOperation, T_regen_C: float, sulfur_to_coke_kg: float) -> dict:
    """Regenerator combustion: heat released, air and flue gas (per kg feed, kmol/kg feed)."""
    full = op.combustion_mode == "full"
    if op.combustion_mode not in ("full", "partial"):
        raise ValueError("combustion_mode must be 'full' or 'partial'")
    excess = op.excess_air_frac if op.excess_air_frac is not None else (0.10 if full else 0.0)
    ratio = op.co2_co_ratio if op.co2_co_ratio is not None else (200.0 if full else 1.5)
    f_co2 = ratio / (1.0 + ratio)

    h_wt = op.coke_hydrogen_wt_frac
    c_kmol = coke_kg_per_kg_feed * (1.0 - h_wt) / MW_C
    h2_kmol = coke_kg_per_kg_feed * h_wt / (2 * MW_H)
    s_kmol = sulfur_to_coke_kg / 32.06  # -> SO2 (its heat, ~0.5% of coke burn, is neglected)

    o2_stoich = c_kmol * (f_co2 + 0.5 * (1.0 - f_co2)) + 0.5 * h2_kmol + s_kmol
    o2_fed = o2_stoich * (1.0 + excess)
    n2 = o2_fed * 79.0 / 21.0
    flue = {"CO2": c_kmol * f_co2, "CO": c_kmol * (1.0 - f_co2), "H2O": h2_kmol,
            "N2": n2, "O2": o2_fed - o2_stoich, "SO2": s_kmol}

    q_burn = 1000.0 * (c_kmol * (f_co2 * -DHF_CO2 + (1.0 - f_co2) * -DHF_CO) + h2_kmol * -DHF_H2O_G)
    T_K = T_regen_C + 273.15
    q_flue = sum(n * gas_sensible_enthalpy_kJ_kmol(sp, T_K) for sp, n in flue.items() if n > 0)
    q_air = (o2_fed * gas_sensible_enthalpy_kJ_kmol("O2", op.air_inlet_C + 273.15)
             + n2 * gas_sensible_enthalpy_kJ_kmol("N2", op.air_inlet_C + 273.15))
    air_kg = o2_fed * GAS_MW["O2"] + n2 * GAS_MW["N2"]
    return {"q_burn": q_burn, "q_flue": q_flue, "q_air": q_air, "flue_kmol": flue,
            "air_kg": air_kg, "co2_co": ratio, "excess": excess}


# --------------------------------------------------------------------
# Solver
# --------------------------------------------------------------------
@dataclass
class FccResult:
    feed: FccFeed
    operation: FccOperation
    regen_temperature_C: float
    cat_to_oil: float
    conversion_wt_pct: float
    yields_wt_pct: dict
    yields_vol_pct: dict
    coke_wt_pct: float
    delta_coke_wt_pct: float
    heat_balance_kJ_per_kg_feed: dict
    riser: dict
    regenerator: dict
    flue_gas: dict
    sulfur_distribution: dict
    gasoline_sulfur_ppm: float
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        y = self.yields_wt_pct
        return (f"{self.feed.name}: conv {self.conversion_wt_pct:.1f} wt%, C/O {self.cat_to_oil:.2f}, "
                f"Tregen {self.regen_temperature_C:.0f} C, coke {self.coke_wt_pct:.2f} wt%, "
                f"gasoline {y['gasoline']:.1f}, LPG {y['lpg']:.1f}, dry gas {y['dry_gas']:.1f}, "
                f"LCO {y['lco']:.1f}, slurry {y['slurry']:.1f}")


def _yields_at(feed: FccFeed, op: FccOperation, kin: FccKinetics, cat_to_oil: float) -> dict:
    """Riser yields (kg/kg feed) at a given cat/oil, including CCR coke."""
    prof = riser_kinetics(feed, op.riser_outlet_C, cat_to_oil, op.riser_residence_s, kin, op.catalyst_activity)
    coke_cat = prof["coke_cat"][-1]
    coke_ccr = op.ccr_to_coke * feed.ccr_wt / 100.0
    # CCR-derived coke is carbon taken out of the unconverted heavy fraction.
    unconv = max(0.0, prof["unconverted"][-1] - coke_ccr)
    gasoline, gas = prof["gasoline"][-1], prof["gas"][-1]
    coke = coke_cat + coke_ccr
    lpg_share = _gas_lump_split(op.riser_outlet_C)
    return {
        "gasoline": gasoline, "lpg": gas * lpg_share, "dry_gas": gas * (1.0 - lpg_share),
        "coke": coke, "lco": unconv * op.lco_frac_of_unconverted,
        "slurry": unconv * (1.0 - op.lco_frac_of_unconverted), "profile": prof,
    }


def _balance(feed: FccFeed, op: FccOperation, kin: FccKinetics, t_regen: float) -> dict:
    """Riser + regenerator balance at a trial regenerator temperature.

    The riser's heat demand fixes cat/oil; the kinetics at that cat/oil
    fix coke; ``residual`` is (heat released + air enthalpy in) minus
    (riser demand + flue-gas sensible + desorption + losses + cooler).
    Conversion (which sets the heat of cracking) and cat/oil are mutually
    dependent, so they are iterated to a fixed point (converges in ~3).
    """
    rot = op.riser_outlet_C
    dt = t_regen - rot
    if dt <= 5.0:
        raise ValueError("regenerator must be hotter than the riser outlet")
    h_out = steam_enthalpy_kJ_kg(rot, op.riser_outlet_P_kPa_g + 101.325)
    h_in = steam_enthalpy_kJ_kg(op.steam_C, op.steam_P_kPa_abs)
    per_co = (op.stripping_steam_kg_per_t_cat / 1000.0) * (h_out - h_in)  # kJ/kg feed per unit C/O
    conv = 75.0
    for _ in range(4):
        demand = _riser_heat_demand(feed, op, conv, 0.0)  # stripping term added via per_co
        q_fixed = sum(demand.values())
        co = q_fixed / (op.catalyst_cp_kJ_kgK * dt - per_co)
        y = _yields_at(feed, op, kin, co)
        conv = 100.0 * (1.0 - y["lco"] - y["slurry"])
    demand = _riser_heat_demand(feed, op, conv, co)
    q_riser = sum(demand.values())
    burn = _burn(y["coke"], op, t_regen, op.sulfur_to_coke * feed.sulfur_wt / 100.0)
    q_desorb = op.coke_desorption_kJ_kg * y["coke"]
    q_loss = op.regen_heat_loss_frac * burn["q_burn"]
    q_out = burn["q_flue"] + q_desorb + q_loss + op.catalyst_cooler_kJ_kg_feed + q_riser
    return dict(co=co, y=y, conv=conv, demand=demand, q_riser=q_riser, burn=burn,
                q_desorb=q_desorb, q_loss=q_loss, residual=burn["q_burn"] + burn["q_air"] - q_out)


def fcc_operate(feed: FccFeed, op: FccOperation, kin: FccKinetics = FccKinetics()) -> FccResult:
    """Solve the coupled riser / regenerator heat balance for the regenerator temperature."""
    lo, hi = op.riser_outlet_C + 40.0, 900.0
    if _balance(feed, op, kin, lo)["residual"] < 0:
        raise ValueError(
            "heat balance cannot close: even with the regenerator only ~40 C above the riser "
            "outlet the coke burn cannot cover the riser demand (feed too light/clean - "
            "torch oil or a hotter feed preheat would be needed).")
    if _balance(feed, op, kin, hi)["residual"] > 0:
        raise ValueError(
            "heat balance cannot close below 900 C: coke make far exceeds the heat demand "
            "(heavy/high-CCR feed - a catalyst cooler, lower cat/oil or a lighter blend is needed; "
            "try FccOperation.catalyst_cooler_kJ_kg_feed).")
    t_regen = brentq(lambda t: _balance(feed, op, kin, t)["residual"], lo, hi, xtol=1e-3)
    return _assemble(feed, op, kin, t_regen, _balance(feed, op, kin, t_regen))


def cooler_duty_for_regen_temperature(
    feed: FccFeed, op: FccOperation, target_regen_C: float, kin: FccKinetics = FccKinetics(),
) -> float:
    """Catalyst-cooler duty (kJ/kg feed) needed to hold the regenerator at ``target_regen_C``.

    For resid FCC: high CCR makes the coke burn overshoot what the riser
    can absorb; a cooler removes the surplus.  With no cooler in ``op`` the
    balance residual at the target temperature is exactly that surplus.
    """
    from dataclasses import replace
    return _balance(feed, replace(op, catalyst_cooler_kJ_kg_feed=0.0), kin, target_regen_C)["residual"]


# --------------------------------------------------------------------
def _assemble(feed: FccFeed, op: FccOperation, kin: FccKinetics, t_regen: float, s: dict) -> FccResult:
    y, co, conv = s["y"], s["co"], s["conv"]
    wt = {k: 100.0 * y[k] for k in ("dry_gas", "lpg", "gasoline", "lco", "slurry", "coke")}
    wt_total = sum(wt.values())
    # closure check on the lumped balance (should be ~100)
    vol = {}
    feed_vol_per_kg = 1.0 / feed.density_kg_m3
    for k, rho in PRODUCT_DENSITY_KG_M3.items():
        vol[k] = 100.0 * y[k] / rho / feed_vol_per_kg
    delta_coke = wt["coke"] / co

    # --- riser hydrodynamics along the reaction coordinate ---
    prof = y["profile"]
    T_K = op.riser_outlet_C + 273.15
    P_Pa = (op.riser_outlet_P_kPa_g + 101.325) * 1000.0
    steam_kmol = op.dispersion_steam_wt / GAS_MW["H2O"]
    unconv_mw = feed.mw * 0.85
    kmol = (prof["unconverted"] / unconv_mw + prof["gasoline"] / MW_GASOLINE
            + prof["gas"] / MW_GAS_LUMP + steam_kmol)  # kmol per kg feed along the riser
    # coke is solid; CCR coke carbon is removed from the vapour (small)
    q_m3_s_per_kg_s = kmol * 1000.0 * R_UNIVERSAL * T_K / P_Pa  # (m3/s) per (kg/s feed)
    q_exit = q_m3_s_per_kg_s[-1] * op.feed_rate_kg_s
    area = q_exit / op.riser_exit_velocity_m_s
    diameter = math.sqrt(4.0 * area / math.pi)
    v_profile = q_m3_s_per_kg_s * op.feed_rate_kg_s / area
    height = float(_trapz(v_profile, prof["t"]))
    cat_circ = co * op.feed_rate_kg_s
    riser = {"diameter_m": diameter, "height_m": height, "inlet_velocity_m_s": float(v_profile[0]),
             "exit_velocity_m_s": float(v_profile[-1]), "catalyst_circulation_kg_s": cat_circ,
             "solids_flux_kg_m2_s": cat_circ / area, "vapour_residence_s": op.riser_residence_s}

    # --- regenerator ---
    burn = s["burn"]
    flue_kmol = burn["flue_kmol"]
    n_flue = sum(flue_kmol.values()) * op.feed_rate_kg_s  # kmol/s
    P_reg = (op.regen_P_kPa_g + 101.325) * 1000.0
    q_flue_m3_s = n_flue * 1000.0 * R_UNIVERSAL * (t_regen + 273.15) / P_reg
    a_reg = q_flue_m3_s / op.regen_superficial_velocity_m_s
    d_reg = math.sqrt(4.0 * a_reg / math.pi)
    inventory_kg = cat_circ * op.regen_catalyst_residence_min * 60.0
    bed_h = inventory_kg / (op.regen_bed_density_kg_m3 * a_reg)
    coke_burn_kg_h = y["coke"] * op.feed_rate_kg_s * 3600.0
    regen = {"diameter_m": d_reg, "dense_bed_height_m": bed_h, "catalyst_inventory_t": inventory_kg / 1000.0,
             "air_rate_kg_s": burn["air_kg"] * op.feed_rate_kg_s, "coke_burn_kg_h": coke_burn_kg_h,
             "flue_gas_m3_s": q_flue_m3_s, "excess_air_frac": burn["excess"], "co2_co_ratio": burn["co2_co"]}
    tot = sum(flue_kmol.values())
    dry = tot - flue_kmol["H2O"]
    flue = {
        "mol_frac_wet": {k: v / tot for k, v in flue_kmol.items() if v > 0},
        "O2_vol_pct_dry": 100.0 * flue_kmol["O2"] / dry,
        "CO_ppmv_dry": 1e6 * flue_kmol["CO"] / dry,
        "SO2_ppmv_dry": 1e6 * flue_kmol["SO2"] / dry,
    }

    # --- sulfur distribution (feed S in kg S per kg feed) ---
    s_feed = feed.sulfur_wt / 100.0
    s_gasoline = op.sulfur_to_gasoline * s_feed
    sdist = {
        "H2S": op.sulfur_to_h2s * s_feed, "coke_SO2": op.sulfur_to_coke * s_feed, "gasoline": s_gasoline,
        "LCO_slurry": max(0.0, s_feed * (1 - op.sulfur_to_h2s - op.sulfur_to_coke - op.sulfur_to_gasoline)),
    }
    gasoline_s_ppm = 1e6 * s_gasoline / y["gasoline"] if y["gasoline"] > 0 else 0.0

    # --- heat balance table ---
    d = s["demand"]
    hb = {**{f"riser: {k.replace('_', ' ')}": v for k, v in d.items()},
          "riser: total demand": s["q_riser"],
          "regen: coke combustion": burn["q_burn"], "regen: air sensible in": burn["q_air"],
          "regen: flue-gas sensible out": burn["q_flue"], "regen: coke desorption": s["q_desorb"],
          "regen: losses": s["q_loss"], "regen: catalyst cooler": op.catalyst_cooler_kJ_kg_feed,
          "residual (closure)": s["residual"]}

    warnings = _checks(feed, op, t_regen, co, conv, wt["coke"], riser, regen, delta_coke)
    return FccResult(feed, op, t_regen, co, conv, wt | {"total": wt_total}, vol, wt["coke"], delta_coke,
                     hb, riser, regen, flue, sdist, gasoline_s_ppm, warnings)


def _checks(feed, op, t_regen, co, conv, coke, riser, regen, dcoke) -> list[str]:
    """Screening flags against commonly cited FCC operating envelopes (illustrative thresholds)."""
    w = []
    if t_regen > 760:
        w.append(f"regenerator {t_regen:.0f} C exceeds ~760 C: catalyst hydrothermal damage / metallurgy limit - consider a catalyst cooler")
    if t_regen < 660:
        w.append(f"regenerator {t_regen:.0f} C is cold: incomplete burn / afterburn risk, coke too low for the heat balance")
    if not 4.0 <= co <= 10.0:
        w.append(f"cat/oil {co:.1f} outside the usual ~4-10 band")
    if not 0.4 <= dcoke <= 1.6:
        w.append(f"delta coke {dcoke:.2f} wt% outside the usual ~0.4-1.6 band")
    if riser["exit_velocity_m_s"] < 15 or riser["exit_velocity_m_s"] > 30:
        w.append(f"riser exit velocity {riser['exit_velocity_m_s']:.0f} m/s outside ~15-30 m/s")
    if feed.ni_ppm + feed.v_ppm > 5.0:
        w.append(f"feed Ni+V {feed.ni_ppm + feed.v_ppm:.1f} ppm: metals passivation / higher catalyst make-up needed")
    if feed.ccr_wt > 1.5:
        w.append(f"feed CCR {feed.ccr_wt:.1f} wt%: resid-type feed; expect a catalyst cooler and a two-stage regenerator")
    if regen["dense_bed_height_m"] > 12.0:
        w.append("dense-bed height > 12 m: revisit regenerator velocity/residence time")
    if regen["dense_bed_height_m"] < 4.0:
        w.append(f"dense-bed height {regen['dense_bed_height_m']:.1f} m is shallow (< 4 m): coke burn may be incomplete - raise catalyst residence time or lower superficial velocity")
    return w


def rot_sweep(feed: FccFeed, op: FccOperation, rots_C: list[float], kin: FccKinetics = FccKinetics()) -> list[FccResult]:
    """Operate the unit across riser outlet temperatures (gasoline-vs-gas trade-off)."""
    from dataclasses import replace
    return [fcc_operate(feed, replace(op, riser_outlet_C=r), kin) for r in rots_C]
