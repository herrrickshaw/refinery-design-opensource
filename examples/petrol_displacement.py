"""Petrol displaced by ethanol: PPAC data, the FCC secondary mode, and which routes pay.

Sources: PPAC Ready Reckoner FY2025-26 (Tables 4.5, 4.11, 6.1, 6.10) and Industry Consumption Report Jan-2026;
OMC ethanol tender reports; Process Consulting Services, "Mitigating FCC gas plant impacts when increasing reactor LPG
yields" (Digital Refining, PTQ Q2 2023); IOCL PP/PE price lists (2026).

Run: python examples/petrol_displacement.py
"""
from refinery_design import ethanol, petchem_prices as pp, trade
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.fcc_modes import modes
from refinery_design.routes import displaced_by_blend_step, petrol_switch_options

print("=" * 100)
print("1. PETROL IN INDIA (PPAC): consumption is BLENDED petrol; the balance gap is the ethanol")
print("=" * 100)
print(f"{'FY':8s} {'MS cons':>8s} {'MS prod':>8s} {'imports':>8s} {'exports':>8s} {'refinery petrol used':>21s} {'implied ethanol':>16s}")
for y in ("2022-23", "2023-24", "2024-25", "2025-26"):
    b = trade.petrol_balance(y)
    print(f"{y:8s} {b['consumption']:8.1f} {b['production']:8.1f} {b['imports']:8.1f} {b['exports']:8.1f} {b['domestic_refinery_petrol']:21.1f} "
          f"{b['implied_ethanol_mmt']:9.1f} ({b['implied_ethanol_share_pct']:.0f}% of MS mass)")
print(f"PPAC Jan-2026: MS 3.51 MMT (+6.1% y/y), Apr-Jan +6.4%; PPAC EBP: ESY 2024-25 19.24%, ESY 2025-26 (Nov-Mar) 19.99%")
t = ethanol.tender()["esy_2025_26_cycle1"]
print(f"OMC tender ESY 2025-26 cycle 1: need {t['requirement_crore_litres']} crore L, offers {t['offers_crore_litres']} (grain {t['grain_offers']}, sugarcane {t['sugarcane_offers']}); "
      f"ESY 2026-27 expected demand {ethanol.tender()['esy_2026_27_expected']['demand_crore_litres_low']}-{ethanol.tender()['esy_2026_27_expected']['demand_crore_litres_high']} crore L (news; no tender found)")
print("\nRefinery petrol needed at FY25-26 MS demand (42.6 MMT):")
for s in ethanol.ms_scenarios(42.6):
    print(f"  E{s['blend_pct']:.0f}: ethanol {s['ethanol_mass_pct']:4.1f}% of mass, refinery petrol {s['refinery_petrol_mmt']:5.1f} MMT (displaced {s['displaced_mmt']:4.1f})")
print(f"  E12 -> E20 frees {ethanol.blend_step_freed_mmt(42.6, 0.12, 0.20):.1f} MMT/yr nationally; petrol exports rose "
      f"{trade.trade_qty_mmt('exports', 'petrol', '2022-23'):.1f} -> {trade.trade_qty_mmt('exports', 'petrol', '2025-26'):.1f} Mt")

R = paradip_model_refinery(True)
print("\n" + "=" * 100)
print("2. THE FCC SECONDARY MODE (Paradip-basket refinery, VGO hydrotreated)")
print("=" * 100)
print(f"Gasoline-range pool {R.pools_kg_h['gasoline_range']*8400/1e6:,.0f} kt/y; the E12->E20 step displaces {displaced_by_blend_step(R, 42.6):,.0f} kt/y of it.")
print(f"{'mode':14s} {'gasoline':>8s} {'LPG':>6s} {'LCO':>6s} {'C3=':>5s} {'gasoline chg kt/y':>18s} {'WGFR x':>7s}  gas-plant fix")
for m in modes(R.fcc.feed, R.fcc.operation):
    y, g = m.yields_wt_pct, m.gas_plant
    fix = "none needed" if g.wgfr_ratio <= 1 else (f"receiver -{g.receiver_temp_drop_F:.0f} F or +{g.receiver_pressure_needed_psig - 3.5:.1f} psi" if g.receiver_pressure_needed_psig else "beyond paper: new compressor/gas plant")
    print(f"{m.name:14s} {y['gasoline']:8.1f} {y['lpg']:6.1f} {y['lco']:6.1f} {m.propylene_wt_pct:5.1f} {m.gasoline_change_t_y/1e3:18.0f} {g.wgfr_ratio:7.2f}  {fix}")

print("\n" + "=" * 100)
print("3. ROUTES SCREEN at Sept-2026 crude with PPAC FY25-26 trade cracks; PP and PE at IOCL list prices")
print("=" * 100)
deck = trade.RebasedTradeDeck("2025-26", pp.crude_snapshot()["brent"])
print(f"{deck.label}: gasoline ${deck.product_usd_t('gasoline_range'):,.0f}/t, diesel ${deck.product_usd_t('middle_distillate'):,.0f}/t, LPG ${deck.product_usd_t('lpg'):,.0f}/t, naphtha ${deck.product_usd_t('naphtha'):,.0f}/t; "
      f"PP ${pp.iocl_deck().pp_usd_t:,.0f}/t, HDPE ${pp.iocl_pe_usd_t():,.0f}/t")
print(f"{'route':38s} {'gas removed kt/y':>16s} {'fuel $M/y':>10s} {'petchem $M/y':>13s} {'net $M/y':>9s}")
for r in petrol_switch_options(R, deck, pp.iocl_deck(), pe_usd_t=pp.iocl_pe_usd_t()):
    f = lambda v: "" if v is None else f"{v:,.0f}"
    print(f"{r.name:38s} {r.gasoline_removed_kt_y:16,.0f} {r.fuel_margin_usd_m_y:10,.0f} {f(r.petchem_margin_usd_m_y):>13s} {f(r.net_usd_m_y):>9s}   {r.note[:60]}")
print("\n(fuel = change vs the base FCC mode selling LPG/LCO instead of gasoline, LCO at 0.9 x diesel, LCO hydrotreating cost excluded;\n"
      " PP routes net of a capital charge on the PP plant only - FCC-side capex NOT included; all against the same deck.)")
