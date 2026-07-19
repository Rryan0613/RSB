import math

from candidate_evaluation import (
    CandidateEvaluationValidationError,
    validate_candidate_evaluation_record,
)


class CandidateRankingValidationError(ValueError):
    pass


def _validate_line(value) -> "float | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise CandidateRankingValidationError("line must not be a bool")
    if not isinstance(value, (int, float)):
        raise CandidateRankingValidationError(
            f"line must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise CandidateRankingValidationError("line must not be NaN")
    if math.isinf(value):
        raise CandidateRankingValidationError("line must not be infinite")
    return float(value)


def _validate_required_numeric(value, name: str) -> float:
    if isinstance(value, bool):
        raise CandidateRankingValidationError(f"{name} must not be a bool")
    if not isinstance(value, (int, float)):
        raise CandidateRankingValidationError(
            f"{name} must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise CandidateRankingValidationError(f"{name} must not be NaN")
    if math.isinf(value):
        raise CandidateRankingValidationError(f"{name} must not be infinite")
    return float(value)


def _validate_optional_unit_score(value, name: str) -> "float | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise CandidateRankingValidationError(f"{name} must not be a bool")
    if not isinstance(value, (int, float)):
        raise CandidateRankingValidationError(
            f"{name} must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise CandidateRankingValidationError(f"{name} must not be NaN")
    if math.isinf(value):
        raise CandidateRankingValidationError(f"{name} must not be infinite")
    if value < 0.0:
        raise CandidateRankingValidationError(f"{name} must be >= 0.0, got {value!r}")
    if value > 1.0:
        raise CandidateRankingValidationError(f"{name} must be <= 1.0, got {value!r}")
    return float(value)


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CandidateRankingValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def _validate_candidate_evaluation(value, idx: int) -> "tuple[str, list[str]]":
    try:
        validated = validate_candidate_evaluation_record(value)
    except CandidateEvaluationValidationError as exc:
        raise CandidateRankingValidationError(
            f"candidate_evs[{idx}] candidate_evaluation is invalid: {exc}"
        ) from exc
    return validated["status"], validated["pass_reasons"]


def _validate_score_list(scores, name: str, expected_len: int) -> list:
    if scores is None:
        return [None] * expected_len
    if not isinstance(scores, (list, tuple)):
        raise CandidateRankingValidationError(
            f"{name} must be a list or tuple, got {type(scores).__name__!r}"
        )
    if len(scores) != expected_len:
        raise CandidateRankingValidationError(
            f"{name} must have the same length as candidate_evs "
            f"({expected_len}), got {len(scores)}"
        )
    return [
        _validate_optional_unit_score(item, f"{name}[{i}]")
        for i, item in enumerate(scores)
    ]


def _score_sort_key(value) -> "tuple[int, float]":
    if value is None:
        return (1, 0.0)
    return (0, -value)


def _sort_key(record) -> tuple:
    return (
        -record["expected_value"],
        -record["edge"],
        _score_sort_key(record["data_quality_score"]),
        _score_sort_key(record["confidence_score"]),
        _score_sort_key(record["calibration_score"]),
        record["original_index"],
    )


def _build_output_record(record, rank, ranking_status: str, validated_metadata: dict) -> dict:
    return {
        "rank": rank,
        "ranking_status": ranking_status,
        "candidate_ev": record["candidate_ev"],
        "event_id": record["event_id"],
        "market_type": record["market_type"],
        "selection": record["selection"],
        "line": record["line"],
        "edge": record["edge"],
        "expected_value": record["expected_value"],
        "candidate_status": record["candidate_status"],
        "pass_reasons": record["pass_reasons"],
        "data_quality_score": record["data_quality_score"],
        "confidence_score": record["confidence_score"],
        "calibration_score": record["calibration_score"],
        "original_index": record["original_index"],
        "metadata": dict(validated_metadata),
    }


def rank_candidate_ev_enrichments(
    candidate_evs,
    *,
    data_quality_scores=None,
    confidence_scores=None,
    calibration_scores=None,
    metadata=None,
) -> list:
    if not isinstance(candidate_evs, (list, tuple)):
        raise CandidateRankingValidationError(
            f"candidate_evs must be a list or tuple, got {type(candidate_evs).__name__!r}"
        )
    if len(candidate_evs) == 0:
        raise CandidateRankingValidationError("candidate_evs must not be empty")

    expected_len = len(candidate_evs)
    validated_dq = _validate_score_list(
        data_quality_scores, "data_quality_scores", expected_len
    )
    validated_conf = _validate_score_list(
        confidence_scores, "confidence_scores", expected_len
    )
    validated_calib = _validate_score_list(
        calibration_scores, "calibration_scores", expected_len
    )
    validated_metadata = _validate_metadata(metadata)

    intermediate = []
    for idx, item in enumerate(candidate_evs):
        if not isinstance(item, dict):
            raise CandidateRankingValidationError(
                f"candidate_evs[{idx}] must be a dict, got {type(item).__name__!r}"
            )
        try:
            event_id = item["event_id"]
            market_type = item["market_type"]
            selection = item["selection"]
            line_raw = item["line"]
            edge_raw = item["edge"]
            expected_value_raw = item["expected_value"]
            candidate_evaluation_raw = item["candidate_evaluation"]
        except KeyError as exc:
            raise CandidateRankingValidationError(
                f"candidate_evs[{idx}] is missing required key: {exc}"
            ) from exc

        line = _validate_line(line_raw)
        edge = _validate_required_numeric(edge_raw, f"candidate_evs[{idx}] edge")
        expected_value = _validate_required_numeric(
            expected_value_raw, f"candidate_evs[{idx}] expected_value"
        )
        status, pass_reasons = _validate_candidate_evaluation(candidate_evaluation_raw, idx)

        intermediate.append(
            {
                "candidate_ev": dict(item),
                "event_id": event_id,
                "market_type": market_type,
                "selection": selection,
                "line": line,
                "edge": edge,
                "expected_value": expected_value,
                "candidate_status": status,
                "pass_reasons": pass_reasons,
                "data_quality_score": validated_dq[idx],
                "confidence_score": validated_conf[idx],
                "calibration_score": validated_calib[idx],
                "original_index": idx,
            }
        )

    rankable = [r for r in intermediate if r["candidate_status"] == "candidate"]
    excluded = [r for r in intermediate if r["candidate_status"] != "candidate"]

    rankable.sort(key=_sort_key)
    excluded.sort(key=lambda r: r["original_index"])

    results = [
        _build_output_record(record, rank, "ranked", validated_metadata)
        for rank, record in enumerate(rankable, start=1)
    ]
    results.extend(
        _build_output_record(record, None, "excluded", validated_metadata)
        for record in excluded
    )
    return results
