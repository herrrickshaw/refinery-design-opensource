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
from refinery_design.flowsheet import RefineryConfig, refine
from refinery_design.hydrotreater import SERVICES, hydrotreat

st.set_page_config(page_title="Refinery Conceptual Sizing", layout="wide")
st.title("Oil Refinery Design (open-source)")
st.caption(
    "Conceptual sizing from real published crude assays and textbook correlations "
    "(Gary & Handwerk, Sadeghbeigi, Riazi, Nelson). Screening only - see the disclaimer at the bottom "
    "and docs/METHODOLOGY.md for citations."
)

KEYS = available_crudes()
NAMES = {k: load_crude(k).name for k in KEYS}

tab_types, tab_slate, tab_cdu, tab_fcc, tab_ht, tab_ref = st.tabs(
    ["Crude types", "Slate & blending", "Crude / vacuum unit", "FCC", "Hydrotreater & coker", "Whole refinery"]
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

st.divider()
st.caption(
    "Disclaimer: textbook/public-domain conceptual sizing for early-stage screening only. Not a substitute for a "
    "rigorous process simulator, a kinetic FCC model fitted to plant data, or licensor/vendor design. Crude assays are "
    "ExxonMobil's public downloads, provided without warranty; check current assays before any commercial use."
)
