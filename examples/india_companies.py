"""How Indian refineries ran in FY2015-16 vs FY2025-26, and how their FCCs have changed.

Data: refinery_design/data/india_companies.json (PPAC, IPNG, company annual reports; see docs/INDIA_COMPANIES.md).
Utilisation is DERIVED (throughput / 1-April capacity), not company-reported; capacity marked 'i' is inferred.
"""
from refinery_design import companies as co

f = lambda v, n=1: "   -  " if v is None else f"{v:6.{n}f}"

print("=" * 118)
print("1. THEN vs NOW, by refinery (crude processed MMT, capacity MMTPA, derived utilisation %, distillate yield %)")
print("=" * 118)
print(f"{'refinery':36s} {'cap 15-16':>9s} {'cap 25-26':>9s} {'thr 15-16':>9s} {'thr 25-26':>9s} {'thr chg %':>9s} {'util 15-16':>10s} {'util 25-26':>10s} {'dist 15-16':>10s} {'dist 25-26':>10s}")
for r in co.refineries():
    v = co.then_vs_now(r["id"])
    mark = "i" if v["capacity_inferred_now"] else " "
    print(f"{r['id']:36s} {f(v['capacity_then']):>9s} {f(v['capacity_now'])}{mark:>2s}   {f(v['throughput_then'],2):>9s} {f(v['throughput_now'],2):>9s} {f(v['throughput_change_pct']):>9s} "
          f"{f(v['utilisation_then']):>10s} {f(v['utilisation_now']):>10s} {f(v['distillate_then']):>10s} {f(v['distillate_now']):>10s}")

print("\n" + "=" * 118)
print("2. COMPANY ROLL-UPS (refineries with both throughput and capacity in the year)")
print("=" * 118)
print(f"{'':10s}" + "".join(f"{fy[2:]:>13s}" for fy in ("2015-16", "2018-19", "2020-21", "2022-23", "2024-25", "2025-26")))
for c in ("IOCL", "BPCL", "HPCL", "Reliance", "Nayara", "CPCL", "MRPL", "NRL", "HMEL"):
    cells = []
    for fy in ("2015-16", "2018-19", "2020-21", "2022-23", "2024-25", "2025-26"):
        x = co.company_rollup(c, fy)
        cells.append(f"{x['throughput_mmt']:5.1f}/{x['utilisation_pct'] or 0:5.1f}%{'*' if x['flagged'] else ' '}" if x["throughput_mmt"] else "      -      ")
    print(f"{c:10s}" + "".join(f"{s:>13s}" for s in cells))
print("(throughput MMT / derived utilisation)   * = a refinery above 125% that year: stale capacity basis, roll-up unreliable (Reliance SEZ before FY2018-19)")

print("\n" + "=" * 118)
print("3. FCC-FAMILY UNITS in the data (capacities are lower bounds: many nameplates were never published)")
print("=" * 118)
for kind, d in co.fcc_summary().items():
    o, c = d["operating"], d["coming"]
    print(f"{kind:7s} operating {o['units']:2d} units, known capacity {o['capacity_known_mmtpa']:5.2f} MMTPA ({o['capacity_unknown']} nameplates not found) | "
          f"coming {c['units']} units, known {c['capacity_known_mmtpa']:5.2f} MMTPA ({c['capacity_unknown']} not found)")

print("\n" + "=" * 118)
print("4. FCC CHANGE TIMELINE (documented events only; no FCC yield or operating-mode data was published)")
print("=" * 118)
for e in co.fcc_changes():
    print(f"{e['year']}  {e['refinery']:34s} [{e['kind']:20s}] {e['event']}")

print("\n" + "=" * 118)
print("5. ANNOUNCED PLANS (capex/timing as quoted; sources disagree in places - see the JSON 'plans')")
print("=" * 118)
for p in co.plans():
    print(f"- {p['company']}: {p['project'][:92]}\n    capex: {p.get('capex', 'n/a')[:130]}\n    timing: {p.get('timing', 'n/a')[:130]}")
