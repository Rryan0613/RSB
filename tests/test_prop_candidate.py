import pytest

from prop_candidate import (
    PropCandidateValidationError,
    normalize_sport,
    normalize_league,
    normalize_market_type,
    normalize_selection,
    build_prop_candidate,
)


# ---------------------------------------------------------------------------
# PropCandidateValidationError
# ---------------------------------------------------------------------------

def test_prop_candidate_validation_error_is_value_error():
    assert issubclass(PropCandidateValidationError, ValueError)


# ---------------------------------------------------------------------------
# normalize_sport
# ---------------------------------------------------------------------------

def test_normalize_sport_basic():
    assert normalize_sport("soccer") == "soccer"


def test_normalize_sport_strips_whitespace():
    assert normalize_sport("  soccer  ") == "soccer"


def test_normalize_sport_lowercases():
    assert normalize_sport("SOCCER") == "soccer"


def test_normalize_sport_spaces_to_underscores():
    assert normalize_sport("american football") == "american_football"


def test_normalize_sport_hyphens_to_underscores():
    assert normalize_sport("american-football") == "american_football"


def test_normalize_sport_returns_str():
    assert type(normalize_sport("soccer")) is str


@pytest.mark.parametrize("value", [None, 42, ["soccer"]])
def test_normalize_sport_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        normalize_sport(value)


def test_normalize_sport_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        normalize_sport("")


def test_normalize_sport_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        normalize_sport("   ")


# ---------------------------------------------------------------------------
# normalize_league
# ---------------------------------------------------------------------------

def test_normalize_league_basic():
    assert normalize_league("nba") == "nba"


def test_normalize_league_strips():
    assert normalize_league("  nba  ") == "nba"


def test_normalize_league_lowercases():
    assert normalize_league("NBA") == "nba"


def test_normalize_league_spaces_to_underscores():
    assert normalize_league("world cup") == "world_cup"


def test_normalize_league_hyphens_to_underscores():
    assert normalize_league("world-cup") == "world_cup"


def test_normalize_league_returns_str():
    assert type(normalize_league("nba")) is str


@pytest.mark.parametrize("value", [None, 0, ["nba"]])
def test_normalize_league_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        normalize_league(value)


def test_normalize_league_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        normalize_league("")


def test_normalize_league_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        normalize_league("   ")


# ---------------------------------------------------------------------------
# normalize_market_type
# ---------------------------------------------------------------------------

def test_normalize_market_type_basic():
    assert normalize_market_type("player_points") == "player_points"


def test_normalize_market_type_strips():
    assert normalize_market_type("  player_points  ") == "player_points"


def test_normalize_market_type_lowercases():
    assert normalize_market_type("PLAYER_POINTS") == "player_points"


def test_normalize_market_type_spaces_to_underscores():
    assert normalize_market_type("player points") == "player_points"


def test_normalize_market_type_hyphens_to_underscores():
    assert normalize_market_type("player-points") == "player_points"


def test_normalize_market_type_returns_str():
    assert type(normalize_market_type("player_points")) is str


@pytest.mark.parametrize("value", [None, 0, ["player_points"]])
def test_normalize_market_type_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        normalize_market_type(value)


def test_normalize_market_type_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        normalize_market_type("")


def test_normalize_market_type_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        normalize_market_type("   ")


# ---------------------------------------------------------------------------
# normalize_selection
# ---------------------------------------------------------------------------

def test_normalize_selection_basic():
    assert normalize_selection("over") == "over"


def test_normalize_selection_strips():
    assert normalize_selection("  over  ") == "over"


def test_normalize_selection_lowercases():
    assert normalize_selection("OVER") == "over"


def test_normalize_selection_spaces_to_underscores():
    assert normalize_selection("home win") == "home_win"


def test_normalize_selection_hyphens_to_underscores():
    assert normalize_selection("home-win") == "home_win"


def test_normalize_selection_returns_str():
    assert type(normalize_selection("over")) is str


@pytest.mark.parametrize("value", [None, 1, ["over"]])
def test_normalize_selection_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        normalize_selection(value)


def test_normalize_selection_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        normalize_selection("")


def test_normalize_selection_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        normalize_selection("   ")


# ---------------------------------------------------------------------------
# build_prop_candidate — return shape
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "sport", "league", "event_id", "market_type", "selection",
    "line", "player_id", "player_name", "team_id", "team_name",
    "opponent_id", "opponent_name", "created_at", "metadata",
}


def test_build_prop_candidate_returns_exactly_14_keys():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert set(result.keys()) == EXPECTED_KEYS
    assert len(result) == 14


def test_build_prop_candidate_returns_plain_dict():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert type(result) is dict


def test_build_prop_candidate_all_keys_always_present():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    for key in EXPECTED_KEYS:
        assert key in result


# ---------------------------------------------------------------------------
# build_prop_candidate — canonical example (all fields)
# ---------------------------------------------------------------------------

def test_build_prop_candidate_full_canonical():
    result = build_prop_candidate(
        "soccer",
        "world_cup",
        "WC2026_G42",
        "player_shots_on_target",
        "over",
        line=2.5,
        player_id="p_mbappe",
        player_name="Kylian Mbappé",
        team_id="t_france",
        team_name="France",
        opponent_id="t_argentina",
        opponent_name="Argentina",
        created_at="2026-06-29T10:00:00Z",
        metadata={"source": "manual"},
    )
    assert result["sport"] == "soccer"
    assert result["league"] == "world_cup"
    assert result["event_id"] == "WC2026_G42"
    assert result["market_type"] == "player_shots_on_target"
    assert result["selection"] == "over"
    assert result["line"] == pytest.approx(2.5)
    assert result["player_id"] == "p_mbappe"
    assert result["player_name"] == "Kylian Mbappé"
    assert result["team_id"] == "t_france"
    assert result["team_name"] == "France"
    assert result["opponent_id"] == "t_argentina"
    assert result["opponent_name"] == "Argentina"
    assert result["created_at"] == "2026-06-29T10:00:00Z"
    assert result["metadata"] == {"source": "manual"}


# ---------------------------------------------------------------------------
# build_prop_candidate — minimal required fields / optional defaults
# ---------------------------------------------------------------------------

def test_build_prop_candidate_minimal_required_only():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["sport"] == "soccer"
    assert result["league"] == "world_cup"
    assert result["event_id"] == "WC2026_G42"
    assert result["market_type"] == "player_points"
    assert result["selection"] == "over"
    assert result["line"] is None
    assert result["player_id"] is None
    assert result["player_name"] is None
    assert result["team_id"] is None
    assert result["team_name"] is None
    assert result["opponent_id"] is None
    assert result["opponent_name"] is None
    assert result["created_at"] is None
    assert result["metadata"] == {}


# ---------------------------------------------------------------------------
# build_prop_candidate — required field validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["soccer"]])
def test_build_prop_candidate_sport_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(value, "world_cup", "WC2026_G42", "player_points", "over")


def test_build_prop_candidate_sport_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("", "world_cup", "WC2026_G42", "player_points", "over")


def test_build_prop_candidate_sport_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("   ", "world_cup", "WC2026_G42", "player_points", "over")


@pytest.mark.parametrize("value", [None, 42, ["nba"]])
def test_build_prop_candidate_league_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", value, "WC2026_G42", "player_points", "over")


def test_build_prop_candidate_league_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "", "WC2026_G42", "player_points", "over")


def test_build_prop_candidate_league_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "   ", "WC2026_G42", "player_points", "over")


@pytest.mark.parametrize("value", [None, 42, ["WC2026"]])
def test_build_prop_candidate_event_id_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", value, "player_points", "over")


def test_build_prop_candidate_event_id_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "", "player_points", "over")


def test_build_prop_candidate_event_id_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "   ", "player_points", "over")


@pytest.mark.parametrize("value", [None, 42, ["player_points"]])
def test_build_prop_candidate_market_type_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "WC2026_G42", value, "over")


def test_build_prop_candidate_market_type_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "WC2026_G42", "", "over")


def test_build_prop_candidate_market_type_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "WC2026_G42", "   ", "over")


@pytest.mark.parametrize("value", [None, 42, ["over"]])
def test_build_prop_candidate_selection_rejects_non_string(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "WC2026_G42", "player_points", value)


def test_build_prop_candidate_selection_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "WC2026_G42", "player_points", "")


def test_build_prop_candidate_selection_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate("soccer", "world_cup", "WC2026_G42", "player_points", "   ")


# ---------------------------------------------------------------------------
# build_prop_candidate — event_id case preservation
# ---------------------------------------------------------------------------

def test_build_prop_candidate_event_id_preserves_case():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["event_id"] == "WC2026_G42"


def test_build_prop_candidate_event_id_strips_whitespace():
    result = build_prop_candidate(
        "soccer", "world_cup", "  WC2026_G42  ", "player_points", "over"
    )
    assert result["event_id"] == "WC2026_G42"


def test_build_prop_candidate_event_id_not_lowercased():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026-GroupA-G42", "player_points", "over"
    )
    assert result["event_id"] == "WC2026-GroupA-G42"


# ---------------------------------------------------------------------------
# build_prop_candidate — optional id fields
# ---------------------------------------------------------------------------

def test_build_prop_candidate_player_id_none():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["player_id"] is None


def test_build_prop_candidate_player_id_valid_string():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        player_id="p_mbappe",
    )
    assert result["player_id"] == "p_mbappe"


def test_build_prop_candidate_player_id_strips_whitespace():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        player_id="  p_mbappe  ",
    )
    assert result["player_id"] == "p_mbappe"


def test_build_prop_candidate_player_id_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            player_id="",
        )


def test_build_prop_candidate_player_id_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            player_id="   ",
        )


def test_build_prop_candidate_team_id_none():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["team_id"] is None


def test_build_prop_candidate_team_id_valid_string():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        team_id="t_france",
    )
    assert result["team_id"] == "t_france"


def test_build_prop_candidate_opponent_id_none():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["opponent_id"] is None


def test_build_prop_candidate_opponent_id_valid_string():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        opponent_id="t_argentina",
    )
    assert result["opponent_id"] == "t_argentina"


# ---------------------------------------------------------------------------
# build_prop_candidate — display name fields (case preserved, stripped)
# ---------------------------------------------------------------------------

def test_build_prop_candidate_player_name_none():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["player_name"] is None


def test_build_prop_candidate_player_name_preserves_case():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        player_name="Kylian Mbappé",
    )
    assert result["player_name"] == "Kylian Mbappé"


def test_build_prop_candidate_player_name_strips_whitespace():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        player_name="  Kylian Mbappé  ",
    )
    assert result["player_name"] == "Kylian Mbappé"


def test_build_prop_candidate_player_name_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            player_name="",
        )


def test_build_prop_candidate_team_name_preserves_case():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        team_name="France",
    )
    assert result["team_name"] == "France"


def test_build_prop_candidate_opponent_name_preserves_case():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        opponent_name="Argentina",
    )
    assert result["opponent_name"] == "Argentina"


# ---------------------------------------------------------------------------
# build_prop_candidate — line validation
# ---------------------------------------------------------------------------

def test_build_prop_candidate_line_none():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["line"] is None


def test_build_prop_candidate_line_float():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        line=2.5,
    )
    assert result["line"] == pytest.approx(2.5)


def test_build_prop_candidate_line_int_returns_float():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        line=2,
    )
    assert result["line"] == pytest.approx(2.0)
    assert type(result["line"]) is float


def test_build_prop_candidate_line_negative():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "spread", "home",
        line=-3.5,
    )
    assert result["line"] == pytest.approx(-3.5)


def test_build_prop_candidate_line_zero():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "spread", "home",
        line=0,
    )
    assert result["line"] == pytest.approx(0.0)
    assert type(result["line"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_build_prop_candidate_line_rejects_bool(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            line=value,
        )


@pytest.mark.parametrize("value", ["2.5", [2.5]])
def test_build_prop_candidate_line_rejects_non_numeric(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            line=value,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_prop_candidate_line_rejects_nan_and_inf(value):
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            line=value,
        )


# ---------------------------------------------------------------------------
# build_prop_candidate — created_at
# ---------------------------------------------------------------------------

def test_build_prop_candidate_created_at_none():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["created_at"] is None


def test_build_prop_candidate_created_at_valid_string():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        created_at="2026-06-29T10:00:00Z",
    )
    assert result["created_at"] == "2026-06-29T10:00:00Z"


def test_build_prop_candidate_created_at_strips_whitespace():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        created_at="  2026-06-29T10:00:00Z  ",
    )
    assert result["created_at"] == "2026-06-29T10:00:00Z"


def test_build_prop_candidate_created_at_rejects_empty():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            created_at="",
        )


def test_build_prop_candidate_created_at_rejects_whitespace_only():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            created_at="   ",
        )


def test_build_prop_candidate_created_at_rejects_non_string():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            created_at=20260629,
        )


# ---------------------------------------------------------------------------
# build_prop_candidate — metadata
# ---------------------------------------------------------------------------

def test_build_prop_candidate_metadata_none_returns_empty_dict():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["metadata"] == {}
    assert type(result["metadata"]) is dict


def test_build_prop_candidate_metadata_passed_dict():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        metadata={"source": "manual"},
    )
    assert result["metadata"] == {"source": "manual"}


def test_build_prop_candidate_metadata_is_plain_dict():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        metadata={"source": "manual"},
    )
    assert type(result["metadata"]) is dict


def test_build_prop_candidate_metadata_mutation_isolation():
    caller_meta = {"source": "manual"}
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over",
        metadata=caller_meta,
    )
    result["metadata"]["extra"] = "injected"
    assert "extra" not in caller_meta


def test_build_prop_candidate_metadata_rejects_non_dict():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            metadata=["source"],
        )


def test_build_prop_candidate_metadata_rejects_string():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            metadata="source",
        )


# ---------------------------------------------------------------------------
# build_prop_candidate — normalization applied in output
# ---------------------------------------------------------------------------

def test_build_prop_candidate_sport_normalized_in_output():
    result = build_prop_candidate(
        "  SOCCER  ", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["sport"] == "soccer"


def test_build_prop_candidate_league_normalized_in_output():
    result = build_prop_candidate(
        "soccer", "World Cup", "WC2026_G42", "player_points", "over"
    )
    assert result["league"] == "world_cup"


def test_build_prop_candidate_market_type_normalized_in_output():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "Player-Points", "over"
    )
    assert result["market_type"] == "player_points"


def test_build_prop_candidate_selection_normalized_in_output():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "  OVER  "
    )
    assert result["selection"] == "over"


def test_build_prop_candidate_event_id_not_lowercased_in_output():
    result = build_prop_candidate(
        "soccer", "world_cup", "WC2026_G42", "player_points", "over"
    )
    assert result["event_id"] == "WC2026_G42"


# ---------------------------------------------------------------------------
# build_prop_candidate — operation order
# ---------------------------------------------------------------------------

def test_build_prop_candidate_bad_sport_raises_before_line_check():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            None, "world_cup", "WC2026_G42", "player_points", "over",
            line=True,
        )


def test_build_prop_candidate_bad_league_raises_before_event_id_check():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "", "WC2026_G42", "player_points", "over"
        )


def test_build_prop_candidate_bad_line_raises_before_optional_fields():
    with pytest.raises(PropCandidateValidationError):
        build_prop_candidate(
            "soccer", "world_cup", "WC2026_G42", "player_points", "over",
            line=True, player_id=42,
        )


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_prop_candidate_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "prop_candidate.py"
    tree = ast.parse(src.read_text())
    banned = {
        "sqlite3", "database", "json", "subprocess", "pathlib",
        "odds", "ev", "edge", "candidate_evaluation", "backtest_review",
        "review_taxonomy", "review_notes",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
