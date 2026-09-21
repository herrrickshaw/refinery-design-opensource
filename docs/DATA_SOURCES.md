# Data sources and what was verified

Same standard as every sibling document: not endorsement, every entry
fetched and inspected at the time of writing (September 2026), unverified
claims flagged rather than presented as confirmed.

## Crude assays - verified, values extracted

ExxonMobil publishes crude assays as downloadable workbooks:
<https://corporate.exxonmobil.com/what-we-do/energy-supply/crude-trading/crude-oil-assays>.
Eight were downloaded and parsed by `scripts/build_assay_data.py`
(Bakken, Azeri BTC, Qua Iboe, Upper Zakum, Alaska North Slope, Dalia, Cold Lake
Blend, Kearl). Only property *values* are stored in
`refinery_design/data/assays.json`; the workbooks are not redistributed. The
page states the materials are provided "courtesy of ExxonMobil" with no
representations or warranties on accuracy - each user must make their own
determination. Check current assays before any commercial use.

Things found while parsing that users should know:

* The TBP curves are extrapolated by the assay provider to ~700 &deg;C
  (~92-98% distilled).
* Cold Lake's lightest assay cut is labelled "C5-65" but its yield lumps in the
  dissolved C4- gas (4.4 wt% vs ~2-3 wt% for the true C5-65 slice); assays
  define the lightest cut inconsistently, so cross-checks start at 65 &deg;C.
* Narrow vacuum cuts often report Ni/V as 0.0 (below detection); whole-cut
  metals appear only in the aggregate residue cuts.

## Nelson complexity factors - verified

Wikipedia, "Nelson complexity index" (factor table, 1998 and older vintages, and
the Jamnagar reference value 21.1). A second source found by search lists
hydrotreating at 2.0 and coking at 5.5; the differences are why the index is
treated as approximate to ~10% between sources.

## Paradip refinery - verified (capacities), search snippet only (yields)

Oil & Gas Journal, "Indian Oil commissions Paradip refinery":
<https://www.ogj.com/refining-processing/refining/operations/article/17246528/indian-oil-commissions-paradip-refinery>
- "15 million-tonne/year, full-conversion refinery", Nelson complexity 12.2 (as of commissioning; superseded by CHT's 10.6 below),
FCC 4.2 mtpa, delayed coker 4.1 mtpa, CCR reformer 2.9 mtpa, naphtha
hydrotreating 3.9 mtpa, diesel hydrotreater 120,000 b/d, and further units.
Three entries carry units that do not scale against a 15 mtpa plant as printed
("105,000-tpy" VGO HDT, "650-tpy" alkylation, "300-tpy" isomerisation); they are
read as b/d, kt/yr and kt/yr and flagged wherever used.

IndianOil's own pages redirected (HTTP 307) and could not be fetched directly;
the "81.1% distillate yield, no black oil" figure comes from a search-result
summary of IndianOil's material, not a fetched page, and its definition of
"distillate" is unstated - it is used for plausibility only.

## CHT - Nelson complexity of Indian refineries - verified

Centre for High Technology, MoPNG, "Refinery complexity Index":
<https://cht.gov.in/refinery-complexity-index> (page last updated 10-04-2026).
A table of 19 refineries with commissioning year, nameplate capacity and NCI
"based on OGJ WW Refining & Complexity survey 2025" (Paradip 10.6, Panipat 10.5,
Kochi 11.2, Haldia 11.8, Bina 11.8, Barauni 6.0 ...; PSU total 158.6 MMTPA). The
page gives no formula or factor table. Hand-transcribed into
`refinery_design/data/india_refineries.json` by `scripts/build_india_data.py`;
capacities are checked against the page's own totals in `tests/test_india.py`.

## PPAC - refinery margins, yields, fuel & loss - verified

Petroleum Planning & Analysis Cell, *Ready Reckoner FY2022-23*
(<https://ppac.gov.in>; the PDF URL is in `scripts/build_india_data.py`): Table 4.1
capacity and throughput, 4.7 GRM by company FY2017-18 to FY2022-23 (FY2022-23
provisional; GRM defined per EIA as product revenue minus raw-material cost;
North-East refineries include an excise benefit), 4.8 distillate yield by PSU
refinery, 4.9 fuel & loss, 4.12 exchange rates, 8.1 the Indian-basket formula
(75.62% mean of Oman and Dubai + 24.38% Brent Dated; FY2022-23 average $93.15/bbl,
FY2021-22 $79.18). PPAC publishes GRM by company, not by refinery, and does not
define "distillate". Newer editions of the Ready Reckoner may exist; this repo
uses FY2022-23.

## PPAC Ready Reckoner FY 2025-26 (newest edition) - verified

`The PPAC Ready Reckoner FY 2025-26`
(<https://ppac.gov.in/download.php?file=rep_studies%2F1784899305_The_PPAC_Ready_Reckoner_FY_2025%E2%80%9326_Final.pdf>)
supersedes the FY2022-23 edition for: Table 4.5 production, 4.7 GRM (FY2023-24 to FY2025-26; IOCL and MRPL
stopped publishing GRM for FY2025-26), 4.8 distillate yield, 4.11 import/export (FY2020-21 to FY2025-26), 6.1
consumption (MS 35.0 -> 37.2 -> 40.0 -> 42.6 MMT FY2022-23 to FY2025-26) and 6.10 ethanol blending (ESY 2024-25:
1,040.1 crore litres, 19.24%; ESY 2025-26 Nov-Mar: 423.4 crore litres, 19.99%). The trade table was parsed from the
PDF text and agrees with PPAC's printed totals to +/-0.4 MMT (`tests/test_trade_ethanol.py`); the parser slices
on newlines, not `splitlines()` (form-feed characters shift line numbers). PPAC Industry Consumption Report
January 2026 (fetched): MS 3.51 MMT (+6.1%), Apr-Jan +6.4%; naphtha domestic consumption 9.77 MMT (-11.9%,
94% petrochemicals). Figures inside charts and the ESY/feedstock column assignment of Table 6.10(A) were not
machine-readable; the latter is flagged in the data file.

## NRL - partly verified

Numaligarh's domestic-crude sourcing (3,033 kt from OIL/ONGC of 3,066 kt processed, FY2024-25; expansion to
9 MMTPA with imported crude via Paradip, commissioned Dec 2025) is from web-search summaries of NRL/Oil India
reporting (medium-low confidence). The excise-duty footnote is PPAC's own (verified). How domestic crude is
priced relative to imports was not found.

## Ethanol tenders - news-sourced, medium/low confidence

OMC ESY 2025-26 Cycle 1 tender (IAmRenew, fetched): requirement 1,050 crore litres, offers 1,776.49 (sugarcane
471.63, grain 1,304.86), FCI-rice ethanol Rs 60,320/kl (Rs 58,500 the year before). Supreme Court allowed a further
149 crore litres for Q-IV (Business Standard - page blocked, snippet only). ESY 2026-27 expected demand
1,150-1,212 crore litres (ChiniMandi snippet; 60.6 bn litres of petrol x 20%). **No ESY 2026-27 tender
allocation was found.** Capacity ~2,000 crore litres against ~1,000-1,050 demand.

## Petrochemical economics - partial

* **Verified (search summaries of the OGJ / IndianOil material):** Paradip's
  680 kt/y polypropylene plant cost Rs 3,150 crore, uses Spheripol technology and
  is integrated with the refinery's INDMAX (light-olefin FCC) unit. Converted at
  PPAC's FY2018-19 Rs 69.89/$ = $451 M.
* **Verified (search summaries of FCC literature):** conventional FCC propylene
  ~6 wt% of feed; >9 wt% with ZSM-5 additive at 10-20 wt% loading; each 5 wt%
  additive dilutes catalyst activity 1-2 wt%; propylene-mode units above 20 wt%.
* **Not available:** propylene, naphtha, LPG and petcoke prices. The OilPriceAPI feed
  carries crude (Brent, Dubai, WTI, Urals; Oman not recognised) and US gasoline/diesel/jet
  only. Two industry articles on refining-petrochemical integration contain no usable price
  or margin figures. Polypropylene prices are covered by the next section; propylene is not.
* **Assumptions, unsourced:** PP conversion opex, hurdle rate, plant life,
  the split of propylene-mode propylene between forgone gasoline and LCO.

## Polypropylene and propylene prices - PP verified (primary), propylene not

* **IOCL PP ex-works price lists - verified, primary.** Rs/MT, "basic & cash prices, GST
  additional", from the PDFs IOCL's authorised distributor (Turakhia Polymers, DCA cum CS of
  IOCL) publishes, mirrored at <https://www.plastemart.com/polymer-pricelist/pp-iocl/4/33>.
  Read at 01-01-2026, 01-03-2026 and 11-09-2026 (Thane column): homopolymer injection 1110MG
  Rs 90,452 / 99,952 / 154,452. Plastemart also reports the price *revisions* (IOCL +Rs 1,500 to
  5,000/MT on 1 Sep 2026; +3,000 to 5,000 on 11 Sep). A distributor list, not IOCL's own site;
  prices are before discounts and freight.
* **USD/INR 95.82 (17 Sep 2026) - medium confidence:** from a web-search summary of the
  exchange-rate history, not a fetched rate page.
* **Crude snapshot 2026-09-21 (OilPriceAPI):** Brent $102.47, Dubai $116.35, WTI $94.62, Urals
  $106.45. Oman is not offered; Dubai stands in for it in PPAC's basket formula.
* **Aggregator snippets - low confidence, some conflicting:** India PP $1,050 (Jan 2026) rising to
  $1,319 (Mar) in one result and $1,080 (Mar) in another, against +10.5% Jan-Mar on the IOCL list.
  Not used in any calculation.
* **Propylene - no 2026-09 price exists in anything accessible.** Snippets only: India CFR ~$760
  (Sep 2025), ~$794 (Oct), ~$792 (Dec) from Procurement Resource; Northeast Asia ~$1,010 (Mar 2026)
  from IMARC. Polymerupdate lists "Propylene CFR India" daily but behind a login, and its PP price
  pages return blanks without one. `PetchemPriceDeck.propylene_usd_t` is left `None` by default.

## Refinery rundowns - Digital Refining

Articles read at <https://www.digitalrefining.com>: "Maximising distillate production from the FCC
unit" (LCO +4-6 vol% by lowering the gasoline end point, ~5 vol% for 430 -> 380 degF; riser 10-30 degF
cooler in distillate mode), "FCC product fractionation for maximum LCO" (LCO end point 640 degF /
338 degC, flash point 130 degF / 54 degC; the yield figure itself is in a chart not in the text),
"Refining/petrochemical integration - FCC gasoline to petrochemicals" (conventional FCC propylene
3-5%, high-severity 15-28%; FCC gasoline sulfur 1,000-2,000 ppm; 50-70% aromatics in high-severity
naphtha) and "Refining-petrochemicals integration: an Indian view" and "Increasing refinery
profitability via propylene maximisation" (no usable numbers). From search summaries only: FCC ~20 vol%
of the gasoline pool, LCO ~5% of the diesel pool, LCO cetane ~20. The figures are used as the
`rundown.py` slope and as cross-checks; regional context (mostly US/global) differs from India.

## Delayed-coker correlations - partially verified

Coke = 1.6 x CCR and gas = 7.8 + 0.144 x CCR (Gary & Handwerk) were confirmed
in a search summary of the literature comparing coking correlations (Munoz et
al., *Energy & Fuels*, doi:10.1021/ef4014423). The book's naphtha/gas-oil
equations could not be confirmed and are deliberately not used.

## FCC operating ranges - NOT page-verified

The commonly cited envelopes used in the screening flags and calibration
targets (ROT 520-540 &deg;C, cat/oil 5-9, regenerator 680-730 &deg;C, riser
residence 2-3 s, conversion 70-80 wt%, coke 4.5-6 wt%) are the ones in standard
FCC references such as Sadeghbeigi's handbook. The handbook itself was not
accessible, so these were **not verified page by page**; they are labelled as
typical-range assumptions everywhere they are used. FCC sulfur distribution
(35-45% of feed S to H2S, 2-5% to coke, 2-10% to gasoline) was confirmed in a
search summary of FCC literature.

## Textbook correlations - checked numerically, not against the books

Riazi-Daubert, Watson-Nelson cp, Fishtine latent heat and the Refutas index
are implemented from their standard published forms and checked numerically:
n-hexane latent heat within ~1% of NIST (337.7 vs 335 kJ/kg), n-hexadecane
molecular weight within ~3% of 226.4, CoolProp enthalpies against JANAF (CO2,
N2 within 2%) and IAPWS steam tables.

## Licensor / catalyst vendors

No licensor (UOP/Honeywell, Axens, KBR, Technip, Shell Global Solutions) or
catalyst-vendor data was used or verified; nothing here should be read as
reproducing any proprietary design basis.
