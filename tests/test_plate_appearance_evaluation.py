"""Tests for the MLB plate-appearance walk-forward evaluation primitives."""

import json
import math
import random
from pathlib import Path

import pytest

from mlb.plate_appearance import (
    RATE_CATEGORIES,
    group_pitches_into_plate_appearances,
)
from mlb.plate_appearance_rates import (
    PlateAppearanceRateError,
    attach_prior_outcome_rates,
)
from mlb.plate_appearance_probability import (
    DEFAULT_BATTER_PRIOR_STRENGTH,
    DEFAULT_LEAGUE_PRIOR_STRENGTH,
    DEFAULT_PITCHER_PRIOR_STRENGTH,
    MODEL_METHODS,
    build_pa_probability_distribution,
)
from mlb.statcast_normalize import NORMALIZED_PITCH_FIELD_ORDER, build_rsb_pitch_id
from mlb.plate_appearance_evaluation import (
    CALENDAR_MONTH_DIAGNOSTIC_FIELD_ORDER,
    _mean,
    CATEGORY_DIAGNOSTIC_FIELD_ORDER,
    COVERAGE_BASIS,
    COVERAGE_FIELD_ORDER,
    EVALUATION_SAMPLE_BASIS,
    MODEL_CONFIG_FIELD_ORDER,
    PA_CLASSWISE_CALIBRATION_BIN_EDGES,
    PA_EVALUATION_SCHEMA_VERSION,
    PA_TOP_LABEL_CALIBRATION_BIN_EDGES,
    REPORT_FIELD_ORDER,
    RESULT_FIELD_ORDER,
    SCORABLE_PA_STATUS,
    WINDOW_FIELD_ORDER,
    PlateAppearanceEvaluationError,
    build_evaluation_model_config,
    evaluate_pa_walk_forward,
    validate_pa_evaluation_report,
)

SNAPSHOT_ID = "20260811T120000000000Z_abcdef012345"
K = len(RATE_CATEGORIES)


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------


def _pitch(**overrides) -> dict:
    base = {
        "source_game_id": "700001",
        "source_play_id": None,
        "game_date": "2024-04-01",
        "game_year": 2024,
        "at_bat_number": 1,
        "pitch_number": 1,
        "inning": 1,
        "inning_half": "top",
        "game_type": "R",
        "home_team": "NYY",
        "away_team": "BOS",
        "home_score": 0,
        "away_score": 0,
        "batter_id": "600001",
        "pitcher_id": "700010",
        "batter_stands": "R",
        "pitcher_throws": "L",
        "on_1b": None,
        "on_2b": None,
        "on_3b": None,
        "balls": 0,
        "strikes": 0,
        "outs": 0,
        "pitch_type": "FF",
        "pitch_name": "4-Seam Fastball",
        "release_speed": 95.1,
        "zone": 5,
        "pitch_result_type": "X",
        "pa_event_raw": None,
        "bb_type": None,
        "launch_speed": None,
        "launch_angle": None,
        "hit_distance": None,
        "snapshot_id": SNAPSHOT_ID,
        "source_provider": "baseball_savant",
        "normalized_schema_version": "1",
        "source_row_index": 0,
    }
    base.update(overrides)
    base["rsb_pitch_id"] = build_rsb_pitch_id(
        base["source_game_id"], base["at_bat_number"], base["pitch_number"]
    )
    return {field: base[field] for field in NORMALIZED_PITCH_FIELD_ORDER}


def _pa_pitches(
    *,
    game_date="2024-04-01",
    game_id="700001",
    at_bat_number=1,
    batter_id="600001",
    pitchers=("700010",),
    event="field_out",
    snapshot_id=SNAPSHOT_ID,
):
    """One plate appearance, one pitch per entry in `pitchers`.

    `event` lands on the terminal pitch; `None` leaves the PA incomplete.
    """
    pitches = []
    for index, pitcher_id in enumerate(pitchers):
        terminal = index == len(pitchers) - 1
        pitches.append(
            _pitch(
                game_date=game_date,
                source_game_id=game_id,
                at_bat_number=at_bat_number,
                pitch_number=index + 1,
                batter_id=batter_id,
                pitcher_id=pitcher_id,
                pitcher_throws="L" if pitcher_id.endswith("0") else "R",
                pa_event_raw=event if terminal else None,
                snapshot_id=snapshot_id,
            )
        )
    return pitches


_EVENTS = (
    "strikeout",
    "single",
    "field_out",
    "walk",
    "home_run",
    "double",
    "field_out",
    "strikeout",
    "single",
    "field_out",
)


def _enriched(specs) -> list:
    """Build a rate-enriched history from a list of PA spec dicts."""
    pitches = []
    for spec in specs:
        pitches.extend(_pa_pitches(**spec))
    return attach_prior_outcome_rates(group_pitches_into_plate_appearances(pitches))


def _default_specs(days=5, game_id="700001", start_day=1, month="04"):
    specs = []
    at_bat = 0
    for offset in range(days):
        day = start_day + offset
        for index, event in enumerate(_EVENTS):
            at_bat += 1
            specs.append(
                {
                    "game_date": "2024-%s-%02d" % (month, day),
                    "game_id": game_id,
                    "at_bat_number": at_bat,
                    "batter_id": "60000%d" % (index % 3 + 1),
                    "pitchers": ("70001%d" % (index % 2),),
                    "event": event,
                }
            )
    return specs


def _history(days=5):
    return _enriched(_default_specs(days=days))


def _configs(*methods):
    return [build_evaluation_model_config(model_method=method) for method in methods]


def _window(report, config_index=0, window_index=0):
    return report["results"][config_index]["windows"][window_index]


def _category(window, name):
    return next(
        entry for entry in window["category_diagnostics"] if entry["category"] == name
    )


def _assert_close(actual, expected, tolerance=1e-12):
    assert abs(actual - expected) <= tolerance


# ---------------------------------------------------------------------------
# model configuration
# ---------------------------------------------------------------------------


def test_config_has_the_contract_field_set_and_order():
    config = build_evaluation_model_config(model_method="league_only")
    assert tuple(config) == MODEL_CONFIG_FIELD_ORDER


def test_config_requires_a_model_method():
    with pytest.raises(TypeError):
        build_evaluation_model_config()


def test_config_rejects_an_unknown_method():
    with pytest.raises(PlateAppearanceEvaluationError):
        build_evaluation_model_config(model_method="deep_learning")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"league_prior_strength": 0.0},
        {"league_prior_strength": -1.0},
        {"league_prior_strength": "1.0"},
        {"league_prior_strength": True},
        {"league_prior_strength": float("nan")},
        {"league_prior_strength": float("inf")},
        {"batter_prior_strength": 0.0},
        {"pitcher_prior_strength": -5.0},
    ],
)
def test_config_rejects_invalid_strengths(kwargs):
    with pytest.raises(PlateAppearanceEvaluationError):
        build_evaluation_model_config(
            model_method="matchup_combination", **kwargs
        )


def test_unused_strengths_are_recorded_as_none():
    config = build_evaluation_model_config(model_method="league_only")
    assert config["league_prior_strength"] == DEFAULT_LEAGUE_PRIOR_STRENGTH
    assert config["batter_prior_strength"] is None
    assert config["pitcher_prior_strength"] is None


def test_batter_shrinkage_records_batter_strength_only():
    config = build_evaluation_model_config(model_method="batter_shrinkage")
    assert config["batter_prior_strength"] == DEFAULT_BATTER_PRIOR_STRENGTH
    assert config["pitcher_prior_strength"] is None


def test_matchup_records_every_strength():
    config = build_evaluation_model_config(model_method="matchup_combination")
    assert config["batter_prior_strength"] == DEFAULT_BATTER_PRIOR_STRENGTH
    assert config["pitcher_prior_strength"] == DEFAULT_PITCHER_PRIOR_STRENGTH


def test_config_id_collapses_irrelevant_strengths():
    default = build_evaluation_model_config(model_method="league_only")
    altered = build_evaluation_model_config(
        model_method="league_only", batter_prior_strength=999.0
    )
    assert default["config_id"] == altered["config_id"]


def test_config_id_changes_with_a_relevant_strength():
    default = build_evaluation_model_config(model_method="batter_shrinkage")
    altered = build_evaluation_model_config(
        model_method="batter_shrinkage", batter_prior_strength=25.0
    )
    assert default["config_id"] != altered["config_id"]


def test_config_id_is_deterministic_across_calls():
    assert (
        build_evaluation_model_config(model_method="matchup_combination")["config_id"]
        == build_evaluation_model_config(model_method="matchup_combination")["config_id"]
    )


def test_config_ids_differ_across_methods():
    ids = {
        build_evaluation_model_config(model_method=method)["config_id"]
        for method in MODEL_METHODS
    }
    assert len(ids) == len(MODEL_METHODS)


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------


def test_rejects_non_sequence_records():
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward({"a": 1}, model_configs=_configs("league_only"))


def test_rejects_empty_records():
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward([], model_configs=_configs("league_only"))


def test_rejects_non_dict_record():
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(["nope"], model_configs=_configs("league_only"))


def test_rejects_missing_field():
    records = _history(days=2)
    del records[0]["prior_league_pa_count"]
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


def test_rejects_extra_field():
    records = _history(days=2)
    records[0]["surprise"] = 1
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


def test_rejects_schema_version_mismatch():
    records = _history(days=2)
    records[0]["normalized_pa_schema_version"] = "99"
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


def test_rejects_duplicate_pa_id():
    records = _history(days=2)
    records.append(dict(records[0]))
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


def test_rejects_multiple_source_snapshot_ids():
    records = _history(days=2)
    records[0]["source_snapshot_id"] = "20260811T120000000000Z_ffffffffffff"
    with pytest.raises(PlateAppearanceEvaluationError) as excinfo:
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))
    assert "exactly one source snapshot" in str(excinfo.value)


@pytest.mark.parametrize("configs", [[], (), "league_only", None])
def test_rejects_invalid_model_configs(configs):
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(_history(days=2), model_configs=configs)


def test_rejects_duplicate_config_id():
    configs = _configs("league_only", "league_only")
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(_history(days=2), model_configs=configs)


def test_rejects_hand_built_inconsistent_config():
    config = build_evaluation_model_config(model_method="league_only")
    config["batter_prior_strength"] = 100.0
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(_history(days=2), model_configs=[config])


def test_rejects_config_with_wrong_field_set():
    config = build_evaluation_model_config(model_method="league_only")
    del config["model_config_version"]
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(_history(days=2), model_configs=[config])


# ---------------------------------------------------------------------------
# prior-state coherence
# ---------------------------------------------------------------------------


def test_intact_history_passes_coherence():
    report = evaluate_pa_walk_forward(
        _history(days=3), model_configs=_configs("league_only")
    )
    assert report["coverage"]["input_pa_count"] == 30


def test_mutated_prior_counts_are_rejected():
    records = _history(days=3)
    records[-1]["prior_batter_outcome_counts"] = dict(
        records[-1]["prior_batter_outcome_counts"]
    )
    records[-1]["prior_batter_outcome_counts"]["single"] += 7
    with pytest.raises(PlateAppearanceEvaluationError) as excinfo:
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))
    assert "prior-state coherence failure" in str(excinfo.value)


def test_mutated_prior_pa_count_is_rejected():
    records = _history(days=3)
    records[-1]["prior_league_pa_count"] += 1
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


def test_head_truncated_history_is_rejected():
    """Dropping early dates leaves later records claiming prior state that the
    supplied history can no longer justify."""
    records = _history(days=4)
    kept = [r for r in records if r["game_date"] != "2024-04-01"]
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))


def test_mid_history_date_removal_is_rejected():
    records = _history(days=4)
    kept = [r for r in records if r["game_date"] != "2024-04-02"]
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))


def test_post_enrichment_filtering_of_completed_pas_is_rejected():
    records = _history(days=4)
    kept = [r for index, r in enumerate(records) if index != 3]
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))


def test_spliced_histories_are_rejected():
    """Records enriched in two separate runs carry prior state that cannot both
    be true of one combined history."""
    first = _enriched(_default_specs(days=2, start_day=1))
    second = _enriched(_default_specs(days=2, start_day=3))
    for index, record in enumerate(second):
        record["at_bat_number"] += 1000
    combined = first + second
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(combined, model_configs=_configs("league_only"))


def test_upstream_rate_error_propagates_unwrapped():
    records = _history(days=2)
    records[0]["pa_status"] = "banana"
    with pytest.raises(PlateAppearanceRateError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


def test_tail_truncation_is_accepted_and_documented():
    """A stated limitation, asserted rather than merely written down: no
    retained record's prior state depends on the dropped tail."""
    records = _history(days=4)
    kept = [r for r in records if r["game_date"] != "2024-04-04"]
    report = evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))
    assert report["coverage"]["input_pa_count"] == 30


def test_removing_an_incomplete_pa_is_accepted_and_documented():
    """The other stated limitation: incomplete PAs never update a counter, so
    their absence is invisible to coherence validation."""
    specs = _default_specs(days=2)
    specs.append(
        {
            "game_date": "2024-04-01",
            "game_id": "700001",
            "at_bat_number": 500,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": "truncated_pa",
        }
    )
    records = _enriched(specs)
    kept = [r for r in records if r["pa_status"] == SCORABLE_PA_STATUS]
    report = evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))
    assert report["coverage"]["incomplete_pa_count"] == 0


# ---------------------------------------------------------------------------
# scorable target selection
# ---------------------------------------------------------------------------


def test_incomplete_pas_are_never_scored():
    specs = _default_specs(days=2)
    specs.append(
        {
            "game_date": "2024-04-02",
            "game_id": "700001",
            "at_bat_number": 500,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": None,
        }
    )
    report = evaluate_pa_walk_forward(
        _enriched(specs), model_configs=_configs("league_only")
    )
    assert report["coverage"]["input_pa_count"] == 21
    assert report["coverage"]["incomplete_pa_count"] == 1
    assert report["coverage"]["intersection_pa_count"] == 20
    assert _window(report)["scored_pa_count"] == 20


def test_truncated_pa_is_never_scored():
    specs = _default_specs(days=2)
    specs.append(
        {
            "game_date": "2024-04-02",
            "game_id": "700001",
            "at_bat_number": 500,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": "truncated_pa",
        }
    )
    report = evaluate_pa_walk_forward(
        _enriched(specs), model_configs=_configs("league_only")
    )
    assert report["coverage"]["incomplete_pa_count"] == 1
    assert _window(report)["scored_pa_count"] == 20


def test_history_with_no_completed_pas_raises():
    specs = [
        {
            "game_date": "2024-04-01",
            "game_id": "700001",
            "at_bat_number": 1,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": None,
        }
    ]
    with pytest.raises(PlateAppearanceEvaluationError) as excinfo:
        evaluate_pa_walk_forward(
            _enriched(specs), model_configs=_configs("league_only")
        )
    assert "no completed plate appearances" in str(excinfo.value)


# ---------------------------------------------------------------------------
# intersection sampling
# ---------------------------------------------------------------------------


def _mixed_eligibility_specs():
    specs = _default_specs(days=2)
    specs.append(
        {
            "game_date": "2024-04-02",
            "game_id": "700001",
            "at_bat_number": 500,
            "batter_id": "600001",
            "pitchers": ("700010", "700011"),
            "event": "single",
        }
    )
    return specs


def test_batter_only_configs_include_pitcher_ineligible_pas():
    report = evaluate_pa_walk_forward(
        _enriched(_mixed_eligibility_specs()),
        model_configs=_configs("league_only", "batter_shrinkage"),
    )
    assert report["coverage"]["pitcher_rate_ineligible_pa_count"] == 1
    assert report["coverage"]["intersection_pa_count"] == 21
    assert _window(report)["scored_pa_count"] == 21


def test_a_pitcher_dependent_config_excludes_ineligible_pas():
    report = evaluate_pa_walk_forward(
        _enriched(_mixed_eligibility_specs()),
        model_configs=_configs("league_only", "matchup_combination"),
    )
    assert report["coverage"]["intersection_pa_count"] == 20
    assert _window(report)["scored_pa_count"] == 20


def test_every_config_shares_one_denominator():
    report = evaluate_pa_walk_forward(
        _enriched(_mixed_eligibility_specs()),
        model_configs=_configs(*MODEL_METHODS),
    )
    counts = {
        _window(report, index)["scored_pa_count"]
        for index in range(len(MODEL_METHODS))
    }
    assert len(counts) == 1


def test_no_pitcher_eligible_pas_raises_a_specific_error():
    specs = [
        {
            "game_date": "2024-04-01",
            "game_id": "700001",
            "at_bat_number": index + 1,
            "batter_id": "600001",
            "pitchers": ("700010", "700011"),
            "event": "single",
        }
        for index in range(3)
    ]
    with pytest.raises(PlateAppearanceEvaluationError) as excinfo:
        evaluate_pa_walk_forward(
            _enriched(specs), model_configs=_configs("pitcher_shrinkage")
        )
    assert "pitcher_rate_eligible=True" in str(excinfo.value)


def test_sample_basis_is_always_intersection():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    assert report["sample_basis"] == EVALUATION_SAMPLE_BASIS == "intersection"


# ---------------------------------------------------------------------------
# coverage
# ---------------------------------------------------------------------------


def test_coverage_has_the_contract_field_set_and_order():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    assert tuple(report["coverage"]) == COVERAGE_FIELD_ORDER


def test_method_support_covers_every_method_over_completed_pas():
    report = evaluate_pa_walk_forward(
        _enriched(_mixed_eligibility_specs()),
        model_configs=_configs("league_only"),
    )
    support = {
        row["model_method"]: row["natively_supported_completed_pa_count"]
        for row in report["coverage"]["method_support"]
    }
    assert support["league_only"] == 21
    assert support["batter_shrinkage"] == 21
    assert support["pitcher_shrinkage"] == 20
    assert support["matchup_combination"] == 20


def test_coverage_reports_date_and_month_spans():
    april = _default_specs(days=2, month="04")
    may = _default_specs(days=2, month="05")
    for spec in may:
        spec["at_bat_number"] += 1000
    report = evaluate_pa_walk_forward(
        _enriched(april + may), model_configs=_configs("league_only")
    )
    coverage = report["coverage"]
    assert coverage["first_game_date"] == "2024-04-01"
    assert coverage["last_game_date"] == "2024-05-02"
    assert coverage["distinct_game_date_count"] == 4
    assert coverage["distinct_calendar_month_count"] == 2


def test_coverage_counts_cold_start_records():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    assert report["coverage"]["zero_league_history_pa_count"] == 1
    assert report["coverage"]["zero_batter_history_pa_count"] == 3
    assert report["coverage"]["coverage_basis"] == COVERAGE_BASIS


def test_coverage_basis_matches_the_upstream_snapshot_constant():
    """The evaluator duplicates this string to stay filesystem-free; the two
    must never drift."""
    from mlb.plate_appearance_snapshot import COVERAGE_BASIS as UPSTREAM

    assert COVERAGE_BASIS == UPSTREAM


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------


def _single_pa_report(event="strikeout"):
    specs = [
        {
            "game_date": "2024-04-01",
            "game_id": "700001",
            "at_bat_number": 1,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": event,
        }
    ]
    return evaluate_pa_walk_forward(
        _enriched(specs), model_configs=_configs("league_only")
    )


def test_cold_start_log_loss_is_uniform_log_loss():
    """With no league history the league baseline reduces exactly to uniform,
    so log loss is ln(K)."""
    window = _window(_single_pa_report())
    _assert_close(window["mean_log_loss"], math.log(K))


def test_cold_start_brier_score_is_the_uniform_value():
    window = _window(_single_pa_report())
    expected = (K - 1) * (1.0 / K) ** 2 + (1.0 / K - 1.0) ** 2
    _assert_close(window["mean_brier_score"], expected)


def test_argmax_ties_break_by_rate_categories_order():
    """A uniform distribution ties every category; the first RATE_CATEGORIES
    member must win deterministically."""
    assert RATE_CATEGORIES[0] == "strikeout"
    _assert_close(_window(_single_pa_report("strikeout"))["accuracy"], 1.0)
    _assert_close(_window(_single_pa_report("walk"))["accuracy"], 0.0)


def test_accuracy_is_between_zero_and_one():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=3), model_configs=_configs("batter_shrinkage")
        )
    )
    assert 0.0 <= window["accuracy"] <= 1.0


def test_window_has_the_contract_field_set_and_order():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    assert tuple(window) == WINDOW_FIELD_ORDER


# ---------------------------------------------------------------------------
# calibration diagnostics
# ---------------------------------------------------------------------------


def test_all_twelve_categories_are_diagnosed_in_canonical_order():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=3), model_configs=_configs("league_only")
        )
    )
    assert tuple(
        entry["category"] for entry in window["category_diagnostics"]
    ) == RATE_CATEGORIES


def test_category_diagnostic_has_the_contract_field_set_and_order():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    for entry in window["category_diagnostics"]:
        assert tuple(entry) == CATEGORY_DIAGNOSTIC_FIELD_ORDER


def test_zero_occurrence_category_still_receives_calibration_statistics():
    """A category predicted at some positive rate that never occurs is
    measurably miscalibrated, and must not be hidden behind None."""
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=3), model_configs=_configs("league_only")
        )
    )
    entry = _category(window, "intentional_walk")
    assert entry["actual_count"] == 0
    assert entry["actual_frequency"] == 0.0
    assert entry["mean_predicted_probability"] > 0.0
    assert entry["calibration_gap"] < 0.0
    _assert_close(
        entry["calibration_gap"], -entry["mean_predicted_probability"]
    )
    assert entry["reliability"]["expected_calibration_error"] is not None
    assert entry["reliability"]["maximum_calibration_error"] is not None


def test_intentional_walk_remains_its_own_visible_category():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    categories = [entry["category"] for entry in window["category_diagnostics"]]
    assert "intentional_walk" in categories
    assert "walk" in categories


def test_observed_category_frequency_matches_the_sample():
    report = evaluate_pa_walk_forward(
        _history(days=3), model_configs=_configs("league_only")
    )
    window = _window(report)
    total = window["scored_pa_count"]
    assert sum(
        entry["actual_count"] for entry in window["category_diagnostics"]
    ) == total
    entry = _category(window, "field_out")
    _assert_close(entry["actual_frequency"], entry["actual_count"] / total)


def test_the_two_bin_edge_schemes_differ():
    assert PA_CLASSWISE_CALIBRATION_BIN_EDGES != PA_TOP_LABEL_CALIBRATION_BIN_EDGES


def test_each_reliability_block_records_the_edges_it_used():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    assert window["top_label_reliability"]["bin_edges"] == list(
        PA_TOP_LABEL_CALIBRATION_BIN_EDGES
    )
    for entry in window["category_diagnostics"]:
        assert entry["reliability"]["bin_edges"] == list(
            PA_CLASSWISE_CALIBRATION_BIN_EDGES
        )


def test_macro_classwise_ece_is_the_arithmetic_mean_of_category_eces():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=3), model_configs=_configs("batter_shrinkage")
        )
    )
    values = [
        entry["reliability"]["expected_calibration_error"]
        for entry in window["category_diagnostics"]
    ]
    assert all(value is not None for value in values)
    _assert_close(
        window["macro_classwise_expected_calibration_error"],
        math.fsum(values) / len(values),
    )


def test_calibration_bins_are_not_a_public_argument():
    with pytest.raises(TypeError):
        evaluate_pa_walk_forward(
            _history(days=2),
            model_configs=_configs("league_only"),
            bin_edges=(0.0, 1.0),
        )


# ---------------------------------------------------------------------------
# calendar-month diagnostics
# ---------------------------------------------------------------------------


def test_calendar_month_rows_have_the_contract_field_set_and_order():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    for row in window["calendar_month_diagnostics"]:
        assert tuple(row) == CALENDAR_MONTH_DIAGNOSTIC_FIELD_ORDER


def test_single_month_history_emits_one_row():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=3), model_configs=_configs("league_only")
        )
    )
    rows = window["calendar_month_diagnostics"]
    assert len(rows) == 1
    assert rows[0]["calendar_month"] == "2024-04"


def test_multi_month_history_emits_sorted_rows():
    specs = _default_specs(days=2, month="04")
    later = _default_specs(days=2, month="05")
    for index, spec in enumerate(later):
        spec["at_bat_number"] += 1000
    window = _window(
        evaluate_pa_walk_forward(
            _enriched(specs + later), model_configs=_configs("league_only")
        )
    )
    rows = window["calendar_month_diagnostics"]
    assert [row["calendar_month"] for row in rows] == ["2024-04", "2024-05"]


def test_calendar_month_counts_sum_to_the_window_total():
    window = _window(
        evaluate_pa_walk_forward(
            _enriched(_default_specs(days=3)), model_configs=_configs("league_only")
        )
    )
    assert sum(
        row["scored_pa_count"] for row in window["calendar_month_diagnostics"]
    ) == window["scored_pa_count"]


def test_calendar_month_reports_cold_start_records():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    assert window["calendar_month_diagnostics"][0][
        "zero_league_history_pa_count"
    ] == 1


def test_calendar_month_rows_carry_no_calibration_curves():
    window = _window(
        evaluate_pa_walk_forward(
            _history(days=2), model_configs=_configs("league_only")
        )
    )
    for row in window["calendar_month_diagnostics"]:
        assert "reliability" not in row
        assert "expected_calibration_error" not in row


# ---------------------------------------------------------------------------
# split / holdout
# ---------------------------------------------------------------------------


def test_no_split_gives_one_full_window():
    report = evaluate_pa_walk_forward(
        _history(days=3), model_configs=_configs("league_only")
    )
    assert report["split_date"] is None
    assert [window["window"] for window in report["results"][0]["windows"]] == ["full"]


def test_split_partitions_on_the_boundary_date():
    report = evaluate_pa_walk_forward(
        _history(days=4),
        model_configs=_configs("league_only"),
        split_date="2024-04-03",
    )
    windows = report["results"][0]["windows"]
    assert [window["window"] for window in windows] == ["tuning", "holdout"]
    assert windows[0]["last_game_date"] == "2024-04-02"
    assert windows[1]["first_game_date"] == "2024-04-03"
    assert windows[0]["scored_pa_count"] == 20
    assert windows[1]["scored_pa_count"] == 20


def test_split_before_the_history_raises():
    with pytest.raises(PlateAppearanceEvaluationError) as excinfo:
        evaluate_pa_walk_forward(
            _history(days=3),
            model_configs=_configs("league_only"),
            split_date="2024-01-01",
        )
    assert "tuning window empty" in str(excinfo.value)


def test_split_after_the_history_raises():
    with pytest.raises(PlateAppearanceEvaluationError) as excinfo:
        evaluate_pa_walk_forward(
            _history(days=3),
            model_configs=_configs("league_only"),
            split_date="2025-01-01",
        )
    assert "holdout window empty" in str(excinfo.value)


@pytest.mark.parametrize(
    "split_date",
    ["2024-4-1", "20240401", "April 1 2024", "2024-13-01", "2024-04-40", "", "2024-ab-01"],
)
def test_malformed_split_date_raises(split_date):
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(
            _history(days=3),
            model_configs=_configs("league_only"),
            split_date=split_date,
        )


def test_non_string_split_date_raises():
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(
            _history(days=3),
            model_configs=_configs("league_only"),
            split_date=20240401,
        )


def test_split_date_is_recorded_in_the_report():
    report = evaluate_pa_walk_forward(
        _history(days=4),
        model_configs=_configs("league_only"),
        split_date="2024-04-03",
    )
    assert report["split_date"] == "2024-04-03"


# ---------------------------------------------------------------------------
# leakage regressions
# ---------------------------------------------------------------------------


def test_future_records_do_not_change_earlier_scored_metrics():
    """The core walk-forward guarantee: appending later history leaves every
    earlier record's contribution untouched."""
    early = evaluate_pa_walk_forward(
        _enriched(_default_specs(days=3)), model_configs=_configs("matchup_combination")
    )
    extended = evaluate_pa_walk_forward(
        _enriched(_default_specs(days=5)),
        model_configs=_configs("matchup_combination"),
        split_date="2024-04-04",
    )
    early_window = _window(early)
    tuning_window = extended["results"][0]["windows"][0]
    for field in ("scored_pa_count", "mean_log_loss", "mean_brier_score", "accuracy"):
        assert early_window[field] == tuning_window[field]
    assert early_window["category_diagnostics"] == tuning_window["category_diagnostics"]


def test_evaluator_probabilities_match_a_direct_v033_call():
    records = _enriched(_default_specs(days=2))
    config = build_evaluation_model_config(model_method="batter_shrinkage")
    report = evaluate_pa_walk_forward(records, model_configs=[config])

    scored = [r for r in records if r["pa_status"] == SCORABLE_PA_STATUS]
    direct = [
        build_pa_probability_distribution(
            record,
            method="batter_shrinkage",
            league_prior_strength=config["league_prior_strength"],
            batter_prior_strength=config["batter_prior_strength"],
        )["probabilities"]
        for record in scored
    ]
    window = _window(report)
    expected = math.fsum(
        probabilities["single"] for probabilities in direct
    ) / len(direct)
    _assert_close(_category(window, "single")["mean_predicted_probability"], expected)


def test_pitcher_attribution_error_never_escapes():
    records = _enriched(_mixed_eligibility_specs())
    for method in MODEL_METHODS:
        report = evaluate_pa_walk_forward(
            records, model_configs=_configs(method)
        )
        assert _window(report)["scored_pa_count"] > 0


def test_evaluation_does_not_mutate_its_inputs():
    records = _enriched(_default_specs(days=2))
    snapshot = json.dumps(records, sort_keys=True)
    configs = _configs("league_only", "matchup_combination")
    config_snapshot = json.dumps(configs, sort_keys=True)
    evaluate_pa_walk_forward(records, model_configs=configs)
    assert json.dumps(records, sort_keys=True) == snapshot
    assert json.dumps(configs, sort_keys=True) == config_snapshot


# ---------------------------------------------------------------------------
# determinism and provenance
# ---------------------------------------------------------------------------


def _shuffled(records, seed=11):
    copy = list(records)
    random.Random(seed).shuffle(copy)
    return copy


def test_shuffled_input_produces_an_identical_report():
    records = _enriched(_default_specs(days=4))
    configs = _configs("league_only", "batter_shrinkage", "matchup_combination")
    ordered = evaluate_pa_walk_forward(records, model_configs=configs)
    shuffled = evaluate_pa_walk_forward(_shuffled(records), model_configs=configs)
    assert json.dumps(ordered, sort_keys=True) == json.dumps(shuffled, sort_keys=True)


def test_repeated_evaluation_is_identical():
    records = _enriched(_default_specs(days=3))
    configs = _configs("matchup_combination")
    first = evaluate_pa_walk_forward(records, model_configs=configs)
    second = evaluate_pa_walk_forward(records, model_configs=configs)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_input_hash_is_stable_across_input_order():
    records = _enriched(_default_specs(days=3))
    configs = _configs("league_only")
    assert (
        evaluate_pa_walk_forward(records, model_configs=configs)["input_content_sha256"]
        == evaluate_pa_walk_forward(
            _shuffled(records), model_configs=configs
        )["input_content_sha256"]
    )


def _reverse_nested_mappings(records):
    """Rebuild every nested mapping with reversed key insertion order."""
    rebuilt = []
    for record in records:
        copy = {}
        for field, value in record.items():
            if isinstance(value, dict):
                copy[field] = {
                    key: value[key] for key in reversed(list(value))
                }
            else:
                copy[field] = value
        rebuilt.append(copy)
    return rebuilt


def test_nested_mapping_insertion_order_does_not_change_the_hash():
    """prior_*_outcome_counts / _rates are mappings; two semantically identical
    histories must hash identically regardless of nested key order."""
    records = _enriched(_default_specs(days=3))
    reordered = _reverse_nested_mappings(records)

    sample = reordered[5]["prior_league_outcome_counts"]
    assert list(sample) != list(RATE_CATEGORIES)
    assert sample == records[5]["prior_league_outcome_counts"]

    configs = _configs("league_only")
    original = evaluate_pa_walk_forward(records, model_configs=configs)
    shuffled = evaluate_pa_walk_forward(reordered, model_configs=configs)
    assert original["input_content_sha256"] == shuffled["input_content_sha256"]


def test_nested_mapping_insertion_order_does_not_change_the_report():
    records = _enriched(_default_specs(days=3))
    configs = _configs("league_only", "matchup_combination")
    original = evaluate_pa_walk_forward(records, model_configs=configs)
    reordered = evaluate_pa_walk_forward(
        _reverse_nested_mappings(records), model_configs=configs
    )
    assert json.dumps(original, sort_keys=True) == json.dumps(
        reordered, sort_keys=True
    )


def test_input_hash_changes_when_content_changes():
    records = _enriched(_default_specs(days=3))
    configs = _configs("league_only")
    baseline = evaluate_pa_walk_forward(records, model_configs=configs)
    longer = evaluate_pa_walk_forward(
        _enriched(_default_specs(days=4)), model_configs=configs
    )
    assert baseline["input_content_sha256"] != longer["input_content_sha256"]


def test_input_hash_is_a_hex_digest():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    digest = report["input_content_sha256"]
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_report_carries_no_clock_derived_field():
    """The report is a pure function of its inputs, so it must expose no
    generation timestamp anywhere in its schema."""
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    for field in REPORT_FIELD_ORDER:
        assert not field.endswith("_at")
        assert "timestamp" not in field
    for field in COVERAGE_FIELD_ORDER:
        assert not field.endswith("_at")
        assert "timestamp" not in field

    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "plate_appearance_evaluation.py"
    )
    tree = ast.parse(src.read_text())
    # Calendar parsing is permitted (split_date must be a real date); reading a
    # wall clock is not, because a report must be a pure function of its input.
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    for forbidden in ("now", "today", "utcnow", "time", "monotonic", "perf_counter"):
        assert forbidden not in called, f"wall-clock call {forbidden!r} found"


def test_report_records_provenance_and_versions():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    assert report["pa_evaluation_schema_version"] == PA_EVALUATION_SCHEMA_VERSION
    assert report["normalized_pa_schema_version"] == "1"
    assert report["normalized_pa_probability_schema_version"] == "1"
    assert report["source_snapshot_id"] == SNAPSHOT_ID


def test_report_has_the_contract_field_set_and_order():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    assert tuple(report) == REPORT_FIELD_ORDER
    assert tuple(report["results"][0]) == RESULT_FIELD_ORDER


def test_report_notes_warn_against_ranking_by_calibration_error():
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    joined = " ".join(report["notes"])
    assert "calibration error" in joined
    assert "rank" in joined


# ---------------------------------------------------------------------------
# report validation
# ---------------------------------------------------------------------------


def _valid_report():
    return evaluate_pa_walk_forward(
        _history(days=3), model_configs=_configs("league_only", "batter_shrinkage")
    )


def test_validate_returns_a_valid_report_unchanged():
    report = _valid_report()
    assert validate_pa_evaluation_report(report) is report


def test_validate_rejects_non_dict():
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(["not", "a", "report"])


def test_validate_rejects_wrong_field_set():
    report = _valid_report()
    del report["notes"]
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_version_mismatch():
    report = _valid_report()
    report["pa_evaluation_schema_version"] = "99"
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_altered_sample_basis():
    report = _valid_report()
    report["sample_basis"] = "all_supported"
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_altered_bin_edges():
    report = _valid_report()
    report["classwise_bin_edges"] = [0.0, 1.0]
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_a_bad_digest():
    report = _valid_report()
    report["input_content_sha256"] = "abc"
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_mismatched_result_count():
    report = _valid_report()
    report["results"] = report["results"][:1]
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_a_config_id_mismatch():
    report = _valid_report()
    report["results"][0]["config_id"] = "0" * 64
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_a_dropped_category_diagnostic():
    report = _valid_report()
    window = report["results"][0]["windows"][0]
    window["category_diagnostics"] = window["category_diagnostics"][:-1]
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_inconsistent_calendar_month_counts():
    report = _valid_report()
    window = report["results"][0]["windows"][0]
    window["calendar_month_diagnostics"][0]["scored_pa_count"] += 1
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_an_unexpected_window_set():
    report = _valid_report()
    report["results"][0]["windows"][0]["window"] = "tuning"
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_empty_notes():
    report = _valid_report()
    report["notes"] = []
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_evaluation_has_no_banned_imports():
    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "plate_appearance_evaluation.py"
    )
    tree = ast.parse(src.read_text())
    banned = {
        "requests", "urllib", "http", "socket", "pybaseball", "pandas",
        "numpy", "sklearn", "scipy", "run_slate", "database", "data_quality",
        "market_selector", "sqlite3", "paths",
    }
    imported = set()
    relative = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative.add(node.module.split(".")[0] if node.module else "")
            elif node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
    assert "plate_appearance_snapshot" not in relative


def test_evaluation_performs_no_filesystem_access():
    """The module must not read or write anything: importing the snapshot layer
    or touching a path would end its purity."""
    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "plate_appearance_evaluation.py"
    )
    tree = ast.parse(src.read_text())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    for forbidden in ("open", "read_text", "write_text", "read_bytes", "mkdir"):
        assert forbidden not in called, f"filesystem call {forbidden!r} found"

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level and node.module:
            imported_modules.add(node.module)
    assert "plate_appearance_snapshot" not in imported_modules


# ---------------------------------------------------------------------------
# integration
# ---------------------------------------------------------------------------


def test_end_to_end_from_synthetic_pitches():
    """pitch records -> grouping -> rate enrichment -> evaluation."""
    specs = _default_specs(days=4)
    specs.append(
        {
            "game_date": "2024-04-02",
            "game_id": "700001",
            "at_bat_number": 900,
            "batter_id": "600002",
            "pitchers": ("700010", "700011"),
            "event": "double",
        }
    )
    specs.append(
        {
            "game_date": "2024-04-03",
            "game_id": "700001",
            "at_bat_number": 901,
            "batter_id": "600003",
            "pitchers": ("700010",),
            "event": "truncated_pa",
        }
    )

    pitches = []
    for spec in specs:
        pitches.extend(_pa_pitches(**spec))
    pas = group_pitches_into_plate_appearances(pitches)
    records = attach_prior_outcome_rates(pas)

    report = evaluate_pa_walk_forward(
        records,
        model_configs=_configs(*MODEL_METHODS),
        split_date="2024-04-03",
    )

    assert report["coverage"]["input_pa_count"] == 42
    assert report["coverage"]["incomplete_pa_count"] == 1
    assert report["coverage"]["pitcher_rate_ineligible_pa_count"] == 1
    # one incomplete and one pitcher-ineligible record leave the intersection
    assert report["coverage"]["intersection_pa_count"] == 40
    assert len(report["results"]) == len(MODEL_METHODS)
    for result in report["results"]:
        for window in result["windows"]:
            assert window["scored_pa_count"] > 0
            assert window["mean_log_loss"] > 0
            assert len(window["category_diagnostics"]) == K


# ---------------------------------------------------------------------------
# log-loss clamping (regression: the default epsilon does bind)
# ---------------------------------------------------------------------------


def _tiny_prior_history():
    """A realized category with no prior league history, so its probability is
    driven far below backtest.py's default 1e-15 clamp."""
    specs = [
        {
            "game_date": "2024-04-01",
            "game_id": "700001",
            "at_bat_number": index + 1,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": "field_out",
        }
        for index in range(6)
    ]
    specs.append(
        {
            "game_date": "2024-04-02",
            "game_id": "700001",
            "at_bat_number": 99,
            "batter_id": "600002",
            "pitchers": ("700011",),
            "event": "triple",
        }
    )
    return _enriched(specs)


def test_tiny_prior_strength_drives_probability_below_the_default_epsilon():
    records = _tiny_prior_history()
    target = next(r for r in records if r["pa_outcome_category"] == "triple")
    assert target["prior_league_outcome_counts"]["triple"] == 0
    probabilities = build_pa_probability_distribution(
        target, method="league_only", league_prior_strength=1e-20
    )["probabilities"]
    assert 0.0 < probabilities["triple"] < 1e-15


def test_log_loss_is_not_floored_by_the_default_epsilon():
    """v0.3.3 guarantees strict positivity, not p >= 1e-15. Clamping at the
    default would understate log loss for exactly the overconfident
    configurations this version exists to detect."""
    records = _tiny_prior_history()
    config = build_evaluation_model_config(
        model_method="league_only", league_prior_strength=1e-20
    )
    report = evaluate_pa_walk_forward(
        records, model_configs=[config], split_date="2024-04-02"
    )
    holdout = report["results"][0]["windows"][1]
    assert holdout["scored_pa_count"] == 1

    target = next(r for r in records if r["pa_outcome_category"] == "triple")
    probabilities = build_pa_probability_distribution(
        target, method="league_only", league_prior_strength=1e-20
    )["probabilities"]
    p_actual = probabilities["triple"]

    _assert_close(holdout["mean_log_loss"], -math.log(p_actual), tolerance=1e-9)
    assert holdout["mean_log_loss"] > -math.log(1e-15)


def test_default_strength_log_loss_is_unaffected_by_the_epsilon_choice():
    """The wider clamp must change nothing for ordinary configurations."""
    records = _history(days=3)
    report = evaluate_pa_walk_forward(
        records, model_configs=_configs("league_only")
    )
    window = _window(report)
    scored = [r for r in records if r["pa_status"] == SCORABLE_PA_STATUS]
    expected = math.fsum(
        -math.log(
            build_pa_probability_distribution(record, method="league_only")[
                "probabilities"
            ][record["pa_outcome_category"]]
        )
        for record in scored
    ) / len(scored)
    _assert_close(window["mean_log_loss"], expected, tolerance=1e-12)


# ---------------------------------------------------------------------------
# split_date must be a real calendar date
# ---------------------------------------------------------------------------


def _february_history():
    specs = []
    for day, event in (("28", "field_out"), ("29", "single")):
        specs.append(
            {
                "game_date": "2024-02-%s" % day,
                "game_id": "700001",
                "at_bat_number": int(day),
                "batter_id": "600001",
                "pitchers": ("700010",),
                "event": event,
            }
        )
    return _enriched(specs)


@pytest.mark.parametrize("split_date", ["2024-02-30", "2024-02-31", "2023-02-29", "2024-13-01", "2024-00-10", "2024-04-00"])
def test_impossible_calendar_dates_are_rejected(split_date):
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(
            _history(days=3),
            model_configs=_configs("league_only"),
            split_date=split_date,
        )


def test_leap_day_is_accepted_in_a_leap_year():
    report = evaluate_pa_walk_forward(
        _february_history(),
        model_configs=_configs("league_only"),
        split_date="2024-02-29",
    )
    assert report["split_date"] == "2024-02-29"
    assert [w["window"] for w in report["results"][0]["windows"]] == [
        "tuning",
        "holdout",
    ]


# ---------------------------------------------------------------------------
# source_snapshot_id validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, "", 12345, ["a"], {"a": 1}])
def test_invalid_source_snapshot_id_raises_the_module_error(value):
    """Unhashable or malformed values must not leak a raw TypeError out of set
    membership."""
    records = _history(days=2)
    records[0]["source_snapshot_id"] = value
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(records, model_configs=_configs("league_only"))


# ---------------------------------------------------------------------------
# coherence guarantee boundary (documented blind spots)
# ---------------------------------------------------------------------------


def _final_date_two_game_history():
    """Two games on the final date. Same-date games are frozen from each other,
    so neither can observe the other's outcomes."""
    specs = [
        {
            "game_date": "2024-04-01",
            "game_id": "700001",
            "at_bat_number": index + 1,
            "batter_id": "600001",
            "pitchers": ("700010",),
            "event": "field_out",
        }
        for index in range(4)
    ]
    for game_id in ("700001", "700002"):
        for index in range(4):
            specs.append(
                {
                    "game_date": "2024-04-02",
                    "game_id": game_id,
                    "at_bat_number": 100 + index,
                    "batter_id": "600002",
                    "pitchers": ("700011",),
                    "event": "single",
                }
            )
    return _enriched(specs)


def test_same_date_cross_game_omission_on_the_final_date_is_undetectable():
    """Documents the guarantee boundary rather than weakening validation: the
    dropped record is not the last in canonical order, yet no retained record's
    prior state depends on it, so coherence validation cannot see it."""
    records = _final_date_two_game_history()
    ordered = sorted(
        records,
        key=lambda r: (r["game_date"], int(r["source_game_id"]), r["at_bat_number"]),
    )
    dropped = ordered[7]
    assert dropped["game_date"] == "2024-04-02"
    assert dropped["source_game_id"] == "700001"
    # a later game on the same date still follows it in canonical order
    assert ordered[-1]["source_game_id"] == "700002"

    kept = [r for r in records if r["rsb_pa_id"] != dropped["rsb_pa_id"]]
    report = evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))
    assert report["coverage"]["input_pa_count"] == len(records) - 1


def test_omission_that_changes_a_retained_record_is_still_detected():
    """The complement of the boundary test: the guarantee is effect-based, not
    position-based."""
    records = _final_date_two_game_history()
    ordered = sorted(
        records,
        key=lambda r: (r["game_date"], int(r["source_game_id"]), r["at_bat_number"]),
    )
    # an earlier-date record: later dates inherit its outcome, so dropping it
    # changes retained prior state
    kept = [r for r in records if r["rsb_pa_id"] != ordered[0]["rsb_pa_id"]]
    with pytest.raises(PlateAppearanceEvaluationError):
        evaluate_pa_walk_forward(kept, model_configs=_configs("league_only"))


# ---------------------------------------------------------------------------
# report validator rejects internally inconsistent reports
# ---------------------------------------------------------------------------


def _mutate(mutator, split_date=None):
    report = evaluate_pa_walk_forward(
        _history(days=4),
        model_configs=_configs("league_only", "batter_shrinkage"),
        split_date=split_date,
    )
    mutator(report)
    with pytest.raises(PlateAppearanceEvaluationError):
        validate_pa_evaluation_report(report)


def test_validate_rejects_a_nan_window_metric():
    def mutate(report):
        report["results"][0]["windows"][0]["mean_log_loss"] = float("nan")

    _mutate(mutate)


def test_validate_rejects_a_negative_window_metric():
    def mutate(report):
        report["results"][0]["windows"][0]["mean_brier_score"] = -0.1

    _mutate(mutate)


def test_validate_rejects_out_of_range_accuracy():
    def mutate(report):
        report["results"][0]["windows"][0]["accuracy"] = 7

    _mutate(mutate)


def test_validate_rejects_a_malformed_method_support_row():
    def mutate(report):
        del report["coverage"]["method_support"][0][
            "natively_supported_completed_pa_count"
        ]

    _mutate(mutate)


def test_validate_rejects_reordered_method_support():
    def mutate(report):
        report["coverage"]["method_support"].reverse()

    _mutate(mutate)


def test_validate_rejects_method_support_exceeding_completed_count():
    def mutate(report):
        report["coverage"]["method_support"][0][
            "natively_supported_completed_pa_count"
        ] = 10 ** 6

    _mutate(mutate)


def test_validate_rejects_a_result_config_unrelated_to_the_top_level_config():
    """A self-consistent config that simply is not the one this report declared."""

    def mutate(report):
        foreign = build_evaluation_model_config(model_method="matchup_combination")
        report["results"][0]["config"] = foreign
        report["results"][0]["config_id"] = foreign["config_id"]

    _mutate(mutate)


def test_validate_rejects_a_result_config_that_contradicts_its_own_id():
    def mutate(report):
        report["results"][0]["config"] = report["results"][1]["config"]

    _mutate(mutate)


def test_validate_rejects_wrong_nested_reliability_bin_edges():
    def mutate(report):
        window = report["results"][0]["windows"][0]
        window["category_diagnostics"][0]["reliability"]["bin_edges"] = list(
            PA_TOP_LABEL_CALIBRATION_BIN_EDGES
        )

    _mutate(mutate)


def test_validate_rejects_a_forged_stored_ece():
    def mutate(report):
        window = report["results"][0]["windows"][0]
        window["top_label_reliability"]["expected_calibration_error"] = 0.0

    _mutate(mutate)


def test_validate_rejects_corrupted_reliability_bins():
    def mutate(report):
        window = report["results"][0]["windows"][0]
        window["top_label_reliability"]["bins"][0]["calibration_gap"] = 0.9

    _mutate(mutate)


def test_validate_rejects_reliability_bin_counts_that_miss_the_sample():
    def mutate(report):
        window = report["results"][0]["windows"][0]
        for entry in window["top_label_reliability"]["bins"]:
            if entry["count"]:
                entry["count"] -= 1
                break

    _mutate(mutate)


def test_validate_rejects_a_non_hex_digest_of_the_right_length():
    def mutate(report):
        report["input_content_sha256"] = "z" * 64

    _mutate(mutate)


def test_validate_rejects_an_uppercase_digest():
    def mutate(report):
        report["input_content_sha256"] = report["input_content_sha256"].upper()

    _mutate(mutate)


def test_validate_rejects_an_impossible_split_date():
    def mutate(report):
        report["split_date"] = "2024-02-31"

    _mutate(mutate, split_date="2024-04-03")


def test_validate_rejects_an_empty_source_snapshot_id():
    def mutate(report):
        report["source_snapshot_id"] = ""

    _mutate(mutate)


def test_validate_rejects_coverage_counts_that_do_not_reconcile():
    def mutate(report):
        report["coverage"]["incomplete_pa_count"] += 1

    _mutate(mutate)


def test_validate_rejects_pitcher_eligibility_counts_that_do_not_reconcile():
    def mutate(report):
        report["coverage"]["pitcher_rate_eligible_pa_count"] += 1

    _mutate(mutate)


def test_validate_rejects_intersection_exceeding_completed():
    def mutate(report):
        report["coverage"]["intersection_pa_count"] = (
            report["coverage"]["completed_pa_count"] + 1
        )

    _mutate(mutate)


def test_validate_rejects_zero_history_exceeding_the_sample():
    def mutate(report):
        report["coverage"]["zero_league_history_pa_count"] = (
            report["coverage"]["intersection_pa_count"] + 1
        )

    _mutate(mutate)


def test_validate_rejects_a_negative_coverage_count():
    def mutate(report):
        report["coverage"]["completed_pa_count"] = -1

    _mutate(mutate)


def test_validate_rejects_window_counts_that_miss_the_intersection():
    def mutate(report):
        report["results"][0]["windows"][0]["scored_pa_count"] += 1

    _mutate(mutate)


def test_validate_rejects_configs_scored_on_different_denominators():
    def mutate(report):
        window = report["results"][1]["windows"][0]
        window["scored_pa_count"] = window["scored_pa_count"] - 1
        report["coverage"]["intersection_pa_count"] -= 1

    _mutate(mutate)


def test_validate_rejects_category_counts_that_do_not_sum_to_the_sample():
    def mutate(report):
        report["results"][0]["windows"][0]["category_diagnostics"][0][
            "actual_count"
        ] += 1

    _mutate(mutate)


def test_validate_rejects_a_forged_category_calibration_gap():
    def mutate(report):
        report["results"][0]["windows"][0]["category_diagnostics"][0][
            "calibration_gap"
        ] = 0.5

    _mutate(mutate)


def test_validate_rejects_a_forged_macro_ece():
    def mutate(report):
        report["results"][0]["windows"][0][
            "macro_classwise_expected_calibration_error"
        ] = 0.0

    _mutate(mutate)


def test_validate_rejects_out_of_order_calendar_months():
    def mutate(report):
        rows = report["results"][0]["windows"][0]["calendar_month_diagnostics"]
        rows.append(dict(rows[0]))
        rows[-1]["calendar_month"] = "2023-01"
        rows[-1]["scored_pa_count"] = 0

    _mutate(mutate)


def test_validate_rejects_monthly_zero_history_exceeding_its_own_count():
    def mutate(report):
        row = report["results"][0]["windows"][0]["calendar_month_diagnostics"][0]
        row["zero_league_history_pa_count"] = row["scored_pa_count"] + 1

    _mutate(mutate)


def test_validate_rejects_a_blank_note():
    def mutate(report):
        report["notes"].append("   ")

    _mutate(mutate)


def test_validate_rejects_a_non_string_note():
    def mutate(report):
        report["notes"].append(42)

    _mutate(mutate)


def test_validate_rejects_a_duplicated_config():
    def mutate(report):
        report["model_configs"].append(dict(report["model_configs"][0]))

    _mutate(mutate)


def test_validate_accepts_an_untouched_split_report():
    report = evaluate_pa_walk_forward(
        _history(days=4),
        model_configs=_configs("league_only", "batter_shrinkage"),
        split_date="2024-04-03",
    )
    assert validate_pa_evaluation_report(report) is report


def test_report_note_about_macro_ece_is_input_agnostic():
    """The note must not assert an outcome-frequency structure that a supplied
    history need not have."""
    report = evaluate_pa_walk_forward(
        _history(days=2), model_configs=_configs("league_only")
    )
    joined = " ".join(report["notes"])
    assert "8 of 12" not in joined
    assert "5%" not in joined
    assert "low-frequency outcomes" in joined


# ---------------------------------------------------------------------------
# new aggregation uses exact summation
# ---------------------------------------------------------------------------


def test_new_aggregation_uses_exactly_rounded_summation():
    """v0.3.4's own aggregation must be perfectly rounded regardless of how the
    interpreter's built-in sum happens to accumulate."""
    values = [
        -1.4157350694399827e-17,
        -2.8208469174285942e17,
        -1.6132208904711808e17,
    ]
    assert sum(values) != math.fsum(values)
    _assert_close(_mean(values), math.fsum(values) / len(values), tolerance=0.0)
    assert _mean(values) != sum(values) / len(values)


def test_mean_rejects_an_empty_collection():
    with pytest.raises(PlateAppearanceEvaluationError):
        _mean([])


def test_mean_matches_the_obvious_answer_for_ordinary_values():
    _assert_close(_mean([1.0, 2.0, 3.0]), 2.0)


# ---------------------------------------------------------------------------
# results and model_configs must be a bijection
# ---------------------------------------------------------------------------


def test_validate_rejects_a_duplicated_result_standing_in_for_a_missing_one():
    """Count equality plus per-result membership is not enough: [A, A] has the
    right length and two legitimate ids while omitting B entirely."""
    import copy

    def mutate(report):
        report["results"][1] = copy.deepcopy(report["results"][0])

    _mutate(mutate)


def test_validate_rejects_duplicated_results_under_a_split():
    import copy

    def mutate(report):
        report["results"][0] = copy.deepcopy(report["results"][1])

    _mutate(mutate, split_date="2024-04-03")


def test_every_model_config_appears_in_results_exactly_once():
    report = evaluate_pa_walk_forward(
        _history(days=3),
        model_configs=_configs("league_only", "batter_shrinkage", "matchup_combination"),
    )
    config_ids = [config["config_id"] for config in report["model_configs"]]
    result_ids = [result["config_id"] for result in report["results"]]
    assert sorted(result_ids) == sorted(config_ids)
    assert len(set(result_ids)) == len(result_ids)
