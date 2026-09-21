# Safety guidance for these designs: OISD and other sections

Reproduce with `examples/safety_review.py`; code in `refinery_design/safety.py`; standards list in
`refinery_design/data/oisd_standards.json` (built by `scripts/build_oisd_data.py`).

## What was and was not checked

| Verified | Confidence |
|---|---|
| The **list** of OISD standards, titles and current editions, from OISD's own site (105 entries, fetched 21 Sep 2026) | high |
| OISD-STD-116 (June 2025) requirement details, from an iFluids summary | medium |
| OISD-STD-118 separation distances, from a blog | low |
| FCC hazards (slide valves, afterburn) and naphthenic-acid corrosion thresholds, from technical articles (search summaries) | medium |
| Statutory framework (OISD, Factories Act 1948, MSIHC Rules 1989, PESO, PNGRB) from secondary sources | medium |

**The standards themselves were not read** - OISD sells them. This is therefore a *map to the right standards plus early-warning
flags from the model*, not a safety case, HAZOP, or a substitute for the standards, the licensor's package, or statutory approvals.
The OISD site does not present TLS chains that Python's `urllib` or WebFetch validate; system `curl` does, and verification was
never disabled.

**A correction the official list forced.** I had assumed OISD-STD-154 covered fired heaters. It is *Training in midstream and
downstream sector of petroleum industry*. Fired furnaces are **OISD-STD-111** (Process design and operating philosophies on fired
process furnace, Apr 2016) and **OISD-STD-133** (Inspection of fired heaters). The mapping and a test now use the official titles.

## Statutory context

OISD was set up in 1986 under MoPNG. Secondary sources describe compliance with the relevant OISD standards as mandatory for
refineries, petrochemical plants and LPG installations, with several standards incorporated into regulation. Also applicable: the
Factories Act 1948 and the Manufacture, Storage and Import of Hazardous Chemicals Rules 1989 (state factory inspectorates), PESO
(petroleum storage, compressed gases, pressure vessels), PNGRB technical standards (refineries and gas processing among them).

## Design element -> OISD standards (current editions from the list)

| Element | Standards |
|---|---|
| Layout, control rooms | **118** Layouts for Oil and Gas Installations (Jun 2025); **163** Safety of Control Room (Jun 2024); **113** Area classification for electrical installations (Oct 2013); **164** Fire proofing of steel supporting structures (Jul 2012) |
| Fire protection | **116** Fire protection facilities for petroleum refineries, **petrochemical complexes** and oil/gas processing plants (Jun 2025); GDN-115 fire-fighting equipment; 142 inspection of fire-fighting systems; 173 electrical installations |
| Crude / vacuum unit, furnaces | **111** fired process furnace (Apr 2016); **106** pressure relief & disposal (Oct 2010); 109 blow-down & sewer; 128 unfired pressure vessels; 130 piping; **133** fired heaters inspection |
| FCC reactor-regenerator | 106, 111, **112** air-hydrocarbon mixtures & pyrophoric substances (Aug 2019), **152** safety instrumentation (Jun 2024), 153 SIS maintenance, 128, **178** management of change (Aug 2023) |
| FCC gas plant (LPG/propylene mode) | 106, **240** asset integrity of rotary equipment (Jun 2024), 152, 116, 178 |
| Hydrotreater / hydrogen | **241** hydrogen and hydrogen blends (Jun 2024), 152, 128, 130, 114 hazardous chemicals, 106 |
| Delayed coker | 111, 112, 152, 128, 106 - **no coker-specific OISD standard is in the list** |
| LPG / propylene storage | **144** LPG installations (Aug 2026), 150 mounded storage, 236 refrigerated LPG storage, RP-158 bulk LPG, 116, 108 |
| Steam cracker | 111, 116, 241, 152, 106, 118 - **no cracker-specific OISD standard is in the list** |
| Polymer plants | 116, 113, RP-110 static electricity, GDN-180 lightning, 173 |
| Process safety management | 105 work permit (Aug 2023), 178 MoC, 145 internal audits, 227 emergency response, GDN-206 safety management system, 155 PPE, 154 training |
| Environment | 201, GDN-224 VOC, GDN-200 oil-spill contingency |

**What the secondary summary says OISD-STD-116 (2025) requires** (medium confidence): fire-water pressure 7 kg/cm2 at the remotest
point; water spray rings or monitors for columns over 45 m; automatic water spray for LPG/C4 vessels, hydrogen compressors and
loading gantries; water curtain for naphtha-cracker furnaces; sprinklers in polymer extruder, bagging and pelletising buildings;
petrochemical complexes explicitly in scope; cryogenic-liquid protocols. **Not verified against the standard**: whether propylene and
ethylene fall under the LPG standards (144/150/236) or need their own basis.

## What the models flag (Paradip-basket refinery, 15 mtpa; `examples/safety_review.py`)

* **Crude corrosivity:** literature rules of thumb - TAN of ~0.3-0.5 mgKOH/g for a crude and 1.5 mgKOH/g for a fraction - with the
  caveat that TAN alone is *not* a reliable predictor (sweet crudes with low TAN have corroded); attack occurs above ~232 C in
  crude/vacuum units unless the metallurgy is high-Mo (316/317L class), and overlaps with high-temperature sulfidation. Of the eight
  assays, **Dalia (TAN 1.50), Cold Lake (1.12; heavy fractions above 1.5) and Kearl (2.08)** raise the flag; the Paradip basket
  (TAN 0.55, 2.9 wt% S) is a *watch* item plus sour service. Bakken, Azeri, Qua Iboe do not; Upper Zakum and Alaska North Slope are
  flagged for sour service only. **The relative-value ranking in `CRUDE_SOURCING_AND_LOCAL_CURRENCY.md` does not price this** -
  Dalia's +$1.8/bbl advantage excludes metallurgy and inspection cost.
* **FCC regenerator:** above 760 C (this repo's heuristic threshold) is an *action* flag: afterburn and overheating can approach
  the metallurgical limit of internals; the Paradip basket's hydrotreated VGO still runs at 772 C. Slide valves are the catalyst
  barrier keeping hydrocarbons off the air side (an ExxonMobil 2015 incident followed slide-valve erosion) - scope them into the SIS
  (152/153).
* **FCC gas plant:** modes above +15% wet-gas flow are flagged for compressor, condensing, absorber/stripper, relief/flare and
  LPG/C4 fire-protection review (*watch* for high severity, x1.31; *action* for propylene mode, x1.73, beyond the PCS paper's
  demonstrated range). Every yield-mode change is a **management-of-change** event (OISD-STD-178).
* **Hydrotreater:** hydrogen make-up (88 t/day for the VGO unit) and H2S (346 t/day removed) put it under hydrogen (241) and hazardous
  chemicals (114).
* **LPG/propylene:** ~981 kt/y LPG-range product needs LPG installation and storage standards (144/150/236) and automatic water spray
  on LPG/C4 vessels.
* **Steam cracker and polymers:** 0.81 Mt/y ethylene and 0.45 Mt/y propylene from 3 Mt/y naphtha: new ethylene/propylene storage and
  refrigeration, a hydrogen-rich stream, furnace water curtain and polymer-building sprinklers under the 2025 fire standard.

## Dual-feed (LPG) crackers

`safety.dual_feed_flags` adds propane/butane feed handling to the cracker flags: refrigerated or pressurised feed storage, vaporisers and feed-gas
piping to the furnaces (a leak is a vapour-cloud source), fixed gas detection, and automatic water spray on LPG vessels (OISD-STD-116, 2025, per the
secondary summary) with layout separation under OISD-STD-118. The LPG installation standards are OISD-STD-144 (edition Aug 2026), 150 (mounded) and
236 (refrigerated); whether they govern a cracker's feed storage was not verified.

## Limits

No consequence modelling, no relief or flare load calculation, no SIL determination and no layout were done. The 760 C and 15%
flags are this repo's screening heuristics. The separation distances quoted by the blog are unverified. Treat everything here as
"which standard to open, and what to ask the licensor", not as compliance.
