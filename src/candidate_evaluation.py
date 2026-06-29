import math


class CandidateEvaluationValidationError(ValueError):
    pass


VALID_CANDIDATE_STATUSES = frozenset({
    "candidate",
    "rejected",
    "not_evaluable",
})

VALID_PASS_REASONS = frozenset({
    "edge_below_minimum",
    "missing_model_probability",
    "missing_implied_probability",
    "invalid_model_probability",
    "invalid_implied_probability",
    "market_semantics_unclear",
    "data_quality_concern",
    "manual_review_required",
    "unknown",
})


def _normalize(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_edge(edge) -> float | None:
    if edge is None:
        return None
    if isinstance(edge, bool):
        raise CandidateEvaluationValidationError("edge must not be a bool")
    if not isinstance(edge, (int, float)):
        raise CandidateEvaluationValidationError(
            f"edge must be int or float, got {type(edge).__name__!r}"
        )
    if math.isnan(edge):
        raise CandidateEvaluationValidationError("edge must not be NaN")
    if math.isinf(edge):
        raise CandidateEvaluationValidationError("edge must not be infinite")
    if edge < -1.0:
        raise CandidateEvaluationValidationError(
            f"edge must be >= -1.0, got {edge!r}"
        )
    if edge > 1.0:
        raise CandidateEvaluationValidationError(
            f"edge must be <= 1.0, got {edge!r}"
        )
    return float(edge)


def normalize_candidate_status(status: str) -> str:
    if not isinstance(status, str):
        raise CandidateEvaluationValidationError(
            f"status must be a string, got {type(status).__name__!r}"
        )
    normalized = _normalize(status)
    if not normalized:
        raise CandidateEvaluationValidationError(
            "status must not be empty or whitespace-only"
        )
    if normalized not in VALID_CANDIDATE_STATUSES:
        raise CandidateEvaluationValidationError(
            f"Unknown candidate status: {status!r}. "
            f"Valid statuses: {sorted(VALID_CANDIDATE_STATUSES)}"
        )
    return normalized


def normalize_pass_reason(reason: str) -> str:
    if not isinstance(reason, str):
        raise CandidateEvaluationValidationError(
            f"pass_reason must be a string, got {type(reason).__name__!r}"
        )
    normalized = _normalize(reason)
    if not normalized:
        raise CandidateEvaluationValidationError(
            "pass_reason must not be empty or whitespace-only"
        )
    if normalized not in VALID_PASS_REASONS:
        raise CandidateEvaluationValidationError(
            f"Unknown pass_reason: {reason!r}. "
            f"Valid pass_reasons: {sorted(VALID_PASS_REASONS)}"
        )
    return normalized


def validate_pass_reasons(pass_reasons) -> list[str]:
    if pass_reasons is None:
        return []
    if not isinstance(pass_reasons, (list, tuple)):
        raise CandidateEvaluationValidationError(
            f"pass_reasons must be a list or tuple, got {type(pass_reasons).__name__!r}"
        )
    return [normalize_pass_reason(item) for item in pass_reasons]


def build_candidate_evaluation(
    status: str,
    edge=None,
    pass_reasons=None,
) -> dict:
    normalized_status = normalize_candidate_status(status)
    validated_edge = _validate_edge(edge)
    validated_reasons = validate_pass_reasons(pass_reasons)

    if normalized_status == "candidate" and validated_reasons:
        raise CandidateEvaluationValidationError(
            f"status='candidate' requires pass_reasons to be empty, "
            f"got {validated_reasons!r}"
        )
    if normalized_status in ("rejected", "not_evaluable") and not validated_reasons:
        raise CandidateEvaluationValidationError(
            f"status={normalized_status!r} requires at least one pass_reason"
        )

    return {
        "status": normalized_status,
        "edge": validated_edge,
        "pass_reasons": validated_reasons,
    }
