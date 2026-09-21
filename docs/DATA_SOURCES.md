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
- "15 million-tonne/year, full-conversion refinery", Nelson complexity 12.2,
FCC 4.2 mtpa, delayed coker 4.1 mtpa, CCR reformer 2.9 mtpa, naphtha
hydrotreating 3.9 mtpa, diesel hydrotreater 120,000 b/d, and further units.
Three entries carry units that do not scale against a 15 mtpa plant as printed
("105,000-tpy" VGO HDT, "650-tpy" alkylation, "300-tpy" isomerisation); they are
read as b/d, kt/yr and kt/yr and flagged wherever used.

IndianOil's own pages redirected (HTTP 307) and could not be fetched directly;
the "81.1% distillate yield, no black oil" figure comes from a search-result
summary of IndianOil's material, not a fetched page, and its definition of
"distillate" is unstated - it is used for plausibility only.

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
