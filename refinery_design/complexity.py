"""Nelson complexity index.

NCI = sum_i F_i * (C_i / C_CDU): each unit's feed capacity relative to
crude-distillation capacity, weighted by a cost-based factor.  The factor
table below is the one tabulated on Wikipedia's "Nelson complexity index"
page (checked against it while building this repo); it gives two vintages
that differ for thermal processes (coking/visbreaking) and lubricants.
Other published tables also differ on hydrotreating (2.0 vs 3.0) and
coking (5.5-6.0), so treat the index as approximate to ~10% between
sources - `docs/VALIDATION.md` shows this on a real refinery.
"""
from __future__ import annotations

NELSON_FACTORS = {
    "1998": {
        "cdu": 1.0, "asphalt": 1.5, "vacuum": 2.0, "thermal": 2.75, "hydrorefining": 3.0,
        "reforming": 5.0, "fcc": 6.0, "hydrocracking": 6.0, "alkylation": 10.0,
        "oxygenates": 10.0, "aromatics_isomerisation": 15.0, "lubes": 60.0,
    },
    "older": {
        "cdu": 1.0, "asphalt": 1.5, "vacuum": 2.0, "thermal": 5.0, "hydrorefining": 3.0,
        "reforming": 5.0, "fcc": 6.0, "hydrocracking": 6.0, "alkylation": 10.0,
        "oxygenates": 10.0, "aromatics_isomerisation": 15.0, "lubes": 10.0,
    },
}


def nelson_complexity(cdu_capacity: float, units: dict[str, float], factors: str = "1998") -> float:
    """Nelson complexity index.  ``units`` maps unit name -> feed capacity in the
    same units as ``cdu_capacity`` (the ``cdu`` entry itself is implied)."""
    table = NELSON_FACTORS[factors]
    total = table["cdu"]
    for name, cap in units.items():
        if name == "cdu":
            continue
        if name not in table:
            raise KeyError(f"unknown unit {name!r}; known: {', '.join(table)}")
        total += table[name] * cap / cdu_capacity
    return total
