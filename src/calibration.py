"""Pure calibration diagnostic primitives.

Reliability binning and the summary statistics derived from it. No database,
filesystem, network, or non-stdlib dependency, and no domain knowledge about
any particular sport or outcome space.

This module deliberately ships no default bin edges. Where to place bins
depends entirely on how the caller's predicted probabilities are distributed,
so a default here would silently encode an assumption about someone else's
data. Callers own their edges and record the ones they used.
"""

import math


class CalibrationValidationError(ValueError):
    pass


RELIABILITY_BIN_FIELD_ORDER = (
    "bin_index",
    "lower_edge",
    "upper_edge",
    "count",
    "mean_predicted_probability",
    "observed_frequency",
    "calibration_gap",
)

_EXPECTED_BIN_FIELDS = frozenset(RELIABILITY_BIN_FIELD_ORDER)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_bin_edges(bin_edges) -> tuple:
    if not isinstance(bin_edges, (list, tuple)):
        raise CalibrationValidationError(
            f"bin_edges must be a list or tuple, got {type(bin_edges).__name__!r}"
        )
    if len(bin_edges) < 2:
        raise CalibrationValidationError(
            f"bin_edges must contain at least 2 edges, got {len(bin_edges)}"
        )

    edges = []
    for index, edge in enumerate(bin_edges):
        if not _is_number(edge):
            raise CalibrationValidationError(
                f"bin_edges[{index}] must be numeric, got {type(edge).__name__!r}"
            )
        number = float(edge)
        if not math.isfinite(number):
            raise CalibrationValidationError(
                f"bin_edges[{index}] must be finite, got {edge!r}"
            )
        edges.append(number)

    for index in range(len(edges) - 1):
        if edges[index] >= edges[index + 1]:
            raise CalibrationValidationError(
                f"bin_edges must be strictly increasing; edge {index} "
                f"({edges[index]!r}) is not less than edge {index + 1} "
                f"({edges[index + 1]!r})"
            )

    if edges[0] != 0.0:
        raise CalibrationValidationError(
            f"bin_edges must start at 0.0, got {edges[0]!r}"
        )
    if edges[-1] != 1.0:
        raise CalibrationValidationError(
            f"bin_edges must end at 1.0, got {edges[-1]!r}"
        )
    return tuple(edges)


def _validate_pairs(pairs) -> list:
    if not isinstance(pairs, (list, tuple)):
        raise CalibrationValidationError(
            f"pairs must be a list or tuple, got {type(pairs).__name__!r}"
        )

    validated = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise CalibrationValidationError(
                f"pairs[{index}] must be a 2-item sequence of "
                f"(predicted_probability, occurred)"
            )
        probability, occurred = pair
        if not _is_number(probability):
            raise CalibrationValidationError(
                f"pairs[{index}] predicted_probability must be numeric, got "
                f"{type(probability).__name__!r}"
            )
        number = float(probability)
        if not math.isfinite(number):
            raise CalibrationValidationError(
                f"pairs[{index}] predicted_probability must be finite, got "
                f"{probability!r}"
            )
        if not (0.0 <= number <= 1.0):
            raise CalibrationValidationError(
                f"pairs[{index}] predicted_probability must be in [0, 1], got "
                f"{probability!r}"
            )
        # A real bool, not an int that happens to be 0 or 1: an outcome flag
        # arriving as an int usually means a label was passed where a
        # membership test was intended.
        if not isinstance(occurred, bool):
            raise CalibrationValidationError(
                f"pairs[{index}] occurred must be a bool, got "
                f"{type(occurred).__name__!r}"
            )
        validated.append((number, occurred))
    return validated


def _bin_index_for(probability: float, edges: tuple) -> int:
    """Half-open [lower, upper) placement, except the final bin, which is
    closed [lower, 1.0] so that a probability of exactly 1.0 has a home."""
    last = len(edges) - 2
    for index in range(last + 1):
        if probability < edges[index + 1]:
            return index
    return last


def build_reliability_bins(pairs, *, bin_edges) -> list:
    """Bin (predicted_probability, occurred) pairs into a reliability curve.

    `bin_edges` is required and has no default: see the module docstring.

    Empty bins are emitted with `count = 0` and `None` statistics rather than
    dropped, so the bin structure is identical for every model scored against
    the same edges. That is what makes two reliability curves comparable.
    """
    edges = _validate_bin_edges(bin_edges)
    validated = _validate_pairs(pairs)

    bin_count = len(edges) - 1
    probabilities = [[] for _ in range(bin_count)]
    occurrences = [0] * bin_count

    for probability, occurred in validated:
        index = _bin_index_for(probability, edges)
        probabilities[index].append(probability)
        if occurred:
            occurrences[index] += 1

    bins = []
    for index in range(bin_count):
        count = len(probabilities[index])
        if count == 0:
            mean_predicted = None
            observed = None
            gap = None
        else:
            mean_predicted = math.fsum(probabilities[index]) / count
            observed = occurrences[index] / count
            gap = observed - mean_predicted
        values = {
            "bin_index": index,
            "lower_edge": edges[index],
            "upper_edge": edges[index + 1],
            "count": count,
            "mean_predicted_probability": mean_predicted,
            "observed_frequency": observed,
            "calibration_gap": gap,
        }
        bins.append({field: values[field] for field in RELIABILITY_BIN_FIELD_ORDER})
    return bins


# Gaps are recomputed from values the builder derived in one step, so any
# disagreement beyond floating-point noise means the record was edited.
GAP_CONSISTENCY_TOLERANCE = 1e-12


def _validate_bin_scalar(value, name: str, label: str) -> float:
    if not _is_number(value):
        raise CalibrationValidationError(
            f"{label} {name} must be numeric, got {type(value).__name__!r}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise CalibrationValidationError(
            f"{label} {name} must be finite, got {value!r}"
        )
    return number


def _validate_unit_interval(value, name: str, label: str) -> float:
    number = _validate_bin_scalar(value, name, label)
    if not (0.0 <= number <= 1.0):
        raise CalibrationValidationError(
            f"{label} {name} must be in [0, 1], got {value!r}"
        )
    return number


def _validate_bins(bins) -> list:
    """Enforce the full reliability-bin contract.

    These bins arrive from outside — a caller may hand back a structure this
    module never built — so shape alone is not enough. The bins must describe a
    contiguous partition of [0, 1] whose per-bin statistics agree with each
    other, or the summary statistics computed from them are meaningless.
    """
    if not isinstance(bins, (list, tuple)):
        raise CalibrationValidationError(
            f"bins must be a list or tuple, got {type(bins).__name__!r}"
        )
    if not bins:
        raise CalibrationValidationError("bins must not be empty")

    validated = []
    for index, entry in enumerate(bins):
        label = f"bins[{index}]"
        if not isinstance(entry, dict):
            raise CalibrationValidationError(
                f"{label} must be a dict, got {type(entry).__name__!r}"
            )
        if set(entry) != _EXPECTED_BIN_FIELDS:
            missing = _EXPECTED_BIN_FIELDS - set(entry)
            extra = set(entry) - _EXPECTED_BIN_FIELDS
            raise CalibrationValidationError(
                f"{label} does not match the reliability bin contract; "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )

        bin_index = entry["bin_index"]
        # An actual int, not merely a value that compares equal to one: 0.0 == 0
        # and True == 1, so a value check alone would admit both.
        if (
            not isinstance(bin_index, int)
            or isinstance(bin_index, bool)
            or bin_index != index
        ):
            raise CalibrationValidationError(
                f"{label} bin_index must be the int {index}, got {bin_index!r}"
            )

        lower = _validate_unit_interval(entry["lower_edge"], "lower_edge", label)
        upper = _validate_unit_interval(entry["upper_edge"], "upper_edge", label)
        if lower >= upper:
            raise CalibrationValidationError(
                f"{label} lower_edge ({lower!r}) must be less than upper_edge "
                f"({upper!r})"
            )
        if index == 0 and lower != 0.0:
            raise CalibrationValidationError(
                f"{label} first lower_edge must be 0.0, got {lower!r}"
            )
        if index == len(bins) - 1 and upper != 1.0:
            raise CalibrationValidationError(
                f"{label} final upper_edge must be 1.0, got {upper!r}"
            )
        if index > 0 and lower != validated[-1]["upper_edge"]:
            raise CalibrationValidationError(
                f"{label} lower_edge ({lower!r}) does not continue from the "
                f"previous bin's upper_edge ({validated[-1]['upper_edge']!r}); "
                f"bins must partition [0, 1] contiguously"
            )

        count = entry["count"]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise CalibrationValidationError(
                f"{label} count must be a non-negative int, got {count!r}"
            )

        if count == 0:
            for name in (
                "mean_predicted_probability",
                "observed_frequency",
                "calibration_gap",
            ):
                if entry[name] is not None:
                    raise CalibrationValidationError(
                        f"{label} is empty but carries a non-null {name}"
                    )
        else:
            predicted = _validate_unit_interval(
                entry["mean_predicted_probability"],
                "mean_predicted_probability",
                label,
            )
            observed = _validate_unit_interval(
                entry["observed_frequency"], "observed_frequency", label
            )
            gap = _validate_bin_scalar(
                entry["calibration_gap"], "calibration_gap", label
            )
            if abs(gap - (observed - predicted)) > GAP_CONSISTENCY_TOLERANCE:
                raise CalibrationValidationError(
                    f"{label} calibration_gap ({gap!r}) does not equal "
                    f"observed_frequency - mean_predicted_probability "
                    f"({observed - predicted!r})"
                )
            # The mean of values drawn from [lower, upper) must itself fall in
            # that interval, with the final bin closed at 1.0 exactly as the
            # builder places it.
            final = index == len(bins) - 1
            inside = lower <= predicted <= upper if final else lower <= predicted < upper
            if not inside:
                raise CalibrationValidationError(
                    f"{label} mean_predicted_probability ({predicted!r}) lies "
                    f"outside its own bin interval "
                    f"[{lower!r}, {upper!r}{']' if final else ')'}"
                )

        validated.append(entry)
    return validated


def expected_calibration_error(bins) -> "float | None":
    """Count-weighted mean absolute calibration gap across non-empty bins.

    `None` when the bins hold no observations at all. A bin being empty is not
    the same as there being no data.
    """
    validated = _validate_bins(bins)
    total = sum(entry["count"] for entry in validated)
    if total == 0:
        return None
    weighted = math.fsum(
        entry["count"] * abs(float(entry["calibration_gap"]))
        for entry in validated
        if entry["count"] > 0
    )
    return weighted / total


def maximum_calibration_error(bins) -> "float | None":
    """Largest absolute calibration gap over non-empty bins, or `None` when the
    bins hold no observations."""
    validated = _validate_bins(bins)
    gaps = [
        abs(float(entry["calibration_gap"]))
        for entry in validated
        if entry["count"] > 0
    ]
    if not gaps:
        return None
    return max(gaps)
