from candidate_evaluation import validate_pass_reasons


class CandidateReportValidationError(ValueError):
    pass


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CandidateReportValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def _validate_top_n(value) -> "int | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise CandidateReportValidationError("top_n must not be a bool")
    if not isinstance(value, int):
        raise CandidateReportValidationError(
            f"top_n must be an int, got {type(value).__name__!r}"
        )
    if value < 0:
        raise CandidateReportValidationError(f"top_n must be >= 0, got {value!r}")
    return value


def _validate_rank(value, name: str) -> int:
    if isinstance(value, bool):
        raise CandidateReportValidationError(f"{name} must not be a bool")
    if not isinstance(value, int):
        raise CandidateReportValidationError(
            f"{name} must be an int, got {type(value).__name__!r}"
        )
    if value <= 0:
        raise CandidateReportValidationError(
            f"{name} must be a positive integer, got {value!r}"
        )
    return value


def build_candidate_report(
    ranked_candidates,
    *,
    top_n=None,
    metadata=None,
) -> dict:
    if not isinstance(ranked_candidates, (list, tuple)):
        raise CandidateReportValidationError(
            f"ranked_candidates must be a list or tuple, "
            f"got {type(ranked_candidates).__name__!r}"
        )

    validated_top_n = _validate_top_n(top_n)
    validated_metadata = _validate_metadata(metadata)

    ranked_records = []
    excluded_records = []
    pass_reason_counts: dict = {}
    expected_rank = 1

    for idx, item in enumerate(ranked_candidates):
        if not isinstance(item, dict):
            raise CandidateReportValidationError(
                f"ranked_candidates[{idx}] must be a dict, got {type(item).__name__!r}"
            )
        try:
            rank = item["rank"]
            ranking_status = item["ranking_status"]
            item["candidate_status"]
            pass_reasons_raw = item["pass_reasons"]
            item["original_index"]
        except KeyError as exc:
            raise CandidateReportValidationError(
                f"ranked_candidates[{idx}] is missing required key: {exc}"
            ) from exc

        if ranking_status not in ("ranked", "excluded"):
            raise CandidateReportValidationError(
                f"ranked_candidates[{idx}] ranking_status must be 'ranked' or "
                f"'excluded', got {ranking_status!r}"
            )

        pass_reasons = validate_pass_reasons(pass_reasons_raw)

        if ranking_status == "ranked":
            validated_rank = _validate_rank(rank, f"ranked_candidates[{idx}] rank")
            if validated_rank != expected_rank:
                raise CandidateReportValidationError(
                    f"ranked_candidates[{idx}] rank {validated_rank!r} is out of "
                    f"order; expected {expected_rank!r}"
                )
            expected_rank += 1
            ranked_records.append(dict(item))
        else:
            if rank is not None:
                raise CandidateReportValidationError(
                    f"ranked_candidates[{idx}] excluded record must have "
                    f"rank=None, got {rank!r}"
                )
            excluded_records.append(dict(item))

        for reason in pass_reasons:
            pass_reason_counts[reason] = pass_reason_counts.get(reason, 0) + 1

    if validated_top_n is not None:
        top_ranked_candidates = ranked_records[:validated_top_n]
    else:
        top_ranked_candidates = list(ranked_records)

    ranked_count = len(ranked_records)
    excluded_count = len(excluded_records)

    return {
        "total_records": len(ranked_candidates),
        "ranked_count": ranked_count,
        "excluded_count": excluded_count,
        "top_n": validated_top_n,
        "top_ranked_candidates": top_ranked_candidates,
        "excluded_candidates": excluded_records,
        "pass_reason_counts": pass_reason_counts,
        "ranking_status_counts": {"ranked": ranked_count, "excluded": excluded_count},
        "metadata": validated_metadata,
    }
