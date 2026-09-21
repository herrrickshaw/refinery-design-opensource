"""Crude sourcing: what the Indian basket and import data show, and what local-currency settlement can and cannot save.

Data (``data/crude_sourcing.json``, ``scripts/build_crude_sourcing_data.py``) come from PPAC's Ready Reckoner FY2025-26
(basket, import bill), and from news reports (rupee-settled imports, supplier objections, bilateral trade, Urals
differentials) whose confidence is tagged in the file.  Nothing here is a forecast.

**The central caveat on "savings from local-currency trade".**  No source found quantifies the saving.  The one official
statement found (MoPNG, via Outlook Business, Dec 2023) says the opposite for the importer: suppliers *passed extra
conversion costs on to IOC*.  A ~2% "transaction cost" claim exists for Indian *exporters* to the UAE, not for crude.  So
this module offers arithmetic (the value of one basis point, scenario grids) and a feasibility test (can the partner
recycle the rupees it receives?), and refuses to state a saving as fact.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "crude_sourcing.json"


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def basket_usd_bbl(period: str) -> float:
    """PPAC Indian basket: a fiscal year like ``"2025-26"`` or a 2026 month like ``"2026-04"``."""
    r = _raw()
    return float(r["basket_annual_usd_bbl"].get(period) or r["basket_2026_monthly_usd_bbl"][period])


def crude_import(year: str) -> dict:
    r = _raw()["crude_imports"]
    row = r["rows"][year]
    return dict(zip(r["columns"], row))


def implied_rs_per_usd(year: str) -> float:
    c = crude_import(year)
    return c["rs_crore"] * 1e7 / (c["usd_million"] * 1e6)


def realised_vs_basket(year: str) -> dict:
    """PPAC's realised crude import price against the Indian basket, and the bill that gap represents.

    Realised = value / barrels (Table 8.24).  The basket is a benchmark (FOB-type) price, so a *negative* gap is a
    saving net of freight and insurance; the gap also carries grade mix and timing.
    """
    c = crude_import(year)
    realised = c["usd_million"] / c["million_bbl"]
    b = basket_usd_bbl(year)
    return {"realised_usd_bbl": realised, "basket_usd_bbl": b, "gap_usd_bbl": realised - b,
            "gap_usd_bn": (realised - b) * c["million_bbl"] / 1000.0, "bill_usd_bn": c["usd_million"] / 1000.0}


def shock_extra_bill_usd_bn(months=("2026-03", "2026-04", "2026-05", "2026-06"), baseline: str = "2026-02",
                            annual_million_bbl: float | None = None) -> dict:
    """Extra crude bill from the 2026 Hormuz-related price spike versus the February basket.

    Assumes imports run at 1/12 of ``annual_million_bbl`` (default FY2025-26) each month - an approximation, because
    monthly import volumes are not in the data.
    """
    mb = (crude_import("2025-26")["million_bbl"] if annual_million_bbl is None else annual_million_bbl) / 12.0
    base = basket_usd_bbl(baseline)
    rows = {m: (basket_usd_bbl(m) - base) * mb / 1000.0 for m in months}
    return {"per_month_usd_bn": rows, "total_usd_bn": sum(rows.values()), "monthly_million_bbl": mb, "baseline_usd_bbl": base}


def rupee_settled_share_of_crude_bill(year: str = "2025-26") -> float:
    """Rupee-settled imports (ALL goods) as a share of the crude bill.  Numerator is not crude-only: read as scale, not share."""
    rs = _raw()["rupee_settled"]["fy_rs_crore"][year]
    return rs / crude_import(year)["rs_crore"]


def value_of_one_bp_usd_m(bill_usd_bn: float | None = None, share_switched: float = 1.0) -> float:
    """$ million per year per basis point of cost difference on the settled share of the crude bill."""
    bill = crude_import("2025-26")["usd_million"] / 1000.0 if bill_usd_bn is None else bill_usd_bn
    return bill * 1e9 * share_switched * 1e-4 / 1e6


def local_currency_grid(shares=(0.05, 0.10, 0.25, 0.50), bps=(-50, -25, 0, 10, 25, 50), bill_usd_bn: float | None = None) -> list[dict]:
    """Annual saving ($ million) for switching ``share`` of the crude bill at a cost change of ``bps`` (positive = saving).

    The sign and size of ``bps`` are NOT established; the negative side of the grid is the pass-through the ministry reported.
    """
    return [{"share_switched": s, "bps_saved": b, "usd_million_per_year": b * value_of_one_bp_usd_m(bill_usd_bn, s)}
            for s in shares for b in bps]


def self_financing_ratio(country: str) -> float:
    """India's exports to a country divided by its imports from it: how much of the rupees paid the partner can spend back
    on Indian goods (total trade, not crude only).  Low ratios mean rupee balances pile up unused."""
    t = _raw()["bilateral_trade_usd_bn"][country]
    return t["exports"] / t["imports"]


def rupee_recycling_gap_usd_bn(country: str) -> float:
    t = _raw()["bilateral_trade_usd_bn"][country]
    return t["imports"] - t["exports"]


def partner_feasibility() -> list[dict]:
    out = []
    for c in ("UAE", "Saudi Arabia", "Iraq", "Russia"):
        out.append({"country": c, "self_financing_ratio": self_financing_ratio(c), "trade_gap_usd_bn": rupee_recycling_gap_usd_bn(c),
                    "crude_share_q1_fy26_pct": _raw()["crude_share_q1_fy26_pct"].get(c)})
    return sorted(out, key=lambda r: -r["self_financing_ratio"])


def urals_regime(live_urals: float, live_brent: float) -> dict:
    """Is Russian crude at a discount or a premium to Brent right now?"""
    d = live_urals - live_brent
    return {"urals_minus_brent": d, "regime": "premium" if d > 0 else "discount",
            "history": _raw()["urals_vs_brent"]}


# --------------------------------------------------------------------
# Which crude is worth what, in a given refinery
# --------------------------------------------------------------------
def crude_relative_values(deck, reference: str = "azeri_btc", throughput_bpd: float = 200_000, keys=None) -> list[dict]:
    """Net product value per barrel of each assay crude in the SAME refinery at the SAME product prices, relative to a
    reference crude.  The difference is the most one could pay above (or must be paid below) the reference for that crude.

    Uses the flowsheet (CDU/VDU + FCC on hydrotreated VGO + delayed coker) at ``deck``'s product prices; unmodelled
    fuel & loss is charged identically.  Crudes whose FCC feed cannot heat-balance are flagged, not dropped.
    """
    from .assay import available_crudes, load_crude
    from .flowsheet import RefineryConfig, refine
    from .grm import gross_refining_margin

    rows = []
    for k in (keys or available_crudes()):
        c = load_crude(k)
        r = refine(c, throughput_bpd, RefineryConfig(vgo_hydrotreat=True))
        g = gross_refining_margin(r, deck)
        rows.append({"key": k, "name": c.name, "api": c.api, "sulfur_wt": c.sulfur_wt, "tan": c.tan,
                     "net_realisation_usd_bbl": g.product_worth_usd_bbl - g.fuel_loss_cost_usd_bbl,
                     "light_product_yield_wt_pct": r.light_product_yield_wt_pct, "fcc_flags": len(r.warnings)})
    ref = next(x["net_realisation_usd_bbl"] for x in rows if x["key"] == reference)
    for x in rows:
        x["value_vs_reference_usd_bbl"] = x["net_realisation_usd_bbl"] - ref
    return sorted(rows, key=lambda x: -x["value_vs_reference_usd_bbl"])


# --------------------------------------------------------------------
# Russian crude: what the 2026 reporting says (low-medium confidence, sources conflict)
# --------------------------------------------------------------------
def russia_news() -> dict:
    return dict(_raw()["russia_news_2026"])


def russian_landed_advantage_usd_bbl(discount_to_brent: float, freight_premium_vs_alternative: float = 0.0) -> float:
    """Net advantage of a Russian barrel over a Brent-priced one: -(discount) minus any extra freight.  Positive = cheaper.

    ``discount_to_brent`` follows the reports' sign (negative = discount).  Delivered (DAP) quotes already include freight,
    so pass ``freight_premium_vs_alternative=0`` for those.
    """
    return -discount_to_brent - freight_premium_vs_alternative


def russia_discount_range() -> tuple:
    d = [r["usd_bbl"] for r in _raw()["russia_news_2026"]["discount_to_brent_reports"]]
    return min(d), max(d)
