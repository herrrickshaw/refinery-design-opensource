# Petrochemical addition: does propylene -> polypropylene pay?

An evaluation on the Paradip-like flowsheet (15 mtpa, medium-sour + heavy-sour
basket, VGO hydrotreated), reproduced by `examples/petrochemical_evaluation.py`.
Read `DATA_SOURCES.md` first: **no propylene or polypropylene price was available
to this repo**, so the answer is a break-even, not a profit forecast.

## The question, and the data that anchor it

* **Complexity and margins (CHT, PPAC).** CHT's table gives every Indian
  refinery's NCI (https://cht.gov.in/refinery-complexity-index); PPAC gives GRM by
  company and distillate yield by refinery (https://ppac.gov.in, Ready Reckoner
  FY2022-23). Across IOCL/BPCL/HPCL/CPCL/MRPL, GRM rises with NCI in every cut but
  weakly (r = 0.28-0.41, n = 5). **Complexity is not a reliable guide to margin,
  and the Nelson index cannot see a polypropylene plant at all** - the factor table
  has no polymer entry, so every option below changes the NCI by exactly 0.
* **Precedent.** Paradip added a 680 kt/y polypropylene plant (Rs 3,150 crore,
  $451 M at PPAC's FY2018-19 exchange rate) fed by its INDMAX light-olefin FCC.
  That plant is 16.2% of the FCC's 4.2 Mt/y feed, implying a propylene-mode
  yield of ~16 wt%.
* **Baseline margin.** Product prices are calibrated so the flowsheet earns
  IOCL's PPAC GRM: $11.25/bbl in FY2021-22 (Indian basket $79.18) or $19.52/bbl in
  FY2022-23 ($93.15). Two regimes: modest fuel cracks and strong ones.

## The three routes

| Route | Propylene | PP (kt/y) | PP capex | Displaces |
|---|---|---|---|---|
| Conventional recovery from FCC LPG | 4.0 wt% of feed (34% of LPG) | 158 | $188 M | LPG |
| ZSM-5 additive | 6.0 wt% | 237 | $239 M | LPG + gasoline-range |
| Propylene-mode FCC (INDMAX-type) | 16.2 wt% | 641 | $435 M + FCC revamp | LPG + gasoline/LCO |

PP capex is Paradip's $451 M scaled by the six-tenths rule. The propylene-mode FCC
capex is **not** included (unknown); see the affordable-capex row below. The
heavy, hydrotreated VGO makes little LPG, so the conventional and ZSM-5 volumes
are well below Paradip's (4.0 vs the 6 wt% typical of a lighter feed).

## Result: break-even PP price ($/t)

At PP opex $100/t, 12% hurdle, 20-year life, 0.98 PP yield (all unsourced
assumptions):

| Route | FY2021-22 deck (weak fuel cracks) | FY2022-23 deck (strong fuel cracks) |
|---|---|---|
| Conventional | 906 | 1,020 |
| ZSM-5 | 950 | 1,092 |
| Propylene-mode | 983 | 1,164 |

Net margin after capital charge ($M/y) at PP $1,100/t: FY2021-22 conventional +31,
ZSM-5 +36, propylene-mode +75; FY2022-23 +13, +2, **-41**. At $1,300/t: +62/+83/+203
and +44/+49/+87. GRM uplift at $1,100/t: +0.55 / +0.67 / +1.31 $/bbl of crude
(FY2021-22) and +0.37 / +0.33 / +0.17 (FY2022-23).

## What this says

1. **The break-even sits ~$190-260/t above the fuel value being displaced.** The
   route does not pay unless PP trades comfortably above gasoline/diesel
   equivalent - so the decision is a view on the PP-minus-fuel spread, not on the
   refinery.
2. **Petrochemicals are a hedge, not an addition.** The routes that displace
   gasoline/diesel (ZSM-5, propylene-mode) have their break-even rise by ~$140-180/t
   when fuel cracks are strong, and propylene-mode turns negative at $1,100/t.
   They earn most when refining margins are weak - qualitatively the
   smoothing effect the integration literature describes.
3. **Conventional recovery is the low-regret step but small.** Lowest break-even and
   least sensitive to fuel margins (it displaces LPG only), but 158 kt/y is a
   quarter of Paradip's PP plant, so scale economics are unfavourable
   (the six-tenths rule gives $1,190/t of capacity against Paradip's $663).
4. **Propylene-mode is the highest-upside, highest-risk option and its capex is the
   open number.** At PP $1,300/t the FCC-side revamp could cost up to ~$1.5 bn (weak
   fuel cracks) or ~$650 M (strong) before the option stops covering its capital
   charge; at $1,100/t, ~$560 M or $0. Hold a licensor quote against those.
5. **Sensitivity to the gasoline/LCO split of the displaced product is negligible**
   here because gasoline-range and middle-distillate are priced within ~4% of each
   other per tonne (within ~4%).

## Recommendation

Treat the petrochemical step as an FCC-and-spread decision, not a complexity
decision:

* Start with the ZSM-5 route or conventional recovery sized to the FCC's own
  propylene - small capex, break-even $906-1,092/t.
* Move to a dedicated propylene-mode FCC only against a firm licensor capex below
  the affordable-capex figure at a PP price you can defend through a fuel-margin
  upswing, since that is when it underperforms.
* Do not use the Nelson index (or the weak GRM-NCI relationship) to justify it:
  the index does not register the investment.

## What would change the answer

A propylene/PP price deck (the essential missing input), a real capex quote for the
FCC-side revamp, the actual propylene yield the FCC reaches on this feed (the
16.2 wt% is Paradip-implied, not modelled), catalyst activity dilution from ZSM-5
(each 5 wt% additive costs 1-2 wt% activity, not modelled), and product-quality
premia (polymer-grade vs refinery-grade propylene). Steam-cracker, aromatics
(paraxylene) and PDH routes are not evaluated.
