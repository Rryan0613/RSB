import math


class OddsValidationError(ValueError):
    pass


def _reject_non_numeric(value, name: str) -> None:
    if isinstance(value, bool):
        raise OddsValidationError(f"{name} must not be a bool")
    if not isinstance(value, (int, float)):
        raise OddsValidationError(
            f"{name} must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise OddsValidationError(f"{name} must not be NaN")
    if math.isinf(value):
        raise OddsValidationError(f"{name} must not be infinite")


def american_to_implied_probability(odds) -> float:
    _reject_non_numeric(odds, "odds")
    if odds == 0:
        raise OddsValidationError("American odds must not be zero")
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def decimal_to_implied_probability(odds) -> float:
    _reject_non_numeric(odds, "odds")
    if odds <= 1.0:
        raise OddsValidationError(
            f"Decimal odds must be greater than 1.0, got {odds!r}"
        )
    return 1.0 / odds


def fractional_to_implied_probability(numerator, denominator) -> float:
    _reject_non_numeric(numerator, "numerator")
    _reject_non_numeric(denominator, "denominator")
    if numerator <= 0:
        raise OddsValidationError(
            f"numerator must be greater than 0, got {numerator!r}"
        )
    if denominator <= 0:
        raise OddsValidationError(
            f"denominator must be greater than 0, got {denominator!r}"
        )
    return denominator / (numerator + denominator)


def validate_probability(probability) -> float:
    _reject_non_numeric(probability, "probability")
    if probability < 0:
        raise OddsValidationError(
            f"probability must be >= 0, got {probability!r}"
        )
    if probability > 1:
        raise OddsValidationError(
            f"probability must be <= 1, got {probability!r}"
        )
    return float(probability)


def american_to_decimal_odds(odds) -> float:
    _reject_non_numeric(odds, "odds")
    if odds == 0:
        raise OddsValidationError("American odds must not be zero")
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def decimal_to_american_odds(odds) -> float:
    _reject_non_numeric(odds, "odds")
    if odds <= 1.0:
        raise OddsValidationError(
            f"Decimal odds must be greater than 1.0, got {odds!r}"
        )
    if odds >= 2.0:
        return (odds - 1.0) * 100.0
    return -100.0 / (odds - 1.0)
