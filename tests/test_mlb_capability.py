import pytest

from mlb_capability import (
    MLB_SPORT,
    MLB_LEAGUE,
    build_mlb_capability_profile,
)


_EXPECTED_MARKET_CAPABILITY_KEYS = {
    "sport",
    "league",
    "market_type",
    "selection_type",
    "requires_line",
    "allows_line",
    "line_value_type",
    "requires_player",
    "requires_team",
    "requires_opponent",
    "requires_starting_status",
    "start_required_supported",
    "participation_required_supported",
    "void_condition_supported",
    "settlement_rule_required",
    "supported_selection_values",
    "required_fields",
    "optional_fields",
    "metadata",
}

_TEAM_MARKETS = ("moneyline", "run_line")
_TEAM_GAME_MARKETS = ("moneyline", "run_line", "total_runs", "team_total_runs")
_LINE_MARKETS = ("run_line", "total_runs", "team_total_runs")
_OVER_UNDER_MARKETS = ("total_runs", "team_total_runs")

_BATTER_MARKETS = (
    "player_hits",
    "player_total_bases",
    "player_home_runs",
    "player_rbis",
    "player_runs",
    "player_stolen_bases",
)

_PITCHER_MARKETS = (
    "pitcher_strikeouts",
    "pitcher_outs_recorded",
    "pitcher_hits_allowed",
    "pitcher_walks_allowed",
    "pitcher_earned_runs_allowed",
)

_LINE_MARKETS_FULL = _LINE_MARKETS + _BATTER_MARKETS + _PITCHER_MARKETS
_OVER_UNDER_MARKETS_FULL = _OVER_UNDER_MARKETS + _BATTER_MARKETS + _PITCHER_MARKETS

_ALL_MARKET_TYPES = _TEAM_GAME_MARKETS + _BATTER_MARKETS + _PITCHER_MARKETS


def _markets_by_type(profile):
    return {market["market_type"]: market for market in profile["supported_markets"]}


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

def test_mlb_sport_constant():
    assert MLB_SPORT == "baseball"


def test_mlb_league_constant():
    assert MLB_LEAGUE == "mlb"


# ---------------------------------------------------------------------------
# profile shape
# ---------------------------------------------------------------------------

def test_profile_sport_matches_constant():
    profile = build_mlb_capability_profile()
    assert profile["sport"] == MLB_SPORT


def test_profile_league_matches_constant():
    profile = build_mlb_capability_profile()
    assert profile["league"] == MLB_LEAGUE


def test_profile_metadata_is_stable():
    profile = build_mlb_capability_profile()
    assert profile["metadata"] == {"profile_type": "mlb_capability_seed"}


def test_profile_market_count_matches_supported_markets_length():
    profile = build_mlb_capability_profile()
    assert profile["market_count"] == len(profile["supported_markets"])


def test_profile_market_count_is_15():
    profile = build_mlb_capability_profile()
    assert profile["market_count"] == 15


def test_profile_is_plain_dict():
    profile = build_mlb_capability_profile()
    assert type(profile) is dict


def test_profile_supported_markets_is_plain_list():
    profile = build_mlb_capability_profile()
    assert type(profile["supported_markets"]) is list


def test_profile_supported_markets_entries_are_plain_dicts():
    profile = build_mlb_capability_profile()
    for market in profile["supported_markets"]:
        assert type(market) is dict


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------

def test_build_mlb_capability_profile_is_deterministic():
    result_one = build_mlb_capability_profile()
    result_two = build_mlb_capability_profile()
    assert result_one == result_two


def test_build_mlb_capability_profile_no_mutation_leak_via_market_dict():
    result_one = build_mlb_capability_profile()
    result_one["supported_markets"][0]["market_type"] = "mutated"
    result_two = build_mlb_capability_profile()
    assert result_two["supported_markets"][0]["market_type"] != "mutated"


def test_build_mlb_capability_profile_no_mutation_leak_via_markets_list():
    result_one = build_mlb_capability_profile()
    result_one["supported_markets"].append({"bogus": True})
    result_two = build_mlb_capability_profile()
    assert len(result_two["supported_markets"]) == 15


def test_build_mlb_capability_profile_no_mutation_leak_via_metadata():
    result_one = build_mlb_capability_profile()
    result_one["metadata"]["mutated"] = True
    result_two = build_mlb_capability_profile()
    assert result_two["metadata"] == {"profile_type": "mlb_capability_seed"}


# ---------------------------------------------------------------------------
# expected market slugs / no duplicates
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _ALL_MARKET_TYPES)
def test_expected_market_type_present(market_type):
    profile = build_mlb_capability_profile()
    market_types = {market["market_type"] for market in profile["supported_markets"]}
    assert market_type in market_types


def test_no_duplicate_market_selection_pairs():
    profile = build_mlb_capability_profile()
    pairs = [
        (market["market_type"], market["selection_type"])
        for market in profile["supported_markets"]
    ]
    assert len(pairs) == len(set(pairs))


def test_expected_market_selection_pairs_exact():
    expected_pairs = {
        ("moneyline", "team"),
        ("run_line", "team"),
        ("total_runs", "over_under"),
        ("team_total_runs", "over_under"),
    }
    expected_pairs |= {(market_type, "over_under") for market_type in _BATTER_MARKETS}
    expected_pairs |= {(market_type, "over_under") for market_type in _PITCHER_MARKETS}

    profile = build_mlb_capability_profile()
    actual_pairs = {
        (market["market_type"], market["selection_type"])
        for market in profile["supported_markets"]
    }
    assert actual_pairs == expected_pairs


def test_every_market_has_exact_v0_2_11_key_shape():
    profile = build_mlb_capability_profile()
    for market in profile["supported_markets"]:
        assert set(market.keys()) == _EXPECTED_MARKET_CAPABILITY_KEYS


# ---------------------------------------------------------------------------
# line semantics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _LINE_MARKETS_FULL)
def test_line_markets_require_and_allow_line(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_line"] is True
    assert market["allows_line"] is True
    assert market["line_value_type"] == "float"


def test_moneyline_does_not_allow_or_require_line():
    market = _markets_by_type(build_mlb_capability_profile())["moneyline"]
    assert market["requires_line"] is False
    assert market["allows_line"] is False
    assert market["line_value_type"] is None


# ---------------------------------------------------------------------------
# selection value semantics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _OVER_UNDER_MARKETS_FULL)
def test_over_under_markets_expose_over_under_values(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["supported_selection_values"] == ["over", "under"]


@pytest.mark.parametrize("market_type", _TEAM_MARKETS)
def test_team_markets_expose_home_away_values(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["supported_selection_values"] == ["home", "away"]


# ---------------------------------------------------------------------------
# team/game market requirements
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _TEAM_GAME_MARKETS)
def test_team_game_markets_require_team_and_opponent_not_player(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_team"] is True
    assert market["requires_opponent"] is True
    assert market["requires_player"] is False


@pytest.mark.parametrize("market_type", _TEAM_GAME_MARKETS)
def test_team_game_markets_have_no_player_participation_flags(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_starting_status"] is False
    assert market["start_required_supported"] is False
    assert market["participation_required_supported"] is False
    assert market["void_condition_supported"] is False


def test_moneyline_required_fields():
    market = _markets_by_type(build_mlb_capability_profile())["moneyline"]
    assert market["required_fields"] == ["team", "opponent"]


@pytest.mark.parametrize("market_type", ("run_line", "total_runs", "team_total_runs"))
def test_line_game_markets_required_fields(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["required_fields"] == ["team", "opponent", "line"]


# ---------------------------------------------------------------------------
# batter market requirements
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _BATTER_MARKETS)
def test_batter_markets_require_player_team_opponent(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_player"] is True
    assert market["requires_team"] is True
    assert market["requires_opponent"] is True
    assert market["required_fields"] == ["player", "team", "opponent", "line"]


@pytest.mark.parametrize("market_type", _BATTER_MARKETS)
def test_batter_markets_participation_and_void_flags(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_starting_status"] is False
    assert market["start_required_supported"] is False
    assert market["participation_required_supported"] is True
    assert market["void_condition_supported"] is True


# ---------------------------------------------------------------------------
# pitcher market requirements
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _PITCHER_MARKETS)
def test_pitcher_markets_require_player_team_opponent(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_player"] is True
    assert market["requires_team"] is True
    assert market["requires_opponent"] is True
    assert market["required_fields"] == ["player", "team", "opponent", "line"]


@pytest.mark.parametrize("market_type", _PITCHER_MARKETS)
def test_pitcher_markets_starting_participation_and_void_flags(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["requires_starting_status"] is True
    assert market["start_required_supported"] is True
    assert market["participation_required_supported"] is True
    assert market["void_condition_supported"] is True


# ---------------------------------------------------------------------------
# settlement rule
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market_type", _ALL_MARKET_TYPES)
def test_all_markets_require_settlement_rule(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["settlement_rule_required"] is True


@pytest.mark.parametrize("market_type", _ALL_MARKET_TYPES)
def test_all_markets_have_empty_optional_fields_and_metadata(market_type):
    market = _markets_by_type(build_mlb_capability_profile())[market_type]
    assert market["optional_fields"] == []
    assert market["metadata"] == {}
