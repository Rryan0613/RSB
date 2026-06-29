import pytest

from edge import calculate_edge
from odds import OddsValidationError


# ---------------------------------------------------------------------------
# calculate_edge — valid behavior
# ---------------------------------------------------------------------------

def test_edge_positive():
    assert calculate_edge(0.55, 0.50) == pytest.approx(0.05)


def test_edge_negative():
    assert calculate_edge(0.45, 0.50) == pytest.approx(-0.05)


def test_edge_zero():
    assert calculate_edge(0.50, 0.50) == pytest.approx(0.0)


def test_edge_max_positive_boundary():
    assert calculate_edge(1.0, 0.0) == pytest.approx(1.0)


def test_edge_max_negative_boundary():
    assert calculate_edge(0.0, 1.0) == pytest.approx(-1.0)


def test_edge_int_inputs():
    assert calculate_edge(1, 0) == pytest.approx(1.0)


def test_edge_returns_float():
    assert type(calculate_edge(0.55, 0.50)) is float


def test_edge_no_rounding():
    assert calculate_edge(0.55, 0.50) == 0.55 - 0.50


# ---------------------------------------------------------------------------
# invalid model_probability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [True, False])
def test_edge_rejects_bool_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(value, 0.50)


@pytest.mark.parametrize("value", ["0.5", None, [0.5]])
def test_edge_rejects_non_numeric_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(value, 0.50)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_edge_rejects_nan_and_inf_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(value, 0.50)


@pytest.mark.parametrize("value", [-0.01, -1.0])
def test_edge_rejects_below_0_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(value, 0.50)


@pytest.mark.parametrize("value", [1.01, 2.0])
def test_edge_rejects_above_1_model_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(value, 0.50)


# ---------------------------------------------------------------------------
# invalid implied_probability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [True, False])
def test_edge_rejects_bool_implied_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(0.50, value)


@pytest.mark.parametrize("value", ["0.5", None, [0.5]])
def test_edge_rejects_non_numeric_implied_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(0.50, value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_edge_rejects_nan_and_inf_implied_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(0.50, value)


@pytest.mark.parametrize("value", [-0.01, -1.0])
def test_edge_rejects_below_0_implied_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(0.50, value)


@pytest.mark.parametrize("value", [1.01, 2.0])
def test_edge_rejects_above_1_implied_probability(value):
    with pytest.raises(OddsValidationError):
        calculate_edge(0.50, value)


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_edge_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "edge.py"
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
