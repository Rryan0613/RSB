"""Pure backtest review overlay. No database, filesystem, or external dependencies."""


class BacktestReviewValidationError(ValueError):
    pass


MIN_EVALUATED_ROWS = 10
ACCURACY_STRONG_THRESHOLD = 0.60
ACCURACY_WEAK_THRESHOLD = 0.40

VALID_REVIEW_STATUSES = frozenset({
    "strong",
    "mixed",
    "weak",
    "insufficient_data",
})


def build_backtest_review(report: dict) -> dict:
    if not isinstance(report, dict):
        raise BacktestReviewValidationError(
            f"report must be a dict, got {type(report).__name__!r}"
        )
    if "evaluated_rows" not in report:
        raise BacktestReviewValidationError("report must contain 'evaluated_rows'")
    if "skipped_rows" not in report:
        raise BacktestReviewValidationError("report must contain 'skipped_rows'")
    if "overall" not in report:
        raise BacktestReviewValidationError("report must contain 'overall'")
    if not isinstance(report["overall"], dict):
        raise BacktestReviewValidationError("report['overall'] must be a dict")
    if "accuracy" not in report["overall"]:
        raise BacktestReviewValidationError("report['overall'] must contain 'accuracy'")

    evaluated_rows = report["evaluated_rows"]
    if isinstance(evaluated_rows, bool):
        raise BacktestReviewValidationError("evaluated_rows must not be a bool")
    if not isinstance(evaluated_rows, int):
        raise BacktestReviewValidationError(
            f"evaluated_rows must be an int, got {type(evaluated_rows).__name__!r}"
        )
    if evaluated_rows < 0:
        raise BacktestReviewValidationError(
            f"evaluated_rows must be non-negative, got {evaluated_rows!r}"
        )

    skipped_rows = report["skipped_rows"]
    if isinstance(skipped_rows, bool):
        raise BacktestReviewValidationError("skipped_rows must not be a bool")
    if not isinstance(skipped_rows, int):
        raise BacktestReviewValidationError(
            f"skipped_rows must be an int, got {type(skipped_rows).__name__!r}"
        )
    if skipped_rows < 0:
        raise BacktestReviewValidationError(
            f"skipped_rows must be non-negative, got {skipped_rows!r}"
        )

    accuracy = report["overall"]["accuracy"]
    if accuracy is not None:
        if isinstance(accuracy, bool):
            raise BacktestReviewValidationError("accuracy must not be a bool")
        if not isinstance(accuracy, (int, float)):
            raise BacktestReviewValidationError(
                f"accuracy must be numeric, got {type(accuracy).__name__!r}"
            )
        if accuracy != accuracy:
            raise BacktestReviewValidationError("accuracy must not be NaN")
        if accuracy < 0.0:
            raise BacktestReviewValidationError(
                f"accuracy must be >= 0.0, got {accuracy!r}"
            )
        if accuracy > 1.0:
            raise BacktestReviewValidationError(
                f"accuracy must be <= 1.0, got {accuracy!r}"
            )
        accuracy = float(accuracy)

    if evaluated_rows < MIN_EVALUATED_ROWS or accuracy is None:
        review_status = "insufficient_data"
    elif accuracy >= ACCURACY_STRONG_THRESHOLD:
        review_status = "strong"
    elif accuracy >= ACCURACY_WEAK_THRESHOLD:
        review_status = "mixed"
    else:
        review_status = "weak"

    needs_review = review_status in ("weak", "insufficient_data") or skipped_rows > 0
    skipped_row_flag = skipped_rows > 0

    return {
        "review_status": review_status,
        "needs_review": needs_review,
        "skipped_row_flag": skipped_row_flag,
        "evaluated_rows": evaluated_rows,
        "accuracy": accuracy,
    }
