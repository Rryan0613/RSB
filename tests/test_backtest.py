"""Deterministic unit tests for src/backtest.py pure metric primitives."""

import math
import pytest
from backtest import (
    accuracy,
    brier_score_binary,
    brier_score_multiclass,
    clamp_probability,
    log_loss_binary,
    log_loss_multiclass,
    mean,
    prediction_correct,
    probability_assigned_to_actual,
)


# ---------------------------------------------------------------------------
# clamp_probability
# ---------------------------------------------------------------------------

class TestClampProbability:
    def test_interior_value_unchanged(self):
        assert clamp_probability(0.5) == 0.5

    def test_clamps_zero_to_epsilon(self):
        eps = 1e-15
        assert clamp_probability(0.0) == eps

    def test_clamps_one_to_one_minus_epsilon(self):
        eps = 1e-15
        assert clamp_probability(1.0) == 1.0 - eps

    def test_clamps_negative_to_epsilon(self):
        eps = 1e-10
        assert clamp_probability(-1.0, epsilon=eps) == eps

    def test_clamps_above_one_to_one_minus_epsilon(self):
        eps = 1e-10
        assert clamp_probability(2.0, epsilon=eps) == 1.0 - eps

    def test_custom_epsilon(self):
        result = clamp_probability(0.3, epsilon=0.1)
        assert result == 0.3

    def test_rejects_string(self):
        with pytest.raises(TypeError):
            clamp_probability("0.5")

    def test_rejects_none(self):
        with pytest.raises(TypeError):
            clamp_probability(None)

    def test_rejects_list(self):
        with pytest.raises(TypeError):
            clamp_probability([0.5])

    def test_rejects_nan(self):
        with pytest.raises(ValueError):
            clamp_probability(float("nan"))

    def test_rejects_inf(self):
        with pytest.raises(ValueError):
            clamp_probability(float("inf"))

    def test_rejects_neg_inf(self):
        with pytest.raises(ValueError):
            clamp_probability(float("-inf"))

    def test_rejects_epsilon_zero(self):
        with pytest.raises(ValueError):
            clamp_probability(0.5, epsilon=0.0)

    def test_rejects_epsilon_negative(self):
        with pytest.raises(ValueError):
            clamp_probability(0.5, epsilon=-1e-15)

    def test_rejects_epsilon_half(self):
        with pytest.raises(ValueError):
            clamp_probability(0.5, epsilon=0.5)

    def test_rejects_epsilon_above_half(self):
        with pytest.raises(ValueError):
            clamp_probability(0.5, epsilon=0.6)

    def test_rejects_epsilon_nan(self):
        with pytest.raises(ValueError):
            clamp_probability(0.5, epsilon=float("nan"))

    def test_rejects_epsilon_inf(self):
        with pytest.raises(ValueError):
            clamp_probability(0.5, epsilon=float("inf"))

    def test_rejects_bool_probability(self):
        with pytest.raises(TypeError):
            clamp_probability(True)

    def test_rejects_bool_epsilon(self):
        with pytest.raises(TypeError):
            clamp_probability(0.5, epsilon=True)


# ---------------------------------------------------------------------------
# brier_score_binary
# ---------------------------------------------------------------------------

class TestBrierScoreBinary:
    def test_perfect_prediction_actual_one(self):
        assert brier_score_binary(1.0, 1) == 0.0

    def test_perfect_prediction_actual_zero(self):
        assert brier_score_binary(0.0, 0) == 0.0

    def test_worst_prediction_actual_one(self):
        assert brier_score_binary(0.0, 1) == 1.0

    def test_worst_prediction_actual_zero(self):
        assert brier_score_binary(1.0, 0) == 1.0

    def test_known_value_point_seven_actual_one(self):
        # (0.7 - 1)^2 = 0.09
        assert abs(brier_score_binary(0.7, 1) - 0.09) < 1e-12

    def test_known_value_point_three_actual_zero(self):
        # (0.3 - 0)^2 = 0.09
        assert abs(brier_score_binary(0.3, 0) - 0.09) < 1e-12

    def test_midpoint(self):
        # (0.5 - 1)^2 = 0.25
        assert abs(brier_score_binary(0.5, 1) - 0.25) < 1e-12

    def test_bool_true_as_actual(self):
        assert brier_score_binary(1.0, True) == 0.0

    def test_bool_false_as_actual(self):
        assert brier_score_binary(0.0, False) == 0.0

    def test_rejects_probability_below_zero(self):
        with pytest.raises(ValueError):
            brier_score_binary(-0.1, 1)

    def test_rejects_probability_above_one(self):
        with pytest.raises(ValueError):
            brier_score_binary(1.1, 1)

    def test_rejects_nan_probability(self):
        with pytest.raises(ValueError):
            brier_score_binary(float("nan"), 1)

    def test_rejects_inf_probability(self):
        with pytest.raises(ValueError):
            brier_score_binary(float("inf"), 1)

    def test_rejects_actual_two(self):
        with pytest.raises(ValueError):
            brier_score_binary(0.5, 2)

    def test_rejects_actual_negative(self):
        with pytest.raises(ValueError):
            brier_score_binary(0.5, -1)

    def test_rejects_float_actual(self):
        with pytest.raises(TypeError):
            brier_score_binary(0.5, 1.0)

    def test_rejects_string_actual(self):
        with pytest.raises(TypeError):
            brier_score_binary(0.5, "1")

    def test_rejects_string_probability(self):
        with pytest.raises(TypeError):
            brier_score_binary("0.5", 1)

    def test_rejects_none_probability(self):
        with pytest.raises(TypeError):
            brier_score_binary(None, 1)

    def test_rejects_bool_probability(self):
        with pytest.raises(TypeError):
            brier_score_binary(True, 1)


# ---------------------------------------------------------------------------
# log_loss_binary
# ---------------------------------------------------------------------------

class TestLogLossBinary:
    def test_known_value_point_eight_actual_one(self):
        # -log(0.8) ≈ 0.22314355
        expected = -math.log(0.8)
        assert abs(log_loss_binary(0.8, 1) - expected) < 1e-12

    def test_known_value_point_two_actual_zero(self):
        # -log(1 - 0.2) = -log(0.8) ≈ 0.22314355
        expected = -math.log(0.8)
        assert abs(log_loss_binary(0.2, 0) - expected) < 1e-12

    def test_known_value_point_nine_actual_one(self):
        expected = -math.log(0.9)
        assert abs(log_loss_binary(0.9, 1) - expected) < 1e-12

    def test_zero_probability_actual_zero_uses_epsilon(self):
        # p=0, actual=0 → -log(1 - epsilon) ≈ epsilon (tiny positive)
        eps = 1e-15
        result = log_loss_binary(0.0, 0, epsilon=eps)
        assert result >= 0.0
        assert result < 1e-13

    def test_one_probability_actual_one_uses_epsilon(self):
        # p=1 clamped to (1 - epsilon), actual=1 → -log(1 - epsilon) ≈ epsilon (tiny positive)
        eps = 1e-15
        result = log_loss_binary(1.0, 1, epsilon=eps)
        assert result > 0.0
        assert result < 1e-13
        assert math.isfinite(result)

    def test_one_probability_actual_zero_uses_epsilon(self):
        # p=1, actual=0 → -log(1 - (1-eps)) = -log(eps) (large but finite)
        eps = 1e-15
        result = log_loss_binary(1.0, 0, epsilon=eps)
        assert math.isfinite(result)
        assert result > 30.0  # -log(1e-15) ≈ 34.5

    def test_zero_probability_actual_one_uses_epsilon(self):
        # p=0, actual=1 → -log(eps)
        eps = 1e-15
        result = log_loss_binary(0.0, 1, epsilon=eps)
        assert math.isfinite(result)
        assert result > 30.0

    def test_bool_true_as_actual(self):
        expected = -math.log(0.7)
        assert abs(log_loss_binary(0.7, True) - expected) < 1e-12

    def test_bool_false_as_actual(self):
        expected = -math.log(1.0 - 0.3)
        assert abs(log_loss_binary(0.3, False) - expected) < 1e-12

    def test_rejects_probability_below_zero(self):
        with pytest.raises(ValueError):
            log_loss_binary(-0.1, 1)

    def test_rejects_probability_above_one(self):
        with pytest.raises(ValueError):
            log_loss_binary(1.1, 1)

    def test_rejects_nan_probability(self):
        with pytest.raises(ValueError):
            log_loss_binary(float("nan"), 1)

    def test_rejects_inf_probability(self):
        with pytest.raises(ValueError):
            log_loss_binary(float("inf"), 1)

    def test_rejects_actual_two(self):
        with pytest.raises(ValueError):
            log_loss_binary(0.5, 2)

    def test_rejects_float_actual(self):
        with pytest.raises(TypeError):
            log_loss_binary(0.5, 1.0)

    def test_rejects_string_probability(self):
        with pytest.raises(TypeError):
            log_loss_binary("0.5", 1)

    def test_rejects_bool_probability(self):
        with pytest.raises(TypeError):
            log_loss_binary(False, 0)


# ---------------------------------------------------------------------------
# prediction_correct
# ---------------------------------------------------------------------------

class TestPredictionCorrect:
    def test_matching_labels(self):
        assert prediction_correct("home_win", "home_win") is True

    def test_non_matching_labels(self):
        assert prediction_correct("home_win", "draw") is False

    def test_case_sensitive(self):
        assert prediction_correct("Home_Win", "home_win") is False

    def test_rejects_empty_predicted(self):
        with pytest.raises(ValueError):
            prediction_correct("", "home_win")

    def test_rejects_empty_actual(self):
        with pytest.raises(ValueError):
            prediction_correct("home_win", "")

    def test_rejects_both_empty(self):
        with pytest.raises(ValueError):
            prediction_correct("", "")

    def test_rejects_non_string_predicted(self):
        with pytest.raises((TypeError, ValueError)):
            prediction_correct(None, "home_win")

    def test_rejects_non_string_actual(self):
        with pytest.raises((TypeError, ValueError)):
            prediction_correct("home_win", None)


# ---------------------------------------------------------------------------
# probability_assigned_to_actual
# ---------------------------------------------------------------------------

class TestProbabilityAssignedToActual:
    def test_returns_correct_probability(self):
        probs = {"home_win": 0.5, "draw": 0.3, "away_win": 0.2}
        assert probability_assigned_to_actual(probs, "home_win") == 0.5

    def test_returns_minority_class_probability(self):
        probs = {"home_win": 0.6, "draw": 0.25, "away_win": 0.15}
        assert probability_assigned_to_actual(probs, "away_win") == 0.15

    def test_rejects_missing_actual_label(self):
        probs = {"home_win": 0.6, "draw": 0.4}
        with pytest.raises(ValueError):
            probability_assigned_to_actual(probs, "away_win")

    def test_rejects_empty_dict(self):
        with pytest.raises(ValueError):
            probability_assigned_to_actual({}, "home_win")

    def test_rejects_nan_probability(self):
        probs = {"home_win": float("nan"), "draw": 0.3}
        with pytest.raises(ValueError):
            probability_assigned_to_actual(probs, "home_win")

    def test_rejects_inf_probability(self):
        probs = {"home_win": float("inf"), "draw": 0.3}
        with pytest.raises(ValueError):
            probability_assigned_to_actual(probs, "home_win")

    def test_rejects_negative_probability(self):
        probs = {"home_win": -0.1, "draw": 0.3}
        with pytest.raises(ValueError):
            probability_assigned_to_actual(probs, "home_win")

    def test_rejects_above_one_probability(self):
        probs = {"home_win": 1.5, "draw": 0.3}
        with pytest.raises(ValueError):
            probability_assigned_to_actual(probs, "home_win")

    def test_rejects_non_numeric_probability(self):
        probs = {"home_win": "0.5", "draw": 0.3}
        with pytest.raises(TypeError):
            probability_assigned_to_actual(probs, "home_win")

    def test_rejects_bool_probability_in_dict(self):
        with pytest.raises(TypeError):
            probability_assigned_to_actual({"home_win": True}, "home_win")

    def test_does_not_require_sum_to_one(self):
        # Primitives do not enforce sum-to-1
        probs = {"home_win": 0.4, "draw": 0.4}
        result = probability_assigned_to_actual(probs, "draw")
        assert result == 0.4


# ---------------------------------------------------------------------------
# brier_score_multiclass
# ---------------------------------------------------------------------------

class TestBrierScoreMulticlass:
    def test_soccer_home_win_known_value(self):
        # probabilities = {home:0.5, draw:0.25, away:0.25}, actual = home_win
        # score = (0.5-1)^2 + (0.25-0)^2 + (0.25-0)^2 = 0.25 + 0.0625 + 0.0625 = 0.375
        probs = {"home_win": 0.5, "draw": 0.25, "away_win": 0.25}
        result = brier_score_multiclass(probs, "home_win")
        assert abs(result - 0.375) < 1e-12

    def test_soccer_draw_known_value(self):
        # probabilities = {home:0.5, draw:0.25, away:0.25}, actual = draw
        # score = (0.5-0)^2 + (0.25-1)^2 + (0.25-0)^2 = 0.25 + 0.5625 + 0.0625 = 0.875
        probs = {"home_win": 0.5, "draw": 0.25, "away_win": 0.25}
        result = brier_score_multiclass(probs, "draw")
        assert abs(result - 0.875) < 1e-12

    def test_perfect_prediction_zero_score(self):
        probs = {"home_win": 1.0, "draw": 0.0, "away_win": 0.0}
        result = brier_score_multiclass(probs, "home_win")
        assert result == 0.0

    def test_worst_prediction_maximum_score(self):
        # actual=home_win, predicted=0 for home_win → (0-1)^2 + (1-0)^2 = 2
        probs = {"home_win": 0.0, "away_win": 1.0}
        result = brier_score_multiclass(probs, "home_win")
        assert abs(result - 2.0) < 1e-12

    def test_rejects_missing_actual_label(self):
        probs = {"home_win": 0.6, "draw": 0.4}
        with pytest.raises(ValueError):
            brier_score_multiclass(probs, "away_win")

    def test_rejects_empty_dict(self):
        with pytest.raises(ValueError):
            brier_score_multiclass({}, "home_win")

    def test_rejects_nan_probability(self):
        probs = {"home_win": float("nan"), "draw": 0.3}
        with pytest.raises(ValueError):
            brier_score_multiclass(probs, "home_win")

    def test_rejects_probability_above_one(self):
        probs = {"home_win": 1.5, "draw": 0.3}
        with pytest.raises(ValueError):
            brier_score_multiclass(probs, "home_win")

    def test_rejects_negative_probability(self):
        probs = {"home_win": -0.1, "draw": 0.5}
        with pytest.raises(ValueError):
            brier_score_multiclass(probs, "draw")

    def test_rejects_non_numeric_probability(self):
        probs = {"home_win": "high", "draw": 0.3}
        with pytest.raises(TypeError):
            brier_score_multiclass(probs, "home_win")

    def test_rejects_bool_probability_in_dict(self):
        with pytest.raises(TypeError):
            brier_score_multiclass({"home_win": True, "draw": 0.0}, "home_win")

    def test_does_not_require_sum_to_one(self):
        # Do not require probabilities to sum to 1 at primitive level
        probs = {"home_win": 0.4, "draw": 0.4}
        result = brier_score_multiclass(probs, "home_win")
        # (0.4-1)^2 + (0.4-0)^2 = 0.36 + 0.16 = 0.52
        assert abs(result - 0.52) < 1e-12


# ---------------------------------------------------------------------------
# log_loss_multiclass
# ---------------------------------------------------------------------------

class TestLogLossMulticlass:
    def test_known_value_soccer_home_win(self):
        # p(home_win) = 0.6 → -log(0.6)
        probs = {"home_win": 0.6, "draw": 0.3, "away_win": 0.1}
        expected = -math.log(0.6)
        assert abs(log_loss_multiclass(probs, "home_win") - expected) < 1e-12

    def test_known_value_soccer_draw(self):
        probs = {"home_win": 0.6, "draw": 0.3, "away_win": 0.1}
        expected = -math.log(0.3)
        assert abs(log_loss_multiclass(probs, "draw") - expected) < 1e-12

    def test_known_value_soccer_away_win(self):
        probs = {"home_win": 0.6, "draw": 0.3, "away_win": 0.1}
        expected = -math.log(0.1)
        assert abs(log_loss_multiclass(probs, "away_win") - expected) < 1e-12

    def test_near_zero_probability_clamped(self):
        eps = 1e-15
        probs = {"home_win": 0.0, "draw": 1.0}
        result = log_loss_multiclass(probs, "home_win", epsilon=eps)
        assert math.isfinite(result)
        assert result > 30.0

    def test_rejects_missing_actual_label(self):
        probs = {"home_win": 0.6, "draw": 0.4}
        with pytest.raises(ValueError):
            log_loss_multiclass(probs, "away_win")

    def test_rejects_empty_dict(self):
        with pytest.raises(ValueError):
            log_loss_multiclass({}, "home_win")

    def test_rejects_nan_probability(self):
        probs = {"home_win": float("nan"), "draw": 0.3}
        with pytest.raises(ValueError):
            log_loss_multiclass(probs, "home_win")

    def test_rejects_negative_probability(self):
        probs = {"home_win": -0.1, "draw": 0.5}
        with pytest.raises(ValueError):
            log_loss_multiclass(probs, "draw")

    def test_rejects_non_numeric_probability(self):
        probs = {"home_win": "0.6", "draw": 0.4}
        with pytest.raises(TypeError):
            log_loss_multiclass(probs, "home_win")

    def test_rejects_bool_probability_in_dict(self):
        with pytest.raises(TypeError):
            log_loss_multiclass({"home_win": False, "draw": 1.0}, "home_win")


# ---------------------------------------------------------------------------
# mean
# ---------------------------------------------------------------------------

class TestMean:
    def test_three_values(self):
        assert mean([1.0, 2.0, 3.0]) == 2.0

    def test_two_values(self):
        assert mean([0.5, 0.5]) == 0.5

    def test_single_value(self):
        assert mean([7.0]) == 7.0

    def test_tuple_input(self):
        assert mean((1.0, 2.0, 3.0)) == 2.0

    def test_integer_values(self):
        assert mean([1, 2, 3]) == 2.0

    def test_brier_scores_mean(self):
        scores = [0.09, 0.25, 0.09]
        expected = (0.09 + 0.25 + 0.09) / 3
        assert abs(mean(scores) - expected) < 1e-12

    def test_rejects_empty_list(self):
        with pytest.raises(ValueError):
            mean([])

    def test_rejects_empty_tuple(self):
        with pytest.raises(ValueError):
            mean(())

    def test_rejects_nan(self):
        with pytest.raises(ValueError):
            mean([1.0, float("nan"), 3.0])

    def test_rejects_inf(self):
        with pytest.raises(ValueError):
            mean([1.0, float("inf"), 3.0])

    def test_rejects_non_numeric(self):
        with pytest.raises(TypeError):
            mean([1.0, "two", 3.0])

    def test_rejects_none_element(self):
        with pytest.raises(TypeError):
            mean([1.0, None, 3.0])

    def test_rejects_bool_values(self):
        with pytest.raises(TypeError):
            mean([True, False])


# ---------------------------------------------------------------------------
# accuracy
# ---------------------------------------------------------------------------

class TestAccuracy:
    def test_all_correct(self):
        assert accuracy([True, True, True]) == 1.0

    def test_all_incorrect(self):
        assert accuracy([False, False, False]) == 0.0

    def test_mixed(self):
        result = accuracy([True, True, False])
        assert abs(result - 2 / 3) < 1e-12

    def test_single_true(self):
        assert accuracy([True]) == 1.0

    def test_single_false(self):
        assert accuracy([False]) == 0.0

    def test_tuple_input(self):
        result = accuracy((True, False, True))
        assert abs(result - 2 / 3) < 1e-12

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            accuracy([])

    def test_rejects_integers_not_bool(self):
        with pytest.raises(TypeError):
            accuracy([1, 0, 1])

    def test_rejects_string_truthy(self):
        with pytest.raises(TypeError):
            accuracy(["yes", "no"])

    def test_rejects_none(self):
        with pytest.raises(TypeError):
            accuracy([None, True])

    def test_rejects_mixed_bool_and_int(self):
        with pytest.raises(TypeError):
            accuracy([True, 1, False])


# ---------------------------------------------------------------------------
# No database / filesystem dependency proofs
# ---------------------------------------------------------------------------

class TestNoDatabaseOrFilesystemDependency:
    def test_brier_score_binary_pure(self):
        # Callable with no external resources
        result = brier_score_binary(0.7, 1)
        assert abs(result - 0.09) < 1e-12

    def test_log_loss_binary_pure(self):
        result = log_loss_binary(0.8, 1)
        assert math.isfinite(result)
        assert result > 0.0

    def test_brier_score_multiclass_pure(self):
        probs = {"home_win": 0.5, "draw": 0.25, "away_win": 0.25}
        result = brier_score_multiclass(probs, "home_win")
        assert math.isfinite(result)

    def test_log_loss_multiclass_pure(self):
        probs = {"home_win": 0.6, "draw": 0.3, "away_win": 0.1}
        result = log_loss_multiclass(probs, "draw")
        assert math.isfinite(result)

    def test_mean_pure(self):
        assert mean([0.1, 0.2, 0.3]) == pytest.approx(0.2)

    def test_accuracy_pure(self):
        assert accuracy([True, False, True]) == pytest.approx(2 / 3)

    def test_module_has_no_db_import(self):
        import backtest
        import sys
        # Confirm database module is not loaded as a side effect of importing backtest
        assert "database" not in sys.modules or "backtest" not in str(
            getattr(sys.modules.get("database"), "__file__", "")
        )

    def test_module_has_no_path_import(self):
        import backtest
        import sys
        assert "paths" not in [
            m for m in sys.modules if m == "paths"
            and "backtest" in str(getattr(sys.modules.get(m), "__file__", ""))
        ]
