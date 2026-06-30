import pytest

from prop_result import (
    PropResultValidationError,
    VALID_SETTLEMENT_STATUSES,
    FINAL_SETTLEMENT_STATUSES,
    normalize_market_type,
    normalize_selection,
    normalize_settlement_status,
    build_prop_result,
)


# ---------------------------------------------------------------------------
# PropResultValidationError
# ---------------------------------------------------------------------------

def test_prop_result_validation_error_is_value_error():
    assert issubclass(PropResultValidationError, ValueError)


# ---------------------------------------------------------------------------
# VALID_SETTLEMENT_STATUSES
# ---------------------------------------------------------------------------

def test_valid_settlement_statuses_is_frozenset():
    assert isinstance(VALID_SETTLEMENT_STATUSES, frozenset)


def test_valid_settlement_statuses_contents():
    assert VALID_SETTLEMENT_STATUSES == frozenset({
        "won", "lost", "push", "void", "pending", "unknown",
    })


# ---------------------------------------------------------------------------
# FINAL_SETTLEMENT_STATUSES
# ---------------------------------------------------------------------------

def test_final_settlement_statuses_is_frozenset():
    assert isinstance(FINAL_SETTLEMENT_STATUSES, frozenset)


def test_final_settlement_statuses_contents():
    assert FINAL_SETTLEMENT_STATUSES == frozenset({"won", "lost", "push", "void"})


def test_final_settlement_statuses_subset_of_valid():
    assert FINAL_SETTLEMENT_STATUSES <= VALID_SETTLEMENT_STATUSES


# ---------------------------------------------------------------------------
# normalize_market_type
# ---------------------------------------------------------------------------

def test_normalize_market_type_basic():
    assert normalize_market_type("player_points") == "player_points"


def test_normalize_market_type_strips_whitespace():
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
    with pytest.raises(PropResultValidationError):
        normalize_market_type(value)


def test_normalize_market_type_rejects_empty():
    with pytest.raises(PropResultValidationError):
        normalize_market_type("")


def test_normalize_market_type_rejects_whitespace_only():
    with pytest.raises(PropResultValidationError):
        normalize_market_type("   ")


# ---------------------------------------------------------------------------
# normalize_selection
# ---------------------------------------------------------------------------

def test_normalize_selection_basic():
    assert normalize_selection("over") == "over"


def test_normalize_selection_strips_whitespace():
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
    with pytest.raises(PropResultValidationError):
        normalize_selection(value)


def test_normalize_selection_rejects_empty():
    with pytest.raises(PropResultValidationError):
        normalize_selection("")


def test_normalize_selection_rejects_whitespace_only():
    with pytest.raises(PropResultValidationError):
        normalize_selection("   ")


# ---------------------------------------------------------------------------
# normalize_settlement_status
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", sorted(VALID_SETTLEMENT_STATUSES))
def test_normalize_settlement_status_all_valid(status):
    assert normalize_settlement_status(status) == status


def test_normalize_settlement_status_strips_whitespace():
    assert normalize_settlement_status("  won  ") == "won"


def test_normalize_settlement_status_lowercases():
    assert normalize_settlement_status("WON") == "won"


def test_normalize_settlement_status_spaces_to_underscores():
    # Verifies slug normalization before frozenset check
    with pytest.raises(PropResultValidationError):
        normalize_settlement_status("not real")


def test_normalize_settlement_status_returns_str():
    assert type(normalize_settlement_status("won")) is str


@pytest.mark.parametrize("value", [None, 42, ["won"]])
def test_normalize_settlement_status_rejects_non_string(value):
    with pytest.raises(PropResultValidationError):
        normalize_settlement_status(value)


def test_normalize_settlement_status_rejects_empty():
    with pytest.raises(PropResultValidationError):
        normalize_settlement_status("")


def test_normalize_settlement_status_rejects_whitespace_only():
    with pytest.raises(PropResultValidationError):
        normalize_settlement_status("   ")


def test_normalize_settlement_status_rejects_unknown():
    with pytest.raises(PropResultValidationError):
        normalize_settlement_status("graded")


def test_normalize_settlement_status_rejects_win():
    with pytest.raises(PropResultValidationError):
        normalize_settlement_status("win")


# ---------------------------------------------------------------------------
# build_prop_result — return shape
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "event_id", "market_type", "selection", "line", "actual_value",
    "settlement_status", "settled_at", "source", "settlement_rule",
    "start_required", "participation_required", "void_condition",
    "void_reason", "metadata",
}


def test_build_prop_result_returns_exactly_14_keys():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert set(result.keys()) == EXPECTED_KEYS
    assert len(result) == 14


def test_build_prop_result_returns_plain_dict():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert type(result) is dict


def test_build_prop_result_all_keys_always_present():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    for key in EXPECTED_KEYS:
        assert key in result


# ---------------------------------------------------------------------------
# build_prop_result — canonical examples
# ---------------------------------------------------------------------------

def test_build_prop_result_canonical_won():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_shots_on_target",
        selection="over",
        line=2.5,
        actual_value=3.0,
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        source="manual",
        settlement_rule="standard_over_under",
        start_required=True,
        participation_required=True,
        void_condition="player_did_not_start",
        metadata={"batch_id": "b001"},
    )
    assert result["event_id"] == "WC2026_G42"
    assert result["market_type"] == "player_shots_on_target"
    assert result["selection"] == "over"
    assert result["line"] == pytest.approx(2.5)
    assert result["actual_value"] == pytest.approx(3.0)
    assert result["settlement_status"] == "won"
    assert result["settled_at"] == "2026-06-30T20:00:00Z"
    assert result["source"] == "manual"
    assert result["settlement_rule"] == "standard_over_under"
    assert result["start_required"] is True
    assert result["participation_required"] is True
    assert result["void_condition"] == "player_did_not_start"
    assert result["void_reason"] is None
    assert result["metadata"] == {"batch_id": "b001"}


def test_build_prop_result_canonical_pending():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["settlement_status"] == "pending"
    assert result["settled_at"] is None
    assert result["actual_value"] is None
    assert result["void_reason"] is None


def test_build_prop_result_canonical_void_with_reason():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_shots_on_target",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
        void_reason="player_did_not_participate",
    )
    assert result["settlement_status"] == "void"
    assert result["settled_at"] == "2026-06-30T20:00:00Z"
    assert result["void_reason"] == "player_did_not_participate"


def test_build_prop_result_canonical_void_without_reason():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "void"
    assert result["void_reason"] is None


def test_build_prop_result_canonical_lost():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        line=2.5,
        actual_value=1.0,
        settlement_status="lost",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "lost"
    assert result["settled_at"] == "2026-06-30T20:00:00Z"


def test_build_prop_result_canonical_push():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        line=3.0,
        actual_value=3.0,
        settlement_status="push",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "push"


def test_build_prop_result_canonical_unknown():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="unknown",
    )
    assert result["settlement_status"] == "unknown"
    assert result["settled_at"] is None


# ---------------------------------------------------------------------------
# build_prop_result — minimal required-only / optional defaults
# ---------------------------------------------------------------------------

def test_build_prop_result_minimal_pending_defaults():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["line"] is None
    assert result["actual_value"] is None
    assert result["settled_at"] is None
    assert result["source"] is None
    assert result["settlement_rule"] is None
    assert result["start_required"] is None
    assert result["participation_required"] is None
    assert result["void_condition"] is None
    assert result["void_reason"] is None
    assert result["metadata"] == {}


def test_build_prop_result_minimal_won_with_settled_at():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "won"
    assert result["actual_value"] is None


# ---------------------------------------------------------------------------
# build_prop_result — event_id validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["WC2026_G42"]])
def test_build_prop_result_event_id_rejects_non_string(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id=value,
            market_type="player_points",
            selection="over",
            settlement_status="pending",
        )


def test_build_prop_result_event_id_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
        )


def test_build_prop_result_event_id_rejects_whitespace_only():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="   ",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
        )


def test_build_prop_result_event_id_strips_whitespace():
    result = build_prop_result(
        event_id="  WC2026_G42  ",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["event_id"] == "WC2026_G42"


def test_build_prop_result_event_id_preserves_case():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["event_id"] == "WC2026_G42"


def test_build_prop_result_event_id_not_lowercased():
    result = build_prop_result(
        event_id="WC2026-GroupA-G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["event_id"] == "WC2026-GroupA-G42"


# ---------------------------------------------------------------------------
# build_prop_result — market_type and selection normalization in output
# ---------------------------------------------------------------------------

def test_build_prop_result_market_type_normalized_in_output():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="Player-Points",
        selection="over",
        settlement_status="pending",
    )
    assert result["market_type"] == "player_points"


def test_build_prop_result_selection_normalized_in_output():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="  OVER  ",
        settlement_status="pending",
    )
    assert result["selection"] == "over"


@pytest.mark.parametrize("value", [None, 42, ["player_points"]])
def test_build_prop_result_market_type_rejects_non_string(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type=value,
            selection="over",
            settlement_status="pending",
        )


def test_build_prop_result_market_type_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="",
            selection="over",
            settlement_status="pending",
        )


@pytest.mark.parametrize("value", [None, 42, ["over"]])
def test_build_prop_result_selection_rejects_non_string(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection=value,
            settlement_status="pending",
        )


def test_build_prop_result_selection_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="",
            settlement_status="pending",
        )


# ---------------------------------------------------------------------------
# build_prop_result — line validation
# ---------------------------------------------------------------------------

def test_build_prop_result_line_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["line"] is None


def test_build_prop_result_line_float():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        line=2.5,
    )
    assert result["line"] == pytest.approx(2.5)


def test_build_prop_result_line_int_returns_float():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        line=2,
    )
    assert result["line"] == pytest.approx(2.0)
    assert type(result["line"]) is float


def test_build_prop_result_line_negative():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="spread",
        selection="home",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        line=-3.5,
    )
    assert result["line"] == pytest.approx(-3.5)


def test_build_prop_result_line_zero():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="spread",
        selection="home",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        line=0,
    )
    assert result["line"] == pytest.approx(0.0)
    assert type(result["line"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_build_prop_result_line_rejects_bool(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            line=value,
        )


@pytest.mark.parametrize("value", ["2.5", [2.5]])
def test_build_prop_result_line_rejects_non_numeric(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            line=value,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_prop_result_line_rejects_nan_and_inf(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            line=value,
        )


# ---------------------------------------------------------------------------
# build_prop_result — actual_value validation
# ---------------------------------------------------------------------------

def test_build_prop_result_actual_value_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["actual_value"] is None


def test_build_prop_result_actual_value_float():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        actual_value=3.0,
    )
    assert result["actual_value"] == pytest.approx(3.0)


def test_build_prop_result_actual_value_int_returns_float():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        actual_value=3,
    )
    assert result["actual_value"] == pytest.approx(3.0)
    assert type(result["actual_value"]) is float


def test_build_prop_result_actual_value_zero():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_shots_on_target",
        selection="over",
        settlement_status="lost",
        settled_at="2026-06-30T20:00:00Z",
        actual_value=0,
    )
    assert result["actual_value"] == pytest.approx(0.0)
    assert type(result["actual_value"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_build_prop_result_actual_value_rejects_bool(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            actual_value=value,
        )


@pytest.mark.parametrize("value", ["3.0", [3.0]])
def test_build_prop_result_actual_value_rejects_non_numeric(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            actual_value=value,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_prop_result_actual_value_rejects_nan_and_inf(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            actual_value=value,
        )


def test_build_prop_result_actual_value_independent_of_line():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
        line=2.5,
        actual_value=None,
    )
    assert result["line"] == pytest.approx(2.5)
    assert result["actual_value"] is None


# ---------------------------------------------------------------------------
# build_prop_result — settlement_status validation
# ---------------------------------------------------------------------------

def test_build_prop_result_settlement_status_normalized_in_output():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="PENDING",
    )
    assert result["settlement_status"] == "pending"


@pytest.mark.parametrize("value", [None, 42, ["won"]])
def test_build_prop_result_settlement_status_rejects_non_string(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status=value,
        )


def test_build_prop_result_settlement_status_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="",
        )


def test_build_prop_result_settlement_status_rejects_unknown():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="graded",
        )


# ---------------------------------------------------------------------------
# build_prop_result — settled_at validation
# ---------------------------------------------------------------------------

def test_build_prop_result_settled_at_none_for_pending():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["settled_at"] is None


def test_build_prop_result_settled_at_none_for_unknown():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="unknown",
    )
    assert result["settled_at"] is None


def test_build_prop_result_settled_at_valid_for_won():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settled_at"] == "2026-06-30T20:00:00Z"


def test_build_prop_result_settled_at_strips_whitespace():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="won",
        settled_at="  2026-06-30T20:00:00Z  ",
    )
    assert result["settled_at"] == "2026-06-30T20:00:00Z"


def test_build_prop_result_settled_at_rejects_empty_string():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="won",
            settled_at="",
        )


def test_build_prop_result_settled_at_rejects_whitespace_only():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="won",
            settled_at="   ",
        )


@pytest.mark.parametrize("value", [20260630, ["2026-06-30"]])
def test_build_prop_result_settled_at_rejects_non_string(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="won",
            settled_at=value,
        )


# ---------------------------------------------------------------------------
# build_prop_result — source validation
# ---------------------------------------------------------------------------

def test_build_prop_result_source_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["source"] is None


def test_build_prop_result_source_valid_string():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        source="manual",
    )
    assert result["source"] == "manual"


def test_build_prop_result_source_strips_whitespace():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        source="  manual  ",
    )
    assert result["source"] == "manual"


def test_build_prop_result_source_preserves_case():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        source="Manual_Feed",
    )
    assert result["source"] == "Manual_Feed"


def test_build_prop_result_source_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            source="",
        )


def test_build_prop_result_source_rejects_non_string():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            source=42,
        )


# ---------------------------------------------------------------------------
# build_prop_result — settlement_rule validation
# ---------------------------------------------------------------------------

def test_build_prop_result_settlement_rule_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["settlement_rule"] is None


def test_build_prop_result_settlement_rule_valid_string():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        settlement_rule="standard_over_under",
    )
    assert result["settlement_rule"] == "standard_over_under"


def test_build_prop_result_settlement_rule_strips_whitespace():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        settlement_rule="  standard_over_under  ",
    )
    assert result["settlement_rule"] == "standard_over_under"


def test_build_prop_result_settlement_rule_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            settlement_rule="",
        )


def test_build_prop_result_settlement_rule_rejects_non_string():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            settlement_rule=99,
        )


# ---------------------------------------------------------------------------
# build_prop_result — start_required validation
# ---------------------------------------------------------------------------

def test_build_prop_result_start_required_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["start_required"] is None


def test_build_prop_result_start_required_true():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        start_required=True,
    )
    assert result["start_required"] is True


def test_build_prop_result_start_required_false():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        start_required=False,
    )
    assert result["start_required"] is False


@pytest.mark.parametrize("value", [1, 0, "true", "false", 1.0, [True]])
def test_build_prop_result_start_required_rejects_non_bool(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            start_required=value,
        )


# ---------------------------------------------------------------------------
# build_prop_result — participation_required validation
# ---------------------------------------------------------------------------

def test_build_prop_result_participation_required_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["participation_required"] is None


def test_build_prop_result_participation_required_true():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        participation_required=True,
    )
    assert result["participation_required"] is True


def test_build_prop_result_participation_required_false():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        participation_required=False,
    )
    assert result["participation_required"] is False


@pytest.mark.parametrize("value", [1, 0, "true", "false"])
def test_build_prop_result_participation_required_rejects_non_bool(value):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            participation_required=value,
        )


# ---------------------------------------------------------------------------
# build_prop_result — void_condition validation
# ---------------------------------------------------------------------------

def test_build_prop_result_void_condition_none():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["void_condition"] is None


def test_build_prop_result_void_condition_valid_string():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        void_condition="player_did_not_start",
    )
    assert result["void_condition"] == "player_did_not_start"


def test_build_prop_result_void_condition_strips_whitespace():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        void_condition="  player_did_not_start  ",
    )
    assert result["void_condition"] == "player_did_not_start"


def test_build_prop_result_void_condition_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            void_condition="",
        )


def test_build_prop_result_void_condition_rejects_non_string():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            void_condition=True,
        )


# ---------------------------------------------------------------------------
# build_prop_result — void_reason validation
# ---------------------------------------------------------------------------

def test_build_prop_result_void_reason_none_for_void():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["void_reason"] is None


def test_build_prop_result_void_reason_valid_for_void():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
        void_reason="player_did_not_participate",
    )
    assert result["void_reason"] == "player_did_not_participate"


def test_build_prop_result_void_reason_strips_whitespace():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
        void_reason="  player_did_not_participate  ",
    )
    assert result["void_reason"] == "player_did_not_participate"


def test_build_prop_result_void_reason_rejects_empty():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="void",
            settled_at="2026-06-30T20:00:00Z",
            void_reason="",
        )


def test_build_prop_result_void_reason_rejects_non_string():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="void",
            settled_at="2026-06-30T20:00:00Z",
            void_reason=42,
        )


@pytest.mark.parametrize("status", ["won", "lost", "push", "pending", "unknown"])
def test_build_prop_result_void_reason_raises_for_non_void_status(status):
    kwargs = dict(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status=status,
        void_reason="some_reason",
    )
    if status in {"won", "lost", "push"}:
        kwargs["settled_at"] = "2026-06-30T20:00:00Z"
    with pytest.raises(PropResultValidationError):
        build_prop_result(**kwargs)


# ---------------------------------------------------------------------------
# build_prop_result — metadata validation
# ---------------------------------------------------------------------------

def test_build_prop_result_metadata_none_returns_empty_dict():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["metadata"] == {}
    assert type(result["metadata"]) is dict


def test_build_prop_result_metadata_passed_dict():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        metadata={"batch_id": "b001"},
    )
    assert result["metadata"] == {"batch_id": "b001"}


def test_build_prop_result_metadata_is_plain_dict():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        metadata={"batch_id": "b001"},
    )
    assert type(result["metadata"]) is dict


def test_build_prop_result_metadata_mutation_isolation():
    caller_meta = {"batch_id": "b001"}
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
        metadata=caller_meta,
    )
    result["metadata"]["extra"] = "injected"
    assert "extra" not in caller_meta


def test_build_prop_result_metadata_rejects_non_dict():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            metadata=["batch_id"],
        )


def test_build_prop_result_metadata_rejects_string():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            metadata="batch_id",
        )


# ---------------------------------------------------------------------------
# build_prop_result — structural invariants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", sorted(FINAL_SETTLEMENT_STATUSES))
def test_build_prop_result_final_status_without_settled_at_raises(status):
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status=status,
            settled_at=None,
        )


@pytest.mark.parametrize("status", sorted(FINAL_SETTLEMENT_STATUSES))
def test_build_prop_result_final_status_with_settled_at_passes(status):
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status=status,
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == status
    assert result["settled_at"] == "2026-06-30T20:00:00Z"


def test_build_prop_result_pending_with_settled_at_raises():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="pending",
            settled_at="2026-06-30T20:00:00Z",
        )


def test_build_prop_result_unknown_with_settled_at_raises():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="unknown",
            settled_at="2026-06-30T20:00:00Z",
        )


def test_build_prop_result_pending_without_settled_at_passes():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="pending",
    )
    assert result["settled_at"] is None


def test_build_prop_result_unknown_without_settled_at_passes():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="unknown",
    )
    assert result["settled_at"] is None


def test_build_prop_result_non_void_with_void_reason_raises():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="won",
            settled_at="2026-06-30T20:00:00Z",
            void_reason="some_reason",
        )


def test_build_prop_result_void_with_void_reason_passes():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
        void_reason="player_did_not_participate",
    )
    assert result["void_reason"] == "player_did_not_participate"


def test_build_prop_result_void_without_void_reason_passes():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        settlement_status="void",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["void_reason"] is None


# ---------------------------------------------------------------------------
# build_prop_result — no automatic settlement inference
# ---------------------------------------------------------------------------

def test_build_prop_result_won_without_actual_value_passes():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        line=2.5,
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "won"
    assert result["actual_value"] is None


def test_build_prop_result_lost_without_actual_value_passes():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        line=2.5,
        settlement_status="lost",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "lost"
    assert result["actual_value"] is None


def test_build_prop_result_line_and_actual_value_coexist_without_inference():
    result = build_prop_result(
        event_id="WC2026_G42",
        market_type="player_points",
        selection="over",
        line=2.5,
        actual_value=1.0,
        settlement_status="won",
        settled_at="2026-06-30T20:00:00Z",
    )
    assert result["settlement_status"] == "won"
    assert result["line"] == pytest.approx(2.5)
    assert result["actual_value"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# build_prop_result — operation order
# ---------------------------------------------------------------------------

def test_build_prop_result_bad_event_id_raises_before_market_type_check():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id=None,
            market_type=None,
            selection="over",
            settlement_status="pending",
        )


def test_build_prop_result_bad_market_type_raises_before_selection_check():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="",
            selection=None,
            settlement_status="pending",
        )


def test_build_prop_result_bad_line_raises_before_status_check():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="graded",
            line=True,
        )


def test_build_prop_result_bad_status_raises_before_invariant_check():
    with pytest.raises(PropResultValidationError):
        build_prop_result(
            event_id="WC2026_G42",
            market_type="player_points",
            selection="over",
            settlement_status="graded",
            settled_at="2026-06-30T20:00:00Z",
        )


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_prop_result_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "prop_result.py"
    tree = ast.parse(src.read_text())
    banned = {
        "sqlite3", "database", "json", "subprocess", "pathlib",
        "odds", "ev", "edge", "candidate_evaluation", "backtest_review",
        "review_taxonomy", "review_notes", "prop_candidate", "odds_snapshot",
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
