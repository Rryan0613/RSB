import ast
import pathlib

import pytest

from candidate_ev import (
    CandidateEVValidationError,
    build_candidate_ev_enrichment,
)
from ev import EVValidationError
from odds import OddsValidationError


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_CANDIDATE = {
    "event_id": "match_001",
    "market_type": "player_shots",
    "selection": "over",
    "line": 2.5,
}

_SNAPSHOT_AMERICAN = {
    "event_id": "match_001",
    "market_type": "player_shots",
    "selection": "over",
    "line": 2.5,
    "odds": 150,
    "odds_format": "american",
}

_SNAPSHOT_DECIMAL = {
    "event_id": "match_001",
    "market_type": "player_shots",
    "selection": "over",
    "line": 2.5,
    "odds": 2.5,
    "odds_format": "decimal",
}


def _call(**overrides):
    kwargs = dict(
        candidate=dict(_CANDIDATE),
        odds_snapshot=dict(_SNAPSHOT_AMERICAN),
        model_probability=0.60,
    )
    kwargs.update(overrides)
    return build_candidate_ev_enrichment(**kwargs)


# ---------------------------------------------------------------------------
# CandidateEVValidationError
# ---------------------------------------------------------------------------

def test_candidate_ev_validation_error_is_value_error():
    assert issubclass(CandidateEVValidationError, ValueError)


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------

def test_return_is_plain_dict():
    assert type(_call()) is dict


def test_return_has_exactly_13_keys():
    assert len(_call()) == 13


def test_return_key_names_and_order():
    expected = [
        "candidate",
        "odds_snapshot",
        "event_id",
        "market_type",
        "selection",
        "line",
        "model_probability",
        "implied_probability",
        "edge",
        "expected_value",
        "minimum_edge",
        "candidate_evaluation",
        "metadata",
    ]
    assert list(_call().keys()) == expected


# ---------------------------------------------------------------------------
# Canonical examples
# ---------------------------------------------------------------------------

def test_canonical_american_example_values():
    # odds=+150: implied = 100/250 = 0.4; decimal = 2.5
    # edge = 0.60 - 0.40 = 0.20; ev = 0.60*2.5 - 1.0 = 0.50
    result = _call(model_probability=0.60)
    assert result["event_id"] == "match_001"
    assert result["market_type"] == "player_shots"
    assert result["selection"] == "over"
    assert result["line"] == pytest.approx(2.5)
    assert result["model_probability"] == pytest.approx(0.60)
    assert result["implied_probability"] == pytest.approx(100.0 / 250.0)
    assert result["edge"] == pytest.approx(0.20)
    assert result["expected_value"] == pytest.approx(0.50)
    assert result["minimum_edge"] == pytest.approx(0.0)
    assert result["candidate_evaluation"]["status"] == "candidate"
    assert result["metadata"] == {}


def test_canonical_decimal_example_values():
    # odds=2.0 decimal: implied = 0.5; decimal_odds = 2.0
    # edge = 0.60 - 0.50 = 0.10; ev = 0.60*2.0 - 1.0 = 0.20
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds"] = 2.0
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["implied_probability"] == pytest.approx(0.50)
    assert result["edge"] == pytest.approx(0.10)
    assert result["expected_value"] == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# candidate validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "string", 42, []])
def test_candidate_not_dict_raises(value):
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=value,
            odds_snapshot=dict(_SNAPSHOT_AMERICAN),
            model_probability=0.60,
        )


@pytest.mark.parametrize("key", ["event_id", "market_type", "selection", "line"])
def test_candidate_missing_required_key_raises(key):
    cand = dict(_CANDIDATE)
    del cand[key]
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=cand,
            odds_snapshot=dict(_SNAPSHOT_AMERICAN),
            model_probability=0.60,
        )


# ---------------------------------------------------------------------------
# odds_snapshot validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "string", 42, []])
def test_odds_snapshot_not_dict_raises(value):
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=value,
            model_probability=0.60,
        )


@pytest.mark.parametrize("key", ["event_id", "market_type", "selection", "line", "odds", "odds_format"])
def test_odds_snapshot_missing_required_key_raises(key):
    snap = dict(_SNAPSHOT_AMERICAN)
    del snap[key]
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


# ---------------------------------------------------------------------------
# Shallow copy behavior
# ---------------------------------------------------------------------------

def test_candidate_shallow_copy_isolates_from_caller_mutation():
    cand = dict(_CANDIDATE)
    result = _call(candidate=cand)
    cand["event_id"] = "mutated"
    assert result["candidate"]["event_id"] == "match_001"


def test_odds_snapshot_shallow_copy_isolates_from_caller_mutation():
    snap = dict(_SNAPSHOT_AMERICAN)
    result = _call(odds_snapshot=snap)
    snap["event_id"] = "mutated"
    assert result["odds_snapshot"]["event_id"] == "match_001"


def test_candidate_in_result_is_not_same_object_as_input():
    cand = dict(_CANDIDATE)
    result = _call(candidate=cand)
    assert result["candidate"] is not cand


def test_odds_snapshot_in_result_is_not_same_object_as_input():
    snap = dict(_SNAPSHOT_AMERICAN)
    result = _call(odds_snapshot=snap)
    assert result["odds_snapshot"] is not snap


# ---------------------------------------------------------------------------
# Identity matching
# ---------------------------------------------------------------------------

def test_identity_match_succeeds():
    result = _call()
    assert result["event_id"] == "match_001"
    assert result["market_type"] == "player_shots"
    assert result["selection"] == "over"


def test_event_id_mismatch_raises():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["event_id"] = "match_002"
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_market_type_mismatch_raises():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["market_type"] = "player_goals"
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_selection_mismatch_raises():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["selection"] = "under"
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


# ---------------------------------------------------------------------------
# Line validation
# ---------------------------------------------------------------------------

def test_candidate_line_none_accepted():
    cand = dict(_CANDIDATE)
    cand["line"] = None
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = None
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] is None


def test_candidate_line_int_converted_to_float():
    cand = dict(_CANDIDATE)
    cand["line"] = 3
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = 3
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(3.0)
    assert type(result["line"]) is float


def test_candidate_line_negative_accepted():
    cand = dict(_CANDIDATE)
    cand["line"] = -1.5
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = -1.5
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(-1.5)


def test_candidate_line_zero_accepted():
    cand = dict(_CANDIDATE)
    cand["line"] = 0.0
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = 0.0
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(0.0)


@pytest.mark.parametrize("value", [True, False])
def test_candidate_line_bool_raises(value):
    cand = dict(_CANDIDATE)
    cand["line"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=cand,
            odds_snapshot=dict(_SNAPSHOT_AMERICAN),
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", ["2.5", [2.5]])
def test_candidate_line_non_numeric_raises(value):
    cand = dict(_CANDIDATE)
    cand["line"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=cand,
            odds_snapshot=dict(_SNAPSHOT_AMERICAN),
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_candidate_line_nan_inf_raises(value):
    cand = dict(_CANDIDATE)
    cand["line"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=cand,
            odds_snapshot=dict(_SNAPSHOT_AMERICAN),
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [True, False])
def test_odds_snapshot_line_bool_raises(value):
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_odds_snapshot_line_nan_inf_raises(value):
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", ["3.0", [3.0]])
def test_odds_snapshot_line_non_numeric_raises(value):
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


# ---------------------------------------------------------------------------
# Line resolution
# ---------------------------------------------------------------------------

def test_line_resolution_candidate_wins_when_not_none():
    cand = dict(_CANDIDATE)
    cand["line"] = 3.5
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = None
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(3.5)


def test_line_resolution_odds_snapshot_used_when_candidate_none():
    cand = dict(_CANDIDATE)
    cand["line"] = None
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = 2.5
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(2.5)


def test_line_resolution_both_none_returns_none():
    cand = dict(_CANDIDATE)
    cand["line"] = None
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = None
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] is None


def test_line_resolution_both_equal_non_none():
    cand = dict(_CANDIDATE)
    cand["line"] = 2.5
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = 2.5
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(2.5)


def test_line_resolution_int_and_float_equal():
    cand = dict(_CANDIDATE)
    cand["line"] = 2
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = 2.0
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["line"] == pytest.approx(2.0)


def test_line_mismatch_raises():
    cand = dict(_CANDIDATE)
    cand["line"] = 2.5
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = 3.0
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=cand,
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_line_returns_float_not_int():
    cand = dict(_CANDIDATE)
    cand["line"] = 2
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["line"] = None
    result = build_candidate_ev_enrichment(
        candidate=cand,
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert type(result["line"]) is float


# ---------------------------------------------------------------------------
# model_probability validation
# ---------------------------------------------------------------------------

def test_model_probability_is_caller_supplied():
    result = _call(model_probability=0.70)
    assert result["model_probability"] == pytest.approx(0.70)


def test_model_probability_returns_float():
    result = _call(model_probability=0.60)
    assert type(result["model_probability"]) is float


def test_model_probability_int_promoted_to_float():
    result = _call(model_probability=1)
    assert result["model_probability"] == pytest.approx(1.0)
    assert type(result["model_probability"]) is float


def test_model_probability_boundary_zero():
    result = _call(model_probability=0.0)
    assert result["model_probability"] == pytest.approx(0.0)


def test_model_probability_boundary_one():
    result = _call(model_probability=1.0)
    assert result["model_probability"] == pytest.approx(1.0)


@pytest.mark.parametrize("value", [True, False])
def test_model_probability_bool_raises(value):
    with pytest.raises(OddsValidationError):
        _call(model_probability=value)


@pytest.mark.parametrize("value", ["0.5", None, [0.5]])
def test_model_probability_non_numeric_raises(value):
    with pytest.raises(OddsValidationError):
        _call(model_probability=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_model_probability_nan_inf_raises(value):
    with pytest.raises(OddsValidationError):
        _call(model_probability=value)


@pytest.mark.parametrize("value", [-0.01, -1.0])
def test_model_probability_below_0_raises(value):
    with pytest.raises(OddsValidationError):
        _call(model_probability=value)


@pytest.mark.parametrize("value", [1.01, 2.0])
def test_model_probability_above_1_raises(value):
    with pytest.raises(OddsValidationError):
        _call(model_probability=value)


# ---------------------------------------------------------------------------
# American odds path
# ---------------------------------------------------------------------------

def test_american_positive_odds_implied_probability():
    # odds=+150: 100/(150+100) = 100/250 = 0.4
    result = _call(model_probability=0.60)
    assert result["implied_probability"] == pytest.approx(100.0 / 250.0)


def test_american_negative_odds_implied_probability():
    # odds=-120: 120/(120+100) = 120/220
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds"] = -120
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["implied_probability"] == pytest.approx(120.0 / 220.0)


def test_american_odds_expected_value_uses_decimal_conversion():
    # odds=+150 → decimal=2.5; ev = 0.60*2.5 - 1.0 = 0.50
    result = _call(model_probability=0.60)
    assert result["expected_value"] == pytest.approx(0.50)


def test_american_odds_edge_calculated():
    # edge = 0.60 - 0.40 = 0.20
    result = _call(model_probability=0.60)
    assert result["edge"] == pytest.approx(0.20)


def test_american_odds_implied_probability_returns_float():
    assert type(_call()["implied_probability"]) is float


def test_american_odds_edge_returns_float():
    assert type(_call()["edge"]) is float


def test_american_odds_expected_value_returns_float():
    assert type(_call()["expected_value"]) is float


# ---------------------------------------------------------------------------
# Decimal odds path
# ---------------------------------------------------------------------------

def test_decimal_odds_implied_probability():
    # odds=2.5 decimal: 1/2.5 = 0.4
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=dict(_SNAPSHOT_DECIMAL),
        model_probability=0.60,
    )
    assert result["implied_probability"] == pytest.approx(1.0 / 2.5)


def test_decimal_odds_expected_value():
    # odds=2.5 decimal; ev = 0.60*2.5 - 1.0 = 0.50
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=dict(_SNAPSHOT_DECIMAL),
        model_probability=0.60,
    )
    assert result["expected_value"] == pytest.approx(0.50)


def test_decimal_odds_edge_calculated():
    # edge = 0.60 - 0.40 = 0.20
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=dict(_SNAPSHOT_DECIMAL),
        model_probability=0.60,
    )
    assert result["edge"] == pytest.approx(0.20)


def test_decimal_odds_implied_probability_returns_float():
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=dict(_SNAPSHOT_DECIMAL),
        model_probability=0.60,
    )
    assert type(result["implied_probability"]) is float


def test_decimal_odds_two_point_zero():
    # odds=2.0 decimal: implied = 0.5; ev = 0.60*2.0-1.0 = 0.20; edge = 0.10
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds"] = 2.0
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["implied_probability"] == pytest.approx(0.50)
    assert result["expected_value"] == pytest.approx(0.20)
    assert result["edge"] == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Invalid odds_format
# ---------------------------------------------------------------------------

def test_invalid_odds_format_string_raises():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds_format"] = "fractional"
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_empty_odds_format_raises():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds_format"] = ""
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [None, 42, ["american"]])
def test_odds_format_non_string_raises(value):
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds_format"] = value
    with pytest.raises(CandidateEVValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_odds_format_case_insensitive_american():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds_format"] = "American"
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["implied_probability"] == pytest.approx(100.0 / 250.0)


def test_odds_format_case_insensitive_decimal():
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds_format"] = "DECIMAL"
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=snap,
        model_probability=0.60,
    )
    assert result["implied_probability"] == pytest.approx(1.0 / 2.5)


# ---------------------------------------------------------------------------
# Invalid odds values
# ---------------------------------------------------------------------------

def test_american_odds_zero_raises():
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds"] = 0
    with pytest.raises(OddsValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [True, False])
def test_american_odds_bool_raises(value):
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds"] = value
    with pytest.raises(OddsValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_american_odds_nan_inf_raises(value):
    snap = dict(_SNAPSHOT_AMERICAN)
    snap["odds"] = value
    with pytest.raises(OddsValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_decimal_odds_exactly_one_raises():
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds"] = 1.0
    with pytest.raises(OddsValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


def test_decimal_odds_below_one_raises():
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds"] = 0.5
    with pytest.raises(OddsValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


@pytest.mark.parametrize("value", [True, False])
def test_decimal_odds_bool_raises(value):
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds"] = value
    with pytest.raises(OddsValidationError):
        build_candidate_ev_enrichment(
            candidate=dict(_CANDIDATE),
            odds_snapshot=snap,
            model_probability=0.60,
        )


# ---------------------------------------------------------------------------
# minimum_edge validation
# ---------------------------------------------------------------------------

def test_minimum_edge_default_is_zero():
    result = _call()
    assert result["minimum_edge"] == pytest.approx(0.0)


def test_minimum_edge_boundary_zero():
    result = _call(minimum_edge=0.0)
    assert result["minimum_edge"] == pytest.approx(0.0)


def test_minimum_edge_boundary_one():
    result = _call(minimum_edge=1.0)
    assert result["minimum_edge"] == pytest.approx(1.0)


def test_minimum_edge_int_promoted_to_float():
    result = _call(minimum_edge=0)
    assert type(result["minimum_edge"]) is float


def test_minimum_edge_returns_float():
    result = _call(minimum_edge=0.05)
    assert type(result["minimum_edge"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_minimum_edge_bool_raises(value):
    with pytest.raises(CandidateEVValidationError):
        _call(minimum_edge=value)


@pytest.mark.parametrize("value", ["0.05", None, [0.05]])
def test_minimum_edge_non_numeric_raises(value):
    with pytest.raises(CandidateEVValidationError):
        _call(minimum_edge=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_minimum_edge_nan_inf_raises(value):
    with pytest.raises(CandidateEVValidationError):
        _call(minimum_edge=value)


def test_minimum_edge_below_zero_raises():
    with pytest.raises(CandidateEVValidationError):
        _call(minimum_edge=-0.01)


def test_minimum_edge_above_one_raises():
    with pytest.raises(CandidateEVValidationError):
        _call(minimum_edge=1.01)


# ---------------------------------------------------------------------------
# candidate_evaluation status and pass_reasons
# ---------------------------------------------------------------------------

def test_candidate_eval_status_candidate_when_edge_exceeds_minimum():
    # edge=0.20, minimum_edge=0.10 → candidate
    result = _call(model_probability=0.60, minimum_edge=0.10)
    assert result["candidate_evaluation"]["status"] == "candidate"
    assert result["candidate_evaluation"]["pass_reasons"] == []


def test_candidate_eval_status_rejected_when_edge_below_minimum():
    # edge=0.20, minimum_edge=0.25 → rejected
    result = _call(model_probability=0.60, minimum_edge=0.25)
    assert result["candidate_evaluation"]["status"] == "rejected"
    assert result["candidate_evaluation"]["pass_reasons"] == ["edge_below_minimum"]


def test_candidate_eval_status_candidate_at_exact_boundary():
    # model_probability=0.5, decimal odds=2.0 → implied=0.5, edge=0.0 exactly
    # minimum_edge=0.0 → 0.0 >= 0.0 → candidate
    snap = dict(_SNAPSHOT_DECIMAL)
    snap["odds"] = 2.0
    result = build_candidate_ev_enrichment(
        candidate=dict(_CANDIDATE),
        odds_snapshot=snap,
        model_probability=0.5,
        minimum_edge=0.0,
    )
    assert result["candidate_evaluation"]["status"] == "candidate"
    assert result["candidate_evaluation"]["pass_reasons"] == []


def test_candidate_eval_status_candidate_with_default_zero_minimum():
    # any positive edge → candidate when minimum_edge=0.0 (default)
    result = _call(model_probability=0.60)
    assert result["candidate_evaluation"]["status"] == "candidate"


def test_candidate_eval_is_plain_dict():
    assert type(_call()["candidate_evaluation"]) is dict


def test_candidate_eval_has_expected_keys():
    result = _call()
    assert set(result["candidate_evaluation"].keys()) == {"status", "edge", "pass_reasons"}


# ---------------------------------------------------------------------------
# candidate_evaluation contains computed edge
# ---------------------------------------------------------------------------

def test_candidate_eval_edge_matches_computed_edge():
    result = _call(model_probability=0.60)
    assert result["candidate_evaluation"]["edge"] == pytest.approx(result["edge"])


def test_candidate_eval_edge_is_float():
    result = _call(model_probability=0.60)
    assert type(result["candidate_evaluation"]["edge"]) is float


def test_candidate_eval_edge_present_when_rejected():
    result = _call(model_probability=0.60, minimum_edge=0.25)
    assert result["candidate_evaluation"]["edge"] == pytest.approx(result["edge"])


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

def test_metadata_default_is_empty_dict():
    result = _call()
    assert result["metadata"] == {}


def test_metadata_passed_dict_returned():
    result = _call(metadata={"source": "test"})
    assert result["metadata"] == {"source": "test"}


def test_metadata_is_plain_dict():
    result = _call(metadata={"k": "v"})
    assert type(result["metadata"]) is dict


def test_metadata_shallow_copy_isolates_from_caller_mutation():
    meta = {"k": "v"}
    result = _call(metadata=meta)
    meta["k"] = "mutated"
    assert result["metadata"]["k"] == "v"


def test_metadata_none_becomes_empty_dict():
    result = _call(metadata=None)
    assert result["metadata"] == {}


@pytest.mark.parametrize("value", ["string", 42, [{"k": "v"}]])
def test_metadata_non_dict_raises(value):
    with pytest.raises(CandidateEVValidationError):
        _call(metadata=value)


# ---------------------------------------------------------------------------
# Banned imports
# ---------------------------------------------------------------------------

def test_candidate_ev_has_no_banned_imports():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "candidate_ev.py"
    tree = ast.parse(src.read_text())
    banned = {
        "sqlite3", "database", "json", "subprocess", "pathlib",
        "prop_candidate", "odds_snapshot", "prop_result",
        "review_taxonomy", "review_notes", "backtest_review", "stage_market",
        "run_slate", "simulator", "config_validation",
        "market_selector", "slate_odds", "model", "features", "historical_replay",
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
