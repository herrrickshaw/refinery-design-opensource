"""Interactive refinery conceptual-sizing tool: crude types, crude unit, FCC, hydrotreating, coker.

Run with: streamlit run streamlit_app.py

Real published crude assays (ExxonMobil public downloads) + cited textbook
correlations.  See README.md, docs/METHODOLOGY.md and the disclaimer at the bottom.
"""
from __future__ import annotations

from dataclasses import replace

import pandas as pd
import streamlit as st

from refinery_design.assay import INF, Slate, available_crudes, load_crude
from refinery_design.coker import delayed_coker
from refinery_design.distillation import distill
from refinery_design.fcc import FccFeed, FccKinetics, FccOperation, cooler_duty_for_regen_temperature, fcc_operate, riser_kinetics, rot_sweep
from refinery_design import companies as cos, crude_sourcing as csrc, dual_feed_cracker as dfc, steam_cracker as scr, ethanol as eth, india, petchem_prices as pcp, rundown as rd, safety as sfty, trade as ptrade
from refinery_design.fcc_modes import modes as fcc_modes_fn
from refinery_design.routes import petrol_switch_options
from refinery_design.flowsheet import RefineryConfig, refine
from refinery_design.grm import PriceDeck, calibrate_deck, gross_refining_margin
from refinery_design.petrochemical import PetchemAssumptions, affordable_fcc_capex_usd, build_option, evaluate
from refinery_design.hydrotreater import SERVICES, hydrotreat

st.set_page_config(page_title="Refinery Conceptual Sizing", layout="wide")
st.title("Oil Refinery Design (open-source)")
st.caption(
    "Conceptual sizing from real published crude assays and textbook correlations "
    "(Gary & Handwerk, Sadeghbeigi, Riazi, Nelson). Screening only - see the disclaimer at the bottom "
    "and docs/METHODOLOGY.md for citations."
)

@st.cache_resource
def paradip_model_refinery_dual():
    from refinery_design.benchmarks import paradip_model_refinery
    return paradip_model_refinery(True)


KEYS = available_crudes()
NAMES = {k: load_crude(k).name for k in KEYS}

tab_types, tab_slate, tab_cdu, tab_fcc, tab_ht, tab_ref, tab_india, tab_grm, tab_petrol, tab_dual, tab_cos, tab_src, tab_safe = st.tabs(
    ["Crude types", "Slate & blending", "Crude / vacuum unit", "FCC", "Hydrotreater & coker", "Whole refinery",
     "India: CHT & PPAC", "GRM & petrochemicals", "Petrol & routes", "Dual-feed cracker", "Indian refiners", "Crude sourcing", "Safety"]
)


def slate_from_widgets(prefix: str, defaults: list[str]) -> Slate:
    chosen = st.multiselect("Crudes in the slate", KEYS, default=defaults, format_func=NAMES.get, key=f"{prefix}_sel")
    if not chosen:
        st.stop()
    parts = []
    cols = st.columns(len(chosen))
    for col, k in zip(cols, chosen):
        parts.append((load_crude(k), col.number_input(f"{NAMES[k]} (vol %)", 0.0, 100.0, 100.0 / len(chosen), key=f"{prefix}_{k}")))
    if sum(f for _, f in parts) <= 0:
        st.stop()
    return Slate(parts)


# ---------------------------------------------------------------------
with tab_types:
    st.header("Crude oil types")
    st.caption("Eight real assays from light-sweet to heavy-sour and high-TAN. Classification: DOE-EIA gravity breaks "
               "(31.1 / 22.3 API), sweet <= 0.5 wt% S, high-TAN >= 0.5 mgKOH/g, Watson K.")
    rows = []
    for k in KEYS:
        c = load_crude(k)
        cl = c.classification()
        rows.append({
            "Crude": c.name, "Origin": c.origin, "API": round(c.api, 1), "S wt%": round(c.sulfur_wt, 2),
            "TAN": round(c.tan, 2), "Ni+V ppm": round(c.ni_ppm + c.v_ppm, 1), "CCR wt%": round(c.mcr_wt, 1),
            "Watson K": round(c.uop_k, 2), "Class": f"{cl['gravity']} / {cl['sulfur']} / {cl['acidity']} / {cl['character']}",
            "Naphtha wt%": round(100 * c.cut(36.1, 150).wt_frac, 1), "Middle dist wt%": round(100 * c.cut(150, 370).wt_frac, 1),
            "VGO wt%": round(100 * c.cut(370, 550).wt_frac, 1), "Vac. resid wt%": round(100 * c.cut(550, INF).wt_frac, 1),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    sel = st.multiselect("TBP curves", KEYS, default=["bakken", "dalia", "cold_lake_blend"], format_func=NAMES.get)
    if sel:
        curve = pd.DataFrame({NAMES[k]: pd.Series(load_crude(k).tbp[:, 2], index=load_crude(k).tbp[:, 0]) for k in sel})
        st.line_chart(curve.loc[0:700], x_label="TBP temperature (C)", y_label="cumulative vol % distilled")

# ---------------------------------------------------------------------
with tab_slate:
    st.header("Slate & blending")
    slate = slate_from_widgets("slate", ["azeri_btc", "cold_lake_blend"])
    cl = slate.classification()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("API", f"{slate.api:.1f}"); c2.metric("Sulfur", f"{slate.sulfur_wt:.2f} wt%")
    c3.metric("TAN", f"{slate.tan:.2f} mgKOH/g"); c4.metric("Watson K", f"{slate.uop_k:.2f}")
    st.write(f"**{cl['gravity']} / {cl['sulfur']} / {cl['acidity']} / {cl['character']}**  -  Ni+V {slate.ni_ppm + slate.v_ppm:.1f} ppm, CCR {slate.mcr_wt:.1f} wt%")
    edges = [(-50.0, 36.1, "LPG"), (36.1, 150.0, "Naphtha"), (150.0, 250.0, "Kerosene"), (250.0, 370.0, "Diesel"), (370.0, 550.0, "VGO"), (550.0, INF, "Vacuum residue")]
    cuts = [slate.cut(a, b, n) for a, b, n in edges]
    st.dataframe(pd.DataFrame([{"Cut": c.name, "wt%": round(100 * c.wt_frac, 1), "vol%": round(100 * c.vol_frac, 1),
                                "Density kg/m3": None if c.density_kg_m3 is None else round(c.density_kg_m3),
                                "S wt%": None if c.sulfur_wt is None else round(c.sulfur_wt, 2),
                                "CCR wt%": None if c.mcr_wt is None else round(c.mcr_wt, 1)} for c in cuts]), hide_index=True)

# ---------------------------------------------------------------------
with tab_cdu:
    st.header("Crude & vacuum unit")
    slate = slate_from_widgets("cdu", ["upper_zakum"])
    c1, c2, c3, c4 = st.columns(4)
    bpd = c1.number_input("Crude charge (bpd)", 10_000, 1_000_000, 200_000, step=10_000)
    nap = c2.number_input("Naphtha end point (C)", 100.0, 200.0, 150.0)
    dsl = c3.number_input("Diesel end point (C)", 300.0, 400.0, 370.0)
    vgo = c4.number_input("VGO end point (C)", 480.0, 600.0, 550.0)
    try:
        r = distill(slate, bpd, naphtha_end_C=nap, diesel_end_C=dsl, vgo_end_C=vgo)
        st.metric("Atmospheric furnace duty (screening)", f"{r.furnace_duty_MW:.0f} MW", f"{r.vaporised_wt_frac*100:.0f} wt% vaporised")
        st.dataframe(pd.DataFrame([{"Stream": n, "wt%": round(100 * s.wt_frac, 1), "bpd": round(s.flow_bpd), "kg/h": round(s.mass_kg_h),
                                    "Density": None if s.density_kg_m3 is None else round(s.density_kg_m3),
                                    "S wt%": None if s.cut.sulfur_wt is None else round(s.cut.sulfur_wt, 2)} for n, s in r.streams.items()]), hide_index=True)
    except ValueError as e:
        st.error(str(e))

# ---------------------------------------------------------------------
with tab_fcc:
    st.header("FCC reactor-regenerator")
    st.caption("4-lump riser kinetics (constants calibrated to typical yield ranges) coupled to the regenerator heat balance.")
    src = st.radio("Feed", ["From a crude's VGO / residue cut", "Manual"], horizontal=True)
    if src.startswith("From"):
        slate = slate_from_widgets("fcc", ["dalia"])
        cutname = st.radio("Cut", ["VGO 370-550 C", "Atmospheric residue 370+ C"], horizontal=True)
        cut = slate.cut(370, 550, "VGO") if cutname.startswith("VGO") else slate.cut(370, INF, "AR")
        feed = FccFeed.from_cut(cut, f"{slate.name} {cutname.split()[0]}")
    else:
        m1, m2, m3, m4 = st.columns(4)
        feed = FccFeed("manual feed", m1.number_input("Density kg/m3", 850.0, 1020.0, 920.0), m2.number_input("MABP (C)", 350.0, 650.0, 460.0),
                       m3.number_input("Sulfur wt%", 0.0, 6.0, 0.6), m4.number_input("CCR wt%", 0.0, 12.0, 0.4), 400.0)
    st.write(f"Feed: API {feed.api:.1f}, Watson K {feed.watson_k:.2f}, S {feed.sulfur_wt:.2f} wt%, CCR {feed.ccr_wt:.2f} wt%, "
             f"basic N {feed.basic_n_ppm:.0f} ppm, Ni+V {feed.ni_ppm + feed.v_ppm:.1f} ppm")
    a1, a2, a3, a4 = st.columns(4)
    rate = a1.number_input("Feed rate (kg/s)", 10.0, 500.0, 100.0)
    rot = a2.number_input("Riser outlet T (C)", 480.0, 580.0, 530.0)
    pre = a3.number_input("Feed preheat (C)", 150.0, 380.0, 250.0)
    tau = a4.number_input("Riser residence (s)", 1.0, 5.0, 2.5)
    b1, b2, b3 = st.columns(3)
    mode = b1.selectbox("Regenerator", ["full", "partial"])
    cooler = b2.number_input("Catalyst cooler (kJ/kg feed)", 0.0, 6000.0, 0.0, step=50.0)
    target = b3.number_input("...or size cooler for T_regen (C)", 650.0, 800.0, 720.0)
    op = FccOperation(feed_rate_kg_s=rate, riser_outlet_C=rot, feed_preheat_C=pre, riser_residence_s=tau,
                      combustion_mode=mode, catalyst_cooler_kJ_kg_feed=cooler)
    try:
        r = fcc_operate(feed, op)
    except ValueError as e:
        st.error(str(e))
        try:
            st.info(f"Cooler duty to hold {target:.0f} C: {cooler_duty_for_regen_temperature(feed, op, target):,.0f} kJ/kg feed - enter it above.")
        except ValueError:
            pass
        st.stop()
    for w in r.warnings:
        st.warning(w)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Conversion", f"{r.conversion_wt_pct:.1f} wt%"); k2.metric("Cat/oil", f"{r.cat_to_oil:.2f}")
    k3.metric("Regenerator", f"{r.regen_temperature_C:.0f} C"); k4.metric("Coke", f"{r.coke_wt_pct:.2f} wt%")
    k5.metric("Gasoline S", f"{r.gasoline_sulfur_ppm:,.0f} ppm")
    y1, y2 = st.columns(2)
    with y1:
        st.subheader("Yields")
        st.dataframe(pd.DataFrame({"wt%": {k: round(v, 2) for k, v in r.yields_wt_pct.items()}}))
        st.subheader("Heat balance (kJ/kg feed)")
        st.dataframe(pd.DataFrame({"kJ/kg": {k: round(float(v), 1) for k, v in r.heat_balance_kJ_per_kg_feed.items()}}))
    with y2:
        st.subheader("Riser")
        st.dataframe(pd.DataFrame({"": {k: round(float(v), 2) for k, v in r.riser.items()}}))
        st.subheader("Regenerator")
        st.dataframe(pd.DataFrame({"": {k: round(float(v), 2) for k, v in r.regenerator.items()}}))
        st.write(f"Flue gas: O2 {r.flue_gas['O2_vol_pct_dry']:.1f} vol% dry, CO {r.flue_gas['CO_ppmv_dry']:.0f} ppmv, SO2 {r.flue_gas['SO2_ppmv_dry']:.0f} ppmv dry")
    st.subheader("Rundown streams")
    st.dataframe(pd.DataFrame([{"Stream": x.name, "wt%": round(x.wt_pct_of_feed, 1),
                                "vol%": None if x.vol_pct_of_feed is None else round(x.vol_pct_of_feed, 1),
                                "S ppm": None if x.sulfur_ppm is None else round(x.sulfur_ppm), "Note": x.note} for x in rd.rundown(r)]),
                 hide_index=True)
    shift_F = st.slider("Lower the gasoline end point by (degF)", 0, 60, 0)
    if shift_F:
        g = rd.gasoline_end_point_shift(r, shift_F / 1.8)
        st.write(f"Moves {g['moved_vol_pct_of_feed']:.1f} vol% of feed from gasoline to LCO: gasoline "
                 f"{g['yields_wt_pct']['gasoline']:.1f} wt%, LCO {g['yields_wt_pct']['lco']:.1f} wt%.")
    st.subheader("Riser outlet temperature sweep")
    try:
        sweep = rot_sweep(feed, op, [500.0, 515.0, 530.0, 545.0, 560.0])
        st.dataframe(pd.DataFrame([{"ROT C": s.operation.riser_outlet_C, "Conv wt%": round(s.conversion_wt_pct, 1), "C/O": round(s.cat_to_oil, 2),
                                    "T regen C": round(s.regen_temperature_C), "Gasoline": round(s.yields_wt_pct["gasoline"], 1),
                                    "LPG": round(s.yields_wt_pct["lpg"], 1), "Dry gas": round(s.yields_wt_pct["dry_gas"], 1)} for s in sweep]), hide_index=True)
    except ValueError:
        st.caption("Sweep unavailable for this feed/cooler setting (heat balance does not close across the range).")

# ---------------------------------------------------------------------
with tab_ht:
    st.header("Hydrotreater")
    h1, h2, h3, h4 = st.columns(4)
    svc = h1.selectbox("Service", list(SERVICES), index=2)
    flow = h2.number_input("Feed (bpd)", 1000, 300_000, 40_000, step=1000)
    s_in = h3.number_input("Feed sulfur (wt%)", 0.01, 5.0, 1.0)
    s_out = h4.number_input("Product sulfur (ppm)", 0.5, 2000.0, 10.0)
    dens = st.number_input("Feed density (kg/m3)", 650.0, 1000.0, 850.0)
    try:
        r = hydrotreat(flow * 0.158987 * dens / 24.0, dens, s_in, s_out, service=svc)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("LHSV", f"{r.lhsv_1_h:.2f} 1/h"); m2.metric("Reactor volume", f"{r.reactor_volume_m3:,.0f} m3")
        m3.metric("Catalyst", f"{r.catalyst_t:,.0f} t"); m4.metric("H2 makeup", f"{r.h2_makeup_Nm3_m3:.0f} Nm3/m3")
        st.write(f"H2S produced {r.h2s_kg_h:,.0f} kg/h; chemical H2 {r.h2_chemical_kg_h:,.0f} kg/h; makeup {r.h2_makeup_kg_h:,.0f} kg/h")
    except ValueError as e:
        st.error(str(e))
    st.header("Delayed coker")
    q1, q2 = st.columns(2)
    vr_flow = q1.number_input("Vacuum residue feed (t/h)", 10.0, 1000.0, 300.0)
    ccr = q2.number_input("Feed CCR (wt%)", 5.0, 35.0, 20.0)
    try:
        ck = delayed_coker(vr_flow * 1000.0, ccr)
        st.write({k: round(v, 1) for k, v in ck.yields_wt_pct.items()})
        st.metric("Coke drum volume (one fill)", f"{ck.drum_volume_m3:,.0f} m3")
    except ValueError as e:
        st.error(str(e))

# ---------------------------------------------------------------------
with tab_ref:
    st.header("Whole refinery")
    slate = slate_from_widgets("ref", ["upper_zakum"])
    r1, r2, r3, r4 = st.columns(4)
    bpd = r1.number_input("Crude charge (bpd) ", 10_000, 1_000_000, 200_000, step=10_000)
    with_fcc = r2.checkbox("FCC on VGO", True)
    with_coker = r3.checkbox("Delayed coker on vacuum residue", True)
    with_ht = r4.checkbox("VGO hydrotreater (FCC pretreat)", False)
    try:
        res = refine(slate, bpd, RefineryConfig(fcc=with_fcc, coker=with_coker, vgo_hydrotreat=with_ht and with_fcc))
        for w in res.warnings:
            st.warning(w)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Light products", f"{res.light_product_yield_wt_pct:.1f} wt%"); m2.metric("Middle distillate", f"{res.middle_distillate_yield_wt_pct:.1f} wt%")
        m3.metric("Black oil", f"{res.black_oil_yield_wt_pct:.1f} wt%"); m4.metric("Nelson (modelled units)", f"{res.complexity():.2f}")
        st.bar_chart(pd.Series({k: round(v, 2) for k, v in res.pools_wt_pct().items() if v > 0}), x_label="pool", y_label="wt% of crude")
        if res.vgo_hydrotreater:
            h = res.vgo_hydrotreater
            st.write(f"VGO hydrotreater: LHSV {h.lhsv_1_h:.2f} 1/h, reactor {h.reactor_volume_m3:,.0f} m3, catalyst {h.catalyst_t:,.0f} t, "
                     f"H2 make-up {h.h2_makeup_kg_h*24/1000:,.0f} t/day")
        st.caption(f"Mass closure {res.mass_closure:.6f}")
    except ValueError as e:
        st.error(str(e))

# ---------------------------------------------------------------------
with tab_india:
    st.header("Indian refineries: complexity (CHT) and margins (PPAC)")
    st.caption("NCI: Centre for High Technology, https://cht.gov.in/refinery-complexity-index (OGJ 2025 survey). "
               "GRM, yields: PPAC Ready Reckoner FY2022-23, https://ppac.gov.in.")
    rows = [{"Refinery": r["refinery"], "Company": r["company"], "NCI": r["nci"], "MMTPA": r["capacity_mmtpa"]}
            for r in india.refineries() if r["nci"] is not None]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    w = india.company_nci()
    st.dataframe(pd.DataFrame([{"Company": c, "NCI (cap-weighted)": round(w[c], 2),
                                "GRM FY21-22 $/bbl": india.grm_usd_bbl(c, "2021-22"),
                                "GRM FY22-23 $/bbl": india.grm_usd_bbl(c, "2022-23")} for c in ("IOCL", "BPCL", "HPCL", "CPCL", "MRPL")]),
                 hide_index=True)
    fits = {yr or "mean of years": india.grm_nci_fit(yr) for yr in (None, "2021-22", "2022-23")}
    st.dataframe(pd.DataFrame(fits).T.round(2))
    st.caption("GRM rises with NCI but weakly (r 0.28-0.41, n = 5): do not lean on complexity as a margin guarantee.")

# ---------------------------------------------------------------------
with tab_grm:
    st.header("GRM and a petrochemical (propylene -> polypropylene) addition")
    st.caption("Product prices are INPUTS. Calibrate the cracks to a PPAC-reported GRM; petchem is judged by break-even PP price "
               "because no propylene/PP price is available. See docs/PETROCHEMICAL_EVALUATION.md.")
    slate = slate_from_widgets("grm", ["upper_zakum", "cold_lake_blend"])
    g1, g2, g3, g4 = st.columns(4)
    bpd = g1.number_input("Crude charge (bpd)  ", 50_000, 600_000, 290_000, step=10_000)
    crude_px = g2.number_input("Crude price ($/bbl)", 40.0, 150.0, 79.18)
    target = g3.number_input("Target GRM to calibrate ($/bbl)", 1.0, 40.0, 11.25)
    pp_px = g4.number_input("PP price ($/t)", 700.0, 2500.0, float(round(pcp.iocl_deck().pp_usd_t / 50) * 50), step=50.0,
                            help="Default: IOCL homopolymer-injection list price, 11 Sep 2026, at Rs 95.82/$. Propylene has no observed price.")
    try:
        res = refine(slate, bpd, RefineryConfig(vgo_hydrotreat=True))
        deck = calibrate_deck(res, PriceDeck(crude_px), target)
        g = gross_refining_margin(res, deck)
        c1, c2, c3 = st.columns(3)
        c1.metric("GRM (calibrated)", f"{g.grm_usd_bbl:.2f} $/bbl")
        c2.metric("Implied middle-distillate crack", f"{deck.cracks_usd_bbl['middle_distillate']:.1f} $/bbl")
        c3.metric("Nelson (modelled units)", f"{res.complexity():.2f}")
        a = PetchemAssumptions()
        out = []
        for mode in ("conventional", "zsm5", "propylene_mode"):
            o = build_option(res, deck, mode, a)
            e = evaluate(o, pp_px, a)
            out.append({"Route": mode, "Propylene wt% of FCC feed": round(o.propylene_wt_pct_of_fcc_feed, 1), "PP kt/y": round(o.pp_t_y / 1e3),
                        "PP capex $M": round(o.capex_usd / 1e6), "Break-even PP $/t": round(e.breakeven_pp_price_usd_t),
                        "Net $M/y at PP price": round(e.net_usd_y / 1e6, 1), "GRM uplift $/bbl": round(e.grm_uplift_usd_bbl, 2),
                        "Max FCC-side capex $M": round(affordable_fcc_capex_usd(o, pp_px, a) / 1e6) if mode == "propylene_mode" else None})
        st.dataframe(pd.DataFrame(out), hide_index=True)
        st.caption("PP capex scaled from Paradip (680 kt/y, Rs 3,150 crore) by the six-tenths rule. Opex $100/t, 12% hurdle, 20 y are assumptions. "
                   "Nelson index change: 0.0.")
    except ValueError as e:
        st.error(str(e))

# ---------------------------------------------------------------------
with tab_petrol:
    st.header("Petrol displaced by ethanol, the FCC secondary mode, and routes")
    st.caption("PPAC Ready Reckoner FY2025-26; PCS paper (Digital Refining PTQ Q2 2023). See docs/PETROL_DISPLACEMENT.md.")
    bal = pd.DataFrame([{"FY": y, **{k: round(v, 1) for k, v in ptrade.petrol_balance(y).items()}} for y in ("2022-23", "2023-24", "2024-25", "2025-26")])
    st.dataframe(bal, hide_index=True)
    st.dataframe(pd.DataFrame(eth.ms_scenarios(42.6)).round(1), hide_index=True)
    from refinery_design.benchmarks import paradip_model_refinery
    Rp = paradip_model_refinery(True)
    st.write(f"Paradip-basket refinery: gasoline-range pool {Rp.pools_kg_h['gasoline_range']*8400/1e6:,.0f} kt/y; E12 to E20 displaces "
             f"{__import__('refinery_design.routes', fromlist=['x']).displaced_by_blend_step(Rp, 42.6):,.0f} kt/y.")
    st.subheader("FCC modes and the gas plant")
    st.dataframe(pd.DataFrame([{"mode": m.name, "gasoline wt%": round(m.yields_wt_pct["gasoline"], 1), "LPG wt%": round(m.yields_wt_pct["lpg"], 1),
                                "LCO wt%": round(m.yields_wt_pct["lco"], 1), "propylene wt%": round(m.propylene_wt_pct, 1),
                                "gasoline change kt/y": round(m.gasoline_change_t_y / 1e3), "wet-gas load x": round(m.gas_plant.wgfr_ratio, 2),
                                "within PCS paper range": m.gas_plant.within_paper_range} for m in fcc_modes_fn(Rp.fcc.feed, Rp.fcc.operation)]), hide_index=True)
    rr = st.slider("PP realisation (% of IOCL list)", 60, 100, 100) / 100.0
    deck2 = ptrade.RebasedTradeDeck("2025-26", pcp.crude_snapshot()["brent"])
    rows = petrol_switch_options(Rp, deck2, __import__("dataclasses").replace(pcp.iocl_deck(), realisation=rr), pe_usd_t=pcp.iocl_pe_usd_t(realisation=rr))
    st.dataframe(pd.DataFrame([{"route": r.name, "gasoline removed kt/y": round(r.gasoline_removed_kt_y), "fuel change $M/y": round(r.fuel_margin_usd_m_y),
                                "petchem before capital $M/y": None if r.petchem_margin_usd_m_y is None else round(r.petchem_margin_usd_m_y),
                                "net $M/y": None if r.net_usd_m_y is None else round(r.net_usd_m_y), "note": r.note} for r in rows]), hide_index=True)

with tab_dual:
    st.header("Dual-feed cracker: refinery naphtha + LPG")
    st.caption("Propane yields from a real industrial table (US patent 5,990,370, BP Chemicals), recycled to extinction; butane and the feed split are "
               "ASSUMPTIONS. Prices default to the Sept-2026 deck. See docs/PETROCHEMICAL_EVALUATION.md.")
    snapd = pcp.crude_snapshot()
    deckd = ptrade.RebasedTradeDeck("2025-26", snapd["brent"])
    prd = pcp.iocl_deck()
    d1, d2, d3, d4 = st.columns(4)
    feed_mt = d1.number_input("Total feed (Mt/y)", 0.5, 8.0, 4.0, step=0.5, key="dual_feed")
    lpg_share = d2.slider("LPG share of feed (%)", 0, 100, 75, step=5) / 100.0
    bfrac = d3.slider("Butane share of the LPG (%)", 0, 100, 50, step=10, help="Butane yields are ASSUMED.") / 100.0
    capex_tpa = d4.number_input("Capex ($ per tpa at 4 Mt)", 500.0, 2500.0, 1500.0, step=100.0, key="dual_capex")
    e1, e2c, e3, e4 = st.columns(4)
    pe_d = e1.number_input("PE price ($/t)", 600.0, 2500.0, float(round(pcp.iocl_pe_usd_t())), step=50.0, key="dual_pe")
    pp_d = e2c.number_input("PP price ($/t)", 600.0, 2500.0, float(round(prd.pp_usd_t)), step=50.0, key="dual_pp")
    nap_d = e3.number_input("Naphtha ($/t)", 300.0, 1500.0, float(round(deckd.product_usd_t("naphtha"))), step=25.0)
    lpg_d = e4.number_input("LPG ($/t)", 300.0, 1500.0, float(round(deckd.product_usd_t("lpg"))), step=25.0)
    ad = scr.CrackerAssumptions(capex_usd_per_tpa_at_ref=capex_tpa)
    total = feed_mt * 1e6
    od = dfc.build_dual_feed(total * (1 - lpg_share), total * lpg_share, butane_fraction=bfrac, a=ad)
    ed = dfc.evaluate_dual_feed(od, deckd, pe_d, pp_d, naphtha_usd_t=nap_d, lpg_usd_t=lpg_d, a=ad)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ethylene", f"{od.ethylene_t_y/1e6:.2f} Mt/y")
    m2.metric("Margin before capital", f"${ed.margin_before_capital_usd_y/1e6:,.0f} M/y")
    m3.metric("Net after capital", f"${ed.net_usd_y/1e6:,.0f} M/y")
    m4.metric("Break-even PE", f"${ed.breakeven_pe_usd_t:,.0f}/t")
    try:
        be = dfc.breakeven_lpg_usd_t(od, deckd, pe_d, pp_d, naphtha_usd_t=nap_d, a=ad) if od.lpg_t_y > 0 else None
    except ValueError:
        be = None
    if be is not None:
        st.write(f"Break-even LPG price at this mix: **${be:,.0f}/t** (deck ${lpg_d:,.0f}/t).")
    for w in od.warnings:
        st.warning(w)
    st.subheader("LPG-share sweep at this feed size")
    sweep = pd.DataFrame(dfc.lpg_share_sweep(total, deckd, pe_d, pp_d, butane_fraction=bfrac, a=ad))
    sweep["lpg_share"] = (sweep["lpg_share"] * 100).round(0).astype(int)
    st.dataframe(sweep.rename(columns={"lpg_share": "LPG %", "ethylene_mt": "ethylene Mt/y", "before_capital_usd_m": "before capital $M/y",
                                       "net_usd_m": "net $M/y", "margin_per_t_feed": "$/t feed", "breakeven_pe": "break-even PE $/t"}).round(1),
                 hide_index=True)
    st.line_chart(sweep.set_index("lpg_share")[["before_capital_usd_m", "net_usd_m"]].rename(columns={"before_capital_usd_m": "before capital $M/y", "net_usd_m": "net $M/y"}))
    st.subheader("Propane yields: patent Table 1 (per pass) and recycled to extinction")
    st.dataframe(pd.DataFrame([{"conversion %": c, **{k: round(v, 1) for k, v in {
        "ethylene": dfc.propane_yields(c).ethylene, "propylene": dfc.propane_yields(c).propylene, "C4": dfc.propane_yields(c).c4,
        "pygas": dfc.propane_yields(c).pygas, "fuel oil": dfc.propane_yields(c).pyrolysis_fuel_oil}.items()}} for c in (84, 88, 92)]), hide_index=True)
    st.subheader("The refinery's own supply (Paradip basket)")
    Rd = paradip_model_refinery_dual()
    rd_out = dfc.refinery_dual_feed(Rd, deckd, prd, pe_d, butane_fraction=bfrac, a=ad)
    sup, o_r, e_r = rd_out["supply"], rd_out["option"], rd_out["evaluation"]
    st.write(f"LPG pool {sup['lpg_pool_t_y']/1e3:,.0f} kt/y, less FCC propylene kept for PP {sup['propylene_recovered_t_y']/1e3:,.0f} kt/y -> "
             f"**{sup['available_t_y']/1e3:,.0f} kt/y** available. With {o_r.naphtha_t_y/1e3:,.0f} kt/y naphtha: ethylene {o_r.ethylene_t_y/1e6:.2f} Mt/y, "
             f"cash ${e_r.margin_before_capital_usd_y/1e6:,.0f} M/y, net ${e_r.net_usd_y/1e6:,.0f} M/y.")
    for w in o_r.warnings:
        st.warning(w)

with tab_cos:
    st.header("Indian refiners: capacity, production runs, FCC units and plans")
    st.caption("PPAC Ready Reckoners and refinery-wise tables, IPNG 2019-20, company annual reports and investor material; every value has a source and "
               "disagreeing sources are kept. Utilisation is DERIVED (throughput / 1-April capacity). See docs/INDIA_COMPANIES.md.")
    grp = st.selectbox("Company", list(cos.MODULES), key="cos_company")
    mod = cos.MODULES[grp]
    rlist = mod.refineries()
    then_fy, now_fy = st.select_slider("Compare fiscal years", options=cos.years(), value=("2015-16", "2025-26"), key="cos_range")
    rows = []
    for r in rlist:
        v = cos.then_vs_now(r["id"], then_fy, now_fy)
        rows.append({"refinery": r["id"], f"capacity {then_fy}": v["capacity_then"], f"capacity {now_fy}": v["capacity_now"],
                     f"throughput {then_fy}": v["throughput_then"], f"throughput {now_fy}": v["throughput_now"], "throughput change %": v["throughput_change_pct"],
                     f"utilisation {then_fy} %": v["utilisation_then"], f"utilisation {now_fy} %": v["utilisation_now"],
                     f"distillate {then_fy} %": v["distillate_then"], f"distillate {now_fy} %": v["distillate_now"],
                     "capacity inferred": v["capacity_inferred_now"], "note": v["note"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    if grp != "Others":
        ru = cos.company_rollup(mod.NAME, now_fy)
        st.write(f"**{mod.NAME} {now_fy}:** {ru['throughput_mmt']:.1f} MMT on {ru['capacity_mmtpa']:.1f} MMTPA = {ru['utilisation_pct']}% "
                 f"({ru['refineries_counted']} of {ru['refineries_total']} refineries with both numbers)" + (f"; unconfirmed >125%: {', '.join(ru['flagged'])}" if ru["flagged"] else ""))
    tbl = pd.DataFrame(cos.utilisation_table(None))
    tbl = tbl[tbl["refinery"].isin([r["id"] for r in rlist])]
    if not tbl.empty:
        c1c, c2c = st.columns(2)
        c1c.caption("Crude processed (MMT)")
        c1c.line_chart(tbl.pivot(index="fy", columns="refinery", values="throughput_mmt"))
        c2c.caption("Derived utilisation (%)")
        c2c.line_chart(tbl.pivot(index="fy", columns="refinery", values="utilisation_pct"))
        flagged = tbl[tbl["flag"].notna()][["refinery", "fy", "utilisation_pct", "flag"]]
        if not flagged.empty:
            with st.expander(f"{len(flagged)} refinery-years above 125% utilisation"):
                st.dataframe(flagged, hide_index=True)
    st.subheader("FCC-family units")
    fu = pd.DataFrame([u for r in rlist for u in r["fcc_units"]])
    if not fu.empty:
        st.dataframe(fu[["refinery", "unit", "kind", "status", "change", "year", "capacity", "confidence", "note"]].rename(columns={"capacity": "capacity MMTPA"}), hide_index=True)
    fc = pd.DataFrame([e for r in rlist for e in cos.fcc_changes(refinery_id=r["id"])])
    if not fc.empty:
        st.caption("Documented FCC-related changes (there is no published FCC yield or operating-mode data - propylene wt%, conversion - so mode shifts are not visible except where a company said so)")
        st.dataframe(fc[["year", "refinery", "kind", "event"]], hide_index=True)
    pl = pd.DataFrame(cos.plans(mod.NAME) if grp != "Others" else [p for n in cos.others.NAMES for p in cos.plans(n)])
    if not pl.empty:
        st.subheader("Announced plans")
        st.dataframe(pl.drop_duplicates(subset=["company", "project"]).reindex(columns=["company", "project", "scope", "capex", "timing", "status"]), hide_index=True)
    st.subheader("Caveats for this company")
    for c in mod.CAVEATS:
        st.warning(c)
    with st.expander("India-wide FCC picture (lower bounds; many nameplates were never published)"):
        st.dataframe(pd.DataFrame([{"kind": k, "operating units": d["operating"]["units"], "operating known MMTPA": d["operating"]["capacity_known_mmtpa"],
                                    "operating nameplate not found": d["operating"]["capacity_unknown"], "coming units": d["coming"]["units"],
                                    "coming known MMTPA": d["coming"]["capacity_known_mmtpa"]} for k, d in cos.fcc_summary().items()]), hide_index=True)

with tab_src:
    st.header("Crude sourcing and local-currency settlement")
    st.caption("PPAC Tables 8.1 and 8.24; news (confidence tagged). No measured saving from local-currency settlement was found. "
               "See docs/CRUDE_SOURCING_AND_LOCAL_CURRENCY.md.")
    st.dataframe(pd.DataFrame([{"FY": y, **{k: round(v, 2) for k, v in csrc.realised_vs_basket(y).items()}}
                               for y in ("2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26")]), hide_index=True)
    st.write(f"2026 shock, Mar-Jun extra crude bill vs February basket: **${csrc.shock_extra_bill_usd_bn()['total_usd_bn']:.1f} bn**; "
             f"one basis point on the FY25-26 bill = **${csrc.value_of_one_bp_usd_m():.1f} M/yr**.")
    st.dataframe(pd.DataFrame(csrc.local_currency_grid()).pivot(index="share_switched", columns="bps_saved", values="usd_million_per_year").round(0))
    st.dataframe(pd.DataFrame(csrc.partner_feasibility()).round(2), hide_index=True)
    snap2 = pcp.crude_snapshot()
    st.dataframe(pd.DataFrame(csrc.crude_relative_values(ptrade.RebasedTradeDeck("2025-26", snap2["brent"]), throughput_bpd=100_000))
                 [["name", "api", "sulfur_wt", "tan", "net_realisation_usd_bbl", "value_vs_reference_usd_bbl"]].round(2), hide_index=True)
    st.caption(f"Live spreads vs Brent: Dubai {snap2['dubai']-snap2['brent']:+.1f}, WTI {snap2['wti']-snap2['brent']:+.1f}, Urals {snap2['urals']-snap2['brent']:+.1f}. "
               "Relative values exclude freight and corrosion/metallurgy cost.")

with tab_safe:
    st.header("Safety: OISD standards map and model flags")
    st.caption("OISD list, titles and editions from oisd.gov.in (standards not read). Not a safety case. See docs/SAFETY.md.")
    for element, d in sfty.DESIGN_MAP.items():
        with st.expander(element):
            st.write(d["check"])
            st.dataframe(pd.DataFrame([{"standard": n, "title": sfty.standard(n)["title"], "edition": sfty.standard(n)["edition"]} for n in d["oisd"]]), hide_index=True)
            st.caption("Basis: " + d["basis"])
    st.subheader("Flags for the crude slate on the Whole refinery tab defaults")
    for f in sfty.crude_corrosion_flags(load_crude("dalia").as_slate()):
        st.warning(f"{f.topic} [{f.level}]: {f.message}")

st.divider()
st.caption(
    "Disclaimer: textbook/public-domain conceptual sizing for early-stage screening only. Not a substitute for a "
    "rigorous process simulator, a kinetic FCC model fitted to plant data, or licensor/vendor design. Crude assays are "
    "ExxonMobil's public downloads, provided without warranty; check current assays before any commercial use."
)
