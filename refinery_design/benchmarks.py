"""Published data for a real refinery, used as a validation benchmark.

IndianOil Paradip (Odisha): capacities as reported by Oil & Gas Journal,
"Indian Oil commissions Paradip refinery" (reported Nelson complexity: 10.6 by
CHT/OGJ 2025, 12.2 by IndianOil at commissioning; "15 million-tonne/year,
full-conversion refinery").  Three entries in that
report carry units that do not scale against a 15 mtpa refinery as printed
("105,000-tpy" VGO hydrotreater, "650-tpy" alkylation, "300-tpy"
isomerisation); they are read here as b/d, kt/yr and kt/yr respectively and
flagged, and the index is reported both with and without them.
"""
from __future__ import annotations

from .complexity import nelson_complexity

CDU_MTPA = 15.0
# CHT (MoPNG), citing the OGJ WW Refining & Complexity survey 2025 - the reference used for validation
REPORTED_NCI = 10.6
# IndianOil's own figure at commissioning (OGJ 2016) - superseded by the survey value above
IOC_COMMISSIONING_NCI = 12.2
_BPD_TO_MTPA = 0.159 * 0.84 * 365 / 1e6  # barrel/day of ~0.84 t/m3 gas oil -> Mt/yr

# published unambiguously (Mt/yr)
UNAMBIGUOUS = {"fcc": 4.2, "thermal": 4.1, "reforming": 2.9}
NAPHTHA_HT_MTPA = 3.9
DIESEL_HT_MTPA = 120_000 * _BPD_TO_MTPA     # "120,000 b/d"
# ambiguous units, read as noted in the module docstring
VGO_HT_MTPA = 105_000 * _BPD_TO_MTPA
ALKYLATION_MTPA, ISOMERISATION_MTPA, PARAXYLENE_MTPA = 0.65, 0.30, 1.2


def paradip_nci(factors: str = "1998", vdu_share: float = 1.0, with_ambiguous: bool = True) -> float:
    """Nelson index of Paradip from its published unit list.

    ``vdu_share`` is the vacuum unit's capacity as a fraction of the CDU
    (not published; 0.6-1.0 brackets a typical reduced-crude share).
    """
    units = dict(UNAMBIGUOUS)
    units["vacuum"] = vdu_share * CDU_MTPA
    units["hydrorefining"] = NAPHTHA_HT_MTPA + DIESEL_HT_MTPA + (VGO_HT_MTPA if with_ambiguous else 0.0)
    if with_ambiguous:
        units["alkylation"] = ALKYLATION_MTPA
        units["aromatics_isomerisation"] = ISOMERISATION_MTPA + PARAXYLENE_MTPA
    return nelson_complexity(CDU_MTPA, units, factors)


# --------------------------------------------------------------------
# Crude -> unit-loading consistency: what crude slate would load a 15 mtpa
# CDU with a 4.1 mtpa coker and a 4.2 mtpa FCC?
# --------------------------------------------------------------------
COKER_TO_CDU = 4.1 / CDU_MTPA   # 27.3%
FCC_TO_CDU = 4.2 / CDU_MTPA     # 28.0%


def paradip_blend_fit(medium_sour: str = "upper_zakum", heavy_sour: str = "cold_lake_blend") -> dict:
    """Fit ONE parameter - the heavy-crude fraction of a two-crude slate - so the
    vacuum-residue yield matches Paradip's coker/CDU ratio, then report the
    *independent* prediction of the VGO yield against Paradip's FCC/CDU ratio.

    Assumes the coker is fed by the vacuum residue and the FCC by the VGO
    (Paradip may also route other streams, so a match is a consistency check,
    not proof).  Ratios are mass-based; capacities are Mt/yr.
    """
    from scipy.optimize import brentq

    from .assay import INF, Slate, load_crude

    a, b = load_crude(medium_sour), load_crude(heavy_sour)

    def slate(x: float) -> Slate:
        return Slate([(a, 1 - x), (b, x)])

    x = brentq(lambda f: slate(f).cut(550, INF).wt_frac - COKER_TO_CDU, 0.0, 1.0)
    s = slate(x)
    return {"heavy_fraction_vol": x, "api": s.api, "sulfur_wt": s.sulfur_wt,
            "vr_wt_frac": s.cut(550, INF).wt_frac, "vgo_wt_frac": s.cut(370, 550).wt_frac,
            "coker_to_cdu": COKER_TO_CDU, "fcc_to_cdu": FCC_TO_CDU}


# --------------------------------------------------------------------
# PPAC-reported distillate yield of Paradip (Ready Reckoner Table 4.8), % - definition not stated
# --------------------------------------------------------------------
PARADIP_PPAC_DISTILLATE_PCT = {"2018-19": 80.8, "2019-20": 80.7, "2020-21": 79.2, "2021-22": 79.6, "2022-23": 79.5}


def paradip_model_refinery(vgo_hydrotreat: bool = True):
    """The fitted Paradip crude basket run through the flowsheet at 15 mtpa."""
    from .assay import Slate, load_crude
    from .flowsheet import RefineryConfig, refine

    fit = paradip_blend_fit()
    x = fit["heavy_fraction_vol"]
    slate = Slate([(load_crude("upper_zakum"), 1 - x), (load_crude("cold_lake_blend"), x)])
    bpd = CDU_MTPA * 1e9 / 8760.0 / slate.density_kg_m3 / 0.158987294928 * 24.0
    return refine(slate, bpd, RefineryConfig(vgo_hydrotreat=vgo_hydrotreat))
