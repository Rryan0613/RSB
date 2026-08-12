from pathlib import Path

import pytest

from mlb.plate_appearance import (
    INCOMPLETE_TERMINAL_EVENTS,
    PLATE_APPEARANCE_FIELD_ORDER,
    PLATE_APPEARANCE_SCHEMA_VERSION,
    RATE_CATEGORIES,
    build_rsb_pa_id,
)
from mlb.plate_appearance_rates import (
    RATE_ENRICHED_FIELD_ORDER,
    PlateAppearanceRateError,
    attach_prior_outcome_rates,
)


def _pa(
    *,
    source_game_id="700001",
    game_date="2024-04-01",
    at_bat_number=1,
    batter_id="600001",
    pitcher_id="700010",
    pitcher_rate_eligible=True,
    pa_status="completed",
    pa_outcome_category="single",
    **overrides,
) -> dict:
    base = {
        "rsb_pa_id": build_rsb_pa_id(source_game_id, at_bat_number),
        "source_game_id": source_game_id,
        "game_date": game_date,
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
    }
    base.update(overrides)
    return {field: base[field] for field in PLATE_APPEARANCE_FIELD_ORDER}


def _find(records, source_game_id, at_bat_number):
    for r in records:
        if r["source_game_id"] == source_game_id and r["at_bat_number"] == at_bat_number:
            return r
    raise AssertionError("record not found")


# ---------------------------------------------------------------------------
# shape / determinism
# ---------------------------------------------------------------------------


def test_output_field_order_matches_contract():
    records = attach_prior_outcome_rates([_pa()])
    assert list(records[0].keys()) == list(RATE_ENRICHED_FIELD_ORDER)


def test_empty_input_returns_empty_list():
    assert attach_prior_outcome_rates([]) == []


def test_deterministic_for_identical_input():
    pas = [_pa(at_bat_number=1, pa_outcome_category="single"), _pa(at_bat_number=2, pa_outcome_category="walk")]
    assert attach_prior_outcome_rates(pas) == attach_prior_outcome_rates(pas)


# ---------------------------------------------------------------------------
# first observation
# ---------------------------------------------------------------------------


def test_first_pa_has_zero_prior_state_and_none_rates():
    records = attach_prior_outcome_rates([_pa()])
    pa = records[0]
    assert pa["prior_batter_pa_count"] == 0
    assert pa["prior_pitcher_pa_count"] == 0
    assert pa["prior_league_pa_count"] == 0
    assert pa["prior_batter_outcome_counts"] == {c: 0 for c in RATE_CATEGORIES}
    assert pa["prior_batter_outcome_rates"] == {c: None for c in RATE_CATEGORIES}
    assert pa["prior_pitcher_outcome_rates"] == {c: None for c in RATE_CATEGORIES}
    assert pa["prior_league_outcome_rates"] == {c: None for c in RATE_CATEGORIES}


# ---------------------------------------------------------------------------
# within-game chronology
# ---------------------------------------------------------------------------


def test_second_pa_in_same_game_sees_first_pas_outcome():
    pas = [
        _pa(at_bat_number=1, batter_id="B1", pitcher_id="P1", pa_outcome_category="walk"),
        _pa(at_bat_number=2, batter_id="B1", pitcher_id="P1", pa_outcome_category="single"),
    ]
    records = attach_prior_outcome_rates(pas)
    second = _find(records, "700001", 2)
    assert second["prior_batter_pa_count"] == 1
    assert second["prior_batter_outcome_counts"]["walk"] == 1
    assert second["prior_batter_outcome_rates"]["walk"] == pytest.approx(1.0)
    assert second["prior_batter_outcome_rates"]["single"] == pytest.approx(0.0)
    assert second["prior_pitcher_pa_count"] == 1
    assert second["prior_league_pa_count"] == 1


def test_rates_computed_over_full_category_set_when_denominator_positive():
    pas = [
        _pa(at_bat_number=1, batter_id="B1", pa_outcome_category="strikeout"),
        _pa(at_bat_number=2, batter_id="B1", pa_outcome_category="strikeout"),
        _pa(at_bat_number=3, batter_id="B1", pa_outcome_category="home_run"),
        _pa(at_bat_number=4, batter_id="B1", pa_outcome_category="single"),
    ]
    records = attach_prior_outcome_rates(pas)
    fourth = _find(records, "700001", 4)
    assert fourth["prior_batter_pa_count"] == 3
    assert fourth["prior_batter_outcome_rates"]["strikeout"] == pytest.approx(2 / 3)
    assert fourth["prior_batter_outcome_rates"]["home_run"] == pytest.approx(1 / 3)
    assert fourth["prior_batter_outcome_rates"]["walk"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# same-day cross-game leakage isolation
# ---------------------------------------------------------------------------


def test_same_day_different_game_does_not_leak():
    pas = [
        _pa(source_game_id="700001", game_date="2024-04-01", at_bat_number=1, batter_id="B1", pa_outcome_category="single"),
        _pa(source_game_id="700002", game_date="2024-04-01", at_bat_number=1, batter_id="B1", pa_outcome_category="double"),
    ]
    records = attach_prior_outcome_rates(pas)
    second_game_pa = _find(records, "700002", 1)
    assert second_game_pa["prior_batter_pa_count"] == 0
    assert second_game_pa["prior_batter_outcome_rates"] == {c: None for c in RATE_CATEGORIES}


def test_same_day_different_game_isolation_is_symmetric():
    pas = [
        _pa(source_game_id="700002", game_date="2024-04-01", at_bat_number=1, batter_id="B1", pa_outcome_category="double"),
        _pa(source_game_id="700001", game_date="2024-04-01", at_bat_number=1, batter_id="B1", pa_outcome_category="single"),
    ]
    records = attach_prior_outcome_rates(pas)
    game_700001_pa = _find(records, "700001", 1)
    assert game_700001_pa["prior_batter_pa_count"] == 0


def test_earlier_date_contributes_to_later_date():
    pas = [
        _pa(source_game_id="700001", game_date="2024-04-01", at_bat_number=1, batter_id="B1", pa_outcome_category="single"),
        _pa(source_game_id="700002", game_date="2024-04-02", at_bat_number=1, batter_id="B1", pa_outcome_category="double"),
    ]
    records = attach_prior_outcome_rates(pas)
    later = _find(records, "700002", 1)
    assert later["prior_batter_pa_count"] == 1
    assert later["prior_batter_outcome_counts"]["single"] == 1


# ---------------------------------------------------------------------------
# pitcher-rate eligibility
# ---------------------------------------------------------------------------


def test_ineligible_pa_does_not_update_pitcher_history_but_updates_batter_and_league():
    pas = [
        _pa(
            source_game_id="700001", game_date="2024-04-01", at_bat_number=1,
            batter_id="Bx", pitcher_id="P1", pitcher_rate_eligible=False,
            pa_outcome_category="triple",
        ),
        _pa(
            source_game_id="700002", game_date="2024-04-02", at_bat_number=1,
            batter_id="Bx", pitcher_id="P2", pa_outcome_category="single",
        ),
        _pa(
            source_game_id="700002", game_date="2024-04-02", at_bat_number=2,
            batter_id="By", pitcher_id="P1", pitcher_rate_eligible=True,
            pa_outcome_category="single",
        ),
    ]
    records = attach_prior_outcome_rates(pas)

    batter_followup = _find(records, "700002", 1)
    assert batter_followup["prior_batter_pa_count"] == 1
    assert batter_followup["prior_batter_outcome_counts"]["triple"] == 1
    assert batter_followup["prior_league_pa_count"] == 1

    pitcher_followup = _find(records, "700002", 2)
    assert pitcher_followup["prior_pitcher_pa_count"] == 0


def test_prior_pitcher_state_still_read_even_when_this_pa_is_ineligible():
    pas = [
        _pa(
            source_game_id="700001", game_date="2024-04-01", at_bat_number=1,
            pitcher_id="P1", pitcher_rate_eligible=True, pa_outcome_category="single",
        ),
        _pa(
            source_game_id="700002", game_date="2024-04-02", at_bat_number=1,
            pitcher_id="P1", pitcher_rate_eligible=False, pa_outcome_category="double",
        ),
    ]
    records = attach_prior_outcome_rates(pas)
    second = _find(records, "700002", 1)
    assert second["prior_pitcher_pa_count"] == 1
    assert second["prior_pitcher_outcome_counts"]["single"] == 1


# ---------------------------------------------------------------------------
# incomplete PAs
# ---------------------------------------------------------------------------


def test_incomplete_pa_gets_prior_state_but_does_not_update_counters():
    pas = [
        _pa(at_bat_number=1, batter_id="B1", pa_status="incomplete", pa_outcome_category=None),
        _pa(at_bat_number=2, batter_id="B1", pa_outcome_category="single"),
    ]
    records = attach_prior_outcome_rates(pas)
    first = _find(records, "700001", 1)
    second = _find(records, "700001", 2)
    assert first["prior_batter_pa_count"] == 0
    assert second["prior_batter_pa_count"] == 0  # incomplete PA never updated the counter


# ---------------------------------------------------------------------------
# incomplete-terminal-event markers (real Savant validation: truncated_pa)
# ---------------------------------------------------------------------------


def test_incomplete_pa_with_truncated_pa_terminal_event_is_accepted():
    assert "truncated_pa" in INCOMPLETE_TERMINAL_EVENTS
    pa = _pa(pa_status="incomplete", pa_outcome_category=None)
    pa["terminal_pa_event_raw"] = "truncated_pa"
    records = attach_prior_outcome_rates([pa])
    assert records[0]["terminal_pa_event_raw"] == "truncated_pa"


def test_truncated_pa_receives_prior_state_normally():
    pas = [
        _pa(at_bat_number=1, batter_id="B1", pitcher_id="P1", pa_outcome_category="walk"),
        _pa(at_bat_number=2, batter_id="B1", pitcher_id="P1", pa_status="incomplete", pa_outcome_category=None),
    ]
    pas[1]["terminal_pa_event_raw"] = "truncated_pa"
    records = attach_prior_outcome_rates(pas)
    second = _find(records, "700001", 2)
    assert second["prior_batter_pa_count"] == 1
    assert second["prior_batter_outcome_counts"]["walk"] == 1


def test_truncated_pa_does_not_update_batter_pitcher_or_league_history():
    pas = [
        _pa(
            source_game_id="700001", game_date="2024-04-01", at_bat_number=1,
            batter_id="Bx", pitcher_id="P1", pa_status="incomplete", pa_outcome_category=None,
        ),
        _pa(
            source_game_id="700002", game_date="2024-04-02", at_bat_number=1,
            batter_id="Bx", pitcher_id="P1", pa_outcome_category="single",
        ),
    ]
    pas[0]["terminal_pa_event_raw"] = "truncated_pa"
    records = attach_prior_outcome_rates(pas)
    followup = _find(records, "700002", 1)
    assert followup["prior_batter_pa_count"] == 0
    assert followup["prior_pitcher_pa_count"] == 0
    assert followup["prior_league_pa_count"] == 0


def test_incomplete_pa_with_arbitrary_unknown_non_null_terminal_event_still_fails():
    pa = _pa(pa_status="incomplete", pa_outcome_category=None)
    pa["terminal_pa_event_raw"] = "some_other_unrecognized_incomplete_marker"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_completed_pa_with_truncated_pa_terminal_event_fails():
    pa = _pa(pa_outcome_category="single")
    pa["terminal_pa_event_raw"] = "truncated_pa"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_incomplete_pa_with_none_terminal_event_raw_still_works():
    pa = _pa(pa_status="incomplete", pa_outcome_category=None)
    assert pa["terminal_pa_event_raw"] is None
    records = attach_prior_outcome_rates([pa])
    assert records[0]["terminal_pa_event_raw"] is None


# ---------------------------------------------------------------------------
# malformed input
# ---------------------------------------------------------------------------


def test_rejects_non_list_input():
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates("not-a-list")


def test_rejects_record_missing_a_required_field():
    pa = _pa()
    del pa["batter_id"]
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_record_with_extra_field():
    pa = _pa()
    pa["unexpected_extra_field"] = "x"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_invalid_pa_status():
    pa = _pa()
    pa["pa_status"] = "bogus"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_stringy_pitcher_rate_eligible_rather_than_treating_it_as_truthy():
    # Regression: "False" is a non-empty string and therefore truthy in
    # Python; it must be rejected, not silently accepted and treated as
    # eligible=True by downstream counting.
    pa = _pa()
    pa["pitcher_rate_eligible"] = "False"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_wrong_normalized_pa_schema_version():
    pa = _pa()
    pa["normalized_pa_schema_version"] = "999"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_completed_pa_with_unrecognized_terminal_event():
    pa = _pa()
    pa["terminal_pa_event_raw"] = "some_unrecognized_code"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_completed_pa_with_detailed_outcome_inconsistent_with_terminal_event():
    pa = _pa(pa_outcome_category="single")
    pa["terminal_pa_event_raw"] = "single"
    pa["pa_outcome_detailed"] = "double"  # inconsistent with terminal_pa_event_raw
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_completed_pa_with_category_inconsistent_with_detailed_outcome():
    pa = _pa(pa_outcome_category="single")
    pa["terminal_pa_event_raw"] = "single"
    pa["pa_outcome_detailed"] = "single"
    pa["pa_outcome_category"] = "double"  # inconsistent with pa_outcome_detailed
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_incomplete_pa_with_non_null_terminal_event_raw():
    pa = _pa(pa_status="incomplete", pa_outcome_category=None)
    pa["terminal_pa_event_raw"] = "single"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_incomplete_pa_with_non_null_detailed_outcome():
    pa = _pa(pa_status="incomplete", pa_outcome_category=None)
    pa["pa_outcome_detailed"] = "single"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_completed_pa_with_null_category():
    pa = _pa()
    pa["pa_outcome_category"] = None
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_incomplete_pa_with_non_null_category():
    pa = _pa(pa_status="incomplete", pa_outcome_category=None)
    pa["pa_outcome_category"] = "single"
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa])


def test_rejects_duplicate_rsb_pa_id():
    pa = _pa()
    with pytest.raises(PlateAppearanceRateError):
        attach_prior_outcome_rates([pa, dict(pa)])


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_plate_appearance_rates_has_no_banned_imports():
    import ast

    src = Path(__file__).resolve().parents[1] / "src" / "mlb" / "plate_appearance_rates.py"
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
