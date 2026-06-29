import math

from odds import american_to_decimal_odds, american_to_implied_probability, validate_probability


class EVValidationError(ValueError):
    pass


def _validate_decimal_odds(value):
    if isinstance(value, bool):
        raise EVValidationError("decimal_odds must not be a bool")
    if not isinstance(value, (int, float)):
        raise EVValidationError(
            f"decimal_odds must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise EVValidationError("decimal_odds must not be NaN")
    if math.isinf(value):
        raise EVValidationError("decimal_odds must not be infinite")
    if value <= 1.0:
        raise EVValidationError(
            f"decimal_odds must be greater than 1.0, got {value!r}"
        )
    return float(value)


def calculate_expected_value(model_probability, decimal_odds) -> float:
    model_probability = validate_probability(model_probability)
    decimal_odds = _validate_decimal_odds(decimal_odds)
    return model_probability * decimal_odds - 1.0


def american_to_decimal(odds) -> float:
    return american_to_decimal_odds(odds)


def implied_probability(odds) -> float:
    return american_to_implied_probability(odds)


def ev_per_unit(model_probability, odds) -> float:
    decimal_odds = american_to_decimal_odds(odds)
    return calculate_expected_value(model_probability, decimal_odds)


def edge(model_probability, odds) -> float:
    model_probability = validate_probability(model_probability)
    implied = american_to_implied_probability(odds)
    return model_probability - implied
