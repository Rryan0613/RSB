"""Tests for the generic calibration diagnostic primitives."""

import math

import pytest

from calibration import (
    RELIABILITY_BIN_FIELD_ORDER,
    CalibrationValidationError,
    build_reliability_bins,
    expected_calibration_error,
    maximum_calibration_error,
)

EDGES = (0.0, 0.25, 0.5, 0.75, 1.0)


def _assert_close(actual, expected, tolerance=1e-12):
    assert abs(actual - expected) <= tolerance


# ---------------------------------------------------------------------------
# bin_edges is required and validated
# ---------------------------------------------------------------------------


def test_bin_edges_is_required():
    with pytest.raises(TypeError):
        build_reliability_bins([(0.5, True)])


def test_module_exposes_no_default_bin_edges():
    import calibration

    assert not [name for name in dir(calibration) if "DEFAULT" in name]


@pytest.mark.parametrize(
    "edges",
    [
        (0.0,),
        (),
        (0.0, 0.5, 0.5, 1.0),
        (0.0, 0.75, 0.5, 1.0),
        (0.1, 0.5, 1.0),
        (0.0, 0.5, 0.9),
        (0.0, "0.5", 1.0),
        (0.0, True, 1.0),
        (0.0, float("nan"), 1.0),
        (0.0, float("inf"), 1.0),
    ],
)
def test_invalid_bin_edges_rejected(edges):
    with pytest.raises(CalibrationValidationError):
        build_reliability_bins([(0.5, True)], bin_edges=edges)


def test_bin_edges_must_be_a_sequence():
    with pytest.raises(CalibrationValidationError):
        build_reliability_bins([(0.5, True)], bin_edges="01")


def test_two_edges_is_the_minimum_accepted():
    bins = build_reliability_bins([(0.5, True)], bin_edges=(0.0, 1.0))
    assert len(bins) == 1


# ---------------------------------------------------------------------------
# pair validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pair",
    [
        (0.5,),
        (0.5, True, 1),
        ("0.5", True),
        (True, True),
        (float("nan"), True),
        (float("inf"), True),
        (-0.01, True),
        (1.01, True),
        (0.5, 1),
        (0.5, "yes"),
        (0.5, None),
    ],
)
def test_invalid_pairs_rejected(pair):
    with pytest.raises(CalibrationValidationError):
        build_reliability_bins([pair], bin_edges=EDGES)


def test_pairs_must_be_a_sequence():
    with pytest.raises(CalibrationValidationError):
        build_reliability_bins({"a": 1}, bin_edges=EDGES)


def test_occurred_must_be_a_real_bool_not_an_int():
    with pytest.raises(CalibrationValidationError):
        build_reliability_bins([(0.5, 1)], bin_edges=EDGES)


# ---------------------------------------------------------------------------
# bin placement
# ---------------------------------------------------------------------------


def test_bins_have_the_contract_field_set_and_order():
    bins = build_reliability_bins([(0.5, True)], bin_edges=EDGES)
    for entry in bins:
        assert tuple(entry) == RELIABILITY_BIN_FIELD_ORDER


def test_placement_is_half_open_on_the_lower_edge():
    bins = build_reliability_bins([(0.25, True)], bin_edges=EDGES)
    assert bins[0]["count"] == 0
    assert bins[1]["count"] == 1


def test_final_bin_is_closed_so_probability_one_has_a_home():
    bins = build_reliability_bins([(1.0, True)], bin_edges=EDGES)
    assert bins[-1]["count"] == 1


def test_probability_zero_lands_in_the_first_bin():
    bins = build_reliability_bins([(0.0, False)], bin_edges=EDGES)
    assert bins[0]["count"] == 1


def test_edges_are_reported_on_every_bin():
    bins = build_reliability_bins([(0.5, True)], bin_edges=EDGES)
    assert [entry["lower_edge"] for entry in bins] == [0.0, 0.25, 0.5, 0.75]
    assert [entry["upper_edge"] for entry in bins] == [0.25, 0.5, 0.75, 1.0]


# ---------------------------------------------------------------------------
# empty bins keep the curve comparable
# ---------------------------------------------------------------------------


def test_empty_bins_are_emitted_with_null_statistics():
    bins = build_reliability_bins([(0.1, True)], bin_edges=EDGES)
    assert len(bins) == 4
    for entry in bins[1:]:
        assert entry["count"] == 0
        assert entry["mean_predicted_probability"] is None
        assert entry["observed_frequency"] is None
        assert entry["calibration_gap"] is None


def test_bin_structure_is_identical_across_different_data():
    sparse = build_reliability_bins([(0.1, True)], bin_edges=EDGES)
    dense = build_reliability_bins(
        [(0.1, True), (0.4, False), (0.6, True), (0.9, True)], bin_edges=EDGES
    )
    assert len(sparse) == len(dense)
    assert [entry["bin_index"] for entry in sparse] == [
        entry["bin_index"] for entry in dense
    ]


def test_no_pairs_yields_all_empty_bins():
    bins = build_reliability_bins([], bin_edges=EDGES)
    assert [entry["count"] for entry in bins] == [0, 0, 0, 0]


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------


def test_calibration_gap_is_observed_minus_predicted():
    bins = build_reliability_bins(
        [(0.1, True), (0.1, False)], bin_edges=(0.0, 1.0)
    )
    _assert_close(bins[0]["mean_predicted_probability"], 0.1)
    _assert_close(bins[0]["observed_frequency"], 0.5)
    _assert_close(bins[0]["calibration_gap"], 0.4)


def test_positive_gap_means_underconfident():
    bins = build_reliability_bins([(0.2, True)], bin_edges=(0.0, 1.0))
    assert bins[0]["calibration_gap"] > 0


def test_negative_gap_means_overconfident():
    bins = build_reliability_bins([(0.8, False)], bin_edges=(0.0, 1.0))
    assert bins[0]["calibration_gap"] < 0


def test_expected_calibration_error_is_count_weighted():
    bins = build_reliability_bins(
        [(0.1, True), (0.1, False), (0.9, True)], bin_edges=(0.0, 0.5, 1.0)
    )
    # bin 0: n=2, |gap| = |0.5 - 0.1| = 0.4 ; bin 1: n=1, |gap| = 0.1
    _assert_close(expected_calibration_error(bins), (2 * 0.4 + 1 * 0.1) / 3)


def test_maximum_calibration_error_is_the_largest_absolute_gap():
    bins = build_reliability_bins(
        [(0.1, True), (0.1, False), (0.9, True)], bin_edges=(0.0, 0.5, 1.0)
    )
    _assert_close(maximum_calibration_error(bins), 0.4)


def test_perfect_calibration_gives_zero_error():
    pairs = [(0.5, True), (0.5, False)]
    bins = build_reliability_bins(pairs, bin_edges=(0.0, 1.0))
    _assert_close(expected_calibration_error(bins), 0.0)
    _assert_close(maximum_calibration_error(bins), 0.0)


def test_statistics_are_none_only_when_there_are_no_observations():
    bins = build_reliability_bins([], bin_edges=EDGES)
    assert expected_calibration_error(bins) is None
    assert maximum_calibration_error(bins) is None


def test_all_negative_outcomes_still_produce_real_statistics():
    """Zero positives is not zero data: predicting 0.3 for something that never
    happens is measurable miscalibration."""
    bins = build_reliability_bins(
        [(0.3, False), (0.3, False)], bin_edges=(0.0, 1.0)
    )
    _assert_close(bins[0]["observed_frequency"], 0.0)
    _assert_close(bins[0]["calibration_gap"], -0.3)
    _assert_close(expected_calibration_error(bins), 0.3)
    _assert_close(maximum_calibration_error(bins), 0.3)


def test_empty_bins_do_not_dilute_the_expected_calibration_error():
    dense = build_reliability_bins([(0.1, True)], bin_edges=(0.0, 1.0))
    sparse = build_reliability_bins([(0.1, True)], bin_edges=EDGES)
    _assert_close(
        expected_calibration_error(dense), expected_calibration_error(sparse)
    )


# ---------------------------------------------------------------------------
# statistic input validation
# ---------------------------------------------------------------------------


def test_statistics_reject_non_bin_input():
    for bad in ({"a": 1}, [{"count": 1}], [1, 2, 3], "bins"):
        with pytest.raises(CalibrationValidationError):
            expected_calibration_error(bad)
        with pytest.raises(CalibrationValidationError):
            maximum_calibration_error(bad)


def test_statistics_reject_a_negative_count():
    bins = build_reliability_bins([(0.5, True)], bin_edges=(0.0, 1.0))
    bins[0]["count"] = -1
    with pytest.raises(CalibrationValidationError):
        expected_calibration_error(bins)


def test_statistics_reject_an_empty_bin_carrying_a_gap():
    bins = build_reliability_bins([(0.1, True)], bin_edges=EDGES)
    bins[3]["calibration_gap"] = 0.5
    with pytest.raises(CalibrationValidationError):
        expected_calibration_error(bins)


def test_statistics_reject_a_non_finite_gap():
    bins = build_reliability_bins([(0.5, True)], bin_edges=(0.0, 1.0))
    bins[0]["calibration_gap"] = float("nan")
    with pytest.raises(CalibrationValidationError):
        maximum_calibration_error(bins)


# ---------------------------------------------------------------------------
# determinism and purity
# ---------------------------------------------------------------------------


def test_result_is_independent_of_pair_order():
    pairs = [(0.1, True), (0.9, False), (0.4, True), (0.6, False)]
    forward = build_reliability_bins(pairs, bin_edges=EDGES)
    backward = build_reliability_bins(list(reversed(pairs)), bin_edges=EDGES)
    assert forward == backward


def test_repeated_calls_are_identical():
    pairs = [(0.13, True), (0.27, False), (0.91, True)]
    assert build_reliability_bins(pairs, bin_edges=EDGES) == build_reliability_bins(
        pairs, bin_edges=EDGES
    )


def test_inputs_are_not_mutated():
    pairs = [(0.1, True), (0.9, False)]
    snapshot = list(pairs)
    edges = list(EDGES)
    build_reliability_bins(pairs, bin_edges=edges)
    assert pairs == snapshot
    assert edges == list(EDGES)


def test_tuple_and_list_pairs_are_equivalent():
    assert build_reliability_bins(
        [(0.1, True)], bin_edges=EDGES
    ) == build_reliability_bins([[0.1, True]], bin_edges=EDGES)


def test_calibration_has_no_banned_imports():
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "calibration.py"
    tree = ast.parse(src.read_text())
    banned = {
        "requests", "urllib", "http", "socket", "pybaseball", "pandas",
        "numpy", "sklearn", "scipy", "run_slate", "database", "data_quality",
        "market_selector", "sqlite3", "paths", "mlb",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
    assert imported == {"math"}


# ---------------------------------------------------------------------------
# bin-structure invariants (bins can arrive from outside this module)
# ---------------------------------------------------------------------------


def _bins():
    return build_reliability_bins(
        [(0.1, True), (0.4, False), (0.6, True), (0.9, False)], bin_edges=EDGES
    )


def _assert_both_reject(bins):
    with pytest.raises(CalibrationValidationError):
        expected_calibration_error(bins)
    with pytest.raises(CalibrationValidationError):
        maximum_calibration_error(bins)


def test_statistics_reject_empty_bins_list():
    _assert_both_reject([])


def test_statistics_reject_out_of_sequence_bin_index():
    bins = _bins()
    bins[2]["bin_index"] = 7
    _assert_both_reject(bins)


def test_statistics_reject_non_contiguous_bins():
    bins = _bins()
    bins[1]["lower_edge"] = 0.3
    _assert_both_reject(bins)


def test_statistics_reject_a_first_edge_that_is_not_zero():
    bins = _bins()
    bins[0]["lower_edge"] = 0.05
    _assert_both_reject(bins)


def test_statistics_reject_a_final_edge_that_is_not_one():
    bins = _bins()
    bins[-1]["upper_edge"] = 0.95
    _assert_both_reject(bins)


def test_statistics_reject_inverted_edges():
    bins = _bins()
    bins[0]["lower_edge"], bins[0]["upper_edge"] = 0.25, 0.0
    _assert_both_reject(bins)


def test_statistics_reject_edges_outside_the_unit_interval():
    bins = _bins()
    bins[-1]["upper_edge"] = 1.5
    _assert_both_reject(bins)


def test_statistics_reject_a_forged_calibration_gap():
    bins = _bins()
    bins[0]["calibration_gap"] = 0.99
    _assert_both_reject(bins)


def test_statistics_reject_an_out_of_range_observed_frequency():
    bins = _bins()
    bins[0]["observed_frequency"] = 1.5
    _assert_both_reject(bins)


def test_statistics_reject_a_mean_prediction_outside_its_own_bin():
    bins = _bins()
    bins[0]["mean_predicted_probability"] = 0.9
    bins[0]["calibration_gap"] = bins[0]["observed_frequency"] - 0.9
    _assert_both_reject(bins)


def test_statistics_reject_a_populated_bin_with_null_statistics():
    bins = _bins()
    bins[0]["mean_predicted_probability"] = None
    _assert_both_reject(bins)


def test_statistics_reject_a_boolean_count():
    bins = _bins()
    bins[0]["count"] = True
    _assert_both_reject(bins)


def test_a_mean_prediction_exactly_at_one_is_valid_in_the_closed_final_bin():
    bins = build_reliability_bins([(1.0, True)], bin_edges=EDGES)
    assert expected_calibration_error(bins) == 0.0


# ---------------------------------------------------------------------------
# bin_index must be an actual int, not a value that compares equal to one
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_index", [0.0, "0", True, None, [0]])
def test_statistics_reject_a_non_int_bin_index(bad_index):
    """0.0 == 0 and True == 1, so an equality check alone would admit both."""
    bins = _bins()
    bins[0]["bin_index"] = bad_index
    _assert_both_reject(bins)


def test_statistics_reject_a_bool_bin_index_at_its_matching_position():
    """True == 1, so a bool at index 1 would slip past a pure value check."""
    bins = _bins()
    bins[1]["bin_index"] = True
    _assert_both_reject(bins)


def test_statistics_accept_a_genuine_int_bin_index():
    bins = _bins()
    assert all(isinstance(entry["bin_index"], int) for entry in bins)
    assert expected_calibration_error(bins) is not None
