import pytest

from candidate_evaluation import (
    CandidateEvaluationValidationError,
    VALID_CANDIDATE_STATUSES,
    VALID_PASS_REASONS,
    normalize_candidate_status,
    normalize_pass_reason,
    validate_pass_reasons,
    build_candidate_evaluation,
)


# ---------------------------------------------------------------------------
# CandidateEvaluationValidationError
# ---------------------------------------------------------------------------

def test_candidate_evaluation_validation_error_is_value_error():
    assert issubclass(CandidateEvaluationValidationError, ValueError)


# ---------------------------------------------------------------------------
# normalize_candidate_status — valid
# ---------------------------------------------------------------------------

def test_normalize_candidate_status_candidate():
    assert normalize_candidate_status("candidate") == "candidate"


def test_normalize_candidate_status_rejected():
    assert normalize_candidate_status("rejected") == "rejected"


def test_normalize_candidate_status_not_evaluable():
    assert normalize_candidate_status("not_evaluable") == "not_evaluable"


def test_normalize_candidate_status_strips_whitespace():
    assert normalize_candidate_status("  candidate  ") == "candidate"


def test_normalize_candidate_status_lowercases():
    assert normalize_candidate_status("CANDIDATE") == "candidate"


def test_normalize_candidate_status_lowercases_rejected():
    assert normalize_candidate_status("REJECTED") == "rejected"


def test_normalize_candidate_status_lowercases_not_evaluable():
    assert normalize_candidate_status("NOT_EVALUABLE") == "not_evaluable"


def test_normalize_candidate_status_normalizes_spaces_to_underscores():
    assert normalize_candidate_status("not evaluable") == "not_evaluable"


def test_normalize_candidate_status_normalizes_hyphens_to_underscores():
    assert normalize_candidate_status("not-evaluable") == "not_evaluable"


def test_normalize_candidate_status_returns_string():
    assert type(normalize_candidate_status("candidate")) is str


# ---------------------------------------------------------------------------
# normalize_candidate_status — invalid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["candidate"]])
def test_normalize_candidate_status_rejects_non_string(value):
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_candidate_status(value)


def test_normalize_candidate_status_rejects_empty_string():
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_candidate_status("")


def test_normalize_candidate_status_rejects_whitespace_only():
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_candidate_status("   ")


def test_normalize_candidate_status_rejects_unknown():
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_candidate_status("approved")


# ---------------------------------------------------------------------------
# normalize_pass_reason — valid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason", sorted(VALID_PASS_REASONS))
def test_normalize_pass_reason_all_valid_reasons(reason):
    assert normalize_pass_reason(reason) == reason


def test_normalize_pass_reason_strips_whitespace():
    assert normalize_pass_reason("  unknown  ") == "unknown"


def test_normalize_pass_reason_lowercases():
    assert normalize_pass_reason("UNKNOWN") == "unknown"


def test_normalize_pass_reason_normalizes_spaces_to_underscores():
    assert normalize_pass_reason("edge below minimum") == "edge_below_minimum"


def test_normalize_pass_reason_normalizes_hyphens_to_underscores():
    assert normalize_pass_reason("edge-below-minimum") == "edge_below_minimum"


def test_normalize_pass_reason_returns_string():
    assert type(normalize_pass_reason("unknown")) is str


# ---------------------------------------------------------------------------
# normalize_pass_reason — invalid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 0, ["unknown"]])
def test_normalize_pass_reason_rejects_non_string(value):
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_pass_reason(value)


def test_normalize_pass_reason_rejects_empty_string():
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_pass_reason("")


def test_normalize_pass_reason_rejects_whitespace_only():
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_pass_reason("   ")


def test_normalize_pass_reason_rejects_unknown():
    with pytest.raises(CandidateEvaluationValidationError):
        normalize_pass_reason("bad_reason")


# ---------------------------------------------------------------------------
# validate_pass_reasons — valid
# ---------------------------------------------------------------------------

def test_validate_pass_reasons_none_returns_empty_list():
    assert validate_pass_reasons(None) == []


def test_validate_pass_reasons_empty_list_returns_empty_list():
    assert validate_pass_reasons([]) == []


def test_validate_pass_reasons_empty_tuple_returns_empty_list():
    assert validate_pass_reasons(()) == []


def test_validate_pass_reasons_valid_list():
    result = validate_pass_reasons(["unknown", "data_quality_concern"])
    assert result == ["unknown", "data_quality_concern"]


def test_validate_pass_reasons_tuple_accepted():
    result = validate_pass_reasons(("unknown",))
    assert result == ["unknown"]


def test_validate_pass_reasons_returns_list_not_tuple():
    result = validate_pass_reasons(("unknown",))
    assert type(result) is list


def test_validate_pass_reasons_order_preserved():
    reasons = ["unknown", "data_quality_concern", "manual_review_required"]
    assert validate_pass_reasons(reasons) == reasons


def test_validate_pass_reasons_duplicates_preserved():
    reasons = ["unknown", "unknown"]
    assert validate_pass_reasons(reasons) == ["unknown", "unknown"]


def test_validate_pass_reasons_normalizes_items():
    result = validate_pass_reasons(["  UNKNOWN  "])
    assert result == ["unknown"]


# ---------------------------------------------------------------------------
# validate_pass_reasons — invalid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["unknown", 0, {"unknown"}])
def test_validate_pass_reasons_rejects_non_list_tuple(value):
    with pytest.raises(CandidateEvaluationValidationError):
        validate_pass_reasons(value)


def test_validate_pass_reasons_rejects_non_string_item():
    with pytest.raises(CandidateEvaluationValidationError):
        validate_pass_reasons([42])


def test_validate_pass_reasons_rejects_empty_string_item():
    with pytest.raises(CandidateEvaluationValidationError):
        validate_pass_reasons([""])


def test_validate_pass_reasons_rejects_whitespace_only_item():
    with pytest.raises(CandidateEvaluationValidationError):
        validate_pass_reasons(["   "])


def test_validate_pass_reasons_rejects_unknown_reason():
    with pytest.raises(CandidateEvaluationValidationError):
        validate_pass_reasons(["bad_reason"])


# ---------------------------------------------------------------------------
# build_candidate_evaluation — return shape
# ---------------------------------------------------------------------------

def test_build_candidate_evaluation_returns_exactly_three_keys():
    result = build_candidate_evaluation("candidate", edge=0.05)
    assert set(result.keys()) == {"status", "edge", "pass_reasons"}


def test_build_candidate_evaluation_returns_plain_dict():
    result = build_candidate_evaluation("candidate")
    assert type(result) is dict


def test_build_candidate_evaluation_edge_key_always_present_when_none():
    result = build_candidate_evaluation("candidate", edge=None)
    assert "edge" in result
    assert result["edge"] is None


def test_build_candidate_evaluation_candidate_canonical():
    result = build_candidate_evaluation("candidate", edge=0.05)
    assert result["status"] == "candidate"
    assert result["edge"] == pytest.approx(0.05)
    assert result["pass_reasons"] == []


def test_build_candidate_evaluation_rejected_canonical():
    result = build_candidate_evaluation(
        "rejected", edge=0.01, pass_reasons=["edge_below_minimum"]
    )
    assert result["status"] == "rejected"
    assert result["edge"] == pytest.approx(0.01)
    assert result["pass_reasons"] == ["edge_below_minimum"]


def test_build_candidate_evaluation_not_evaluable_canonical():
    result = build_candidate_evaluation(
        "not_evaluable", edge=None, pass_reasons=["missing_model_probability"]
    )
    assert result["status"] == "not_evaluable"
    assert result["edge"] is None
    assert result["pass_reasons"] == ["missing_model_probability"]


# ---------------------------------------------------------------------------
# build_candidate_evaluation — status normalization
# ---------------------------------------------------------------------------

def test_build_candidate_evaluation_status_strips_whitespace():
    result = build_candidate_evaluation("  candidate  ")
    assert result["status"] == "candidate"


def test_build_candidate_evaluation_status_lowercases():
    result = build_candidate_evaluation("CANDIDATE")
    assert result["status"] == "candidate"


def test_build_candidate_evaluation_invalid_status_raises():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("approved")


# ---------------------------------------------------------------------------
# build_candidate_evaluation — edge validation
# ---------------------------------------------------------------------------

def test_build_candidate_evaluation_edge_none_allowed_candidate():
    result = build_candidate_evaluation("candidate", edge=None)
    assert result["edge"] is None


def test_build_candidate_evaluation_edge_none_allowed_rejected():
    result = build_candidate_evaluation(
        "rejected", edge=None, pass_reasons=["unknown"]
    )
    assert result["edge"] is None


def test_build_candidate_evaluation_edge_none_allowed_not_evaluable():
    result = build_candidate_evaluation(
        "not_evaluable", edge=None, pass_reasons=["unknown"]
    )
    assert result["edge"] is None


def test_build_candidate_evaluation_edge_positive():
    result = build_candidate_evaluation("candidate", edge=0.08)
    assert result["edge"] == pytest.approx(0.08)


def test_build_candidate_evaluation_edge_negative():
    result = build_candidate_evaluation(
        "rejected", edge=-0.05, pass_reasons=["edge_below_minimum"]
    )
    assert result["edge"] == pytest.approx(-0.05)


def test_build_candidate_evaluation_edge_zero():
    result = build_candidate_evaluation("candidate", edge=0)
    assert result["edge"] == pytest.approx(0.0)


def test_build_candidate_evaluation_edge_int_returns_float():
    result = build_candidate_evaluation("candidate", edge=0)
    assert type(result["edge"]) is float


def test_build_candidate_evaluation_edge_positive_boundary():
    result = build_candidate_evaluation("candidate", edge=1.0)
    assert result["edge"] == pytest.approx(1.0)


def test_build_candidate_evaluation_edge_negative_boundary():
    result = build_candidate_evaluation(
        "rejected", edge=-1.0, pass_reasons=["edge_below_minimum"]
    )
    assert result["edge"] == pytest.approx(-1.0)


def test_build_candidate_evaluation_edge_float_returns_float():
    result = build_candidate_evaluation("candidate", edge=0.05)
    assert type(result["edge"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_build_candidate_evaluation_edge_rejects_bool(value):
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", edge=value)


@pytest.mark.parametrize("value", ["0.05", [0.05]])
def test_build_candidate_evaluation_edge_rejects_non_numeric(value):
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", edge=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_candidate_evaluation_edge_rejects_nan_and_inf(value):
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", edge=value)


@pytest.mark.parametrize("value", [1.01, -1.01])
def test_build_candidate_evaluation_edge_rejects_out_of_range(value):
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", edge=value)


# ---------------------------------------------------------------------------
# build_candidate_evaluation — pass_reasons normalization
# ---------------------------------------------------------------------------

def test_build_candidate_evaluation_pass_reasons_normalized_in_output():
    result = build_candidate_evaluation(
        "rejected", pass_reasons=["  UNKNOWN  "]
    )
    assert result["pass_reasons"] == ["unknown"]


def test_build_candidate_evaluation_pass_reasons_tuple_accepted():
    result = build_candidate_evaluation(
        "rejected", pass_reasons=("unknown",)
    )
    assert result["pass_reasons"] == ["unknown"]
    assert type(result["pass_reasons"]) is list


def test_build_candidate_evaluation_pass_reasons_order_preserved():
    reasons = ["unknown", "data_quality_concern", "manual_review_required"]
    result = build_candidate_evaluation("rejected", pass_reasons=reasons)
    assert result["pass_reasons"] == reasons


def test_build_candidate_evaluation_pass_reasons_duplicates_preserved():
    result = build_candidate_evaluation(
        "rejected", pass_reasons=["unknown", "unknown"]
    )
    assert result["pass_reasons"] == ["unknown", "unknown"]


# ---------------------------------------------------------------------------
# build_candidate_evaluation — structural invariants
# ---------------------------------------------------------------------------

def test_build_candidate_evaluation_candidate_empty_reasons_passes():
    result = build_candidate_evaluation("candidate", pass_reasons=[])
    assert result["pass_reasons"] == []


def test_build_candidate_evaluation_candidate_none_reasons_passes():
    result = build_candidate_evaluation("candidate", pass_reasons=None)
    assert result["pass_reasons"] == []


def test_build_candidate_evaluation_candidate_with_reasons_raises():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", pass_reasons=["unknown"])


def test_build_candidate_evaluation_rejected_with_reasons_passes():
    result = build_candidate_evaluation(
        "rejected", pass_reasons=["edge_below_minimum"]
    )
    assert result["status"] == "rejected"
    assert result["pass_reasons"] == ["edge_below_minimum"]


def test_build_candidate_evaluation_rejected_empty_reasons_raises():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("rejected", pass_reasons=[])


def test_build_candidate_evaluation_rejected_none_reasons_raises():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("rejected", pass_reasons=None)


def test_build_candidate_evaluation_not_evaluable_with_reasons_passes():
    result = build_candidate_evaluation(
        "not_evaluable", pass_reasons=["missing_model_probability"]
    )
    assert result["status"] == "not_evaluable"
    assert result["pass_reasons"] == ["missing_model_probability"]


def test_build_candidate_evaluation_not_evaluable_empty_reasons_raises():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("not_evaluable", pass_reasons=[])


def test_build_candidate_evaluation_not_evaluable_none_reasons_raises():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("not_evaluable", pass_reasons=None)


# ---------------------------------------------------------------------------
# build_candidate_evaluation — operation order
# ---------------------------------------------------------------------------

def test_build_candidate_evaluation_bad_status_raises_before_edge_check():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("approved", edge=True)


def test_build_candidate_evaluation_bad_edge_raises_before_reasons_check():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", edge=True, pass_reasons=["bad_reason"])


def test_build_candidate_evaluation_whitespace_reason_fails_before_invariant():
    with pytest.raises(CandidateEvaluationValidationError):
        build_candidate_evaluation("candidate", pass_reasons=["   "])


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_candidate_evaluation_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "candidate_evaluation.py"
    tree = ast.parse(src.read_text())
    banned = {"sqlite3", "database", "json", "subprocess", "pathlib",
              "odds", "edge", "review_taxonomy", "review_notes"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
