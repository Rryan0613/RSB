import math

from odds_providers import MockOddsProvider
from odds_providers.base import build_match_id, market_selection_from_outcome


def test_build_match_id_is_stable_from_event_fields():
    match_id = build_match_id("2026-06-26T20:00:00Z", "Canada", "France")
    assert match_id == "2026-06-26_canada_france"


def test_market_selection_mapping_for_h2h_outcomes():
    assert market_selection_from_outcome("Canada", "Canada", "France") == "home_win"
    assert market_selection_from_outcome("France", "Canada", "France") == "away_win"
    assert market_selection_from_outcome("Draw", "Canada", "France") == "draw"


def test_mock_provider_returns_requested_books_only():
    provider = MockOddsProvider()
    lines = provider.fetch_odds(
        sport_key="soccer_fifa_world_cup",
        bookmakers=["fanduel", "betmgm"],
        markets=["h2h"],
    )

    books = {line.sportsbook for line in lines}
    assert books == {"fanduel", "betmgm"}
    assert all(line.sport_key == "soccer_fifa_world_cup" for line in lines)


def test_mock_provider_normalizes_implied_probability():
    provider = MockOddsProvider()
    lines = provider.fetch_odds(
        sport_key="soccer_fifa_world_cup",
        bookmakers=["fanduel"],
        markets=["h2h"],
    )

    home_line = [line for line in lines if line.selection == "home_win"][0]
    expected = 100 / (225 + 100)
    assert math.isclose(home_line.implied_probability, expected, rel_tol=1e-9)
