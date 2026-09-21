"""Crude-oil assays: the crude *types* layer.

Real published assays (ExxonMobil's public downloads - see
``docs/DATA_SOURCES.md`` and ``scripts/build_assay_data.py``) spanning
light-sweet to heavy-sour and high-TAN crudes.  Each ``Crude`` carries the
whole-crude properties, the narrow assay cuts (density, sulfur, nitrogen,
TAN, carbon residue, metals per cut) and a TBP curve.

Any pair of cut points can be requested: yields come from the TBP curve
(so mass and volume close exactly), intensive properties are
mass-weighted over the assay cuts that the requested cut overlaps.
``Slate`` blends crudes by volume; cut yields add, intensive properties
mass-average (sulfur, TAN, ppm metals and carbon residue are all
per-mass quantities, so this is exact, not an approximation).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from .properties import (
    BBL_M3, api_from_density, acid_class, gravity_class, k_class, sulfur_class,
    sg_from_api, watson_k, WATER_DENSITY_15C,
)

DATA_FILE = Path(__file__).parent / "data" / "assays.json"
_C5_START_C = 36.1  # n-pentane normal boiling point; boundary between "C4-" and C5+
INF = math.inf


@dataclass(frozen=True)
class Cut:
    """A boiling-range cut of a crude or slate.

    ``wt_frac`` / ``vol_frac`` are fractions of the parent crude's mass /
    volume.  Intensive properties are ``None`` when the assay does not
    report them for that boiling range.
    """

    name: str
    lo_C: float
    hi_C: float
    wt_frac: float
    vol_frac: float
    density_kg_m3: float | None
    tb_mean_C: float | None
    sulfur_wt: float | None = None
    basic_n_ppm: float | None = None
    total_n_ppm: float | None = None
    tan: float | None = None
    mcr_wt: float | None = None
    ni_ppm: float | None = None
    v_ppm: float | None = None
    uop_k: float | None = None

    @property
    def api(self) -> float | None:
        return None if self.density_kg_m3 is None else api_from_density(self.density_kg_m3)

    @property
    def sg(self) -> float | None:
        return None if self.density_kg_m3 is None else self.density_kg_m3 / WATER_DENSITY_15C


_INTENSIVE = ("sulfur_wt", "basic_n_ppm", "total_n_ppm", "tan", "mcr_wt", "ni_ppm", "v_ppm", "uop_k")


class _TbpMixin:
    """Shared TBP-curve maths; subclasses provide ``_curve()``."""

    def cum_wt(self, T_C: float) -> float:
        """Cumulative wt fraction (0-1) distilled at TBP temperature T_C."""
        return self._interp(T_C, 1)

    def cum_vol(self, T_C: float) -> float:
        return self._interp(T_C, 2)

    def _interp(self, T_C: float, col: int) -> float:
        if T_C == INF:
            return 1.0
        t = self._curve()
        if T_C <= t[0, 0]:
            return 0.0
        if T_C >= t[-1, 0]:
            # Assays extrapolate to ~700 degC (~97% distilled); beyond that,
            # linear approach to 100% at 1000 degC keeps the residue finite.
            last = t[-1, col] / 100.0
            return last + (1.0 - last) * min(1.0, (T_C - t[-1, 0]) / (1000.0 - t[-1, 0]))
        return float(np.interp(T_C, t[:, 0], t[:, col])) / 100.0

    def mean_tb_C(self, lo_C: float, hi_C: float, n: int = 40) -> float:
        """Mass-average boiling temperature of the [lo, hi] cut (degC)."""
        hi = min(hi_C, 800.0)
        lo = max(lo_C, float(self._curve()[0, 0]))
        grid = np.linspace(lo, hi, n + 1)
        w = np.array([self.cum_wt(g) for g in grid])
        dw = np.diff(w)
        if dw.sum() <= 0:
            return 0.5 * (lo + hi)
        mid = 0.5 * (grid[:-1] + grid[1:])
        return float((mid * dw).sum() / dw.sum())


@dataclass
class Crude(_TbpMixin):
    """One crude oil, from a published assay."""

    key: str
    name: str
    origin: str
    whole: dict
    assay_cuts: list[dict]
    tbp: np.ndarray = field(repr=False)  # columns: T_C, cum wt%, cum vol%

    # ---- whole-crude properties ---------------------------------
    @property
    def density_kg_m3(self) -> float:
        return self.whole["density"] * 1000.0

    @property
    def api(self) -> float:
        return self.whole["api"]

    @property
    def sulfur_wt(self) -> float:
        return self.whole["sulfur_wt"]

    @property
    def tan(self) -> float:
        return self.whole.get("tan") or 0.0

    @property
    def ni_ppm(self) -> float:
        return self.whole.get("ni_ppm") or 0.0

    @property
    def v_ppm(self) -> float:
        return self.whole.get("v_ppm") or 0.0

    @property
    def mcr_wt(self) -> float:
        return self.whole.get("mcr_wt") or 0.0

    @property
    def pour_C(self) -> float | None:
        return self.whole.get("pour_C")

    @property
    def uop_k(self) -> float:
        """Whole-crude Watson K from the volume-average boiling point."""
        return watson_k(self.whole["vabp_C"] + 273.15, self.density_kg_m3 / WATER_DENSITY_15C)

    def classification(self) -> dict[str, str]:
        return {
            "gravity": gravity_class(self.api),
            "sulfur": sulfur_class(self.sulfur_wt),
            "acidity": acid_class(self.tan),
            "character": k_class(self.uop_k),
        }

    # ---- TBP / cuts ---------------------------------------------
    def _curve(self) -> np.ndarray:
        return self.tbp

    def _narrow_cuts(self) -> list[dict]:
        """Assay cuts with numeric limits, dropping aggregate cuts (e.g.
        370-FBP) that merely span several narrower ones."""
        cuts = []
        for c in self.assay_cuts:
            lo, hi = _limit(c["start_C"], True), _limit(c["end_C"], False)
            cuts.append({**c, "lo": lo, "hi": hi})
        keep = []
        for c in cuts:
            inner = [d for d in cuts if d is not c and d["lo"] >= c["lo"] and d["hi"] <= c["hi"]]
            if len(inner) < 2:
                keep.append(c)
        return keep

    def cut(self, lo_C: float, hi_C: float, name: str = "") -> Cut:
        """Yield and quality of the cut boiling between ``lo_C`` and ``hi_C``."""
        wt = self.cum_wt(hi_C) - self.cum_wt(lo_C)
        vol = self.cum_vol(hi_C) - self.cum_vol(lo_C)
        density = self.density_kg_m3 * wt / vol if vol > 1e-12 else None
        weights = []
        for c in self._narrow_cuts():
            a, b = max(lo_C, c["lo"]), min(hi_C, c["hi"])
            weights.append(max(0.0, self.cum_wt(b) - self.cum_wt(a)) if b > a else 0.0)
        props = {}
        for key in _INTENSIVE:
            num = den = 0.0
            for c, w in zip(self._narrow_cuts(), weights):
                v = c.get(key)
                if w > 0 and v is not None:
                    num += w * v
                    den += w
            props[key] = num / den if den > 0 else None
        return Cut(name=name or f"{lo_C:g}-{hi_C:g}C", lo_C=lo_C, hi_C=hi_C, wt_frac=wt,
                   vol_frac=vol, density_kg_m3=density,
                   tb_mean_C=self.mean_tb_C(lo_C, hi_C) if wt > 1e-12 else None, **props)

    def as_slate(self) -> "Slate":
        return Slate([(self, 1.0)])


def _limit(v, is_start: bool) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().upper()
    if s == "IBP":
        return -50.0
    if s == "FBP":
        return INF
    if s in ("C4", "C5"):
        return _C5_START_C
    raise ValueError(f"unrecognised cut limit {v!r}")


# --------------------------------------------------------------------
class Slate(_TbpMixin):
    """A volumetric blend of crudes (the crude-unit feed)."""

    def __init__(self, components: list[tuple[Crude, float]]):
        if not components:
            raise ValueError("a slate needs at least one crude")
        total = sum(f for _, f in components)
        if total <= 0:
            raise ValueError("slate fractions must be positive")
        self.components = [(c, f / total) for c, f in components]
        rho = [c.density_kg_m3 for c, _ in self.components]
        self._mass_frac = [x * r for (_, x), r in zip(self.components, rho)]
        m = sum(self._mass_frac)
        self._mass_frac = [w / m for w in self._mass_frac]
        self.name = " + ".join(f"{x*100:.0f}% {c.name}" if len(self.components) > 1 else c.name
                               for c, x in self.components)
        # blended TBP on a common grid
        grid = np.arange(-50.0, 700.1, 5.0)
        wt = sum(w * np.array([c.cum_wt(g) for g in grid]) for (c, _), w in zip(self.components, self._mass_frac))
        vol = sum(x * np.array([c.cum_vol(g) for g in grid]) for c, x in self.components)
        self.tbp = np.column_stack([grid, wt * 100.0, vol * 100.0])

    def _curve(self) -> np.ndarray:
        return self.tbp

    # ---- whole-slate properties ---------------------------------
    @property
    def density_kg_m3(self) -> float:
        return sum(x * c.density_kg_m3 for c, x in self.components)

    @property
    def api(self) -> float:
        return api_from_density(self.density_kg_m3)

    def _mass_avg(self, attr: str) -> float:
        return sum(w * getattr(c, attr) for (c, _), w in zip(self.components, self._mass_frac))

    @property
    def sulfur_wt(self) -> float:
        return self._mass_avg("sulfur_wt")

    @property
    def tan(self) -> float:
        return self._mass_avg("tan")

    @property
    def ni_ppm(self) -> float:
        return self._mass_avg("ni_ppm")

    @property
    def v_ppm(self) -> float:
        return self._mass_avg("v_ppm")

    @property
    def mcr_wt(self) -> float:
        return self._mass_avg("mcr_wt")

    @property
    def uop_k(self) -> float:
        return sum(x * c.uop_k for c, x in self.components)

    def classification(self) -> dict[str, str]:
        return {
            "gravity": gravity_class(self.api),
            "sulfur": sulfur_class(self.sulfur_wt),
            "acidity": acid_class(self.tan),
            "character": k_class(self.uop_k),
        }

    def cut(self, lo_C: float, hi_C: float, name: str = "") -> Cut:
        cuts = [c.cut(lo_C, hi_C) for c, _ in self.components]
        mass = [w * ct.wt_frac for w, ct in zip(self._mass_frac, cuts)]          # per unit slate mass
        vol = [x * ct.vol_frac for (_, x), ct in zip(self.components, cuts)]     # per unit slate volume
        m_tot = sum(mass)
        slate_rho = self.density_kg_m3
        wt_frac = m_tot
        vol_frac = sum(vol)
        density = slate_rho * wt_frac / vol_frac if vol_frac > 1e-12 else None
        props = {}
        for key in _INTENSIVE:
            num = den = 0.0
            for m, ct in zip(mass, cuts):
                v = getattr(ct, key)
                if v is not None and m > 0:
                    num += m * v
                    den += m
            props[key] = num / den if den > 0 else None
        return Cut(name=name or f"{lo_C:g}-{hi_C:g}C", lo_C=lo_C, hi_C=hi_C, wt_frac=wt_frac,
                   vol_frac=vol_frac, density_kg_m3=density,
                   tb_mean_C=self.mean_tb_C(lo_C, hi_C) if wt_frac > 1e-12 else None, **props)

    def as_slate(self) -> "Slate":
        return self


# --------------------------------------------------------------------
@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def available_crudes() -> list[str]:
    return list(_raw()["crudes"])


def load_crude(key: str) -> Crude:
    """Load one of :func:`available_crudes` by key (e.g. ``"dalia"``)."""
    raw = _raw()["crudes"]
    if key not in raw:
        raise KeyError(f"unknown crude {key!r}; available: {', '.join(raw)}")
    d = raw[key]
    return Crude(key=key, name=d["name"], origin=d["origin"], whole=d["whole"],
                 assay_cuts=d["cuts"], tbp=np.array(d["tbp_T_cumwt_cumvol"], dtype=float))


def barrels_to_kg(bbl: float, density_kg_m3: float) -> float:
    return bbl * BBL_M3 * density_kg_m3
