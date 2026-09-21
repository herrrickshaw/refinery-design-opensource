"""Propylene / polypropylene price deck and the verdict on each route.

PP: IOCL's own ex-works price lists (Rs/MT, GST extra) at three 2026 dates - a primary source.
Propylene: NO 2026-09 observation exists in anything accessible; only stale/regional snippets, listed below.
Crude: live snapshot (OilPriceAPI) through PPAC's Indian-basket formula (Dubai stands in for Oman).
Cracks: PPAC-calibrated at FY2021-22 (weak) and FY2022-23 (strong) GRMs, re-based to the Sept-2026 crude level.

Run: python examples/petchem_price_deck.py
"""
from dataclasses import replace

from refinery_design import petchem_prices as pp
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.grm import PriceDeck, calibrate_deck
from refinery_design.petrochemical import (
    PROPYLENE_WT, PetchemAssumptions, breakeven_propylene_price_usd_t, build_option, verdict,
)

print("=" * 100)
print("PP PRICE DECK - IOCL ex-works, Thane, basic & cash, GST additional (Rs/MT)")
print("=" * 100)
print(f"{'grade':32s} {'1 Jan':>9s} {'1 Mar':>9s} {'11 Sep':>9s} {'Jan->Mar':>9s} {'Jan->Sep':>9s}")
for g in pp.GRADES:
    a, b, c = (pp.iocl_pp_inr_per_mt(g, d) for d in ("2026-01-01", "2026-03-01", "2026-09-11"))
    print(f"{g:32s} {a:9,.0f} {b:9,.0f} {c:9,.0f} {pp.iocl_pp_change_pct(g, d1='2026-03-01'):8.1f}% {pp.iocl_pp_change_pct(g):8.1f}%")
deck_pp = pp.iocl_deck()
print(f"\n{deck_pp.label}: Rs 154,452/MT at Rs {pp.usd_inr():.2f}/$ = ${deck_pp.pp_usd_t:,.0f}/t (list price, before discounts and freight)")
print("\nPropylene - observations found (all low confidence; NONE for Sept 2026):")
for o in pp.propylene_observations():
    print(f"  {o['date']}  ${o['value']:>5,}/t  {o['market']:15s} {o['source']}")

print("\n" + "=" * 100)
print("VERDICT: PARADIP-BASKET FCC (VGO hydrotreated), PP PRICE = IOCL LIST x REALISATION")
print("=" * 100)
c = pp.crude_snapshot()
crude = pp.indian_basket_snapshot_usd_bbl()
print(f"Crude snapshot {c['date']}: Brent ${c['brent']}, Dubai ${c['dubai']} -> Indian basket ${crude:.2f}/bbl (PPAC formula, Oman~Dubai)")
r = paradip_model_refinery(vgo_hydrotreat=True)
a = PetchemAssumptions()
for label, tgt in (("weak fuel cracks (PPAC FY21-22 GRM $11.25)", 11.25), ("strong fuel cracks (PPAC FY22-23 GRM $19.52)", 19.52)):
    deck = replace(calibrate_deck(r, PriceDeck(79.18), tgt), crude_usd_bbl=crude)
    print(f"\n{label}: LPG ${deck.product_usd_t('lpg'):,.0f}/t  gasoline-range ${deck.product_usd_t('gasoline_range'):,.0f}/t  "
          f"middle distillate ${deck.product_usd_t('middle_distillate'):,.0f}/t")
    print(f"  {'route':15s} {'PP kt/y':>8s} {'break-even PP':>14s} | headroom $/t and net $M/y at realisation 100% / 90% / 80% | propylene-sale BE")
    for mode in PROPYLENE_WT:
        o = build_option(r, deck, mode, a)
        cells = []
        for real in (1.0, 0.9, 0.8):
            v = verdict(o, replace(deck_pp, realisation=real), a)
            cells.append(f"{v.headroom_usd_t:+5.0f} / {v.net_usd_y/1e6:+5.0f}")
        v0 = verdict(o, deck_pp, a)
        print(f"  {mode:15s} {o.pp_t_y/1e3:8.0f} {v0.breakeven_pp_usd_t:14,.0f} | " + "   ".join(cells) +
              f" | ${breakeven_propylene_price_usd_t(o, a):,.0f}/t")
print("\nCaveats: the PP list price is a domestic selling price (includes any import-parity premium) and rose 71% in")
print("2026 alongside crude; cracks are PPAC-year fits re-based to today's crude, not observed 2026 cracks; propylene")
print("prices are unobserved, so the propylene-sale column is a break-even to compare with your own view.")
