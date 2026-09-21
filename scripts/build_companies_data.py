"""Write ``refinery_design/data/india_companies.json``: refinery-by-refinery capacity, throughput and FCC history for
Indian refiners, plus announced expansion plans.

Inputs (``research/``): three extraction files compiled in September 2026, one per group of companies.  Every number
in them carries a source; where sources disagree both values are kept (``alt``).  Nothing is estimated.

* ``india_companies_iocl.json``       IOCL - PPAC Ready Reckoners, IOCL annual reports FY2015-16..FY2024-25, Q4 FY26 call, IOCL/OGJ pages
* ``india_companies_bpcl_hpcl.json``  BPCL, HPCL, HMEL, HRRL - annual reports, PPAC, CHT, company investor presentations
* ``india_companies_others.json``     Reliance, Nayara, CPCL, MRPL, NRL, ONGC - IPNG 2019-20 (OCR), PPAC endpoint, annual reports, press

What this script does *by hand* (and the reader should check): the FCC unit table and the FCC change timeline
(``FCC_UNITS``, ``FCC_CHANGES`` below) are transcribed from the sourced facts in the research files, because the
sources describe them in prose.  Everything else is mechanical normalisation: fiscal years as ``2015-16``, throughput
in MMT, capacity in MMTPA, one primary value per year with the disagreeing alternatives kept.

Two rules that matter:

* Capacity for the 'others' group is given for 1 April 2015-2020 and 2026 only.  For FY2021-22..FY2025-26 it is carried
  forward *only where the 2020 and 2026 values are equal*, and labelled ``inferred``.  Otherwise it is left blank.
* Where two files cover the same refinery (Bina, HMEL) the BPCL/HPCL file is primary and the other fills gaps.

Run: python scripts/build_companies_data.py [--research DIR]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "refinery_design" / "data" / "india_companies.json"
FY_RE = re.compile(r"^(?:FY)?(\d{4})-(\d{2})$")
YEARS = [f"{y}-{(y + 1) % 100:02d}" for y in range(2015, 2026)]


# ---------------------------------------------------------------- helpers
def _fy(key: str) -> str | None:
    m = FY_RE.match(str(key))
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _prio(source: str) -> int:
    """Lower is preferred: company annual report, then PPAC, then CHT, then anything else (calls, slides, press)."""
    s = (source or "").upper()
    if re.search(r"(^|[_ ])AR\d|_AR|ANNUAL REPORT", s):
        return 0
    if "PPAC" in s or "IPNG" in s:
        return 1
    if "CHT" in s:
        return 2
    return 3


def _entries(x) -> list[dict]:
    if x is None:
        return []
    if isinstance(x, list):
        out = []
        for e in x:
            out += _entries(e)
        return out
    if isinstance(x, dict):
        return [x] if "value" in x else []
    return [{"value": x}]


def pick(x, default_source: str = "", scale: float = 1.0, ndigits: int = 3):
    es = [e for e in _entries(x) if e.get("value") is not None]
    if not es:
        return None
    es = sorted(es, key=lambda e: _prio(e.get("source", "")))  # stable
    f = es[0]
    val = lambda e: round(e["value"] * scale, ndigits) if isinstance(e["value"], (int, float)) else e["value"]
    rec = {"value": val(f), "source": f.get("source") or default_source}
    if f.get("note"):
        rec["note"] = f["note"]
    if f.get("normalised") is not None:
        rec["normalised"] = f["normalised"]
    alt = [{"value": val(e), "source": e.get("source", "")} for e in es[1:] if val(e) != val(f)]
    if alt:
        rec["alt"] = alt
    return rec


def series(d, default_source: str = "", scale: float = 1.0, ndigits: int = 3) -> dict:
    out = {}
    for k, v in (d or {}).items():
        fy = _fy(k)
        if fy is None:
            continue
        rec = pick(v, default_source, scale, ndigits)
        if rec is not None:
            out[fy] = rec
    return dict(sorted(out.items()))


def flat(x) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, list):
        return "; ".join(t for t in (flat(i) for i in x) if t)
    if isinstance(x, dict):
        if "value" in x:
            extra = f" [{x['source']}]" if x.get("source") else ""
            asof = f" (as of {x['as_of']})" if x.get("as_of") else ""
            return f"{x['value']}{asof}{extra}"
        return "; ".join(f"{k}: {flat(v)}" for k, v in x.items() if flat(v))
    return str(x)


def _plan_fields(p: dict) -> dict:
    out = {"scope": [], "capex": [], "timing": [], "status": [], "other": []}
    for k, v in p.items():
        if k in ("company", "project", "item", "sources"):
            continue
        t = flat(v)
        if not t:
            continue
        kl = k.lower()
        if any(s in kl for s in ("cost", "capex")):
            out["capex"].append(t)
        elif any(s in kl for s in ("commission", "dates", "timing")):
            out["timing"].append(t)
        elif any(s in kl for s in ("scope", "fcc_content")):
            out["scope"].append(t)
        elif any(s in kl for s in ("status", "progress")):
            out["status"].append(t)
        else:
            out["other"].append(f"{k}: {t}")
    return {k: " | ".join(v) for k, v in out.items() if v}


# ---------------------------------------------------------------- refinery construction
def _record(company, name, **kw) -> dict:
    r = {"id": f"{company}/{name}", "company": company, "name": name, "capacity_mmtpa": {}, "throughput_mmt": {},
         "distillate_yield_pct": {}, "grm_usd_bbl": {}, "utilisation_reported_pct": {}, "notes": []}
    r.update(kw)
    return r


def from_iocl(d: dict) -> list[dict]:
    out = []
    for name, v in d["refineries"].items():
        r = _record("IOCL", name, commissioned=v.get("commissioned_year"))
        r["capacity_mmtpa"] = series(v.get("capacity_mmtpa_on_1_april_of_FY"), "PPAC installed capacity on 1 April of the FY")
        r["capacity_basis"] = v.get("capacity_note", "")
        r["throughput_mmt"] = series(v.get("throughput_mmt"))
        r["distillate_yield_pct"] = series(v.get("distillate_yield_pct"))
        r["grm_usd_bbl"] = series(v.get("grm_usd_per_bbl"))
        r["notes"] = list(v.get("notes", []))
        out.append(r)
    return out


B_MAP = {"BPCL Mumbai": ("BPCL", "Mumbai"), "BPCL Kochi": ("BPCL", "Kochi"), "BPCL Bina": ("BPCL", "Bina"),
         "HPCL Mumbai": ("HPCL", "Mumbai"), "HPCL Visakh": ("HPCL", "Visakh"),
         "HMEL Bathinda (JV, 48.99% HPCL)": ("HMEL", "Bathinda"), "HRRL Barmer (under construction, HPCL 74%)": ("HRRL", "Barmer")}
B_OWN = {"HMEL/Bathinda": "JV: HPCL 48.99%", "HRRL/Barmer": "JV: HPCL 74%; new refinery, dedicated to the nation 4 July 2026"}


def from_bpcl_hpcl(d: dict) -> list[dict]:
    out = []
    for key, v in d["refineries"].items():
        company, name = B_MAP[key]
        r = _record(company, name, ownership=B_OWN.get(f"{company}/{name}", ""))
        r["capacity_mmtpa"] = series(v.get("capacity_mmtpa_ppac_1_april"), "PPAC installed capacity on 1 April of the FY")
        r["throughput_mmt"] = series(v.get("throughput_mmt"))
        r["utilisation_reported_pct"] = series(v.get("utilisation_pct_published"))
        r["distillate_yield_pct"] = series(v.get("distillate_yield_pct_CHT"), "CHT")
        r["grm_usd_bbl"] = series(v.get("grm_usd_per_bbl"))
        nci = pick((v.get("complexity") or {}).get("nelson_complexity_index"))
        if nci:
            r["nci"] = nci
        r["notes"] = list(v.get("notes", []))
        out.append(r)
    return out


O_MAP = {"Reliance_Jamnagar_DTA": ("Reliance", "Jamnagar DTA"), "Reliance_Jamnagar_SEZ": ("Reliance", "Jamnagar SEZ"),
         "Nayara_Vadinar": ("Nayara", "Vadinar"), "CPCL_Manali": ("CPCL", "Manali"),
         "CPCL_Cauvery_Basin_Nagapattinam": ("CPCL", "Cauvery Basin (Nagapattinam)"), "MRPL_Mangalore": ("MRPL", "Mangalore"),
         "NRL_Numaligarh": ("NRL", "Numaligarh"), "HMEL_Bathinda": ("HMEL", "Bathinda"), "ONGC_Tatipaka": ("ONGC", "Tatipaka"),
         "BPCL_Bina_BORL": ("BPCL", "Bina")}
O_OWN = {"Nayara/Vadinar": "Rosneft 49.13%; Kesani Enterprises / United Capital Partners hold the rest"}


def _others_capacity(cap: dict) -> dict:
    out = {}
    for k, v in cap.items():
        if not str(k).isdigit() or int(k) > 2020:
            continue
        y = int(k)
        out[f"{y}-{(y + 1) % 100:02d}"] = {"value": v, "source": "IPNG 2019-20 Table III.1 (1 April of the FY; OCR of an image PDF)"}
    c20, c26 = cap.get("2020"), cap.get("2026")
    if c20 is not None and c26 is not None and abs(c20 - c26) <= 0.01:
        for y in range(2021, 2026):
            out[f"{y}-{(y + 1) % 100:02d}"] = {"value": c20, "source": "inferred: capacity equal on 1 April 2020 (IPNG) and 1 April 2026 (PPAC)", "inferred": True}
    return dict(sorted(out.items()))


def from_others(d: dict) -> list[dict]:
    out = []
    for key, v in d["refineries"].items():
        company, name = O_MAP[key]
        r = _record(company, name, ownership=O_OWN.get(f"{company}/{name}", ""))
        r["capacity_mmtpa"] = _others_capacity(v.get("capacity_mmtpa_on_1_april", {}))
        for fy, e in v.get("throughput_tmt_by_fy", {}).items():
            if e.get("value_tmt") is not None:
                r["throughput_mmt"][fy] = {"value": round(e["value_tmt"] / 1000.0, 3), "source": e.get("source", "")}
        r["notes"] = list(v.get("notes", []))
        out.append(r)
    return out


def merge(primary: dict, secondary: dict) -> dict:
    """Fill gaps in ``primary`` from ``secondary`` (both refinery records); primary values are never overwritten."""
    for field in ("capacity_mmtpa", "throughput_mmt"):
        for fy, e in secondary[field].items():
            if fy not in primary[field]:
                primary[field][fy] = dict(e, source=f"{e.get('source', '')} (from the Reliance/Nayara/others research file)")
        primary[field] = dict(sorted(primary[field].items()))
    primary["notes"] += [f"[others file] {n}" for n in secondary["notes"]]
    return primary


# ---------------------------------------------------------------- company-level series
def company_series(i: dict, b: dict, o: dict) -> dict:
    it, bt, ot = i["company_totals_by_year"], b["company_totals_by_year"], o["company_totals_by_year"]
    out = {
        "IOCL": {
            "throughput_mmt": series(it["iocl_reported_throughput_mmt"], "IOCL annual report"),
            "throughput_mmt_ppac": series(it["ppac_iocl_total_throughput_mmt"], "PPAC"),
            "capacity_mmtpa": series(it["ppac_iocl_capacity_1_april_mmtpa"], "PPAC"),
            "utilisation_reported_pct": series(it["iocl_reported_capacity_utilisation_pct"]),
            "distillate_yield_pct": series(it["distillate_yield_pct_iocl_reported"]),
            "grm_usd_bbl": series(it["grm_usd_per_bbl_reported"]),
            "fuel_and_loss_pct": {k: v for k, v in it["fuel_and_loss_pct_iocl_reported"].items() if _fy(k)},
            "petrochemicals": it.get("petrochemicals", {}),
            "notes": [flat(it.get("nelson_complexity_index"))],
        },
    }
    for key, code in (("BPCL (Mumbai+Kochi+Bina)", "BPCL"), ("HPCL (Mumbai+Visakh, excl. HMEL)", "HPCL")):
        t = bt[key]
        cap = {}
        for k, v in t.get("installed_capacity_mmtpa_ppac", {}).items():
            m = re.match(r"1\.04\.(\d{4})", k)
            if m:
                y = int(m.group(1))
                cap[f"{y}-{(y + 1) % 100:02d}"] = {"value": v, "source": "PPAC installed capacity (1 April of the FY)"}
        out[code] = {
            "throughput_mmt": series(t.get("throughput_mmt")), "capacity_mmtpa": dict(sorted(cap.items())),
            "utilisation_reported_pct": series(t.get("utilisation_pct")), "distillate_yield_pct": series(t.get("distillate_yield_pct")),
            "grm_usd_bbl": series(t.get("grm_usd_per_bbl")), "capex": {k: flat(v) for k, v in (t.get("capex") or {}).items()},
            "notes": [t["installed_capacity_mmtpa_ppac"].get("note", "")] if isinstance(t.get("installed_capacity_mmtpa_ppac"), dict) else [],
        }
    ril_tp = {k: {"value": round(v / 1000.0, 3), "source": "IPNG / PPAC (crude processed, Jamnagar DTA + SEZ)"}
              for k, v in ot["RIL_total_crude_processed_tmt"].items() if _fy(k)}
    ril_own = ot.get("RIL_company_defined_total_throughput_mmt", {})
    grm = ot["GRM_usd_per_bbl_by_company"]
    mk = lambda d: {k: {"value": v, "source": "company / PPAC (company definitions differ)"} for k, v in (d or {}).items() if _fy(k) and v is not None}
    out["Reliance"] = {"throughput_mmt": dict(sorted(ril_tp.items())), "grm_usd_bbl": mk(grm.get("RIL")),
                       "throughput_mmt_company_defined": {k: v for k, v in ril_own.items() if _fy(k)},
                       "notes": ["Reliance's own 'total throughput' (about 80 MMT in FY2025-26) is a different measure from crude processed "
                                 "(67.3 MMT); the two must not be compared. Jamnagar DTA and SEZ are reported separately by PPAC but "
                                 "not by Reliance."]}
    out["CPCL"] = {"throughput_mmt": {k: {"value": round(v / 1000.0, 3), "source": "IPNG / PPAC (Manali + Cauvery Basin)"}
                                       for k, v in ot["CPCL_total_incl_CBR_tmt"].items() if _fy(k)}, "grm_usd_bbl": mk(grm.get("CPCL")), "notes": []}
    out["MRPL"] = {"grm_usd_bbl": mk(grm.get("MRPL")), "notes": []}
    out["NRL"] = {"grm_usd_bbl": mk(grm.get("NRL")),
                  "notes": ["NRL's GRM is not comparable with the other PSUs (excise-duty benefit; mainly domestic Assam crude) - see refinery_design/india.py."]}
    out["Nayara"] = {"notes": [flat(ot.get("Nayara_ownership")), "Nayara publishes no refinery throughput, GRM or Nelson index; PPAC throughput is the only run-rate series."]}
    return out


# ---------------------------------------------------------------- plans
def plans(i: dict, b: dict, o: dict) -> list[dict]:
    out = []
    for p in i["plans"]:
        out.append({"company": "IOCL", "project": p.get("project", ""), **_plan_fields(p)})
    for p in b["plans"]:
        out.append({"company": p["company"], "project": p.get("project", ""), **_plan_fields(p)})
    for p in o["plans"]:
        out.append({"company": p["company"], "project": p.get("item", ""), **_plan_fields(p)})
    return out


# ---------------------------------------------------------------- hand-curated FCC records (transcribed from the research files)
# kind: FCC | RFCC | PFCC | INDMAX | PRFCC.  change: new (default) | revamp (an existing unit modified - not counted as a unit) | replacement.  status: operating | planned | commissioning.  year = commissioning year or
# expected year (None if not found).  capacity in MMTPA (None if not found).  confidence: primary | secondary | low.
FCC_UNITS = [
    dict(refinery="IOCL/Guwahati", unit="INDMAX (pilot)", kind="INDMAX", status="operating", year=2003, capacity=0.1, confidence="secondary", note="IOCL refinery page; trade-press summary"),
    dict(refinery="IOCL/Gujarat (Koyali)", unit="FCCU (riser)", kind="FCC", status="operating", year=1982, capacity=None, confidence="primary", note="IOCL refinery page"),
    dict(refinery="IOCL/Gujarat (Koyali)", unit="INDMAX FCCU (new, J-18 / LuPech)", kind="INDMAX", status="planned", year=2026, capacity=2.7, confidence="primary", note="Refinery expansion 13.7->18 MMTPA targeted Nov 2026 (OGJ, Aug 2026)"),
    dict(refinery="IOCL/Mathura", unit="FCCU", kind="FCC", status="operating", year=1982, capacity=1.5, confidence="primary", note="Revamped 2014 from 1.3 to 1.5 MMTPA (IOCL refinery page)"),
    dict(refinery="IOCL/Barauni", unit="RFCCU", kind="RFCC", status="operating", year=2002, capacity=1.4, confidence="primary", note="Year is that of the Barauni Expansion Project; RFCCU year not separately stated. To be expanded 1.4->1.7 MMTPA in the 6->9 MMTPA project (OGJ, Aug 2026), due Dec 2026"),
    dict(refinery="IOCL/Panipat", unit="INDMAX (new, P-25)", kind="INDMAX", status="planned", year=2026, capacity=2.5, confidence="secondary", note="15->25 MMTPA expansion, 94% complete at 30 Jun 2026, full commissioning Dec 2026; licence from a trade-press summary. Whether Panipat has a legacy FCC was not confirmed"),
    dict(refinery="IOCL/Bongaigaon", unit="INDMAX FCC (with LPG treatment)", kind="INDMAX", status="operating", year=2020, capacity=0.74, confidence="secondary", note="IOCL page for the year; capacity from trade press"),
    dict(refinery="IOCL/Paradip", unit="INDMAX FCC", kind="INDMAX", status="operating", year=2016, capacity=4.27, confidence="secondary", note="Sources disagree: 4.27 vs 4.17 MMTPA; commissioning April 2016 per one article, December 2015 per another"),
    dict(refinery="IOCL/Haldia", unit="none (once-through hydrocracker 1.7 MMTPA, DCU 1.7 MMTPA)", kind=None, status="operating", year=None, capacity=None, confidence="primary", note="No FCC listed on IOCL's Haldia page; a 42 KTPA propylene recovery unit has in-principle approval (AR 2024-25)"),
    dict(refinery="BPCL/Mumbai", unit="CCU + FCCU (two catalytic cracking units)", kind="FCC", status="operating", year=None, capacity=None, confidence="primary", note="BPCL: '40+ year old'; capacities not found"),
    dict(refinery="BPCL/Mumbai", unit="PRFCC (Petro-Resid FCC), replacement", kind="PRFCC", status="planned", change="replacement", year=2029, capacity=None, confidence="primary", note="About Rs 14,200 crore; replaces the old CCU and FCCU; valorises vacuum residue to propylene, MS and HSD (AR 2024-25; Jan 2026 investor presentation)"),
    dict(refinery="BPCL/Kochi", unit="FCCU (conventional) fed by a VGO hydro-desulphuriser", kind="FCC", status="operating", year=None, capacity=None, confidence="primary", note="Capacity and year not found"),
    dict(refinery="BPCL/Kochi", unit="PFCC (Petro-FCC)", kind="PFCC", status="operating", year=None, capacity=None, confidence="primary", note="Refinery went 9.5->15.5 MMTPA by 1 April 2018 (PPAC). AR 2023-24: with minor modification it can supply additional propylene beyond the PDPP unit"),
    dict(refinery="BPCL/Kochi", unit="PFCC revamp for homo-polymer PP feed + 400 KTPA PP unit", kind="PFCC", status="planned", change="revamp", year=2027, capacity=None, confidence="primary", note="Rs 4,460 crore; October 2027 (project table) or December 2027 (MD&A text)"),
    dict(refinery="BPCL/Bina", unit="none (hydrocracker + delayed coker only)", kind=None, status="operating", year=None, capacity=None, confidence="primary", note="Bina has no FCC. Its 7.8->11 MMTPA expansion adds a 1.2 Mt/y dual-feed ETHYLENE cracker (steam cracker), not an FCC; commissioning May 2028"),
    dict(refinery="HPCL/Mumbai", unit="NFCCU (new FCC) and OFCCU (old FCC)", kind="FCC", status="operating", year=None, capacity=None, confidence="primary", note="Named in AR 2024-25 technology-absorption annexure; capacities not found"),
    dict(refinery="HPCL/Visakh", unit="FCC-1 and FCC-2 (FCCU-I, FCCU-II)", kind="FCC", status="operating", year=None, capacity=None, confidence="primary", note="Two FCCs per the modernisation project's feasibility report; the modernisation added a full-conversion hydrocracker (2023) and a 3.55 MMTPA LC-MAX residue upgrader (commissioned during FY2025-26), NOT a new FCC"),
    dict(refinery="HMEL/Bathinda", unit="Petro-FCC integrated with polypropylene", kind="PFCC", status="operating", year=2012, capacity=None, confidence="low", note="HMEL site claim; a search summary gives 47 kb/d, single secondary source. Refinery commissioned 2012"),
    dict(refinery="HRRL/Barmer", unit="PFCC incl. propylene recovery (TechnipFMC licence)", kind="PFCC", status="commissioning", year=2026, capacity=2.9, confidence="secondary", note="Commissioning in progress 13 May 2026; refinery dedicated to the nation 4 July 2026"),
    dict(refinery="Reliance/Jamnagar DTA", unit="FCC (listed among the complex's units)", kind="FCC", status="operating", year=None, capacity=None, confidence="low", note="Nameplate not published in the sources reached; 'RFCC' not confirmed. Petcoke gasification is the main upgrading story"),
    dict(refinery="Nayara/Vadinar", unit="FCC (with diesel hydro-desulphuriser)", kind="FCC", status="operating", year=2006, capacity=None, confidence="low", note="Commissioned Nov 2006 per Wikipedia; nameplate not found (a search summary said 2.9 Mt/yr but its origin could not be verified). Petchem integration: propylene recovery unit + FCC upgrade + 450 ktpa UNIPOL PP, foundation stone Nov 2021, production expected Oct-Dec 2023 (start not verified from a Nayara document; ~Rs 6,000 crore from a search summary)"),
    dict(refinery="CPCL/Manali", unit="FCCU (one)", kind="FCC", status="operating", year=None, capacity=None, confidence="primary", note="Record throughput 1,085 TMT in FY2025-26 (previous best 1,084 in FY2017-18); design capacity not stated"),
    dict(refinery="CPCL/Cauvery Basin (Nagapattinam)", unit="INDMAX (planned, 9 MMTPA refinery-cum-petchem)", kind="INDMAX", status="planned", year=None, capacity=None, confidence="secondary", note="Existing 1 MMTPA refinery shut since FY2019-20; new complex Rs 36,354 crore in the FY25 report; commissioning date not extracted"),
    dict(refinery="MRPL/Mangalore", unit="Petro-FCC (Phase-III)", kind="PFCC", status="operating", year=2014, capacity=None, confidence="primary", note="Commissioned Q2 FY2014-15; feeds a 440,000 tpa PP unit (commercial production 18 Jun 2015); capacity not stated"),
    dict(refinery="NRL/Numaligarh", unit="Petro-FCC (new, NREP)", kind="PFCC", status="planned", year=2026, capacity=1.95, confidence="secondary", note="3->9 MMTPA expansion; feeds a new 360 KTPA PP unit; completion target Dec 2026 (one unverified aggregator says Dec 2027). Existing 3 MMTPA refinery has no FCC"),
]

# The chronology of FCC-related change, with the evidence type.  Events quoted by fiscal year are dated by the calendar year in which
# that fiscal year ENDS (FY2018-19 -> 2019).  Each entry is a documented event; there is NO published
# FCC yield data (propylene wt%, conversion) in any source reached, so operating-mode changes are not visible except
# where the company says so.
FCC_CHANGES = [
    dict(year=2003, refinery="IOCL/Guwahati", event="INDMAX pilot unit (0.1 MMTPA)", kind="new unit"),
    dict(year=2006, refinery="Nayara/Vadinar", event="FCC and diesel hydro-desulphuriser commissioned (first phase)", kind="new unit"),
    dict(year=2014, refinery="IOCL/Mathura", event="FCCU revamped from 1.3 to 1.5 MMTPA", kind="revamp"),
    dict(year=2014, refinery="MRPL/Mangalore", event="Petro-FCC commissioned in Phase-III (propylene for a 440 ktpa PP unit)", kind="new unit"),
    dict(year=2016, refinery="IOCL/Paradip", event="4.27 MMTPA INDMAX commissioned - the largest FCC-family unit in the set", kind="new unit"),
    dict(year=2019, refinery="Reliance/Jamnagar DTA", event="Unplanned FCC shutdown named as a reason segment EBIT fell 19.8% in FY2018-19 (GRM $9.2/bbl)", kind="disruption"),
    dict(year=2020, refinery="IOCL/Bongaigaon", event="0.74 MMTPA INDMAX commissioned", kind="new unit"),
    dict(year=2022, refinery="CPCL/Manali", event="FCCU throughput 38% above design after the Refinery-III modernisation (FY2021-22)", kind="debottleneck"),
    dict(year=2023, refinery="Nayara/Vadinar", event="Propylene recovery unit + FCC upgrade + 450 ktpa PP (production expected Oct-Dec 2023; start not verified)", kind="petchem integration"),
    dict(year=2025, refinery="MRPL/Mangalore", event="Wet-gas scrubber on the PFCC regenerator stack commissioned (Rs 129 crore)", kind="environmental"),
    dict(year=2025, refinery="HPCL/Mumbai", event="Co-processing of plastic pyrolysis oil in the NFCC unit; ZSM-5 loader on the NFCC; additive trial completed at Visakh FCC-2 (AR 2024-25)", kind="operating mode / catalyst"),
    dict(year=2026, refinery="CPCL/Manali", event="Record FCCU throughput of 1,085 TMT in FY2025-26", kind="debottleneck"),
    dict(year=2026, refinery="HPCL/Visakh", event="3.55 MMTPA LC-MAX residue upgrader commissioned: more converted bottoms, feeding existing FCCs rather than adding one", kind="upstream of FCC"),
    dict(year=2026, refinery="HRRL/Barmer", event="2.9 MMTPA PFCC commissioned; refinery dedicated 4 July 2026", kind="new unit"),
    dict(year=2026, refinery="IOCL/Gujarat (Koyali)", event="2.7 MMTPA INDMAX due (Nov 2026)", kind="planned"),
    dict(year=2026, refinery="IOCL/Panipat", event="2.5 MMTPA INDMAX due (Dec 2026); project cost up from Rs 32,946 to Rs 38,231 crore", kind="planned"),
    dict(year=2026, refinery="IOCL/Barauni", event="RFCC expansion 1.4 to 1.7 MMTPA due (Dec 2026)", kind="planned"),
    dict(year=2026, refinery="NRL/Numaligarh", event="1.95 MMTPA petro-FCC due (Dec 2026 target) feeding a 360 KTPA PP unit", kind="planned"),
    dict(year=2027, refinery="BPCL/Kochi", event="PFCC revamp for homo-polymer PP feed with a 400 KTPA PP unit (Oct/Dec 2027; Rs 4,460 crore)", kind="planned"),
    dict(year=2029, refinery="BPCL/Mumbai", event="PRFCC (about Rs 14,200 crore) to replace the 40+ year old CCU and FCCU", kind="planned"),
]


def build(research: Path) -> dict:
    i = json.loads((research / "india_companies_iocl.json").read_text())
    b = json.loads((research / "india_companies_bpcl_hpcl.json").read_text())
    o = json.loads((research / "india_companies_others.json").read_text())
    recs = {r["id"]: r for r in from_iocl(i) + from_bpcl_hpcl(b)}
    for r in from_others(o):
        if r["id"] in recs:
            merge(recs[r["id"]], r)
        else:
            recs[r["id"]] = r
    for u in FCC_UNITS:
        u.setdefault("change", "new")
    for rid, r in recs.items():
        r["fcc_units"] = [u for u in FCC_UNITS if u["refinery"] == rid]
    unknown = {u["refinery"] for u in FCC_UNITS} - set(recs)
    unknown |= {c["refinery"] for c in FCC_CHANGES} - set(recs)
    if unknown:
        raise SystemExit(f"FCC records reference unknown refineries: {sorted(unknown)}")
    return {
        "_note": "Built by scripts/build_companies_data.py from research/*.json. Values are the primary source's; disagreeing sources are kept as 'alt'. "
                 "Utilisation is derived in refinery_design/companies (throughput / capacity), except 'utilisation_reported_pct'.",
        "research_date": "2026-09-21", "years": YEARS,
        "refineries": list(recs.values()),
        "companies": company_series(i, b, o),
        "plans": plans(i, b, o),
        "fcc_changes": FCC_CHANGES,
        "sources": {"iocl": {s["id"]: s["ref"] for s in i["sources"]},
                    "bpcl_hpcl": b["sources"] if isinstance(b["sources"], dict) else {s["id"]: s["ref"] for s in b["sources"]},
                    "others": {s["id"]: s["ref"] for s in o["sources"]}},
        "gaps": {"iocl": i["gaps"], "bpcl_hpcl": b["gaps"], "others": o["gaps"]},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--research", default=str(ROOT / "research"))
    args = ap.parse_args()
    data = build(Path(args.research))
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    n_tp = sum(len(r["throughput_mmt"]) for r in data["refineries"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['refineries'])} refineries, {n_tp} refinery-year throughputs, "
          f"{len(data['plans'])} plans, {len(FCC_UNITS)} FCC records, {len(FCC_CHANGES)} FCC events")
