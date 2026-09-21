"""Write ``refinery_design/data/ppac_2526.json``: petrol, ethanol and trade data from PPAC's newest editions.

Sources (all public, fetched September 2026):

* PPAC, *The PPAC Ready Reckoner FY 2025-26* (Table 4.5 production, 4.11 import/export, 6.1 consumption,
  6.10 ethanol blending programme):
  https://ppac.gov.in/download.php?file=rep_studies%2F1784899305_The_PPAC_Ready_Reckoner_FY_2025%E2%80%9326_Final.pdf
  The trade table was parsed from the PDF text (see the tolerance note: parsed totals agree with PPAC's printed
  totals to +/-0.2 MMT) and embedded below as a literal so it can be reviewed line by line.
* PPAC, *Industry Consumption Report POL & NG, January 2026* (monthly MS/naphtha/LPG commentary).
* Ethanol tender facts: news reports (IAmRenew, Business Standard, ChiniMandi) - medium/low confidence, tagged below.

Run: python scripts/build_ppac_2526_data.py
"""
import json
from pathlib import Path

YEARS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
# PPAC Table 4.11: {product: {fiscal year: [quantity MMT, value US$ billion]}}
TRADE = {'exports': {'atf': {'2020-21': [3.5, 1.3],
                     '2021-22': [5.2, 3.7],
                     '2022-23': [7.3, 7.3],
                     '2023-24': [8.6, 7.0],
                     '2024-25': [8.6, 6.1],
                     '2025-26': [6.8, 4.7]},
             'bitumen': {'2020-21': [0.01, 0.003],
                         '2021-22': [0.01, 0.004],
                         '2022-23': [0.01, 0.01],
                         '2023-24': [0.02, 0.009],
                         '2024-25': [0.02, 0.01],
                         '2025-26': [0.03, 0.02]},
             'diesel': {'2020-21': [30.6, 11.1],
                        '2021-22': [32.4, 22.1],
                        '2022-23': [28.5, 28.9],
                        '2023-24': [28.2, 22.1],
                        '2024-25': [28.0, 19.1],
                        '2025-26': [27.3, 19.1]},
             'fuel_oil': {'2020-21': [1.2, 0.3],
                          '2021-22': [1.8, 0.9],
                          '2022-23': [1.8, 1.0],
                          '2023-24': [2.1, 1.0],
                          '2024-25': [2.4, 1.1],
                          '2025-26': [2.0, 0.8]},
             'kerosene': {'2020-21': [0.02, 0.01],
                          '2021-22': [0.01, 0.01],
                          '2022-23': [0.01, 0.01],
                          '2023-24': [0.01, 0.01],
                          '2024-25': [0.01, 0.01],
                          '2025-26': [0.02, 0.01]},
             'ldo': {'2020-21': [0.0, 0.0],
                     '2021-22': [0.0, 0.0],
                     '2022-23': [0.001, 0.002],
                     '2023-24': [0.0, 0.0],
                     '2024-25': [0.0, 0.0],
                     '2025-26': [0.0, 0.0]},
             'lpg': {'2020-21': [0.5, 0.2],
                     '2021-22': [0.5, 0.4],
                     '2022-23': [0.5, 0.5],
                     '2023-24': [0.5, 0.4],
                     '2024-25': [0.6, 0.4],
                     '2025-26': [0.6, 0.4]},
             'lubes': {'2020-21': [0.01, 0.01],
                       '2021-22': [0.01, 0.02],
                       '2022-23': [0.01, 0.03],
                       '2023-24': [0.01, 0.02],
                       '2024-25': [0.02, 0.04],
                       '2025-26': [0.011, 0.02]},
             'naphtha': {'2020-21': [6.5, 2.5],
                         '2021-22': [6.9, 5.0],
                         '2022-23': [5.7, 4.2],
                         '2023-24': [5.3, 3.3],
                         '2024-25': [5.2, 3.4],
                         '2025-26': [6.0, 3.4]},
             'others': {'2020-21': [2.3, 0.9],
                        '2021-22': [2.3, 1.4],
                        '2022-23': [3.7, 2.5],
                        '2023-24': [4.4, 2.8],
                        '2024-25': [3.8, 2.3],
                        '2025-26': [1.8, 1.0]},
             'petcoke': {'2020-21': [0.6, 0.04],
                         '2021-22': [0.2, 0.1],
                         '2022-23': [0.3, 0.1],
                         '2023-24': [0.03, 0.003],
                         '2024-25': [0.7, 0.4],
                         '2025-26': [0.3, 0.1]},
             'petrol': {'2020-21': [11.6, 5.0],
                        '2021-22': [13.5, 10.9],
                        '2022-23': [13.1, 12.9],
                        '2023-24': [13.5, 11.2],
                        '2024-25': [15.8, 11.6],
                        '2025-26': [16.7, 11.5]}},
 'imports': {'atf': {'2020-21': [0.0, 0.0],
                     '2021-22': [0.0, 0.0],
                     '2022-23': [0.0, 0.0],
                     '2023-24': [0.0, 0.0],
                     '2024-25': [0.0, 0.0],
                     '2025-26': [0.0, 0.0]},
             'bitumen': {'2020-21': [2.1, 0.6],
                         '2021-22': [2.6, 1.0],
                         '2022-23': [2.8, 1.2],
                         '2023-24': [3.2, 1.3],
                         '2024-25': [2.9, 1.1],
                         '2025-26': [2.7, 1.0]},
             'crude': {'2020-21': [196.5, 62.2],
                       '2021-22': [212.4, 120.7],
                       '2022-23': [232.7, 157.5],
                       '2023-24': [234.3, 133.4],
                       '2024-25': [243.2, 137.2],
                       '2025-26': [245.8, 123.4]},
             'diesel': {'2020-21': [0.6, 0.3],
                        '2021-22': [0.04, 0.03],
                        '2022-23': [0.3, 0.5],
                        '2023-24': [0.04, 0.04],
                        '2024-25': [0.04, 0.03],
                        '2025-26': [0.04, 0.03]},
             'fuel_oil': {'2020-21': [6.5, 1.9],
                          '2021-22': [9.0, 4.4],
                          '2022-23': [8.6, 4.2],
                          '2023-24': [9.1, 4.1],
                          '2024-25': [7.7, 3.4],
                          '2025-26': [5.4, 2.2]},
             'kerosene': {'2020-21': [0.003, 0.0],
                          '2021-22': [0.0, 0.0],
                          '2022-23': [0.0, 0.0],
                          '2023-24': [0.0, 0.0],
                          '2024-25': [0.0, 0.0],
                          '2025-26': [0.0, 0.0]},
             'lpg': {'2020-21': [16.5, 7.2],
                     '2021-22': [17.0, 12.2],
                     '2022-23': [18.3, 13.3],
                     '2023-24': [18.5, 10.4],
                     '2024-25': [20.7, 12.5],
                     '2025-26': [21.3, 11.3]},
             'lubes': {'2020-21': [2.7, 1.6],
                       '2021-22': [3.1, 2.6],
                       '2022-23': [2.2, 2.3],
                       '2023-24': [2.4, 2.3],
                       '2024-25': [2.9, 2.6],
                       '2025-26': [3.2, 2.7]},
             'naphtha': {'2020-21': [1.2, 0.5],
                         '2021-22': [0.2, 0.2],
                         '2022-23': [0.9, 0.6],
                         '2023-24': [1.2, 0.8],
                         '2024-25': [0.9, 0.6],
                         '2025-26': [1.1, 0.7]},
             'others': {'2020-21': [4.1, 1.0],
                        '2021-22': [2.2, 1.5],
                        '2022-23': [1.8, 1.4],
                        '2023-24': [2.5, 1.6],
                        '2024-25': [2.4, 1.6],
                        '2025-26': [2.5, 1.6]},
             'petcoke': {'2020-21': [8.3, 0.9],
                         '2021-22': [4.2, 1.1],
                         '2022-23': [8.7, 2.3],
                         '2023-24': [11.0, 1.7],
                         '2024-25': [13.2, 1.6],
                         '2025-26': [10.0, 1.4]},
             'petrol': {'2020-21': [1.4, 0.7],
                        '2021-22': [0.7, 0.5],
                        '2022-23': [1.1, 1.1],
                        '2023-24': [0.7, 0.7],
                        '2024-25': [0.2, 0.2],
                        '2025-26': [0.0, 0.0]}}}

CONSUMPTION_YEARS = ["2014-15", "2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
CONSUMPTION_MMT = {   # PPAC Table 6.1 (MS consumption is blended petrol, i.e. includes ethanol)
    "lpg":     [18.0, 19.6, 21.6, 23.3, 24.9, 26.3, 27.6, 28.3, 28.5, 29.7, 31.3, 33.2],
    "ms":      [19.1, 21.8, 23.8, 26.2, 28.3, 30.0, 28.0, 30.8, 35.0, 37.2, 40.0, 42.6],
    "naphtha": [11.1, 13.3, 13.2, 12.9, 14.1, 14.3, 14.1, 13.2, 12.2, 13.8, 13.0, 11.7],
    "hsd":     [69.4, 74.6, 76.0, 81.1, 83.5, 82.6, 72.7, 76.7, 85.9, 89.6, 91.4, 94.7],
    "atf":     [5.7, 6.3, 7.0, 7.6, 8.3, 8.0, 3.7, 5.0, 7.4, 8.2, 9.0, 9.2],
}
PRODUCTION_MMT = {    # PPAC Table 4.5, all sources (refineries + fractionators)
    "years": YEARS,
    "hsd": [100.4, 107.2, 113.8, 115.9, 118.2, 120.8], "ms": [35.8, 40.2, 42.8, 45.1, 48.3, 49.8],
    "naphtha": [19.4, 20.0, 17.0, 18.3, 17.9, 18.4], "atf": [7.1, 10.3, 15.0, 17.1, 17.8, 16.4],
    "lpg": [12.1, 12.2, 12.8, 12.8, 12.8, 13.1], "fuel_oil": [7.4, 8.9, 10.3, 10.4, 10.9, 10.3],
    "petcoke": [12.0, 15.5, 15.4, 15.1, 15.0, 14.8],
}
EBP = {   # PPAC Table 6.10 (Ethanol Blending Programme)
    "ESY 2021-22 (Dec21-Nov22)": {"ethanol_crore_litres": 408.1, "blend_pct_volume": 8.10},
    "ESY 2022-23 (Dec22-Mar23)": {"ethanol_crore_litres": 185.5, "blend_pct_volume": 11.58},
    "ESY 2024-25 (Nov-Oct)": {"ethanol_crore_litres": 1040.1, "blend_pct_volume": 19.24},
    "ESY 2025-26 (Nov-Mar)": {"ethanol_crore_litres": 423.4, "blend_pct_volume": 19.99},
    "note": "PPAC's FY2022-23 edition and FY2025-26 edition report different ESY windows; both are quoted as printed.",
}
ICR_JAN_2026 = {   # PPAC Industry Consumption Report, January 2026
    "ms_mmt_jan_2026": 3.51, "ms_growth_jan_pct": 6.1, "ms_growth_apr_jan_pct": 6.4,
    "naphtha_domestic_apr_jan_mmt": 9.77, "naphtha_growth_apr_jan_pct": -11.9, "naphtha_petchem_share_pct": 94,
    "lpg_mmt_jan_2026": 3.03, "lpg_growth_jan_pct": 7.0, "hsd_apr_jan_tmt": 78325, "hsd_growth_apr_jan_pct": 3.1,
}
TENDER = {   # news-reported; confidence tags
    "esy_2025_26_cycle1": {"requirement_crore_litres": 1050, "offers_crore_litres": 1776.49, "sugarcane_offers": 471.63, "grain_offers": 1304.86,
                           "sugar_based_share_pct": 28, "fci_rice_price_rs_per_kl": 60320, "fci_rice_price_rs_per_kl_prev": 58500,
                           "source": "IAmRenew (fetched); Business Standard / ChiniMandi snippets", "confidence": "medium"},
    "esy_2025_26_q4_extra": {"additional_crore_litres": 149, "note": "Supreme Court allowed OMCs to award to Q-IV bidders",
                             "source": "Business Standard (search snippet; page blocked)", "confidence": "low"},
    "esy_2026_27_expected": {"demand_crore_litres_low": 1150, "demand_crore_litres_high": 1212, "petrol_bn_litres_assumed": 60.6,
                             "source": "ChiniMandi (search snippet)", "confidence": "low"},
    "installed_capacity_crore_litres": 2000, "e20_reached": "ESY 2025-26 (five years ahead of the 2030 schedule)",
    "sources_note": "No ESY 2026-27 OMC tender allocation was found; the figures are expected demand, not a tender.",
}
FEEDSTOCK_MIX_PCT = {   # PPAC Table 6.10(A), ESY 2022-23 .. 2025-26 (share of ethanol receipts)
    "Sugarcane juice": [25.4, 9.6, 15.9, 26.9], "B-heavy molasses": [46.5, 22.0, 13.3, 7.3], "C-heavy molasses": [1.1, 8.5, 1.6, 1.2],
    "Damaged food grains": [6.3, 17.2, 7.7, 5.0], "Surplus food grains": [14.6, 0.0, 13.5, 21.6], "Maize": [6.2, 42.7, 47.9, 38.0],
    "_esy": ["2022-23", "2023-24", "2024-25", "2025-26"],
    "_note": "column order as printed in PPAC Table 6.10(A); the printed header row was not machine-readable, so the year "
             "assignment is inferred from the ESY columns listed in the table title.",
}


def main() -> None:
    out = {"_note": "See scripts/build_ppac_2526_data.py for sources.", "years": YEARS, "trade_usd_bn_and_mmt": TRADE,
           "consumption_years": CONSUMPTION_YEARS, "consumption_mmt": CONSUMPTION_MMT, "production_mmt": PRODUCTION_MMT,
           "ebp": EBP, "icr_jan_2026": ICR_JAN_2026, "ethanol_tender": TENDER, "feedstock_mix_pct": FEEDSTOCK_MIX_PCT}
    dest = Path(__file__).resolve().parents[1] / "refinery_design" / "data" / "ppac_2526.json"
    dest.write_text(json.dumps(out, indent=1))
    print("wrote", dest)


if __name__ == "__main__":
    main()
