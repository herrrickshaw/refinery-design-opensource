"""Write ``refinery_design/data/crude_sourcing.json``: crude basket, import bill, rupee-settlement and bilateral-trade data.

Sources (fetched September 2026):

* PPAC *Ready Reckoner FY 2025-26*: Table 8.1 (Indian basket price, annual and 2026 monthly; the basket is Brent
  Dated for sweet + mean of Oman & Dubai for sour, from March 2026 on crude actually imported), Table 8.24
  (quantity and value of Indian crude imports), and the chapter highlights on the 28-Feb-2026 US-Israel-Iran
  conflict and the Strait of Hormuz.  https://ppac.gov.in (URL in ``build_ppac_2526_data.py``).
* EcoNiti Daily Brief, 25 Jul 2026 (rupee-settled imports; fetched): medium confidence.
* Outlook Business, 24 Dec 2023 (MoPNG statement on suppliers' objections; fetched): medium confidence.
* Trade balances: SEAIR "Top 10 trading partners of India 2025-26" and IBEF (web-search snippets): LOW confidence.
* Urals differentials: news reports (web-search snippets): LOW confidence, some conflicting.
* Live benchmarks: OilPriceAPI market overview, 21 Sep 2026 (see ``build_petchem_prices.py``).

Run: python scripts/build_crude_sourcing_data.py
"""
import json
from pathlib import Path

BASKET_ANNUAL = {  # PPAC Table 8.1, $/bbl, fiscal year
    "2014-15": 84.16, "2015-16": 46.17, "2016-17": 47.56, "2017-18": 56.43, "2018-19": 69.88, "2019-20": 60.47,
    "2020-21": 44.82, "2021-22": 79.18, "2022-23": 93.15, "2023-24": 82.58, "2024-25": 78.56, "2025-26": 70.99,
}
BASKET_2026_MONTHLY = {"2026-01": 63.08, "2026-02": 69.01, "2026-03": 113.49, "2026-04": 114.48, "2026-05": 106.23, "2026-06": 83.22}
BASKET_PEAK = {"value": 135.0, "when": "first week of April 2026", "source": "PPAC Ready Reckoner FY2025-26 chapter highlights"}
CRUDE_IMPORTS = {  # PPAC Table 8.24: MMT, million bbl, US$ million, Rs crore, $/bbl (PPAC-approximate, 1 MT = 7.33 bbl)
    "2018-19": [226.5, 1660.2, 111915, 783183, 67.41], "2019-20": [227.0, 1663.6, 101376, 717001, 60.94],
    "2020-21": [196.5, 1440.1, 62248, 459779, 43.23], "2021-22": [212.4, 1556.8, 120675, 901262, 77.52],
    "2022-23": [232.7, 1705.7, 157531, 1260372, 92.36], "2023-24": [234.3, 1717.1, 133366, 1105176, 77.67],
    "2024-25": [243.2, 1782.8, 137174, 1160618, 76.94], "2025-26": [245.8, 1801.5, 123379, 1092248, 68.49],
}
RUPEE_SETTLED = {  # EcoNiti Daily Brief 2026-07-25 (all imports, not only crude)
    "fy_rs_crore": {"2023-24": 99680, "2024-25": 113000, "2025-26": 172000},
    "dec25_feb26_rs_crore": 42506, "dec25_feb26_share_of_imports_pct": 2.4,
    "mar_may26_rs_crore": 138000, "mar_may26_usd_bn": 14.6, "mar_may26_share_of_imports_pct": 7.1,
    "russian_crude_imports_usd_bn": {"2026-02": 2.49, "2026-03..05": 17.13}, "russian_crude_mar_may_yoy_pct": 30,
    "source": "EcoNiti Daily Brief, 25 Jul 2026", "confidence": "medium",
}
SUPPLIER_OBJECTIONS = {
    "statement": "Suppliers cited repatriation of funds in the preferred currency and high transaction costs of conversion along with "
                 "exchange-fluctuation risk; IOC incurred high transaction costs as suppliers passed the extra costs on.",
    "fy2022_23_psu_rupee_settled_crude": 0, "middle_east_share_of_crude_fy2022_23_pct": 58,
    "source": "Outlook Business, 24 Dec 2023 (citing MoPNG)", "confidence": "medium",
}
BILATERAL_USD_BN = {   # India exports to / imports from; FY2025-26 unless noted. LOW confidence (aggregator snippets)
    "UAE": {"exports": 37.36, "imports": 63.89, "fy": "2025-26"}, "Russia": {"exports": 4.49, "imports": 55.37, "fy": "2025-26"},
    "Iraq": {"exports": 2.96, "imports": 24.56, "fy": "2025-26"}, "Saudi Arabia": {"exports": 11.76, "imports": 30.12, "fy": "2024-25"},
    "confidence": "low", "source": "SEAIR / IBEF web-search snippets; imports are TOTAL imports (crude-dominant for Russia/Iraq/Saudi)",
}
CRUDE_SHARE_Q1_FY26_PCT = {"Iraq": 19.89, "Russia": 17.92, "Saudi Arabia": 16.03, "UAE": 11.00,
                           "confidence": "low", "source": "tradeint.com web-search snippet (Q1 FY2025-26, by value)"}
UDALS_VS_BRENT = [   # delivered India, $/bbl vs Dated Brent (negative = discount); news reports, LOW confidence
    {"when": "2026-02 loadings", "usd_bbl": -10.0}, {"when": "2026-03/04 loadings", "usd_bbl": 4.5},
    {"when": "2026-06/07", "usd_bbl": -10.0}, {"when": "2026-09-21 live (Urals 106.45 vs Brent 102.47)", "usd_bbl": 3.98},
]
RUSSIA_NEWS = {   # 2026 reporting; web-search summaries and fetched pages - MEDIUM/LOW confidence, some sources conflict
    "volumes_mbpd": {"2026-07": 2.8, "2026-08": 2.0, "2026-09_first_14_days": 1.42},
    "share_of_india_crude_pct": {"2026-07": 55.9, "2026-08": 45.0},
    "august_fall_pct": 26.3,
    "august_fall_reasons": ["US tariff pressure", "Ukrainian drone strikes (~40% of Russian export capacity removed by March 2026, per one analysis)",
                            "China outbidding (Russian imports ~1.7 mb/d in August vs ~1.4 in July)"],
    "discount_to_brent_reports": [
        {"period": "post-2022 sanctions era", "usd_bbl": -11.5, "note": "$10 to over $13 below Brent"},
        {"period": "pre-conflict (Bloomberg via analysis site)", "usd_bbl": -3.0}, {"period": "2026-01 delivery", "usd_bbl": -5.0},
        {"period": "2026-02 loadings, delivered India", "usd_bbl": -10.0}, {"period": "2026-03/04", "usd_bbl": 4.5, "note": "first-ever premium to Dated Brent"},
        {"period": "2026-07", "usd_bbl": -10.0, "note": "one source: discounts widened to more than $10"},
        {"period": "2026-08", "usd_bbl": 0.0, "note": "another source: approximate parity or slight premium - CONFLICTS with the July report"}],
    "freight_usd_bbl": {"Novorossiysk to India west coast (Suezmax)": 20.0, "Baltic ports": 13.0, "note": "from one analysis; freight premium of ~$7/bbl constrains discount depth"},
    "refiners": {"Reliance": "purchases fell to ~292,000 b/d (EU rules on products from Russian crude)", "Nayara": "~400,000 b/d after maintenance; already under sanctions",
                 "state_refiners": "IOC, BPCL, HPCL increased purchases"},
    "us_waivers": "30-day US waiver for stranded Russian cargoes (March 2026), a second waiver, and reported expiry/lapse by May-June 2026; not a broad relaxation",
    "august_2026_import_bill": {"usd_bn": 11.7, "vs_aug_2025_usd_bn": 9.9, "volume_mmt": 19.0, "avg_usd_bbl": 90.19, "avg_usd_bbl_aug_2025": 69.11, "avg_usd_bbl_jul_2026": 82.04,
                                "source": "The Wire (fetched)"},
    "indian_basket_14_sep_2026_usd_bbl": {"value": 128.70, "source": "BusinessToday 15 Sep 2026 (fetched); differs from the $112.97 obtained by applying PPAC's formula to the 21-Sep live feed (Dubai used for Oman)"},
    "payment_currency_for_russian_crude": "NOT found in any source; rupee-settled imports rose sharply in Mar-May 2026 (EcoNiti) alongside Russian purchases, which is circumstantial",
    "sources": ["EcoNiti 2026-09-03", "BusinessToday 2026-09-15", "The Wire (Aug-2026 import bill)", "discoveryalert analyses", "Euronews 2026-03-06 (waiver)", "OilPrice.com (Nayara)"],
    "confidence": "low-medium",
}
LCS_CLAIM = {"statement": "Indian traders pay ~2% average transaction cost when exporting to the UAE; the India-UAE Local Currency Settlement "
                          "framework (RBI-CBUAE MoU, 2023) removes conversion through a third currency. Not quantified in basis points.",
             "source": "Deccan Herald / DrishtiIAS (web-search snippet)", "confidence": "low"}


def main() -> None:
    out = {"basket_annual_usd_bbl": BASKET_ANNUAL, "basket_2026_monthly_usd_bbl": BASKET_2026_MONTHLY, "basket_peak": BASKET_PEAK,
           "crude_imports": {"columns": ["mmt", "million_bbl", "usd_million", "rs_crore", "usd_bbl_ppac"], "rows": CRUDE_IMPORTS},
           "rupee_settled": RUPEE_SETTLED, "supplier_objections": SUPPLIER_OBJECTIONS, "bilateral_trade_usd_bn": BILATERAL_USD_BN,
           "crude_share_q1_fy26_pct": CRUDE_SHARE_Q1_FY26_PCT, "urals_vs_brent": UDALS_VS_BRENT, "lcs_claim": LCS_CLAIM, "russia_news_2026": RUSSIA_NEWS}
    dest = Path(__file__).resolve().parents[1] / "refinery_design" / "data" / "crude_sourcing.json"
    dest.write_text(json.dumps(out, indent=1))
    print("wrote", dest)


if __name__ == "__main__":
    main()
