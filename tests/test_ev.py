import math

from ev import american_to_decimal, implied_probability, ev_per_unit, edge

def test_american_to_decimal_positive_odds():
    assert american_to_decimal(150) == 2.5

def test_american_to_decimal_negative_odds():
    assert math.isclose(american_to_decimal(-120), 1.8333333333, rel_tol=1e-9)

def test_implied_probability_positive_odds():
    assert math.isclose(implied_probability(150), 0.4, rel_tol=1e-9)

def test_implied_probability_negative_odds():
    assert math.isclose(implied_probability(-120), 120 / 220, rel_tol=1e-9)

def test_ev_per_unit_positive_when_probability_beats_price():
    assert ev_per_unit(0.60, -120) > 0

def test_edge_matches_probability_minus_implied():
    assert math.isclose(edge(0.60, -120), 0.60 - implied_probability(-120), rel_tol=1e-9)
