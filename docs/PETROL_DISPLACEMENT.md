# Petrol displaced by ethanol: options and a secondary FCC mode

Reproduce with `examples/petrol_displacement.py`. Data: PPAC Ready Reckoner FY2025-26 (Tables 4.5, 4.11, 6.1, 6.10) and
its January-2026 Industry Consumption Report; OMC tender reports; Process Consulting Services (PCS), *Mitigating FCC gas
plant impacts when increasing reactor LPG yields*, Digital Refining PTQ Q2 2023 (read in full, figures included).

## 1. What PPAC shows

| FY | MS consumed | MS produced | imports | exports | refinery petrol used at home | implied ethanol |
|---|---|---|---|---|---|---|
| 2022-23 | 35.0 | 42.8 | 1.1 | 13.1 | 30.8 | 4.2 MMT (12% of MS mass) |
| 2023-24 | 37.2 | 45.1 | 0.7 | 13.5 | 32.3 | 4.9 (13%) |
| 2024-25 | 40.0 | 48.3 | 0.2 | 15.8 | 32.7 | 7.3 (18%) |
| 2025-26 | 42.6 | 49.8 | 0.0 | 16.7 | 33.1 | 9.5 (22%) |

PPAC's MS consumption is *blended* petrol, so production + imports - exports falls short of it by the ethanol blended;
the gap tracks PPAC's own blending percentages (ESY 2024-25: 19.24%; ESY 2025-26 Nov-Mar: 19.99%). Three things follow:

* **Domestic demand kept growing** (MS +6.4% Apr-Jan FY2025-26, January 2026 3.51 MMT +6.1%) while the blend rose, so the
  refinery petrol placed at home rose only 30.8 -> 33.1 MMT in three years;
* **Refineries made more petrol anyway** (42.8 -> 49.8 MMT) and **exported the surplus**: petrol exports 13.1 -> 16.7 MMT.
  The "displacement" has so far been absorbed by exports, i.e. moved to international price risk, not shut in;
* At FY2025-26 demand, E20 leaves refineries supplying 33.7 MMT of 42.6 MMT (ethanol 20.9% of mass, since ethanol is denser
  than petrol); going from E12 to E20 freed **3.5 MMT/yr**; E27 or E30 would free a further 3.1 or 4.4 MMT. After E20 the
  step is over and refinery petrol demand grows again with MS (~6%/yr, ~2 MMT/yr).

**Ethanol tenders** (news-sourced, medium/low confidence): the OMC ESY 2025-26 Cycle 1 tender asked for 1,050 crore litres
and drew offers of 1,776.49 crore (sugarcane 471.63, grain 1,304.86); FCI-rice ethanol Rs 60,320/kl (Rs 58,500 the year
before); the Supreme Court allowed a further 149 crore litres for Q-IV; ESY 2026-27 demand is expected at 1,150-1,212 crore
litres (60.6 bn litres of petrol at 20%). Installed capacity (~2,000 crore litres) is about twice the demand, so **the
mandate is supply-secure, not supply-constrained** - E20 is a permanent step, not a shortage that will unwind. No ESY 2026-27
tender allocation was found.

## 2. Options when the petrol outlet shrinks

| # | Option | Status here |
|---|---|---|
| 0 | Export the surplus petrol (what India is doing) | baseline; exports 16.7 MMT at $689/t FY25-26 (PPAC) |
| 1 | FCC distillate mode (cooler riser, gasoline end point down) | modelled |
| 2 | FCC ZSM-5 / LPG mode | modelled |
| 3 | FCC high-severity + ZSM-5 | modelled |
| 4 | Propylene-mode FCC (Paradip-type INDMAX) | modelled |
| 5 | Convert the extra propylene to PP | modelled (`petrochemical.py`) |
| 6 | Send straight-run naphtha to a steam cracker (PE + PP) | modelled (`steam_cracker.py`) |
| 7 | Lower reformer severity / aromatics (PX, benzene) | listed, not modelled (no reformer in the flowsheet); PPAC shows benzene among exports |
| 8 | Alkylate/isomerate less | listed, not modelled |
| 9 | Ethanol allows a lower-octane petrol pool (less reformer severity) | qualitative, not verified here |

## 3. The gasoline-lean FCC mode (Mode B) and the gas plant

The FCC is the gasoline machine, so the lever is a **secondary mode of operation** that runs the FCC gasoline-lean. What the
PCS paper establishes (facts read from its text and figures):

* wet-gas flow rises with reactor propylene: Figure 8, 34,500 -> 39,700 -> 44,300 ICFM at 7.5 / 10.3 / 13.1 wt% C3= at
  constant dry gas, 130 F and 3.5 psig - **+5.1% per +1 wt% propylene**;
* it falls with receiver pressure (Figure 9, 13.1 wt%: 44,300 / 36,000 / 30,000 ICFM at 3.5 / 6.5 / 9.5 psig) and temperature
  (Figure 10: 130 -> 115 F cuts 34,500 -> 30,200 ICFM, ~0.8%/F; the text's rule of thumb is ~1%/F);
* the cheap moves are a pressure survey, removing main-column inlet-nozzle coke (2-4 psi), trays to packing (2-4 psi), air
  fin-fan bundles (2-5 psi), removing the wet-gas flow meter (1-2 psi), extra cooling-water flow;
* absorber C3= recovery is typically 95-99% today (85-90% historically); operate at >=98% (<=3 mol% C3= in the off-gas); the
  debutanised-gasoline recycle must rise (their example: 5 -> 25 kb/d); +20 psi absorber pressure or -20 F improves recovery;
* ZSM-5 cracks mid-boiling gasoline to LPG, raises wet-gas flow and cuts liquid to the absorber, **reducing** C3= recovery;
* incremental LPG that cannot be recovered simply moves from the gasoline pool to fuel gas; the paper concludes that raising
  LPG at gasoline's expense "increases profitability due to product differential values" - but only if it is recovered.

On the Paradip-basket refinery (VGO hydrotreated, FCC feed 4.2 Mt/y), with wet-gas load from the paper's slope (dry-gas term is
this repo's extrapolation):

| Mode | gasoline / LPG / LCO wt% | propylene | gasoline change | wet-gas load | gas-plant fix |
|---|---|---|---|---|---|
| gasoline (base) | 47.8 / 11.8 / 22.4 | 4.0 | 0 | 1.00 | - |
| distillate (riser -11 C, end point -50 F) | 42.5 / 10.1 / 29.1 | 3.4 | -214 kt/y | 0.92 | none (unloads it) |
| LPG (ZSM-5, x1.5 propylene) | 44.5 / 15.1 / 22.4 | 6.0 | -134 kt/y | 1.10 | receiver -11 F or +1.5 psi |
| high severity (+20 C, ZSM-5) | 43.9 / 20.0 / 18.2 | 7.9 | -157 kt/y | 1.31 | receiver -29 F or +4.1 psi; compressor/driver likely |
| propylene mode (16.2 wt%) | 35.5 / 33.8 / 12.7 | 16.2 | -496 kt/y | 1.73 | **beyond the paper**: new compressor and gas plant |

The E12 -> E20 step displaces about **367 kt/y** of this refinery's 3,861 kt/y gasoline-range pool. ZSM-5 or high severity
alone remove 134-157 kt/y; distillate mode 214 kt/y; only the propylene mode (496 kt/y) or a combination covers it.
A propylene-mode yield of 16.2 wt% is the value implied by Paradip's published PP/FCC capacities, not modelled kinetics.

## 4. What each route earns (Sept-2026 crude, PPAC FY25-26 cracks, IOCL PP/PE list prices)

| Route | gasoline removed | fuel-only change | PP/PE margin (before capital) | net of capital charge |
|---|---|---|---|---|
| distillate: sell LPG/LCO | 214 kt | -$30 M/y | - | -$30 M/y |
| ZSM-5: sell LPG | 134 kt | -$25 M/y | - | -$25 M/y |
| ZSM-5 + PP unit | 134 kt | +$31 M/y | +$56 M | **+$15 M/y** |
| high severity: sell LPG | 157 kt | -$39 M/y | - | -$39 M/y |
| high severity + PP unit | 157 kt | +$70 M/y | +$110 M | **+$46 M/y** |
| propylene mode: sell LPG | 496 kt | -$117 M/y | - | -$117 M/y |
| propylene mode + PP unit | 496 kt | +$228 M/y | +$344 M | **+$179 M/y** |
| naphtha cracker -> PE + PP (1.5 Mt) | 1,545 kt | - | -$123 M | -$577 M/y |

(LCO at 0.9 x diesel with its hydrotreating cost excluded; PP-route net is after a capital charge on the PP plant only -
**FCC-side capex is not included**; all against one deck.) Reading it:

* **Selling the extra LPG or LCO as fuel loses money** at these prices: gasoline ($967/t) is worth more than LPG ($783/t) or
  discounted LCO. Fuel-only mode switching is not a profit lever in this deck; it is a *volume* lever.
* **The profit comes from polypropylene**, so the FCC mode switch is a petrochemical decision. Break-even PP price under this
  observed-price deck: **$1,058 / 1,097 / 1,126 per t** (conventional / ZSM-5 / propylene mode) against the $1,612/t IOCL list
  price. Under the earlier GRM-calibrated decks the break-evens were $1,182-1,320 (their cracks were wider); both are in
  `PETROCHEMICAL_EVALUATION.md`. At list price the propylene-mode FCC could cost up to ~$2.3 bn (FY25-26 cracks at today's
  crude) or ~$3.6 bn (FY25-26 prices as observed) before the option stops paying its capital charge.
* **India's own LPG position makes LPG-mode more valuable than the fuel price says and PP more valuable than LPG:** LPG imports
  are 21.3 MMT (64% of consumption, $11.3 bn) - each tonne of FCC LPG replaces an import - but LPG is priced at the *import*
  unit value ($531/t FY25-26), which is what the deck uses.

## 5. Proposed secondary mode of operation

**Mode B - "gasoline-lean / propylene-lean FCC"**, staged so each step fits the gas plant:

1. **Stage 0 (no capital):** pressure survey of the main column to wet-gas compressor path; fix nozzle coking; raise receiver
   pressure/lower receiver temperature; note the compressor curve margin. Run the distillate variant (riser -11 C, end point
   -50 F) whenever gasoline is oversupplied and diesel is worth more than gasoline: it *unloads* the gas plant (0.92x) and
   removes ~214 kt/y - but its LCO needs hydrotreating (cetane ~20), not costed here.
2. **Stage 1 (additive):** ZSM-5 (x1.5 propylene). On a typical lighter VGO that is 6 -> 9 wt% (+15% wet-gas flow: about -16 F
   or +2 psi); on the Paradip basket's low-LPG feed it is 4 -> 6 wt% (+10%: -11 F or +1.5 psi). Watch C3= recovery and
   debutaniser recycle. Only pays with PP or a propylene buyer (fuel-only: -$25 M/y).
3. **Stage 2:** riser +20 C plus ZSM-5 (~8 wt% propylene, x1.31): compressor/driver and absorber changes probable.
4. **Stage 3:** a dedicated propylene-mode unit with its own gas plant and PP - the Paradip route; beyond what a tweak can do.

**Trigger:** run Mode B when the PP price exceeds the stage's break-even (about $1.06-1.13 k/t here) with margin for
realisation risk, and the petrol export netback is weaker than the LCO/LPG alternative; otherwise run the base mode. Every
mode change goes through management of change and the safety review (`SAFETY.md`): wet-gas load, relief/flare loads, LPG/C4
fire protection, and SIS.

**Caveats.** Mode yields other than propylene are this repo's shifts (mass-conserving; propylene 60% of incremental LPG; the
propylene-mode split 70/30 gasoline/LCO) - none are in the PCS paper. The wet-gas ratio is relative to base; absolute compressor
capacity is unit-specific and not modelled. The paper demonstrates 7.5-13.1 wt% propylene; the propylene mode is outside it.
