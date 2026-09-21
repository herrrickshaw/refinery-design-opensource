"""Indian refiners by company: capacities, production runs, FCC units and announced plans.  See :mod:`refinery_design.companies.core`.

Per-company modules (``iocl``, ``bpcl``, ``hpcl``, ``reliance``, ``nayara``, ``others``) carry that company's caveats and a
``summary()``; the analytics live in ``core`` and are re-exported here.
"""
from . import bpcl, hpcl, iocl, nayara, others, reliance
from .core import (alternatives, capacity, capacity_inferred, companies, company_rollup, company_series, distillate_yield_pct,
                   fcc_changes, fcc_summary, fcc_units, gaps, plans, refineries, refinery, sources, then_vs_now, throughput,
                   is_unconfirmed_overrun, utilisation_flag, utilisation_pct, utilisation_table, years)

MODULES = {"IOCL": iocl, "BPCL": bpcl, "HPCL": hpcl, "Reliance": reliance, "Nayara": nayara, "Others": others}

__all__ = ["MODULES", "alternatives", "capacity", "capacity_inferred", "companies", "company_rollup", "company_series",
           "distillate_yield_pct", "fcc_changes", "fcc_summary", "fcc_units", "gaps", "plans", "refineries", "refinery",
           "sources", "then_vs_now", "throughput", "is_unconfirmed_overrun", "utilisation_flag", "utilisation_pct", "utilisation_table", "years",
           "bpcl", "hpcl", "iocl", "nayara", "others", "reliance"]
