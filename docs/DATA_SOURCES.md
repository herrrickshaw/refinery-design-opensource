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

## Petrochemical economics - partial

* **Verified (search summaries of the OGJ / IndianOil material):** Paradip's
  680 kt/y polypropylene plant cost Rs 3,150 crore, uses Spheripol technology and
  is integrated with the refinery's INDMAX (light-olefin FCC) unit. Converted at
  PPAC's FY2018-19 Rs 69.89/$ = $451 M.
* **Verified (search summaries of FCC literature):** conventional FCC propylene
  ~6 wt% of feed; >9 wt% with ZSM-5 additive at 10-20 wt% loading; each 5 wt%
  additive dilutes catalyst activity 1-2 wt%; propylene-mode units above 20 wt%.
* **Not available:** propylene, polypropylene, naphtha, LPG and petcoke prices.
  The OilPriceAPI feed tried here carries crude (Brent, Dubai, Oman, WTI, Urals)
  and US gasoline/diesel/jet only. Two industry articles on refining-petrochemical
  integration were read and contain no usable price or margin figures. Hence the
  break-even framing.
* **Assumptions, unsourced:** PP conversion opex, hurdle rate, plant life,
  the split of propylene-mode propylene between forgone gasoline and LCO.

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
