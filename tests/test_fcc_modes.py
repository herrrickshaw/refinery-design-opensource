import pytest

from refinery_design import fcc_modes as fm
from refinery_design import petrochemical as pc
from refinery_design.fcc import FccFeed, FccOperation

REF = FccFeed("ref VGO", density_kg_m3=928.7, mabp_C=460.0, sulfur_wt=0.5, ccr_wt=0.3)
OP = FccOperation(feed_rate_kg_s=100.0)
M = {m.name: m for m in fm.modes(REF, OP)}


def test_paper_slopes_from_figures_8_to_11():
    assert fm.PCS_WGFR_PCT_PER_WT_PROPYLENE == pytest.approx(5.07, abs=0.05)       # 34.5k -> 44.3k ICFM over 5.6 wt%
    assert fm.PCS_WGFR_PCT_PER_F_RECEIVER == pytest.approx(0.83, abs=0.02)         # 130 -> 115 F
    assert fm.PCS_RULE_OF_THUMB_PCT_PER_F == 1.0
    assert [p for p, _ in fm.PCS_RECEIVER_PRESSURE_RATIO] == [3.5, 6.5, 9.5]
    assert fm.PCS_RECEIVER_PRESSURE_RATIO[1][1] == pytest.approx(0.8126, abs=1e-3)


def test_mode_ordering_of_gasoline_and_lpg():
    order = ["gasoline", "distillate", "lpg_zsm5", "high_severity", "propylene"]
    assert list(M) == order
    g = [M[n].yields_wt_pct["gasoline"] for n in order]
    assert g == sorted(g, reverse=True)
    assert M["gasoline"].gasoline_change_t_y == 0.0
    assert M["distillate"].lco_change_t_y > 0 > M["distillate"].gasoline_change_t_y
    assert M["lpg_zsm5"].lpg_change_t_y > 0 and M["propylene"].lpg_change_t_y > M["high_severity"].lpg_change_t_y > M["lpg_zsm5"].lpg_change_t_y


def test_every_mode_conserves_mass():
    for m in M.values():
        assert sum(m.yields_wt_pct.values()) == pytest.approx(100.0, abs=1e-6), m.name


def test_propylene_targets_come_from_the_literature_and_paradip():
    assert M["gasoline"].propylene_wt_pct == pytest.approx(6.0, abs=0.05)
    assert M["lpg_zsm5"].propylene_wt_pct == pytest.approx(9.0, abs=0.1)
    assert M["propylene"].propylene_wt_pct == pytest.approx(pc.PARADIP_IMPLIED_PROPYLENE_WT)


def test_gas_plant_load_grows_with_lpg_and_falls_in_distillate_mode():
    r = {n: M[n].gas_plant.wgfr_ratio for n in M}
    assert r["gasoline"] == 1.0 and r["distillate"] < 1.0
    assert 1.0 < r["lpg_zsm5"] < r["high_severity"] < r["propylene"]
    # ZSM-5: +3 wt% propylene = +15% at the paper's 5.1%/wt% slope
    assert r["lpg_zsm5"] == pytest.approx(1.0 + 3.0 * fm.PCS_WGFR_PCT_PER_WT_PROPYLENE / 100.0, abs=0.01)


def test_mitigation_reads_back_from_the_paper_curves():
    c = fm.gas_plant_check(1.15)
    assert c.receiver_temp_drop_F == pytest.approx((1 - 1 / 1.15) / 0.0083, abs=1.0)        # ~16 F
    assert 3.5 < c.receiver_pressure_needed_psig < 9.5 and c.within_paper_range
    # exactly the Figure 9 point: 44,300 -> 36,000 ICFM needs 6.5 psig
    assert fm.gas_plant_check(44_300.0 / 36_000.0).receiver_pressure_needed_psig == pytest.approx(6.5, abs=0.05)
    none = fm.gas_plant_check(0.9)
    assert none.receiver_temp_drop_F is None and none.receiver_pressure_needed_psig is None
    beyond = fm.gas_plant_check(1.7)
    assert not beyond.within_paper_range and beyond.receiver_pressure_needed_psig is None
    assert any("compressor" in n for n in beyond.notes) and any("98%" in n for n in beyond.notes)


def test_dry_gas_term_is_a_flagged_extrapolation_but_directionally_right():
    base = {"dry_gas": 3.6, "lpg": 17.8}
    hotter = {"dry_gas": 5.6, "lpg": 17.8}
    assert fm.wgfr_ratio(base, hotter) > 1.0
    assert fm.wgfr_ratio(base, base) == 1.0
