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
pytest -q                                          # 126 tests
python examples/full_refinery_worked_example.py    # 8 crudes through one refinery
python examples/fcc_worked_example.py              # FCC heat balance, riser, regenerator
python examples/paradip_check.py                   # validation against a real refinery
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
* **Real refinery (IndianOil Paradip, 15 mtpa)** - Nelson index from the
  published unit list lands 2-7% below the reported 12.2 (the list is
  partly ambiguous; a range is reported). A single fitted blend parameter
  that matches Paradip's coker/CDU ratio (27.3%) *independently predicts*
  its FCC/CDU ratio (28.1% vs published 28.0%). Run through the flowsheet,
  that heavy-sour basket's VGO cannot run raw in an FCC (regenerator 816 &deg;C)
  - and Paradip's unit list includes the VGO hydrotreater that fixes it.
* **FCC kinetics are calibrated, not fitted to plant data** - constants
  reproduce typical published yield ranges at a reference feed; the
  structure (over-cracking maximum, ROT trade-off, heat-balance-driven coke)
  is the literature-grounded part. Feed-quality effects are directional
  heuristics with illustrative magnitudes. See `docs/VALIDATION.md`.

## Not covered (roadmap)

Catalytic reforming, hydrocracking, alkylation, sulfur recovery, hydrogen
plant, crude-column tray hydraulics, preheat-train pinch design, ZSM-5 /
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
