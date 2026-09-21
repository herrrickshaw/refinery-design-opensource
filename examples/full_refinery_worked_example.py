"""Crude types -> whole-refinery yields: the same refinery, eight different crudes.

The point of the example: a refinery's product slate, its FCC's health and its
coker's load are set by the crude.  Each of the eight real published assays is
run through the same 200 kbpd configuration (CDU/VDU + FCC on VGO + delayed
coker on vacuum residue) and compared, then a blend is examined.

Run: python examples/full_refinery_worked_example.py
"""
from __future__ import annotations

from refinery_design.assay import Slate, available_crudes, load_crude
from refinery_design.flowsheet import refine

BPD = 200_000

print("=" * 108)
print(f"ONE REFINERY, EIGHT CRUDES  ({BPD:,} bpd, CDU/VDU + FCC + delayed coker)")
print("=" * 108)
print(f"{'crude':20s} {'API':>5s} {'S wt%':>6s} {'TAN':>5s}  {'type':32s} "
      f"{'light':>6s} {'mid-dist':>8s} {'petcoke':>8s} {'FCC conv':>8s} {'Tregen':>7s}")
rows = sorted((load_crude(k) for k in available_crudes()), key=lambda c: -c.api)
for c in rows:
    r = refine(c, BPD)
    p = r.pools_wt_pct()
    cl = c.classification()
    kind = f"{cl['gravity']}/{cl['sulfur']}/{cl['acidity']}"
    conv = f"{r.fcc.conversion_wt_pct:.0f}%" if r.fcc else "-"
    treg = f"{r.fcc.regen_temperature_C:.0f}C" if r.fcc else "-"
    flag = " !" if r.warnings else ""
    print(f"{c.name:20s} {c.api:5.1f} {c.sulfur_wt:6.2f} {c.tan:5.2f}  {kind:32s} "
          f"{r.light_product_yield_wt_pct:5.1f}% {p['middle_distillate']:7.1f}% {p['petcoke']:7.1f}% "
          f"{conv:>8s} {treg:>7s}{flag}")
print("  light = LPG + gasoline-range + middle distillate, wt% of crude; '!' = FCC screening warning")

print("\n" + "=" * 108)
print("BLENDING: what does heavy crude do to a light-sweet base (Azeri BTC)?")
print("=" * 108)
base = load_crude("azeri_btc")
heavy = load_crude("cold_lake_blend")
for frac in (0.0, 0.15, 0.30, 0.50):
    s = Slate([(base, 1 - frac), (heavy, frac)]) if frac else base.as_slate()
    r = refine(s, BPD)
    p = r.pools_wt_pct()
    cl = s.classification()
    print(f"{frac*100:4.0f}% Cold Lake: API {s.api:5.1f}  S {s.sulfur_wt:4.2f} wt%  TAN {s.tan:4.2f}  "
          f"{cl['gravity']}/{cl['sulfur']}/{cl['acidity']:8s} | light {r.light_product_yield_wt_pct:5.1f}%  "
          f"petcoke {p['petcoke']:5.1f}%  FCC Tregen {r.fcc.regen_temperature_C:4.0f} C"
          f"{'  <- exceeds ~760 C limit' if r.fcc.regen_temperature_C > 760 else ''}")

print("\n" + "=" * 108)
print("DETAIL: Upper Zakum (medium-sour) refinery balance")
print("=" * 108)
r = refine(load_crude("upper_zakum"), BPD)
d = r.distillation
print(f"Crude unit furnace duty: {d.furnace_duty_MW:.0f} MW ({d.vaporised_wt_frac*100:.0f} wt% vaporised)")
print(f"{'stream':16s} {'wt%':>6s} {'bpd':>9s} {'density':>8s} {'S wt%':>6s}")
for n, s in d.streams.items():
    print(f"{n:16s} {s.wt_frac*100:6.1f} {s.flow_bpd:9,.0f} {s.density_kg_m3:8.0f} {s.cut.sulfur_wt or 0:6.2f}")
print(f"\nFCC: {r.fcc.summary()}")
print(f"Delayed coker: coke {r.coker.yields_wt_pct['coke']:.1f} wt%, gas {r.coker.yields_wt_pct['gas']:.1f} wt%, "
      f"drum volume {r.coker.drum_volume_m3:,.0f} m3")
print(f"Mass closure: {r.mass_closure:.6f}   Nelson index (modelled units): {r.complexity():.2f}")
print("\nProduct pools, wt% of crude:")
for k, v in r.pools_wt_pct().items():
    print(f"  {k:18s} {v:6.2f}")
