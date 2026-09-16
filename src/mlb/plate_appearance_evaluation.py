"""Pure MLB plate-appearance walk-forward evaluation primitives.

Measures how well v0.3.3's per-plate-appearance categorical probabilities score
and calibrate against realized outcomes, under strict chronological
(walk-forward) information.

No filesystem, database, network, or non-stdlib dependency. See
docs/MLB_PLATE_APPEARANCE_EVALUATION_CONTRACT.md.

This module measures. It never adjusts a probability, selects a winning
configuration, or changes a v0.3.3 default.
"""

import hashlib
import json
import math
from datetime import datetime

from backtest import (
    accuracy,
    brier_score_multiclass,
    log_loss_multiclass,
    prediction_correct,
)
from calibration import (
    CalibrationValidationError,
    build_reliability_bins,
    expected_calibration_error,
    maximum_calibration_error,
)

from .plate_appearance import (
    PLATE_APPEARANCE_FIELD_ORDER,
    PLATE_APPEARANCE_SCHEMA_VERSION,
    RATE_CATEGORIES,
)
from .plate_appearance_rates import (
    RATE_ENRICHED_FIELD_ORDER,
    attach_prior_outcome_rates,
)
from .plate_appearance_probability import (
    DEFAULT_BATTER_PRIOR_STRENGTH,
    DEFAULT_LEAGUE_PRIOR_STRENGTH,
    DEFAULT_PITCHER_PRIOR_STRENGTH,
    MODEL_METHODS,
    PITCHER_DEPENDENT_METHODS,
    PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION,
    PROBABILITY_MODEL_CONFIG_VERSION,
    _BATTER_DEPENDENT_METHODS,
    build_pa_probability_distribution,
    supported_methods_for,
)


class PlateAppearanceEvaluationError(ValueError):
    pass


PA_EVALUATION_SCHEMA_VERSION = "1"

# Only completed plate appearances carry a categorical target. Incomplete PAs,
# including the `truncated_pa` provider marker, still received a well-defined
# pre-PA distribution from v0.3.3, but there is nothing to score them against.
SCORABLE_PA_STATUS = "completed"

# Recorded in every report, not selectable. Comparative metrics are always
# computed on the intersection of records every compared config supports, so
# competing configs can never be scored on different denominators. A future
# version that adds another basis must bump PA_EVALUATION_SCHEMA_VERSION.
EVALUATION_SAMPLE_BASIS = "intersection"

# Duplicated verbatim from plate_appearance_snapshot.COVERAGE_BASIS rather than
# imported: that module pulls in the filesystem/path layer and this one is
# pure. tests/test_plate_appearance_evaluation.py asserts the two never drift.
COVERAGE_BASIS = "normalized_pitch_represented_pa"

# Classwise one-vs-rest probabilities span roughly 0.0006 (catcher_interference)
# to 0.42 (field_out), with 8 of the 12 categories below 0.05, so the edges are
# skewed hard toward zero. Uniform-width bins would put almost every
# observation for a rare category in the first bin.
PA_CLASSWISE_CALIBRATION_BIN_EDGES = (
    0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 1.0,
)

# Top-label probability is the max over K categories summing to 1, so it cannot
# fall below 1/K (~0.083 for K=12) and in practice clusters around 0.30-0.55.
# The zero-skewed classwise edges would collapse every top-label observation
# into a single bin, which is why these are a separate constant.
PA_TOP_LABEL_CALIBRATION_BIN_EDGES = (
    0.0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.8, 1.0,
)

# v0.3.3 guarantees strict positivity, not any particular magnitude: its prior
# strengths accept every finite positive value, so a small but valid
# league_prior_strength can drive the realized category's probability far below
# backtest.py's default 1e-15 clamp. Clamping there would silently understate
# log loss for exactly the overconfident configurations this version exists to
# detect, so the clamp is pushed to the smallest positive representable float
# and every valid v0.3.3 probability passes through it unchanged.
_LOG_LOSS_EPSILON = math.nextafter(0.0, 1.0)

MODEL_CONFIG_FIELD_ORDER = (
    "config_id",
    "model_method",
    "model_config_version",
    "league_prior_strength",
    "batter_prior_strength",
    "pitcher_prior_strength",
)

METHOD_SUPPORT_FIELD_ORDER = (
    "model_method",
    "natively_supported_completed_pa_count",
)

COVERAGE_FIELD_ORDER = (
    "input_pa_count",
    "completed_pa_count",
    "incomplete_pa_count",
    "pitcher_rate_eligible_pa_count",
    "pitcher_rate_ineligible_pa_count",
    "intersection_pa_count",
    "zero_league_history_pa_count",
    "zero_batter_history_pa_count",
    "zero_pitcher_history_pa_count",
    "first_game_date",
    "last_game_date",
    "distinct_game_date_count",
    "distinct_calendar_month_count",
    "method_support",
    "coverage_basis",
)

RELIABILITY_BLOCK_FIELD_ORDER = (
    "bin_edges",
    "bins",
    "expected_calibration_error",
    "maximum_calibration_error",
)

CATEGORY_DIAGNOSTIC_FIELD_ORDER = (
    "category",
    "actual_count",
    "actual_frequency",
    "mean_predicted_probability",
    "calibration_gap",
    "reliability",
)

CALENDAR_MONTH_DIAGNOSTIC_FIELD_ORDER = (
    "calendar_month",
    "scored_pa_count",
    "mean_log_loss",
    "mean_brier_score",
    "accuracy",
    "zero_league_history_pa_count",
)

WINDOW_FIELD_ORDER = (
    "window",
    "first_game_date",
    "last_game_date",
    "scored_pa_count",
    "mean_log_loss",
    "mean_brier_score",
    "accuracy",
    "top_label_reliability",
    "category_diagnostics",
    "macro_classwise_expected_calibration_error",
    "calendar_month_diagnostics",
)

RESULT_FIELD_ORDER = ("config_id", "config", "windows")

REPORT_FIELD_ORDER = (
    "pa_evaluation_schema_version",
    "normalized_pa_schema_version",
    "normalized_pa_probability_schema_version",
    "sample_basis",
    "split_date",
    "classwise_bin_edges",
    "top_label_bin_edges",
    "source_snapshot_id",
    "input_content_sha256",
    "coverage",
    "model_configs",
    "results",
    "notes",
)

FULL_WINDOW = "full"
TUNING_WINDOW = "tuning"
HOLDOUT_WINDOW = "holdout"

# The nine prior_* fields v0.3.2 appends. Derived rather than restated so the
# coherence check cannot drift from the upstream contract.
_PRIOR_STATE_FIELDS = RATE_ENRICHED_FIELD_ORDER[len(PLATE_APPEARANCE_FIELD_ORDER):]

_EXPECTED_INPUT_FIELDS = frozenset(RATE_ENRICHED_FIELD_ORDER)
_EXPECTED_CONFIG_FIELDS = frozenset(MODEL_CONFIG_FIELD_ORDER)

_REPORT_NOTES = (
    "Comparative metrics are computed on the intersection sample only: every "
    "config is scored on an identical set of plate appearances.",
    "Mean multiclass log loss and mean multiclass Brier score are the primary "
    "model-comparison metrics. Accuracy is descriptive only.",
    "Expected and maximum calibration error are bin-dependent diagnostics and "
    "must never be used alone to rank or select model configurations.",
    "macro_classwise_expected_calibration_error is a summary diagnostic and "
    "can be dominated by low-frequency outcomes, which makes it misleading as "
    "a standalone number. It must not be used as a model-selection metric.",
    "Walk-forward chronology is date-granular across games: the plate "
    "appearance contract carries no game-start timestamp, so two games on the "
    "same date never inform each other's prior state in either direction.",
    "Pitcher eligibility is knowable only after the fact. When a "
    "pitcher-dependent config is present the intersection sample is not a "
    "random sample of plate appearances, and its metrics are like-for-like "
    "between methods but do not generalize to all plate appearances.",
    "Prior-state coherence validation detects a change only when it alters "
    "some retained record's regenerated prior state. It proves the supplied "
    "records are mutually consistent under the upstream rate contract; it "
    "does not prove the history is globally complete.",
)

assert set(_PRIOR_STATE_FIELDS) < _EXPECTED_INPUT_FIELDS
assert len(_PRIOR_STATE_FIELDS) == 9
assert set(PITCHER_DEPENDENT_METHODS) <= set(MODEL_METHODS)
assert set(_BATTER_DEPENDENT_METHODS) <= set(MODEL_METHODS)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mean(values) -> float:
    """Arithmetic mean over a non-empty collection, accumulated with fsum.

    Aggregation introduced by this version uses fsum so a long chronological
    history cannot accumulate ordering-dependent floating-point drift.
    `src/backtest.py` is deliberately left unchanged, so the per-record metrics
    it computes still accumulate with ordinary addition.
    """
    if not values:
        raise PlateAppearanceEvaluationError("cannot average an empty collection")
    return math.fsum(values) / len(values)


def _validate_prior_strength(value, name: str) -> float:
    if not _is_number(value):
        raise PlateAppearanceEvaluationError(
            f"{name} must be numeric, got {type(value).__name__!r}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise PlateAppearanceEvaluationError(
            f"{name} must be finite, got {value!r}"
        )
    if number <= 0.0:
        raise PlateAppearanceEvaluationError(
            f"{name} must be strictly positive, got {value!r}"
        )
    return number


def build_evaluation_model_config(
    *,
    model_method,
    league_prior_strength=DEFAULT_LEAGUE_PRIOR_STRENGTH,
    batter_prior_strength=DEFAULT_BATTER_PRIOR_STRENGTH,
    pitcher_prior_strength=DEFAULT_PITCHER_PRIOR_STRENGTH,
) -> dict:
    """Build one validated, self-describing evaluation model configuration.

    `model_method` is required and has no default, matching v0.3.3's rule that
    the most complex method can never be selected by accident.

    All three strengths are validated even when the chosen method does not
    consume them, because each has a valid default and overriding one is a
    deliberate claim. Strengths the method does not use are then recorded as
    exactly `None`, both in the record and in `config_id`, so `league_only` at
    two different batter strengths is one configuration rather than two.
    """
    if model_method not in MODEL_METHODS:
        raise PlateAppearanceEvaluationError(
            f"model_method must be one of {list(MODEL_METHODS)}, got {model_method!r}"
        )

    alpha = _validate_prior_strength(league_prior_strength, "league_prior_strength")
    kappa_batter = _validate_prior_strength(
        batter_prior_strength, "batter_prior_strength"
    )
    kappa_pitcher = _validate_prior_strength(
        pitcher_prior_strength, "pitcher_prior_strength"
    )

    uses_batter = model_method in _BATTER_DEPENDENT_METHODS
    uses_pitcher = model_method in PITCHER_DEPENDENT_METHODS

    batter = kappa_batter if uses_batter else None
    pitcher = kappa_pitcher if uses_pitcher else None

    identity = (
        f"{model_method}:{alpha!r}:{batter!r}:{pitcher!r}:"
        f"{PROBABILITY_MODEL_CONFIG_VERSION}"
    )
    config_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()

    values = {
        "config_id": config_id,
        "model_method": model_method,
        "model_config_version": PROBABILITY_MODEL_CONFIG_VERSION,
        "league_prior_strength": alpha,
        "batter_prior_strength": batter,
        "pitcher_prior_strength": pitcher,
    }
    return {field: values[field] for field in MODEL_CONFIG_FIELD_ORDER}


def _validate_config_record(config, index: int) -> dict:
    if not isinstance(config, dict):
        raise PlateAppearanceEvaluationError(
            f"model_configs[{index}] must be a dict, got {type(config).__name__!r}"
        )
    if set(config) != _EXPECTED_CONFIG_FIELDS:
        missing = _EXPECTED_CONFIG_FIELDS - set(config)
        extra = set(config) - _EXPECTED_CONFIG_FIELDS
        raise PlateAppearanceEvaluationError(
            f"model_configs[{index}] does not match the evaluation model config "
            f"contract; missing={sorted(missing)} extra={sorted(extra)}"
        )
    rebuilt = build_evaluation_model_config(
        model_method=config["model_method"],
        league_prior_strength=config["league_prior_strength"],
        batter_prior_strength=(
            config["batter_prior_strength"]
            if config["batter_prior_strength"] is not None
            else DEFAULT_BATTER_PRIOR_STRENGTH
        ),
        pitcher_prior_strength=(
            config["pitcher_prior_strength"]
            if config["pitcher_prior_strength"] is not None
            else DEFAULT_PITCHER_PRIOR_STRENGTH
        ),
    )
    if rebuilt != config:
        raise PlateAppearanceEvaluationError(
            f"model_configs[{index}] is not self-consistent; rebuilding it from "
            f"its own method and strengths produced a different record. Build "
            f"configs with build_evaluation_model_config()."
        )
    return rebuilt


def _validate_model_configs(model_configs) -> list:
    if not isinstance(model_configs, (list, tuple)):
        raise PlateAppearanceEvaluationError(
            f"model_configs must be a list or tuple, got "
            f"{type(model_configs).__name__!r}"
        )
    if not model_configs:
        raise PlateAppearanceEvaluationError("model_configs must not be empty")

    configs = []
    seen = set()
    for index, config in enumerate(model_configs):
        validated = _validate_config_record(config, index)
        if validated["config_id"] in seen:
            raise PlateAppearanceEvaluationError(
                f"duplicate config_id across model_configs: "
                f"{validated['config_id']}"
            )
        seen.add(validated["config_id"])
        configs.append(validated)
    return configs


def _strength_kwargs(config) -> dict:
    """Method-relevant strength kwargs only.

    v0.3.3's `build_pa_probability_distribution` validates every strength
    argument it receives before dispatching on method, and `None` fails that
    validation. Unused strengths are therefore omitted entirely so v0.3.3's own
    defaults apply, rather than being forwarded as `None`.
    """
    kwargs = {"league_prior_strength": config["league_prior_strength"]}
    if config["batter_prior_strength"] is not None:
        kwargs["batter_prior_strength"] = config["batter_prior_strength"]
    if config["pitcher_prior_strength"] is not None:
        kwargs["pitcher_prior_strength"] = config["pitcher_prior_strength"]
    return kwargs


def _validate_input_records(pa_records) -> list:
    if not isinstance(pa_records, (list, tuple)):
        raise PlateAppearanceEvaluationError(
            f"pa_records must be a list or tuple, got {type(pa_records).__name__!r}"
        )
    if not pa_records:
        raise PlateAppearanceEvaluationError("pa_records must not be empty")

    seen_pa_ids = set()
    snapshot_ids = set()
    for index, record in enumerate(pa_records):
        if not isinstance(record, dict):
            raise PlateAppearanceEvaluationError(
                f"pa_records[{index}] must be a dict, got {type(record).__name__!r}"
            )
        if set(record) != _EXPECTED_INPUT_FIELDS:
            missing = _EXPECTED_INPUT_FIELDS - set(record)
            extra = set(record) - _EXPECTED_INPUT_FIELDS
            raise PlateAppearanceEvaluationError(
                f"pa_records[{index}] does not match the rate-enriched plate "
                f"appearance contract; missing={sorted(missing)} "
                f"extra={sorted(extra)}"
            )
        if record["normalized_pa_schema_version"] != PLATE_APPEARANCE_SCHEMA_VERSION:
            raise PlateAppearanceEvaluationError(
                f"pa_records[{index}] normalized_pa_schema_version must be "
                f"{PLATE_APPEARANCE_SCHEMA_VERSION!r}, got "
                f"{record['normalized_pa_schema_version']!r}"
            )
        pa_id = record["rsb_pa_id"]
        if pa_id in seen_pa_ids:
            raise PlateAppearanceEvaluationError(
                f"duplicate rsb_pa_id across pa_records: {pa_id}"
            )
        seen_pa_ids.add(pa_id)
        snapshot_id = record["source_snapshot_id"]
        if not isinstance(snapshot_id, str) or not snapshot_id:
            raise PlateAppearanceEvaluationError(
                f"pa_records[{index}] source_snapshot_id must be a non-empty "
                f"string, got {snapshot_id!r}"
            )
        snapshot_ids.add(snapshot_id)

    if len(snapshot_ids) != 1:
        raise PlateAppearanceEvaluationError(
            f"pa_records must come from exactly one source snapshot, got "
            f"{len(snapshot_ids)}: {sorted(snapshot_ids)!r}"
        )
    return list(pa_records)


def _canonical_sort(records) -> list:
    return sorted(
        records,
        key=lambda r: (r["game_date"], int(r["source_game_id"]), r["at_bat_number"]),
    )


def _canonical_bytes(ordered) -> bytes:
    """Deterministic canonical serialization of a rate-enriched history.

    Records are rebuilt against RATE_ENRICHED_FIELD_ORDER, which enforces the
    exact field set, and serialized with `sort_keys=True`. Sorting keys applies
    recursively, so the nested `prior_*_outcome_counts` and
    `prior_*_outcome_rates` mappings canonicalize too: two semantically
    identical histories hash identically regardless of the insertion order of
    any mapping at any depth. List-valued fields such as `source_pitch_ids` and
    `source_pitcher_ids` keep their order, which is meaningful.
    """
    lines = []
    for record in ordered:
        rebuilt = {field: record[field] for field in RATE_ENRICHED_FIELD_ORDER}
        lines.append(
            json.dumps(
                rebuilt,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def _input_content_sha256(ordered) -> str:
    return hashlib.sha256(_canonical_bytes(ordered)).hexdigest()


def _validate_prior_state_coherence(ordered) -> None:
    """Verify the supplied prior state is exactly what v0.3.2 would produce.

    Strips each record back to the plate-appearance contract, re-runs the
    existing `attach_prior_outcome_rates`, and requires every regenerated
    `prior_*` field to match. The regenerated state is used only for this
    check; scoring continues to consume the supplied records, so this module
    never becomes a second implementation of the temporal policy.

    Float comparison is exact and safe here: each rate is a single
    deterministic `count / pa_count` division on identical integers through the
    same code path, with no accumulation or reordering.

    The guarantee is effect-based: an omission, edit, or splice is detected
    when it causes at least one RETAINED record's regenerated prior_* state to
    differ from its supplied state. A change that leaves every retained
    record's prior state untouched is invisible here, so this is prior-state
    coherence validation, NOT artifact-completeness validation. Known blind
    spots:

    - tail truncation may be undetectable, because no retained record's prior
      state depends on a dropped final date;
    - omitted incomplete plate appearances may be undetectable, because they
      never update any counter;
    - because same-date games are deliberately frozen from each other (v0.3.2
      same-day cross-game policy), an omission from a game on the final
      retained date can also be undetectable even when it is not the last
      record in canonical order, since no remaining record's priors depend on
      it.
    """
    stripped = [
        {field: record[field] for field in PLATE_APPEARANCE_FIELD_ORDER}
        for record in ordered
    ]
    # PlateAppearanceRateError from upstream propagates unwrapped: it is the
    # authoritative diagnosis of a malformed plate-appearance history.
    regenerated = attach_prior_outcome_rates(stripped)
    by_pa_id = {record["rsb_pa_id"]: record for record in regenerated}

    for record in ordered:
        pa_id = record["rsb_pa_id"]
        expected = by_pa_id.get(pa_id)
        if expected is None:
            raise PlateAppearanceEvaluationError(
                f"prior-state coherence failure: rsb_pa_id {pa_id} disappeared "
                f"when prior state was regenerated"
            )
        for field in _PRIOR_STATE_FIELDS:
            if record[field] != expected[field]:
                raise PlateAppearanceEvaluationError(
                    f"prior-state coherence failure for rsb_pa_id {pa_id}: "
                    f"supplied {field}={record[field]!r} but regenerating the "
                    f"supplied history produced {expected[field]!r}. The "
                    f"records were filtered, edited, or spliced after "
                    f"attach_prior_outcome_rates ran."
                )


def _validate_split_date(split_date):
    if split_date is None:
        return None
    if not isinstance(split_date, str):
        raise PlateAppearanceEvaluationError(
            f"split_date must be a string or None, got "
            f"{type(split_date).__name__!r}"
        )
    parts = split_date.split("-")
    if len(parts) != 3 or [len(part) for part in parts] != [4, 2, 2]:
        raise PlateAppearanceEvaluationError(
            f"split_date must be an ISO date (YYYY-MM-DD), got {split_date!r}"
        )
    if not all(part.isdigit() for part in parts):
        raise PlateAppearanceEvaluationError(
            f"split_date must be an ISO date (YYYY-MM-DD), got {split_date!r}"
        )
    # A real Gregorian date, not merely well-shaped digits: 2024-02-31 is not a
    # day. strptime matches the strict parsing the upstream normalized pitch
    # contract already applies to game_date.
    try:
        datetime.strptime(split_date, "%Y-%m-%d")
    except ValueError as exc:
        raise PlateAppearanceEvaluationError(
            f"split_date is not a valid calendar date: {split_date!r}"
        ) from exc
    return split_date


def _build_intersection_sample(ordered, configs) -> list:
    """Completed plate appearances every supplied config natively supports.

    When every config is league- or batter-only the intersection is every
    completed plate appearance. As soon as one pitcher-dependent config is
    present, records with `pitcher_rate_eligible = False` leave the sample, so
    all configs remain scored on one identical denominator.
    """
    completed = [
        record for record in ordered
        if record["pa_status"] == SCORABLE_PA_STATUS
    ]
    if not completed:
        raise PlateAppearanceEvaluationError(
            "no completed plate appearances to score: every supplied record has "
            f"pa_status != {SCORABLE_PA_STATUS!r}"
        )

    methods = [config["model_method"] for config in configs]
    sample = [
        record for record in completed
        if all(method in supported_methods_for(record) for method in methods)
    ]
    if not sample:
        pitcher_dependent = sorted(
            set(methods) & set(PITCHER_DEPENDENT_METHODS)
        )
        if pitcher_dependent:
            raise PlateAppearanceEvaluationError(
                f"the intersection sample is empty: no completed plate "
                f"appearance has pitcher_rate_eligible=True, which "
                f"{pitcher_dependent} require. Evaluate league_only/"
                f"batter_shrinkage configs instead, or supply a history "
                f"containing pitcher-attributable plate appearances."
            )
        raise PlateAppearanceEvaluationError(
            "the intersection sample is empty for the supplied model_configs"
        )
    return sample


def _partition_windows(sample, split_date) -> list:
    if split_date is None:
        return [(FULL_WINDOW, sample)]

    tuning = [record for record in sample if record["game_date"] < split_date]
    holdout = [record for record in sample if record["game_date"] >= split_date]
    observed = (sample[0]["game_date"], sample[-1]["game_date"])
    if not tuning:
        raise PlateAppearanceEvaluationError(
            f"split_date {split_date!r} leaves the tuning window empty; scored "
            f"game_date range is {observed[0]!r}..{observed[1]!r}"
        )
    if not holdout:
        raise PlateAppearanceEvaluationError(
            f"split_date {split_date!r} leaves the holdout window empty; scored "
            f"game_date range is {observed[0]!r}..{observed[1]!r}"
        )
    return [(TUNING_WINDOW, tuning), (HOLDOUT_WINDOW, holdout)]


def _top_label(probabilities) -> tuple:
    """Highest-probability category, ties broken by RATE_CATEGORIES order."""
    best = RATE_CATEGORIES[0]
    best_probability = probabilities[best]
    for category in RATE_CATEGORIES[1:]:
        if probabilities[category] > best_probability:
            best = category
            best_probability = probabilities[category]
    return best, best_probability


def _score_records(records, config) -> list:
    """One scored row per record, in canonical chronological order."""
    kwargs = _strength_kwargs(config)
    method = config["model_method"]

    scored = []
    for record in records:
        distribution = build_pa_probability_distribution(
            record, method=method, **kwargs
        )
        probabilities = distribution["probabilities"]
        actual = record["pa_outcome_category"]
        top_category, top_probability = _top_label(probabilities)
        scored.append(
            {
                "game_date": record["game_date"],
                "prior_league_pa_count": record["prior_league_pa_count"],
                "actual_category": actual,
                "probabilities": probabilities,
                "log_loss": log_loss_multiclass(
                probabilities, actual, epsilon=_LOG_LOSS_EPSILON
            ),
                "brier_score": brier_score_multiclass(probabilities, actual),
                "top_category": top_category,
                "top_probability": top_probability,
                "correct": prediction_correct(top_category, actual),
            }
        )
    return scored


def _reliability_block(pairs, bin_edges) -> dict:
    bins = build_reliability_bins(pairs, bin_edges=bin_edges)
    values = {
        "bin_edges": list(bin_edges),
        "bins": bins,
        "expected_calibration_error": expected_calibration_error(bins),
        "maximum_calibration_error": maximum_calibration_error(bins),
    }
    return {field: values[field] for field in RELIABILITY_BLOCK_FIELD_ORDER}


def _category_diagnostics(scored) -> list:
    """One row per RATE_CATEGORIES member, always all twelve, in canonical order.

    A category with zero positive occurrences is still fully diagnosed: its
    one-vs-rest pairs are all `(p, False)`, which are valid reliability
    observations. A category predicted at 3% that never happens carries a real
    -0.03 calibration gap, and hiding that behind `None` would conceal genuine
    miscalibration.
    """
    total = len(scored)
    diagnostics = []
    for category in RATE_CATEGORIES:
        pairs = [
            (row["probabilities"][category], row["actual_category"] == category)
            for row in scored
        ]
        actual_count = sum(1 for _, occurred in pairs if occurred)
        actual_frequency = actual_count / total
        mean_predicted = math.fsum(
            probability for probability, _ in pairs
        ) / total
        values = {
            "category": category,
            "actual_count": actual_count,
            "actual_frequency": actual_frequency,
            "mean_predicted_probability": mean_predicted,
            "calibration_gap": actual_frequency - mean_predicted,
            "reliability": _reliability_block(
                pairs, PA_CLASSWISE_CALIBRATION_BIN_EDGES
            ),
        }
        diagnostics.append(
            {field: values[field] for field in CATEGORY_DIAGNOSTIC_FIELD_ORDER}
        )
    return diagnostics


def _macro_classwise_ece(diagnostics) -> "float | None":
    """Arithmetic mean of the per-category ECEs.

    Deliberately unweighted: every classwise curve is built from the same
    scored sample and therefore holds the same number of observations, so a
    count weighting across classes would be an identity dressed up as a
    weighting. Within each class, ECE remains count-weighted across its bins.
    """
    values = [
        entry["reliability"]["expected_calibration_error"]
        for entry in diagnostics
        if entry["reliability"]["expected_calibration_error"] is not None
    ]
    if not values:
        return None
    return math.fsum(values) / len(values)


def _calendar_month_diagnostics(scored) -> list:
    """Fixed, non-configurable calendar-month breakdown.

    Descriptive only: it never filters a record, and the bucket size is not a
    parameter. Its purpose is to stop early cold-start plate appearances, where
    league history is thin or empty, from hiding inside a single full-history
    mean now that no burn-in filter exists.
    """
    months = {}
    for row in scored:
        months.setdefault(row["game_date"][:7], []).append(row)

    rows = []
    for month in sorted(months):
        group = months[month]
        values = {
            "calendar_month": month,
            "scored_pa_count": len(group),
            "mean_log_loss": _mean([row["log_loss"] for row in group]),
            "mean_brier_score": _mean([row["brier_score"] for row in group]),
            "accuracy": accuracy([row["correct"] for row in group]),
            "zero_league_history_pa_count": sum(
                1 for row in group if row["prior_league_pa_count"] == 0
            ),
        }
        rows.append(
            {field: values[field] for field in CALENDAR_MONTH_DIAGNOSTIC_FIELD_ORDER}
        )
    return rows


def _build_window(window_name, records, config) -> dict:
    scored = _score_records(records, config)
    diagnostics = _category_diagnostics(scored)
    top_label_pairs = [
        (row["top_probability"], row["correct"]) for row in scored
    ]
    values = {
        "window": window_name,
        "first_game_date": records[0]["game_date"],
        "last_game_date": records[-1]["game_date"],
        "scored_pa_count": len(scored),
        "mean_log_loss": _mean([row["log_loss"] for row in scored]),
        "mean_brier_score": _mean([row["brier_score"] for row in scored]),
        "accuracy": accuracy([row["correct"] for row in scored]),
        "top_label_reliability": _reliability_block(
            top_label_pairs, PA_TOP_LABEL_CALIBRATION_BIN_EDGES
        ),
        "category_diagnostics": diagnostics,
        "macro_classwise_expected_calibration_error": _macro_classwise_ece(
            diagnostics
        ),
        "calendar_month_diagnostics": _calendar_month_diagnostics(scored),
    }
    return {field: values[field] for field in WINDOW_FIELD_ORDER}


def _build_coverage(ordered, sample) -> dict:
    completed = [
        record for record in ordered
        if record["pa_status"] == SCORABLE_PA_STATUS
    ]
    eligible = sum(1 for record in ordered if record["pitcher_rate_eligible"])
    game_dates = sorted({record["game_date"] for record in ordered})

    method_support = []
    for method in MODEL_METHODS:
        supported = sum(
            1 for record in completed if method in supported_methods_for(record)
        )
        method_support.append(
            {
                field: {
                    "model_method": method,
                    "natively_supported_completed_pa_count": supported,
                }[field]
                for field in METHOD_SUPPORT_FIELD_ORDER
            }
        )

    values = {
        "input_pa_count": len(ordered),
        "completed_pa_count": len(completed),
        "incomplete_pa_count": len(ordered) - len(completed),
        "pitcher_rate_eligible_pa_count": eligible,
        "pitcher_rate_ineligible_pa_count": len(ordered) - eligible,
        "intersection_pa_count": len(sample),
        # Zero-history counts describe the scored intersection sample, not the
        # whole input: they exist to expose cold-start distortion in the
        # metrics, and only scored records reach a metric.
        "zero_league_history_pa_count": sum(
            1 for record in sample if record["prior_league_pa_count"] == 0
        ),
        "zero_batter_history_pa_count": sum(
            1 for record in sample if record["prior_batter_pa_count"] == 0
        ),
        "zero_pitcher_history_pa_count": sum(
            1 for record in sample if record["prior_pitcher_pa_count"] == 0
        ),
        "first_game_date": game_dates[0],
        "last_game_date": game_dates[-1],
        "distinct_game_date_count": len(game_dates),
        "distinct_calendar_month_count": len({date[:7] for date in game_dates}),
        "method_support": method_support,
        "coverage_basis": COVERAGE_BASIS,
    }
    return {field: values[field] for field in COVERAGE_FIELD_ORDER}


# Stored summary statistics are recomputed from the same values by the same
# code path, so agreement is exact; the tolerance guards only against future
# floating-point drift, never against a genuinely different number.
_RECOMPUTATION_TOLERANCE = 1e-12


def _require_int(value, label: str, *, minimum=0) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise PlateAppearanceEvaluationError(
            f"{label} must be an int, got {type(value).__name__!r}"
        )
    if value < minimum:
        raise PlateAppearanceEvaluationError(
            f"{label} must be >= {minimum}, got {value!r}"
        )
    return value


def _require_finite(value, label: str, *, minimum=None) -> float:
    if not _is_number(value):
        raise PlateAppearanceEvaluationError(
            f"{label} must be numeric, got {type(value).__name__!r}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise PlateAppearanceEvaluationError(
            f"{label} must be finite, got {value!r}"
        )
    if minimum is not None and number < minimum:
        raise PlateAppearanceEvaluationError(
            f"{label} must be >= {minimum}, got {value!r}"
        )
    return number


def _require_unit(value, label: str) -> float:
    number = _require_finite(value, label)
    if not (0.0 <= number <= 1.0):
        raise PlateAppearanceEvaluationError(
            f"{label} must be in [0, 1], got {value!r}"
        )
    return number


def _require_close(actual, expected, label: str) -> None:
    if abs(actual - expected) > _RECOMPUTATION_TOLERANCE:
        raise PlateAppearanceEvaluationError(
            f"{label} is {actual!r} but recomputing it from the report's own "
            f"contents gives {expected!r}"
        )


def _validate_reliability_block(block, label, expected_edges, expected_count) -> None:
    if not isinstance(block, dict) or set(block) != frozenset(
        RELIABILITY_BLOCK_FIELD_ORDER
    ):
        raise PlateAppearanceEvaluationError(
            f"{label} does not match the reliability block contract"
        )
    if block["bin_edges"] != list(expected_edges):
        raise PlateAppearanceEvaluationError(
            f"{label} bin_edges do not match the fixed edges this contract "
            f"requires"
        )
    # The calibration primitives validate the bin structure themselves, so
    # recomputation doubles as validation. Their error type is translated here
    # so the report validator presents one exception boundary.
    try:
        recomputed_ece = expected_calibration_error(block["bins"])
        recomputed_mce = maximum_calibration_error(block["bins"])
    except CalibrationValidationError as exc:
        raise PlateAppearanceEvaluationError(
            f"{label} bins are not a valid reliability curve: {exc}"
        ) from exc

    for name, recomputed in (
        ("expected_calibration_error", recomputed_ece),
        ("maximum_calibration_error", recomputed_mce),
    ):
        stored = block[name]
        if recomputed is None:
            if stored is not None:
                raise PlateAppearanceEvaluationError(
                    f"{label} {name} must be None when the bins hold no "
                    f"observations, got {stored!r}"
                )
            continue
        _require_close(
            _require_finite(stored, f"{label} {name}"), recomputed, f"{label} {name}"
        )

    total = sum(entry["count"] for entry in block["bins"])
    if total != expected_count:
        raise PlateAppearanceEvaluationError(
            f"{label} bin counts sum to {total}, expected {expected_count}"
        )


def _validate_category_diagnostics(diagnostics, scored_count, label) -> list:
    if not isinstance(diagnostics, list) or tuple(
        entry.get("category") if isinstance(entry, dict) else None
        for entry in diagnostics
    ) != RATE_CATEGORIES:
        raise PlateAppearanceEvaluationError(
            f"{label} category_diagnostics must carry every RATE_CATEGORIES "
            f"member in canonical order"
        )

    eces = []
    actual_total = 0
    for entry in diagnostics:
        name = f"{label} category {entry['category']!r}"
        if set(entry) != frozenset(CATEGORY_DIAGNOSTIC_FIELD_ORDER):
            raise PlateAppearanceEvaluationError(
                f"{name} does not match the category diagnostic contract"
            )
        actual_count = _require_int(entry["actual_count"], f"{name} actual_count")
        if actual_count > scored_count:
            raise PlateAppearanceEvaluationError(
                f"{name} actual_count ({actual_count}) exceeds the window's "
                f"scored_pa_count ({scored_count})"
            )
        actual_total += actual_count
        frequency = _require_unit(
            entry["actual_frequency"], f"{name} actual_frequency"
        )
        _require_close(
            frequency, actual_count / scored_count, f"{name} actual_frequency"
        )
        predicted = _require_unit(
            entry["mean_predicted_probability"],
            f"{name} mean_predicted_probability",
        )
        gap = _require_finite(entry["calibration_gap"], f"{name} calibration_gap")
        _require_close(gap, frequency - predicted, f"{name} calibration_gap")

        _validate_reliability_block(
            entry["reliability"],
            f"{name} reliability",
            PA_CLASSWISE_CALIBRATION_BIN_EDGES,
            scored_count,
        )
        eces.append(entry["reliability"]["expected_calibration_error"])

    if actual_total != scored_count:
        raise PlateAppearanceEvaluationError(
            f"{label} category actual_count values sum to {actual_total}, "
            f"expected {scored_count}"
        )
    return eces


def _validate_calendar_months(rows, scored_count, label) -> None:
    if not isinstance(rows, list) or not rows:
        raise PlateAppearanceEvaluationError(
            f"{label} calendar_month_diagnostics must be a non-empty list"
        )
    total = 0
    months = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != frozenset(
            CALENDAR_MONTH_DIAGNOSTIC_FIELD_ORDER
        ):
            raise PlateAppearanceEvaluationError(
                f"{label} calendar month row does not match its contract"
            )
        month = row["calendar_month"]
        if not isinstance(month, str) or len(month) != 7 or month[4] != "-":
            raise PlateAppearanceEvaluationError(
                f"{label} calendar_month must be YYYY-MM, got {month!r}"
            )
        months.append(month)
        name = f"{label} month {month!r}"
        count = _require_int(row["scored_pa_count"], f"{name} scored_pa_count", minimum=1)
        total += count
        _require_finite(row["mean_log_loss"], f"{name} mean_log_loss", minimum=0.0)
        _require_finite(row["mean_brier_score"], f"{name} mean_brier_score", minimum=0.0)
        _require_unit(row["accuracy"], f"{name} accuracy")
        zero_history = _require_int(
            row["zero_league_history_pa_count"], f"{name} zero_league_history_pa_count"
        )
        if zero_history > count:
            raise PlateAppearanceEvaluationError(
                f"{name} zero_league_history_pa_count ({zero_history}) exceeds "
                f"its own scored_pa_count ({count})"
            )
    if months != sorted(months):
        raise PlateAppearanceEvaluationError(
            f"{label} calendar_month_diagnostics must be in chronological order"
        )
    if len(set(months)) != len(months):
        raise PlateAppearanceEvaluationError(
            f"{label} calendar_month_diagnostics contains a duplicate month"
        )
    if total != scored_count:
        raise PlateAppearanceEvaluationError(
            f"{label} calendar month counts sum to {total}, expected {scored_count}"
        )


def _validate_window(window, label, expected_name) -> None:
    if not isinstance(window, dict) or set(window) != frozenset(WINDOW_FIELD_ORDER):
        raise PlateAppearanceEvaluationError(
            f"{label} does not match the window contract"
        )
    if window["window"] != expected_name:
        raise PlateAppearanceEvaluationError(
            f"{label} window must be {expected_name!r}, got {window['window']!r}"
        )
    scored = _require_int(window["scored_pa_count"], f"{label} scored_pa_count", minimum=1)
    _require_finite(window["mean_log_loss"], f"{label} mean_log_loss", minimum=0.0)
    _require_finite(window["mean_brier_score"], f"{label} mean_brier_score", minimum=0.0)
    _require_unit(window["accuracy"], f"{label} accuracy")

    for name in ("first_game_date", "last_game_date"):
        value = window[name]
        if not isinstance(value, str) or not value:
            raise PlateAppearanceEvaluationError(
                f"{label} {name} must be a non-empty string, got {value!r}"
            )
    if window["first_game_date"] > window["last_game_date"]:
        raise PlateAppearanceEvaluationError(
            f"{label} first_game_date is after last_game_date"
        )

    _validate_reliability_block(
        window["top_label_reliability"],
        f"{label} top_label_reliability",
        PA_TOP_LABEL_CALIBRATION_BIN_EDGES,
        scored,
    )
    eces = _validate_category_diagnostics(window["category_diagnostics"], scored, label)
    macro = window["macro_classwise_expected_calibration_error"]
    present = [value for value in eces if value is not None]
    if not present:
        if macro is not None:
            raise PlateAppearanceEvaluationError(
                f"{label} macro_classwise_expected_calibration_error must be None"
            )
    else:
        _require_close(
            _require_finite(
                macro, f"{label} macro_classwise_expected_calibration_error"
            ),
            math.fsum(present) / len(present),
            f"{label} macro_classwise_expected_calibration_error",
        )
    _validate_calendar_months(window["calendar_month_diagnostics"], scored, label)


def _validate_coverage(coverage) -> dict:
    if not isinstance(coverage, dict) or set(coverage) != frozenset(
        COVERAGE_FIELD_ORDER
    ):
        raise PlateAppearanceEvaluationError(
            "report coverage does not match the coverage contract"
        )
    counts = {}
    for name in (
        "input_pa_count",
        "completed_pa_count",
        "incomplete_pa_count",
        "pitcher_rate_eligible_pa_count",
        "pitcher_rate_ineligible_pa_count",
        "intersection_pa_count",
        "zero_league_history_pa_count",
        "zero_batter_history_pa_count",
        "zero_pitcher_history_pa_count",
        "distinct_game_date_count",
        "distinct_calendar_month_count",
    ):
        counts[name] = _require_int(coverage[name], f"report coverage {name}")

    if counts["completed_pa_count"] + counts["incomplete_pa_count"] != counts[
        "input_pa_count"
    ]:
        raise PlateAppearanceEvaluationError(
            "report coverage completed + incomplete must equal input_pa_count"
        )
    if counts["pitcher_rate_eligible_pa_count"] + counts[
        "pitcher_rate_ineligible_pa_count"
    ] != counts["input_pa_count"]:
        raise PlateAppearanceEvaluationError(
            "report coverage pitcher eligible + ineligible must equal "
            "input_pa_count"
        )
    if counts["intersection_pa_count"] > counts["completed_pa_count"]:
        raise PlateAppearanceEvaluationError(
            "report coverage intersection_pa_count cannot exceed "
            "completed_pa_count"
        )
    if counts["intersection_pa_count"] < 1:
        raise PlateAppearanceEvaluationError(
            "report coverage intersection_pa_count must be positive"
        )
    for name in (
        "zero_league_history_pa_count",
        "zero_batter_history_pa_count",
        "zero_pitcher_history_pa_count",
    ):
        if counts[name] > counts["intersection_pa_count"]:
            raise PlateAppearanceEvaluationError(
                f"report coverage {name} cannot exceed intersection_pa_count"
            )
    if counts["distinct_calendar_month_count"] > counts["distinct_game_date_count"]:
        raise PlateAppearanceEvaluationError(
            "report coverage distinct_calendar_month_count cannot exceed "
            "distinct_game_date_count"
        )
    for name in ("first_game_date", "last_game_date"):
        value = coverage[name]
        if not isinstance(value, str) or not value:
            raise PlateAppearanceEvaluationError(
                f"report coverage {name} must be a non-empty string, got {value!r}"
            )
    if coverage["first_game_date"] > coverage["last_game_date"]:
        raise PlateAppearanceEvaluationError(
            "report coverage first_game_date is after last_game_date"
        )

    support = coverage["method_support"]
    if not isinstance(support, list) or tuple(
        row.get("model_method") if isinstance(row, dict) else None for row in support
    ) != MODEL_METHODS:
        raise PlateAppearanceEvaluationError(
            "report coverage method_support must carry every MODEL_METHODS "
            "member in canonical order"
        )
    for row in support:
        if set(row) != frozenset(METHOD_SUPPORT_FIELD_ORDER):
            raise PlateAppearanceEvaluationError(
                f"report coverage method_support row "
                f"{row.get('model_method')!r} does not match its contract"
            )
        supported = _require_int(
            row["natively_supported_completed_pa_count"],
            f"report coverage method_support {row['model_method']!r} count",
        )
        if supported > counts["completed_pa_count"]:
            raise PlateAppearanceEvaluationError(
                f"report coverage method_support {row['model_method']!r} count "
                f"({supported}) exceeds completed_pa_count "
                f"({counts['completed_pa_count']})"
            )

    if coverage["coverage_basis"] != COVERAGE_BASIS:
        raise PlateAppearanceEvaluationError(
            f"report coverage_basis must be {COVERAGE_BASIS!r}, got "
            f"{coverage['coverage_basis']!r}"
        )
    return counts


def validate_pa_evaluation_report(report) -> dict:
    """Whole-record validator for an evaluation report.

    Fails closed on any internally inconsistent report, not merely a
    misshapen one: stored summary statistics are recomputed from the report's
    own contents and counts must reconcile across coverage, windows,
    categories, calibration bins, and calendar months. It deliberately does not
    rescore the raw plate-appearance history — that would be a second
    evaluation, not validation — so it verifies self-consistency only.

    Returns the report unchanged when valid; never repairs it.
    """
    if not isinstance(report, dict):
        raise PlateAppearanceEvaluationError(
            f"report must be a dict, got {type(report).__name__!r}"
        )
    if set(report) != frozenset(REPORT_FIELD_ORDER):
        missing = frozenset(REPORT_FIELD_ORDER) - set(report)
        extra = set(report) - frozenset(REPORT_FIELD_ORDER)
        raise PlateAppearanceEvaluationError(
            f"report does not match the evaluation report contract; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    expected_versions = {
        "pa_evaluation_schema_version": PA_EVALUATION_SCHEMA_VERSION,
        "normalized_pa_schema_version": PLATE_APPEARANCE_SCHEMA_VERSION,
        "normalized_pa_probability_schema_version": (
            PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION
        ),
    }
    for name, expected in expected_versions.items():
        if report[name] != expected:
            raise PlateAppearanceEvaluationError(
                f"report {name} must be {expected!r}, got {report[name]!r}"
            )

    if report["sample_basis"] != EVALUATION_SAMPLE_BASIS:
        raise PlateAppearanceEvaluationError(
            f"report sample_basis must be {EVALUATION_SAMPLE_BASIS!r}, got "
            f"{report['sample_basis']!r}"
        )
    split_date = _validate_split_date(report["split_date"])

    if report["classwise_bin_edges"] != list(PA_CLASSWISE_CALIBRATION_BIN_EDGES):
        raise PlateAppearanceEvaluationError(
            "report classwise_bin_edges must match "
            "PA_CLASSWISE_CALIBRATION_BIN_EDGES"
        )
    if report["top_label_bin_edges"] != list(PA_TOP_LABEL_CALIBRATION_BIN_EDGES):
        raise PlateAppearanceEvaluationError(
            "report top_label_bin_edges must match "
            "PA_TOP_LABEL_CALIBRATION_BIN_EDGES"
        )

    snapshot_id = report["source_snapshot_id"]
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise PlateAppearanceEvaluationError(
            f"report source_snapshot_id must be a non-empty string, got "
            f"{snapshot_id!r}"
        )
    digest = report["input_content_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or set(digest) - set("0123456789abcdef")
    ):
        raise PlateAppearanceEvaluationError(
            f"report input_content_sha256 must be 64 lowercase hexadecimal "
            f"characters, got {digest!r}"
        )

    counts = _validate_coverage(report["coverage"])
    configs = _validate_model_configs(report["model_configs"])
    configs_by_id = {config["config_id"]: config for config in configs}

    results = report["results"]
    if not isinstance(results, list) or len(results) != len(configs):
        raise PlateAppearanceEvaluationError(
            "report results must carry exactly one entry per model config"
        )

    expected_windows = (
        (FULL_WINDOW,) if split_date is None else (TUNING_WINDOW, HOLDOUT_WINDOW)
    )
    denominators = None
    date_ranges = None
    seen_result_ids = set()
    for index, result in enumerate(results):
        label = f"report results[{index}]"
        if not isinstance(result, dict) or set(result) != frozenset(
            RESULT_FIELD_ORDER
        ):
            raise PlateAppearanceEvaluationError(
                f"{label} does not match the result contract"
            )
        config_id = result["config_id"]
        if config_id not in configs_by_id:
            raise PlateAppearanceEvaluationError(
                f"{label} config_id {config_id!r} does not appear in the "
                f"report's model_configs"
            )
        if config_id in seen_result_ids:
            raise PlateAppearanceEvaluationError(
                f"{label} repeats config_id {config_id!r}; results must carry "
                f"exactly one entry per model config"
            )
        seen_result_ids.add(config_id)
        if result["config"] != configs_by_id[config_id]:
            raise PlateAppearanceEvaluationError(
                f"{label} config does not match the report's model_configs "
                f"entry for {config_id!r}"
            )

        windows = result["windows"]
        if not isinstance(windows, list) or len(windows) != len(expected_windows):
            raise PlateAppearanceEvaluationError(
                f"{label} windows must be {list(expected_windows)}"
            )
        for window, expected_name in zip(windows, expected_windows):
            _validate_window(
                window, f"{label} window {expected_name!r}", expected_name
            )

        scored = tuple(window["scored_pa_count"] for window in windows)
        if sum(scored) != counts["intersection_pa_count"]:
            raise PlateAppearanceEvaluationError(
                f"{label} window scored counts sum to {sum(scored)}, but "
                f"coverage intersection_pa_count is "
                f"{counts['intersection_pa_count']}; every config must be "
                f"scored on the intersection sample"
            )
        ranges = tuple(
            (window["first_game_date"], window["last_game_date"])
            for window in windows
        )
        if denominators is None:
            denominators, date_ranges = scored, ranges
        elif scored != denominators or ranges != date_ranges:
            raise PlateAppearanceEvaluationError(
                f"{label} does not share the comparative denominator and date "
                f"range of the earlier configs; intersection-only comparison "
                f"requires identical windows for every config"
            )

    # Count equality plus per-result membership still permits a duplicated
    # result to stand in for a missing one, so the correspondence is closed
    # explicitly: results and model_configs must be a bijection.
    if seen_result_ids != set(configs_by_id):
        missing = sorted(set(configs_by_id) - seen_result_ids)
        raise PlateAppearanceEvaluationError(
            f"report results must carry exactly one entry per model config; "
            f"no result was found for config_id(s) {missing}"
        )

    notes = report["notes"]
    if not isinstance(notes, list) or not notes:
        raise PlateAppearanceEvaluationError("report notes must be a non-empty list")
    for note in notes:
        if not isinstance(note, str) or not note.strip():
            raise PlateAppearanceEvaluationError(
                f"report notes entries must be non-empty strings, got {note!r}"
            )
    return report


def evaluate_pa_walk_forward(pa_records, *, model_configs, split_date=None) -> dict:
    """Evaluate v0.3.3 probabilities against realized outcomes, walk-forward.

    `pa_records` are rate-enriched plate appearances exactly as
    `attach_prior_outcome_rates` emits them. Walk-forward safety is inherited
    from that upstream contract rather than reimplemented here: every record
    already carries the batter/pitcher/league state that existed strictly
    before it. This module verifies that state is coherent, selects scorable
    targets, and measures.

    Only completed plate appearances are scorable. Comparative metrics are
    computed on the intersection of records every supplied config supports, so
    configs are never compared across different denominators; per-method
    support is reported separately in `coverage`.

    `split_date` is measurement-only. `None` gives a single exploratory
    full-history window; a supplied date splits into `tuning`
    (`game_date < split_date`) and `holdout` (`game_date >= split_date`).
    Nothing here selects a winning configuration or changes a v0.3.3 default.
    Once holdout metrics have been inspected and the compared configurations
    are then changed on the basis of those metrics, that holdout is
    contaminated for confirmatory use and a fresh future holdout is required.
    """
    records = _validate_input_records(pa_records)
    ordered = _canonical_sort(records)
    input_digest = _input_content_sha256(ordered)
    _validate_prior_state_coherence(ordered)

    configs = _validate_model_configs(model_configs)
    split = _validate_split_date(split_date)

    sample = _build_intersection_sample(ordered, configs)
    windows = _partition_windows(sample, split)

    results = []
    for config in configs:
        values = {
            "config_id": config["config_id"],
            "config": config,
            "windows": [
                _build_window(name, window_records, config)
                for name, window_records in windows
            ],
        }
        results.append({field: values[field] for field in RESULT_FIELD_ORDER})

    values = {
        "pa_evaluation_schema_version": PA_EVALUATION_SCHEMA_VERSION,
        "normalized_pa_schema_version": PLATE_APPEARANCE_SCHEMA_VERSION,
        "normalized_pa_probability_schema_version": (
            PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION
        ),
        "sample_basis": EVALUATION_SAMPLE_BASIS,
        "split_date": split,
        "classwise_bin_edges": list(PA_CLASSWISE_CALIBRATION_BIN_EDGES),
        "top_label_bin_edges": list(PA_TOP_LABEL_CALIBRATION_BIN_EDGES),
        "source_snapshot_id": ordered[0]["source_snapshot_id"],
        "input_content_sha256": input_digest,
        "coverage": _build_coverage(ordered, sample),
        "model_configs": configs,
        "results": results,
        "notes": list(_REPORT_NOTES),
    }
    report = {field: values[field] for field in REPORT_FIELD_ORDER}
    return validate_pa_evaluation_report(report)
