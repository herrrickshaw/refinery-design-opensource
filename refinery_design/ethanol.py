"""Ethanol blending and the petrol it displaces.

* PPAC's MS consumption (Table 6.1) is *blended* petrol; production + imports - exports (Tables 4.5, 4.11)
  falls short of it by the ethanol blended.  ``trade.petrol_balance`` exposes that gap and
  ``tests/test_ethanol.py`` checks it against PPAC's own blending percentages.
* Blend fractions are by volume; ethanol (789 kg/m3) is denser than petrol (745 kg/m3, an assumption),
  so a 20% volume blend is ~20.9% of blended mass.

Tender facts (OMC ethanol supply-year tenders) come from news reports, tagged with a confidence level in
``data/ppac_2526.json``; no ESY 2026-27 tender allocation was found.
"""
from __future__ import annotations

from .trade import _raw, petrol_balance

ETHANOL_DENSITY = 789.0   # kg/m3
PETROL_DENSITY = 745.0    # kg/m3 (assumption)


def ethanol_mass_share(blend_vol_frac: float) -> float:
    """Ethanol's share of blended-petrol mass for a volume blend fraction (0-1)."""
    if not 0.0 <= blend_vol_frac < 1.0:
        raise ValueError("blend_vol_frac must be in [0, 1)")
    e = blend_vol_frac * ETHANOL_DENSITY
    return e / (e + (1.0 - blend_vol_frac) * PETROL_DENSITY)


def refinery_petrol_mmt(ms_mmt: float, blend_vol_frac: float) -> float:
    """Refinery-made petrol needed to supply ``ms_mmt`` of blended MS at the given volume blend."""
    return ms_mmt * (1.0 - ethanol_mass_share(blend_vol_frac))


def petrol_displaced_mmt(ms_mmt: float, blend_vol_frac: float) -> float:
    """Petrol a refinery no longer has to make relative to an unblended world."""
    return ms_mmt - refinery_petrol_mmt(ms_mmt, blend_vol_frac)


def blend_step_freed_mmt(ms_mmt: float, from_blend: float, to_blend: float) -> float:
    """Refinery petrol freed by raising the blend from ``from_blend`` to ``to_blend`` at fixed MS demand."""
    return refinery_petrol_mmt(ms_mmt, from_blend) - refinery_petrol_mmt(ms_mmt, to_blend)


def ethanol_crore_litres(petrol_bn_litres: float, blend_vol_frac: float) -> float:
    """Ethanol needed for a petrol volume (billion litres) at a blend: crore litres (1 bn litres = 100 crore)."""
    return petrol_bn_litres * blend_vol_frac * 100.0


def ebp() -> dict:
    return dict(_raw()["ebp"])


def tender() -> dict:
    return dict(_raw()["ethanol_tender"])


def ms_scenarios(ms_mmt: float, blends=(0.0, 0.10, 0.12, 0.20, 0.27, 0.30)) -> list[dict]:
    """Refinery petrol requirement at a range of volume blends (E27/E30 are hypothetical)."""
    return [{"blend_pct": 100 * b, "ethanol_mass_pct": 100 * ethanol_mass_share(b), "refinery_petrol_mmt": refinery_petrol_mmt(ms_mmt, b),
             "displaced_mmt": petrol_displaced_mmt(ms_mmt, b)} for b in blends]


__all__ = ["ethanol_mass_share", "refinery_petrol_mmt", "petrol_displaced_mmt", "blend_step_freed_mmt",
           "ethanol_crore_litres", "ebp", "tender", "ms_scenarios", "petrol_balance"]
