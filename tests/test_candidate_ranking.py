import ast
import pathlib

import pytest

from candidate_evaluation import CandidateEvaluationValidationError, build_candidate_evaluation
from candidate_ranking import (
    CandidateRankingValidationError,
    rank_candidate_ev_enrichments,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_ev(
    *,
    event_id="match_001",
    market_type="player_shots",
    selection="over",
    line=2.5,
    edge=0.10,
    expected_value=0.20,
    status="candidate",
    pass_reasons=None,
    eval_edge="__default__",
):
    if eval_edge == "__default__":
        eval_edge = edge
    if status == "candidate":
        candidate_evaluation = build_candidate_evaluation(
            status, edge=eval_edge, pass_reasons=[]
        )
    else:
        candidate_evaluation = build_candidate_evaluation(
            status, edge=eval_edge, pass_reasons=pass_reasons or ["edge_below_minimum"]
        )
    return {
        "event_id": event_id,
        "market_type": market_type,
        "selection": selection,
        "line": line,
        "edge": edge,
        "expected_value": expected_value,
        "candidate_evaluation": candidate_evaluation,
    }


def _rank(candidate_evs, **overrides):
    return rank_candidate_ev_enrichments(candidate_evs, **overrides)


# ---------------------------------------------------------------------------
# CandidateRankingValidationError
# ---------------------------------------------------------------------------

def test_candidate_ranking_validation_error_is_value_error():
    assert issubclass(CandidateRankingValidationError, ValueError)


# ---------------------------------------------------------------------------
# candidate_evs top-level validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "string", 42, {}, ()])
def test_candidate_evs_non_list_or_empty_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank(value)


def test_candidate_evs_empty_list_raises():
    with pytest.raises(CandidateRankingValidationError):
        _rank([])


def test_candidate_evs_tuple_accepted():
    result = _rank((_make_ev(),))
    assert len(result) == 1


@pytest.mark.parametrize("value", [None, "string", 42, [1, 2]])
def test_candidate_ev_item_not_dict_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([value])


# ---------------------------------------------------------------------------
# missing required keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    ["event_id", "market_type", "selection", "line", "edge", "expected_value", "candidate_evaluation"],
)
def test_missing_required_key_raises(key):
    item = _make_ev()
    del item[key]
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


# ---------------------------------------------------------------------------
# line validation
# ---------------------------------------------------------------------------

def test_line_none_accepted():
    result = _rank([_make_ev(line=None)])
    assert result[0]["line"] is None


def test_line_int_converted_to_float():
    result = _rank([_make_ev(line=3)])
    assert result[0]["line"] == pytest.approx(3.0)
    assert type(result[0]["line"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_line_bool_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev(line=value)])


@pytest.mark.parametrize("value", ["2.5", [2.5]])
def test_line_non_numeric_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev(line=value)])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_line_nan_inf_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev(line=value)])


# ---------------------------------------------------------------------------
# edge / expected_value validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [True, False])
def test_edge_bool_raises(value):
    item = _make_ev()
    item["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", ["0.1", None, [0.1]])
def test_edge_non_numeric_raises(value):
    item = _make_ev()
    item["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_edge_nan_inf_raises(value):
    item = _make_ev()
    item["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", [True, False])
def test_expected_value_bool_raises(value):
    item = _make_ev()
    item["expected_value"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", ["0.2", None, [0.2]])
def test_expected_value_non_numeric_raises(value):
    item = _make_ev()
    item["expected_value"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_expected_value_nan_inf_raises(value):
    item = _make_ev()
    item["expected_value"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


def test_edge_and_expected_value_int_converted_to_float():
    item = _make_ev(edge=0, expected_value=0)
    result = _rank([item])
    assert type(result[0]["edge"]) is float
    assert type(result[0]["expected_value"]) is float


# ---------------------------------------------------------------------------
# candidate_evaluation shape validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "string", 42, []])
def test_candidate_evaluation_not_dict_raises(value):
    item = _make_ev()
    item["candidate_evaluation"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("key", ["status", "edge", "pass_reasons"])
def test_candidate_evaluation_missing_key_raises(key):
    item = _make_ev()
    del item["candidate_evaluation"][key]
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


def test_candidate_evaluation_invalid_status_raises():
    item = _make_ev()
    item["candidate_evaluation"]["status"] = "not_a_real_status"
    with pytest.raises(CandidateEvaluationValidationError):
        _rank([item])


def test_candidate_evaluation_invalid_pass_reasons_raises():
    item = _make_ev()
    item["candidate_evaluation"]["pass_reasons"] = ["not_a_real_reason"]
    with pytest.raises(CandidateEvaluationValidationError):
        _rank([item])


def test_candidate_evaluation_embedded_edge_none_allowed():
    item = _make_ev(eval_edge=None)
    result = _rank([item])
    assert result[0]["ranking_status"] == "ranked"


@pytest.mark.parametrize("value", [True, False])
def test_candidate_evaluation_embedded_edge_bool_raises(value):
    item = _make_ev()
    item["candidate_evaluation"]["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", ["0.1", [0.1]])
def test_candidate_evaluation_embedded_edge_non_numeric_raises(value):
    item = _make_ev()
    item["candidate_evaluation"]["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_candidate_evaluation_embedded_edge_nan_inf_raises(value):
    item = _make_ev()
    item["candidate_evaluation"]["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", [-1.01, 1.01])
def test_candidate_evaluation_embedded_edge_out_of_range_raises(value):
    item = _make_ev()
    item["candidate_evaluation"]["edge"] = value
    with pytest.raises(CandidateRankingValidationError):
        _rank([item])


@pytest.mark.parametrize("value", [-1.0, 1.0])
def test_candidate_evaluation_embedded_edge_boundary_accepted(value):
    item = _make_ev()
    item["candidate_evaluation"]["edge"] = value
    result = _rank([item])
    assert result[0]["ranking_status"] == "ranked"


def test_candidate_evaluation_embedded_edge_mismatch_with_top_level_edge_allowed():
    # No equality requirement between embedded and top-level edge in this version.
    item = _make_ev(edge=0.20, eval_edge=0.05)
    result = _rank([item])
    assert result[0]["edge"] == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# ranking by expected_value
# ---------------------------------------------------------------------------

def test_ranking_sorts_by_expected_value_descending():
    items = [
        _make_ev(event_id="low", expected_value=0.10),
        _make_ev(event_id="high", expected_value=0.50),
        _make_ev(event_id="mid", expected_value=0.30),
    ]
    result = _rank(items)
    assert [r["event_id"] for r in result] == ["high", "mid", "low"]
    assert [r["rank"] for r in result] == [1, 2, 3]


def test_ranking_status_ranked_for_all_candidates():
    result = _rank([_make_ev()])
    assert result[0]["ranking_status"] == "ranked"
    assert result[0]["rank"] == 1


# ---------------------------------------------------------------------------
# edge tie-breaker
# ---------------------------------------------------------------------------

def test_edge_tie_breaker():
    items = [
        _make_ev(event_id="lower_edge", expected_value=0.20, edge=0.05),
        _make_ev(event_id="higher_edge", expected_value=0.20, edge=0.15),
    ]
    result = _rank(items)
    assert [r["event_id"] for r in result] == ["higher_edge", "lower_edge"]


# ---------------------------------------------------------------------------
# data_quality_score tie-breaker
# ---------------------------------------------------------------------------

def test_data_quality_score_tie_breaker():
    items = [
        _make_ev(event_id="low_dq", expected_value=0.20, edge=0.10),
        _make_ev(event_id="high_dq", expected_value=0.20, edge=0.10),
    ]
    result = _rank(items, data_quality_scores=[0.2, 0.9])
    assert [r["event_id"] for r in result] == ["high_dq", "low_dq"]


def test_data_quality_score_none_sorts_last():
    items = [
        _make_ev(event_id="has_score", expected_value=0.20, edge=0.10),
        _make_ev(event_id="no_score", expected_value=0.20, edge=0.10),
    ]
    result = _rank(items, data_quality_scores=[None, 0.1])
    assert [r["event_id"] for r in result] == ["no_score", "has_score"]


# ---------------------------------------------------------------------------
# confidence_score tie-breaker
# ---------------------------------------------------------------------------

def test_confidence_score_tie_breaker():
    items = [
        _make_ev(event_id="low_conf", expected_value=0.20, edge=0.10),
        _make_ev(event_id="high_conf", expected_value=0.20, edge=0.10),
    ]
    result = _rank(
        items,
        data_quality_scores=[0.5, 0.5],
        confidence_scores=[0.2, 0.8],
    )
    assert [r["event_id"] for r in result] == ["high_conf", "low_conf"]


# ---------------------------------------------------------------------------
# calibration_score tie-breaker
# ---------------------------------------------------------------------------

def test_calibration_score_tie_breaker():
    items = [
        _make_ev(event_id="low_calib", expected_value=0.20, edge=0.10),
        _make_ev(event_id="high_calib", expected_value=0.20, edge=0.10),
    ]
    result = _rank(
        items,
        data_quality_scores=[0.5, 0.5],
        confidence_scores=[0.5, 0.5],
        calibration_scores=[0.3, 0.7],
    )
    assert [r["event_id"] for r in result] == ["high_calib", "low_calib"]


# ---------------------------------------------------------------------------
# original_index stable tie-breaker
# ---------------------------------------------------------------------------

def test_original_index_stable_tie_breaker_when_all_equal():
    items = [
        _make_ev(event_id="first", expected_value=0.20, edge=0.10),
        _make_ev(event_id="second", expected_value=0.20, edge=0.10),
        _make_ev(event_id="third", expected_value=0.20, edge=0.10),
    ]
    result = _rank(items)
    assert [r["event_id"] for r in result] == ["first", "second", "third"]
    assert [r["original_index"] for r in result] == [0, 1, 2]


# ---------------------------------------------------------------------------
# exclusion of rejected / not_evaluable records
# ---------------------------------------------------------------------------

def test_rejected_record_excluded_with_rank_none():
    result = _rank([_make_ev(status="rejected")])
    assert result[0]["ranking_status"] == "excluded"
    assert result[0]["rank"] is None


def test_not_evaluable_record_excluded_with_rank_none():
    result = _rank(
        [_make_ev(status="not_evaluable", pass_reasons=["missing_model_probability"])]
    )
    assert result[0]["ranking_status"] == "excluded"
    assert result[0]["rank"] is None


def test_excluded_records_appear_after_ranked_records():
    items = [
        _make_ev(event_id="rejected_first", status="rejected"),
        _make_ev(event_id="candidate_second", expected_value=0.50),
    ]
    result = _rank(items)
    assert [r["ranking_status"] for r in result] == ["ranked", "excluded"]
    assert result[0]["event_id"] == "candidate_second"
    assert result[1]["event_id"] == "rejected_first"


def test_excluded_records_ordered_by_original_index():
    items = [
        _make_ev(event_id="rejected_a", status="rejected"),
        _make_ev(event_id="candidate", expected_value=0.50),
        _make_ev(event_id="rejected_b", status="rejected"),
    ]
    result = _rank(items)
    excluded = [r for r in result if r["ranking_status"] == "excluded"]
    assert [r["event_id"] for r in excluded] == ["rejected_a", "rejected_b"]
    assert [r["original_index"] for r in excluded] == [0, 2]


# ---------------------------------------------------------------------------
# optional score list length validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "arg_name",
    ["data_quality_scores", "confidence_scores", "calibration_scores"],
)
def test_score_list_wrong_length_raises(arg_name):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev(), _make_ev(event_id="second")], **{arg_name: [0.5]})


@pytest.mark.parametrize(
    "arg_name",
    ["data_quality_scores", "confidence_scores", "calibration_scores"],
)
def test_score_list_non_list_or_tuple_raises(arg_name):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev()], **{arg_name: "not_a_list"})


@pytest.mark.parametrize(
    "arg_name",
    ["data_quality_scores", "confidence_scores", "calibration_scores"],
)
def test_score_list_tuple_accepted(arg_name):
    result = _rank([_make_ev()], **{arg_name: (0.5,)})
    assert len(result) == 1


# ---------------------------------------------------------------------------
# optional score item validation
# ---------------------------------------------------------------------------

def test_score_item_none_allowed():
    result = _rank([_make_ev()], data_quality_scores=[None])
    assert result[0]["data_quality_score"] is None


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_score_item_boundary_accepted(value):
    result = _rank([_make_ev()], data_quality_scores=[value])
    assert result[0]["data_quality_score"] == pytest.approx(value)


def test_score_item_int_converted_to_float():
    result = _rank([_make_ev()], data_quality_scores=[1])
    assert type(result[0]["data_quality_score"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_score_item_bool_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev()], data_quality_scores=[value])


@pytest.mark.parametrize("value", ["0.5", [0.5]])
def test_score_item_non_numeric_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev()], data_quality_scores=[value])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_score_item_nan_inf_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev()], data_quality_scores=[value])


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_score_item_out_of_range_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev()], data_quality_scores=[value])


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

def test_metadata_default_is_empty_dict():
    result = _rank([_make_ev()])
    assert result[0]["metadata"] == {}


def test_metadata_provided_dict_attached_to_every_record():
    items = [_make_ev(event_id="a"), _make_ev(event_id="b", expected_value=0.50)]
    result = _rank(items, metadata={"run_id": "abc"})
    assert result[0]["metadata"] == {"run_id": "abc"}
    assert result[1]["metadata"] == {"run_id": "abc"}


def test_metadata_is_independent_copy_per_record():
    items = [_make_ev(event_id="a"), _make_ev(event_id="b", expected_value=0.50)]
    result = _rank(items, metadata={"k": "v"})
    result[0]["metadata"]["k"] = "mutated"
    assert result[1]["metadata"]["k"] == "v"


def test_metadata_shallow_copy_isolates_from_caller_mutation():
    meta = {"k": "v"}
    result = _rank([_make_ev()], metadata=meta)
    meta["k"] = "mutated"
    assert result[0]["metadata"]["k"] == "v"


def test_metadata_none_becomes_empty_dict():
    result = _rank([_make_ev()], metadata=None)
    assert result[0]["metadata"] == {}


@pytest.mark.parametrize("value", ["string", 42, [{"k": "v"}]])
def test_metadata_non_dict_raises(value):
    with pytest.raises(CandidateRankingValidationError):
        _rank([_make_ev()], metadata=value)


def test_embedded_candidate_ev_metadata_not_used_as_ranking_metadata():
    item = _make_ev()
    item["metadata"] = {"embedded": True}
    result = _rank([item], metadata={"run": "top_level"})
    assert result[0]["metadata"] == {"run": "top_level"}


# ---------------------------------------------------------------------------
# caller input isolation
# ---------------------------------------------------------------------------

def test_candidate_ev_shallow_copy_isolates_from_caller_mutation():
    item = _make_ev()
    result = _rank([item])
    item["event_id"] = "mutated"
    assert result[0]["candidate_ev"]["event_id"] == "match_001"


def test_candidate_ev_in_result_is_not_same_object_as_input():
    item = _make_ev()
    result = _rank([item])
    assert result[0]["candidate_ev"] is not item


def test_candidate_evs_input_list_not_mutated():
    items = [_make_ev()]
    original_len = len(items)
    _rank(items)
    assert len(items) == original_len


# ---------------------------------------------------------------------------
# return shape
# ---------------------------------------------------------------------------

def test_return_is_list():
    assert type(_rank([_make_ev()])) is list


def test_return_records_are_plain_dicts():
    result = _rank([_make_ev()])
    assert type(result[0]) is dict


def test_return_has_exactly_16_keys():
    result = _rank([_make_ev()])
    assert len(result[0]) == 16


def test_return_key_order():
    expected = [
        "rank",
        "ranking_status",
        "candidate_ev",
        "event_id",
        "market_type",
        "selection",
        "line",
        "edge",
        "expected_value",
        "candidate_status",
        "pass_reasons",
        "data_quality_score",
        "confidence_score",
        "calibration_score",
        "original_index",
        "metadata",
    ]
    result = _rank([_make_ev()])
    assert list(result[0].keys()) == expected


# ---------------------------------------------------------------------------
# no rounding
# ---------------------------------------------------------------------------

def test_no_rounding_of_edge_and_expected_value():
    item = _make_ev(edge=0.123456789, expected_value=0.987654321, eval_edge=0.123456789)
    result = _rank([item])
    assert result[0]["edge"] == pytest.approx(0.123456789)
    assert result[0]["expected_value"] == pytest.approx(0.987654321)


def test_no_rounding_of_scores():
    result = _rank([_make_ev()], data_quality_scores=[0.123456789])
    assert result[0]["data_quality_score"] == pytest.approx(0.123456789)


# ---------------------------------------------------------------------------
# Banned imports
# ---------------------------------------------------------------------------

def test_candidate_ranking_has_no_banned_imports():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "candidate_ranking.py"
    tree = ast.parse(src.read_text())
    banned = {
        "sqlite3", "database", "json", "subprocess", "pathlib",
        "candidate_ev", "prop_candidate", "odds_snapshot", "prop_result",
        "review_taxonomy", "review_notes", "backtest_review", "stage_market",
        "run_slate", "simulator", "config_validation",
        "market_selector", "slate_odds", "model", "features", "historical_replay",
        "odds", "edge", "ev",
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
