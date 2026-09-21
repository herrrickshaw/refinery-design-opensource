"""BPCL (Bharat Petroleum): Mumbai, Kochi and Bina; 35.3 MMTPA; roughly 41 MMT processed in FY2025-26."""
from . import core

NAME = "BPCL"
OWNERSHIP = "Public sector (Government of India majority shareholder)"
CAVEATS = [
    "Bina (the former BORL) has NO FCC. Its 7.8->11 MMTPA expansion adds a 1.2 Mt/y dual-feed ETHYLENE cracker (a steam cracker), commissioning May 2028; "
    "the propylene-to-polypropylene link is Kochi's PFCC and Bina's 550 KTPA PP fed from the cracker.",
    "PPAC's 'BPC total' capacity excluded Bina (then BORL) until 1 April 2022 and includes it from 1 April 2023.",
    "BPCL Mumbai has run above 100% utilisation every year on a 12 MMTPA nameplate unchanged since 2006 (129.8% in FY2024-25).",
    "FY2025-26 BPCL figures (41.15 MMT, GRM $11.74/bbl, distillate yield 84.54%) come from a third-party transcript of the Q4 FY26 call: treat as secondary.",
    "Bina expansion cost differs by source: Rs 43,367 crore (annual reports), about Rs 49,000-49,800 crore (CMD statement, Q4 FY26 call).",
]


def refineries() -> list[dict]:
    return core.refineries(NAME)


def summary(now: str = "2025-26") -> dict:
    return core.company_rollup(NAME, now)
