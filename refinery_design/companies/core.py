"""Indian refiners refinery-by-refinery: capacity, production runs, FCC units and announced plans.

Data: ``data/india_companies.json``, built by ``scripts/build_companies_data.py`` from three extraction files in
``research/`` (PPAC Ready Reckoners and refinery-wise crude-processing tables, IPNG 2019-20, company annual reports,
investor presentations, CHT, and press where nothing better exists).  Every value carries a source; where sources
disagree the primary is kept and the others are listed in ``alt``.

Conventions
-----------
* Fiscal years are ``"2015-16"`` .. ``"2025-26"``.  Throughput is crude processed in MMT; capacity is MMTPA on
  1 April of the fiscal year (PPAC).
* **Utilisation is derived here** as throughput over that capacity.  It is not a company-reported figure, and it can
  exceed 100% because refineries run above nameplate.  Values above 125% are flagged, and the flag says whether a
  company-reported utilisation confirms them (BPCL Mumbai: real) or not (Reliance's SEZ refinery in FY2015-16..FY2017-18,
  where the source's capacity column moved from 27 to 35.2 MMTPA, so 137% is probably not a real over-run).
* Capacity for Reliance, Nayara, CPCL, MRPL, NRL and ONGC is published for 1 April 2015-2020 and 2026 only; for
  FY2021-22..FY2025-26 it is carried forward where the 2020 and 2026 values are equal and marked ``inferred``.
* There is **no published FCC yield or mode data** (propylene wt%, conversion) in any source reached.  The FCC
  section documents units, capacities where stated, and dated changes - it cannot say how a unit's operating mode
  moved except where a company said so.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "india_companies.json"
UTILISATION_FLAG_PCT = 125.0


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def years() -> list[str]:
    return list(_raw()["years"])


def companies() -> list[str]:
    seen: list[str] = []
    for r in _raw()["refineries"]:
        if r["company"] not in seen:
            seen.append(r["company"])
    return seen


def refineries(company: str | None = None) -> list[dict]:
    return [r for r in _raw()["refineries"] if company is None or r["company"] == company]


def refinery(refinery_id: str) -> dict:
    for r in _raw()["refineries"]:
        if r["id"] == refinery_id:
            return r
    raise KeyError(refinery_id)


def _val(series: dict, fy: str):
    e = series.get(fy)
    return None if e is None else e["value"]


def throughput(refinery_id: str, fy: str) -> float | None:
    """Crude processed, MMT (primary source's value)."""
    return _val(refinery(refinery_id)["throughput_mmt"], fy)


def capacity(refinery_id: str, fy: str) -> float | None:
    """Installed capacity on 1 April of the FY, MMTPA; None if not available."""
    return _val(refinery(refinery_id)["capacity_mmtpa"], fy)


def capacity_inferred(refinery_id: str, fy: str) -> bool:
    e = refinery(refinery_id)["capacity_mmtpa"].get(fy)
    return bool(e and e.get("inferred"))


def utilisation_pct(refinery_id: str, fy: str) -> float | None:
    """Derived: throughput / capacity on 1 April.  None if either is missing or capacity is zero."""
    t, c = throughput(refinery_id, fy), capacity(refinery_id, fy)
    if t is None or not c:
        return None
    return 100.0 * t / c


def utilisation_flag(pct: float | None, refinery_id: str | None = None, fy: str | None = None) -> str | None:
    """Text when derived utilisation exceeds 125%, else None.  If the company itself reports a utilisation within 3 points of the derived
    figure the over-run is real (BPCL Mumbai, 129.8% in FY2024-25 on a 12 MMTPA nameplate unchanged since 2006); otherwise it is
    unconfirmed and may be a stale capacity column (Reliance SEZ before FY2018-19)."""
    if pct is None or pct <= UTILISATION_FLAG_PCT:
        return None
    if refinery_id and fy:
        e = refinery(refinery_id)["utilisation_reported_pct"].get(fy)
        if e is not None and abs(e["value"] - pct) <= 3.0:
            return f"above {UTILISATION_FLAG_PCT:.0f}% and confirmed: the company reports {e['value']:.1f}%"
    return (f"above {UTILISATION_FLAG_PCT:.0f}% and not confirmed by a company-reported figure: either a real over-run of nameplate "
            "or a stale capacity basis")


def is_unconfirmed_overrun(refinery_id: str, fy: str) -> bool:
    f = utilisation_flag(utilisation_pct(refinery_id, fy), refinery_id, fy)
    return f is not None and "not confirmed" in f


def distillate_yield_pct(refinery_id: str, fy: str) -> float | None:
    return _val(refinery(refinery_id)["distillate_yield_pct"], fy)


def alternatives(refinery_id: str, series_name: str, fy: str) -> list[dict]:
    """Other sources' values for the same year (empty when sources agree or only one exists)."""
    e = refinery(refinery_id)[series_name].get(fy)
    return [] if e is None else list(e.get("alt", []))


def utilisation_table(company: str | None = None) -> list[dict]:
    """One row per refinery-year with capacity, throughput, derived utilisation, distillate yield and flags."""
    rows = []
    for r in refineries(company):
        for fy in years():
            t, c = throughput(r["id"], fy), capacity(r["id"], fy)
            if t is None and c is None:
                continue
            u = utilisation_pct(r["id"], fy)
            rows.append({"refinery": r["id"], "fy": fy, "capacity_mmtpa": c, "capacity_inferred": capacity_inferred(r["id"], fy),
                         "throughput_mmt": t, "utilisation_pct": None if u is None else round(u, 1),
                         "distillate_yield_pct": distillate_yield_pct(r["id"], fy), "flag": utilisation_flag(u, r["id"], fy)})
    return rows


def company_rollup(company: str, fy: str) -> dict:
    """Sum over the company's refineries with BOTH throughput and capacity in that year (so utilisation is like-for-like).
    ``complete`` is False when some refinery lacks either number - the totals then understate the company.
    ``flagged`` lists refineries above 125% that year with no company-reported figure to confirm it: the roll-up's utilisation is then doubtful."""
    t = c = 0.0
    n = have = 0
    flagged = []
    for r in refineries(company):
        n += 1
        tt, cc = throughput(r["id"], fy), capacity(r["id"], fy)
        if tt is not None and cc is not None:
            t, c, have = t + tt, c + cc, have + 1
            if cc and is_unconfirmed_overrun(r["id"], fy):
                flagged.append(r["id"])
    return {"company": company, "fy": fy, "throughput_mmt": round(t, 2), "capacity_mmtpa": round(c, 2),
            "utilisation_pct": round(100 * t / c, 1) if c else None, "refineries_counted": have, "refineries_total": n,
            "complete": have == n, "flagged": flagged}


def then_vs_now(refinery_id: str, then: str = "2015-16", now: str = "2025-26") -> dict:
    """How a refinery ran in ``then`` vs ``now``: capacity, throughput, derived utilisation, distillate yield, FCC units and
    the dated FCC events in between (and those planned after ``now``).  Missing values are None; nothing is filled in."""
    r = refinery(refinery_id)
    y0, y1 = int(then[:4]), int(now[:4]) + 1  # FY 2015-16 starts in calendar 2015; events in calendar year of the FY end count
    comm = r.get("commissioned")
    pre = comm is not None and comm >= int(then[:4]) + 1  # FY 'then' ended before the refinery was commissioned
    pct = lambda a, b: None if pre or a is None or b is None or a == 0 else round(100.0 * (b - a) / a, 1)
    c0, c1 = capacity(refinery_id, then), capacity(refinery_id, now)
    t0, t1 = throughput(refinery_id, then), throughput(refinery_id, now)
    u0, u1 = utilisation_pct(refinery_id, then), utilisation_pct(refinery_id, now)
    d0, d1 = distillate_yield_pct(refinery_id, then), distillate_yield_pct(refinery_id, now)
    return {
        "refinery": refinery_id, "then": then, "now": now,
        "capacity_then": c0, "capacity_now": c1, "capacity_change_pct": pct(c0, c1),
        "throughput_then": t0, "throughput_now": t1, "throughput_change_pct": pct(t0, t1),
        "utilisation_then": None if u0 is None else round(u0, 1), "utilisation_now": None if u1 is None else round(u1, 1),
        "distillate_then": d0, "distillate_now": d1,
        "fcc_units": r["fcc_units"],
        "fcc_events": [e for e in fcc_changes(refinery_id=refinery_id) if y0 <= e["year"] <= y1],
        "fcc_events_after": [e for e in fcc_changes(refinery_id=refinery_id) if e["year"] > y1],  # planned / expected beyond ``now``
        "capacity_inferred_now": capacity_inferred(refinery_id, now),
        "note": (f"commissioned {comm}, after the '{then}' year: that year's figures are commissioning-stage and no change is computed"
                 if pre else ""),
    }


def fcc_units(company: str | None = None, status: str | None = None) -> list[dict]:
    out = []
    for r in refineries(company):
        for u in r["fcc_units"]:
            if status is None or u["status"] == status:
                out.append(dict(u))
    return out


def fcc_changes(company: str | None = None, refinery_id: str | None = None, since: int | None = None) -> list[dict]:
    out = []
    for e in _raw()["fcc_changes"]:
        if company and not e["refinery"].startswith(company + "/"):
            continue
        if refinery_id and e["refinery"] != refinery_id:
            continue
        if since and e["year"] < since:
            continue
        out.append(dict(e))
    return sorted(out, key=lambda e: (e["year"], e["refinery"]))


def fcc_summary() -> dict:
    """Counts and *known* capacity of FCC-family units by kind, operating vs planned/commissioning.  Units whose capacity was not found
    are counted separately - the capacity totals are therefore lower bounds, not the national FCC capacity."""
    out: dict[str, dict] = {}
    for u in fcc_units():
        if u["kind"] is None or u.get("change") == "revamp":  # a revamp modifies an existing unit; it is not a unit
            continue
        bucket = "operating" if u["status"] == "operating" else "coming"
        k = out.setdefault(u["kind"], {"operating": {"units": 0, "capacity_known_mmtpa": 0.0, "capacity_unknown": 0},
                                       "coming": {"units": 0, "capacity_known_mmtpa": 0.0, "capacity_unknown": 0}})[bucket]
        k["units"] += 1
        if u["capacity"] is None:
            k["capacity_unknown"] += 1
        else:
            k["capacity_known_mmtpa"] = round(k["capacity_known_mmtpa"] + u["capacity"], 2)
    return out


def plans(company: str | None = None) -> list[dict]:
    import re
    return [p for p in _raw()["plans"] if company is None or company in re.findall(r"\w+", p["company"])]


def company_series(company: str) -> dict:
    """Company-level series (company-reported where available): throughput, utilisation, distillate yield, GRM, plus notes."""
    return _raw()["companies"].get(company, {})


def gaps() -> dict:
    return dict(_raw()["gaps"])


def sources() -> dict:
    return dict(_raw()["sources"])
