"""Capture numeric outputs of the public API as JSON (floats stored via repr -> exact).

Used to freeze the pre-refactor behaviour: ``python tests/golden/capture.py out.json``
(run against the original code to regenerate ``characterisation.json``).
"""
from __future__ import annotations

import dataclasses
import json
import math
import sys
from dataclasses import replace

import numpy as np

from refinery_design import dual_feed_cracker as df
from refinery_design import petchem_prices as pp
from refinery_design import steam_cracker as sc
from refinery_design import trade
from refinery_design.assay import Slate, available_crudes, load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.fcc import (FccFeed, FccOperation, cooler_duty_for_regen_temperature, fcc_operate, pretreated,
                                 riser_kinetics, rot_sweep)
from refinery_design.flowsheet import RefineryConfig, refine


def plain(o, depth=0):
    """Recursively convert results to JSON-able structures (floats as repr strings)."""
    if depth > 6:
        return "<deep>"
    if isinstance(o, bool) or o is None or isinstance(o, str):
        return o
    if isinstance(o, (int,)):
        return o
    if isinstance(o, (float, np.floating)):
        return "inf" if math.isinf(o) else repr(float(o))
    if isinstance(o, np.ndarray):
        return [plain(x, depth + 1) for x in o.tolist()]
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {f.name: plain(getattr(o, f.name), depth + 1) for f in dataclasses.fields(o)}
    if isinstance(o, dict):
        return {str(k): plain(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [plain(x, depth + 1) for x in o]
    return repr(type(o).__name__)


def capture() -> dict:
    out: dict = {}
    # --- assays: classification, cuts, slate blend -------------------------
    for key in available_crudes():
        c = load_crude(key)
        out[f"assay/{key}"] = {
            "cls": c.classification(), "uop_k": c.uop_k, "api": c.api,
            "cuts": [c.cut(lo, hi) for lo, hi in ((-50, 150), (150, 250), (250, 370), (370, 550), (370, float("inf")), (550, float("inf")))],
        }
    slate = Slate([(load_crude("dalia"), 0.6), (load_crude("bakken"), 0.4)])
    out["assay/slate"] = {"name": slate.name, "cls": slate.classification(), "sulfur": slate.sulfur_wt, "tan": slate.tan,
                          "uop_k": slate.uop_k, "cuts": [slate.cut(370, 550), slate.cut(550, float("inf"))]}
    # --- FCC ---------------------------------------------------------------
    for key in ("bakken", "dalia", "upper_zakum", "cold_lake_blend"):
        try:
            crude = load_crude(key)
        except KeyError:
            continue
        feed = FccFeed.from_cut(crude.cut(370, 550, "VGO"))
        op = FccOperation(feed_rate_kg_s=100.0)
        try:
            out[f"fcc/{key}"] = fcc_operate(feed, op)
        except ValueError as e:
            out[f"fcc/{key}"] = str(e)
        try:
            out[f"fcc_ht/{key}"] = fcc_operate(pretreated(feed), op)
        except ValueError as e:
            out[f"fcc_ht/{key}"] = str(e)
        out[f"fcc_cooler/{key}"] = cooler_duty_for_regen_temperature(feed, op, 730.0)
        out[f"fcc_partial/{key}"] = _try(lambda: fcc_operate(feed, replace(op, combustion_mode="partial")))
    dalia = load_crude("dalia")
    feed = FccFeed.from_cut(dalia.cut(370, 550, "VGO"))
    out["fcc/rot_sweep"] = rot_sweep(feed, FccOperation(feed_rate_kg_s=100.0), [500.0, 520.0, 540.0])
    out["fcc/riser"] = riser_kinetics(feed, 530.0, 6.0, 2.5)
    out["fcc/resid"] = _try(lambda: fcc_operate(FccFeed.from_cut(dalia.cut(370, float("inf"), "AR")),
                                                  FccOperation(feed_rate_kg_s=100.0, catalyst_cooler_kJ_kg_feed=400.0)))
    # --- flowsheet ---------------------------------------------------------
    for key in ("bakken", "dalia"):
        out[f"refine/{key}"] = refine(load_crude(key), 100000.0)
    out["refine/ht"] = refine(slate, 150000.0, RefineryConfig(vgo_hydrotreat=True))
    # --- crackers ----------------------------------------------------------
    snap = pp.crude_snapshot()
    deck = trade.RebasedTradeDeck("2025-26", snap["brent"])
    pe, prices = pp.iocl_pe_usd_t(), pp.iocl_deck()
    for t in (4.0e6, 1.0e6, 2.0e5):
        o = sc.build_cracker(t, 850.0, crude_t_y=1.5e7)
        out[f"sc/build/{t:g}"] = o
        out[f"sc/eval/{t:g}"] = sc.evaluate_cracker(o, deck, pe, prices.pp_usd_t)
    out["sc/eval_naphtha"] = sc.evaluate_cracker(sc.build_cracker(4e6, 820.0), deck, pe, prices.pp_usd_t, naphtha_usd_t=600.0)
    out["sc/bina"] = sc.bina_check()
    out["sc/yields"] = [sc.yields_at(t) for t in (780.0, 820.0, 850.0, 900.0)]
    for nap, lpg in ((1e6, 3e6), (4e6, 0.0), (0.0, 4e6), (2e6, 2e6)):
        o = df.build_dual_feed(nap, lpg, refinery_lpg_t_y=1e6)
        out[f"df/build/{nap:g}/{lpg:g}"] = o
        out[f"df/eval/{nap:g}/{lpg:g}"] = df.evaluate_dual_feed(o, deck, pe, prices.pp_usd_t)
    out["df/sweep"] = df.lpg_share_sweep(4.0e6, deck, pe, prices.pp_usd_t)
    out["df/breakeven_lpg"] = df.breakeven_lpg_usd_t(df.build_dual_feed(1e6, 3e6), deck, pe, prices.pp_usd_t)
    R = paradip_model_refinery(True)
    out["df/refinery"] = df.refinery_dual_feed(R, deck, prices, pe)
    out["df/refinery75"] = df.refinery_dual_feed(R, deck, prices, pe, lpg_share_of_feed=0.75)
    return out


def _try(fn):
    try:
        return fn()
    except ValueError as e:
        return f"ValueError: {e}"


if __name__ == "__main__":
    data = {k: plain(v) for k, v in capture().items()}
    with open(sys.argv[1], "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
    print(f"captured {len(data)} entries")
