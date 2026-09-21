"""Crude and vacuum distillation: material balance and furnace duty.

The crude type sets everything here.  Cut yields come from the assay's TBP
curve for the chosen cut points; quality (density, sulfur, carbon residue,
metals) comes from the assay cuts.  The furnace duty is a screening
estimate: liquid sensible heat from the preheat train exit to the coil
outlet plus latent heat of the vaporised distillate (with overflash),
integrated slice-by-slice over the TBP curve using a constant Watson K
(Gary & Handwerk; Kistiakowsky/Fishtine latent heat, Watson-Nelson cp).

It is not a column simulation: no tray hydraulics, pumparound duties or
pinch-based preheat-train design.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .assay import Crude, Cut, Slate
from .properties import (
    BBL_M3, WATER_DENSITY_15C, latent_heat_kJ_kg, liquid_cp_kJ_kgK, riazi_daubert_mw,
    sg_from_watson_k,
)

LPG_END_C = 36.1  # C4- / C5+ boundary


@dataclass(frozen=True)
class Stream:
    name: str
    cut: Cut
    mass_kg_h: float
    flow_bpd: float

    @property
    def wt_frac(self) -> float:
        return self.cut.wt_frac

    @property
    def vol_frac(self) -> float:
        return self.cut.vol_frac

    @property
    def density_kg_m3(self) -> float | None:
        return self.cut.density_kg_m3

    @property
    def sulfur_kg_h(self) -> float:
        return 0.0 if self.cut.sulfur_wt is None else self.mass_kg_h * self.cut.sulfur_wt / 100.0


@dataclass(frozen=True)
class DistillationResult:
    feed_name: str
    feed_bpd: float
    feed_kg_h: float
    streams: dict[str, Stream]
    furnace_duty_MW: float
    vaporised_wt_frac: float

    def stream(self, name: str) -> Stream:
        return self.streams[name]

    @property
    def mass_closure(self) -> float:
        """Sum of product masses / feed mass (should be 1.0)."""
        return sum(s.mass_kg_h for s in self.streams.values()) / self.feed_kg_h


def distill(
    feed: Crude | Slate,
    throughput_bpd: float,
    naphtha_end_C: float = 150.0,
    kero_end_C: float = 250.0,
    diesel_end_C: float = 370.0,
    vgo_end_C: float = 550.0,
    preheat_C: float = 250.0,
    coil_outlet_C: float = 360.0,
    overflash_wt_frac: float = 0.03,
) -> DistillationResult:
    """Crude unit + vacuum unit material balance and CDU furnace duty.

    ``throughput_bpd`` is crude charge in barrels per day.  Cut points are
    TBP temperatures: ``naphtha_end_C`` .. ``vgo_end_C`` are the CDU
    naphtha/kerosene/diesel end points and the VDU VGO end point.
    """
    if not (LPG_END_C < naphtha_end_C < kero_end_C < diesel_end_C < vgo_end_C):
        raise ValueError("cut points must increase: naphtha < kerosene < diesel < VGO end points")
    slate = feed.as_slate()
    feed_kg_h = throughput_bpd * BBL_M3 * slate.density_kg_m3 / 24.0
    bounds = [
        ("lpg", -50.0, LPG_END_C), ("naphtha", LPG_END_C, naphtha_end_C),
        ("kerosene", naphtha_end_C, kero_end_C), ("diesel", kero_end_C, diesel_end_C),
        ("vgo", diesel_end_C, vgo_end_C), ("vacuum_residue", vgo_end_C, math.inf),
    ]
    streams = {}
    for name, lo, hi in bounds:
        c = slate.cut(lo, hi, name)
        streams[name] = Stream(name, c, mass_kg_h=feed_kg_h * c.wt_frac,
                               flow_bpd=throughput_bpd * c.vol_frac)
    duty, vap = cdu_furnace_duty_MW(slate, feed_kg_h, diesel_end_C, preheat_C, coil_outlet_C, overflash_wt_frac)
    return DistillationResult(slate.name, throughput_bpd, feed_kg_h, streams, duty, vap)


def cdu_furnace_duty_MW(
    slate: Slate, feed_kg_h: float, diesel_end_C: float, preheat_C: float,
    coil_outlet_C: float, overflash_wt_frac: float = 0.03,
) -> tuple[float, float]:
    """Screening estimate of atmospheric-furnace duty and vaporised mass fraction."""
    if coil_outlet_C <= preheat_C:
        raise ValueError("coil outlet must be hotter than the preheat-train exit")
    k = slate.uop_k
    sg_mean = slate.density_kg_m3 / WATER_DENSITY_15C
    cp = liquid_cp_kJ_kgK(sg_mean, k, 0.5 * (preheat_C + coil_outlet_C))
    sensible = cp * (coil_outlet_C - preheat_C)  # kJ/kg feed

    # Latent heat: integrate slice by slice over the vaporised range.
    vap_end = diesel_end_C
    grid = np.arange(-50.0, vap_end + 10.0, 10.0)
    latent = 0.0
    w_total = 0.0
    for a, b in zip(grid[:-1], grid[1:]):
        dw = slate.cum_wt(b) - slate.cum_wt(a)
        if dw <= 0:
            continue
        tb_K = 0.5 * (a + b) + 273.15
        sg = sg_from_watson_k(tb_K, k)
        latent += dw * latent_heat_kJ_kg(tb_K, riazi_daubert_mw(tb_K, sg))
        w_total += dw
    vap_frac = min(1.0, w_total + overflash_wt_frac)
    # overflash is vaporised at the diesel end-point boiling range
    if overflash_wt_frac > 0:
        tb_K = vap_end + 273.15
        latent += overflash_wt_frac * latent_heat_kJ_kg(tb_K, riazi_daubert_mw(tb_K, sg_from_watson_k(tb_K, k)))
    duty_kJ_per_kg = sensible + latent
    return duty_kJ_per_kg * feed_kg_h / 3600.0 / 1000.0, vap_frac
