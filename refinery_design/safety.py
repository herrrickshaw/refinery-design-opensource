"""Safety guidance mapped onto these designs: which OISD standards apply, and what the model's own outputs flag.

**What this is - and is not.**  The OISD standards are sold by OISD and were *not* read.  What was verified:
(1) the list of standards, titles and current editions, from OISD's own site (``data/oisd_standards.json``);
(2) requirement details for OISD-STD-116 (June 2025) from a secondary summary (iFluids) and for OISD-STD-118 from a blog
(both tagged, lower confidence); (3) FCC hazards and naphthenic-acid corrosion thresholds from published technical
articles.  Where a number is used here it carries its source; screening thresholds that are this repo's own are labelled
``repo heuristic``.  This is a pointer to the right standards and a set of early flags - NOT a safety case, HAZOP or a
substitute for the standards, licensors' packages, or statutory approvals.

Statutory context (secondary sources): OISD was set up in 1986 under MoPNG; compliance with the relevant OISD standards is
described as mandatory for refineries, petrochemical plants and LPG installations, with several standards incorporated into
regulation; the Factories Act 1948 and the MSIHC Rules 1989 (state inspectorates), PESO (petroleum storage, compressed
gases, pressure vessels) and PNGRB technical standards also apply.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "oisd_standards.json"

# published rule-of-thumb thresholds for naphthenic acid corrosion (literature via search summaries)
TAN_CRUDE_WATCH = 0.5          # mgKOH/g; "0.3-0.5" in the literature, older rule of thumb 0.5
TAN_FRACTION_WATCH = 1.5       # mgKOH/g for a crude fraction
NAPHTHENIC_ACID_MIN_T_C = 232.0   # ~450 F: above this in crude/vacuum units unless high-Mo alloy (316/317L)


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def standard(number: str) -> dict:
    """{"title", "edition"} for an OISD number such as ``"OISD-STD-116"``."""
    return dict(_raw()["standards"][number])


def all_standards() -> dict:
    return {k: dict(v) for k, v in _raw()["standards"].items()}


# design element -> (OISD numbers, what to check, basis)
DESIGN_MAP: dict[str, dict] = {
    "layout": {
        "oisd": ["OISD-STD-118", "OISD-STD-163", "OISD-STD-113", "OISD-STD-164"],
        "check": "unit blocks, control-room siting and blast resistance, electrical area classification, fire-proofing of supports. "
                 "A secondary source quotes 30 m between process blocks, 30 m to a blast-resistant control room, 60 m to the boundary "
                 "and a 1.6 kW/m2 boundary limit for flares - NOT verified against the standard.",
        "basis": "OISD list (verified); distances: blog, low confidence"},
    "fire_protection": {
        "oisd": ["OISD-STD-116", "OISD-GDN-115", "OISD-STD-142", "OISD-STD-173"],
        "check": "OISD-STD-116 (Jun 2025) now covers petrochemical complexes. Per a secondary summary: fire-water pressure 7 kg/cm2 at "
                 "the remotest point; water spray rings or monitors for columns > 45 m; automatic water spray for LPG/C4 vessels, "
                 "hydrogen compressors and gantries; water curtain for naphtha-cracker furnaces; sprinklers in polymer extruder, bagging "
                 "and pelletising buildings.",
        "basis": "OISD list (verified); requirements: iFluids summary of the 2025 edition, medium confidence"},
    "crude_unit": {
        "oisd": ["OISD-STD-111", "OISD-STD-106", "OISD-STD-109", "OISD-STD-128", "OISD-STD-130", "OISD-STD-133"],
        "check": "fired furnace design/operation, relief and disposal, blowdown and sewer, inspection of pressure vessels, piping and "
                 "fired heaters. High-TAN crude: naphthenic-acid corrosion above ~232 C unless 316/317L-class alloy; it overlaps with "
                 "high-temperature sulfidation for sour crude.",
        "basis": "OISD list (verified); corrosion: technical literature via search summaries"},
    "fcc_reactor_regenerator": {
        "oisd": ["OISD-STD-106", "OISD-STD-111", "OISD-STD-112", "OISD-STD-152", "OISD-STD-153", "OISD-STD-128", "OISD-STD-178"],
        "check": "keep hydrocarbons out of the air side: slide valves are the catalyst barrier between reactor and regenerator; erosion "
                 "or corrosion of a slide valve has caused hydrocarbon leakage into downstream equipment (ExxonMobil 2015 incident). "
                 "Afterburn can drive gas temperatures toward the metallurgical limit of regenerator internals; runaway afterburn can "
                 "cause catastrophic damage. Safety instrumentation (OISD-STD-152/153) and management of change (178) for any mode change.",
        "basis": "OISD list (verified); hazards: technical articles via search summaries"},
    "fcc_gas_plant": {
        "oisd": ["OISD-STD-106", "OISD-STD-240", "OISD-STD-152", "OISD-STD-116", "OISD-STD-178"],
        "check": "Shifting gasoline to LPG/propylene raises wet-gas flow (PCS paper: ~5.1% per wt% reactor propylene) and the "
                 "condensing and absorber load: check the wet-gas compressor (asset integrity, OISD-STD-240), relief and flare loads "
                 "(106), automatic water spray on LPG/C4 vessels (116), and route every yield-mode change through MoC (178).",
        "basis": "OISD list (verified); wet-gas facts: PCS paper (verified figures)"},
    "hydrotreater_hydrogen": {
        "oisd": ["OISD-STD-241", "OISD-STD-152", "OISD-STD-128", "OISD-STD-130", "OISD-STD-114", "OISD-STD-106"],
        "check": "high-pressure hydrogen service, H2S handling, hazardous chemicals, inspection of vessels and piping, relief.",
        "basis": "OISD list (verified)"},
    "delayed_coker": {
        "oisd": ["OISD-STD-111", "OISD-STD-112", "OISD-STD-152", "OISD-STD-128", "OISD-STD-106"],
        "check": "no OISD standard specific to the delayed coker was found in the list; furnace, pyrophoric-substance handling "
                 "(iron sulfide / coke), SIS, vessel inspection and relief apply. Drum switching and unheading procedures fall under "
                 "work permit (105) and SIS (152).",
        "basis": "OISD list (verified that no coker-specific standard is listed)"},
    "lpg_propylene_storage": {
        "oisd": ["OISD-STD-144", "OISD-STD-150", "OISD-STD-236", "OISD-RP-158", "OISD-STD-116", "OISD-STD-108"],
        "check": "LPG installations (144, edition Aug 2026), mounded (150) and refrigerated (236) storage. Whether propylene and "
                 "ethylene fall under these LPG standards or need their own basis is NOT verified - confirm with OISD/PESO.",
        "basis": "OISD list (verified); applicability to propylene/ethylene unverified"},
    "steam_cracker": {
        "oisd": ["OISD-STD-111", "OISD-STD-116", "OISD-STD-241", "OISD-STD-152", "OISD-STD-106", "OISD-STD-118"],
        "check": "cracker furnaces (111; 116 water curtain per the 2025 summary), hydrogen-rich stream (~90 mol% H2 in the cracked-gas "
                 "hydrogen; 241), cryogenic ethylene/propylene refrigeration (116 2025 cryogenic-liquid protocols; standard-specific "
                 "requirements not read), SIS (152), relief and flare (106). No OISD standard specific to the cracker was found.",
        "basis": "OISD list (verified); details: secondary summaries, medium/low confidence"},
    "polymer_plants": {
        "oisd": ["OISD-STD-116", "OISD-STD-113", "OISD-RP-110", "OISD-GDN-180", "OISD-STD-173"],
        "check": "extruder/pelletising/bagging buildings (sprinklers per the 2025 summary), electrical area classification, static "
                 "electricity, lightning protection. Polymer powder dust hazards are not covered by any OISD standard found.",
        "basis": "OISD list (verified); sprinklers: iFluids summary"},
    "process_safety_management": {
        "oisd": ["OISD-STD-105", "OISD-STD-178", "OISD-STD-145", "OISD-STD-227", "OISD-GDN-206", "OISD-STD-155", "OISD-STD-154"],
        "check": "work permit, management of change, internal audits, emergency response, safety management system, PPE, training.",
        "basis": "OISD list (verified)"},
    "environment": {
        "oisd": ["OISD-STD-201", "OISD-GDN-224", "OISD-GDN-200"],
        "check": "environment management, VOC monitoring, oil-spill contingency. FCC flue-gas SO2 scales with feed sulfur (see fcc.py).",
        "basis": "OISD list (verified)"},
}


@dataclass(frozen=True)
class SafetyFlag:
    topic: str
    level: str                       # "action", "watch" or "info"
    message: str
    standards: list[str] = field(default_factory=list)
    basis: str = ""


def _flag(topic, level, msg, element, basis) -> SafetyFlag:
    return SafetyFlag(topic, level, msg, list(DESIGN_MAP[element]["oisd"]), basis)


def crude_corrosion_flags(slate) -> list[SafetyFlag]:
    """Naphthenic-acid and sour-service flags from a crude or slate.  TAN is an unreliable predictor by itself (literature)."""
    out = []
    tan, s = slate.tan, slate.sulfur_wt
    cuts = {"kerosene": (150.0, 250.0), "diesel": (250.0, 370.0), "VGO": (370.0, 550.0), "vacuum residue": (550.0, float("inf"))}
    hot = []
    for name, (lo, hi) in cuts.items():
        c = slate.cut(lo, hi)
        if c.tan is not None and c.tan >= TAN_FRACTION_WATCH and hi > NAPHTHENIC_ACID_MIN_T_C:
            hot.append(f"{name} (TAN {c.tan:.1f})")
    if tan >= TAN_CRUDE_WATCH or hot:
        msg = (f"crude TAN {tan:.2f} mgKOH/g" + (f"; fractions above {TAN_FRACTION_WATCH} mgKOH/g: {', '.join(hot)}" if hot else "") +
               f": naphthenic-acid corrosion risk in crude/vacuum-unit sections above ~{NAPHTHENIC_ACID_MIN_T_C:.0f} C unless 316/317L-class "
               "alloy; TAN alone is not a reliable predictor - verify with corrosion monitoring and a materials review")
        out.append(_flag("crude corrosivity", "action" if hot else "watch", msg, "crude_unit", "literature thresholds (search summaries), medium confidence"))
    if s > 0.5:
        out.append(_flag("sour service", "watch", f"sulfur {s:.2f} wt% (sour by trading convention): H2S service, high-temperature "
                         "sulfidation (overlaps naphthenic-acid corrosion above ~232 C), pyrophoric iron sulfide on opening equipment",
                         "crude_unit", "OISD list (verified); mechanism: literature via search summaries"))
    return out


def fcc_flags(fcc_result, mode_results=None) -> list[SafetyFlag]:
    """Flags for an FCC result, and for a list of ``fcc_modes.FccModeResult`` if given."""
    out = []
    t = fcc_result.regen_temperature_C
    if t > 760.0:
        out.append(_flag("FCC regenerator temperature", "action", f"regenerator {t:.0f} C is above 760 C (repo heuristic): afterburn and "
                         "overheating can approach the metallurgical limit of internals - catalyst cooler, feed pretreat or lower severity",
                         "fcc_reactor_regenerator", "repo heuristic; mechanism from FCC literature"))
    elif t < 660.0:
        out.append(_flag("FCC regenerator temperature", "watch", f"regenerator {t:.0f} C is cold (repo heuristic): incomplete burn/afterburn risk",
                         "fcc_reactor_regenerator", "repo heuristic"))
    out.append(_flag("FCC reactor-regenerator isolation", "info", "slide valves are the catalyst barrier keeping hydrocarbons off the air side: "
                     "include slide-valve integrity and differential-pressure trips in the SIS scope", "fcc_reactor_regenerator", "FCC literature via search summaries"))
    for m in (mode_results or []):
        r = m.gas_plant.wgfr_ratio
        if r > 1.15:
            lvl = "action" if not m.gas_plant.within_paper_range else "watch"
            out.append(_flag(f"FCC gas plant ({m.name})", lvl, f"wet-gas flow x{r:.2f} of base"
                             + ("" if m.gas_plant.within_paper_range else " (beyond the PCS paper's demonstrated 7.5-13.1 wt% propylene)")
                             + ": wet-gas compressor, condensing, absorber/stripper, relief and flare loads and LPG/C4 fire protection need review; "
                             "management of change required", "fcc_gas_plant", "PCS paper (verified); OISD list (verified)"))
    return out


def hydrotreater_flags(hydrotreater_result) -> list[SafetyFlag]:
    h = hydrotreater_result
    return [_flag("hydrotreater", "info", f"{h.service}: hydrogen make-up {h.h2_makeup_kg_h*24/1000:,.0f} t/day, H2S {h.h2s_kg_h*24/1000:,.0f} t/day "
                  "removed: hydrogen and H2S service", "hydrotreater_hydrogen", "OISD list (verified); rates from hydrotreater.py")]


def cracker_flags(option) -> list[SafetyFlag]:
    out = [_flag("steam cracker", "watch", f"{option.ethylene_t_y/1e6:.2f} Mt/y ethylene, {option.propylene_t_y/1e6:.2f} Mt/y propylene: new "
                 "ethylene/propylene storage, refrigeration and hydrogen-rich streams; confirm applicable standards for ethylene/propylene", "steam_cracker",
                 "OISD list (verified); applicability unverified"),
           _flag("polymer units", "info", f"PE {option.pe_t_y/1e6:.2f} Mt/y and PP {option.pp_t_y/1e6:.2f} Mt/y: extruder/pelletising/bagging "
                 "buildings need sprinklers under the 2025 fire standard summary", "polymer_plants", "iFluids summary, medium confidence")]
    return out


def dual_feed_flags(option) -> list[SafetyFlag]:
    """Flags for a dual-feed (naphtha + LPG) cracker: adds propane/butane feed storage and handling to the cracker flags."""
    out = cracker_flags(option)
    if option.lpg_t_y > 0:
        out += storage_flags(option.lpg_t_y)
        out.append(_flag("LPG-fed furnaces", "watch", f"{option.lpg_t_y/1e3:,.0f} kt/y propane/butane feed: refrigerated or pressurised feed storage, "
                         "vaporisers and feed-gas piping to furnaces; a leak is a vapour-cloud source - fixed gas detection and automatic water spray on LPG vessels "
                         "(OISD-STD-116 2025 summary), layout separation (118)", "steam_cracker", "OISD list (verified); details: summaries, medium/low confidence"))
    return out


def storage_flags(lpg_t_y: float, propylene_t_y: float = 0.0) -> list[SafetyFlag]:
    msg = f"LPG-range product {lpg_t_y/1e3:,.0f} kt/y" + (f", of which propylene {propylene_t_y/1e3:,.0f} kt/y" if propylene_t_y else "") + \
          ": LPG installation, mounded/refrigerated storage and automatic water spray on LPG/C4 vessels; propylene applicability to the LPG standards not verified"
    return [_flag("LPG/propylene handling", "watch", msg, "lpg_propylene_storage", "OISD list (verified); applicability unverified")]


def refinery_review(result, modes_list=None, cracker=None, slate=None) -> list[SafetyFlag]:
    """Aggregate flags for a flowsheet result (and optional FCC modes / cracker / crude slate)."""
    out = list(crude_corrosion_flags(slate)) if slate is not None else []
    if result.fcc is not None:
        out += fcc_flags(result.fcc, modes_list)
    if result.vgo_hydrotreater is not None:
        out += hydrotreater_flags(result.vgo_hydrotreater)
    lpg = result.pools_kg_h["lpg"] * 8400.0 / 1000.0
    out += storage_flags(lpg)
    if result.coker is not None:
        out.append(_flag("delayed coker", "info", f"coke drum volume {result.coker.drum_volume_m3:,.0f} m3: drum switching/unheading procedures under "
                         "work permit and SIS; no coker-specific OISD standard listed", "delayed_coker", "OISD list (verified)"))
    if cracker is not None:
        out += cracker_flags(cracker)
    return out
