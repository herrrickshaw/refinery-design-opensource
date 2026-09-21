"""Gross refining margin (GRM), the way PPAC reports it.

PPAC (citing EIA) defines GRM as the revenue from the sale of petroleum
products minus the cost of the raw materials used to produce them, per barrel
of crude.  This module values the flowsheet's product pools with a price deck
and deducts the fuel-and-loss the flowsheet does not model, so the result is
comparable to PPAC's company GRMs (Ready Reckoner Table 4.7).

**Prices are inputs, not data.**  Product prices are set as *cracks* (product
$/bbl minus crude $/bbl) from a deck whose default pattern is illustrative and
*unsourced*; only the crude price can come from a live feed.  The honest way to
use it is :func:`calibrate_deck`: scale the cracks so a reference configuration
reproduces a PPAC-reported GRM, then study *differences* between configurations.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .flowsheet import RefineryResult
from .properties import BBL_M3

# product-pool densities (kg/m3) used only to convert cracks ($/bbl) to $/t
POOL_DENSITY = {"lpg": 550.0, "gasoline_range": 730.0, "middle_distillate": 850.0,
                "slurry": 1040.0, "vacuum_residue": 1030.0, "vgo_unconverted": 930.0}
SALEABLE = ("lpg", "gasoline_range", "middle_distillate", "slurry", "vacuum_residue", "vgo_unconverted", "petcoke")
# Illustrative and UNSOURCED - calibrate before use.  Light-product cracks ($/bbl of product minus
# crude) are what calibration scales; LPG and residue/slurry are priced as a fraction of crude value
# per barrel (LPG is worth far less per barrel than per tonne; residue trades at a discount to crude).
DEFAULT_CRACKS_USD_BBL = {"gasoline_range": 12.0, "middle_distillate": 20.0}
DEFAULT_FRAC_OF_CRUDE_PER_BBL = {"lpg": 0.70, "slurry": 0.75, "vacuum_residue": 0.75, "vgo_unconverted": 0.85}
DEFAULT_PETCOKE_FRAC_OF_CRUDE_USD_T = 0.25   # petcoke $/t as a fraction of crude $/t - illustrative


@dataclass(frozen=True)
class PriceDeck:
    crude_usd_bbl: float
    cracks_usd_bbl: dict = field(default_factory=lambda: dict(DEFAULT_CRACKS_USD_BBL))
    petcoke_usd_t: float | None = None
    crude_density_kg_m3: float = 870.0
    label: str = "illustrative"

    def crude_usd_t(self) -> float:
        return self.crude_usd_bbl / (BBL_M3 * self.crude_density_kg_m3 / 1000.0)

    def product_usd_t(self, pool: str) -> float:
        if pool == "petcoke":
            return self.petcoke_usd_t if self.petcoke_usd_t is not None else \
                DEFAULT_PETCOKE_FRAC_OF_CRUDE_USD_T * self.crude_usd_t()
        rho = POOL_DENSITY[pool]
        usd_bbl = (self.crude_usd_bbl + self.cracks_usd_bbl[pool] if pool in self.cracks_usd_bbl
                   else DEFAULT_FRAC_OF_CRUDE_PER_BBL[pool] * self.crude_usd_bbl)
        return usd_bbl / (BBL_M3 * rho / 1000.0)

    def scaled(self, s: float) -> "PriceDeck":
        """Scale the light-product cracks (the quantity calibration adjusts)."""
        return replace(self, cracks_usd_bbl={k: v * s for k, v in self.cracks_usd_bbl.items()})


@dataclass(frozen=True)
class GrmResult:
    grm_usd_bbl: float
    product_worth_usd_bbl: float
    crude_cost_usd_bbl: float
    modelled_fuel_loss_pct: float
    extra_fuel_loss_pct: float
    fuel_loss_cost_usd_bbl: float
    worth_by_pool_usd_bbl: dict


# Fuel burned in heaters, utilities and the hydrogen plant, plus losses, that the flowsheet does not model.
# PPAC reports Paradip's total fuel & loss at 10.0% of throughput (FY2022-23); the flowsheet already
# models 5.6% of it (fuel gas + FCC coke) for the Paradip-like configuration, leaving 4.4%.  Applied to
# every configuration as a fixed overhead, so differences between configurations come only from modelled fuel.
UNMODELLED_FUEL_LOSS_PCT = 4.4


def gross_refining_margin(result: RefineryResult, deck: PriceDeck,
                          unmodelled_fuel_loss_pct: float = UNMODELLED_FUEL_LOSS_PCT) -> GrmResult:
    """GRM ($/bbl of crude) for a flowsheet result.

    Saleable pools are valued with the deck; fuel gas and FCC coke burned are consumed (charged
    implicitly, their crude is in the cost); ``unmodelled_fuel_loss_pct`` of crude is charged at the
    crude price to stand for the fuel and losses PPAC's total (Paradip 10.0%, PSU average 8.9%)
    includes beyond what the flowsheet models.
    """
    pools = result.pools_wt_pct()
    modelled = pools["fuel_gas"] + pools["fcc_coke_burned"]
    crude_kg_bbl = result.feed_kg_h / (result.throughput_bpd / 24.0)   # kg per barrel of crude
    worth = {}
    for pool in SALEABLE:
        kg_per_bbl = pools[pool] / 100.0 * crude_kg_bbl
        worth[pool] = kg_per_bbl / 1000.0 * deck.product_usd_t(pool)
    product_worth = sum(worth.values())
    fuel_cost = unmodelled_fuel_loss_pct / 100.0 * crude_kg_bbl / 1000.0 * deck.crude_usd_t()
    return GrmResult(grm_usd_bbl=product_worth - deck.crude_usd_bbl - fuel_cost, product_worth_usd_bbl=product_worth,
                     crude_cost_usd_bbl=deck.crude_usd_bbl, modelled_fuel_loss_pct=modelled,
                     extra_fuel_loss_pct=unmodelled_fuel_loss_pct, fuel_loss_cost_usd_bbl=fuel_cost,
                     worth_by_pool_usd_bbl=worth)


def calibrate_deck(result: RefineryResult, deck: PriceDeck, target_grm_usd_bbl: float,
                   unmodelled_fuel_loss_pct: float = UNMODELLED_FUEL_LOSS_PCT) -> PriceDeck:
    """Scale the deck's light-product cracks so ``result`` earns exactly ``target_grm_usd_bbl``.

    GRM is linear in the crack scale, so this is exact.  It fixes the *level* of
    the deck to a reported GRM (e.g. PPAC's IOCL 11.25 $/bbl for FY2021-22); the
    *relative* crack pattern remains an assumption.
    """
    g0 = gross_refining_margin(result, deck.scaled(0.0), unmodelled_fuel_loss_pct).grm_usd_bbl
    g1 = gross_refining_margin(result, deck.scaled(1.0), unmodelled_fuel_loss_pct).grm_usd_bbl
    if abs(g1 - g0) < 1e-9:
        raise ValueError("GRM does not respond to the cracks for this configuration")
    s = (target_grm_usd_bbl - g0) / (g1 - g0)
    return replace(deck.scaled(s), label=f"calibrated to {target_grm_usd_bbl:.2f} $/bbl")
