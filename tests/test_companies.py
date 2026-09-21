"""Indian refiners submodule: data integrity, ties to company-reported totals, and the rules that stop misleading comparisons."""
import json

import pytest

from refinery_design import companies as co
from refinery_design.companies import core

RAW = json.loads(core.DATA_FILE.read_text())


def test_every_refinery_id_is_unique_and_named_company_slash_name():
    ids = [r["id"] for r in co.refineries()]
    assert len(ids) == len(set(ids)) == 24
    assert all(r["id"] == f"{r['company']}/{r['name']}" for r in co.refineries())


def test_every_value_carries_a_source_and_only_known_years():
    for r in co.refineries():
        for field in ("capacity_mmtpa", "throughput_mmt", "distillate_yield_pct", "grm_usd_bbl", "utilisation_reported_pct"):
            for fy, e in r[field].items():
                # CHT's distillate-yield series starts a year before the window (FY2014-15); nothing else may
                assert fy in co.years() or (field == "distillate_yield_pct" and fy == "2014-15"), (r["id"], field, fy)
                assert e["source"], (r["id"], field, fy)
                assert isinstance(e["value"], (int, float)) and e["value"] >= 0 or field == "grm_usd_bbl", (r["id"], field, fy)


def test_fcc_records_and_events_refer_to_known_refineries():
    ids = {r["id"] for r in co.refineries()}
    assert {u["refinery"] for u in co.fcc_units()} <= ids
    assert {e["refinery"] for e in co.fcc_changes()} <= ids


def test_refinery_throughputs_tie_to_company_reported_totals():
    # IOCL: PPAC refinery-wise sum vs the company's reported total (differences are PPAC rounding)
    for fy, reported in (("2022-23", 72.41), ("2024-25", 71.56), ("2025-26", 75.5)):
        assert co.company_rollup("IOCL", fy)["throughput_mmt"] == pytest.approx(reported, abs=0.5)
    # Reliance: DTA + SEZ equals the company total crude processed
    for fy in ("2019-20", "2025-26"):
        assert co.company_rollup("Reliance", fy)["throughput_mmt"] == pytest.approx(co.company_series("Reliance")["throughput_mmt"][fy]["value"], abs=0.01)
    # BPCL FY2025-26: the three refineries against the 41.15 MMT reported on the Q4 FY26 call
    assert co.company_rollup("BPCL", "2025-26")["throughput_mmt"] == pytest.approx(41.15, abs=0.5)


def test_utilisation_is_throughput_over_capacity_and_none_when_missing():
    assert co.utilisation_pct("IOCL/Panipat", "2025-26") == pytest.approx(100 * co.throughput("IOCL/Panipat", "2025-26") / 15.0)
    assert co.utilisation_pct("CPCL/Cauvery Basin (Nagapattinam)", "2025-26") is None
    assert co.utilisation_pct("HRRL/Barmer", "2025-26") is None  # capacity not in the series


def test_over_125_pct_is_flagged_as_a_stale_capacity_basis():
    u = co.utilisation_pct("Reliance/Jamnagar SEZ", "2015-16")
    assert u > 125
    assert "not confirmed" in co.utilisation_flag(u, "Reliance/Jamnagar SEZ", "2015-16")
    assert co.is_unconfirmed_overrun("Reliance/Jamnagar SEZ", "2015-16")
    assert co.utilisation_flag(co.utilisation_pct("IOCL/Panipat", "2025-26")) is None
    assert co.utilisation_flag(None) is None


def test_a_real_overrun_is_confirmed_by_the_company_reported_figure():
    # BPCL Mumbai FY2024-25: derived 129.8% equals the annual report's 129.8% - not a stale capacity
    f = co.utilisation_flag(co.utilisation_pct("BPCL/Mumbai", "2024-25"), "BPCL/Mumbai", "2024-25")
    assert "confirmed" in f and "not confirmed" not in f
    assert not co.is_unconfirmed_overrun("BPCL/Mumbai", "2024-25")


def test_capacity_is_inferred_only_where_the_2020_and_2026_values_match():
    assert co.capacity_inferred("Nayara/Vadinar", "2023-24") and co.capacity("Nayara/Vadinar", "2023-24") == 20.0
    assert not co.capacity_inferred("Nayara/Vadinar", "2015-16")
    # Cauvery Basin: 1.0 in 2020, 0 in 2026 -> nothing may be carried forward
    assert co.capacity("CPCL/Cauvery Basin (Nagapattinam)", "2023-24") is None
    # IOCL/BPCL/HPCL capacity comes from PPAC's yearly table, never inferred
    assert not any(co.capacity_inferred(r["id"], fy) for r in co.refineries("IOCL") + co.refineries("BPCL") for fy in co.years())


def test_then_vs_now_capacity_change_and_the_commissioning_guard():
    v = co.then_vs_now("HPCL/Visakh")
    assert (v["capacity_then"], v["capacity_now"], v["capacity_change_pct"]) == (8.3, 15.0, 80.7)
    p = co.then_vs_now("IOCL/Paradip")  # commissioned 2016: 2015-16 is pre-commissioning
    assert p["throughput_change_pct"] is None and "commissioned 2016" in p["note"]
    assert co.then_vs_now("IOCL/Panipat")["note"] == ""


def test_then_vs_now_lists_fcc_events_in_the_window():
    kochi = co.then_vs_now("BPCL/Kochi")
    assert kochi["fcc_events"] == []                       # nothing dated inside 2015-16..2025-26
    assert [e["year"] for e in kochi["fcc_events_after"]] == [2027]   # the PFCC revamp is expected after "now"
    assert {e["year"] for e in co.then_vs_now("CPCL/Manali", then="2021-22")["fcc_events"]} <= set(range(2021, 2028))


def test_bina_takes_the_bpcl_file_as_primary_and_has_no_fcc():
    r = co.refinery("BPCL/Bina")
    assert not any("others file" in e["source"] for fy, e in r["throughput_mmt"].items() if fy >= "2022-23")
    assert [u["kind"] for u in r["fcc_units"]] == [None]
    assert "ETHYLENE cracker" in " ".join(co.bpcl.CAVEATS)


def test_fcc_summary_excludes_revamps_and_sums_known_capacity_only():
    s = co.fcc_summary()
    assert s["INDMAX"]["operating"]["capacity_known_mmtpa"] == pytest.approx(4.27 + 0.74 + 0.1)
    assert s["INDMAX"]["coming"]["units"] == 3 and s["INDMAX"]["coming"]["capacity_unknown"] == 1
    assert s["PFCC"]["coming"]["units"] == 2  # HRRL and NRL; Kochi's PFCC revamp is not a new unit
    assert sum(1 for u in co.fcc_units() if u.get("change") == "revamp") == 1
    # Capacities are lower bounds: many conventional FCCs have no published nameplate
    assert s["FCC"]["operating"]["capacity_unknown"] >= 8


def test_company_series_and_plans():
    assert co.company_series("IOCL")["throughput_mmt"]["2025-26"]["value"] == 75.5
    assert "2025-26" not in co.company_series("IOCL")["grm_usd_bbl"]  # IOCL stopped publishing GRM for FY2025-26
    assert any("Panipat" in p["project"] for p in co.plans("IOCL"))
    assert co.plans("NRL") and all("NRL" in p["company"] for p in co.plans("NRL"))
    assert {p["company"] for p in co.plans("BPCL")} >= {"BPCL", "BPCL Bina"}


def test_disagreeing_sources_are_kept_not_averaged():
    alts = [a for r in co.refineries() for fy in r["throughput_mmt"] for a in co.alternatives(r["id"], "throughput_mmt", fy)]
    assert alts, "expected at least one year where two sources disagree"
    assert all("value" in a and "source" in a for a in alts)


def test_every_company_module_has_caveats_and_a_rollup():
    for name, m in co.MODULES.items():
        assert m.CAVEATS and all(len(c) > 40 for c in m.CAVEATS), name
        assert m.refineries(), name
    assert co.iocl.summary()["complete"] and co.reliance.summary()["refineries_total"] == 2
    assert {r["company"] for r in co.others.refineries()} == set(co.others.NAMES)


def test_utilisation_table_rows():
    rows = co.utilisation_table("Nayara")
    assert [r["fy"] for r in rows] == co.years()
    assert all(r["utilisation_pct"] is not None for r in rows)
    assert min(r["throughput_mmt"] for r in rows) == pytest.approx(17.067)


def test_gaps_and_sources_are_recorded():
    assert set(co.gaps()) == {"iocl", "bpcl_hpcl", "others"} == set(co.sources())
    assert any("FCC" in g for g in co.gaps()["others"])


def test_rollup_carries_the_stale_capacity_flag():
    assert co.company_rollup("Reliance", "2015-16")["flagged"] == ["Reliance/Jamnagar SEZ"]
    assert co.company_rollup("Reliance", "2025-26")["flagged"] == []
    assert co.company_rollup("BPCL", "2024-25")["flagged"] == []   # 129.8% at Mumbai is confirmed by BPCL's own figure
    assert co.company_rollup("IOCL", "2025-26")["flagged"] == []


def test_derived_utilisation_matches_company_reported_figures():
    """Validation of the derivation: throughput / 1-April capacity against every company-reported utilisation in the data (21 pairs).
    Twenty agree within 1.5 points.  The exception is Visakh FY2023-24 (derived 115%, reported 105%): its capacity stepped from 8.3 to
    11.0 to 13.7 MMTPA around then, so a company figure measured against capacity commissioned during the year would differ.  That
    reason is inferred, not verified."""
    diffs = {}
    for r in co.refineries():
        for fy, e in r["utilisation_reported_pct"].items():
            d = co.utilisation_pct(r["id"], fy)
            if d is not None:
                diffs[(r["id"], fy)] = d - e["value"]
    assert len(diffs) >= 20
    outliers = {k for k, v in diffs.items() if abs(v) > 1.5}
    assert outliers == {("HPCL/Visakh", "2023-24")}
    assert sum(abs(v) for k, v in diffs.items() if k not in outliers) / (len(diffs) - len(outliers)) < 0.5
