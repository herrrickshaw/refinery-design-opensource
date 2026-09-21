"""IOCL (Indian Oil Corporation): nine refineries, ~70 MMTPA, 75.5 MMT processed in FY2025-26 (107.4% utilisation)."""
from . import core

NAME = "IOCL"
OWNERSHIP = "Public sector (Ministry of Petroleum & Natural Gas)"
CAVEATS = [
    "FY2025-26 GRM and company-level distillate yield are NOT published: PPAC footnotes that IOCL and MRPL stopped publishing GRM for FY2025-26.",
    "The IOCL Integrated Annual Report 2025-26 section that was reachable (Project SPRINT) carries no refinery figures; FY2025-26 throughput comes from the "
    "Q4 FY26 earnings call and PPAC. Earlier years come from IOCL annual reports FY2015-16..FY2024-25.",
    "PPAC and the annual report disagree for FY2015-16 (58.0 vs 56.69 MMT) and on FY2016-17 utilisation (94.2% or 105.1%, with or without Paradip): both are kept.",
    "IOCL's GRM includes the excise-duty benefit on its North-East refineries (Guwahati, Digboi, Bongaigaon).",
    "INDMAX capacities at Paradip and Bongaigaon come from trade-press summaries, not IOCL documents. Paradip's is 4.27 or 4.17 MMTPA depending on the source.",
]


def refineries() -> list[dict]:
    return core.refineries(NAME)


def summary(now: str = "2025-26") -> dict:
    return core.company_rollup(NAME, now)
