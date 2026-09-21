"""Nayara Energy: Vadinar, 20 MMTPA (formerly Essar Oil)."""
from . import core

NAME = "Nayara"
OWNERSHIP = "Rosneft 49.13%; Kesani Enterprises / United Capital Partners hold the remainder; Reliance-Rosneft stake talks reported at a nascent stage, nothing confirmed"
CAVEATS = [
    "Nayara publishes no annual report, throughput, GRM or Nelson index (its website returned 403); PPAC's provisional refinery-wise figures are the only run-rate series.",
    "FY2025-26 throughput fell 8% to 18.85 MMT (20.49 in FY2024-25); monthly PPAC figures dropped to 1.41 MMT in August and 1.24 MMT in September 2025 against about 1.70 "
    "normally. The cause reported in the press (sanctions) was not confirmed from a company filing.",
    "The FCC was commissioned in Nov 2006 (Wikipedia, secondary); its nameplate was not found. The petrochemical project (propylene recovery unit, FCC upgrade, 450 ktpa "
    "polypropylene) was expected to produce in Oct-Dec 2023, but the actual start was not verified from a Nayara document.",
    "A reported $8 billion ethane cracker comes from media citing sources; Nayara did not comment.",
]


def refineries() -> list[dict]:
    return core.refineries(NAME)


def summary(now: str = "2025-26") -> dict:
    return core.company_rollup(NAME, now)
