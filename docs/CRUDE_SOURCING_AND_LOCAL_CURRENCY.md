# Crude sourcing strategies and local-currency settlement

Reproduce with `examples/crude_sourcing_study.py`. Data: PPAC Ready Reckoner FY2025-26 (Tables 8.1 Indian basket and 8.24 crude
imports); EcoNiti, Outlook Business/MoPNG, SEAIR/IBEF, news on Russian crude (confidence tagged in `data/crude_sourcing.json`);
a live crude snapshot (Brent $102.47, Dubai $116.35, WTI $94.62, Urals $106.45 on 21 Sep 2026).

## The headline, stated carefully

**No source found quantifies a saving from settling crude in rupees or other local currencies, and the one official statement
found points the other way for the importer**: MoPNG, as reported by Outlook Business on 24 December 2023, noted that suppliers cited repatriation of
funds and the high cost and exchange-rate risk of conversion, and that IOC bore high transaction costs because suppliers passed the
extra costs on to it. In FY2022-23 no PSU crude import was settled in rupees.
The only cost figure found is a ~2% average transaction cost paid by Indian *exporters* to the UAE (India-UAE local-currency
settlement coverage) - not a crude number. This study therefore gives arithmetic and feasibility tests, not a savings claim.

## 1. What the Indian basket says (PPAC)

The Indian basket ($/bbl): FY2021-22 79.18, FY2022-23 93.15, FY2023-24 82.58, FY2024-25 78.56, FY2025-26 70.99; 2026: Jan 63.08,
Feb 69.01, **Mar 113.49, Apr 114.48**, May 106.23, Jun 83.22 (peak ~$135 in the first week of April). PPAC ties it to the
US-Israel-Iran conflict from 28 February 2026 and Hormuz disruption. India's realised crude price against the basket (value /
barrels, Table 8.24):

| FY | basket | realised | gap $/bbl | gap $bn |
|---|---|---|---|---|
| 2021-22 | 79.18 | 77.51 | -1.67 | -2.6 |
| 2022-23 | 93.15 | 92.36 | -0.79 | -1.4 |
| **2023-24** | 82.58 | 77.67 | **-4.91** | **-8.4** |
| 2024-25 | 78.56 | 76.94 | -1.62 | -2.9 |
| 2025-26 | 70.99 | 68.49 | -2.50 | -4.5 |

India paid below the basket in seven of the last eight years - the basket is a benchmark price, so this is net of freight and
insurance, and it also carries grade mix and timing. FY2023-24, the discounted-Russian-crude year, is the widest. The 2026 shock
cost roughly **$21 bn** extra over March-June versus the February basket (imports assumed at 1/12 of FY2025-26 volume per month).
August 2026: import bill $11.7 bn vs $9.9 bn a year earlier (+18.2%) on 3% lower volume; average $90.19/bbl vs $69.11.

## 2. Russian crude: what the news says (low-medium confidence; sources conflict)

Volumes ~2.8 mb/d in July 2026 (record, ~56% of India's crude), ~2.0 mb/d in August (-26%, ~45%), 1.42 mb/d in the first 14 days of
September. Reasons reported for August: US tariff pressure, Ukrainian drone strikes (about 40% of Russian export capacity removed
by March 2026, per one analysis), and China outbidding (Russian imports ~1.7 mb/d in August vs ~1.4 in July). Reliance's purchases
fell to ~292,000 b/d under EU rules; Nayara is under sanctions and running ~400,000 b/d; IOC, BPCL and HPCL increased purchases;
the US issued a 30-day waiver for stranded cargoes in March, a second, and reportedly let it lapse by May-June.

**Price.** Delivered discounts to Dated Brent are reported anywhere from about -$12 (post-2022 era) to +$4.5 (a first-ever premium
in March-April 2026); July is reported as ">$10 discount" by one source and August as "parity or slight premium" by another - these
conflict. The live 21-Sep snapshot has Urals **$3.98 above Brent** (and Dubai $13.88 above Brent). Freight is a floor on the
discount: ~$20/bbl from Novorossiysk to India's west coast vs ~$13 from the Baltic. **Payment currency for Russian crude was not
stated in any source found.** Circumstantially, rupee-settled imports rose from Rs 42,506 crore (Dec-Feb) to Rs 1.38 lakh crore
(Mar-May 2026, ~$14.6 bn, 7.1% of imports) alongside Russian crude imports of $17.13 bn in Mar-May (+30% y/y).

So "shift to Russian crude as an alternative" is, today, a **volume and security** answer (a non-Gulf source when Hormuz is
disrupted), not a discount answer - and it carries sanctions, drone-strike and Chinese-competition risk.

## 3. Local-currency settlement: scale, arithmetic, feasibility

* **Scale.** Rupee-settled imports (all goods): Rs 99,680 crore (FY24) -> ~1.13 lakh crore (FY25) -> ~1.72 lakh crore (FY26); that is
  15.7% of the FY25-26 crude bill *in rupee terms* (the numerator is not crude-only).
* **Arithmetic.** One basis point of cost difference on the whole FY25-26 crude bill ($123.4 bn) is **$12.3 M/yr**. Switching 25%
  of the bill at +25 bp saves ~$77 M/yr; at -25 bp it costs ~$77 M/yr. Even 100 bp on the full bill is $1.2 bn. The grid is in
  `crude_sourcing.local_currency_grid()`; the sign of the basis points is the unresolved question.
* **Feasibility - can the partner recycle the rupees?** A supplier accepts rupees only if it can spend them. India's exports as a
  share of imports (total trade, FY2025-26; Saudi FY2024-25; aggregator figures, low confidence):

| Partner | exports/imports | trade gap | crude share (Q1 FY26) |
|---|---|---|---|
| UAE | 0.58 | $26.5 bn | 11.0% |
| Saudi Arabia | 0.39 | $18.4 bn | 16.0% |
| Iraq | 0.12 | $21.6 bn | 19.9% |
| Russia | 0.08 | $50.9 bn | 17.9% |

  The UAE, with the deepest two-way trade and an RBI-CBUAE local-currency framework (2023; IOC's first rupee payment for 1 million
  barrels of ADNOC crude in Dec 2023), is the only large crude partner that can plausibly absorb rupees; Russia, Iraq and Saudi
  Arabia would accumulate them. That is the mechanism behind the suppliers' objection, and it is consistent with the pass-through
  MoPNG reported.

## 4. Crude sourcing strategy (from the basket, assays and refinery model)

1. **Value crude in the refinery, not on the benchmark.** At PPAC FY25-26 cracks and today's Brent, the flowsheet's net product
   value per barrel, relative to Azeri BTC: Qua Iboe +$2.2, Dalia +$1.8, Bakken -$1.8, Alaska North Slope -$3.0, Upper Zakum
   **-$4.8**, Kearl -$6.6, Cold Lake -$8.5. Against market spreads of Dubai **+$13.9**, WTI -$7.8, Urals +$4.0 over Brent, a
   Dubai-linked sour barrel is priced ~$19/bbl above its relative value here (before freight, which is not in the data) while a
   WTI-linked light barrel is ~$6/bbl cheap. Assay proxies stand in for the market grades (Upper Zakum for Dubai-linked sour,
   Bakken for WTI); Urals has no assay, so it is not ranked.
2. **Price in the safety and metallurgy cost.** Dalia ranks well but is high-TAN (1.50 mgKOH/g); Cold Lake and Kearl carry high TAN
   and sulfur (`SAFETY.md`). Corrosion-resistant metallurgy and inspection are not in the netback.
3. **Diversify across regions, then across currencies.** Middle-East dependence was 58% of crude in FY2022-23 (MoPNG via Outlook
   Business); the 2026 shock cost ~$21 bn in four months. Atlantic-basin sweet/medium crudes (Nigeria, Angola, US, Azerbaijan) are
   where the relative-value table and the current spreads point, subject to freight; Russian volume is a security source at
   uncertain price and legal risk.
4. **Settle locally only where the partner can recycle the currency** (UAE first) and treat any saving as unproven until an
   actual transaction-cost comparison is available; the value at stake is ~$12 M/yr per basis point on the whole bill.
5. **Hedge the price, not just the currency**: the 2026 shock ($21 bn in four months) dwarfs any plausible settlement saving
   (25 bp on 25% of the bill is ~$77 M/yr).

## Not established here

Any measured saving from local-currency crude settlement; the payment currency of Russian crude; country-wise crude volumes for
FY2025-26 (PPAC's pages did not carry them; the Q1 shares are a news snippet); freight differentials by route; the sanctions and tariff
position after the waivers. The bilateral trade figures come from aggregator snippets (low confidence).
