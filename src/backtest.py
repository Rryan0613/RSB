"""Pure backtest metric primitives. No database, filesystem, or external dependencies."""

import math


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def clamp_probability(probability: float, epsilon: float = 1e-15) -> float:
    if not _is_number(probability):
        raise TypeError(f"probability must be numeric, got {type(probability).__name__}")
    if math.isnan(probability):
        raise ValueError("probability must not be NaN")
    if math.isinf(probability):
        raise ValueError("probability must not be infinite")
    if not _is_number(epsilon):
        raise TypeError(f"epsilon must be numeric, got {type(epsilon).__name__}")
    if math.isnan(epsilon) or math.isinf(epsilon):
        raise ValueError("epsilon must be a finite number")
    if not (0 < epsilon < 0.5):
        raise ValueError(f"epsilon must be in (0, 0.5), got {epsilon}")
    return max(float(epsilon), min(1.0 - float(epsilon), float(probability)))


def _require_actual_binary(actual: "int | bool") -> int:
    if not isinstance(actual, int):
        raise TypeError(f"actual must be int or bool, got {type(actual).__name__}")
    if int(actual) not in (0, 1):
        raise ValueError(f"actual must be 0 or 1, got {actual}")
    return int(actual)


def _require_probability_in_unit_interval(value: float, name: str = "predicted_probability") -> float:
    if not _is_number(value):
        raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
    if math.isnan(value):
        raise ValueError(f"{name} must not be NaN")
    if math.isinf(value):
        raise ValueError(f"{name} must not be infinite")
    f = float(value)
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"{name} must be in [0, 1], got {f}")
    return f


def _validate_probability_dict(probabilities: "dict[str, float]") -> None:
    if not probabilities:
        raise ValueError("probabilities must not be empty")
    for label, prob in probabilities.items():
        if not _is_number(prob):
            raise TypeError(
                f"probability for '{label}' must be numeric, got {type(prob).__name__}"
            )
        if math.isnan(prob):
            raise ValueError(f"probability for '{label}' must not be NaN")
        if math.isinf(prob):
            raise ValueError(f"probability for '{label}' must not be infinite")
        if not (0.0 <= float(prob) <= 1.0):
            raise ValueError(
                f"probability for '{label}' must be in [0, 1], got {prob}"
            )


def brier_score_binary(predicted_probability: float, actual: "int | bool") -> float:
    p = _require_probability_in_unit_interval(predicted_probability)
    y = float(_require_actual_binary(actual))
    return (p - y) ** 2


def log_loss_binary(
    predicted_probability: float, actual: "int | bool", epsilon: float = 1e-15
) -> float:
    p_raw = _require_probability_in_unit_interval(predicted_probability)
    y = _require_actual_binary(actual)
    p = clamp_probability(p_raw, epsilon)
    if y == 1:
        return -math.log(p)
    return -math.log(1.0 - p)


def prediction_correct(predicted_label: str, actual_label: str) -> bool:
    if not isinstance(predicted_label, str) or not predicted_label:
        raise ValueError("predicted_label must be a non-empty string")
    if not isinstance(actual_label, str) or not actual_label:
        raise ValueError("actual_label must be a non-empty string")
    return predicted_label == actual_label


def probability_assigned_to_actual(
    probabilities: "dict[str, float]", actual_label: str
) -> float:
    _validate_probability_dict(probabilities)
    if actual_label not in probabilities:
        raise ValueError(
            f"actual_label '{actual_label}' not found in probabilities"
        )
    return float(probabilities[actual_label])


def brier_score_multiclass(
    probabilities: "dict[str, float]", actual_label: str
) -> float:
    _validate_probability_dict(probabilities)
    if actual_label not in probabilities:
        raise ValueError(
            f"actual_label '{actual_label}' not found in probabilities"
        )
    total = 0.0
    for label, prob in probabilities.items():
        y_i = 1.0 if label == actual_label else 0.0
        total += (float(prob) - y_i) ** 2
    return total


def log_loss_multiclass(
    probabilities: "dict[str, float]",
    actual_label: str,
    epsilon: float = 1e-15,
) -> float:
    _validate_probability_dict(probabilities)
    if actual_label not in probabilities:
        raise ValueError(
            f"actual_label '{actual_label}' not found in probabilities"
        )
    p_raw = float(probabilities[actual_label])
    p = clamp_probability(p_raw, epsilon)
    return -math.log(p)


def mean(values: "list[float] | tuple[float, ...]") -> float:
    if not values:
        raise ValueError("values must not be empty")
    for i, v in enumerate(values):
        if not _is_number(v):
            raise TypeError(
                f"values[{i}] must be numeric, got {type(v).__name__}"
            )
        if math.isnan(v):
            raise ValueError(f"values[{i}] must not be NaN")
        if math.isinf(v):
            raise ValueError(f"values[{i}] must not be infinite")
    return sum(float(v) for v in values) / len(values)


def accuracy(correct_values: "list[bool] | tuple[bool, ...]") -> float:
    if not correct_values:
        raise ValueError("correct_values must not be empty")
    for i, v in enumerate(correct_values):
        if not isinstance(v, bool):
            raise TypeError(
                f"correct_values[{i}] must be bool, got {type(v).__name__}"
            )
    return sum(1 for v in correct_values if v) / len(correct_values)
