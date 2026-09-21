"""Should a refinery add propylene -> polypropylene? PPAC/CHT-anchored evaluation.

1. What PPAC and CHT publish: NCI, distillate yield, company GRM, and how weakly GRM tracks NCI.
2. The Paradip-basket flowsheet, with its product prices CALIBRATED to a PPAC-reported GRM.
3. Three propylene routes (conventional recovery, ZSM-5, propylene-mode FCC) feeding a PP unit,
   judged by the break-even PP price - because no propylene/PP price is available to this repo.

Sources: CHT https://cht.gov.in/refinery-complexity-index ; PPAC Ready Reckoner FY2022-23 (https://ppac.gov.in);
OGJ (Paradip units); Paradip PP plant: 680 kt/y, Rs 3,150 crore.

Run: python examples/petrochemical_evaluation.py
"""
from refinery_design import india
from refinery_design.benchmarks import PARADIP_PPAC_DISTILLATE_PCT, paradip_model_refinery
from refinery_design.grm import PriceDeck, calibrate_deck, gross_refining_margin
from refinery_design.petrochemical import (
    PARADIP_IMPLIED_PROPYLENE_WT, PARADIP_PP_CAPEX_USD, PetchemAssumptions, affordable_fcc_capex_usd,
    breakeven_grid, build_option, evaluate,
)

print("=" * 96)
print("1. INDIA: COMPLEXITY (CHT, OGJ 2025) AND MARGINS (PPAC)")
print("=" * 96)
print(f"{'refinery':16s} {'company':6s} {'NCI':>5s} {'MMTPA':>6s} {'distillate FY22-23 %':>21s}")
names = {"Mumbai": None}
for r in india.refineries():
    if r["nci"] is None:
        continue
    key = {("HPCL", "Mumbai"): "HPCL Mumbai", ("BPCL", "Mumbai"): "BPCL Mumbai", ("HPCL", "Visakhapatnam"): "Visakh"}.get(
        (r["company"], r["refinery"]), r["refinery"])
    try:
        d = india.distillate_yield_pct(key, "2022-23")
    except KeyError:
        d = None
    print(f"{r['refinery']:16s} {r['company']:6s} {r['nci']:5.1f} {r['capacity_mmtpa']:6.1f} {'' if d is None else f'{d:21.1f}'}")
print("\nGRM ($/bbl, PPAC Table 4.7) vs capacity-weighted NCI by company:")
w = india.company_nci()
for c in ("IOCL", "BPCL", "HPCL", "CPCL", "MRPL"):
    print(f"  {c:5s} NCI {w[c]:5.2f}   FY21-22 {india.grm_usd_bbl(c, '2021-22'):6.2f}   FY22-23 {india.grm_usd_bbl(c, '2022-23'):6.2f}")
for yr in (None, "2021-22", "2022-23"):
    f = india.grm_nci_fit(yr)
    print(f"  fit ({yr or 'mean of years'}): slope {f['slope_usd_bbl_per_nci']:+.2f} $/bbl per NCI point, r = {f['r']:.2f}, n = {f['n']}")
print("  -> the sign says complexity earns margin; r and n say do not lean on it.")

print("\n" + "=" * 96)
print("2. PARADIP-BASKET FLOWSHEET (15 mtpa, VGO hydrotreated) AND PPAC-CALIBRATED PRICES")
print("=" * 96)
r = paradip_model_refinery(vgo_hydrotreat=True)
ppac = sum(PARADIP_PPAC_DISTILLATE_PCT.values()) / len(PARADIP_PPAC_DISTILLATE_PCT)
print(f"Modelled LPG+gasoline+middle-distillate yield {r.light_product_yield_wt_pct:.1f} wt%   "
      f"(PPAC Paradip distillate yield {ppac:.1f}% mean FY19-FY23; definitions differ)")
decks = {}
for label, crude, target in (("FY2021-22", 79.18, india.grm_usd_bbl("IOCL", "2021-22")),
                             ("FY2022-23", 93.15, india.grm_usd_bbl("IOCL", "2022-23"))):
    d = calibrate_deck(r, PriceDeck(crude), target)
    g = gross_refining_margin(r, d)
    decks[label] = d
    print(f"{label}: Indian basket ${crude:.2f}/bbl, IOCL GRM ${target:.2f}/bbl  ->  implied gasoline crack "
          f"${d.cracks_usd_bbl['gasoline_range']:.1f}, middle-distillate crack ${d.cracks_usd_bbl['middle_distillate']:.1f}/bbl "
          f"(model GRM {g.grm_usd_bbl:.2f}; fuel & loss modelled {g.modelled_fuel_loss_pct:.1f}% + {g.extra_fuel_loss_pct:.1f}% overhead)")

print("\n" + "=" * 96)
print("3. PETROCHEMICAL ADDITION: PROPYLENE -> POLYPROPYLENE")
print("=" * 96)
print(f"Anchor: Paradip PP plant 680 kt/y, Rs 3,150 crore = ${PARADIP_PP_CAPEX_USD/1e6:.0f} M (PPAC FX Rs 69.89/$, FY2018-19); "
      f"its 4.2 Mt/y FCC implies propylene-mode yield {PARADIP_IMPLIED_PROPYLENE_WT:.1f} wt% of feed.")
a = PetchemAssumptions()
print(f"Assumptions (unsourced): PP opex ${a.pp_opex_usd_t:.0f}/t, hurdle {a.hurdle_rate*100:.0f}%, life {a.life_years} y, PP yield {a.pp_yield_t_per_t_propylene}.")
print("No propylene / PP price is available - the decision metric is the BREAK-EVEN PP PRICE.\n")
for label, d in decks.items():
    print(f"--- {label} deck: LPG ${d.product_usd_t('lpg'):.0f}/t, gasoline-range ${d.product_usd_t('gasoline_range'):.0f}/t, "
          f"middle distillate ${d.product_usd_t('middle_distillate'):.0f}/t")
    grid = breakeven_grid(r, d, [900.0, 1100.0, 1300.0, 1500.0], a)
    print(f"{'route':15s} {'propylene':>10s} {'PP kt/y':>8s} {'PP capex $M':>12s} {'forgone $/t PP':>15s} {'break-even PP $/t':>18s}   net $M/y at PP price of 900 / 1100 / 1300 / 1500")
    for mode, v in grid.items():
        o, evs = v["option"], v["evals"]
        print(f"{mode:15s} {o.propylene_wt_pct_of_fcc_feed:9.1f}% {o.pp_t_y/1e3:8.0f} {o.capex_usd/1e6:12.0f} "
              f"{o.forgone_value_usd_y/o.pp_t_y:15.0f} {evs[0].breakeven_pp_price_usd_t:18.0f}   "
              + " / ".join(f"{e.net_usd_y/1e6:6.0f}" for e in evs))
    o = build_option(r, d, "propylene_mode", a)
    print(f"  propylene-mode: FCC-side capex is EXCLUDED above; at PP $1,300/t it could cost up to "
          f"${affordable_fcc_capex_usd(o, 1300.0, a)/1e6:,.0f} M before the option stops paying its capital charge "
          f"(${affordable_fcc_capex_usd(o, 1100.0, a)/1e6:,.0f} M at $1,100/t).")
    o1 = build_option(r, d, "conventional", a)
    print(f"  GRM uplift at PP $1,100/t: " + ", ".join(
        f"{m} {evaluate(build_option(r, d, m, a), 1100.0, a).grm_uplift_usd_bbl:+.2f}" for m in ("conventional", "zsm5", "propylene_mode")) + " $/bbl of crude\n")
print("Nelson index change from any of these: 0.0 (the factor table has no polymer/PP entry).")
