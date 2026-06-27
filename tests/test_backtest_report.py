"""Deterministic unit tests for src/backtest_report.py.

Uses in-memory synthetic ReplayRow objects only.
No database access, no filesystem access, no load_replay_rows() calls.
"""

import math

import pytest
from backtest import brier_score_binary, log_loss_binary
from backtest_report import build_backtest_report
from historical_replay import ReplayRow


def _row(
    market="home_win",
    selection="home_win",
    model_probability=0.7,
    actual_label="home_win",
    correct=True,
    match_id="m1",
) -> ReplayRow:
    return ReplayRow(
        match_id=match_id,
        market=market,
        selection=selection,
        model_probability=model_probability,
        actual_label=actual_label,
        correct=correct,
        probability_assigned_to_actual=model_probability if correct else None,
        model_version="0.1.9.0",
        run_id="run_test",
        predicted_at="2026-06-27T00:00:00",
    )


def _invalid_row(**kwargs) -> ReplayRow:
    """Helper to construct a ReplayRow with deliberately invalid fields."""
    defaults = dict(
        match_id="m_inv",
        market="home_win",
        selection="home_win",
        model_probability=0.7,
        actual_label="home_win",
        correct=True,
        probability_assigned_to_actual=None,
        model_version=None,
        run_id=None,
        predicted_at=None,
    )
    defaults.update(kwargs)
    return ReplayRow(**defaults)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmpty:
    def test_zero_total_rows(self):
        report = build_backtest_report([])
        assert report["total_rows"] == 0

    def test_zero_evaluated_rows(self):
        report = build_backtest_report([])
        assert report["evaluated_rows"] == 0

    def test_zero_skipped_rows(self):
        report = build_backtest_report([])
        assert report["skipped_rows"] == 0

    def test_overall_accuracy_is_none(self):
        report = build_backtest_report([])
        assert report["overall"]["accuracy"] is None

    def test_overall_brier_is_none(self):
        report = build_backtest_report([])
        assert report["overall"]["mean_selected_brier_score"] is None

    def test_overall_log_loss_is_none(self):
        report = build_backtest_report([])
        assert report["overall"]["mean_selected_log_loss"] is None

    def test_by_market_is_empty_dict(self):
        report = build_backtest_report([])
        assert report["by_market"] == {}

    def test_notes_list_is_present(self):
        report = build_backtest_report([])
        assert isinstance(report["notes"], list)
        assert len(report["notes"]) > 0

    def test_warnings_list_is_present(self):
        report = build_backtest_report([])
        assert isinstance(report["warnings"], list)


# ---------------------------------------------------------------------------
# One correct row
# ---------------------------------------------------------------------------

class TestOneCorrectRow:
    def setup_method(self):
        self.p = 0.7
        self.row = _row(model_probability=self.p, correct=True, match_id="c1")
        self.report = build_backtest_report([self.row])

    def test_evaluated_rows_one(self):
        assert self.report["evaluated_rows"] == 1

    def test_correct_count_one(self):
        assert self.report["overall"]["correct_count"] == 1

    def test_accuracy_is_one(self):
        assert self.report["overall"]["accuracy"] == 1.0

    def test_brier_uses_model_probability_actual_one(self):
        expected = brier_score_binary(self.p, 1)
        assert abs(self.report["overall"]["mean_selected_brier_score"] - expected) < 1e-12

    def test_log_loss_uses_model_probability_actual_one(self):
        expected = log_loss_binary(self.p, 1)
        assert abs(self.report["overall"]["mean_selected_log_loss"] - expected) < 1e-12

    def test_skipped_rows_zero(self):
        assert self.report["skipped_rows"] == 0


# ---------------------------------------------------------------------------
# One incorrect row
# ---------------------------------------------------------------------------

class TestOneIncorrectRow:
    def setup_method(self):
        self.p = 0.6
        self.row = _row(
            model_probability=self.p,
            selection="home_win",
            actual_label="draw",
            correct=False,
            match_id="i1",
        )
        self.report = build_backtest_report([self.row])

    def test_evaluated_rows_one(self):
        assert self.report["evaluated_rows"] == 1

    def test_correct_count_zero(self):
        assert self.report["overall"]["correct_count"] == 0

    def test_accuracy_is_zero(self):
        assert self.report["overall"]["accuracy"] == 0.0

    def test_brier_uses_model_probability_actual_zero(self):
        expected = brier_score_binary(self.p, 0)
        assert abs(self.report["overall"]["mean_selected_brier_score"] - expected) < 1e-12

    def test_log_loss_uses_model_probability_actual_zero(self):
        expected = log_loss_binary(self.p, 0)
        assert abs(self.report["overall"]["mean_selected_log_loss"] - expected) < 1e-12


# ---------------------------------------------------------------------------
# Mixed correct and incorrect rows
# ---------------------------------------------------------------------------

class TestMixedRows:
    def setup_method(self):
        self.p1, self.p2 = 0.8, 0.4
        rows = [
            _row(model_probability=self.p1, correct=True, match_id="m1"),
            _row(
                model_probability=self.p2,
                correct=False,
                selection="home_win",
                actual_label="draw",
                match_id="m2",
            ),
        ]
        self.report = build_backtest_report(rows)

    def test_evaluated_rows_two(self):
        assert self.report["evaluated_rows"] == 2

    def test_correct_count_one(self):
        assert self.report["overall"]["correct_count"] == 1

    def test_accuracy_one_half(self):
        assert abs(self.report["overall"]["accuracy"] - 0.5) < 1e-12

    def test_mean_brier_score_known_value(self):
        expected = (brier_score_binary(self.p1, 1) + brier_score_binary(self.p2, 0)) / 2
        assert abs(self.report["overall"]["mean_selected_brier_score"] - expected) < 1e-12

    def test_mean_log_loss_known_value(self):
        expected = (log_loss_binary(self.p1, 1) + log_loss_binary(self.p2, 0)) / 2
        assert abs(self.report["overall"]["mean_selected_log_loss"] - expected) < 1e-12

    def test_three_rows_correct_count_and_accuracy(self):
        rows = [
            _row(correct=True, match_id="a"),
            _row(correct=True, match_id="b"),
            _row(correct=False, match_id="c", selection="home_win", actual_label="draw"),
        ]
        report = build_backtest_report(rows)
        assert report["overall"]["correct_count"] == 2
        assert abs(report["overall"]["accuracy"] - 2 / 3) < 1e-12


# ---------------------------------------------------------------------------
# Market grouping
# ---------------------------------------------------------------------------

class TestMarketGrouping:
    def test_two_markets_appear_in_by_market(self):
        rows = [
            _row(market="home_win", correct=True, match_id="a"),
            _row(market="home_win", correct=False, match_id="b",
                 actual_label="draw"),
            _row(market="draw", selection="draw", actual_label="draw",
                 correct=True, match_id="c"),
        ]
        report = build_backtest_report(rows)
        assert "home_win" in report["by_market"]
        assert "draw" in report["by_market"]

    def test_per_market_evaluated_rows(self):
        rows = [
            _row(market="home_win", correct=True, match_id="a"),
            _row(market="home_win", correct=False, match_id="b", actual_label="draw"),
            _row(market="draw", selection="draw", actual_label="draw",
                 correct=True, match_id="c"),
        ]
        report = build_backtest_report(rows)
        assert report["by_market"]["home_win"]["evaluated_rows"] == 2
        assert report["by_market"]["draw"]["evaluated_rows"] == 1

    def test_per_market_correct_count(self):
        rows = [
            _row(market="home_win", correct=True, match_id="a"),
            _row(market="home_win", correct=False, match_id="b", actual_label="draw"),
        ]
        report = build_backtest_report(rows)
        assert report["by_market"]["home_win"]["correct_count"] == 1

    def test_per_market_total_rows(self):
        rows = [
            _row(market="home_win", correct=True, match_id="a"),
            _row(market="home_win", correct=False, match_id="b", actual_label="draw"),
        ]
        report = build_backtest_report(rows)
        assert report["by_market"]["home_win"]["total_rows"] == 2

    def test_per_market_market_field(self):
        rows = [_row(market="away_win", selection="away_win", actual_label="away_win",
                     correct=True, match_id="x")]
        report = build_backtest_report(rows)
        assert report["by_market"]["away_win"]["market"] == "away_win"


# ---------------------------------------------------------------------------
# Skipped rows
# ---------------------------------------------------------------------------

class TestSkippedRows:
    def test_none_model_probability_skipped(self):
        r = _invalid_row(model_probability=None)
        report = build_backtest_report([r])
        assert report["skipped_rows"] == 1
        assert report["evaluated_rows"] == 0

    def test_out_of_range_probability_above_one_skipped(self):
        r = _invalid_row(model_probability=1.5)
        report = build_backtest_report([r])
        assert report["skipped_rows"] == 1

    def test_out_of_range_probability_below_zero_skipped(self):
        r = _invalid_row(model_probability=-0.1)
        report = build_backtest_report([r])
        assert report["skipped_rows"] == 1

    def test_empty_selection_skipped(self):
        r = _invalid_row(selection="", correct=False)
        report = build_backtest_report([r])
        assert report["skipped_rows"] == 1

    def test_empty_actual_label_skipped(self):
        r = _invalid_row(actual_label="", correct=False)
        report = build_backtest_report([r])
        assert report["skipped_rows"] == 1

    def test_skipped_row_adds_warning(self):
        r = _invalid_row(model_probability=None)
        report = build_backtest_report([r])
        assert len(report["warnings"]) > 0

    def test_valid_row_alongside_skipped_row(self):
        valid = _row(correct=True, match_id="v")
        invalid = _invalid_row(model_probability=None)
        report = build_backtest_report([valid, invalid])
        assert report["total_rows"] == 2
        assert report["evaluated_rows"] == 1
        assert report["skipped_rows"] == 1


# ---------------------------------------------------------------------------
# Warnings and notes content
# ---------------------------------------------------------------------------

class TestWarningsAndNotes:
    def test_notes_mention_selected_outcome(self):
        report = build_backtest_report([])
        notes_text = " ".join(report["notes"]).lower()
        assert "selected-outcome" in notes_text or "selected outcome" in notes_text

    def test_notes_mention_three_way_calibration(self):
        report = build_backtest_report([])
        notes_text = " ".join(report["notes"]).lower()
        assert "three-way" in notes_text or "calibration" in notes_text

    def test_notes_mention_not_live_betting_ready(self):
        report = build_backtest_report([])
        notes_text = " ".join(report["notes"]).lower()
        assert "live-betting-ready" in notes_text or "live betting" in notes_text

    def test_notes_mention_retrospective_or_evaluation(self):
        report = build_backtest_report([])
        notes_text = " ".join(report["notes"]).lower()
        assert "retrospective" in notes_text or "evaluation" in notes_text

    def test_overall_keys_do_not_include_forbidden_betting_language(self):
        row = _row(correct=True)
        report = build_backtest_report([row])
        forbidden = {"recommendation", "lock", "parlay", "bet"}
        for key in report["overall"]:
            assert key not in forbidden, f"Unexpected key in overall: {key}"

    def test_no_betting_recommendation_values_in_report(self):
        row = _row(correct=True)
        report = build_backtest_report([row])
        top_keys = set(report.keys())
        assert "recommendation" not in top_keys
        assert "lock" not in top_keys
        assert "parlay" not in top_keys


# ---------------------------------------------------------------------------
# No banned imports / no filesystem or database dependency
# ---------------------------------------------------------------------------

class TestNoBannedImports:
    def test_backtest_report_does_not_expose_sqlite3(self):
        import backtest_report
        assert not hasattr(backtest_report, "sqlite3")

    def test_backtest_report_does_not_expose_database(self):
        import backtest_report
        assert not hasattr(backtest_report, "database")

    def test_backtest_report_does_not_expose_json_module(self):
        import backtest_report
        assert not hasattr(backtest_report, "json")

    def test_replay_row_has_model_probability_not_predicted_probability(self):
        row = _row(model_probability=0.65, correct=True)
        assert hasattr(row, "model_probability")
        assert not hasattr(row, "predicted_probability")

    def test_build_backtest_report_uses_model_probability(self):
        p = 0.65
        row = _row(model_probability=p, correct=True)
        report = build_backtest_report([row])
        expected_brier = brier_score_binary(p, 1)
        assert abs(report["overall"]["mean_selected_brier_score"] - expected_brier) < 1e-12

    def test_no_filesystem_access_needed(self):
        # All inputs are in-memory; function completes with no I/O
        rows = [_row(match_id=str(i)) for i in range(5)]
        report = build_backtest_report(rows)
        assert report["evaluated_rows"] == 5

    def test_no_database_access_needed(self):
        # Works without any SQLite DB present
        rows = [_row(correct=False, match_id="x", actual_label="draw")]
        report = build_backtest_report(rows)
        assert report["evaluated_rows"] == 1


# ---------------------------------------------------------------------------
# Fix 1 — correctness recomputed from selection == actual_label, not row.correct
# ---------------------------------------------------------------------------

class TestRecomputeCorrectness:
    def test_matching_labels_scored_correct_even_when_row_correct_is_false(self):
        # selection == actual_label but row.correct=False — report must score as correct
        row = ReplayRow(
            match_id="m1",
            market="home_win",
            selection="home_win",
            model_probability=0.7,
            actual_label="home_win",
            correct=False,
            probability_assigned_to_actual=None,
            model_version=None,
            run_id=None,
            predicted_at=None,
        )
        report = build_backtest_report([row])
        assert report["overall"]["correct_count"] == 1
        assert report["overall"]["accuracy"] == 1.0
        expected_brier = brier_score_binary(0.7, 1)
        assert abs(report["overall"]["mean_selected_brier_score"] - expected_brier) < 1e-12
        expected_ll = log_loss_binary(0.7, 1)
        assert abs(report["overall"]["mean_selected_log_loss"] - expected_ll) < 1e-12

    def test_mismatched_labels_scored_incorrect_even_when_row_correct_is_true(self):
        # selection != actual_label but row.correct=True — report must score as incorrect
        row = ReplayRow(
            match_id="m2",
            market="home_win",
            selection="home_win",
            model_probability=0.6,
            actual_label="draw",
            correct=True,
            probability_assigned_to_actual=0.6,
            model_version=None,
            run_id=None,
            predicted_at=None,
        )
        report = build_backtest_report([row])
        assert report["overall"]["correct_count"] == 0
        assert report["overall"]["accuracy"] == 0.0
        expected_brier = brier_score_binary(0.6, 0)
        assert abs(report["overall"]["mean_selected_brier_score"] - expected_brier) < 1e-12
        expected_ll = log_loss_binary(0.6, 0)
        assert abs(report["overall"]["mean_selected_log_loss"] - expected_ll) < 1e-12


# ---------------------------------------------------------------------------
# Fix 2 — by_market includes markets with valid names even if all rows skipped
# ---------------------------------------------------------------------------

class TestByMarketAllRowsSkipped:
    def test_market_with_only_invalid_probability_appears_in_by_market(self):
        r = ReplayRow(
            match_id="m1",
            market="home_win",
            selection="home_win",
            model_probability=None,
            actual_label="home_win",
            correct=True,
            probability_assigned_to_actual=None,
            model_version=None,
            run_id=None,
            predicted_at=None,
        )
        report = build_backtest_report([r])
        assert "home_win" in report["by_market"]

    def test_all_skipped_market_has_zero_evaluated_rows(self):
        r = ReplayRow(
            match_id="m1",
            market="home_win",
            selection="home_win",
            model_probability=None,
            actual_label="home_win",
            correct=True,
            probability_assigned_to_actual=None,
            model_version=None,
            run_id=None,
            predicted_at=None,
        )
        report = build_backtest_report([r])
        mkt = report["by_market"]["home_win"]
        assert mkt["evaluated_rows"] == 0
        assert mkt["skipped_rows"] == 1
        assert mkt["total_rows"] == 1
        assert mkt["correct_count"] == 0
        assert mkt["accuracy"] is None
        assert mkt["mean_selected_brier_score"] is None
        assert mkt["mean_selected_log_loss"] is None

    def test_mixed_valid_and_skipped_market_shows_correct_counts(self):
        valid = _row(market="home_win", correct=True, match_id="v")
        invalid = ReplayRow(
            match_id="i",
            market="home_win",
            selection="home_win",
            model_probability=None,
            actual_label="home_win",
            correct=True,
            probability_assigned_to_actual=None,
            model_version=None,
            run_id=None,
            predicted_at=None,
        )
        report = build_backtest_report([valid, invalid])
        mkt = report["by_market"]["home_win"]
        assert mkt["total_rows"] == 2
        assert mkt["evaluated_rows"] == 1
        assert mkt["skipped_rows"] == 1
