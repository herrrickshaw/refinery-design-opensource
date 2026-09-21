"""Write ``refinery_design/data/india_refineries.json``.

Every number below is transcribed by hand from two public Government of India
sources (fetched September 2026) - there is no scraping step, so the values
are reviewable line by line:

* CHT (Centre for High Technology, MoPNG), "Refinery complexity Index":
  https://cht.gov.in/refinery-complexity-index  (NCI "based on OGJ WW Refining &
  Complexity survey 2025"; page last updated 10-04-2026)
* PPAC (Petroleum Planning & Analysis Cell), "Ready Reckoner FY2022-23":
  https://ppac.gov.in/uploads/rep_studies/1689760261_PPAC_READY%20RECKONER-FY2022-23_web_compressed-compressed-min_compressed.pdf
  Tables 4.1 (capacity/throughput), 4.7 (GRM), 4.8 (distillate yield),
  4.9 (fuel & loss), 4.12 (exchange rate), section 8 (Indian basket).

Run: python scripts/build_india_data.py
"""
import json
from pathlib import Path

CHT_URL = "https://cht.gov.in/refinery-complexity-index"
PPAC_URL = ("https://ppac.gov.in/uploads/rep_studies/1689760261_PPAC_READY%20RECKONER-FY2022-23_"
            "web_compressed-compressed-min_compressed.pdf")

# (company, refinery, year commissioned, NCI or None, nameplate MMTPA)
CHT = [
    ("IOCL", "Digboi", 1901, 7.0, 0.65), ("IOCL", "Guwahati", 1962, 7.3, 1.20),
    ("IOCL", "Barauni", 1964, 6.0, 6.00), ("IOCL", "Koyali", 1965, 9.7, 13.70),
    ("IOCL", "Bongaigaon", 1979, 9.0, 2.70), ("IOCL", "Haldia", 1975, 11.8, 8.00),
    ("IOCL", "Mathura", 1982, 7.1, 8.00), ("IOCL", "Panipat", 1998, 10.5, 15.00),
    ("IOCL", "Paradip", 2016, 10.6, 15.00),
    ("CPCL", "Manali", 1965, 10.8, 10.50), ("CPCL", "Nagapattinam", 1993, None, 0.0),
    ("HPCL", "Mumbai", 1954, 9.3, 9.50), ("HPCL", "Visakhapatnam", 1957, 8.4, 15.00),
    ("BPCL", "Mumbai", 1955, 9.8, 12.00), ("BPCL", "Kochi", 1963, 11.2, 15.50),
    ("BPCL", "Bina", 2011, 11.8, 7.80),
    ("NRL", "Numaligarh", 2000, 8.4, 3.00), ("MRPL", "Mangalore", 1996, 9.46, 15.00),
    ("ONGC", "Tatipaka", 2001, None, 0.066),
]
YEARS_GRM = ["2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
# PPAC Table 4.7, $/bbl. None = not available (IOCL and MRPL stopped publishing GRM for FY2025-26; BPCL includes
# BORL from FY2022-23). FY2017-18..FY2022-23 from the FY2022-23 edition, FY2023-24..FY2025-26 from the FY2025-26 edition.
GRM = {'IOCL': [8.49, 5.41, 0.08, 5.64, 11.25, 19.52, 12.05, 4.8, None],
 'BPCL': [6.85, 4.58, 2.5, 4.06, 9.09, 20.24, 14.14, 6.82, 11.74],
 'HPCL': [7.4, 5.01, 1.02, 3.86, 7.19, 12.09, 9.08, 5.74, 8.79],
 'CPCL': [6.42, 3.7, -1.18, 7.14, 8.85, 12.48, 8.64, 4.22, 9.28],
 'MRPL': [7.54, 4.06, -0.23, 3.71, 8.72, 9.88, 10.36, 4.45, None],
 'NRL': [31.92, 28.11, 24.55, 37.23, 43.46, 35.82, 29.72, 19.95, 29.2],
 'BORL': [11.7, 9.8, 5.6, 6.2, 11.0, None, None, None, None],
 'RIL': [11.6, 9.2, 8.9, None, None, None, None, None, None],
 'NEL': [8.95, 6.97, 5.88, None, None, None, None, None, None],
 'Singapore': [7.23, 4.88, 3.25, 0.53, 4.99, 10.76, 6.58, 3.82, 6.53]}
YEARS_DIST = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
# PPAC Table 4.8, distillate pct (source: CHT). FY2018-19..FY2022-23 from the FY2022-23 edition; FY2023-24..FY2025-26 from the FY2025-26 edition.
DIST = {'Barauni': [87.9, 86.9, 87.1, 85.9, 83.8, 83.8, 83.9, 83.1],
 'Koyali': [81.0, 79.5, 72.1, 76.7, 74.0, 73.9, 74.6, 71.7],
 'Haldia': [69.9, 69.0, 72.2, 72.2, 74.8, 73.1, 75.6, 75.5],
 'Mathura': [76.1, 75.6, 72.3, 74.9, 71.8, 71.3, 69.9, 72.0],
 'Panipat': [82.8, 84.8, 80.2, 83.9, 78.9, 79.1, 79.7, 81.7],
 'Guwahati': [81.0, 83.5, 82.1, 86.4, 81.5, 79.9, 82.8, 83.6],
 'Digboi': [75.8, 72.5, 67.9, 79.2, 72.8, 70.8, 71.9, 72.8],
 'Bongaigaon': [84.8, 80.8, 84.8, 81.3, 80.0, 82.3, 82.6, 83.2],
 'Paradip': [80.8, 80.7, 79.2, 79.6, 79.5, 79.9, 80.6, 80.8],
 'Manali': [75.3, 77.6, 78.4, 74.9, 78.3, 78.4, 78.0, 81.1],
 'HPCL Mumbai': [77.6, 77.0, 76.2, 70.4, 75.9, 76.1, 74.6, 76.7],
 'Visakh': [74.5, 72.1, 74.4, 70.7, 67.9, 71.6, 73.8, 74.2],
 'BPCL Mumbai': [82.2, 84.9, 83.7, 84.4, 85.5, 80.9, 81.1, 83.0],
 'Kochi': [82.5, 84.2, 83.8, 85.4, 83.9, 84.2, 83.5, 83.0],
 'Bina': [None, None, None, 84.3, 85.3, 84.5, 84.4, 84.2],
 'Numaligarh': [87.1, 83.0, 86.4, 85.7, 89.9, 86.5, 90.0, 89.9],
 'Mangalore': [76.8, 76.7, 78.1, 78.8, 77.9, 79.4, 82.3, 82.7],
 'PSU average': [79.6, 80.0, 78.6, 79.6, 78.7, 78.5, 79.1, 79.6]}
# PPAC Table 4.9 fuel & loss, % of crude+other inputs: Paradip by year 2017-18..2022-23; PSU total 2022-23
FUEL_LOSS = {"years": ["2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23"],
             "Paradip_pct": [10.9, 9.8, 9.6, 11.0, 11.0, 10.0],
             "PSU_total_2022_23": {"throughput_mmt": 291.0, "fuel_loss_mmt": 26.0}}
# Table 4.1 / 4.2 / 8.1 / 4.12
OTHER = {
    "paradip_crude_processing_mmt": {"2018-19": 14.6, "2019-20": 15.8, "2020-21": 12.5, "2021-22": 13.2, "2022-23": 13.6},
    "hs_crude_share_pct_2022_23": 77.5,
    "indian_basket_avg_usd_bbl": {"2021-22": 79.18, "2022-23": 93.15},
    "indian_basket_formula": "75.62% sour grades (average of Oman & Dubai) + 24.38% sweet grade (Brent Dated), "
                             "from 2020-21 (PPAC Table 8.1 note)",
    "fx_inr_per_usd": {"2017-18": 64.45, "2018-19": 69.89},
}


def main() -> None:
    out = {
        "_note": "Hand-transcribed from CHT and PPAC public pages (see scripts/build_india_data.py).",
        "cht": {"url": CHT_URL, "basis": "OGJ WW Refining & Complexity survey 2025", "page_last_updated": "10-04-2026",
                "refineries": [dict(company=c, refinery=r, commissioned=y, nci=n, capacity_mmtpa=cap)
                               for c, r, y, n, cap in CHT]},
        "ppac": {"url": PPAC_URL, "edition": "Ready Reckoner FY2022-23 (FY2022-23 provisional)",
                 "grm_years": YEARS_GRM, "grm_usd_bbl": GRM, "distillate_years": YEARS_DIST,
                 "distillate_pct": DIST, "fuel_loss": FUEL_LOSS, **OTHER},
    }
    dest = Path(__file__).resolve().parents[1] / "refinery_design" / "data" / "india_refineries.json"
    dest.write_text(json.dumps(out, indent=1))
    print("wrote", dest)


if __name__ == "__main__":
    main()
