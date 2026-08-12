from pathlib import Path

import pytest

from mlb.plate_appearance import (
    DETAILED_TO_CATEGORY,
    INCOMPLETE_TERMINAL_EVENTS,
    PLATE_APPEARANCE_FIELD_ORDER,
    PLATE_APPEARANCE_SCHEMA_VERSION,
    RATE_CATEGORIES,
    TERMINAL_EVENT_TAXONOMY,
    PlateAppearanceValidationError,
    build_rsb_pa_id,
    classify_terminal_event,
    group_pitches_into_plate_appearances,
)
from mlb.statcast_normalize import NORMALIZED_PITCH_FIELD_ORDER, build_rsb_pitch_id


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


def _pa_pitches(*, at_bat_number=1, n=1, terminal_event="field_out", **shared_overrides) -> list:
    pitches = []
    for pitch_number in range(1, n + 1):
        overrides = dict(shared_overrides)
        overrides["at_bat_number"] = at_bat_number
        overrides["pitch_number"] = pitch_number
        overrides["pa_event_raw"] = terminal_event if pitch_number == n else None
        pitches.append(_pitch(**overrides))
    return pitches


# ---------------------------------------------------------------------------
# normal cases
# ---------------------------------------------------------------------------


def test_single_pitch_completed_pa():
    records = group_pitches_into_plate_appearances(_pa_pitches(n=1, terminal_event="single"))
    assert len(records) == 1
    pa = records[0]
    assert pa["pa_status"] == "completed"
    assert pa["pa_outcome_detailed"] == "single"
    assert pa["pa_outcome_category"] == "single"
    assert pa["pitch_count"] == 1


def test_multi_pitch_completed_pa():
    records = group_pitches_into_plate_appearances(_pa_pitches(n=5, terminal_event="walk"))
    assert len(records) == 1
    pa = records[0]
    assert pa["pitch_count"] == 5
    assert pa["pa_outcome_category"] == "walk"
    assert pa["source_pitch_ids"] == [
        build_rsb_pitch_id("700001", 1, i) for i in range(1, 6)
    ]


def test_multiple_pas_in_one_game():
    pitches = _pa_pitches(at_bat_number=1, n=1, terminal_event="strikeout") + _pa_pitches(
        at_bat_number=2, n=1, terminal_event="walk"
    )
    records = group_pitches_into_plate_appearances(pitches)
    assert len(records) == 2
    assert [r["at_bat_number"] for r in records] == [1, 2]


def test_multiple_games():
    pitches = _pa_pitches(
        at_bat_number=1, n=1, terminal_event="single", source_game_id="700001"
    ) + _pa_pitches(at_bat_number=1, n=1, terminal_event="double", source_game_id="700002")
    records = group_pitches_into_plate_appearances(pitches)
    assert len(records) == 2
    assert {r["source_game_id"] for r in records} == {"700001", "700002"}


def test_result_has_exactly_the_contract_keys():
    records = group_pitches_into_plate_appearances(_pa_pitches(n=1, terminal_event="home_run"))
    assert list(records[0].keys()) == list(PLATE_APPEARANCE_FIELD_ORDER)


def test_result_schema_version_stamped():
    records = group_pitches_into_plate_appearances(_pa_pitches(n=1, terminal_event="home_run"))
    assert records[0]["normalized_pa_schema_version"] == PLATE_APPEARANCE_SCHEMA_VERSION


def test_context_fields_carried_from_first_pitch():
    records = group_pitches_into_plate_appearances(
        _pa_pitches(n=3, terminal_event="field_out", inning=4, inning_half="bottom")
    )
    pa = records[0]
    assert pa["inning"] == 4
    assert pa["inning_half"] == "bottom"
    assert pa["outs_before_pa"] == 0
    assert pa["on_1b_before_pa"] is None


# ---------------------------------------------------------------------------
# taxonomy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_event,expected_detailed", sorted(TERMINAL_EVENT_TAXONOMY.items()))
def test_every_terminal_taxonomy_value_classifies(raw_event, expected_detailed):
    records = group_pitches_into_plate_appearances(_pa_pitches(n=1, terminal_event=raw_event))
    pa = records[0]
    assert pa["pa_outcome_detailed"] == expected_detailed
    assert pa["pa_outcome_category"] == DETAILED_TO_CATEGORY[expected_detailed]


def test_intentional_walk_distinct_from_ordinary_walk():
    walk_records = group_pitches_into_plate_appearances(_pa_pitches(n=1, terminal_event="walk"))
    ibb_records = group_pitches_into_plate_appearances(
        _pa_pitches(n=1, terminal_event="intent_walk")
    )
    assert walk_records[0]["pa_outcome_detailed"] == "walk"
    assert walk_records[0]["pa_outcome_category"] == "walk"
    assert ibb_records[0]["pa_outcome_detailed"] == "intent_walk"
    assert ibb_records[0]["pa_outcome_category"] == "intentional_walk"
    assert walk_records[0]["pa_outcome_category"] != ibb_records[0]["pa_outcome_category"]


def test_classify_terminal_event_raises_for_unrecognized_value():
    with pytest.raises(PlateAppearanceValidationError):
        classify_terminal_event("some_future_statcast_event_code")


def test_rate_categories_cover_every_category_value():
    assert set(RATE_CATEGORIES) == set(DETAILED_TO_CATEGORY.values())


# ---------------------------------------------------------------------------
# incompleteness (not fatal)
# ---------------------------------------------------------------------------


def test_null_terminal_event_is_incomplete():
    pitches = _pa_pitches(n=2, terminal_event="single")
    pitches[-1]["pa_event_raw"] = None
    records = group_pitches_into_plate_appearances(pitches)
    pa = records[0]
    assert pa["pa_status"] == "incomplete"
    assert pa["pa_outcome_detailed"] is None
    assert pa["pa_outcome_category"] is None
    assert pa["terminal_pa_event_raw"] is None


def test_incomplete_pa_still_carries_identity_and_context():
    pitches = _pa_pitches(n=3, terminal_event="single")
    pitches[-1]["pa_event_raw"] = None
    records = group_pitches_into_plate_appearances(pitches)
    pa = records[0]
    assert pa["pa_status"] == "incomplete"
    assert pa["batter_id"] == "600001"
    assert pa["pitch_count"] == 3


# ---------------------------------------------------------------------------
# incomplete-terminal-event markers (real Savant validation: truncated_pa)
# ---------------------------------------------------------------------------


def test_truncated_pa_terminal_event_is_incomplete():
    records = group_pitches_into_plate_appearances(
        _pa_pitches(n=2, terminal_event="truncated_pa")
    )
    pa = records[0]
    assert pa["pa_status"] == "incomplete"
    assert pa["pa_outcome_detailed"] is None
    assert pa["pa_outcome_category"] is None
    assert pa["terminal_pa_event_raw"] == "truncated_pa"


def test_truncated_pa_not_in_terminal_event_taxonomy():
    assert "truncated_pa" not in TERMINAL_EVENT_TAXONOMY


def test_truncated_pa_not_in_rate_categories():
    assert "truncated_pa" not in RATE_CATEGORIES
    assert "truncated_pa" in INCOMPLETE_TERMINAL_EVENTS


def test_non_terminal_truncated_pa_fails_closed():
    pitches = _pa_pitches(n=3, terminal_event="single")
    pitches[0]["pa_event_raw"] = "truncated_pa"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


# ---------------------------------------------------------------------------
# terminal detection contradictions
# ---------------------------------------------------------------------------


def test_unrecognized_terminal_event_fails_closed():
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(
            _pa_pitches(n=1, terminal_event="some_unrecognized_code")
        )


def test_non_null_event_on_non_terminal_pitch_fails_closed():
    pitches = _pa_pitches(n=3, terminal_event="single")
    pitches[0]["pa_event_raw"] = "wild_pitch"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


def test_non_null_terminal_looking_event_on_non_terminal_pitch_fails_closed():
    pitches = _pa_pitches(n=3, terminal_event="single")
    pitches[0]["pa_event_raw"] = "double"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


# ---------------------------------------------------------------------------
# chronology contradictions
# ---------------------------------------------------------------------------


def test_duplicate_pitch_number_within_pa_fails_closed():
    pitches = _pa_pitches(n=2, terminal_event="single")
    pitches[1]["pitch_number"] = 1
    pitches[1]["rsb_pitch_id"] = build_rsb_pitch_id("700001", 1, 1) + "_dup"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


def test_non_contiguous_pitch_number_fails_closed():
    pitches = _pa_pitches(n=2, terminal_event="single")
    pitches[1]["pitch_number"] = 3
    pitches[1]["rsb_pitch_id"] = build_rsb_pitch_id("700001", 1, 3)
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


def test_duplicate_rsb_pitch_id_across_input_fails_closed():
    pitches = _pa_pitches(n=1, terminal_event="single")
    duplicate = dict(pitches[0])
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches + [duplicate])


# ---------------------------------------------------------------------------
# context-consistency contradictions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("batter_id", "999999"),
        ("batter_stands", "L"),
        ("game_date", "2024-04-02"),
        ("game_year", 2025),
        ("game_type", "P"),
        ("home_team", "BOS"),
        ("away_team", "NYY"),
        ("inning", 2),
        ("inning_half", "bottom"),
        ("snapshot_id", "some_other_snapshot"),
        ("source_provider", "some_other_provider"),
        ("normalized_schema_version", "2"),
    ],
)
def test_inconsistent_context_field_fails_closed(field, bad_value):
    pitches = _pa_pitches(n=2, terminal_event="single")
    pitches[1][field] = bad_value
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


# ---------------------------------------------------------------------------
# pitcher substitution
# ---------------------------------------------------------------------------


def test_single_pitcher_pa_is_rate_eligible():
    records = group_pitches_into_plate_appearances(_pa_pitches(n=3, terminal_event="single"))
    pa = records[0]
    assert pa["pitcher_rate_eligible"] is True
    assert pa["source_pitcher_ids"] == ["700010"]


def test_legitimate_pitcher_substitution_preserves_pa():
    pitches = _pa_pitches(n=4, terminal_event="single")
    pitches[2]["pitcher_id"] = "700099"
    pitches[3]["pitcher_id"] = "700099"
    pitches[2]["pitcher_throws"] = "R"
    pitches[3]["pitcher_throws"] = "R"
    records = group_pitches_into_plate_appearances(pitches)
    pa = records[0]
    assert pa["pa_status"] == "completed"
    assert pa["pitcher_rate_eligible"] is False
    assert pa["source_pitcher_ids"] == ["700010", "700099"]
    # terminal pitcher (on the mound for the last pitch) is recorded as pitcher_id
    assert pa["pitcher_id"] == "700099"
    assert pa["pitcher_throws"] == "R"


def test_pitcher_sequence_reverting_to_earlier_pitcher_fails_closed():
    pitches = _pa_pitches(n=3, terminal_event="single")
    pitches[0]["pitcher_id"] = "A"
    pitches[1]["pitcher_id"] = "B"
    pitches[2]["pitcher_id"] = "A"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


def test_two_forward_only_substitutions_accepted():
    pitches = _pa_pitches(n=3, terminal_event="single")
    pitches[0]["pitcher_id"], pitches[0]["pitcher_throws"] = "A", "L"
    pitches[1]["pitcher_id"], pitches[1]["pitcher_throws"] = "B", "R"
    pitches[2]["pitcher_id"], pitches[2]["pitcher_throws"] = "C", "L"
    records = group_pitches_into_plate_appearances(pitches)
    pa = records[0]
    assert pa["pa_status"] == "completed"
    assert pa["source_pitcher_ids"] == ["A", "B", "C"]
    assert pa["pitcher_rate_eligible"] is False
    assert pa["pitcher_id"] == "C"
    assert pa["pitcher_throws"] == "L"


def test_three_pitcher_sequence_reverting_still_fails_closed():
    pitches = _pa_pitches(n=4, terminal_event="single")
    pitches[0]["pitcher_id"] = "A"
    pitches[1]["pitcher_id"] = "B"
    pitches[2]["pitcher_id"] = "C"
    pitches[3]["pitcher_id"] = "A"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


# ---------------------------------------------------------------------------
# pitcher throw-hand consistency
# ---------------------------------------------------------------------------


def test_same_pitcher_id_with_inconsistent_throws_fails_closed():
    pitches = _pa_pitches(n=2, terminal_event="single")
    pitches[0]["pitcher_id"], pitches[0]["pitcher_throws"] = "A", "L"
    pitches[1]["pitcher_id"], pitches[1]["pitcher_throws"] = "A", "R"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(pitches)


def test_forward_substitution_with_each_pitcher_internally_consistent_accepted():
    pitches = _pa_pitches(n=2, terminal_event="single")
    pitches[0]["pitcher_id"], pitches[0]["pitcher_throws"] = "A", "L"
    pitches[1]["pitcher_id"], pitches[1]["pitcher_throws"] = "B", "R"
    records = group_pitches_into_plate_appearances(pitches)
    pa = records[0]
    assert pa["pitcher_rate_eligible"] is False
    assert pa["pitcher_id"] == "B"
    assert pa["pitcher_throws"] == "R"


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------


def test_build_rsb_pa_id_deterministic():
    assert build_rsb_pa_id("700001", 1) == build_rsb_pa_id("700001", 1)


def test_build_rsb_pa_id_differs_across_at_bat_number():
    assert build_rsb_pa_id("700001", 1) != build_rsb_pa_id("700001", 2)


def test_rsb_pa_id_stable_regardless_of_non_identity_fields():
    records_1 = group_pitches_into_plate_appearances(
        _pa_pitches(n=1, terminal_event="single", release_speed=90.0)
    )
    records_2 = group_pitches_into_plate_appearances(
        _pa_pitches(n=1, terminal_event="double", release_speed=99.0)
    )
    assert records_1[0]["rsb_pa_id"] == records_2[0]["rsb_pa_id"]


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------


def test_output_ordered_regardless_of_input_order():
    early = _pa_pitches(
        at_bat_number=1, n=1, terminal_event="single", game_date="2024-04-01", source_game_id="700001"
    )
    late = _pa_pitches(
        at_bat_number=1, n=1, terminal_event="double", game_date="2024-04-02", source_game_id="700002"
    )
    records = group_pitches_into_plate_appearances(late + early)
    assert [r["game_date"] for r in records] == ["2024-04-01", "2024-04-02"]


# ---------------------------------------------------------------------------
# malformed input
# ---------------------------------------------------------------------------


def test_rejects_non_list_input():
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances("not-a-list")


def test_rejects_non_dict_pitch_record():
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances(["not-a-dict"])


def test_rejects_pitch_record_missing_a_required_field():
    pitch = _pa_pitches(n=1, terminal_event="single")[0]
    del pitch["batter_id"]
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances([pitch])


def test_rejects_pitch_record_with_extra_field():
    pitch = _pa_pitches(n=1, terminal_event="single")[0]
    pitch["unexpected_extra_field"] = "x"
    with pytest.raises(PlateAppearanceValidationError):
        group_pitches_into_plate_appearances([pitch])


def test_empty_input_returns_empty_list():
    assert group_pitches_into_plate_appearances([]) == []


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_plate_appearance_has_no_banned_imports():
    import ast

    src = Path(__file__).resolve().parents[1] / "src" / "mlb" / "plate_appearance.py"
    tree = ast.parse(src.read_text())
    banned = {
        "requests",
        "urllib",
        "http",
        "socket",
        "pybaseball",
        "pandas",
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
