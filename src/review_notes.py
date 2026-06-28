from review_taxonomy import validate_review_taxonomy


class ReviewNoteValidationError(ValueError):
    pass


def build_review_note(
    review_category: str,
    severity: str,
    data_quality: str,
    summary: str,
    evidence: list[str] | tuple[str, ...] | None = None,
) -> dict:
    taxonomy = validate_review_taxonomy(review_category, severity, data_quality)

    if not isinstance(summary, str):
        raise ReviewNoteValidationError(
            f"summary must be a string, got {type(summary).__name__!r}"
        )
    stripped_summary = summary.strip()
    if not stripped_summary:
        raise ReviewNoteValidationError("summary must not be empty or whitespace-only")

    if evidence is None:
        validated_evidence = []
    else:
        if not isinstance(evidence, (list, tuple)):
            raise ReviewNoteValidationError(
                f"evidence must be a list or tuple, got {type(evidence).__name__!r}"
            )
        validated_evidence = []
        for i, item in enumerate(evidence):
            if not isinstance(item, str):
                raise ReviewNoteValidationError(
                    f"evidence[{i}] must be a string, got {type(item).__name__!r}"
                )
            stripped_item = item.strip()
            if not stripped_item:
                raise ReviewNoteValidationError(
                    f"evidence[{i}] must not be empty or whitespace-only after stripping"
                )
            validated_evidence.append(stripped_item)

    return {
        "review_category": taxonomy["review_category"],
        "severity": taxonomy["severity"],
        "data_quality": taxonomy["data_quality"],
        "summary": stripped_summary,
        "evidence": validated_evidence,
    }
