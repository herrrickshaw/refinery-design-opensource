from dataclasses import replace

import pytest

from refinery_design import petchem_prices as pp
from refinery_design import trade
from refinery_design.assay import load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.flowsheet import RefineryConfig, refine
from refinery_design.routes import displaced_by_blend_step, petrol_switch_options

R = paradip_model_refinery(True)
DECK = trade.RebasedTradeDeck("2025-26", pp.crude_snapshot()["brent"])
PRICES = pp.iocl_deck()
ROWS = {r.name: r for r in petrol_switch_options(R, DECK, PRICES, pe_usd_t=pp.iocl_pe_usd_t())}


def test_blend_step_displacement_is_a_tenth_of_the_gasoline_pool():
    pool_kt = R.pools_kg_h["gasoline_range"] * 8400.0 / 1e6
    d = displaced_by_blend_step(R, 42.6)
    assert d == pytest.approx(pool_kt * 0.0945, rel=0.02)
    assert displaced_by_blend_step(R, 42.6, 0.12, 0.27) > d > displaced_by_blend_step(R, 42.6, 0.12, 0.15)


def test_baseline_and_row_structure():
    base = ROWS["export the surplus petrol (baseline)"]
    assert base.gasoline_removed_kt_y == 0.0 and base.net_usd_m_y == 0.0
    assert {"FCC distillate: sell LPG/LCO", "FCC propylene + PP unit", "naphtha steam cracker -> PE + PP"} <= set(ROWS)


def test_selling_the_extra_lpg_or_lco_as_fuel_loses_against_gasoline_at_these_prices():
    for k in ("FCC distillate: sell LPG/LCO", "FCC lpg_zsm5: sell LPG/LCO", "FCC high_severity: sell LPG/LCO", "FCC propylene: sell LPG/LCO"):
        assert ROWS[k].fuel_margin_usd_m_y < 0, k


def test_only_the_polypropylene_routes_pay_and_bigger_shifts_pay_more():
    z, h, p = (ROWS[f"FCC {m} + PP unit"] for m in ("lpg_zsm5", "high_severity", "propylene"))
    assert 0 < z.net_usd_m_y < h.net_usd_m_y < p.net_usd_m_y
    assert z.gasoline_removed_kt_y < h.gasoline_removed_kt_y < p.gasoline_removed_kt_y
    assert all(r.capital_charge_usd_m_y > 0 for r in (z, h, p))


def test_propylene_mode_covers_the_e20_displacement_but_zsm5_alone_does_not():
    need = displaced_by_blend_step(R, 42.6)
    assert ROWS["FCC propylene + PP unit"].gasoline_removed_kt_y > need > ROWS["FCC lpg_zsm5 + PP unit"].gasoline_removed_kt_y
    assert ROWS["FCC distillate: sell LPG/LCO"].gasoline_removed_kt_y < need


def test_gas_plant_ratios_are_attached_and_distillate_mode_unloads_it():
    assert ROWS["FCC distillate: sell LPG/LCO"].wgfr_ratio < 1.0
    assert 1.0 < ROWS["FCC lpg_zsm5 + PP unit"].wgfr_ratio < ROWS["FCC propylene + PP unit"].wgfr_ratio
    assert "beyond" in ROWS["FCC propylene: sell LPG/LCO"].note


def test_cracker_row_does_not_pay_and_removes_the_whole_naphtha_cut():
    c = ROWS["naphtha steam cracker -> PE + PP"]
    assert c.net_usd_m_y < 0 and c.gasoline_removed_kt_y == pytest.approx(R.distillation.stream("naphtha").mass_kg_h * 8400 / 1e6, rel=1e-6)
    assert "sub-scale" in c.note


def test_realisation_erodes_the_pp_routes_first():
    low = {r.name: r for r in petrol_switch_options(R, DECK, replace(PRICES, realisation=0.8), pe_usd_t=pp.iocl_pe_usd_t())}
    for m in ("lpg_zsm5", "high_severity", "propylene"):
        k = f"FCC {m} + PP unit"
        assert low[k].net_usd_m_y < ROWS[k].net_usd_m_y


def test_no_fcc_is_rejected():
    with pytest.raises(ValueError, match="no FCC"):
        petrol_switch_options(refine(load_crude("bakken"), 100_000, RefineryConfig(fcc=False)), DECK, PRICES)
