import pytest

from slate_odds import find_provider_price, manual_odds_choice, resolve_odds_for_match


def make_line(selection="home_win", home_team="Norway", away_team="France", american_odds=390):
    return {
        "provider": "the_odds_api",
        "provider_event_id": "event_1",
        "match_id": "2026-06-26_norway_france",
        "sport_key": "soccer_fifa_world_cup",
        "commence_time": "2026-06-26T19:00:00Z",
        "home_team": home_team,
        "away_team": away_team,
        "sportsbook": "fanduel",
        "market": "h2h",
        "selection": selection,
        "american_odds": american_odds,
        "implied_probability": 0.2040816326530612,
        "captured_at": "2026-06-26T15:40:08Z",
        "raw_json": {},
    }


def make_decision(selection="home_win", home_team="Norway", away_team="France", american_odds=390):
    line = make_line(selection=selection, home_team=home_team, away_team=away_team, american_odds=american_odds)
    return {
        "status": "qualified",
        "reasons": [],
        "match_id": line["match_id"],
        "market": "h2h",
        "selection": selection,
        "best_line": line,
    }


def make_match(home_team="Norway", away_team="France", odds=None):
    match = {
        "match_id": "2026-06-26_norway_france",
        "date": "2026-06-26",
        "home_team": home_team,
        "away_team": away_team,
        "home": {},
        "away": {},
    }
    if odds is not None:
        match["odds"] = odds
    return match


def test_find_provider_price_by_match_id():
    match = make_match()
    decision = make_decision(selection="home_win", american_odds=390)

    resolved = find_provider_price(match, [decision], requested_selection="home_win")

    assert resolved["line"]["american_odds"] == 390
    assert resolved["match_strategy"] == "match_id"
    assert resolved["provider_selection"] == "home_win"


def test_resolve_provider_odds_before_manual_fallback():
    match = make_match(odds={"home_win": 120})
    decision = make_decision(selection="home_win", american_odds=390)
    context = {"qualified_decisions": [decision]}

    resolved = resolve_odds_for_match(match, provider_context=context)

    assert resolved["source"] == "provider_qualified"
    assert resolved["line"]["american_odds"] == 390


def test_resolve_manual_odds_without_provider_context():
    match = make_match(odds={"home_win": 120})

    resolved = resolve_odds_for_match(match)

    assert resolved["source"] == "manual"
    assert resolved["line"]["provider"] == "manual"
    assert resolved["line"]["american_odds"] == 120


def test_resolve_reversed_provider_team_order():
    match = make_match(home_team="France", away_team="Norway")
    decision = make_decision(selection="away_win", home_team="Norway", away_team="France", american_odds=-170)
    context = {"qualified_decisions": [decision]}

    resolved = resolve_odds_for_match(match, provider_context=context, requested_selection="home_win")

    assert resolved["source"] == "provider_qualified"
    assert resolved["match_strategy"] == "team_date_reversed"
    assert resolved["provider_selection"] == "away_win"
    assert resolved["line"]["american_odds"] == -170


def test_manual_odds_choice_returns_none_when_missing():
    match = make_match()

    assert manual_odds_choice(match) is None


def test_resolve_odds_raises_without_provider_or_manual():
    match = make_match()

    with pytest.raises(ValueError, match="No qualified provider odds found"):
        resolve_odds_for_match(match, allow_manual_fallback=True)
