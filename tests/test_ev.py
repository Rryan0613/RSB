import pytest

from odds import OddsValidationError
from ev import (
    EVValidationError,
    calculate_expected_value,
    american_to_decimal,
    implied_probability,
    ev_per_unit,
    edge,
)
from odds import american_to_decimal_odds, american_to_implied_probability


# ---------------------------------------------------------------------------
# EVValidationError
# ---------------------------------------------------------------------------

def test_ev_validation_error_is_value_error():
    assert issubclass(EVValidationError, ValueError)


# ---------------------------------------------------------------------------
# calculate_expected_value — valid behavior
# ---------------------------------------------------------------------------

def test_ev_positive_when_model_beats_implied():
    # model_prob=0.60, decimal_odds=2.0: 0.60 * 2.0 - 1.0 = 0.20
    assert calculate_expected_value(0.60, 2.0) == pytest.approx(0.20)


def test_ev_negative_when_model_below_implied():
    # model_prob=0.40, decimal_odds=2.0: 0.40 * 2.0 - 1.0 = -0.20
    assert calculate_expected_value(0.40, 2.0) == pytest.approx(-0.20)


def test_ev_zero_at_breakeven():
    # model_prob=0.50, decimal_odds=2.0: 0.50 * 2.0 - 1.0 = 0.0
    assert calculate_expected_value(0.50, 2.0) == pytest.approx(0.0)


def test_ev_model_prob_boundary_zero():
    # 0.0 * 2.5 - 1.0 = -1.0
    assert calculate_expected_value(0.0, 2.5) == pytest.approx(-1.0)


def test_ev_model_prob_boundary_one():
    # 1.0 * 2.5 - 1.0 = 1.5
    assert calculate_expected_value(1.0, 2.5) == pytest.approx(1.5)


def test_ev_integer_model_probability():
    assert calculate_expected_value(1, 2.0) == pytest.approx(1.0)


def test_ev_integer_decimal_odds():
    assert calculate_expected_value(0.5, 2) == pytest.approx(0.0)


def test_ev_returns_float():
    assert type(calculate_expected_value(0.50, 2.0)) is float


def test_ev_exact_formula():
    mp = 0.55
    dec = 2.5
    assert calculate_expected_value(mp, dec) == mp * dec - 1.0


def test_ev_large_decimal_odds():
    # model_prob=0.10, decimal_odds=12.0: 0.10 * 12.0 - 1.0 = 0.20
    assert calculate_expected_value(0.10, 12.0) == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# invalid model_probability — raises OddsValidationError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [True, False])
def test_ev_rejects_bool_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_expected_value(value, 2.0)


@pytest.mark.parametrize("value", ["0.5", None, [0.5]])
def test_ev_rejects_non_numeric_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_expected_value(value, 2.0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_ev_rejects_nan_and_inf_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_expected_value(value, 2.0)


@pytest.mark.parametrize("value", [-0.01, -1.0])
def test_ev_rejects_model_probability_below_0(value):
    with pytest.raises(OddsValidationError):
        calculate_expected_value(value, 2.0)


@pytest.mark.parametrize("value", [1.01, 2.0])
def test_ev_rejects_model_probability_above_1(value):
    with pytest.raises(OddsValidationError):
        calculate_expected_value(value, 2.0)


# ---------------------------------------------------------------------------
# invalid decimal_odds — raises EVValidationError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [True, False])
def test_ev_rejects_bool_decimal_odds(value):
    with pytest.raises(EVValidationError):
        calculate_expected_value(0.5, value)


@pytest.mark.parametrize("value", ["2.0", None, [2.0]])
def test_ev_rejects_non_numeric_decimal_odds(value):
    with pytest.raises(EVValidationError):
        calculate_expected_value(0.5, value)


@pytest.mark.parametrize("value", [float("nan")])
def test_ev_rejects_nan_decimal_odds(value):
    with pytest.raises(EVValidationError):
        calculate_expected_value(0.5, value)


@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_ev_rejects_inf_decimal_odds(value):
    with pytest.raises(EVValidationError):
        calculate_expected_value(0.5, value)


def test_ev_rejects_decimal_odds_exactly_1_0():
    with pytest.raises(EVValidationError):
        calculate_expected_value(0.5, 1.0)


@pytest.mark.parametrize("value", [0.5, 0.0, -1.0])
def test_ev_rejects_decimal_odds_below_1_0(value):
    with pytest.raises(EVValidationError):
        calculate_expected_value(0.5, value)


# ---------------------------------------------------------------------------
# compatibility wrappers — american_to_decimal
# ---------------------------------------------------------------------------

def test_compat_american_to_decimal_positive():
    assert american_to_decimal(150) == pytest.approx(american_to_decimal_odds(150))


def test_compat_american_to_decimal_negative():
    assert american_to_decimal(-120) == pytest.approx(american_to_decimal_odds(-120))


def test_compat_american_to_decimal_returns_float():
    assert type(american_to_decimal(100)) is float


def test_compat_american_to_decimal_rejects_zero():
    with pytest.raises(OddsValidationError):
        american_to_decimal(0)


def test_compat_american_to_decimal_rejects_bool():
    with pytest.raises(OddsValidationError):
        american_to_decimal(True)


# ---------------------------------------------------------------------------
# compatibility wrappers — implied_probability
# ---------------------------------------------------------------------------

def test_compat_implied_probability_positive_odds():
    assert implied_probability(150) == pytest.approx(american_to_implied_probability(150))


def test_compat_implied_probability_negative_odds():
    assert implied_probability(-120) == pytest.approx(american_to_implied_probability(-120))


def test_compat_implied_probability_returns_float():
    assert type(implied_probability(100)) is float


def test_compat_implied_probability_rejects_zero():
    with pytest.raises(OddsValidationError):
        implied_probability(0)


def test_compat_implied_probability_rejects_bool():
    with pytest.raises(OddsValidationError):
        implied_probability(True)


# ---------------------------------------------------------------------------
# compatibility wrappers — ev_per_unit
# ---------------------------------------------------------------------------

def test_compat_ev_per_unit_equals_calculate_expected_value():
    mp = 0.60
    odds = -120
    dec = american_to_decimal_odds(odds)
    assert ev_per_unit(mp, odds) == pytest.approx(calculate_expected_value(mp, dec))


def test_compat_ev_per_unit_returns_float():
    assert type(ev_per_unit(0.60, -120)) is float


def test_compat_ev_per_unit_rejects_invalid_odds():
    with pytest.raises(OddsValidationError):
        ev_per_unit(0.60, 0)


def test_compat_ev_per_unit_rejects_invalid_model_probability():
    with pytest.raises(OddsValidationError):
        ev_per_unit(True, -120)


# ---------------------------------------------------------------------------
# compatibility wrappers — edge
# ---------------------------------------------------------------------------

def test_compat_edge_equals_model_minus_implied():
    mp = 0.60
    odds = -120
    assert edge(mp, odds) == pytest.approx(mp - american_to_implied_probability(odds))


def test_compat_edge_returns_float():
    assert type(edge(0.60, -120)) is float


def test_compat_edge_rejects_invalid_model_probability():
    with pytest.raises(OddsValidationError):
        edge(True, -120)


def test_compat_edge_rejects_invalid_odds():
    with pytest.raises(OddsValidationError):
        edge(0.60, 0)


# ---------------------------------------------------------------------------
# runtime compatibility — all legacy names are importable and callable
# ---------------------------------------------------------------------------

def test_legacy_names_are_importable():
    from ev import american_to_decimal, implied_probability, ev_per_unit, edge
    assert callable(american_to_decimal)
    assert callable(implied_probability)
    assert callable(ev_per_unit)
    assert callable(edge)


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_ev_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "ev.py"
    tree = ast.parse(src.read_text())
    banned = {"sqlite3", "database", "json", "subprocess", "pathlib",
              "run_slate", "market_selector", "slate_odds", "simulator",
              "model", "features", "backtest", "historical_replay"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
