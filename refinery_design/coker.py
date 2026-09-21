"""Delayed coker: yields from carbon residue, and coke-drum sizing.

Yields: Gary & Handwerk ("Petroleum Refining: Technology and Economics")
give the widely used carbon-residue correlations

    coke,  wt% = 1.6 x CCR
    gas (C4-), wt% = 7.8 + 0.144 x CCR

Both were confirmed against secondary literature while building this repo.
The book's naphtha correlation was *not* independently confirmed, so the
liquid remainder is split into naphtha and coker gas oil by an explicit
parameter (``naphtha_frac_of_liquids``) rather than by an unverified
equation.  Gary-Handwerk ignore operating conditions (pressure, recycle);
Volk et al. and later work do better - this is a screening tool.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CokerResult:
    feed_kg_h: float
    ccr_wt: float
    coke_kg_h: float
    gas_kg_h: float
    naphtha_kg_h: float
    gas_oil_kg_h: float
    drum_volume_m3: float

    @property
    def yields_wt_pct(self) -> dict:
        f = self.feed_kg_h / 100.0
        return {"coke": self.coke_kg_h / f, "gas": self.gas_kg_h / f,
                "naphtha": self.naphtha_kg_h / f, "gas_oil": self.gas_oil_kg_h / f}


def delayed_coker(
    feed_kg_h: float, ccr_wt: float, naphtha_frac_of_liquids: float = 0.22,
    fill_time_h: float = 18.0, coke_bulk_density_kg_m3: float = 800.0, drum_fill_frac: float = 0.75,
) -> CokerResult:
    """Coker yields and the coke-drum volume needed to hold one fill cycle.

    Drum defaults (18 h fill, 800 kg/m3 bulk, 75% fill) are typical-range
    assumptions, not vendor data.
    """
    coke_pct = 1.6 * ccr_wt
    gas_pct = 7.8 + 0.144 * ccr_wt
    if coke_pct + gas_pct >= 100.0:
        raise ValueError(f"CCR {ccr_wt} wt% is outside the correlation's range (coke+gas >= 100%)")
    liquids_pct = 100.0 - coke_pct - gas_pct
    naphtha = liquids_pct * naphtha_frac_of_liquids
    coke_kg_h = feed_kg_h * coke_pct / 100.0
    return CokerResult(
        feed_kg_h=feed_kg_h, ccr_wt=ccr_wt, coke_kg_h=coke_kg_h,
        gas_kg_h=feed_kg_h * gas_pct / 100.0, naphtha_kg_h=feed_kg_h * naphtha / 100.0,
        gas_oil_kg_h=feed_kg_h * (liquids_pct - naphtha) / 100.0,
        drum_volume_m3=coke_kg_h * fill_time_h / (coke_bulk_density_kg_m3 * drum_fill_frac),
    )
