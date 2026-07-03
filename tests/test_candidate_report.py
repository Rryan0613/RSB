import pytest

from candidate_ev import build_candidate_ev_enrichment
from candidate_evaluation import (
    CandidateEvaluationValidationError,
    build_candidate_evaluation,
)
from candidate_ranking import rank_candidate_ev_enrichments
from candidate_report import (
    CandidateReportValidationError,
    build_candidate_report,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_ranked_record(
    *,
    rank=1,
    ranking_status="ranked",
    candidate_status="candidate",
    pass_reasons=None,
    original_index=0,
    **extra,
):
    record = {
        "rank": rank,
        "ranking_status": ranking_status,
        "candidate_status": candidate_status,
        "pass_reasons": pass_reasons if pass_reasons is not None else [],
        "original_index": original_index,
    }
    record.update(extra)
    return record


def _make_excluded_record(*, original_index=0, pass_reasons=None, **extra):
    return _make_ranked_record(
        rank=None,
        ranking_status="excluded",
        candidate_status="rejected",
        pass_reasons=pass_reasons if pass_reasons is not None else ["edge_below_minimum"],
        original_index=original_index,
        **extra,
    )


def _report(ranked_candidates, **overrides):
    return build_candidate_report(ranked_candidates, **overrides)


# ---------------------------------------------------------------------------
# CandidateReportValidationError
# ---------------------------------------------------------------------------

def test_candidate_report_validation_error_is_value_error():
    assert issubclass(CandidateReportValidationError, ValueError)


# ---------------------------------------------------------------------------
# ranked_candidates top-level validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "string", 42, {}])
def test_non_list_or_tuple_raises(value):
    with pytest.raises(CandidateReportValidationError):
        _report(value)


def test_empty_list_returns_valid_all_zero_report():
    result = _report([])
    assert result["total_records"] == 0
    assert result["ranked_count"] == 0
    assert result["excluded_count"] == 0
    assert result["top_ranked_candidates"] == []
    assert result["excluded_candidates"] == []
    assert result["pass_reason_counts"] == {}
    assert result["ranking_status_counts"] == {"ranked": 0, "excluded": 0}
    assert result["metadata"] == {}


def test_tuple_input_accepted():
    result = _report((_make_ranked_record(),))
    assert result["total_records"] == 1
    assert result["ranked_count"] == 1


def test_non_dict_element_raises_with_index_in_message():
    with pytest.raises(CandidateReportValidationError, match=r"\[0\]"):
        _report(["not_a_dict"])


def test_non_dict_element_at_later_index_raises_with_correct_index():
    with pytest.raises(CandidateReportValidationError, match=r"\[1\]"):
        _report([_make_ranked_record(), 42])


# ---------------------------------------------------------------------------
# Required key validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "missing_key",
    ["rank", "ranking_status", "candidate_status", "pass_reasons", "original_index"],
)
def test_missing_required_key_raises(missing_key):
    record = _make_ranked_record()
    del record[missing_key]
    with pytest.raises(CandidateReportValidationError):
        _report([record])


# ---------------------------------------------------------------------------
# ranking_status validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["invalid", "", "RANKED", None, 1])
def test_invalid_ranking_status_raises(value):
    record = _make_ranked_record(ranking_status=value)
    with pytest.raises(CandidateReportValidationError):
        _report([record])


# ---------------------------------------------------------------------------
# ranked-record rank validation
# ---------------------------------------------------------------------------

def test_ranked_record_with_rank_none_raises():
    record = _make_ranked_record(rank=None)
    with pytest.raises(CandidateReportValidationError):
        _report([record])


def test_ranked_record_with_bool_rank_raises():
    record = _make_ranked_record(rank=True)
    with pytest.raises(CandidateReportValidationError):
        _report([record])


def test_ranked_record_with_zero_rank_raises():
    record = _make_ranked_record(rank=0)
    with pytest.raises(CandidateReportValidationError):
        _report([record])


def test_ranked_record_with_negative_rank_raises():
    record = _make_ranked_record(rank=-1)
    with pytest.raises(CandidateReportValidationError):
        _report([record])


def test_ranked_record_with_non_int_rank_raises():
    record = _make_ranked_record(rank=1.5)
    with pytest.raises(CandidateReportValidationError):
        _report([record])


def test_ranked_records_out_of_order_raises():
    records = [
        _make_ranked_record(rank=2, original_index=0),
        _make_ranked_record(rank=1, original_index=1),
    ]
    with pytest.raises(CandidateReportValidationError):
        _report(records)


def test_ranked_records_with_gap_in_sequence_raises():
    records = [
        _make_ranked_record(rank=1, original_index=0),
        _make_ranked_record(rank=3, original_index=1),
    ]
    with pytest.raises(CandidateReportValidationError):
        _report(records)


def test_ranked_records_valid_sequential_order_accepted():
    records = [
        _make_ranked_record(rank=1, original_index=0),
        _make_ranked_record(rank=2, original_index=1),
        _make_ranked_record(rank=3, original_index=2),
    ]
    result = _report(records)
    assert result["ranked_count"] == 3


# ---------------------------------------------------------------------------
# excluded-record rank validation
# ---------------------------------------------------------------------------

def test_excluded_record_with_non_none_rank_raises():
    record = _make_excluded_record(original_index=0)
    record["rank"] = 1
    with pytest.raises(CandidateReportValidationError):
        _report([record])


# ---------------------------------------------------------------------------
# Mixed ranked/excluded counts
# ---------------------------------------------------------------------------

def test_mixed_ranked_and_excluded_returns_correct_counts():
    records = [
        _make_ranked_record(rank=1, original_index=0),
        _make_excluded_record(original_index=1),
        _make_ranked_record(rank=2, original_index=2),
        _make_excluded_record(original_index=3),
    ]
    result = _report(records)
    assert result["total_records"] == 4
    assert result["ranked_count"] == 2
    assert result["excluded_count"] == 2
    assert result["ranking_status_counts"] == {"ranked": 2, "excluded": 2}


# ---------------------------------------------------------------------------
# top_ranked_candidates / excluded_candidates ordering
# ---------------------------------------------------------------------------

def test_top_ranked_candidates_includes_ranked_only_and_preserves_rank_order():
    records = [
        _make_ranked_record(rank=1, original_index=0, event_id="a"),
        _make_excluded_record(original_index=1, event_id="b"),
        _make_ranked_record(rank=2, original_index=2, event_id="c"),
    ]
    result = _report(records)
    event_ids = [r["event_id"] for r in result["top_ranked_candidates"]]
    assert event_ids == ["a", "c"]


def test_excluded_candidates_includes_excluded_only_and_preserves_input_order():
    records = [
        _make_excluded_record(original_index=0, event_id="x"),
        _make_ranked_record(rank=1, original_index=1, event_id="y"),
        _make_excluded_record(original_index=2, event_id="z"),
    ]
    result = _report(records)
    event_ids = [r["event_id"] for r in result["excluded_candidates"]]
    assert event_ids == ["x", "z"]


# ---------------------------------------------------------------------------
# top_n behavior
# ---------------------------------------------------------------------------

def test_top_n_zero_returns_empty_top_ranked_candidates():
    records = [_make_ranked_record(rank=1, original_index=0)]
    result = _report(records, top_n=0)
    assert result["top_ranked_candidates"] == []
    assert result["top_n"] == 0


def test_top_n_smaller_than_ranked_count_truncates():
    records = [
        _make_ranked_record(rank=1, original_index=0, event_id="a"),
        _make_ranked_record(rank=2, original_index=1, event_id="b"),
        _make_ranked_record(rank=3, original_index=2, event_id="c"),
    ]
    result = _report(records, top_n=2)
    event_ids = [r["event_id"] for r in result["top_ranked_candidates"]]
    assert event_ids == ["a", "b"]


def test_top_n_larger_than_ranked_count_returns_all():
    records = [
        _make_ranked_record(rank=1, original_index=0, event_id="a"),
        _make_ranked_record(rank=2, original_index=1, event_id="b"),
    ]
    result = _report(records, top_n=10)
    event_ids = [r["event_id"] for r in result["top_ranked_candidates"]]
    assert event_ids == ["a", "b"]


def test_top_n_none_returns_all_ranked():
    records = [
        _make_ranked_record(rank=1, original_index=0),
        _make_ranked_record(rank=2, original_index=1),
    ]
    result = _report(records, top_n=None)
    assert len(result["top_ranked_candidates"]) == 2
    assert result["top_n"] is None


@pytest.mark.parametrize("value", [True, False, -1, 1.5, "2"])
def test_invalid_top_n_raises(value):
    records = [_make_ranked_record(rank=1, original_index=0)]
    with pytest.raises(CandidateReportValidationError):
        _report(records, top_n=value)


# ---------------------------------------------------------------------------
# pass_reason_counts
# ---------------------------------------------------------------------------

def test_pass_reason_counts_tallies_repeated_and_overlapping_reasons():
    records = [
        _make_excluded_record(original_index=0, pass_reasons=["edge_below_minimum"]),
        _make_excluded_record(
            original_index=1,
            pass_reasons=["edge_below_minimum", "data_quality_concern"],
        ),
        _make_ranked_record(rank=1, original_index=2, pass_reasons=[]),
    ]
    result = _report(records)
    assert result["pass_reason_counts"] == {
        "edge_below_minimum": 2,
        "data_quality_concern": 1,
    }


def test_invalid_pass_reasons_raise_via_validate_pass_reasons():
    record = _make_ranked_record(pass_reasons=["not_a_real_reason"])
    with pytest.raises(CandidateEvaluationValidationError):
        _report([record])


# ---------------------------------------------------------------------------
# ranking_status_counts
# ---------------------------------------------------------------------------

def test_ranking_status_counts_sums_to_total_records():
    records = [
        _make_ranked_record(rank=1, original_index=0),
        _make_ranked_record(rank=2, original_index=1),
        _make_excluded_record(original_index=2),
    ]
    result = _report(records)
    counts = result["ranking_status_counts"]
    assert counts["ranked"] + counts["excluded"] == result["total_records"]


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

def test_metadata_defaults_to_empty_dict():
    result = _report([])
    assert result["metadata"] == {}


def test_non_dict_metadata_raises():
    with pytest.raises(CandidateReportValidationError):
        _report([], metadata="not_a_dict")


def test_metadata_is_shallow_copied():
    original = {"source": "test"}
    result = _report([], metadata=original)
    result["metadata"]["source"] = "mutated"
    assert original["source"] == "test"

    original["source"] = "mutated_after"
    assert result["metadata"]["source"] == "mutated"


# ---------------------------------------------------------------------------
# Output records are copies
# ---------------------------------------------------------------------------

def test_output_ranked_record_is_a_copy_not_same_object():
    record = _make_ranked_record(rank=1, original_index=0)
    result = _report([record])
    output_record = result["top_ranked_candidates"][0]
    assert output_record is not record
    output_record["event_id"] = "mutated"
    assert "event_id" not in record


def test_output_excluded_record_is_a_copy_not_same_object():
    record = _make_excluded_record(original_index=0)
    result = _report([record])
    output_record = result["excluded_candidates"][0]
    assert output_record is not record
    output_record["event_id"] = "mutated"
    assert "event_id" not in record


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------

def _build_ev(event_id, edge_target_probability, odds):
    candidate = {
        "event_id": event_id,
        "market_type": "player_shots",
        "selection": "over",
        "line": 2.5,
    }
    odds_snapshot = {
        "event_id": event_id,
        "market_type": "player_shots",
        "selection": "over",
        "line": 2.5,
        "odds": odds,
        "odds_format": "american",
    }
    return build_candidate_ev_enrichment(
        candidate=candidate,
        odds_snapshot=odds_snapshot,
        model_probability=edge_target_probability,
    )


def test_full_pipeline_ev_ranking_and_report():
    evs = [
        _build_ev("match_001", 0.70, 150),
        _build_ev("match_002", 0.30, -110),
        _build_ev("match_003", 0.65, 120),
    ]
    ranked = rank_candidate_ev_enrichments(evs)
    result = build_candidate_report(ranked)

    assert result["total_records"] == 3
    assert result["ranked_count"] + result["excluded_count"] == 3
    assert result["ranking_status_counts"]["ranked"] == result["ranked_count"]
    assert result["ranking_status_counts"]["excluded"] == result["excluded_count"]
    assert len(result["top_ranked_candidates"]) == result["ranked_count"]
    assert len(result["excluded_candidates"]) == result["excluded_count"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_input_produces_identical_output():
    records = [
        _make_ranked_record(rank=1, original_index=0, event_id="a"),
        _make_excluded_record(original_index=1, event_id="b"),
    ]
    result_1 = _report(records)
    result_2 = _report(records)
    assert result_1 == result_2
