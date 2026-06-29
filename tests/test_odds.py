import pytest

from odds import (
    OddsValidationError,
    american_to_decimal_odds,
    american_to_implied_probability,
    decimal_to_american_odds,
    decimal_to_implied_probability,
    fractional_to_implied_probability,
    validate_probability,
)


# ---------------------------------------------------------------------------
# american_to_implied_probability
# ---------------------------------------------------------------------------

def test_american_positive_100_returns_0_5():
    assert american_to_implied_probability(100) == pytest.approx(0.5)


def test_american_negative_100_returns_0_5():
    assert american_to_implied_probability(-100) == pytest.approx(0.5)


def test_american_plus_100_and_minus_100_are_equal():
    assert american_to_implied_probability(100) == american_to_implied_probability(-100)


def test_american_positive_150():
    assert american_to_implied_probability(150) == pytest.approx(0.4)


def test_american_negative_150():
    assert american_to_implied_probability(-150) == pytest.approx(0.6)


def test_american_positive_200():
    assert american_to_implied_probability(200) == pytest.approx(1 / 3)


def test_american_negative_200():
    assert american_to_implied_probability(-200) == pytest.approx(2 / 3)


def test_american_returns_float():
    assert type(american_to_implied_probability(100)) is float
    assert type(american_to_implied_probability(-100)) is float


def test_american_rejects_zero():
    with pytest.raises(OddsValidationError):
        american_to_implied_probability(0)


@pytest.mark.parametrize("value", [True, False])
def test_american_rejects_bool(value):
    with pytest.raises(OddsValidationError):
        american_to_implied_probability(value)


@pytest.mark.parametrize("value", ["100", None, [100]])
def test_american_rejects_non_numeric(value):
    with pytest.raises(OddsValidationError):
        american_to_implied_probability(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_american_rejects_nan_and_inf(value):
    with pytest.raises(OddsValidationError):
        american_to_implied_probability(value)


# ---------------------------------------------------------------------------
# decimal_to_implied_probability
# ---------------------------------------------------------------------------

def test_decimal_2_0_returns_0_5():
    assert decimal_to_implied_probability(2.0) == pytest.approx(0.5)


def test_decimal_1_5():
    assert decimal_to_implied_probability(1.5) == pytest.approx(2 / 3)


def test_decimal_3_0():
    assert decimal_to_implied_probability(3.0) == pytest.approx(1 / 3)


def test_decimal_returns_float():
    assert type(decimal_to_implied_probability(2.0)) is float


def test_decimal_rejects_exactly_1_0():
    with pytest.raises(OddsValidationError):
        decimal_to_implied_probability(1.0)


@pytest.mark.parametrize("value", [0.5, 0.0, -1.0])
def test_decimal_rejects_lte_1_0(value):
    with pytest.raises(OddsValidationError):
        decimal_to_implied_probability(value)


@pytest.mark.parametrize("value", [True, False])
def test_decimal_rejects_bool(value):
    with pytest.raises(OddsValidationError):
        decimal_to_implied_probability(value)


@pytest.mark.parametrize("value", ["2.0", None, [2.0]])
def test_decimal_rejects_non_numeric(value):
    with pytest.raises(OddsValidationError):
        decimal_to_implied_probability(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_decimal_rejects_nan_and_inf(value):
    with pytest.raises(OddsValidationError):
        decimal_to_implied_probability(value)


# ---------------------------------------------------------------------------
# fractional_to_implied_probability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("numerator,denominator,expected", [
    (1, 1, 0.5),
    (1, 2, 2 / 3),
    (2, 1, 1 / 3),
    (5, 2, 2 / 7),
])
def test_fractional_valid_conversions(numerator, denominator, expected):
    assert fractional_to_implied_probability(numerator, denominator) == pytest.approx(expected)


def test_fractional_accepts_float_args():
    assert fractional_to_implied_probability(2.0, 1.0) == pytest.approx(1 / 3)


def test_fractional_returns_float():
    assert type(fractional_to_implied_probability(1, 1)) is float


@pytest.mark.parametrize("numerator", [0, -1, -100])
def test_fractional_rejects_numerator_lte_zero(numerator):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(numerator, 1)


@pytest.mark.parametrize("denominator", [0, -1, -100])
def test_fractional_rejects_denominator_lte_zero(denominator):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(1, denominator)


@pytest.mark.parametrize("value", [True, False])
def test_fractional_rejects_bool_numerator(value):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(value, 1)


@pytest.mark.parametrize("value", [True, False])
def test_fractional_rejects_bool_denominator(value):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(1, value)


@pytest.mark.parametrize("value", ["1", None, [1]])
def test_fractional_rejects_non_numeric_numerator(value):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(value, 1)


@pytest.mark.parametrize("value", ["1", None, [1]])
def test_fractional_rejects_non_numeric_denominator(value):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(1, value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_fractional_rejects_nan_and_inf_numerator(value):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(value, 1)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_fractional_rejects_nan_and_inf_denominator(value):
    with pytest.raises(OddsValidationError):
        fractional_to_implied_probability(1, value)


# ---------------------------------------------------------------------------
# validate_probability
# ---------------------------------------------------------------------------

def test_validate_probability_accepts_zero():
    assert validate_probability(0) == pytest.approx(0.0)


def test_validate_probability_accepts_one():
    assert validate_probability(1) == pytest.approx(1.0)


def test_validate_probability_accepts_midrange():
    assert validate_probability(0.5) == pytest.approx(0.5)


def test_validate_probability_returns_float():
    assert type(validate_probability(0)) is float
    assert type(validate_probability(1)) is float
    assert type(validate_probability(0.75)) is float


@pytest.mark.parametrize("value", [-0.01, -1.0, -100.0])
def test_validate_probability_rejects_below_0(value):
    with pytest.raises(OddsValidationError):
        validate_probability(value)


@pytest.mark.parametrize("value", [1.01, 2.0, 100.0])
def test_validate_probability_rejects_above_1(value):
    with pytest.raises(OddsValidationError):
        validate_probability(value)


@pytest.mark.parametrize("value", [True, False])
def test_validate_probability_rejects_bool(value):
    with pytest.raises(OddsValidationError):
        validate_probability(value)


@pytest.mark.parametrize("value", ["0.5", None, [0.5]])
def test_validate_probability_rejects_non_numeric(value):
    with pytest.raises(OddsValidationError):
        validate_probability(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_validate_probability_rejects_nan_and_inf(value):
    with pytest.raises(OddsValidationError):
        validate_probability(value)


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_odds_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "odds.py"
    tree = ast.parse(src.read_text())
    banned = {"sqlite3", "database", "json", "subprocess", "pathlib"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"


# ---------------------------------------------------------------------------
# american_to_decimal_odds
# ---------------------------------------------------------------------------

def test_american_to_decimal_plus_100_returns_2_0():
    assert american_to_decimal_odds(100) == pytest.approx(2.0)


def test_american_to_decimal_minus_100_returns_2_0():
    assert american_to_decimal_odds(-100) == pytest.approx(2.0)


def test_american_to_decimal_plus_100_and_minus_100_are_equal():
    assert american_to_decimal_odds(100) == american_to_decimal_odds(-100)


def test_american_to_decimal_plus_150_returns_2_5():
    assert american_to_decimal_odds(150) == pytest.approx(2.5)


def test_american_to_decimal_minus_150():
    assert american_to_decimal_odds(-150) == pytest.approx(1.0 + 100.0 / 150.0)


def test_american_to_decimal_plus_200_returns_3_0():
    assert american_to_decimal_odds(200) == pytest.approx(3.0)


def test_american_to_decimal_minus_200():
    assert american_to_decimal_odds(-200) == pytest.approx(1.5)


def test_american_to_decimal_returns_float():
    assert type(american_to_decimal_odds(100)) is float
    assert type(american_to_decimal_odds(-100)) is float


def test_american_to_decimal_rejects_zero():
    with pytest.raises(OddsValidationError):
        american_to_decimal_odds(0)


@pytest.mark.parametrize("value", [True, False])
def test_american_to_decimal_rejects_bool(value):
    with pytest.raises(OddsValidationError):
        american_to_decimal_odds(value)


@pytest.mark.parametrize("value", ["100", None, [100]])
def test_american_to_decimal_rejects_non_numeric(value):
    with pytest.raises(OddsValidationError):
        american_to_decimal_odds(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_american_to_decimal_rejects_nan_and_inf(value):
    with pytest.raises(OddsValidationError):
        american_to_decimal_odds(value)


# ---------------------------------------------------------------------------
# decimal_to_american_odds
# ---------------------------------------------------------------------------

def test_decimal_to_american_2_0_returns_100():
    assert decimal_to_american_odds(2.0) == pytest.approx(100.0)


def test_decimal_to_american_2_5_returns_150():
    assert decimal_to_american_odds(2.5) == pytest.approx(150.0)


def test_decimal_to_american_3_0_returns_200():
    assert decimal_to_american_odds(3.0) == pytest.approx(200.0)


def test_decimal_to_american_1_5_returns_negative_200():
    assert decimal_to_american_odds(1.5) == pytest.approx(-200.0)


def test_decimal_to_american_negative_american_result():
    assert decimal_to_american_odds(1.0 + 100.0 / 150.0) == pytest.approx(-150.0)


def test_decimal_to_american_returns_float():
    assert type(decimal_to_american_odds(2.0)) is float
    assert type(decimal_to_american_odds(1.5)) is float


def test_decimal_to_american_rejects_exactly_1_0():
    with pytest.raises(OddsValidationError):
        decimal_to_american_odds(1.0)


@pytest.mark.parametrize("value", [0.5, 0.0, -1.0])
def test_decimal_to_american_rejects_lte_1_0(value):
    with pytest.raises(OddsValidationError):
        decimal_to_american_odds(value)


@pytest.mark.parametrize("value", [True, False])
def test_decimal_to_american_rejects_bool(value):
    with pytest.raises(OddsValidationError):
        decimal_to_american_odds(value)


@pytest.mark.parametrize("value", ["2.0", None, [2.0]])
def test_decimal_to_american_rejects_non_numeric(value):
    with pytest.raises(OddsValidationError):
        decimal_to_american_odds(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_decimal_to_american_rejects_nan_and_inf(value):
    with pytest.raises(OddsValidationError):
        decimal_to_american_odds(value)


def test_round_trip_positive_american_odds():
    assert decimal_to_american_odds(american_to_decimal_odds(150)) == pytest.approx(150.0)


def test_round_trip_negative_american_odds():
    assert decimal_to_american_odds(american_to_decimal_odds(-120)) == pytest.approx(-120.0)
