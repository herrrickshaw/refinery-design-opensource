# Indian refiners: how they ran, how their FCCs changed, what is planned

`refinery_design.companies` holds 24 Indian refineries by company - IOCL (9), BPCL (3), HPCL (2), HMEL, HRRL, Reliance (Jamnagar DTA and SEZ),
Nayara, CPCL (2), MRPL, NRL and ONGC's Tatipaka - with capacity, crude throughput, distillate yield and GRM by fiscal year (FY2015-16..FY2025-26),
FCC-family units, dated FCC changes and announced plans. One thin module per company (`iocl`, `bpcl`, `hpcl`, `reliance`, `nayara`, `others`)
carries that company's caveats. Run `python examples/india_companies.py`; the app has an **Indian refiners** tab.

## Where the data comes from

Three extraction passes in September 2026 (`research/*.json`, kept in the repo so `scripts/build_companies_data.py` is reproducible):

| Group | Sources |
|---|---|
| IOCL | PPAC Ready Reckoners; IOCL annual reports FY2015-16..FY2024-25; the Q4 FY26 earnings call; IOCL refinery pages; OGJ (Aug 2026) |
| BPCL, HPCL, HMEL, HRRL | company annual reports and investor presentations; PPAC; CHT; HPCL/BPCL press releases |
| Reliance, Nayara, CPCL, MRPL, NRL, ONGC | IPNG 2019-20 (an image-only PDF, read by OCR); PPAC refinery-wise crude-processing endpoint; CPCL/MRPL/NRL annual reports; press |

The IOCL page you pointed to (*IndianOil's SPRINT Fuelling India's Growth*, Integrated Annual Report 2025-26) is a strategy page: Project SPRINT, launched
April 2025, 25 goals, six priorities (Core, Cost, Customer, Technology, Talent, Transition). **It contains no refinery figures**, and no other section of
that report was reachable, so IOCL's FY2025-26 numbers come from the Q4 FY26 call and PPAC.

Every value has a source; where two sources disagree the primary is kept and the others are listed under `alt` (company annual report over PPAC over CHT
over calls and press). Nothing is estimated.

## How the refineries ran: FY2015-16 against FY2025-26

Utilisation below is **derived** (crude processed / capacity on 1 April), not company-reported.

* **Capacity added, and where.** IOCL 54.2 -> 70.3 MMTPA (Paradip's 15 MMTPA came in 2016); BPCL 21.5 -> 35.3 (Kochi 9.5 -> 15.5, Bina 6.0 -> 7.8, folded into
  BPCL's total from 2023); HPCL's own refineries 14.8 -> 24.5 (Visakh 8.3 -> 15.0, +81%; Mumbai 6.5 -> 9.5). HMEL 9.0 -> 11.3.
* **Everyone runs above nameplate.** FY2025-26 roll-ups: IOCL 75.3 MMT on 70.25 (107%), BPCL 41.0 on 35.3 (116%), HPCL 26.0 on 24.5 (106%), MRPL 111.8%,
  CPCL Manali 111.5%, NRL 103.8%. BPCL Mumbai is the extreme: 129.8% in FY2024-25 on a 12 MMTPA nameplate unchanged since 2006 (BPCL's own figure).
* **Private refiners are the exception.** Reliance 98.7% (67.3 MMT on 68.2) and Nayara 94.3% - Nayara down 8% in FY2025-26 to 18.85 MMT from 20.49, with
  monthly runs of 1.41 and 1.24 MMT in August and September 2025 against about 1.70 normally (cause per press, not a filing).
* **Older IOCL refineries are flat.** Throughput FY2015-16 -> FY2025-26: Barauni -1.5%, Gujarat -4.3%, Panipat +3.9%, Haldia +9.0%, Mathura +12.4%; growth is
  in the small North-East refineries (Guwahati +44%) and the new capacity.
* **Distillate yield has not risen at company level.** IOCL reported 80.6% in FY2015-16 ("best ever") and 80.6% in FY2024-25 ("a record"), between
  78.7% and 80.4% in the years in between. Refinery-wise (PPAC) it moved in both directions: Barauni 88.7 -> 83.1, Gujarat 83.1 -> 71.7, Panipat 83.8 -> 81.7,
  Haldia 69.6 -> 75.5. BPCL reported 84.3% (FY2024-25) and HPCL 75.8% (FY2025-26).
* **GRM.** IOCL $5.06 (FY2015-16), $19.52 (FY2022-23), $4.80 (FY2024-25); IOCL and MRPL stopped publishing FY2025-26 GRM (PPAC footnote).

## How the FCCs have been tweaked

The honest answer is narrower than the question: **no source reached publishes FCC yields, conversion or propylene wt%**, so a change of operating mode
(gasoline-max to LPG/propylene-max) cannot be measured. What *is* documented is structural, and it all points one way - toward propylene and petrochemical feed:

| What | Evidence |
|---|---|
| **INDMAX and petro-FCC units, built and coming** | Operating INDMAX with known capacity: Paradip 4.27 (2016), Bongaigaon 0.74 (2020), Guwahati pilot 0.1 = **5.11 MMTPA**. Due: Gujarat 2.7 (Nov 2026), Panipat 2.5 (Dec 2026) = **+5.2 MMTPA**, plus a CPCL Cauvery Basin INDMAX with no capacity found. Petro-FCCs: MRPL (2014), HMEL, Kochi (nameplates not found); HRRL 2.9 (July 2026) and NRL 1.95 (Dec 2026 target) add **4.85 MMTPA** |
| **Existing units expanded or replaced** | Barauni RFCC 1.4 -> 1.7 MMTPA (Dec 2026); Kochi PFCC revamp for homo-polymer PP feed with a 400 KTPA PP unit (Oct/Dec 2027, Rs 4,460 crore); BPCL Mumbai to replace its 40+-year-old CCU and FCCU with a PRFCC (about Rs 14,200 crore, 2029) |
| **Bottoms upgraded ahead of the FCC** | HPCL Visakh added a full-conversion hydrocracker (2023) and a 3.55 MMTPA LC-MAX residue upgrader (FY2025-26) - **not** a new FCC; the existing FCC-1 and FCC-2 receive more converted feed |
| **Small operating-mode and catalyst signals** | HPCL Mumbai co-processes plastic pyrolysis oil in the NFCC, has a ZSM-5 loader on it, and completed an additive trial at a Visakh FCC (AR 2024-25). No yield data given |
| **Debottlenecking is modest** | Mathura FCCU 1.3 -> 1.5 MMTPA (2014). CPCL Manali's FCCU record is 1,085 TMT in FY2025-26 against 1,084 in FY2017-18 and 1,075 in FY2014-15 - essentially unchanged while Manali's crude rose from 9.1 (FY2015-16) to 11.71 MMT; its OHCU and DCU set records in the same year (2,559 and 2,154 TMT), so the FCC was not where the extra crude showed up - an inference from records, not FCC throughput data for both years |
| **Petchem integration** | Nayara: propylene recovery unit + FCC upgrade + 450 ktpa PP (production expected Oct-Dec 2023, start not verified). MRPL PP 440 ktpa (2015). IOCL targets a petrochemical intensity index of 15% by 2030 from about 6.1% |

**Bina has no FCC.** BPCL's 7.8 -> 11 MMTPA expansion (Rs 43,367-49,800 crore depending on source, May 2028) adds a 1.2 Mt/y dual-feed *ethylene* cracker - the
steam-cracker route modelled in `dual_feed_cracker.py` - and its propylene goes to a 550 KTPA PP unit. Kochi, not Bina, is where BPCL's FCC propylene is.

**E20.** No refinery-level product-slate change tied to E20 was found in any source, only blending percentages; the petrol-volume effect in
`docs/PETROL_DISPLACEMENT.md` remains an all-India balance, not an observed refinery response.

## What is planned (capex as quoted; sources disagree in places)

Panipat 15 -> 25 MMTPA, 94% complete at 30 June 2026, Dec 2026, Rs 32,946 -> 38,231 crore (slipped from Sep 2024 in a 2022 report); Gujarat 13.7 -> 18 MMTPA
(Nov 2026); Barauni 6 -> 9 MMTPA (Dec 2026); Bina 7.8 -> 11 (May 2028); NRL 3 -> 9 MMTPA, Rs 22,594 -> 33,901 crore, Dec 2026 (one aggregator says Dec 2027, unverified);
CPCL Cauvery Basin 9 MMTPA, Rs 31,580 -> 36,354 crore; HRRL Barmer 9 MMTPA, Rs 79,459 crore, dedicated 4 July 2026; Nayara PP and a reported $8 billion ethane cracker
(media citing sources; Nayara did not comment). The full list, with each project's scope, cost and timing text, is `companies.plans()`.

## Limits

* **Utilisation is derived.** It matches company-reported figures within 1.5 points in 20 of 21 refinery-years where both exist (mean absolute difference 0.9 points;
  see `tests/test_companies.py`). The exception is Visakh FY2023-24 (derived 115%, reported 105%): its capacity stepped up during the year, so a company figure
  measured against capacity commissioned in the year would differ - an inference, not verified.
* **Above 125% is flagged.** The flag says whether a company figure confirms it (BPCL Mumbai: yes) or not (Reliance SEZ FY2015-16 to FY2017-18, 137%: the source's
  capacity column moved from 27 to 35.2 MMTPA in 2018, so those figures are probably not a real over-run). Roll-ups list unconfirmed refineries under `flagged`.
* **Capacity for Reliance, Nayara, CPCL, MRPL, NRL and ONGC** is published for 1 April 2015-2020 and 2026 only. FY2021-22..FY2025-26 is carried forward only
  where the 2020 and 2026 values are equal, and marked `inferred`; otherwise left blank (Cauvery Basin: 1.0 then 0).
* **FCC capacities are lower bounds.** Eight of the nine conventional FCC units (only Mathura's 1.5 MMTPA is known) and all three operating petro-FCCs have no published nameplate; the summary counts them separately.
* **Reliance's** own "total throughput" (80.0 MMT) is a different measure from crude processed (67.3). **Nayara** publishes no filings. **NRL's** GRM is not
  comparable (excise benefit, domestic crude).
* The FCC unit table and change timeline were transcribed by hand from the sourced facts (the sources describe them in prose); the series are mechanical.
  Events quoted by fiscal year are dated by the calendar year in which that fiscal year ends.
* Some single figures come from weak sources and are tagged in the JSON and the caveats: BPCL FY2025-26 from a third-party transcript, Paradip/Bongaigaon INDMAX capacities from
  trade press, HMEL's FCC size from one search summary, PPAC's IOCL FY2017-18 column (printed scrambled in two later editions; the November 2018 edition was used because it
  sums to the annual report's 69.0 MMT).
* Not found: IOCL's company-level FY2025-26 distillate yield; FY2025-26 annual reports for BPCL and HPCL; refinery-wise GRM after FY2017-18 (IOCL); Nayara and HMEL GRM;
  Reliance GRM after FY2019-20; any FCC yield or mode data. The full list is `companies.gaps()`.
