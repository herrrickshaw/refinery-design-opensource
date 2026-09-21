"""Propylene / polypropylene price deck.

**What is observed and what is not.**  The polypropylene side rests on a primary source:
IOCL's own ex-works PP price lists (Rs/MT, basic and cash, GST additional), read from the PDFs
IOCL's authorised distributor publishes, at three dates in 2026.  Converting to dollars needs an
exchange rate (95.82 on 2026-09-17, from a web-search summary - medium confidence).  The
propylene side has **no 2026-09 observation**: the only figures found are older or regional
aggregator snippets (India CFR ~$760-794/t in late 2025, Northeast Asia ~$1,010/t in March 2026),
all low confidence.  ``PetchemPriceDeck.propylene_usd_t`` is therefore optional and, when set, is
a *scenario*, not a market price.

An IOCL list price is a domestic selling price (it includes whatever import-parity premium the
Indian market carries) before any discounts or freight; use ``realisation`` to haircut it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "petchem_prices.json"
GRADES = ("homopolymer_injection_1110MG", "raffia_1030RG", "bopp_1030FG", "random_copolymer_2120MC")


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def iocl_pp_inr_per_mt(grade: str = "homopolymer_injection_1110MG", date: str = "2026-09-11") -> float:
    """IOCL ex-works PP price, Rs/MT (basic & cash, GST additional, Thane)."""
    return float(_raw()["iocl_pp_ex_works_inr_per_mt"]["grades"][grade][date])


def iocl_pp_change_pct(grade: str = "homopolymer_injection_1110MG", d0: str = "2026-01-01", d1: str = "2026-09-11") -> float:
    """Change in the IOCL Rs list price between two dates - exchange-rate neutral."""
    return 100.0 * (iocl_pp_inr_per_mt(grade, d1) / iocl_pp_inr_per_mt(grade, d0) - 1.0)


def usd_inr() -> float:
    return float(_raw()["usd_inr"]["value"])


def crude_snapshot() -> dict:
    """Live crude prices recorded on 2026-09-21 (Brent, Dubai, WTI, Urals; Oman unavailable)."""
    return dict(_raw()["crude_snapshot_usd_bbl"])


def indian_basket_snapshot_usd_bbl() -> float:
    """PPAC's Indian-basket formula on the recorded snapshot, with Dubai standing in for Oman."""
    from .india import indian_basket_usd_bbl

    c = crude_snapshot()
    return indian_basket_usd_bbl(oman=c["dubai"], dubai=c["dubai"], brent_dated=c["brent"])


def propylene_observations() -> list[dict]:
    """Dated propylene observations found (all low confidence; none for 2026-09)."""
    return list(_raw()["propylene_usd_t"])


@dataclass(frozen=True)
class PetchemPriceDeck:
    pp_usd_t: float
    label: str
    propylene_usd_t: float | None = None     # scenario only - no 2026-09 observation exists
    realisation: float = 1.0                 # share of the list price the refinery actually nets
    notes: list[str] = field(default_factory=list)

    @property
    def pp_realised_usd_t(self) -> float:
        return self.pp_usd_t * self.realisation


def iocl_deck(grade: str = "homopolymer_injection_1110MG", date: str = "2026-09-11", fx: float | None = None,
              realisation: float = 1.0, propylene_usd_t: float | None = None) -> PetchemPriceDeck:
    """Deck from an IOCL list price (converted at ``fx`` or the recorded 17-Sep-2026 rate)."""
    rate = usd_inr() if fx is None else fx
    inr = iocl_pp_inr_per_mt(grade, date)
    return PetchemPriceDeck(
        pp_usd_t=inr / rate, label=f"IOCL {grade} ex-works {date}", propylene_usd_t=propylene_usd_t, realisation=realisation,
        notes=[f"Rs {inr:,.0f}/MT at Rs {rate:.2f}/$ (basic & cash, GST extra, before discounts and freight)"])
