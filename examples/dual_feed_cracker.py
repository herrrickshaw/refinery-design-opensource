"""Dual-feed (naphtha + LPG) cracker: yields from a real propane table, the LPG-share sweep, refinery supply, and the LPG-import catch.

Sources: US patent 5,990,370 (BP Chemicals) Table 1 propane cracking yields; PPAC FY2025-26 (LPG imports 21.3 Mt = 64% of consumption);
IOCL PE/PP price lists (2026); BPCL Bina / IOCL Paradip dual-feed cracker announcements. Butane yields are ASSUMED.

Run: python examples/dual_feed_cracker.py
"""
from refinery_design import dual_feed_cracker as df, petchem_prices as pp, steam_cracker as sc, trade
from refinery_design.benchmarks import paradip_model_refinery

print("=" * 96)
print("1. PROPANE YIELDS: patent Table 1 (per pass) and recycled to extinction")
print("=" * 96)
y = df.per_pass_propane_yields(88.0)
print(f"Per pass at 88% propane conversion (wt%): ethylene {y['ethylene']:.2f}, propylene {y['propylene']:.2f}, methane {y['methane']:.2f}, "
      f"ethane {y['ethane']:.2f}, unconverted propane {y['propane']:.2f}, benzene {y['benzene']:.2f}")
print(f"{'conv %':>7s} {'ethylene':>9s} {'propylene':>10s} {'C4':>5s} {'pygas':>6s} {'fuel oil':>9s} {'fuel gas/other':>15s}   (propane and ethane recycled to extinction)")
for c in (84, 88, 92):
    r = df.propane_yields(c)
    print(f"{c:7d} {r.ethylene:9.1f} {r.propylene:10.1f} {r.c4:5.1f} {r.pygas:6.1f} {r.pyrolysis_fuel_oil:9.1f} {r.fuel_gas_and_other:15.1f}")
n = sc.yields_at(850.0)
print(f"Naphtha @850 C: ethylene {n.ethylene:.1f}, propylene {n.propylene:.1f}, pygas {n.pygas:.1f}, fuel oil {n.pyrolysis_fuel_oil:.1f}  -> propane gives ~{df.propane_yields().ethylene/n.ethylene:.1f}x the ethylene per tonne")
print(f"Butane (ASSUMED, low confidence): ethylene {df.butane_yields().ethylene:.0f} wt%; 50/50 mix -> {df.lpg_yields(0.5).ethylene:.1f} wt%")

snap = pp.crude_snapshot()
deck = trade.RebasedTradeDeck("2025-26", snap["brent"])
pe, prices = pp.iocl_pe_usd_t(), pp.iocl_deck()
print("\n" + "=" * 96)
print("2. LPG-SHARE SWEEP: 4 Mt/y total feed (world-scale ~1.1-1.6 Mt/y ethylene), Sept-2026 prices")
print("=" * 96)
print(f"Feed prices: naphtha ${deck.product_usd_t('naphtha'):,.0f}/t, LPG ${deck.product_usd_t('lpg'):,.0f}/t (import parity); PE ${pe:,.0f}/t, PP ${prices.pp_usd_t:,.0f}/t")
print(f"{'LPG share':>10s} {'ethylene Mt':>12s} {'before capital $M':>18s} {'net $M':>9s} {'$/t feed':>9s} {'break-even PE':>14s}")
for r in df.lpg_share_sweep(4.0e6, deck, pe, prices.pp_usd_t):
    print(f"{r['lpg_share']*100:9.0f}% {r['ethylene_mt']:12.2f} {r['before_capital_usd_m']:18.0f} {r['net_usd_m']:9.0f} {r['margin_per_t_feed']:9.0f} {r['breakeven_pe']:14.0f}")
o = df.build_dual_feed(1.0e6, 3.0e6)
print(f"At 25/75: break-even LPG price ${df.breakeven_lpg_usd_t(o, deck, pe, prices.pp_usd_t):,.0f}/t vs deck ${deck.product_usd_t('lpg'):,.0f}/t "
      f"(PPAC's observed FY25-26 LPG import value was ${trade.unit_value_usd_t('imports', 'lpg', '2025-26'):,.0f}/t, at a $69/bbl basket - a different crude level).")
print("Capex sensitivity, 25/75 4 Mt (net after capital, $M/y): " + ", ".join(
    f"${c}/tpa: {df.evaluate_dual_feed(df.build_dual_feed(1e6, 3e6, a=sc.CrackerAssumptions(capex_usd_per_tpa_at_ref=c)), deck, pe, prices.pp_usd_t, a=sc.CrackerAssumptions(capex_usd_per_tpa_at_ref=c)).net_usd_y/1e6:,.0f}" for c in (1500, 1000, 800)))

R = paradip_model_refinery(True)
print("\n" + "=" * 96)
print("3. THE REFINERY'S OWN SUPPLY (Paradip basket, 15 mtpa)")
print("=" * 96)
r = df.refinery_dual_feed(R, deck, prices, pe)
s, o2, e2 = r["supply"], r["option"], r["evaluation"]
print(f"LPG pool {s['lpg_pool_t_y']/1e3:,.0f} kt/y, of which FCC propylene kept for PP {s['propylene_recovered_t_y']/1e3:,.0f} kt/y -> {s['available_t_y']/1e3:,.0f} kt/y saturated LPG available")
print(f"Naphtha {o2.naphtha_t_y/1e3:,.0f} kt/y + LPG {o2.lpg_t_y/1e3:,.0f} kt/y -> ethylene {o2.ethylene_t_y/1e6:.2f} Mt/y, propylene {o2.propylene_t_y/1e6:.2f} Mt/y; "
      f"cash margin ${e2.margin_before_capital_usd_y/1e6:,.0f} M/y, net ${e2.net_usd_y/1e6:,.0f} M/y (break-even PE ${e2.breakeven_pe_usd_t:,.0f}/t)")
for w in o2.warnings:
    print("  !", w)
for share in (0.5, 0.75):
    rr = df.refinery_dual_feed(R, deck, prices, pe, lpg_share_of_feed=share)
    oo, ee = rr["option"], rr["evaluation"]
    print(f"LPG share {share*100:.0f}%: ethylene {oo.ethylene_t_y/1e6:.2f} Mt/y, cash ${ee.margin_before_capital_usd_y/1e6:,.0f} M, net ${ee.net_usd_y/1e6:,.0f} M; "
          + "; ".join(w for w in oo.warnings if 'imported' in w))
