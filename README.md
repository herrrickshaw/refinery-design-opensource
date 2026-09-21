# refinery-design-opensource

Open-source, literature-grounded conceptual sizing tools for an oil
refinery, with the emphasis on **what the crude does to the plant**: crude
oil types and assays &rarr; crude/vacuum distillation &rarr; **FCC
reactor-regenerator** &rarr; hydrotreating &rarr; delayed coking &rarr;
whole-refinery balance and Nelson complexity. Sibling project to
[lng-design-opensource](https://github.com/herrrickshaw/lng-design-opensource),
[coal-to-urea-design-opensource](https://github.com/herrrickshaw/coal-to-urea-design-opensource),
[ethanol-design-opensource](https://github.com/herrrickshaw/ethanol-design-opensource),
[cbg-design-opensource](https://github.com/herrrickshaw/cbg-design-opensource),
[lignocellulosic-ethanol-opensource](https://github.com/herrrickshaw/lignocellulosic-ethanol-opensource) and
[biomass-to-syngas-opensource](https://github.com/herrrickshaw/biomass-to-syngas-opensource):
same discipline - public-domain/textbook correlations only, CoolProp for
real thermodynamic properties, every method cited, every module tested,
every worked example actually run, and honest reporting of what is
validated versus merely calibrated.

**Scope**: fully generic and literature-only. Crude data are real
published assays (ExxonMobil's public downloads, values extracted, files
not redistributed). Nothing here derives from any proprietary licensor,
vendor or client engineering data. See `docs/METHODOLOGY.md` for
citations, `docs/VALIDATION.md` for cross-checks (including a real
refinery, IndianOil Paradip) and `docs/DATA_SOURCES.md` for exactly what
was and was not verified.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                          # 244 tests
python examples/full_refinery_worked_example.py    # 8 crudes through one refinery
python examples/fcc_worked_example.py              # FCC heat balance, riser, regenerator
python examples/paradip_check.py                   # validation against a real refinery
python examples/petrochemical_evaluation.py        # PPAC/CHT data + propylene/PP break-evens
python examples/petchem_price_deck.py              # IOCL PP price deck (2026) and per-route verdicts
python examples/fcc_rundown.py                     # FCC rundown streams, cut points, pool shares
python examples/petrol_displacement.py             # ethanol-displaced petrol: PPAC data, FCC secondary mode, routes
python examples/crude_sourcing_study.py            # crude basket, 2026 shock, local-currency settlement, Russian crude
python examples/safety_review.py                   # OISD standards map + model safety flags
python examples/dual_feed_cracker.py               # naphtha + LPG dual-feed cracker: sweep, refinery supply, LPG-import catch
streamlit run streamlit_app.py                     # interactive app
```

## Crude oil types

Eight real assays from light-sweet to heavy-sour and high-TAN, each with
whole-crude properties, per-cut density / sulfur / nitrogen / TAN / carbon
residue / metals, and a TBP curve.

| Crude | API | S wt% | TAN | Class (gravity / sulfur / acidity) | Vac. resid wt% |
|---|---|---|---|---|---|
| Bakken | 44.0 | 0.08 | 0.07 | light / sweet / low-TAN | 5.7 |
| Azeri BTC | 39.0 | 0.16 | 0.43 | light / sweet / low-TAN | 9.5 |
| Qua Iboe | 37.3 | 0.12 | 0.27 | light / sweet / low-TAN | 5.7 |
| Upper Zakum | 33.4 | 2.09 | 0.07 | light / sour / low-TAN | 19.9 |
| Alaska North Slope | 32.3 | 1.04 | 0.41 | light / sour / low-TAN | 18.2 |
| Dalia | 22.6 | 0.52 | 1.50 | medium / sour / high-TAN | 25.2 |
| Kearl | 19.8 | 3.83 | 2.08 | heavy / sour / high-TAN | 35.8 |
| Cold Lake Blend | 19.5 | 3.87 | 1.12 | heavy / sour / high-TAN | 36.2 |

Any pair of cut points can be requested (yields from the TBP curve, so mass
and volume close exactly), and crudes blend by volume into a `Slate`.

## Modules

| Module | Method | Key outputs |
|---|---|---|
| `refinery_design/assay.py` | TBP-curve cuts + assay-cut property weighting; volumetric slate blending (Refutas for viscosity) | Cut yields/quality for any cut points, crude classification, blends |
| `refinery_design/distillation.py` | TBP material balance; furnace duty from Watson-Nelson cp + Fishtine latent heat over the TBP curve (Gary & Handwerk) | CDU/VDU product streams (wt, bpd, density, S), furnace duty |
| `refinery_design/fcc.py` | 4-lump riser kinetics (Weekman-Nace / Lee et al. family) coupled to the regenerator heat balance (Sadeghbeigi); vapour-expansion riser sizing; superficial-velocity regenerator sizing | Conversion, cat/oil, regenerator T, coke, yields, heat-balance table, riser/regenerator dimensions, flue gas & SO2, gasoline sulfur, screening warnings, catalyst-cooler duty for resid feed |
| `refinery_design/fcc.py` (`pretreated`) | VGO hydrotreater feed pretreat (illustrative removal severities) | FCC feed after pretreat; used by `RefineryConfig(vgo_hydrotreat=True)` |
| `refinery_design/hydrotreater.py` | n-th order HDS space-velocity scaling from a reference point; H2 stoichiometry | LHSV, reactor volume, catalyst, H2S, H2 make-up |
| `refinery_design/coker.py` | Gary & Handwerk carbon-residue correlations | Coke/gas/liquid yields, coke-drum volume |
| `refinery_design/complexity.py` | Nelson complexity index (two published factor vintages) | NCI |
| `refinery_design/flowsheet.py` | Chains everything on one basis | Whole-refinery pools, light/middle-distillate/black-oil yields, mass closure |
| `refinery_design/india.py` | CHT complexity (NCI) + PPAC GRM, distillate yield, fuel & loss, Indian basket formula | Indian refinery reference data, GRM-vs-NCI fit |
| `refinery_design/grm.py` | PPAC/EIA GRM definition; price deck of cracks; calibration to a reported GRM | GRM ($/bbl), calibrated decks |
| `refinery_design/petrochemical.py` | FCC propylene -> polypropylene: three routes, six-tenths capex scaling, capital charge | Break-even PP price, GRM uplift, affordable FCC capex |
| `refinery_design/petchem_prices.py` | Dated PP (IOCL ex-works, 2026) and propylene price observations with sources and confidence; `PetchemPriceDeck` | PP price deck; propylene left unobserved |
| `refinery_design/rundown.py` | FCC rundown streams, gasoline/LCO cut-point shift, distillate mode, pool shares (Digital Refining figures) | Rundown table, LCO gain, pool shares |
| `refinery_design/trade.py` | PPAC trade / consumption / production; observed unit values; `TradeDeck`; petrol balance (implied ethanol) | Observed-price deck, import dependence |
| `refinery_design/ethanol.py` | Ethanol mass share, refinery petrol needed, E-step displacement, tender arithmetic | Petrol displaced by blending |
| `refinery_design/fcc_modes.py` | FCC gasoline-lean modes + wet-gas load from the PCS paper's figures | Mode yields, gasoline removed, gas-plant fix |
| `refinery_design/steam_cracker.py` | Naphtha steam cracker -> PE + PP; cited yield points, Bina-checked capex | Ethylene/propylene volumes, break-evens |
| `refinery_design/dual_feed_cracker.py` | Naphtha + LPG cracker: propane yields from a real patent table (recycled to extinction), butane assumed, LPG-share sweep, refinery LPG supply | Ethylene/propylene, break-even LPG and PE prices |
| `refinery_design/routes.py` | Petrol-switch options screen on one price deck | Gasoline removed, margin, net of capital |
| `refinery_design/crude_sourcing.py` | Realised import price vs Indian basket, 2026 shock, local-currency arithmetic, assay-based crude value | Sourcing study |
| `refinery_design/safety.py` | OISD standards map (105-entry official list) + screening flags | Which standards apply; model flags |
| `refinery_design/benchmarks.py` | Paradip published data | Validation |

## What crude type does to an FCC (real assays, same unit)

The FCC is fed the crude's own VGO (370-550 &deg;C cut). Same unit, same
conditions, three crudes (`examples/full_refinery_worked_example.py`):

| VGO from | Watson K | S wt% | Conversion | Regenerator | FCC gasoline S |
|---|---|---|---|---|---|
| Bakken (light, paraffinic) | 11.9 | 0.21 | 79% | 682 &deg;C | ~340 ppm |
| Upper Zakum (medium sour) | 11.7 | 2.78 | 69% | 756 &deg;C | ~4,600 ppm |
| Cold Lake (heavy, naphthenic) | 11.3 | 3.50 | 51% | 867 &deg;C (flagged) | ~7,450 ppm |

Feeds with too much carbon residue to heat-balance (e.g. an atmospheric
residue at CCR 20 wt%) are refused with an actionable message, and
`cooler_duty_for_regen_temperature()` sizes the catalyst cooler that would
be needed.

## Validation, honestly

* **Real assays** - TBP-derived cut densities agree with each assay's own
  reported cut densities to a max of 0.9% over 72 cuts; sulfur balances
  close exactly.
* **Real refinery (IndianOil Paradip, 15 mtpa)** - Nelson index from the published
  unit list brackets CHT's 10.6 (10.5-11.9 counting every listed unit; an earlier
  benchmark used IndianOil's commissioning-time 12.2, now corrected). PPAC's
  reported distillate yield (79.2-80.8%) vs the model's 79.3-79.8%. A single fitted
  blend parameter that matches Paradip's coker/CDU ratio (27.3%) *independently
  predicts* its FCC/CDU ratio (28.1% vs published 28.0%). That heavy-sour basket's
  VGO cannot run raw in an FCC (regenerator 816 &deg;C) - and Paradip's unit list
  includes the VGO hydrotreater that fixes it.
* **FCC kinetics are calibrated, not fitted to plant data** - constants
  reproduce typical published yield ranges at a reference feed; the
  structure (over-cracking maximum, ROT trade-off, heat-balance-driven coke)
  is the literature-grounded part. Feed-quality effects are directional
  heuristics with illustrative magnitudes. See `docs/VALIDATION.md`.

## Complexity, margins and petrochemicals (PPAC + CHT)

The repo links the two Government of India sources for refinery complexity and
margins: the Centre for High Technology's
[refinery complexity index](https://cht.gov.in/refinery-complexity-index) (NCI per
refinery, OGJ 2025 survey) and [PPAC](https://ppac.gov.in)'s Ready Reckoner
(GRM by company, distillate yield, fuel & loss, Indian basket).

* GRM tracks complexity across the five PSU companies - but weakly (r = 0.28-0.41,
  n = 5), and a coker only earns margin when the residue discount and distillate
  cracks are wide.
* **Petrochemical addition** (`docs/PETROCHEMICAL_EVALUATION.md`): propylene -> PP
  via conventional recovery, ZSM-5 or a propylene-mode FCC, anchored on Paradip's
  680 kt/y PP plant (Rs 3,150 crore). No propylene/PP price is available to this
  repo, so it reports the **break-even PP price** ($906-1,164/t across routes and
  two PPAC-calibrated margin regimes) and the FCC capex the option can afford. The
  Nelson index does not change - it has no polymer factor.
* **PP price deck:** IOCL's own ex-works lists put homopolymer injection PP at Rs 154,452/MT
  on 11 Sep 2026 (~$1,612/t; +71% since January). Against it every route clears its break-even
  (~$1,180-1,320/t at today's crude) with $290-430/t of headroom - thin at 80% realisation.
  **No 2026 propylene price is accessible**; it is left unobserved, not guessed.
* **Rundowns** (Digital Refining): FCC rundown streams, LCO gain from lowering the gasoline end
  point (~5 vol% per 50 degF), distillate mode and pool shares - cross-checked against the
  published propylene (3-5% / 15-28%) and gasoline-sulfur (1,000-2,000 ppm) ranges.

## Petrol displaced by ethanol, the FCC secondary mode, and the routes (PPAC, latest edition)

PPAC's FY2025-26 Ready Reckoner shows refineries producing more petrol (42.8 -> 49.8 Mt, FY22-23 to FY25-26) as the blend rose to E20,
with the surplus exported (13.1 -> 16.7 Mt); the gap between blended consumption and production + imports - exports is the ethanol
(implied 12% -> 22% of MS mass). For the Paradip-basket refinery, E12 -> E20 displaces ~367 kt/y of a 3,861 kt/y gasoline pool. A
gasoline-lean FCC mode (ZSM-5, higher severity, propylene mode) removes 134-496 kt/y, but the Process Consulting Services paper's wet-gas
figures show the gas plant is the constraint (+5.1% wet-gas flow per wt% propylene; the propylene mode is beyond the paper's range).
**Selling the extra LPG/LCO as fuel loses money; only the PP routes pay** (`docs/PETROL_DISPLACEMENT.md`).

* **Observed prices reproduce reported GRM without calibration** in three of five years (FY22-23: $19.37 vs IOCL $19.52); it misses
  FY2024-25 - reported, not hidden. **NRL's GRM is not comparable** (excise benefit + domestic Assam crude) and is excluded from fits.
* **Steam cracker (naphtha -> ethylene) does not pay** on these assumptions at September 2026 or January 2026 prices, at 3-4 Mt/y of
  naphtha, in every stress case after capital (`docs/PETROCHEMICAL_EVALUATION.md`).
* **Dual-feed cracker (naphtha + LPG)**: propane cracks to ~43% ethylene (real BP patent table, recycled to extinction) vs 27% for naphtha, and the cash margin
  turns positive at ~75% LPG (+$31 M/y; 100%: +$148 M/y at 4 Mt/y) - but it still does not pay after capital, the refinery can supply only ~820 kt/y of LPG, and
  every tonne cracked is a tonne of cooking gas India would import (64% of LPG is already imported). Butane yields are assumed.
* **Crude sourcing** (`docs/CRUDE_SOURCING_AND_LOCAL_CURRENCY.md`): India paid below the Indian basket in 7 of 8 years (FY23-24: $8.4 bn);
  the 2026 Hormuz shock cost ~$21 bn in four months; one basis point on the crude bill is $12.3 M/yr. **No measured saving from
  local-currency settlement was found** - MoPNG reported suppliers passing conversion costs to IOC - and only the UAE can plausibly recycle
  rupees. Russian crude is now a security, not a discount, answer (Urals at a premium to Brent in the 21-Sep snapshot).
* **Safety** (`docs/SAFETY.md`): the official OISD list (105 standards) mapped to each design element, with model-driven flags (high-TAN crudes,
  hot regenerator, gas-plant load, LPG/propylene). The standards were not read; this is a pointer, not a safety case.

## Not covered (roadmap)

Catalytic reforming, hydrocracking, alkylation, sulfur recovery, hydrogen
plant, aromatics/PDH/ethane-LPG dual-feed cracker routes, a reformer, market propylene/PP price data, crude-column tray hydraulics, preheat-train pinch design, ZSM-5 /
propylene maximisation, equilibrium-catalyst metals (Ecat) model, crude
compatibility/asphaltene stability, price-driven crude selection.

## Disclaimer

This tool implements textbook/public-domain conceptual sizing methods for
early-stage screening only. It is not a substitute for a rigorous process
simulator, an FCC kinetic model fitted to plant data, or licensor/vendor
design. Crude assays are ExxonMobil's public downloads, provided by them
without warranty - check current assays before any commercial use. Always
validate against a licensed simulator and vendor data before committing to
equipment specifications.
