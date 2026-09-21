"""Reliance Industries: Jamnagar DTA (33 MMTPA) and SEZ (35.2 MMTPA), the world's largest refining complex."""
from . import core

NAME = "Reliance"
OWNERSHIP = "Private"
CAVEATS = [
    "Reliance does not publish refinery-wise throughput or GRM; the PPAC series comes from oil-company returns. Its own 'total throughput' (80.0 MMT in "
    "FY2025-26) is a different measure from crude processed (67.3 MMT) and the two must not be compared.",
    "The SEZ refinery's capacity is 27 MMTPA in the source's 1 April 2015-2017 columns and 35.2 from 2018, so derived utilisation before FY2018-19 (up to 137%) "
    "reflects a stale capacity, not a real over-run.",
    "The FCC is listed among the Jamnagar complex's units but no nameplate was found, and 'RFCC' could not be sourced from a company document. "
    "Petcoke gasification (commissioned FY2016-17..FY2019-20) is the main documented upgrading step.",
    "No GRM was found after FY2019-20 (Reliance now reports the O2C segment: revenue Rs 662,401 crore, EBITDA Rs 60,546 crore in FY2025-26).",
]


def refineries() -> list[dict]:
    return core.refineries(NAME)


def summary(now: str = "2025-26") -> dict:
    return core.company_rollup(NAME, now)
