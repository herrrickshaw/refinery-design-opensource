"""The other Indian refiners: CPCL, MRPL, NRL, HMEL, HRRL and ONGC's Tatipaka."""
from . import core

NAMES = ("CPCL", "MRPL", "NRL", "HMEL", "HRRL", "ONGC")
CAVEATS = [
    "CPCL Manali ran 11.71 MMT in FY2025-26 (112% of 10.5 MMTPA) with a record FCCU throughput of 1,085 TMT. The Cauvery Basin (Nagapattinam) refinery has been shut since FY2019-20 "
    "and a 9 MMTPA refinery-cum-petchem complex (Rs 36,354 crore in the FY25 report, up from Rs 31,580 crore) is planned; its commissioning date was not extracted.",
    "MRPL reported 120% utilisation in FY2024-25 (18.04 MMT net). MRPL and IOCL stopped publishing GRM for FY2025-26; the $9.22/bbl figure is from a press report of results.",
    "NRL's GRM is not comparable with the other PSUs (excise-duty benefit; mainly domestic Assam crude). Its expansion from 3 to 9 MMTPA (Rs 33,901 crore, up from Rs 22,594 crore) "
    "targets Dec 2026, with a 1.95 MTPA petro-FCC and a 360 KTPA polypropylene unit; one aggregator gives Dec 2027, unverified.",
    "HMEL's early-year throughput and Nelson index are unverified, and the cause of its November-December 2025 dip comes from press, not a filing.",
    "Capacity for CPCL, MRPL, NRL and ONGC is IPNG for 1 April 2015-2020 and PPAC for 2026; FY2021-22..FY2025-26 is carried forward (marked inferred) because the two ends are equal.",
]


def refineries() -> list[dict]:
    out = []
    for n in NAMES:
        out += core.refineries(n)
    return out
