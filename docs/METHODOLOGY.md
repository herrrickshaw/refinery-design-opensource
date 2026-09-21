# Methodology

Each module's docstring carries its own citations in full; this page
summarises them in one place, and says plainly which parts are textbook
correlations, which are calibrated, and which are heuristics.

## Crude assays (`assay.py`, `scripts/build_assay_data.py`)

Real assays (ExxonMobil public downloads; see `DATA_SOURCES.md`). For a
requested cut `[lo, hi]`:

* **Yields** come from the assay's TBP curve (cumulative wt% and vol%
  distilled versus TBP temperature), so mass and volume close exactly and
  cut density is `rho_crude x dwt / dvol`.
* **Intensive properties** (sulfur, basic/total N, TAN, micro carbon residue,
  Ni, V, UOP K) are mass-weighted over the assay cuts the requested cut
  overlaps, weights taken from the TBP curve. Micro carbon residue (ASTM D4530)
  is used as Conradson carbon (ASTM D189); the two agree closely.
* **Blending** (`Slate`) is by volume: cut yields add, and the per-mass
  properties (sulfur, TAN, ppm metals, carbon residue) mass-average - exact,
  not approximate. Viscosity uses the Refutas blending index.
* **Classification**: gravity at the US DOE-EIA breakpoints (31.1 / 22.3 API);
  sweet at <= 0.5 wt% S; high-TAN from 0.5 mgKOH/g (the literature threshold
  spans 0.5-1.0); Watson K bands (>= 12 paraffinic, 11.5-12 intermediate,
  < 11.5 naphthenic/aromatic).

## Petroleum-fraction properties (`properties.py`)

* Watson K = (1.8 Tb)^(1/3)/SG (Watson & Nelson 1933).
* Molecular weight: Riazi & Daubert, Hydrocarbon Processing 66(3), 1987.
* Liquid cp: Watson-Nelson form, cp[Btu/lb-F] = (0.6811 - 0.308 SG +
  (0.000815 - 0.000306 SG) T_F)(0.055 K + 0.35).
* Latent heat at Tb: Fishtine / Kistiakowsky, Tb(8.75 + 1.987 ln Tb) cal/mol
  (Reid, Prausnitz & Poling).
* Vapour cp, steam, air and flue-gas components: CoolProp (n-dodecane ideal-gas
  cp stands in for hydrocarbon vapour; IAPWS-95 for steam).

## Crude and vacuum unit (`distillation.py`)

TBP material balance for LPG / naphtha / kerosene / diesel / VGO / vacuum
residue at chosen cut points. Furnace duty (screening): liquid sensible heat
from preheat-train exit to coil outlet plus latent heat of the vaporised
distillate (plus overflash), integrated over 10 &deg;C TBP slices at constant
Watson K (Gary & Handwerk). Not a column simulation.

## FCC (`fcc.py`)

**Riser kinetics.** A 4-lump scheme (feed/unconverted, gasoline, gas, coke):
second-order feed cracking, first-order gasoline over-cracking, Arrhenius
temperature dependence, exponential catalyst decay with time on stream; the
structure follows Weekman & Nace (AIChE J. 16, 1970) and Lee, Chen, Huang &
Pan (Can. J. Chem. Eng. 67, 1989). **The rate constants are calibrated**, by
least squares, to reproduce typical published yield ranges at a reference
feed (Watson K = 11.8, cat/oil 7, 2.5 s, 530 &deg;C: 75 wt% conversion,
49.5 gasoline, 20 gas, 5.5 catalytic coke). They are not fitted to plant data;
override `FccKinetics` to fit a real unit. The gas lump is split into LPG and
dry gas by a temperature-dependent share (falls with ROT as thermal cracking
grows) - again an illustrative calibration.

**Heat balance** (Sadeghbeigi, *Fluid Catalytic Cracking Handbook*; Gary &
Handwerk). Riser demand = feed liquid heating + vaporisation (+ superheat) +
endothermic reaction (5.6 kJ/kg per wt% conversion, ~420 kJ/kg at 75%) +
dispersion and stripping steam. Catalyst circulation follows:
`cat/oil = q_riser / (cp_cat (T_regen - ROT))`. The regenerator releases coke
heat (C to CO/CO2 by the CO2/CO ratio, H to steam; NIST-JANAF enthalpies of
formation) against air/flue-gas sensible heat (CoolProp), coke desorption
(2.3 MJ/kg, a typical-range assumption), losses (1.5%) and an optional catalyst
cooler. The unknown is the regenerator temperature; cat/oil and conversion
are iterated to a fixed point at each trial, and Brent's method closes the
loop. This reproduces the defining FCC behaviour that **coke make is set by the
heat balance**: across very different feeds the solver returns nearly the same
coke (~5.9 wt%) and lets cat/oil and regenerator temperature move.

**Feed effects (heuristics, illustrative magnitudes).** Watson K scales
crackability and coke selectivity (paraffinic cracks easier, aromatic cokes
more); basic nitrogen deactivates as `1/(1 + 4e-4 ppm)`; feed carbon residue
adds coke 1:1 (FCC literature notes coke exceeds Conradson carbon above ~50%
conversion, so 1:1 is a lower bound). Only the *directions* are literature
findings.

**Sizing.** Riser: vapour molar flow along the reaction coordinate
(unconverted + gasoline + gas + steam, ideal gas, isothermal at ROT) fixes exit
diameter at a design exit velocity (20 m/s) and height from the velocity
integral over the residence time. Regenerator: flue-gas volume at T_regen, P
over a superficial velocity (0.9 m/s) gives diameter; catalyst inventory from a
residence time (5 min) and bed density (550 kg/m3) gives dense-bed height.
Flue-gas composition from the stoichiometric burn plus excess air; SO2 from the
fraction of feed sulfur to coke (default 4%).

**Sulfur distribution** (defaults within the ranges reported in FCC
literature: ~35-45% of feed S to H2S, 2-5% to coke, 2-10% to gasoline):
40 / 4 / 8%, remainder to LCO and slurry.

**Screening flags** (not hard limits): regenerator > 760 or < 660 &deg;C,
cat/oil outside 4-10, delta coke outside 0.4-1.6 wt%, riser exit velocity
outside 15-30 m/s, feed Ni+V > 5 ppm, feed CCR > 1.5 wt%, dense bed < 4 or
> 12 m.

## Hydrotreater (`hydrotreater.py`)

HDS follows an n-th order rate law in sulfur (order 1.5 for diesel; 1.0-1.2
for naphtha/kerosene), so `1/LHSV = [S_out^(1-n) - S_in^(1-n)] / (k (n-1))`.
`k` is set per service from a **reference operating point** (feed S, product
S, LHSV) chosen inside typical published windows - assumptions, not vendor
data. Chemical H2 = 3 mol per mol S removed (2-4 covers mercaptan to
benzothiophenic sulfur) + 5 per mol N; 25% of make-up assumed lost to solution
and purge. Constant temperature; no activation-energy term.

## Delayed coker (`coker.py`)

Gary & Handwerk carbon-residue correlations: coke = 1.6 x CCR, gas (C4-) =
7.8 + 0.144 x CCR (wt%). The liquid remainder is split into naphtha and coker
gas oil by an explicit parameter (default 22% naphtha) because the book's
naphtha equation could not be independently confirmed. Coke-drum volume from
fill time (18 h), bulk density (800 kg/m3) and fill fraction (75%) - typical
assumptions.

## Nelson complexity (`complexity.py`)

NCI = sum F_i (C_i / C_CDU), with the factor table from Wikipedia's "Nelson
complexity index" page (1998 and older vintages). Other published tables
differ on hydrotreating (2.0 vs 3.0) and coking (5.5-6.0).

## Flowsheet (`flowsheet.py`)

CDU/VDU, then FCC on the whole VGO cut and a delayed coker on the vacuum
residue, into product pools; mass closure is asserted to 1e-9 in the tests.
Hydrotreating is sized per stream but not fed back into the balance (its
H2 uptake is small; H2S removal is reported separately).


## Indian reference data (`india.py`)

CHT's NCI table (capacity-weighted by company) and PPAC's GRM, distillate yield
and fuel & loss, hand-transcribed with provenance (`scripts/build_india_data.py`).
`indian_basket_usd_bbl` applies PPAC's own basket formula. `grm_nci_fit` is an
ordinary least-squares line over five companies - descriptive only.

## Gross refining margin (`grm.py`)

GRM per barrel of crude = value of saleable pools - crude cost - fuel & loss, as
PPAC (citing EIA) defines it. Pools are valued with a `PriceDeck`: gasoline-range
and middle-distillate at crude plus a crack ($/bbl); LPG, slurry, vacuum residue
and unconverted VGO at a fraction of crude value per barrel; petcoke at a fraction
of crude $/t. Fuel gas and FCC coke are consumed; a 4.4% configuration-independent
overhead stands in for fuel/loss the flowsheet does not model (PPAC Paradip 10.0%
minus the 5.6% modelled). `calibrate_deck` scales the light cracks so a reference
flowsheet reproduces a reported GRM exactly (GRM is linear in the scale). **The
default cracks are illustrative and unsourced.**

## Petrochemical addition (`petrochemical.py`)

Three routes from FCC propylene to polypropylene: conventional recovery (~34% of
the FCC LPG, i.e. 6 wt% of feed at the reference LPG yield of 17.8 wt%), ZSM-5
(1.5x that, 9 wt%), and propylene-mode (16.2 wt% of feed, implied by Paradip's
680 kt/y PP plant over its 4.2 Mt/y FCC). Each displaces fuel-pool product
(LPG; plus gasoline for the extra ZSM-5 propylene; plus gasoline/LCO 70/30 for
propylene-mode). PP-plant capex = Paradip's $451 M scaled by the six-tenths rule
(Peters & Timmerhaus); capital charge from a capital-recovery factor (12%, 20 y).
`evaluate` returns margin, GRM uplift and the **break-even PP price**;
`affordable_fcc_capex_usd` returns the most a propylene-mode revamp can cost.
No propylene or PP price is used anywhere. The Nelson index is unchanged by
construction (no polymer factor).


## Price deck and rundowns (`petchem_prices.py`, `rundown.py`)

`petchem_prices.py` stores dated observations (IOCL PP ex-works list in Rs/MT at three 2026 dates, the
USD/INR rate, a live crude snapshot, aggregator and propylene snippets with confidence tags) and builds a
`PetchemPriceDeck`. Only the PP level is observed; `propylene_usd_t` defaults to `None`. `realisation`
haircuts the list price. `petrochemical.verdict` returns break-even, headroom (realised price minus
break-even) and net margin; `breakeven_propylene_price_usd_t` is the price refinery-grade propylene must
fetch for a route to cover the fuel it displaces (no PP plant; recovery-unit capex excluded).

`rundown.py` lists the FCC rundown streams (dry gas, LPG with its propylene content, gasoline, LCO,
slurry, coke) with volumes, densities and sulfur; shifts heavy naphtha into LCO at the Digital Refining
slope (~0.18 vol% of feed per degC of gasoline end-point reduction); runs the FCC in distillate mode
(cooler riser plus end-point cut); and computes the FCC's share of the gasoline and diesel pools.
LCO/slurry sulfur split (slurry 2x LCO) and the heavy-naphtha density (780 kg/m3) are assumptions.


## Trade, ethanol, FCC modes, cracker, routes, sourcing, safety (added)

* `trade.py` - PPAC trade values / quantities give observed unit values; `TradeDeck` prices pools at LPG import, petrol/diesel export, fuel-oil
  and petcoke import values; `RebasedTradeDeck` keeps a year's cracks and price fractions at a new crude price; `petrol_balance` exposes the
  implied ethanol (consumption is blended petrol).
* `ethanol.py` - volume blend to mass share via ethanol 789 and petrol 745 kg/m3; refinery petrol = MS x (1 - ethanol mass share).
* `fcc_modes.py` - modes from the FCC model plus mass-conserving shifts; wet-gas load from the PCS paper's Figure 8 slope and Figures 9-10
  for the mitigation; dry-gas term extrapolated.
* `steam_cracker.py` - yield slate interpolated on coil-outlet temperature from cited points; conservative co-product values; capex six-tenths.
* `routes.py` - per-route gasoline removed, fuel-only margin, petrochemical margin and capital charge on one deck.
* `crude_sourcing.py` - realised vs basket, shock bill, value of a basis point and grid, partner self-financing ratio, assay-based relative
  crude value, Russian-crude news accessors.
* `safety.py` - OISD list, design-element map, screening flags with a basis string each.

* `dual_feed_cracker.py` - propane slate from the BP patent table (interpolated on conversion), propane and ethane recycled to extinction (ethane
  selectivity from the patent's Table 2), butane assumed; naphtha slate from `steam_cracker.py`; capex on total feed by the six-tenths rule; LPG priced at
  the deck's import-parity value; refinery LPG supply = LPG pool minus the FCC propylene kept for PP; LPG above that is flagged as imported.
