"""Safety review of the Paradip-basket refinery: which OISD standards apply, and what the model flags.

OISD standards are sold by OISD and were not read; the list, titles and editions come from OISD's own site. Requirement
details are from secondary summaries and are labelled. This is a pointer and an early-warning screen, NOT a safety case.

Run: python examples/safety_review.py
"""
from refinery_design import safety as sf
from refinery_design.assay import Slate, load_crude
from refinery_design.benchmarks import paradip_blend_fit, paradip_model_refinery
from refinery_design.fcc_modes import modes
from refinery_design.steam_cracker import build_cracker

print("=" * 100)
print("1. WHICH OISD STANDARDS APPLY TO WHICH DESIGN ELEMENT (titles and editions from oisd.gov.in)")
print("=" * 100)
for element, d in sf.DESIGN_MAP.items():
    print(f"\n[{element}]  ({d['basis']})")
    for n in d["oisd"]:
        s = sf.standard(n)
        print(f"   {n:14s} {s['title'][:78]:78s} {s['edition']}")
    print(f"   check: {d['check']}")

R = paradip_model_refinery(True)
fit = paradip_blend_fit()
x = fit["heavy_fraction_vol"]
slate = Slate([(load_crude("upper_zakum"), 1 - x), (load_crude("cold_lake_blend"), x)])
print("\n" + "=" * 100)
print(f"2. FLAGS FOR THE PARADIP-BASKET REFINERY ({slate.name}; TAN {slate.tan:.2f}, S {slate.sulfur_wt:.2f} wt%)")
print("=" * 100)
for f in sf.refinery_review(R, modes(R.fcc.feed, R.fcc.operation), build_cracker(3.0e6), slate):
    print(f"[{f.level.upper():6s}] {f.topic}: {f.message}")
    print(f"         standards: {', '.join(f.standards)}   | basis: {f.basis}")

print("\n" + "=" * 100)
print("3. CRUDE CORROSIVITY ACROSS THE EIGHT ASSAYS (TAN thresholds: crude 0.5, fraction 1.5 mgKOH/g; corrosion above ~232 C)")
print("=" * 100)
for k in ("bakken", "azeri_btc", "qua_iboe", "upper_zakum", "alaska_north_slope", "dalia", "cold_lake_blend", "kearl"):
    c = load_crude(k)
    fl = [f for f in sf.crude_corrosion_flags(c.as_slate())]
    tag = ", ".join(f"{f.topic} [{f.level}]" for f in fl) or "none"
    print(f"  {c.name:20s} TAN {c.tan:4.2f}  S {c.sulfur_wt:4.2f} wt%  -> {tag}")
