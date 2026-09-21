"""Crude slate -> CDU/VDU -> FCC (on VGO) + delayed coker (on vacuum residue)
-> product pools.  A whole-refinery mass balance, chaining every module.

Pools (all wt% of crude charge, before hydrotreating; hydrotreating adds a
little hydrogen and removes H2S, reported separately):

* ``lpg``                 crude LPG + FCC LPG
* ``gasoline_range``      straight-run naphtha + FCC gasoline + coker naphtha
* ``middle_distillate``   kerosene + diesel + FCC LCO + coker gas oil
* ``fuel_gas``            FCC dry gas + coker gas
* ``petcoke``             delayed-coker coke
* ``fcc_coke_burned``     coke burned in the FCC regenerator (leaves as flue gas)
* ``slurry``              FCC slurry oil (black oil)
* ``vgo_unconverted``     VGO sold as heavy fuel/feed when there is no FCC (black oil)
* ``vacuum_residue``      only if there is no coker

The FCC is sized for *all* the VGO; if the heat balance cannot close the
error is surfaced rather than papered over.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .assay import Crude, Slate
from .coker import CokerResult, delayed_coker
from .complexity import nelson_complexity
from .distillation import DistillationResult, distill
from .fcc import FccFeed, FccKinetics, FccOperation, FccResult, fcc_operate, pretreated
from .hydrotreater import HydrotreaterResult, hydrotreat
from .properties import BBL_M3


@dataclass(frozen=True)
class RefineryConfig:
    fcc: bool = True
    coker: bool = True
    naphtha_end_C: float = 150.0
    kero_end_C: float = 250.0
    diesel_end_C: float = 370.0
    vgo_end_C: float = 550.0
    fcc_operation: FccOperation | None = None  # feed_rate is overwritten from the VGO flow
    vgo_hydrotreat: bool = False               # pretreat the FCC feed (illustrative severity, see fcc.pretreated)
    vgo_ht_sulfur_removal: float = 0.90


@dataclass
class RefineryResult:
    slate_name: str
    throughput_bpd: float
    distillation: DistillationResult
    fcc: FccResult | None
    coker: CokerResult | None
    vgo_hydrotreater: HydrotreaterResult | None = None
    pools_kg_h: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def feed_kg_h(self) -> float:
        return self.distillation.feed_kg_h

    def pools_wt_pct(self) -> dict:
        return {k: 100.0 * v / self.feed_kg_h for k, v in self.pools_kg_h.items()}

    @property
    def mass_closure(self) -> float:
        return sum(self.pools_kg_h.values()) / self.feed_kg_h

    @property
    def light_product_yield_wt_pct(self) -> float:
        """LPG + gasoline-range + middle distillate, wt% of crude."""
        p = self.pools_wt_pct()
        return p["lpg"] + p["gasoline_range"] + p["middle_distillate"]

    @property
    def middle_distillate_yield_wt_pct(self) -> float:
        return self.pools_wt_pct()["middle_distillate"]

    @property
    def black_oil_yield_wt_pct(self) -> float:
        p = self.pools_wt_pct()
        return p["slurry"] + p["vacuum_residue"] + p["vgo_unconverted"]

    def complexity(self, factors: str = "1998") -> float:
        """Nelson index of this configuration (feed masses; CDU = crude mass)."""
        d = self.distillation
        vr = d.stream("vacuum_residue").mass_kg_h
        vgo = d.stream("vgo").mass_kg_h
        units = {"vacuum": vr + vgo}
        if self.fcc:
            units["fcc"] = vgo
        if self.coker:
            units["thermal"] = vr
        return nelson_complexity(d.feed_kg_h, units, factors)


def refine(feed: Crude | Slate, throughput_bpd: float, cfg: RefineryConfig = RefineryConfig()) -> RefineryResult:
    """Run the whole flowsheet for a crude or slate at ``throughput_bpd``."""
    dist = distill(feed, throughput_bpd, cfg.naphtha_end_C, cfg.kero_end_C, cfg.diesel_end_C, cfg.vgo_end_C)
    S = dist.streams
    warnings: list[str] = []
    pools = {"lpg": S["lpg"].mass_kg_h, "gasoline_range": S["naphtha"].mass_kg_h,
             "middle_distillate": S["kerosene"].mass_kg_h + S["diesel"].mass_kg_h,
             "fuel_gas": 0.0, "petcoke": 0.0, "fcc_coke_burned": 0.0, "slurry": 0.0, "vacuum_residue": 0.0,
             "vgo_unconverted": 0.0}

    fcc_res = None
    vgo_ht = None
    vgo_kg_h = S["vgo"].mass_kg_h
    if cfg.fcc:
        base = cfg.fcc_operation or FccOperation(feed_rate_kg_s=1.0)
        from dataclasses import replace
        op = replace(base, feed_rate_kg_s=vgo_kg_h / 3600.0)
        feed_vgo = FccFeed.from_cut(S["vgo"].cut, f"{dist.feed_name} VGO")
        if cfg.vgo_hydrotreat:
            treated = pretreated(feed_vgo, sulfur_removal=cfg.vgo_ht_sulfur_removal)
            vgo_ht = hydrotreat(vgo_kg_h, feed_vgo.density_kg_m3, feed_vgo.sulfur_wt, treated.sulfur_wt * 1e4,
                                service="vgo", nitrogen_ppm_in=feed_vgo.basic_n_ppm * 2.5, nitrogen_removal=0.6)
            feed_vgo = treated
        fcc_res = fcc_operate(feed_vgo, op)
        warnings += [f"FCC: {w}" for w in fcc_res.warnings]
        y = fcc_res.yields_wt_pct
        pools["lpg"] += vgo_kg_h * y["lpg"] / 100.0
        pools["gasoline_range"] += vgo_kg_h * y["gasoline"] / 100.0
        pools["middle_distillate"] += vgo_kg_h * y["lco"] / 100.0
        pools["fuel_gas"] += vgo_kg_h * y["dry_gas"] / 100.0
        pools["slurry"] += vgo_kg_h * y["slurry"] / 100.0
        pools["fcc_coke_burned"] += vgo_kg_h * y["coke"] / 100.0
    else:
        pools["vgo_unconverted"] += vgo_kg_h   # heavy fuel-grade stream, not diesel

    coker_res = None
    vr = S["vacuum_residue"]
    if cfg.coker:
        ccr = vr.cut.mcr_wt or 0.0
        coker_res = delayed_coker(vr.mass_kg_h, ccr)
        pools["petcoke"] += coker_res.coke_kg_h
        pools["fuel_gas"] += coker_res.gas_kg_h
        pools["gasoline_range"] += coker_res.naphtha_kg_h
        pools["middle_distillate"] += coker_res.gas_oil_kg_h
    else:
        pools["vacuum_residue"] += vr.mass_kg_h
    return RefineryResult(dist.feed_name, throughput_bpd, dist, fcc_res, coker_res, vgo_ht, pools, warnings)
