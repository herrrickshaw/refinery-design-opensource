"""Crude sourcing: what the Indian basket says, the 2026 shock, and local-currency settlement.

Sources: PPAC Ready Reckoner FY2025-26 (Tables 8.1, 8.24); EcoNiti (rupee-settled imports); Outlook Business / MoPNG
(supplier objections); news on Russian crude (confidence tags in data/crude_sourcing.json); live crude snapshot.

Run: python examples/crude_sourcing_study.py
"""
from refinery_design import crude_sourcing as cs, petchem_prices as pp, trade

print("=" * 96)
print("1. REALISED IMPORT PRICE vs THE INDIAN BASKET (PPAC Tables 8.1 and 8.24)")
print("=" * 96)
print(f"{'FY':8s} {'basket':>7s} {'realised':>9s} {'gap $/bbl':>10s} {'bill $bn':>9s} {'gap $bn':>8s}")
for y in ("2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"):
    r = cs.realised_vs_basket(y)
    print(f"{y:8s} {r['basket_usd_bbl']:7.2f} {r['realised_usd_bbl']:9.2f} {r['gap_usd_bbl']:+10.2f} {r['bill_usd_bn']:9.1f} {r['gap_usd_bn']:+8.1f}")
print("Negative = India paid less than the basket. The basket is a benchmark (FOB-type) price, so the gap is net of freight/insurance;\n"
      "it also carries grade mix and timing. FY2023-24 is the widest gap (the discounted-Russian-crude year).")

print("\n" + "=" * 96)
print("2. THE 2026 SHOCK (US-Israel-Iran conflict from 28 Feb 2026, Hormuz disruption)")
print("=" * 96)
for m in ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"):
    print(f"  {m}: Indian basket ${cs.basket_usd_bbl(m):6.2f}/bbl")
s = cs.shock_extra_bill_usd_bn()
print(f"Extra crude bill Mar-Jun 2026 vs the February basket (imports at 1/12 of FY25-26 volume): ${s['total_usd_bn']:.1f} bn")
print(f"  ({', '.join(f'{k[-2:]}: {v:.1f}' for k, v in s['per_month_usd_bn'].items())} $bn/month). PPAC: basket peaked ~$135/bbl in the first week of April.")

print("\n" + "=" * 96)
print("3. LOCAL-CURRENCY SETTLEMENT: scale, feasibility, and what the arithmetic can and cannot say")
print("=" * 96)
r = cs._raw()["rupee_settled"]
print(f"Rupee-settled imports (all goods): Rs {r['fy_rs_crore']['2023-24']:,} cr (FY24) -> Rs {r['fy_rs_crore']['2024-25']:,} cr (FY25) -> Rs {r['fy_rs_crore']['2025-26']:,} cr (FY26); "
      f"Mar-May 2026 alone Rs 1.38 lakh cr (~$14.6 bn, 7.1% of imports); Russian crude Mar-May $17.13 bn.")
print(f"  = {100*cs.rupee_settled_share_of_crude_bill():.1f}% of the FY25-26 crude bill in rupee terms (numerator is ALL imports, not only crude).")
print(f"Value of 1 bp on the whole FY25-26 crude bill (${cs.crude_import('2025-26')['usd_million']/1000:.1f} bn): ${cs.value_of_one_bp_usd_m():.1f} M/yr")
print("Annual saving ($M) if X% of the bill is settled locally at a cost change of B bps (+ = saving):")
grid = {(g["share_switched"], g["bps_saved"]): g["usd_million_per_year"] for g in cs.local_currency_grid()}
bps = (-50, -25, 0, 10, 25, 50)
print("  share  " + "".join(f"{b:>8d}" for b in bps))
for sh in (0.05, 0.10, 0.25, 0.50):
    print(f"  {sh*100:4.0f}%  " + "".join(f"{grid[(sh, b)]:8.0f}" for b in bps))
print("The sign of B is NOT established. MoPNG reported that suppliers passed conversion costs on to IOC (negative B); only a ~2% cost claim for\n"
      "Indian EXPORTERS to the UAE exists, which is not a crude figure. Nothing here is a measured saving.")
print("\nCan the partner recycle the rupees? (India's exports / imports, total trade, FY25-26; Saudi FY24-25)")
for p in cs.partner_feasibility():
    print(f"  {p['country']:13s} self-financing {p['self_financing_ratio']:.2f}   trade gap ${p['trade_gap_usd_bn']:5.1f} bn   crude share (Q1 FY26) {p['crude_share_q1_fy26_pct']}%")

print("\n" + "=" * 96)
print("4. RUSSIAN CRUDE: THE LATEST REPORTING (low-medium confidence, sources conflict)")
print("=" * 96)
n = cs.russia_news()
print(f"Volumes (mb/d): Jul {n['volumes_mbpd']['2026-07']}, Aug {n['volumes_mbpd']['2026-08']} (-{n['august_fall_pct']:.0f}%), Sep first 14 days {n['volumes_mbpd']['2026-09_first_14_days']}; share {n['share_of_india_crude_pct']['2026-07']}% -> {n['share_of_india_crude_pct']['2026-08']}%")
print("August fall: " + "; ".join(n["august_fall_reasons"]))
lo, hi = cs.russia_discount_range()
print(f"Discount to Brent reported anywhere in 2026: {lo:+.0f} to {hi:+.1f} $/bbl (they conflict: July '>$10 discount' vs August 'parity or slight premium').")
snap = pp.crude_snapshot(); u = cs.urals_regime(snap["urals"], snap["brent"])
print(f"Live 21-Sep-2026: Urals ${snap['urals']} vs Brent ${snap['brent']} = {u['urals_minus_brent']:+.2f} ({u['regime']}); Dubai ${snap['dubai']} = {snap['dubai']-snap['brent']:+.2f} over Brent; WTI {snap['wti']-snap['brent']:+.2f}")
print(f"Freight: Novorossiysk->India ~${n['freight_usd_bbl']['Novorossiysk to India west coast (Suezmax)']:.0f}/bbl vs Baltic ~${n['freight_usd_bbl']['Baltic ports']:.0f}. Payment currency for Russian crude: not found in any source.")

print("\n" + "=" * 96)
print("5. WHICH CRUDE IS WORTH WHAT IN A PARADIP-TYPE REFINERY (assays + PPAC FY25-26 cracks at today's Brent)")
print("=" * 96)
deck = trade.RebasedTradeDeck("2025-26", snap["brent"])
rows = cs.crude_relative_values(deck, throughput_bpd=200_000)
print(f"{'crude':20s} {'API':>5s} {'S wt%':>6s} {'net $/bbl':>10s} {'vs Azeri BTC':>13s}")
for x in rows:
    print(f"{x['name']:20s} {x['api']:5.1f} {x['sulfur_wt']:6.2f} {x['net_realisation_usd_bbl']:10.2f} {x['value_vs_reference_usd_bbl']:+13.2f}")
print(f"Market spreads vs Brent today: Dubai {snap['dubai']-snap['brent']:+.1f}, WTI {snap['wti']-snap['brent']:+.1f}, Urals {snap['urals']-snap['brent']:+.1f}. "
      "A sour Gulf crude (Upper Zakum proxy) is worth\nless in this refinery than a Brent-linked medium/light crude, yet Dubai-linked barrels are priced above Brent - before freight.")
