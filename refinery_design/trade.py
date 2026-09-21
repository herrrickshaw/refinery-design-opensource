"""PPAC trade, consumption and production data, and the prices they imply.

Source: PPAC *Ready Reckoner FY 2025-26* (Tables 4.5, 4.11, 6.1; see ``scripts/build_ppac_2526_data.py``).
Quantities are MMT, values US$ billion, both rounded by PPAC (quantities to 0.1 MMT), so unit values
of small flows (< ~1 MMT) are unreliable and are refused.

Two uses:

* :class:`TradeDeck` - a price deck of *observed* product prices (trade unit values, $/t) that plugs
  straight into :func:`refinery_design.grm.gross_refining_margin`, replacing the illustrative cracks.
* :func:`trade_implied_cracks` - the product cracks those prices imply, an independent check on the
  cracks calibrated from reported GRMs.

Definitions (state them, do not hide them): export unit values are FOB-like realised prices of
what India actually shipped (a product mix, not a benchmark); import unit values are landed
prices. LPG is priced at the *import* unit value (India is a marginal LPG importer); petrol and diesel
at *export* unit values (India is a marginal exporter); fuel oil and petcoke at import unit values.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .properties import BBL_M3

DATA_FILE = Path(__file__).parent / "data" / "ppac_2526.json"
MIN_QTY_MMT = 1.0


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_FILE.read_text())


def years() -> list[str]:
    return list(_raw()["years"])


def trade_qty_mmt(side: str, product: str, year: str) -> float:
    """``side`` is ``"imports"`` or ``"exports"``."""
    return float(_raw()["trade_usd_bn_and_mmt"][side][product][year][0])


def trade_value_usd_bn(side: str, product: str, year: str) -> float:
    return float(_raw()["trade_usd_bn_and_mmt"][side][product][year][1])


def unit_value_usd_t(side: str, product: str, year: str) -> float:
    """Realised $/t = value / quantity (PPAC-rounded; small flows are refused)."""
    q = trade_qty_mmt(side, product, year)
    if q < MIN_QTY_MMT:
        raise ValueError(f"{product} {side} {year}: {q} MMT is too small for a reliable unit value (PPAC rounds to 0.1 MMT)")
    return trade_value_usd_bn(side, product, year) * 1000.0 / q


def consumption_mmt(product: str, year: str) -> float:
    r = _raw()
    return float(r["consumption_mmt"][product][r["consumption_years"].index(year)])


def production_mmt(product: str, year: str) -> float:
    p = _raw()["production_mmt"]
    return float(p[product][p["years"].index(year)])


def import_dependence_pct(product: str, year: str) -> float:
    """Imports as a share of domestic consumption (only meaningful for products traded both ways in bulk)."""
    return 100.0 * trade_qty_mmt("imports", product, year) / consumption_mmt(product, year)


def net_export_mmt(product: str, year: str) -> float:
    return trade_qty_mmt("exports", product, year) - trade_qty_mmt("imports", product, year)


def petrol_balance(year: str) -> dict:
    """MS supply/demand from PPAC.  PPAC's MS consumption is *blended* petrol, so it exceeds
    production + imports - exports by roughly the ethanol blended: the gap is the implied ethanol."""
    prod = production_mmt("ms", year)
    imp, exp = trade_qty_mmt("imports", "petrol", year), trade_qty_mmt("exports", "petrol", year)
    cons = consumption_mmt("ms", year)
    domestic_petrol = prod + imp - exp
    return {"production": prod, "imports": imp, "exports": exp, "consumption": cons,
            "domestic_refinery_petrol": domestic_petrol, "implied_ethanol_mmt": cons - domestic_petrol,
            "implied_ethanol_share_pct": 100.0 * (cons - domestic_petrol) / cons}


def crude_usd_bbl(year: str, density_kg_m3: float = 870.0) -> float:
    return unit_value_usd_t("imports", "crude", year) * BBL_M3 * density_kg_m3 / 1000.0


def _usd_bbl(usd_t: float, density: float) -> float:
    return usd_t * BBL_M3 * density / 1000.0


def trade_implied_cracks(year: str, petrol_density: float = 745.0, diesel_density: float = 850.0,
                         naphtha_density: float = 720.0, lpg_density: float = 550.0, fo_density: float = 980.0) -> dict:
    """Cracks ($/bbl, product minus crude) and price fractions implied by PPAC's trade unit values."""
    c = crude_usd_bbl(year)
    g = _usd_bbl(unit_value_usd_t("exports", "petrol", year), petrol_density)
    d = _usd_bbl(unit_value_usd_t("exports", "diesel", year), diesel_density)
    n = _usd_bbl(unit_value_usd_t("exports", "naphtha", year), naphtha_density)
    lpg = _usd_bbl(unit_value_usd_t("imports", "lpg", year), lpg_density)
    fo = _usd_bbl(unit_value_usd_t("imports", "fuel_oil", year), fo_density)
    return {"crude_usd_bbl": c, "gasoline_crack": g - c, "diesel_crack": d - c, "naphtha_crack": n - c,
            "lpg_frac_of_crude": lpg / c, "fuel_oil_frac_of_crude": fo / c}


class TradeDeck:
    """Observed-price deck from PPAC trade unit values, duck-typed as a ``grm.PriceDeck``."""

    def __init__(self, year: str, crude_density_kg_m3: float = 870.0):
        self.year = year
        self.crude_density_kg_m3 = crude_density_kg_m3
        self.crude_usd_bbl = crude_usd_bbl(year, crude_density_kg_m3)
        self.label = f"PPAC trade unit values FY{year}"
        fo = unit_value_usd_t("imports", "fuel_oil", year)
        self._usd_t = {
            "lpg": unit_value_usd_t("imports", "lpg", year),
            "gasoline_range": unit_value_usd_t("exports", "petrol", year),
            "middle_distillate": unit_value_usd_t("exports", "diesel", year),
            "slurry": fo, "vacuum_residue": fo, "vgo_unconverted": fo,
            "petcoke": unit_value_usd_t("imports", "petcoke", year),
            "naphtha": unit_value_usd_t("exports", "naphtha", year),
        }

    def crude_usd_t(self) -> float:
        return unit_value_usd_t("imports", "crude", self.year)

    def product_usd_t(self, pool: str) -> float:
        return self._usd_t[pool]


class RebasedTradeDeck(TradeDeck):
    """PPAC-observed cracks and price fractions (a fiscal year) re-based to a different crude price.

    Gasoline, diesel and naphtha trade at crude plus the trade-implied crack; LPG and fuel oil at the
    trade-implied fraction of crude; petcoke stays at its observed unit value.  Use it to ask "what would that
    year's margin structure look like at today's crude?" - an assumption that cracks do not move with crude.
    """

    def __init__(self, year: str, crude_usd_bbl_new: float, crude_density_kg_m3: float = 870.0):
        super().__init__(year, crude_density_kg_m3)
        k = trade_implied_cracks(year)
        per_t = lambda usd_bbl, rho: usd_bbl / (BBL_M3 * rho / 1000.0)
        self.crude_usd_bbl = crude_usd_bbl_new
        self.label = f"PPAC FY{year} cracks at crude ${crude_usd_bbl_new:.1f}/bbl"
        c = crude_usd_bbl_new
        self._usd_t.update({
            "gasoline_range": per_t(c + k["gasoline_crack"], 745.0),
            "middle_distillate": per_t(c + k["diesel_crack"], 850.0),
            "naphtha": per_t(c + k["naphtha_crack"], 720.0),
            "lpg": per_t(k["lpg_frac_of_crude"] * c, 550.0),
            "slurry": per_t(k["fuel_oil_frac_of_crude"] * c, 980.0),
            "vacuum_residue": per_t(k["fuel_oil_frac_of_crude"] * c, 980.0),
            "vgo_unconverted": per_t(k["fuel_oil_frac_of_crude"] * c, 980.0),
        })
        self._crude_usd_t = per_t(c, crude_density_kg_m3)

    def crude_usd_t(self) -> float:
        return self._crude_usd_t
