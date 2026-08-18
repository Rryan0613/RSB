import math
from pathlib import Path

import pytest

from mlb.plate_appearance import (
    PLATE_APPEARANCE_FIELD_ORDER,
    PLATE_APPEARANCE_SCHEMA_VERSION,
    RATE_CATEGORIES,
    build_rsb_pa_id,
    group_pitches_into_plate_appearances,
)
from mlb.plate_appearance_rates import (
    RATE_ENRICHED_FIELD_ORDER,
    attach_prior_outcome_rates,
)
from mlb.statcast_normalize import (
    NORMALIZED_PITCH_FIELD_ORDER,
    build_rsb_pitch_id,
)
from mlb.plate_appearance_probability import (
    DEFAULT_BATTER_PRIOR_STRENGTH,
    DEFAULT_LEAGUE_PRIOR_STRENGTH,
    DEFAULT_PITCHER_PRIOR_STRENGTH,
    MODEL_METHODS,
    PITCHER_DEPENDENT_METHODS,
    PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION,
    PROBABILITY_FIELD_ORDER,
    PROBABILITY_MODEL_CONFIG_VERSION,
    PROBABILITY_SUM_TOLERANCE,
    PitcherAttributionUnavailableError,
    PlateAppearanceProbabilityValidationError,
    _BATTER_DEPENDENT_METHODS,
    _extract_prior_context,
    _PRIOR_CONTEXT_FIELD_ORDER,
    build_batter_shrinkage_distribution,
    build_league_baseline_distribution,
    build_pa_probability_distribution,
    build_pitcher_shrinkage_distribution,
    combine_matchup_distribution,
    shrink_entity_distribution,
    supported_methods_for,
    validate_pa_probability_distribution,
)

K = len(RATE_CATEGORIES)


def _counts(**overrides) -> dict:
    counts = {category: 0 for category in RATE_CATEGORIES}
    counts.update(overrides)
    return counts


def _total(counts) -> int:
    return sum(counts[category] for category in RATE_CATEGORIES)


def _pa(
    *,
    source_game_id="700001",
    at_bat_number=1,
    batter_id="600001",
    pitcher_id="700010",
    pitcher_rate_eligible=True,
    pa_status="completed",
    pa_outcome_category="single",
    batter_counts=None,
    pitcher_counts=None,
    league_counts=None,
    **overrides,
) -> dict:
    """Build a rate-enriched PA record of the shape attach_prior_outcome_rates emits."""
    batter_counts = _counts() if batter_counts is None else batter_counts
    pitcher_counts = _counts() if pitcher_counts is None else pitcher_counts
    league_counts = _counts() if league_counts is None else league_counts

    base = {
        "rsb_pa_id": build_rsb_pa_id(source_game_id, at_bat_number),
        "source_game_id": source_game_id,
        "game_date": "2024-04-01",
        "game_year": 2024,
        "game_type": "R",
        "home_team": "NYY",
        "away_team": "BOS",
        "inning": 1,
        "inning_half": "top",
        "at_bat_number": at_bat_number,
        "batter_id": batter_id,
        "batter_stands": "R",
        "pitcher_id": pitcher_id,
        "pitcher_throws": "L",
        "source_pitcher_ids": [pitcher_id],
        "pitcher_rate_eligible": pitcher_rate_eligible,
        "outs_before_pa": 0,
        "on_1b_before_pa": None,
        "on_2b_before_pa": None,
        "on_3b_before_pa": None,
        "home_score_before_pa": 0,
        "away_score_before_pa": 0,
        "pa_status": pa_status,
        "pa_outcome_detailed": pa_outcome_category if pa_status == "completed" else None,
        "pa_outcome_category": pa_outcome_category if pa_status == "completed" else None,
        "terminal_pa_event_raw": pa_outcome_category if pa_status == "completed" else None,
        "pitch_count": 1,
        "source_pitch_ids": ["dummy_pitch_id"],
        "source_snapshot_id": "snap_test",
        "normalized_pa_schema_version": PLATE_APPEARANCE_SCHEMA_VERSION,
        "prior_batter_pa_count": _total(batter_counts),
        "prior_batter_outcome_counts": batter_counts,
        "prior_batter_outcome_rates": {c: None for c in RATE_CATEGORIES},
        "prior_pitcher_pa_count": _total(pitcher_counts),
        "prior_pitcher_outcome_counts": pitcher_counts,
        "prior_pitcher_outcome_rates": {c: None for c in RATE_CATEGORIES},
        "prior_league_pa_count": _total(league_counts),
        "prior_league_outcome_counts": league_counts,
        "prior_league_outcome_rates": {c: None for c in RATE_CATEGORIES},
    }
    base.update(overrides)
    return {field: base[field] for field in RATE_ENRICHED_FIELD_ORDER}


def _league_counts_sample() -> dict:
    return _counts(
        strikeout=2200,
        walk=850,
        intentional_walk=30,
        hit_by_pitch=110,
        single=1400,
        double=450,
        triple=40,
        home_run=320,
        field_out=4200,
        fielders_choice=180,
        reached_on_error=110,
        catcher_interference=10,
    )


def _assert_valid_distribution(distribution):
    assert set(distribution) == set(RATE_CATEGORIES)
    for category in RATE_CATEGORIES:
        value = distribution[category]
        assert isinstance(value, float)
        assert math.isfinite(value)
        assert value > 0.0
    assert abs(math.fsum(distribution.values()) - 1.0) <= PROBABILITY_SUM_TOLERANCE


def _assert_close(actual, expected, tolerance=1e-12):
    assert set(actual) == set(expected)
    for category in RATE_CATEGORIES:
        assert actual[category] == pytest.approx(expected[category], abs=tolerance)


# ---------------------------------------------------------------------------
# mathematical properties
# ---------------------------------------------------------------------------


def test_zero_league_history_yields_uniform_distribution():
    context = _extract_prior_context(_pa())
    distribution = build_league_baseline_distribution(context)
    for category in RATE_CATEGORIES:
        assert distribution[category] == pytest.approx(1.0 / K)


def test_league_baseline_keeps_unobserved_categories_strictly_positive():
    league = _counts(strikeout=5000, single=5000)
    context = _extract_prior_context(_pa(league_counts=league))
    distribution = build_league_baseline_distribution(context)
    assert distribution["catcher_interference"] > 0.0
    _assert_valid_distribution(distribution)


def test_league_baseline_approaches_empirical_rate_with_large_history():
    league = _league_counts_sample()
    context = _extract_prior_context(_pa(league_counts=league))
    distribution = build_league_baseline_distribution(context)
    total = _total(league)
    assert distribution["strikeout"] == pytest.approx(league["strikeout"] / total, abs=1e-4)


def test_unseen_batter_yields_league_distribution():
    context = _extract_prior_context(_pa(league_counts=_league_counts_sample()))
    league = build_league_baseline_distribution(context)
    batter = build_batter_shrinkage_distribution(context)
    _assert_close(batter, league)


def test_unseen_pitcher_yields_league_distribution():
    context = _extract_prior_context(_pa(league_counts=_league_counts_sample()))
    league = build_league_baseline_distribution(context)
    pitcher = build_pitcher_shrinkage_distribution(context)
    _assert_close(pitcher, league)


def test_matchup_with_pitcher_at_league_equals_batter_distribution():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(home_run=40, strikeout=90, single=70, field_out=200),
    )
    context = _extract_prior_context(record)
    batter = build_batter_shrinkage_distribution(context)
    matchup = combine_matchup_distribution(context)
    _assert_close(matchup, batter)


def test_matchup_with_batter_at_league_equals_pitcher_distribution():
    record = _pa(
        league_counts=_league_counts_sample(),
        pitcher_counts=_counts(strikeout=300, walk=90, single=140, field_out=400),
    )
    context = _extract_prior_context(record)
    pitcher = build_pitcher_shrinkage_distribution(context)
    matchup = combine_matchup_distribution(context)
    _assert_close(matchup, pitcher)


def test_matchup_with_both_at_league_equals_league_distribution():
    context = _extract_prior_context(_pa(league_counts=_league_counts_sample()))
    league = build_league_baseline_distribution(context)
    matchup = combine_matchup_distribution(context)
    _assert_close(matchup, league)


def test_estimate_moves_toward_empirical_rate_as_sample_grows():
    league = _league_counts_sample()
    league_rate = league["home_run"] / _total(league)

    distances = []
    for multiplier in (1, 10, 100, 1000):
        batter = _counts(
            home_run=10 * multiplier,
            strikeout=20 * multiplier,
            field_out=70 * multiplier,
        )
        context = _extract_prior_context(
            _pa(league_counts=league, batter_counts=batter)
        )
        distribution = build_batter_shrinkage_distribution(context)
        empirical = batter["home_run"] / _total(batter)
        distances.append(abs(distribution["home_run"] - empirical))
        # the batter's home-run rate is far above league, so more evidence must
        # always pull the estimate further above the league baseline
        assert distribution["home_run"] > league_rate

    assert distances == sorted(distances, reverse=True)


def test_tiny_sample_is_pulled_strongly_toward_league():
    league = _league_counts_sample()
    context = _extract_prior_context(
        _pa(league_counts=league, batter_counts=_counts(home_run=1))
    )
    league_distribution = build_league_baseline_distribution(context)
    distribution = build_batter_shrinkage_distribution(context)
    # a single observed home run must not move the estimate far from league
    assert abs(distribution["home_run"] - league_distribution["home_run"]) < 0.01


def test_matchup_amplifies_agreeing_deviations_beyond_either_side():
    league = _league_counts_sample()
    context = _extract_prior_context(
        _pa(
            league_counts=league,
            batter_counts=_counts(strikeout=400, field_out=600),
            pitcher_counts=_counts(strikeout=400, field_out=600),
        )
    )
    league_distribution = build_league_baseline_distribution(context)
    batter = build_batter_shrinkage_distribution(context)
    pitcher = build_pitcher_shrinkage_distribution(context)
    matchup = combine_matchup_distribution(context)

    assert batter["strikeout"] > league_distribution["strikeout"]
    assert pitcher["strikeout"] > league_distribution["strikeout"]
    # documented behavior of the multiplicative form: two same-direction
    # deviations compound rather than average
    assert matchup["strikeout"] > max(batter["strikeout"], pitcher["strikeout"])


def test_shrink_entity_distribution_is_entity_agnostic():
    context = _extract_prior_context(_pa(league_counts=_league_counts_sample()))
    league = build_league_baseline_distribution(context)
    counts = _counts(strikeout=50, single=25, field_out=125)

    as_batter = shrink_entity_distribution(counts, _total(counts), league, 100.0)
    as_pitcher = shrink_entity_distribution(counts, _total(counts), league, 100.0)
    assert as_batter == as_pitcher


# ---------------------------------------------------------------------------
# core invariants
# ---------------------------------------------------------------------------


def test_probabilities_sum_to_one_for_every_method():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(home_run=30, strikeout=60, field_out=110),
        pitcher_counts=_counts(strikeout=200, walk=60, field_out=340),
    )
    for method in MODEL_METHODS:
        built = build_pa_probability_distribution(record, method=method)
        total = math.fsum(built["probabilities"].values())
        assert abs(total - 1.0) <= PROBABILITY_SUM_TOLERANCE


def test_all_probabilities_strictly_positive_and_finite():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(home_run=30, strikeout=60),
        pitcher_counts=_counts(strikeout=200, walk=60),
    )
    for method in MODEL_METHODS:
        built = build_pa_probability_distribution(record, method=method)
        for category in RATE_CATEGORIES:
            value = built["probabilities"][category]
            assert not math.isnan(value)
            assert not math.isinf(value)
            assert value > 0.0


def test_probability_field_order_matches_contract():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    assert tuple(built) == PROBABILITY_FIELD_ORDER


def test_probabilities_keys_are_in_rate_categories_order():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    assert tuple(built["probabilities"]) == RATE_CATEGORIES


def test_deterministic_output_for_identical_input():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(single=40, strikeout=60),
        pitcher_counts=_counts(strikeout=150, walk=40),
    )
    for method in MODEL_METHODS:
        first = build_pa_probability_distribution(record, method=method)
        second = build_pa_probability_distribution(record, method=method)
        assert first == second
        assert repr(first["probabilities"]) == repr(second["probabilities"])


def test_unused_method_fields_are_none():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(single=40),
        pitcher_counts=_counts(strikeout=150),
    )
    for method in MODEL_METHODS:
        built = build_pa_probability_distribution(record, method=method)
        uses_batter = method in _BATTER_DEPENDENT_METHODS
        uses_pitcher = method in PITCHER_DEPENDENT_METHODS

        assert built["league_pa_count_used"] is not None
        assert built["league_prior_strength"] == DEFAULT_LEAGUE_PRIOR_STRENGTH

        if uses_batter:
            assert built["batter_pa_count_used"] == record["prior_batter_pa_count"]
            assert built["batter_prior_strength"] == DEFAULT_BATTER_PRIOR_STRENGTH
        else:
            assert built["batter_pa_count_used"] is None
            assert built["batter_prior_strength"] is None

        if uses_pitcher:
            assert built["pitcher_pa_count_used"] == record["prior_pitcher_pa_count"]
            assert built["pitcher_prior_strength"] == DEFAULT_PITCHER_PRIOR_STRENGTH
        else:
            assert built["pitcher_pa_count_used"] is None
            assert built["pitcher_prior_strength"] is None


def test_hyperparameters_are_recorded_on_every_record():
    built = build_pa_probability_distribution(
        _pa(league_counts=_league_counts_sample()),
        method="matchup_combination",
        league_prior_strength=2.0,
        batter_prior_strength=25.0,
        pitcher_prior_strength=50.0,
    )
    assert built["league_prior_strength"] == 2.0
    assert built["batter_prior_strength"] == 25.0
    assert built["pitcher_prior_strength"] == 50.0
    assert built["model_config_version"] == PROBABILITY_MODEL_CONFIG_VERSION


def test_different_prior_strengths_produce_different_distributions():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(home_run=50, strikeout=50, field_out=100),
    )
    weak = build_pa_probability_distribution(
        record, method="batter_shrinkage", batter_prior_strength=10.0
    )
    strong = build_pa_probability_distribution(
        record, method="batter_shrinkage", batter_prior_strength=1000.0
    )
    assert weak["probabilities"] != strong["probabilities"]
    # less shrinkage means the estimate stays closer to the batter's own rate
    assert weak["probabilities"]["home_run"] > strong["probabilities"]["home_run"]


def test_method_is_required_keyword():
    with pytest.raises(TypeError):
        build_pa_probability_distribution(_pa())


def test_rejects_unknown_method():
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(_pa(), method="deep_learning")


def test_rejects_non_positive_prior_strength():
    for bad in (0.0, -1.0):
        with pytest.raises(PlateAppearanceProbabilityValidationError):
            build_pa_probability_distribution(
                _pa(), method="league_only", league_prior_strength=bad
            )


def test_rejects_non_finite_prior_strength():
    for bad in (float("nan"), float("inf")):
        with pytest.raises(PlateAppearanceProbabilityValidationError):
            build_pa_probability_distribution(
                _pa(), method="league_only", league_prior_strength=bad
            )


# ---------------------------------------------------------------------------
# leakage
# ---------------------------------------------------------------------------


def test_prior_context_extraction_whitelist():
    context = _extract_prior_context(_pa())
    assert tuple(context) == _PRIOR_CONTEXT_FIELD_ORDER
    for banned in (
        "pa_status",
        "pa_outcome_detailed",
        "pa_outcome_category",
        "terminal_pa_event_raw",
        "prior_batter_outcome_rates",
        "prior_pitcher_outcome_rates",
        "prior_league_outcome_rates",
    ):
        assert banned not in context


def test_output_unchanged_when_pa_outcome_fields_differ():
    league = _league_counts_sample()
    batter = _counts(single=40, strikeout=60)
    pitcher = _counts(strikeout=150, walk=40)

    as_home_run = _pa(
        league_counts=league,
        batter_counts=batter,
        pitcher_counts=pitcher,
        pa_outcome_category="home_run",
    )
    as_strikeout = _pa(
        league_counts=league,
        batter_counts=batter,
        pitcher_counts=pitcher,
        pa_outcome_category="strikeout",
    )

    for method in MODEL_METHODS:
        assert build_pa_probability_distribution(
            as_home_run, method=method
        ) == build_pa_probability_distribution(as_strikeout, method=method)


def test_output_unaffected_by_pa_status():
    league = _league_counts_sample()
    batter = _counts(single=40, strikeout=60)
    pitcher = _counts(strikeout=150, walk=40)

    completed = _pa(
        league_counts=league,
        batter_counts=batter,
        pitcher_counts=pitcher,
        pa_status="completed",
    )
    incomplete = _pa(
        league_counts=league,
        batter_counts=batter,
        pitcher_counts=pitcher,
        pa_status="incomplete",
    )

    for method in MODEL_METHODS:
        assert build_pa_probability_distribution(
            completed, method=method
        ) == build_pa_probability_distribution(incomplete, method=method)


def test_output_unaffected_by_terminal_pa_event_raw():
    league = _league_counts_sample()
    truncated = _pa(
        league_counts=league,
        pa_status="incomplete",
        terminal_pa_event_raw="truncated_pa",
    )
    null_terminal = _pa(
        league_counts=league,
        pa_status="incomplete",
        terminal_pa_event_raw=None,
    )
    for method in MODEL_METHODS:
        assert build_pa_probability_distribution(
            truncated, method=method
        ) == build_pa_probability_distribution(null_terminal, method=method)


def test_incomplete_pa_still_produces_a_valid_distribution():
    built = build_pa_probability_distribution(
        _pa(
            league_counts=_league_counts_sample(),
            pa_status="incomplete",
            terminal_pa_event_raw="truncated_pa",
        ),
        method="matchup_combination",
    )
    _assert_valid_distribution(built["probabilities"])


def test_incomplete_pa_is_subject_to_the_same_pitcher_gate():
    record = _pa(
        league_counts=_league_counts_sample(),
        pa_status="incomplete",
        terminal_pa_event_raw="truncated_pa",
        pitcher_rate_eligible=False,
    )
    assert supported_methods_for(record) == ("league_only", "batter_shrinkage")
    for method in PITCHER_DEPENDENT_METHODS:
        with pytest.raises(PitcherAttributionUnavailableError):
            build_pa_probability_distribution(record, method=method)


def test_input_record_not_mutated():
    record = _pa(
        league_counts=_league_counts_sample(),
        batter_counts=_counts(single=40),
        pitcher_counts=_counts(strikeout=150),
    )
    import copy

    snapshot = copy.deepcopy(record)
    for method in MODEL_METHODS:
        build_pa_probability_distribution(record, method=method)
    assert record == snapshot


def test_same_game_chronological_prior_state_flows_through():
    first = _pa(source_game_id="700001", at_bat_number=1, pa_outcome_category="home_run")
    second = _pa(source_game_id="700001", at_bat_number=2, pa_outcome_category="strikeout")
    plain = [
        {field: record[field] for field in PLATE_APPEARANCE_FIELD_ORDER}
        for record in (first, second)
    ]
    enriched = attach_prior_outcome_rates(plain)

    first_built = build_pa_probability_distribution(enriched[0], method="batter_shrinkage")
    second_built = build_pa_probability_distribution(enriched[1], method="batter_shrinkage")

    # PA 1 has no history at all; PA 2 must see exactly PA 1's outcome
    assert first_built["batter_pa_count_used"] == 0
    assert second_built["batter_pa_count_used"] == 1
    assert enriched[1]["prior_batter_outcome_counts"]["home_run"] == 1
    assert (
        second_built["probabilities"]["home_run"]
        > first_built["probabilities"]["home_run"]
    )


# ---------------------------------------------------------------------------
# pitcher attribution gate
# ---------------------------------------------------------------------------


def test_pitcher_shrinkage_raises_when_pitcher_rate_eligible_false():
    with pytest.raises(PitcherAttributionUnavailableError):
        build_pa_probability_distribution(
            _pa(pitcher_rate_eligible=False), method="pitcher_shrinkage"
        )


def test_matchup_raises_when_pitcher_rate_eligible_false():
    with pytest.raises(PitcherAttributionUnavailableError):
        build_pa_probability_distribution(
            _pa(pitcher_rate_eligible=False), method="matchup_combination"
        )


def test_league_and_batter_methods_succeed_when_pitcher_rate_eligible_false():
    record = _pa(
        pitcher_rate_eligible=False,
        league_counts=_league_counts_sample(),
        batter_counts=_counts(single=40, strikeout=60),
    )
    for method in ("league_only", "batter_shrinkage"):
        built = build_pa_probability_distribution(record, method=method)
        _assert_valid_distribution(built["probabilities"])


def test_ineligible_pa_output_does_not_expose_terminal_pitcher_identity():
    league = _league_counts_sample()
    batter = _counts(single=40, strikeout=60)

    # identical prior/batter/league state; only the retrospectively known
    # terminal substitute pitcher differs
    finished_by_b = _pa(
        pitcher_rate_eligible=False,
        pitcher_id="700010",
        league_counts=league,
        batter_counts=batter,
    )
    finished_by_c = _pa(
        pitcher_rate_eligible=False,
        pitcher_id="700099",
        league_counts=league,
        batter_counts=batter,
    )

    for method in ("league_only", "batter_shrinkage"):
        first = build_pa_probability_distribution(finished_by_b, method=method)
        second = build_pa_probability_distribution(finished_by_c, method=method)
        # the identity is withheld entirely, and nothing else varies with it
        assert first["pitcher_id"] is None
        assert second["pitcher_id"] is None
        assert first == second
        assert "700010" not in repr(first)
        assert "700099" not in repr(second)


def test_eligible_pa_output_retains_pitcher_identity():
    built = build_pa_probability_distribution(
        _pa(pitcher_rate_eligible=True, pitcher_id="700010"), method="league_only"
    )
    assert built["pitcher_id"] == "700010"


def test_validate_rejects_pitcher_id_on_ineligible_record():
    built = build_pa_probability_distribution(
        _pa(pitcher_rate_eligible=False), method="league_only"
    )
    built["pitcher_id"] = "700010"
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_missing_pitcher_id_on_eligible_record():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["pitcher_id"] = None
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_pitcher_attribution_error_is_subclass_of_module_error():
    assert issubclass(
        PitcherAttributionUnavailableError, PlateAppearanceProbabilityValidationError
    )
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(
            _pa(pitcher_rate_eligible=False), method="matchup_combination"
        )


def test_direct_step_functions_also_enforce_the_gate():
    context = _extract_prior_context(_pa(pitcher_rate_eligible=False))
    with pytest.raises(PitcherAttributionUnavailableError):
        build_pitcher_shrinkage_distribution(context)
    with pytest.raises(PitcherAttributionUnavailableError):
        combine_matchup_distribution(context)


def test_supported_methods_for_reflects_pitcher_eligibility():
    assert supported_methods_for(_pa(pitcher_rate_eligible=True)) == MODEL_METHODS
    assert supported_methods_for(_pa(pitcher_rate_eligible=False)) == (
        "league_only",
        "batter_shrinkage",
    )


def test_supported_methods_are_exactly_the_methods_that_succeed():
    for eligible in (True, False):
        record = _pa(
            pitcher_rate_eligible=eligible, league_counts=_league_counts_sample()
        )
        supported = supported_methods_for(record)
        for method in MODEL_METHODS:
            if method in supported:
                build_pa_probability_distribution(record, method=method)
            else:
                with pytest.raises(PitcherAttributionUnavailableError):
                    build_pa_probability_distribution(record, method=method)


# ---------------------------------------------------------------------------
# outcome space
# ---------------------------------------------------------------------------


def test_distribution_covers_exactly_the_rate_categories():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    assert set(built["probabilities"]) == set(RATE_CATEGORIES)
    assert len(built["probabilities"]) == 12


def test_intentional_walk_is_its_own_category_never_merged_with_walk():
    league = _counts(walk=800, intentional_walk=40, strikeout=2000, field_out=4000)
    context = _extract_prior_context(_pa(league_counts=league))
    distribution = build_league_baseline_distribution(context)
    assert "intentional_walk" in distribution
    assert "walk" in distribution
    assert distribution["intentional_walk"] != distribution["walk"]
    assert distribution["walk"] > distribution["intentional_walk"]


def test_rare_intentional_walk_history_shrinks_toward_league():
    league = _league_counts_sample()
    context = _extract_prior_context(
        _pa(
            league_counts=league,
            batter_counts=_counts(intentional_walk=2, single=30, field_out=68),
        )
    )
    league_distribution = build_league_baseline_distribution(context)
    distribution = build_batter_shrinkage_distribution(context)
    empirical = 2 / 100
    # the estimate must sit between the league rate and the sparse empirical
    # rate, much closer to league
    assert (
        league_distribution["intentional_walk"]
        < distribution["intentional_walk"]
        < empirical
    )


# ---------------------------------------------------------------------------
# validator
# ---------------------------------------------------------------------------


def test_validate_accepts_a_built_record():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    assert validate_pa_probability_distribution(built) == built


def test_validate_rejects_missing_field():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    del built["model_method"]
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_extra_field():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["surprise"] = 1
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_distribution_that_does_not_sum_to_one():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["probabilities"]["strikeout"] += 0.5
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_negative_probability():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["probabilities"]["strikeout"] = -0.1
    built["probabilities"]["field_out"] = (
        built["probabilities"]["field_out"] + 0.1 + 1.0 / K
    )
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_nan_probability():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["probabilities"]["strikeout"] = float("nan")
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_unknown_method():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["model_method"] = "vibes"
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_populated_field_for_unused_method():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["pitcher_prior_strength"] = 100.0
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_pitcher_method_with_ineligible_record():
    built = build_pa_probability_distribution(_pa(), method="matchup_combination")
    built["pitcher_rate_eligible"] = False
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_wrong_schema_version():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["normalized_pa_probability_schema_version"] = "999"
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_rejects_wrong_model_config_version():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    built["model_config_version"] = "999"
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        validate_pa_probability_distribution(built)


def test_validate_accepts_equivalent_probability_mapping_in_different_key_order():
    built = build_pa_probability_distribution(_pa(), method="league_only")
    reordered = dict(built)
    reordered["probabilities"] = {
        category: built["probabilities"][category]
        for category in reversed(RATE_CATEGORIES)
    }
    # same categories, same values: the same distribution. Insertion order is a
    # builder guarantee, not a condition of semantic validity.
    assert reordered["probabilities"] == built["probabilities"]
    assert validate_pa_probability_distribution(reordered) == reordered


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------


def test_rejects_non_dict_record():
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(["not", "a", "dict"], method="league_only")


def test_rejects_record_missing_a_required_field():
    record = _pa()
    del record["prior_league_outcome_counts"]
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_rejects_record_with_extra_field():
    record = _pa()
    record["unexpected"] = 1
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_rejects_plain_pa_record_without_prior_state():
    plain = {field: _pa()[field] for field in PLATE_APPEARANCE_FIELD_ORDER}
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(plain, method="league_only")


def test_rejects_counts_that_disagree_with_pa_count():
    record = _pa(league_counts=_counts(single=5))
    record["prior_league_pa_count"] = 4
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_rejects_counts_missing_a_category():
    counts = _counts(single=5)
    del counts["catcher_interference"]
    record = _pa()
    record["prior_league_outcome_counts"] = counts
    record["prior_league_pa_count"] = 5
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_rejects_negative_counts():
    record = _pa(league_counts=_counts(single=5, double=-5))
    record["prior_league_pa_count"] = 0
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_rejects_wrong_upstream_pa_schema_version():
    record = _pa()
    record["normalized_pa_schema_version"] = "999"
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_rejects_stringy_pitcher_rate_eligible():
    record = _pa()
    record["pitcher_rate_eligible"] = "true"
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_pa_probability_distribution(record, method="league_only")


def test_prior_context_functions_reject_a_full_pa_record():
    with pytest.raises(PlateAppearanceProbabilityValidationError):
        build_league_baseline_distribution(_pa())


# ---------------------------------------------------------------------------
# value semantics / purity
# ---------------------------------------------------------------------------


def test_output_is_plain_dict_with_value_equality():
    record = _pa(league_counts=_league_counts_sample())
    first = build_pa_probability_distribution(record, method="league_only")
    second = build_pa_probability_distribution(record, method="league_only")
    assert type(first) is dict
    assert first is not second
    assert first == second


def test_no_shared_state_across_calls():
    quiet = _pa(league_counts=_counts(strikeout=10, single=10))
    loud = _pa(league_counts=_league_counts_sample())

    first = build_pa_probability_distribution(quiet, method="league_only")
    build_pa_probability_distribution(loud, method="league_only")
    again = build_pa_probability_distribution(quiet, method="league_only")
    assert first == again


def test_mutating_returned_probabilities_does_not_affect_later_calls():
    record = _pa(league_counts=_league_counts_sample())
    built = build_pa_probability_distribution(record, method="league_only")
    built["probabilities"]["strikeout"] = 0.99
    rebuilt = build_pa_probability_distribution(record, method="league_only")
    assert rebuilt["probabilities"]["strikeout"] != 0.99


def test_plate_appearance_probability_has_no_banned_imports():
    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "plate_appearance_probability.py"
    )
    tree = ast.parse(src.read_text())
    banned = {
        "requests",
        "urllib",
        "http",
        "socket",
        "pybaseball",
        "pandas",
        "numpy",
        "sklearn",
        "run_slate",
        "database",
        "data_quality",
        "market_selector",
        "sqlite3",
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


# ---------------------------------------------------------------------------
# integration
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
        "snapshot_id": "20260811T120000000000Z_abcdef012345",
        "source_provider": "baseball_savant",
        "normalized_schema_version": "1",
        "source_row_index": 0,
    }
    base.update(overrides)
    base["rsb_pitch_id"] = build_rsb_pitch_id(
        base["source_game_id"], base["at_bat_number"], base["pitch_number"]
    )
    return {field: base[field] for field in NORMALIZED_PITCH_FIELD_ORDER}


def test_full_pipeline_statcast_to_probability():
    pitches = [
        _pitch(at_bat_number=1, pa_event_raw="home_run"),
        _pitch(at_bat_number=2, pa_event_raw="strikeout"),
        _pitch(at_bat_number=3, pa_event_raw="single"),
    ]
    pa_records = group_pitches_into_plate_appearances(pitches)
    enriched = attach_prior_outcome_rates(pa_records)

    built = [
        build_pa_probability_distribution(record, method="matchup_combination")
        for record in enriched
    ]
    assert len(built) == 3
    for record in built:
        _assert_valid_distribution(record["probabilities"])
        validate_pa_probability_distribution(record)

    # league history accumulates strictly before each PA
    assert [record["league_pa_count_used"] for record in built] == [0, 1, 2]
