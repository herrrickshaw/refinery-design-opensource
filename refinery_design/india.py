"""Indian refinery reference data: complexity (CHT) and margins (PPAC).

* **NCI and capacity** - Centre for High Technology (MoPNG),
  https://cht.gov.in/refinery-complexity-index ("NCI based on OGJ WW Refining &
  Complexity survey 2025").
* **GRM, distillate yield, fuel & loss, Indian basket** - PPAC Ready Reckoner
  FY2022-23, Tables 4.1, 4.7, 4.8, 4.9, 4.12 and 8.1.
  https://ppac.gov.in (see ``scripts/build_india_data.py`` for the exact URL).

PPAC's GRM is the EIA definition: revenue from product sales minus the cost of
the raw materials used to make them, in $/bbl of crude.  It is a company-level
number (refinery-wise GRM is not published).

**NRL caveat.**  Numaligarh (NRL) reports a GRM of $20-43/bbl (FY2020-21 to FY2025-26), two to four
times the other PSUs, and it is not comparable with them.  Two things set it apart:

* PPAC footnotes that the North-East refineries' GRM "include excise duty benefit" (verified, PPAC
  Table 4.7) - a fiscal incentive that raises reported margin without any change in processing;
* NRL runs mainly *domestic* Upper-Assam crude supplied by Oil India and ONGC (3,033 kt of domestic
  crude out of 3,066 kt processed in FY2024-25, per a news report of NRL's results), not imported
  benchmark crude, so its crude cost is not the import price the other refineries pay.

That domestic-crude pricing arrangement is *not verified* here, so this repo does not attribute a size
to it; it only refuses to mix NRL into any margin comparison.  NRL's expansion from 3 to 9 MMTPA with
imported crude (reported as commissioned December 2025) will change the picture after FY2025-26.
IOCL's own GRM also includes the excise benefit on its North-East refineries (a small share of its
throughput).  :func:`grm_nci_fit` therefore excludes NRL by default.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA_FILE = Path(__file__).parent / "data" / "india_refineries.json"
CHT_URL = "https://cht.gov.in/refinery-complexity-index"


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def refineries() -> list[dict]:
    """CHT table: company, refinery, commissioned, nci (None if not given), capacity_mmtpa."""
    return list(_raw()["cht"]["refineries"])


def nci(refinery: str) -> float:
    for r in refineries():
        if r["refinery"] == refinery and r["nci"] is not None:
            return r["nci"]
    raise KeyError(refinery)


def company_nci() -> dict[str, float]:
    """Capacity-weighted NCI by company (refineries with a published NCI)."""
    acc: dict[str, list[float]] = {}
    for r in refineries():
        if r["nci"] is not None and r["capacity_mmtpa"] > 0:
            acc.setdefault(r["company"], []).append((r["capacity_mmtpa"], r["nci"]))
    return {c: sum(w * n for w, n in v) / sum(w for w, _ in v) for c, v in acc.items()}


def grm_usd_bbl(company: str, year: str) -> float | None:
    p = _raw()["ppac"]
    return p["grm_usd_bbl"][company][p["grm_years"].index(year)]


def distillate_yield_pct(refinery: str, year: str) -> float | None:
    p = _raw()["ppac"]
    return p["distillate_pct"][refinery][p["distillate_years"].index(year)]


def paradip_fuel_loss_pct(year: str = "2022-23") -> float:
    f = _raw()["ppac"]["fuel_loss"]
    return f["Paradip_pct"][f["years"].index(year)]


def psu_fuel_loss_pct() -> float:
    f = _raw()["ppac"]["fuel_loss"]["PSU_total_2022_23"]
    return 100.0 * f["fuel_loss_mmt"] / f["throughput_mmt"]


def indian_basket_usd_bbl(oman: float, dubai: float, brent_dated: float) -> float:
    """PPAC's Indian basket (from 2020-21): 75.62% sour (mean of Oman and Dubai) + 24.38% Brent Dated."""
    return 0.7562 * 0.5 * (oman + dubai) + 0.2438 * brent_dated


NRL_CAVEAT = ("NRL's GRM includes the North-East excise-duty benefit (PPAC Table 4.7 footnote) and reflects mostly domestic "
              "Upper-Assam crude (OIL/ONGC) rather than imported crude; it is not comparable with other refiners' GRM. "
              "The domestic-crude pricing mechanism is not verified here.")
NON_COMPARABLE = ("NRL",)


def grm_nci_fit(year: str | None = None, companies: tuple[str, ...] = ("IOCL", "BPCL", "HPCL", "CPCL", "MRPL")) -> dict:
    """Least-squares GRM ($/bbl) against capacity-weighted NCI across companies.

    ``year=None`` uses each company's mean over the years available.  With
    five companies this is a weak, descriptive statistic - read ``r`` and ``n``.
    """
    w = company_nci()
    p = _raw()["ppac"]
    xs, ys = [], []
    for c in companies:
        series = [v for v in p["grm_usd_bbl"][c] if v is not None]
        y = np.mean(series) if year is None else grm_usd_bbl(c, year)
        if y is not None:
            xs.append(w[c])
            ys.append(y)
    x, y = np.array(xs), np.array(ys)
    slope, intercept = np.polyfit(x, y, 1)
    return {"slope_usd_bbl_per_nci": float(slope), "intercept": float(intercept),
            "r": float(np.corrcoef(x, y)[0, 1]), "n": len(x)}
