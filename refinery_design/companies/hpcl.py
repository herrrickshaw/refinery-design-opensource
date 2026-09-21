"""HPCL (Hindustan Petroleum): Mumbai and Visakh (25 MMTPA together in FY2025-26), plus JV refineries HMEL Bathinda and HRRL Barmer."""
from . import core

NAME = "HPCL"
OWNERSHIP = "Public sector (ONGC is the majority shareholder)"
CAVEATS = [
    "HPCL's own refineries are Mumbai and Visakh. HMEL Bathinda (HPCL 48.99%) and HRRL Barmer (HPCL 74%) are JVs and are listed under their own names.",
    "Visakh went 8.3 -> 11.0 -> 13.7 -> 15.0 MMTPA between 1 April 2022 and 2025. Its modernisation added a hydrocracker and a 3.55 MMTPA LC-MAX residue upgrader, "
    "NOT a new FCC: the existing FCC-1 and FCC-2 now receive more converted bottoms.",
    "HRRL Barmer (9 MMTPA, dedicated to the nation on 4 July 2026) has only about one month of throughput in the data; its 2.9 MMTPA PFCC is the newest FCC-family unit.",
    "FY2015-16..FY2021-22 published utilisation and per-refinery GRM were not found; utilisation is derived from PPAC/CHT throughput and PPAC capacity.",
]


def refineries() -> list[dict]:
    return core.refineries(NAME)


def summary(now: str = "2025-26") -> dict:
    return core.company_rollup(NAME, now)
