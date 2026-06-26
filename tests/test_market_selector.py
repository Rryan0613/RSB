from market_selector import (
    evaluate_odds_lines,
    get_active_rules,
    qualified_best_prices,
    rejected_price_groups,
    select_best_prices,
)
from odds_collector import collect_odds


def runtime_config():
    return {
        "model_config": {"version": "0.1.3", "odds_collection": {"provider": "mock"}},
        "sports_config": {},
        "active_sport": "worldcup",
        "sport_profile": {
            "label": "FIFA World Cup",
            "provider_sport_key": "soccer_fifa_world_cup",
            "bookmakers": ["fanduel", "draftkings", "betmgm"],
            "markets": ["h2h"],
        },
        "odds_config": {
            "provider": "mock",
            "regions": "us",
            "bookmakers": ["fanduel", "draftkings", "betmgm"],
            "markets": ["h2h"],
            "odds_format": "american",
        },
    }


def base_rules():
    return {
        "profile_name": "test_profile",
        "allowed_markets": ["h2h"],
        "allowed_selections": ["home_win", "draw", "away_win"],
        "bookmaker_rules": {
            "required": ["fanduel", "draftkings", "betmgm"],
            "minimum_available": 2,
        },
        "target_odds": {
            "min_decimal": 1.2,
            "max_decimal": 6.0,
        },
        "bet_structure": {
            "single_leg_enabled": True,
            "parlay_enabled": False,
            "same_game_parlay_enabled": False,
        },
    }


def test_select_best_prices_keeps_best_line_per_selection():
    lines = collect_odds(runtime_config())
    best = select_best_prices(lines)

    assert len(best) == 3
    home_win = [line for line in best if line["selection"] == "home_win"][0]
    assert home_win["sportsbook"] == "betmgm"
    assert home_win["american_odds"] == 230


def test_evaluate_odds_lines_qualifies_mock_worldcup_lines():
    lines = collect_odds(runtime_config())
    decisions = evaluate_odds_lines(lines, base_rules())

    assert len(decisions) == 3
    assert all(decision["status"] == "qualified" for decision in decisions)
    assert len(qualified_best_prices(decisions)) == 3
    assert rejected_price_groups(decisions) == []


def test_minimum_sportsbook_requirement_can_reject_group():
    lines = collect_odds(runtime_config())
    rules = base_rules()
    rules["bookmaker_rules"] = {
        "required": ["fanduel", "draftkings", "betmgm", "caesars"],
        "minimum_available": 4,
    }

    decisions = evaluate_odds_lines(lines, rules)

    assert all(decision["status"] == "rejected" for decision in decisions)
    assert all("not_enough_sportsbooks:3" in decision["reasons"] for decision in decisions)


def test_target_odds_range_can_reject_short_prices():
    lines = collect_odds(runtime_config())
    rules = base_rules()
    rules["target_odds"] = {
        "min_decimal": 3.0,
        "max_decimal": 6.0,
    }

    decisions = evaluate_odds_lines(lines, rules)
    away_decision = [decision for decision in decisions if decision["selection"] == "away_win"][0]

    assert away_decision["status"] == "rejected"
    assert any(reason.startswith("below_min_decimal_odds") for reason in away_decision["reasons"])


def test_get_active_rules_loads_default_config():
    rules = get_active_rules()

    assert rules["profile_name"] == "worldcup_default"
    assert rules["allowed_markets"] == ["h2h"]
    assert rules["bet_structure"]["single_leg_enabled"] is True
