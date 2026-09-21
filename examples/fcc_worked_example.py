"""FCC deep dive: heat balance, riser, regenerator, and the crude behind the feed.

Run: python examples/fcc_worked_example.py
"""
from __future__ import annotations

from dataclasses import replace

from refinery_design.assay import load_crude
from refinery_design.fcc import FccFeed, FccOperation, fcc_operate, riser_kinetics, rot_sweep

crude = load_crude("dalia")   # medium-gravity, high-TAN Angolan crude
feed = FccFeed.from_cut(crude.cut(370, 550, "VGO"), f"{crude.name} VGO (370-550 C)")
op = FccOperation(feed_rate_kg_s=100.0)   # ~ 85 kbpd
r = fcc_operate(feed, op)

print("=" * 78)
print(f"FCC FEED  {feed.name}")
print("=" * 78)
print(f"  API {feed.api:.1f}  Watson K {feed.watson_k:.2f}  MABP {feed.mabp_C:.0f} C  MW {feed.mw:.0f}")
print(f"  S {feed.sulfur_wt:.2f} wt%  CCR {feed.ccr_wt:.2f} wt%  basic N {feed.basic_n_ppm:.0f} ppm  Ni+V {feed.ni_ppm + feed.v_ppm:.1f} ppm")

print("\nOPERATION")
print(f"  ROT {op.riser_outlet_C:.0f} C, feed preheat {op.feed_preheat_C:.0f} C, riser residence {op.riser_residence_s} s")
print(f"  -> regenerator {r.regen_temperature_C:.0f} C, cat/oil {r.cat_to_oil:.2f}, "
      f"conversion {r.conversion_wt_pct:.1f} wt%, coke {r.coke_wt_pct:.2f} wt% (delta coke {r.delta_coke_wt_pct:.2f})")

print("\nYIELDS (wt% / vol% of feed)")
for k in ("dry_gas", "lpg", "gasoline", "lco", "slurry", "coke"):
    v = r.yields_vol_pct.get(k)
    print(f"  {k:10s} {r.yields_wt_pct[k]:6.2f}   {'' if v is None else f'{v:6.2f}'}")

print("\nHEAT BALANCE (kJ/kg feed)")
for k, v in r.heat_balance_kJ_per_kg_feed.items():
    print(f"  {k:34s} {v:9.1f}")

print("\nRISER")
for k, v in r.riser.items():
    print(f"  {k:28s} {v:10.2f}")
print("\nREGENERATOR")
for k, v in r.regenerator.items():
    print(f"  {k:28s} {v:10.2f}")
print(f"\nFLUE GAS  O2 {r.flue_gas['O2_vol_pct_dry']:.1f} vol% dry, CO {r.flue_gas['CO_ppmv_dry']:.0f} ppmv, "
      f"SO2 {r.flue_gas['SO2_ppmv_dry']:.0f} ppmv dry")
print(f"FCC gasoline sulfur ~{r.gasoline_sulfur_ppm:.0f} ppm (before post-treatment)")
for w in r.warnings:
    print("  !", w)

print("\n" + "=" * 78)
print("RISER OUTLET TEMPERATURE SWEEP (same feed)")
print("=" * 78)
print(f"{'ROT C':>6s} {'conv':>6s} {'C/O':>5s} {'Tregen':>7s} {'gasoline':>9s} {'LPG':>6s} {'dry gas':>8s} {'coke':>6s}")
for x in rot_sweep(feed, op, [500, 515, 530, 545, 560]):
    y = x.yields_wt_pct
    print(f"{x.operation.riser_outlet_C:6.0f} {x.conversion_wt_pct:6.1f} {x.cat_to_oil:5.2f} {x.regen_temperature_C:7.0f} "
          f"{y['gasoline']:9.1f} {y['lpg']:6.1f} {y['dry_gas']:8.1f} {y['coke']:6.2f}")

print("\n" + "=" * 78)
print("OVER-CRACKING: gasoline vs catalyst circulation at fixed riser (kinetics only)")
print("=" * 78)
for co in (3, 5, 7, 9, 12, 16, 22):
    p = riser_kinetics(feed, 530, co, 2.5)
    conv = 100 * (1 - p["unconverted"][-1])
    print(f"  C/O {co:2d}: conversion {conv:5.1f}%  gasoline {100*p['gasoline'][-1]:5.1f}%  gas {100*p['gas'][-1]:5.1f}%")
