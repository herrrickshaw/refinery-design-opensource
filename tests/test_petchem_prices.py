import pytest

from refinery_design import petchem_prices as pp


def test_iocl_price_points_are_the_ones_read_from_the_pdfs():
    assert pp.iocl_pp_inr_per_mt("homopolymer_injection_1110MG", "2026-09-11") == 154452
    assert pp.iocl_pp_inr_per_mt("homopolymer_injection_1110MG", "2026-01-01") == 90452
    assert pp.iocl_pp_inr_per_mt("raffia_1030RG", "2026-03-01") == 101502
    assert set(pp.GRADES) == {"homopolymer_injection_1110MG", "raffia_1030RG", "bopp_1030FG", "random_copolymer_2120MC"}


def test_price_moves_are_exchange_rate_neutral_and_2026_was_a_sharp_rise():
    assert pp.iocl_pp_change_pct() == pytest.approx(70.76, abs=0.05)                       # Jan -> Sep
    assert pp.iocl_pp_change_pct(d1="2026-03-01") == pytest.approx(10.50, abs=0.05)       # Jan -> Mar
    for g in pp.GRADES:
        a, b, c = (pp.iocl_pp_inr_per_mt(g, d) for d in ("2026-01-01", "2026-03-01", "2026-09-11"))
        assert a < b < c
    # specialty grades price above commodity grades at every date
    assert pp.iocl_pp_inr_per_mt("random_copolymer_2120MC") > pp.iocl_pp_inr_per_mt("homopolymer_injection_1110MG")


def test_deck_conversion_and_realisation():
    d = pp.iocl_deck()
    assert d.pp_usd_t == pytest.approx(154452 / pp.usd_inr())
    assert pp.usd_inr() == pytest.approx(95.82)
    assert d.pp_realised_usd_t == d.pp_usd_t
    d2 = pp.iocl_deck(fx=90.0, realisation=0.9)
    assert d2.pp_usd_t == pytest.approx(154452 / 90.0) and d2.pp_realised_usd_t == pytest.approx(0.9 * 154452 / 90.0)
    assert "GST extra" in d.notes[0]


def test_propylene_has_no_2026_09_observation_and_all_observations_are_low_confidence():
    obs = pp.propylene_observations()
    assert obs and all(o["confidence"] == "low" for o in obs)
    assert not any(o["date"].startswith("2026-09") for o in obs)
    assert pp.iocl_deck().propylene_usd_t is None                # never invented


def test_indian_basket_snapshot_uses_ppacs_formula():
    c = pp.crude_snapshot()
    assert pp.indian_basket_snapshot_usd_bbl() == pytest.approx(0.7562 * c["dubai"] + 0.2438 * c["brent"])
    assert 105 < pp.indian_basket_snapshot_usd_bbl() < 120
