"""FCC rundown streams, gasoline/LCO cut points, distillate mode, and pool shares.

Digital Refining (https://www.digitalrefining.com): LCO +4-6 vol% by lowering the gasoline end point (~5 vol% for
430 -> 380 degF), riser 10-30 degF cooler in distillate mode; conventional FCC propylene 3-5%, high-severity
15-28%; typical FCC gasoline sulfur 1,000-2,000 ppm.

Run: python examples/fcc_rundown.py
"""
from refinery_design import rundown as rd
from refinery_design.assay import load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.fcc import FccFeed, FccOperation, fcc_operate
from refinery_design.flowsheet import refine

feed = FccFeed("reference VGO (K=11.8)", density_kg_m3=928.7, mabp_C=460.0, sulfur_wt=0.9, ccr_wt=0.3)
op = FccOperation(feed_rate_kg_s=100.0)
r = fcc_operate(feed, op)
print("=" * 92)
print(f"FCC RUNDOWN  ({feed.name}, S {feed.sulfur_wt} wt%, conv {r.conversion_wt_pct:.1f} wt%, Tregen {r.regen_temperature_C:.0f} C)")
print("=" * 92)
print(f"{'stream':28s} {'wt%':>6s} {'vol%':>6s} {'density':>8s} {'S ppm':>8s}  note")
for s in rd.rundown(r):
    print(f"{s.name:28s} {s.wt_pct_of_feed:6.1f} {'' if s.vol_pct_of_feed is None else f'{s.vol_pct_of_feed:6.1f}':>6s} "
          f"{'' if s.density_kg_m3 is None else f'{s.density_kg_m3:8.0f}':>8s} {'' if s.sulfur_ppm is None else f'{s.sulfur_ppm:8,.0f}':>8s}  {s.note}")
lo, hi = rd.FCC_GASOLINE_SULFUR_TYPICAL_PPM
print(f"\nGasoline sulfur {r.gasoline_sulfur_ppm:,.0f} ppm vs Digital Refining 'typical' {lo:,.0f}-{hi:,.0f} ppm")

print("\n" + "=" * 92)
print("CUT-POINT SHIFT: lowering the gasoline end point moves heavy naphtha into LCO")
print("=" * 92)
for f in (0, 10, 20, 30, 50):
    g = rd.gasoline_end_point_shift(r, f / 1.8)["yields_wt_pct"]
    print(f"  -{f:2d} degF: gasoline {g['gasoline']:5.1f} wt%   LCO {g['lco']:5.1f} wt%   (+{rd.LCO_GAIN_VOL_PCT_OF_FEED_PER_C*f/1.8:.1f} vol% LCO)")
d = rd.distillate_mode(feed, op)
print(f"\nDistillate mode (riser -11 C and -50 degF end point): LCO +{d['lco_gain_wt_pct']:.1f} wt%, gasoline -{d['gasoline_loss_wt_pct']:.1f} wt%, "
      f"conversion {d['base'].conversion_wt_pct:.1f} -> {d['cooler_riser'].conversion_wt_pct:.1f} wt%")

print("\n" + "=" * 92)
print("POOL SHARES (vol%): FCC gasoline in the gasoline pool, LCO in the diesel pool")
print("=" * 92)
print("  Digital Refining reference (US-style, search summary): ~20% and ~5%")
for name, res in (("Bakken (light sweet)", refine(load_crude("bakken"), 200_000)),
                  ("Alaska North Slope", refine(load_crude("alaska_north_slope"), 200_000)),
                  ("Dalia (medium, high-TAN)", refine(load_crude("dalia"), 200_000)),
                  ("Paradip basket (heavy sour)", paradip_model_refinery())):
    p = rd.pool_shares(res)
    print(f"  {name:28s} FCC gasoline {p['fcc_gasoline_vol_pct_of_gasoline_pool']:5.1f}%   LCO {p['lco_vol_pct_of_diesel_pool']:5.1f}%")
