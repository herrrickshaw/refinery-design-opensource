import pytest

from refinery_design import india
from refinery_design.assay import load_crude
from refinery_design.benchmarks import paradip_model_refinery
from refinery_design.flowsheet import RefineryConfig, refine
from refinery_design.grm import PriceDeck, calibrate_deck, gross_refining_margin

DECK = PriceDeck(crude_usd_bbl=80.0)


def test_grm_is_product_worth_minus_crude_minus_fuel_loss():
    r = refine(load_crude("upper_zakum"), 200_000)
    g = gross_refining_margin(r, DECK)
    assert g.grm_usd_bbl == pytest.approx(g.product_worth_usd_bbl - g.crude_cost_usd_bbl - g.fuel_loss_cost_usd_bbl)
    assert sum(g.worth_by_pool_usd_bbl.values()) == pytest.approx(g.product_worth_usd_bbl)
    assert g.extra_fuel_loss_pct == 4.4


def test_zero_cracks_lose_exactly_the_fuel_and_loss_and_the_petcoke_discount():
    """With every product priced at crude (no cracks) the only margin is the crude value of
    what is burned/lost, so GRM is negative - a sanity anchor for the accounting."""
    r = refine(load_crude("bakken"), 200_000)
    g0 = gross_refining_margin(r, DECK.scaled(0.0))
    assert g0.grm_usd_bbl < 0


def test_calibration_hits_the_target_exactly():
    r = paradip_model_refinery()
    for target in (11.25, 19.52):
        d = calibrate_deck(r, DECK, target)
        assert gross_refining_margin(r, d).grm_usd_bbl == pytest.approx(target, abs=1e-9)
    # a hotter margin environment needs bigger cracks
    assert calibrate_deck(r, DECK, 19.52).cracks_usd_bbl["middle_distillate"] > \
        calibrate_deck(r, DECK, 11.25).cracks_usd_bbl["middle_distillate"]


def test_unmodelled_fuel_loss_default_reconciles_with_ppac_for_the_paradip_configuration():
    """Paradip's PPAC fuel & loss (10.0%) = what the flowsheet models + the fixed overhead."""
    r = paradip_model_refinery()
    modelled = gross_refining_margin(r, DECK).modelled_fuel_loss_pct
    assert modelled + 4.4 == pytest.approx(india.paradip_fuel_loss_pct("2022-23"), abs=0.15)


def test_conversion_units_earn_margin_on_a_heavy_slate_when_light_cracks_are_positive():
    """The mechanism behind 'complexity earns margin': converting residue to light products."""
    heavy = load_crude("cold_lake_blend")
    full = refine(heavy, 200_000)
    no_coker = refine(heavy, 200_000, RefineryConfig(coker=False))
    skimming = refine(heavy, 200_000, RefineryConfig(fcc=False, coker=False))
    deck = DECK
    g = lambda r: gross_refining_margin(r, deck).grm_usd_bbl
    assert g(full) > g(no_coker) > g(skimming)


def test_price_deck_conversions():
    assert DECK.crude_usd_t() == pytest.approx(80.0 / (0.158987 * 0.87), rel=1e-3)
    assert DECK.product_usd_t("gasoline_range") > DECK.product_usd_t("vacuum_residue")
    assert DECK.product_usd_t("lpg") < DECK.product_usd_t("middle_distillate") + 100   # LPG is not richer per tonne than diesel
    assert DECK.product_usd_t("petcoke") == pytest.approx(0.25 * DECK.crude_usd_t())
    assert PriceDeck(80.0, petcoke_usd_t=200.0).product_usd_t("petcoke") == 200.0


def test_a_coker_only_pays_when_the_residue_discount_and_distillate_cracks_are_wide():
    """The other half of 'complexity earns margin': with a thin residue discount and small cracks the
    coker destroys value - consistent with PPAC's weak GRM-vs-NCI relationship."""
    heavy = load_crude("cold_lake_blend")
    full, no_coker = refine(heavy, 200_000), refine(heavy, 200_000, RefineryConfig(coker=False))
    thin = PriceDeck(80.0, cracks_usd_bbl={"gasoline_range": 4.0, "middle_distillate": 8.0})
    g = lambda r, d: gross_refining_margin(r, d).grm_usd_bbl
    wide = DECK
    assert g(full, wide) > g(no_coker, wide)
    assert g(full, thin) < g(no_coker, thin)
