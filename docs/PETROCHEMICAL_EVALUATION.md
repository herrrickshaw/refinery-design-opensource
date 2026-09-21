# Petrochemical addition: does propylene -> polypropylene pay?

An evaluation on the Paradip-like flowsheet (15 mtpa, medium-sour + heavy-sour
basket, VGO hydrotreated), reproduced by `examples/petrochemical_evaluation.py`.
Read `DATA_SOURCES.md` first. The PP side now rests on a primary source (IOCL's own ex-works
price lists, 2026); **no 2026 propylene price is accessible**, so propylene enters only as a
break-even. The answer is a break-even and a headroom against an observed price, not a profit forecast.

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

## Against an observed price deck (Sept 2026)

`petchem_prices.py` holds IOCL's ex-works PP list (Rs/MT, basic and cash, GST additional; Thane) at
three 2026 dates - read from the price-list PDFs IOCL's authorised distributor publishes:

| Grade | 1 Jan | 1 Mar | 11 Sep | Jan -> Sep |
|---|---|---|---|---|
| Homopolymer injection (1110MG) | 90,452 | 99,952 | 154,452 | +70.8% |
| Raffia (1030RG) | 91,502 | 101,502 | 154,002 | +68.3% |
| BOPP (1030FG) | 95,202 | 104,702 | 164,202 | +72.5% |
| Random copolymer (2120MC) | 99,182 | 108,532 | 174,532 | +76.0% |

At Rs 95.82/$ (17 Sep 2026, from a search summary) homopolymer injection is **$1,612/t** list. The
fuel side is re-based to the same date: live Brent $102.47 and Dubai $116.35 through PPAC's
Indian-basket formula (Dubai standing in for Oman) = $112.97/bbl, with the PPAC-calibrated cracks
kept as two regimes. At that crude level LPG is ~$904/t and gasoline/diesel $1,050-1,190/t, so the
break-evens move up (~$1,180-1,320/t) - the higher crude raises what each route displaces.

| Route | Break-even PP ($/t) | Headroom at list / 90% / 80% of list, weak cracks | strong cracks |
|---|---|---|---|
| Conventional | 1,182 | +430 / +269 / +108 | +430 / +269 / +108 |
| ZSM-5 | 1,233-1,254 | +379 / +218 / +57 | +358 / +197 / +36 |
| Propylene-mode | 1,265-1,320 | +347 / +185 / +24 | +292 / +131 / **-30** |

Net after capital charge at list: conventional +$68 M/y, ZSM-5 +$85-90 M/y, propylene-mode
+$187-222 M/y (FCC-side capex excluded). **At the observed price every route pays, with $290-430/t of
headroom - but the headroom is the price premium the market is paying now.** It is thin if the
refinery nets 80% of list, and the propylene-mode route is the first to fail (in strong-cracks
conditions). Selling propylene outright breaks even at $904-1,106/t; the only 2026 propylene figure
found (Northeast Asia, $1,010/t in March, low confidence) is six months old while PP has since risen
~55%, so it is a marker rather than a comparison.

Read this with three cautions: the PP list price is a *domestic* selling price and carries whatever
import-parity premium the Indian market has; PP rose 71% in 2026 alongside crude, so it is a level
that may not persist; and the cracks are PPAC-year fits re-based to today's crude, not observed 2026
cracks.

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

A dated propylene price (still missing - Polymerupdate's daily Propylene CFR India is behind a login), observed 2026 refinery cracks, a real capex quote for the
FCC-side revamp, the actual propylene yield the FCC reaches on this feed (the
16.2 wt% is Paradip-implied, not modelled), catalyst activity dilution from ZSM-5
(each 5 wt% additive costs 1-2 wt% activity, not modelled), and product-quality
premia (polymer-grade vs refinery-grade propylene). Steam-cracker, aromatics
(paraxylene) and PDH routes are not evaluated.


## Steam cracker route: naphtha -> ethylene (added)

`steam_cracker.py` sizes a naphtha cracker with PE (from ethylene) and PP (from propylene). **Cited:** ethylene ~22 wt% at 820 C and
~27 wt% at 850 C coil outlet; whole naphtha 23-30 wt% ethylene, 13-16 propylene, 6-7 butadiene, < 5 pyrolysis fuel oil; 1-1.6 t CO2
per t ethylene; 0.92-1.01 t ethylene per t PE. **Assumed** (no accessible source): other C4 4, pygas 17, pyrolysis fuel oil 4 wt%, the
rest fuel gas; opex $100/t at each unit. **Capex anchors:** $1,600 per tpa of naphtha for a world-scale cracker (Thunder Said Energy,
search summary) and BPCL Bina - Rs 49,000 crore (~$6 bn) for a 1.2 Mt/y dual-feed cracker + 1.15 Mt/y PE + 0.55 Mt/y PP +
aromatics + a 7.8 -> 11 MMTPA refinery expansion - an upper bound on cracker plus derivatives; the model uses $1,500/tpa of feed at
4 Mt scale (six-tenths rule) and reproduces Bina's order of magnitude ($5.7-6.4 bn for 3.6-4.4 Mt of feed).
Co-products are valued conservatively (pygas at gasoline, C4s at LPG, fuel oil at fuel oil, fuel gas as furnace fuel); PE at IOCL's
HDPE raffia list price ($1,480/t, +42% since January; LLDPE film $1,437/t, +45%), PP at $1,612/t, naphtha at $855/t (PPAC FY25-26 cracks
at Brent $102.47).

**Result: it does not pay on these assumptions.** 3 Mt/y of naphtha (0.81 Mt/y ethylene) earns **-$240 M/y before capital** and
-$916 M/y after; the break-even PE price is ~$2,570/t against $1,480 list, or naphtha would have to fall to ~$550/t. Stress tests
(cash margin before capital / net): world-scale 4 Mt naphtha -$320 M / -$1,123 M; severity 880 C -$150 M / -$953 M; plus $300/t on C4s
(butadiene) and $200/t on pygas (benzene) -$64 M / -$867 M; all three plus capex $1,000/tpa **+$106 M / -$430 M**; January 2026 prices
(Brent ~$63, naphtha $511/t, PE $1,042/t) -$210 M / -$1,013 M. **No case tested pays after capital.** Reliability: the ethylene yield
is once-through and the by-product slate is partly assumed, so the sign is more trustworthy than the size; a dual-feed cracker with
cheaper LPG/ethane feed, integrated by-product upgrading and fiscal support is what Indian projects actually build, which this
single-feed naphtha model cannot represent. **Keep the FCC-propylene -> PP routes ahead of it.**

## PPAC trade data and the latest news: which routes fit India's position

* **Naphtha is long, LPG is short.** FY2025-26: naphtha production 18.4 Mt, consumption 11.7 Mt, **exports 6.0 Mt** ($3.4 bn), imports
  1.1 Mt; domestic naphtha consumption fell 11.9% in Apr-Jan FY26 with 94% going to petrochemicals (PPAC). LPG: consumption 33.2 Mt,
  production 13.1 Mt, **imports 21.3 Mt (64%, $11.3 bn)**. A naphtha cracker uses a feed India already exports; an LPG-fed cracker
  would deepen an import dependence - which is why the new Indian crackers are dual-feed.
* **PP is about to be over-built.** Reported: PP capacity to rise 1.8x between FY25-FY30 against demand growth of 1.4x, potentially
  ending import dependence by FY30; India imported ~1.6 Mt PP and ~3.1 Mt PE in 2024 (search summaries; PE/PP imports ~a fifth of
  consumption, PVC ~three-quarters). New capacity: IOC 200 kt PP at Barauni and 500 kt at Gujarat (by March 2026), BPCL Kochi PP
  (Rs 5,514 crore, foundation stone 12 Mar 2026), BPCL Bina (1.2 Mt/y cracker, 1.15 Mt/y PE, 0.55 Mt/y PP, Rs 49,000 crore, 2028),
  IOCL Paradip complex (1.5 MTPA dual-feed cracker, Rs 61,077 crore), HMEL HDPE 450 kt, GAIL Pata 60 kt PP. **The $1,612/t PP list
  price is a 2026 peak** (+71% since January, during a Hormuz-driven supply shock and a temporary nil-duty window: nil basic customs duty
  on PE/PP/PVC/MEG/PTA and ~40 products from 2 April to 30 June 2026, extended to 15 July; the status after that was not found; the
  Quality Control Order on polymers was rescinded in November 2025). PP margins should be expected to compress as capacity arrives, so
  **the PP-route headroom is a price-timing bet, not a structural margin.**
* **PE has the larger import gap** (3.1 Mt vs 1.6 Mt PP), but the route to it - a cracker - is the one that does not pay here.
* **What the trade data support:** (1) monetise the propylene the FCC already makes (PP, or sell propylene); (2) keep exporting surplus naphtha
  and petrol unless a cracker can be built dual-feed at scale; (3) treat LPG mode as import substitution (each FCC LPG tonne replaces
  an imported one at $531/t FY25-26) rather than as a fuel-price play.

## Break-evens on observed prices (update)

With PPAC-observed FY2025-26 trade cracks re-based to Sept-2026 crude, the PP break-evens are **$1,058 / 1,097 / 1,126 per t**
(conventional / ZSM-5 / propylene mode; capital charge on the PP plant only) against the $1,612/t list - a headroom of $486-554/t -
and the propylene-mode FCC could cost up to ~$2.3 bn at list price (~$3.6 bn at FY25-26 prices as observed). The earlier figures in
this document ($1,182-1,320 break-even, $290-430 headroom) used GRM-calibrated cracks (gasoline +$17-26, diesel +$29-43) that were wider
than what FY25-26 trade actually shows (gasoline +$12, diesel +$25), so they priced the displaced fuel higher. **Prefer the
observed-price numbers**; the difference is the deck, not the method. See `PETROL_DISPLACEMENT.md` for the mode-by-mode screen.
