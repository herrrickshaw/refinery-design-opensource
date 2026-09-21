"""Hydrotreating: sulfur removal, hydrogen consumption and reactor volume.

Method
------
* Hydrodesulfurisation follows an n-th order rate law in sulfur
  (apparent order 1.5 is the usual choice for middle distillate; Froment
  et al., Topsoe/Axens process literature), so the space velocity needed
  scales with how deep the sulfur cut is:

      1/LHSV = [S_out^(1-n) - S_in^(1-n)] / (k (n-1))

  ``k`` is set per service by a *reference operating point* (a feed sulfur,
  product sulfur and LHSV that a licensor's published operating window
  would bracket).  These reference points are typical-range assumptions,
  not vendor data - override ``HydrotreaterService`` to match a real
  unit.  Temperature is held constant (no activation-energy term).
* Chemical hydrogen: ``h2_per_s`` mol H2 per mol S removed (2-4 covers
  mercaptan/thiophenic/benzothiophenic sulfur; 3 is the mid value) plus
  ``h2_per_n`` per mol N; a fraction of total makeup is lost to solution
  and purge.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .properties import BBL_M3

MW_S, MW_H2, MW_N, MW_H2S = 32.06, 2.016, 14.007, 34.08
NM3_PER_KMOL = 22.414


@dataclass(frozen=True)
class HydrotreaterService:
    name: str
    ref_s_in_wt: float     # reference feed sulfur, wt%
    ref_s_out_ppm: float   # reference product sulfur, ppm
    ref_lhsv: float        # LHSV (1/h) at the reference point
    order: float = 1.5     # apparent HDS reaction order
    recycle_gas_Nm3_m3: float = 300.0
    catalyst_bulk_density_kg_m3: float = 700.0


SERVICES = {
    "naphtha": HydrotreaterService("naphtha", 0.05, 0.5, 5.0, 1.0, 100.0),
    "kerosene": HydrotreaterService("kerosene", 0.20, 10.0, 3.0, 1.2, 200.0),
    "diesel": HydrotreaterService("diesel", 1.00, 10.0, 1.5, 1.5, 300.0),
    "vgo": HydrotreaterService("vgo", 2.00, 1000.0, 1.0, 1.5, 500.0),
}


@dataclass(frozen=True)
class HydrotreaterResult:
    service: str
    feed_kg_h: float
    feed_bpd: float
    s_in_ppm: float
    s_out_ppm: float
    lhsv_1_h: float
    reactor_volume_m3: float
    catalyst_t: float
    sulfur_removed_kg_h: float
    h2s_kg_h: float
    h2_chemical_kg_h: float
    h2_makeup_kg_h: float
    h2_makeup_Nm3_m3: float
    recycle_gas_Nm3_h: float


def required_lhsv(service: HydrotreaterService, s_in_wt: float, s_out_ppm: float) -> float:
    """LHSV (1/h) needed to take ``s_in_wt`` to ``s_out_ppm`` in this service."""
    n = service.order
    s_ref_in = service.ref_s_in_wt / 100.0
    s_ref_out = service.ref_s_out_ppm / 1e6
    s_in, s_out = s_in_wt / 100.0, s_out_ppm / 1e6
    if s_out >= s_in:
        raise ValueError("product sulfur must be below feed sulfur")
    if n == 1.0:
        f = lambda a, b: math.log(a / b)
    else:
        f = lambda a, b: (b ** (1.0 - n) - a ** (1.0 - n)) / (n - 1.0)
    k = f(s_ref_in, s_ref_out) * service.ref_lhsv
    return k / f(s_in, s_out)


def hydrotreat(
    feed_kg_h: float, density_kg_m3: float, sulfur_wt_in: float, product_sulfur_ppm: float,
    service: str | HydrotreaterService = "diesel", nitrogen_ppm_in: float = 0.0,
    nitrogen_removal: float = 0.9, h2_per_s_mol: float = 3.0, h2_per_n_mol: float = 5.0,
    h2_loss_frac: float = 0.25, extra_h2_Nm3_m3: float = 0.0,
) -> HydrotreaterResult:
    """Size a hydrotreater and its hydrogen demand.

    ``extra_h2_Nm3_m3`` adds aromatics/olefin saturation hydrogen (Nm3 H2 per
    m3 feed) on top of the desulfurisation and denitrogenation stoichiometry.
    """
    svc = SERVICES[service] if isinstance(service, str) else service
    lhsv = required_lhsv(svc, sulfur_wt_in, product_sulfur_ppm)
    q_m3_h = feed_kg_h / density_kg_m3
    volume = q_m3_h / lhsv
    s_in_kg = feed_kg_h * sulfur_wt_in / 100.0
    s_out_kg = feed_kg_h * product_sulfur_ppm / 1e6
    s_removed = s_in_kg - s_out_kg
    n_removed = feed_kg_h * nitrogen_ppm_in / 1e6 * nitrogen_removal
    h2_chem_kmol = h2_per_s_mol * s_removed / MW_S + h2_per_n_mol * n_removed / MW_N
    h2_chem_kg = h2_chem_kmol * MW_H2 + extra_h2_Nm3_m3 * q_m3_h / NM3_PER_KMOL * MW_H2
    h2_makeup_kg = h2_chem_kg / (1.0 - h2_loss_frac)
    return HydrotreaterResult(
        service=svc.name, feed_kg_h=feed_kg_h, feed_bpd=q_m3_h * 24.0 / BBL_M3,
        s_in_ppm=sulfur_wt_in * 1e4, s_out_ppm=product_sulfur_ppm, lhsv_1_h=lhsv,
        reactor_volume_m3=volume, catalyst_t=volume * svc.catalyst_bulk_density_kg_m3 / 1000.0,
        sulfur_removed_kg_h=s_removed, h2s_kg_h=s_removed / MW_S * MW_H2S,
        h2_chemical_kg_h=h2_chem_kg, h2_makeup_kg_h=h2_makeup_kg,
        h2_makeup_Nm3_m3=h2_makeup_kg / MW_H2 * NM3_PER_KMOL / q_m3_h,
        recycle_gas_Nm3_h=svc.recycle_gas_Nm3_m3 * q_m3_h,
    )
