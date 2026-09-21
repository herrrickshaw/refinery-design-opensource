# External validation

Written to the same standard as the sibling repos: what was checked against
an outside source, what was only *calibrated*, what was found along the way,
and what is not validated at all.

## 1. Real assays: internal and cross-consistency

The eight assays are real published data (`DATA_SOURCES.md`). Two independent
checks on how this repo *uses* them, both in the test suite:

| Check | Result |
|---|---|
| Cut density implied by the TBP curve (`rho_crude x dwt/dvol`) vs the density the assay itself reports for each narrow cut (72 cuts, 65 &deg;C and up) | max deviation **0.88%**, mean 0.35% |
| Sulfur in the six crude/vacuum-unit cuts vs sulfur in the crude | closes to **0.0%** for all eight crudes (cut weighting conserves mass) |
| Whole-refinery mass balance (CDU/VDU + FCC + coker pools) | closes to 1e-9 for every crude |

Property helpers against reference values: n-hexane latent heat 337.7 vs 335
kJ/kg (NIST); n-hexadecane molecular weight (Riazi-Daubert) +3.0% vs 226.4;
CoolProp CO2 / N2 sensible enthalpy within 2% of JANAF; steam enthalpy at
250 &deg;C / 4 bar within 8 kJ/kg of the IAPWS tables.

## 2. FCC: calibrated, behaviourally checked, not plant-validated

**What is and is not validated.** The riser rate constants were fitted by
least squares to *typical published yield ranges* at a reference feed. That
makes the reference-case agreement below a calibration, **not a validation**.
No plant data was available or used.

Reference case (Watson K 11.8 VGO, ROT 530 &deg;C, feed preheat 250 &deg;C,
riser 2.5 s, full-burn regenerator; the heat balance is solved, not imposed):

| Quantity | Model | Commonly cited range |
|---|---|---|
| Conversion | 76.8 wt% | 70-80 |
| Gasoline | 49.4 wt% | 44-54 |
| LPG | 17.8 wt% | 14-22 |
| Dry gas | 3.6 wt% | 2-5 |
| Coke | 5.95 wt% (delta coke 0.78) | 4.5-6.5 (0.5-1.1) |
| Cat/oil | 7.6 | 6-9 |
| Regenerator | 708 &deg;C | 680-740 |
| Riser (1.3 m x 40 m, 6.4 -> 20 m/s) | inlet ~4-9 m/s, exit 15-25 m/s | typical |
| Flue-gas O2 (10% excess air) | 2.0 vol% dry | ~1.5-3 |

The ranges are the commonly cited ones (Sadeghbeigi, *FCC Handbook*) but were
not verified page by page - see `DATA_SOURCES.md`. The calibration constants
happen to place the heat-balance solution in the right place, and the coke
target was chosen to make that so (an earlier fit with 4.4 wt% coke closed the
balance at 631 &deg;C and cat/oil 13.9 - not a plausible operating point).

**What *is* tested independent of the calibration** (behaviours the model was
not fitted to; all in `tests/test_fcc.py`):

* gasoline passes through a maximum against cat/oil (over-cracking);
* higher riser outlet temperature raises LPG and dry gas and, past the
  optimum, lowers gasoline;
* hotter feed preheat lowers cat/oil;
* the heat balance closes to < 0.5 kJ/kg and the riser demand equals the
  catalyst enthalpy drop;
* partial burn needs less air per kg coke but more coke overall;
* SO2 and gasoline sulfur scale linearly with feed sulfur;
* a resid feed (CCR 20 wt%) *cannot* close the balance without a catalyst
  cooler and is refused with an actionable message.

## 3. Real refinery: IndianOil Paradip (15 mtpa)

Capacities from Oil & Gas Journal; complexity from the Centre for High
Technology; yields and margins from PPAC (`DATA_SOURCES.md`).

**A correction made along the way.** An earlier version of this repo benchmarked
against a Nelson index of 12.2 - the figure IndianOil quoted at commissioning
(OGJ, 2016). CHT's page (https://cht.gov.in/refinery-complexity-index, "NCI
based on OGJ WW Refining & Complexity survey 2025") gives Paradip **10.6**. The
benchmark now uses the CHT/OGJ-survey value; the older number is kept only as
`IOC_COMMISSIONING_NCI`.

**Nelson complexity from the published unit list** (`examples/paradip_check.py`):

| Factor set | VDU/CDU | Units counted | NCI | vs CHT 10.6 |
|---|---|---|---|---|
| 1998 | 0.6 | unambiguous only | 7.55 | -29% |
| 1998 | 1.0 | unambiguous only | 8.35 | -21% |
| 1998 | 0.6 | + ambiguous-unit readings | 10.51 | **-1%** |
| 1998 | 1.0 | + ambiguous-unit readings | 11.31 | **+7%** |
| older | 0.6 | + ambiguous-unit readings | 11.12 | +5% |
| older | 1.0 | + ambiguous-unit readings | 11.92 | +12% |

The published unit list is partial and three entries have units that do not
scale as printed, so the honest result is a range: counting every listed unit
gives 10.5-11.9, which **brackets** CHT's 10.6; counting only the unambiguous
ones falls 15-29% short (both factor sets). The list omits the hydrogen plant, sulfur plants and
polypropylene unit (the last has no Nelson factor in any case).

**Distillate yield (PPAC Table 4.8).** PPAC reports Paradip at 80.8 / 80.7 / 79.2
/ 79.6 / 79.5% for FY2018-19 to FY2022-23 (mean 80.0%; PSU average 78.7-80.0%).
The flowsheet on the fitted basket gives 79.3% (raw VGO) to 79.8% (hydrotreated
VGO) LPG + gasoline-range + middle distillate. PPAC does not define
"distillate", so this is agreement in magnitude, not a reproduction. (Note the
earlier-quoted 81.1% from IndianOil's material is also consistent.)

**Which crude basket loads the published units?** Paradip's coker is 4.1 mtpa
and FCC 4.2 mtpa against a 15 mtpa CDU (27.3% and 28.0%). Fitting ONE
parameter - the heavy-crude fraction of a two-crude slate - so that
vacuum-residue yield equals the coker ratio gives **43 vol% Cold Lake Blend +
57 vol% Upper Zakum (API 27.0, 2.9 wt% S)**. The VGO yield of that same slate,
an independent prediction, is **28.1%** against the published FCC ratio of
**28.0%**. This is consistent with OGJ's statement that the refinery is
configured for "a broad basket of crudes, including less expensive heavy and
high-sulfur crude grades". It is a consistency check, not proof: two proxy
crudes stand in for a real, changing basket, and the units may take other
streams.

**A finding, not a fit.** Run through this repo's flowsheet at 15 mtpa (~290
kbpd), that basket's VGO cannot run raw in an FCC: regenerator 816 &deg;C,
conversion 60%, gasoline sulfur ~5,800 ppm. Paradip's own unit list includes a
VGO hydrotreater - the feed-pretreat unit the model says is required. With the
illustrative pretreat (`RefineryConfig(vgo_hydrotreat=True)`, sized: ~250 m3,
LHSV 2.0) the FCC improves to 68% conversion / 772 &deg;C / ~520 ppm gasoline
sulfur. Even so it still flags a hot regenerator, i.e. the heaviest baskets need
a catalyst cooler or a deeper pretreat as well; the model reports this rather
than hiding it.

**Yields (plausibility only).** The same run gives 79-80 wt% of crude as LPG +
gasoline-range + middle distillate and only 2.7-3.4 wt% black oil (FCC slurry),
with the residue going to the coker - the 'no black oil' character IndianOil
claims for Paradip.

## 4. Things found along the way

* **Heat balance sets coke, not feed.** Across very different VGOs the solver
  returns nearly identical coke (5.9-6.0 wt%) and moves cat/oil and regenerator
  temperature instead - the textbook FCC behaviour, and the reason a heavy feed
  shows up as a hot regenerator and low conversion rather than more coke.
* **Qua Iboe is a light-sweet crude with a poor FCC feed.** Its VGO carries
  ~2x Bakken's basic nitrogen (671 vs 321 ppm) and 1.3 wt% carbon residue, so
  the FCC runs at 66% conversion / 766 &deg;C against 79% / 682 &deg;C for Bakken
  and 80% / 677 &deg;C for Azeri BTC. The direction (Nigerian VGO is nitrogen-rich
  and naphthenic) is a known crude characteristic; the *size* rests on the
  basic-nitrogen deactivation heuristic (`1/(1 + 4e-4 ppm)`), which is
  illustrative.
* **Sulfur follows the crude into the FCC gasoline.** Gasoline sulfur from the
  same unit spans ~340 ppm (Bakken VGO) to ~7,450 ppm (Cold Lake VGO): the
  hydrotreating and post-treatment burden is a crude-selection question.
* **Nelson tables disagree.** Hydrotreating is 3.0 in one source and 2.0 in
  another; coking 2.75 / 5.0 / 5.5. Both vintages are provided and the index is
  approximate to ~10%.
* **Assay definitional quirks** (Cold Lake's "C5-65" lumping C4-, extrapolated
  TBP to 700 &deg;C, zero-reported metals in narrow cuts) are documented in
  `DATA_SOURCES.md`.

## 5. Not validated

The FCC rate constants against any plant; the feed-quality heuristics
(crackability, coke selectivity, nitrogen poisoning) beyond their direction;
the crude-unit furnace duty (140-170 MW at 200 kbpd - plausible, no public
reference found); the hydrotreater reference operating points and pretreat
severities; the coker naphtha/gas-oil split; regenerator residence time and bed
density. All are exposed as parameters. No licensor or vendor data was used.


## 6. Margins and complexity in the Indian data (PPAC + CHT)

`refinery_design/india.py` joins CHT's NCI (capacity-weighted by company) with
PPAC's company GRM (Ready Reckoner Table 4.7). Across IOCL, BPCL, HPCL, CPCL and
MRPL:

| Year | slope ($/bbl per NCI point) | r | n |
|---|---|---|---|
| mean of FY2017-18 to FY2025-26 | +0.55 | 0.40 | 5 |
| FY2021-22 | +0.44 | 0.28 | 5 |
| FY2022-23 | +2.09 | 0.41 | 5 |
| FY2023-24 | +0.91 | 0.37 | 5 |
| FY2024-25 | +0.15 | 0.13 | 5 |

(Companies: IOCL, BPCL, HPCL, CPCL, MRPL; **NRL is excluded** - see the caveat below. IOCL and MRPL stopped
publishing GRM for FY2025-26, so that year is not fitted.)

Higher complexity goes with higher GRM in every cut, but weakly (r 0.13-0.41; it fades to nearly nothing
in FY2024-25). Five companies
cannot support more, GRM is company-level (PPAC does not publish refinery-wise
GRM), the North-East refineries' figures include an excise-duty benefit, and
crude slate and year dominate. An academic panel study (Driscoll-Kraay
estimator; found by search, abstract only) reports a significant positive
complexity effect on Indian GRM - not reproduced or checked here.

`tests/test_grm.py` shows the mechanism and its condition: on a heavy slate a
coker adds margin only when the residue discount and distillate cracks are wide
(default deck), and *destroys* margin when they are thin. That is consistent
with complexity being a capability, not a guarantee.

**GRM calibration.** Product prices are inputs, not data. `calibrate_deck`
scales the light-product cracks so the Paradip-basket flowsheet reproduces a
PPAC-reported GRM. For IOCL, FY2021-22 ($11.25/bbl at an Indian basket of
$79.18) needs gasoline/diesel cracks of ~$17/$29 per bbl; FY2022-23 ($19.52 at
$93.15) needs ~$26/$43. These are the cracks *this simplified flowsheet* needs;
they absorb everything not modelled (bitumen/lubes/petchem premiums, inventory
effects, product-mix quality) and must not be read as market cracks. The
calibration is exact by construction - it is not a validation of the deck.

## 7. Accounting mistakes found and fixed while building the GRM layer

* Unconverted VGO (no FCC) was being routed into the **middle-distillate pool**,
  valuing it as diesel and making a hydroskimmer look better than a
  full-conversion refinery. It now has its own black-oil pool.
* Charging a *fixed total* fuel-and-loss (PPAC's 8.9-10%) made low-complexity
  configurations pay for fuel they never burn. PPAC's Paradip 10.0% minus the
  flowsheet's own 5.6% leaves a 4.4% configuration-independent overhead
  (`UNMODELLED_FUEL_LOSS_PCT`).
* LPG priced with a $/bbl crack came out richer per tonne than diesel (11.4 vs
  7.4 bbl/t); LPG and residue are now priced as fractions of crude value.


## 8. Rundown cross-checks (Digital Refining)

`rundown.py` and `tests/test_rundown.py` compare the model with published rundown figures:

| Quantity | Model | Digital Refining |
|---|---|---|
| Conventional FCC propylene | 4.0 wt% of feed (Paradip basket) | 3-5% |
| Propylene-mode yield | 16.2 wt% (Paradip-implied) | high-severity 15-28% |
| FCC gasoline sulfur | ~970-1,940 ppm for a 0.6-1.2 wt% S feed (2,100 ppm at 1.3) | typical 1,000-2,000 ppm |
| LCO gain, gasoline end point 430 -> 380 degF | +5 vol% (the slope is set from this) | +4-6 vol% |
| FCC gasoline share of gasoline pool, light-sweet (Bakken) | 26.8 vol% | ~20 vol% (US-style) |
| LCO share of diesel pool, light-sweet (Bakken) | 5.6 vol% | ~5% (US-style) |

The propylene and sulfur rows were not fitted to these figures: the propylene routes come from Paradip's
published capacities and the 6 wt% literature value, and the sulfur split (8% of feed sulfur to
gasoline) came from FCC literature. The LCO slope is *taken from* the article, so it is an input, not a
check. Heavier baskets sit far above the US-style pool shares (Paradip basket 49% and 13%) because a heavy
crude makes little straight-run naphtha and diesel - expected, not a discrepancy. The one modelled
distillate-mode result (riser 11 &deg;C cooler plus the end-point cut) gives +6.3 wt% LCO and -3.6 wt%
gasoline; no published figure was found for that combination.


**NRL is not comparable.** Numaligarh reports $20-43/bbl (FY2025-26: $29.20), two to four times the other PSUs.
PPAC footnotes that the North-East refineries' GRM include an excise-duty benefit (verified); NRL also runs
mostly domestic Upper-Assam crude from Oil India and ONGC (3,033 kt of domestic crude of 3,066 kt processed in
FY2024-25, per a news report of NRL's results) rather than imported benchmark crude. That pricing arrangement is
*not verified* here, so no size is attributed to it; NRL is simply excluded from margin comparisons
(`india.NON_COMPARABLE`, `india.NRL_CAVEAT`). Its 3 -> 9 MMTPA expansion on imported crude (reported as
commissioned December 2025) will change the comparison after FY2025-26.

## 9. Observed prices reproduce reported GRM (PPAC trade data, no calibration)

`trade.TradeDeck` prices the flowsheet's product pools with PPAC's *observed* trade unit values (Table 4.11:
value / quantity): LPG at the import value, petrol and diesel at export values, fuel oil and petcoke at import
values. Run on the Paradip-basket flowsheet with **no calibration**:

| FY | Indian-basket-like crude | Model GRM | PPAC-reported GRM |
|---|---|---|---|
| 2021-22 | $78.6/bbl | 6.46 | IOCL 11.25, BPCL 9.09, HPCL 7.19 |
| 2022-23 | $93.6 | **19.37** | IOCL **19.52**, BPCL 20.24, HPCL 12.09 |
| 2023-24 | $78.8 | 10.34 | IOCL 12.05, BPCL 14.14, HPCL 9.08 |
| 2024-25 | $78.0 | **0.62** | IOCL 4.80, BPCL 6.82, HPCL 5.74 |
| 2025-26 | $69.4 | 8.48 | BPCL 11.74, HPCL 8.79 |

It lands inside the reported PSU range in three of five years (FY2022-23 within $0.15 of IOCL) and **misses in
FY2024-25** ($4-6 low) and to a lesser degree FY2021-22. The flowsheet omits products with premiums (bitumen,
lubes, petchem), uses one export/import unit value per product for a mix of grades, and PPAC's unit values are
rounded and timing-lagged; treat it as a plausibility check, not a fit.

The same data give an independent check on the GRM-calibrated cracks (section 6): trade-implied gasoline/diesel
cracks are +$17.0/+$13.6 (FY2021-22) and +$23.0/+$43.4 (FY2022-23) against calibrated +$17.4/+$29.0 and
+$26.0/+$43.4. They agree on gasoline in both years and on diesel in FY2022-23, and **disagree on diesel in
FY2021-22** (+$13.6 vs +$29.0) - diesel export realisations lagged the crude spike that year. LPG has traded at
0.62-0.80 of crude value per barrel and fuel oil at 0.81-0.97 (defaults in `grm.py`: 0.70 and 0.75 - the fuel-oil
default is on the low side of what India actually realises).


## 10. FCC gas-plant proxy vs the PCS paper's figures

`fcc_modes.py` takes its wet-gas slopes from the paper's own figures, so the tests check *reading* them, not fitting: Figure 8 gives +5.07%
per wt% propylene (34,500 -> 44,300 ICFM over 5.6 wt%); Figure 10 gives 0.83%/F (130 -> 115 F); Figure 9 gives a pressure ratio of 0.813
at 6.5 psig, and the code recovers 6.5 psig from a 44,300/36,000 ratio. Not validated: the dry-gas term in the wet-gas estimate, the
mode yield shifts other than propylene, and any absolute compressor capacity (unit-specific). The propylene mode (x1.73) is outside the
paper's 7.5-13.1 wt% range and is flagged so.

## 11. Cracker capex vs BPCL Bina

The default capex ($1,500/tpa of feed at 4 Mt, six-tenths rule) gives $5.7-6.4 bn for the 3.6-4.4 Mt of naphtha/LPG feed that 1.2 Mt/y of
ethylene needs, against Bina's disclosed ~$6 bn - but Bina's figure *also* includes 1.15 Mt/y PE, 0.55 Mt/y PP, aromatics and a
refinery expansion, so the model is likely to overstate a cracker-only cost. The cracker verdict (does not pay) survives capex of
$1,000/tpa (`docs/PETROCHEMICAL_EVALUATION.md`).

## 12. Corrections made while adding these modules

* PPAC's newer edition (FY2025-26) superseded the FY2022-23 data; GRM-vs-NCI moved from r 0.28-0.41 to 0.13-0.41 with FY2024-25 near zero.
* The trade-table parser first shifted lines because Python's `splitlines()` treats the PDF's form-feed characters as line breaks; totals now
  agree with PPAC's printed ones.
* Break-evens for the PP routes fell from $1,182-1,320 to $1,058-1,126 when the calibrated (wider) cracks were replaced by observed ones.
* OISD-STD-154 is training, not fired heaters (see `SAFETY.md`).


## 13. Dual-feed cracker: propane slate vs a real table

The propane slate is the patent's own table, so its per-pass numbers are reproduced exactly at the 84/86/88/90/92% columns (tests). The derived
overall yield (recycle to extinction, ~43% ethylene from propane) is *not* fitted: it lands on the commonly quoted ~42% for propane, an independent
plausibility check. Not validated: the butane slate (assumed), the ethane-recycle remainder split, the by-product values, and any dual-feed *interaction*
(shared separation train, furnace changeover) - the model simply adds two single-feed slates and scales capex on total feed. With no LPG it reduces to
the naphtha cracker exactly (tested).


## 14. Indian refiners: derived utilisation against company-reported figures

Utilisation is computed (throughput / capacity on 1 April) and is checked against every company-reported utilisation in the data - 21 refinery-years across BPCL, HPCL and HMEL.
Twenty agree within 1.5 points (mean absolute difference 0.9 over all 21; BPCL Mumbai FY2024-25 129.83% derived vs 129.82% reported). The exception is HPCL Visakh FY2023-24
(115.4% vs 105.0%): capacity went 8.3 -> 11.0 -> 13.7 MMTPA around then; that a company figure measured against capacity commissioned during the year explains it is inferred, not verified.
Company-total ties: the refinery sums match IOCL's reported throughput to 0.5 MMT, BPCL's FY2025-26 41.15 MMT to 0.5, and Reliance's DTA + SEZ to its total crude processed exactly.
Not validated: capacity carried forward for Reliance, Nayara, CPCL, MRPL, NRL and ONGC in FY2021-22..FY2025-26 (the 2020 and 2026 endpoints match, the years between were not fetched), any FCC nameplate from a
trade-press summary, and every FCC yield or mode statement (none is published).
