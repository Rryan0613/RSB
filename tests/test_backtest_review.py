"""Deterministic unit tests for src/backtest_review.py.

Uses in-memory synthetic dicts only.
No database access, no filesystem access, no external I/O.
"""

import ast
import inspect
from pathlib import Path

import pytest

from backtest_review import (
    ACCURACY_STRONG_THRESHOLD,
    ACCURACY_WEAK_THRESHOLD,
    MIN_EVALUATED_ROWS,
    VALID_REVIEW_STATUSES,
    BacktestReviewValidationError,
    build_backtest_review,
)


def _report(
    evaluated_rows=10,
    skipped_rows=0,
    accuracy=0.7,
) -> dict:
    """Minimal valid report dict for test use."""
    return {
        "evaluated_rows": evaluated_rows,
        "skipped_rows": skipped_rows,
        "overall": {"accuracy": accuracy},
    }


# ---------------------------------------------------------------------------
# Error class hierarchy
# ---------------------------------------------------------------------------


class TestErrorClass:
    def test_is_subclass_of_value_error(self):
        assert issubclass(BacktestReviewValidationError, ValueError)

    def test_can_be_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise BacktestReviewValidationError("test")

    def test_message_is_preserved(self):
        with pytest.raises(BacktestReviewValidationError, match="test message"):
            raise BacktestReviewValidationError("test message")


# ---------------------------------------------------------------------------
# Constants and allowed statuses
# ---------------------------------------------------------------------------


class TestConstants:
    def test_min_evaluated_rows_is_10(self):
        assert MIN_EVALUATED_ROWS == 10

    def test_accuracy_strong_threshold_is_0_60(self):
        assert ACCURACY_STRONG_THRESHOLD == 0.60

    def test_accuracy_weak_threshold_is_0_40(self):
        assert ACCURACY_WEAK_THRESHOLD == 0.40

    def test_valid_review_statuses_is_frozenset(self):
        assert isinstance(VALID_REVIEW_STATUSES, frozenset)

    def test_valid_review_statuses_contains_strong(self):
        assert "strong" in VALID_REVIEW_STATUSES

    def test_valid_review_statuses_contains_mixed(self):
        assert "mixed" in VALID_REVIEW_STATUSES

    def test_valid_review_statuses_contains_weak(self):
        assert "weak" in VALID_REVIEW_STATUSES

    def test_valid_review_statuses_contains_insufficient_data(self):
        assert "insufficient_data" in VALID_REVIEW_STATUSES

    def test_valid_review_statuses_has_exactly_four_members(self):
        assert len(VALID_REVIEW_STATUSES) == 4


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


class TestStructuralValidation:
    def test_non_dict_report_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="dict"):
            build_backtest_review("not a dict")

    def test_list_report_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review([])

    def test_none_report_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(None)

    def test_missing_evaluated_rows_raises(self):
        report = {"skipped_rows": 0, "overall": {"accuracy": 0.7}}
        with pytest.raises(BacktestReviewValidationError, match="evaluated_rows"):
            build_backtest_review(report)

    def test_missing_skipped_rows_raises(self):
        report = {"evaluated_rows": 10, "overall": {"accuracy": 0.7}}
        with pytest.raises(BacktestReviewValidationError, match="skipped_rows"):
            build_backtest_review(report)

    def test_missing_overall_raises(self):
        report = {"evaluated_rows": 10, "skipped_rows": 0}
        with pytest.raises(BacktestReviewValidationError, match="overall"):
            build_backtest_review(report)

    def test_overall_not_dict_raises(self):
        report = {"evaluated_rows": 10, "skipped_rows": 0, "overall": "bad"}
        with pytest.raises(BacktestReviewValidationError, match="overall"):
            build_backtest_review(report)

    def test_overall_missing_accuracy_raises(self):
        report = {"evaluated_rows": 10, "skipped_rows": 0, "overall": {}}
        with pytest.raises(BacktestReviewValidationError, match="accuracy"):
            build_backtest_review(report)

    def test_overall_list_raises(self):
        report = {"evaluated_rows": 10, "skipped_rows": 0, "overall": [0.7]}
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(report)


# ---------------------------------------------------------------------------
# Value validation — evaluated_rows
# ---------------------------------------------------------------------------


class TestEvaluatedRowsValidation:
    def test_bool_true_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="bool"):
            build_backtest_review(_report(evaluated_rows=True))

    def test_bool_false_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="bool"):
            build_backtest_review(_report(evaluated_rows=False))

    def test_float_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(evaluated_rows=10.0))

    def test_string_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(evaluated_rows="10"))

    def test_none_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(evaluated_rows=None))

    def test_negative_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="non-negative"):
            build_backtest_review(_report(evaluated_rows=-1))

    def test_zero_is_valid(self):
        result = build_backtest_review(_report(evaluated_rows=0))
        assert result["evaluated_rows"] == 0

    def test_positive_is_valid(self):
        result = build_backtest_review(_report(evaluated_rows=10))
        assert result["evaluated_rows"] == 10


# ---------------------------------------------------------------------------
# Value validation — skipped_rows
# ---------------------------------------------------------------------------


class TestSkippedRowsValidation:
    def test_bool_true_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="bool"):
            build_backtest_review(_report(skipped_rows=True))

    def test_bool_false_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="bool"):
            build_backtest_review(_report(skipped_rows=False))

    def test_float_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(skipped_rows=1.0))

    def test_string_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(skipped_rows="0"))

    def test_none_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(skipped_rows=None))

    def test_negative_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="non-negative"):
            build_backtest_review(_report(skipped_rows=-1))

    def test_zero_is_valid(self):
        result = build_backtest_review(_report(skipped_rows=0))
        assert result["skipped_row_flag"] is False

    def test_positive_is_valid(self):
        result = build_backtest_review(_report(skipped_rows=3))
        assert result["skipped_row_flag"] is True


# ---------------------------------------------------------------------------
# Value validation — accuracy
# ---------------------------------------------------------------------------


class TestAccuracyValidation:
    def test_none_is_valid(self):
        result = build_backtest_review(_report(accuracy=None))
        assert result["accuracy"] is None

    def test_bool_true_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="bool"):
            build_backtest_review(_report(accuracy=True))

    def test_bool_false_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="bool"):
            build_backtest_review(_report(accuracy=False))

    def test_string_raises(self):
        with pytest.raises(BacktestReviewValidationError):
            build_backtest_review(_report(accuracy="0.7"))

    def test_nan_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="NaN"):
            build_backtest_review(_report(accuracy=float("nan")))

    def test_below_zero_raises(self):
        with pytest.raises(BacktestReviewValidationError, match=">= 0.0"):
            build_backtest_review(_report(accuracy=-0.01))

    def test_above_one_raises(self):
        with pytest.raises(BacktestReviewValidationError, match="<= 1.0"):
            build_backtest_review(_report(accuracy=1.01))

    def test_zero_is_valid(self):
        result = build_backtest_review(_report(accuracy=0.0))
        assert result["accuracy"] == 0.0

    def test_one_is_valid(self):
        result = build_backtest_review(_report(accuracy=1.0))
        assert result["accuracy"] == 1.0

    def test_int_accuracy_coerced_to_float(self):
        result = build_backtest_review(_report(accuracy=1))
        assert result["accuracy"] == 1.0
        assert isinstance(result["accuracy"], float)


# ---------------------------------------------------------------------------
# insufficient_data classification
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_zero_evaluated_rows_is_insufficient(self):
        result = build_backtest_review(_report(evaluated_rows=0, accuracy=0.9))
        assert result["review_status"] == "insufficient_data"

    def test_nine_evaluated_rows_is_insufficient(self):
        result = build_backtest_review(_report(evaluated_rows=9, accuracy=0.9))
        assert result["review_status"] == "insufficient_data"

    def test_none_accuracy_is_insufficient(self):
        result = build_backtest_review(_report(evaluated_rows=100, accuracy=None))
        assert result["review_status"] == "insufficient_data"

    def test_insufficient_data_needs_review_is_true(self):
        result = build_backtest_review(_report(evaluated_rows=5, accuracy=0.9))
        assert result["needs_review"] is True


# ---------------------------------------------------------------------------
# strong / mixed / weak classification
# ---------------------------------------------------------------------------


class TestClassification:
    def test_accuracy_above_strong_threshold_is_strong(self):
        result = build_backtest_review(_report(accuracy=0.75))
        assert result["review_status"] == "strong"

    def test_accuracy_at_strong_threshold_is_strong(self):
        result = build_backtest_review(_report(accuracy=0.60))
        assert result["review_status"] == "strong"

    def test_accuracy_just_below_strong_threshold_is_mixed(self):
        result = build_backtest_review(_report(accuracy=0.599))
        assert result["review_status"] == "mixed"

    def test_accuracy_at_weak_threshold_is_mixed(self):
        result = build_backtest_review(_report(accuracy=0.40))
        assert result["review_status"] == "mixed"

    def test_accuracy_just_below_weak_threshold_is_weak(self):
        result = build_backtest_review(_report(accuracy=0.399))
        assert result["review_status"] == "weak"

    def test_accuracy_at_zero_is_weak(self):
        result = build_backtest_review(_report(accuracy=0.0))
        assert result["review_status"] == "weak"

    def test_strong_needs_review_is_false_when_no_skipped(self):
        result = build_backtest_review(_report(accuracy=0.70, skipped_rows=0))
        assert result["needs_review"] is False

    def test_mixed_needs_review_is_false_when_no_skipped(self):
        result = build_backtest_review(_report(accuracy=0.50, skipped_rows=0))
        assert result["needs_review"] is False

    def test_weak_needs_review_is_true(self):
        result = build_backtest_review(_report(accuracy=0.30, skipped_rows=0))
        assert result["needs_review"] is True


# ---------------------------------------------------------------------------
# Boundary behavior
# ---------------------------------------------------------------------------


class TestBoundaries:
    def test_exactly_min_evaluated_rows_enters_accuracy_branch(self):
        result = build_backtest_review(_report(evaluated_rows=10, accuracy=0.70))
        assert result["review_status"] != "insufficient_data"

    def test_one_below_min_evaluated_rows_is_insufficient(self):
        result = build_backtest_review(_report(evaluated_rows=9, accuracy=0.70))
        assert result["review_status"] == "insufficient_data"

    def test_accuracy_exactly_0_60_is_strong(self):
        result = build_backtest_review(_report(accuracy=0.60))
        assert result["review_status"] == "strong"

    def test_accuracy_exactly_0_40_is_mixed(self):
        result = build_backtest_review(_report(accuracy=0.40))
        assert result["review_status"] == "mixed"

    def test_accuracy_just_below_0_40_is_weak(self):
        result = build_backtest_review(_report(accuracy=0.3999))
        assert result["review_status"] == "weak"


# ---------------------------------------------------------------------------
# needs_review behavior
# ---------------------------------------------------------------------------


class TestNeedsReview:
    def test_weak_status_sets_needs_review(self):
        result = build_backtest_review(_report(accuracy=0.30, skipped_rows=0))
        assert result["needs_review"] is True

    def test_insufficient_data_sets_needs_review(self):
        result = build_backtest_review(_report(evaluated_rows=5, accuracy=0.70))
        assert result["needs_review"] is True

    def test_strong_with_no_skipped_clears_needs_review(self):
        result = build_backtest_review(_report(accuracy=0.70, skipped_rows=0))
        assert result["needs_review"] is False

    def test_mixed_with_no_skipped_clears_needs_review(self):
        result = build_backtest_review(_report(accuracy=0.50, skipped_rows=0))
        assert result["needs_review"] is False

    def test_strong_with_skipped_rows_sets_needs_review(self):
        result = build_backtest_review(_report(accuracy=0.70, skipped_rows=2))
        assert result["needs_review"] is True

    def test_mixed_with_skipped_rows_sets_needs_review(self):
        result = build_backtest_review(_report(accuracy=0.50, skipped_rows=1))
        assert result["needs_review"] is True

    def test_needs_review_is_bool(self):
        result = build_backtest_review(_report())
        assert isinstance(result["needs_review"], bool)


# ---------------------------------------------------------------------------
# skipped_row_flag behavior
# ---------------------------------------------------------------------------


class TestSkippedRowFlag:
    def test_zero_skipped_rows_flag_is_false(self):
        result = build_backtest_review(_report(skipped_rows=0))
        assert result["skipped_row_flag"] is False

    def test_one_skipped_row_flag_is_true(self):
        result = build_backtest_review(_report(skipped_rows=1))
        assert result["skipped_row_flag"] is True

    def test_many_skipped_rows_flag_is_true(self):
        result = build_backtest_review(_report(skipped_rows=99))
        assert result["skipped_row_flag"] is True

    def test_skipped_row_flag_is_bool(self):
        result = build_backtest_review(_report())
        assert isinstance(result["skipped_row_flag"], bool)


# ---------------------------------------------------------------------------
# Exact return shape
# ---------------------------------------------------------------------------


class TestReturnShape:
    def test_returns_exactly_five_keys(self):
        result = build_backtest_review(_report())
        assert set(result.keys()) == {
            "review_status",
            "needs_review",
            "skipped_row_flag",
            "evaluated_rows",
            "accuracy",
        }

    def test_returns_plain_dict(self):
        result = build_backtest_review(_report())
        assert type(result) is dict

    def test_review_status_is_str(self):
        result = build_backtest_review(_report())
        assert isinstance(result["review_status"], str)

    def test_review_status_is_in_valid_statuses(self):
        result = build_backtest_review(_report())
        assert result["review_status"] in VALID_REVIEW_STATUSES


# ---------------------------------------------------------------------------
# Mirrored evaluated_rows and accuracy values
# ---------------------------------------------------------------------------


class TestMirroredValues:
    def test_evaluated_rows_mirrored_in_output(self):
        result = build_backtest_review(_report(evaluated_rows=42))
        assert result["evaluated_rows"] == 42

    def test_accuracy_mirrored_in_output(self):
        result = build_backtest_review(_report(accuracy=0.65))
        assert abs(result["accuracy"] - 0.65) < 1e-12

    def test_accuracy_none_mirrored_in_output(self):
        result = build_backtest_review(_report(accuracy=None))
        assert result["accuracy"] is None

    def test_accuracy_is_float_in_output_when_not_none(self):
        result = build_backtest_review(_report(accuracy=0.7))
        assert isinstance(result["accuracy"], float)


# ---------------------------------------------------------------------------
# No banned imports / no runtime coupling
# ---------------------------------------------------------------------------


class TestNoBannedImports:
    def _get_source(self):
        import backtest_review
        path = Path(inspect.getfile(backtest_review))
        return path.read_text()

    def _get_ast_imports(self):
        source = self._get_source()
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module.split(".")[0])
        return names

    def test_no_database_import(self):
        assert "database" not in self._get_ast_imports()

    def test_no_sqlite3_import(self):
        assert "sqlite3" not in self._get_ast_imports()

    def test_no_backtest_report_import(self):
        assert "backtest_report" not in self._get_ast_imports()

    def test_no_candidate_evaluation_import(self):
        assert "candidate_evaluation" not in self._get_ast_imports()

    def test_no_review_taxonomy_import(self):
        assert "review_taxonomy" not in self._get_ast_imports()

    def test_no_review_notes_import(self):
        assert "review_notes" not in self._get_ast_imports()

    def test_no_odds_import(self):
        assert "odds" not in self._get_ast_imports()

    def test_no_edge_import(self):
        assert "edge" not in self._get_ast_imports()

    def test_no_json_import(self):
        assert "json" not in self._get_ast_imports()

    def test_no_filesystem_access_needed(self):
        result = build_backtest_review(_report())
        assert isinstance(result, dict)

    def test_no_database_access_needed(self):
        result = build_backtest_review(_report(evaluated_rows=10, accuracy=0.5))
        assert result["review_status"] == "mixed"


# ---------------------------------------------------------------------------
# No betting recommendation / lock / parlay language
# ---------------------------------------------------------------------------


class TestNoBettingLanguage:
    def test_return_keys_contain_no_betting_language(self):
        forbidden = {"recommendation", "lock", "parlay", "bet", "pick"}
        result = build_backtest_review(_report())
        for key in result:
            assert key not in forbidden, f"Forbidden key in result: {key!r}"

    def test_review_status_values_contain_no_betting_language(self):
        forbidden = {"recommendation", "lock", "parlay", "bet", "pick"}
        for status in VALID_REVIEW_STATUSES:
            assert status not in forbidden, f"Forbidden value in statuses: {status!r}"

    def test_module_docstring_does_not_recommend_bets(self):
        import backtest_review
        doc = (backtest_review.__doc__ or "").lower()
        assert "lock" not in doc
        assert "parlay" not in doc
        assert "recommendation" not in doc


# ---------------------------------------------------------------------------
# Integration with build_backtest_report
# ---------------------------------------------------------------------------


class TestIntegrationWithBacktestReport:
    def test_accepts_real_backtest_report_output_empty(self):
        from backtest_report import build_backtest_report
        report = build_backtest_report([])
        result = build_backtest_review(report)
        assert result["review_status"] == "insufficient_data"
        assert result["needs_review"] is True
        assert result["evaluated_rows"] == 0
        assert result["accuracy"] is None

    def test_accepts_real_backtest_report_output_with_rows(self):
        from backtest_report import build_backtest_report
        from historical_replay import ReplayRow

        rows = [
            ReplayRow(
                match_id=str(i),
                market="home_win",
                selection="home_win",
                model_probability=0.7,
                actual_label="home_win",
                correct=True,
                probability_assigned_to_actual=0.7,
                model_version="0.2.3",
                run_id="run_test",
                predicted_at="2026-06-29T00:00:00",
            )
            for i in range(10)
        ]
        report = build_backtest_report(rows)
        result = build_backtest_review(report)
        assert result["review_status"] == "strong"
        assert result["evaluated_rows"] == 10
        assert result["accuracy"] == 1.0
        assert result["needs_review"] is False
        assert result["skipped_row_flag"] is False

    def test_real_report_with_skipped_rows_sets_flag(self):
        from backtest_report import build_backtest_report
        from historical_replay import ReplayRow

        valid_rows = [
            ReplayRow(
                match_id=str(i),
                market="home_win",
                selection="home_win",
                model_probability=0.7,
                actual_label="home_win",
                correct=True,
                probability_assigned_to_actual=0.7,
                model_version="0.2.3",
                run_id="run_test",
                predicted_at="2026-06-29T00:00:00",
            )
            for i in range(10)
        ]
        skipped = ReplayRow(
            match_id="skip",
            market="home_win",
            selection="home_win",
            model_probability=None,
            actual_label="home_win",
            correct=False,
            probability_assigned_to_actual=None,
            model_version=None,
            run_id=None,
            predicted_at=None,
        )
        report = build_backtest_report(valid_rows + [skipped])
        result = build_backtest_review(report)
        assert result["skipped_row_flag"] is True
        assert result["needs_review"] is True
