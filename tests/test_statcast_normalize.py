from pathlib import Path

import pytest

from mlb.statcast_normalize import (
    NORMALIZED_PITCH_FIELD_ORDER,
    NULLABLE_NORMALIZED_FIELDS,
    REQUIRED_NORMALIZED_FIELDS,
    SOURCE_FIELD_MAPPING,
    STATCAST_PITCH_SCHEMA_VERSION,
    StatcastNormalizationError,
    build_rsb_pitch_id,
    normalize_statcast_row,
    normalize_statcast_snapshot,
)

SNAPSHOT_ID = "20260811T120000Z_abcdef012345"
SOURCE_PROVIDER = "baseball_savant"
DATE_RANGE = {"start_date": "2024-04-01", "end_date": "2024-04-01"}


def _valid_row(**overrides):
    row = {
        "game_pk": "700001",
        "sv_id": "240401_190001",
        "game_date": "2024-04-01",
        "game_year": "2024",
        "at_bat_number": "1",
        "pitch_number": "1",
        "inning": "1",
        "inning_topbot": "Top",
        "game_type": "R",
        "home_team": "NYY",
        "away_team": "BOS",
        "home_score": "0",
        "away_score": "0",
        "batter": "600001",
        "pitcher": "700010",
        "stand": "R",
        "p_throws": "L",
        "on_1b": "",
        "on_2b": "",
        "on_3b": "",
        "balls": "0",
        "strikes": "0",
        "outs_when_up": "0",
        "pitch_type": "FF",
        "pitch_name": "4-Seam Fastball",
        "release_speed": "95.1",
        "zone": "5",
        "type": "S",
        "events": "",
        "bb_type": "",
        "launch_speed": "",
        "launch_angle": "",
        "hit_distance": "",
    }
    row.update(overrides)
    return row


def _normalize(**overrides):
    return normalize_statcast_row(
        _valid_row(**overrides),
        source_row_index=0,
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
    )


# ---------------------------------------------------------------------------
# valid source row / shape
# ---------------------------------------------------------------------------


def test_normalize_valid_row_returns_plain_dict():
    result = _normalize()
    assert type(result) is dict


def test_normalize_valid_row_has_exactly_the_contract_keys():
    result = _normalize()
    assert list(result.keys()) == list(NORMALIZED_PITCH_FIELD_ORDER)


def test_normalize_no_pa_terminal_key():
    result = _normalize()
    assert "pa_terminal" not in result


def test_normalize_no_venue_key():
    result = _normalize()
    assert "venue" not in result


def test_normalize_valid_row_field_values():
    result = _normalize()
    assert result["source_game_id"] == "700001"
    assert result["source_play_id"] == "240401_190001"
    assert result["game_date"] == "2024-04-01"
    assert result["game_year"] == 2024
    assert result["at_bat_number"] == 1
    assert result["pitch_number"] == 1
    assert result["inning"] == 1
    assert result["inning_half"] == "top"
    assert result["game_type"] == "R"
    assert result["home_team"] == "NYY"
    assert result["away_team"] == "BOS"
    assert result["home_score"] == 0
    assert result["away_score"] == 0
    assert result["batter_id"] == "600001"
    assert result["pitcher_id"] == "700010"
    assert result["batter_stands"] == "R"
    assert result["pitcher_throws"] == "L"
    assert result["balls"] == 0
    assert result["strikes"] == 0
    assert result["outs"] == 0
    assert result["pitch_type"] == "FF"
    assert result["release_speed"] == pytest.approx(95.1)
    assert result["zone"] == 5
    assert result["pitch_result_type"] == "S"
    assert result["snapshot_id"] == SNAPSHOT_ID
    assert result["source_provider"] == SOURCE_PROVIDER
    assert result["normalized_schema_version"] == STATCAST_PITCH_SCHEMA_VERSION
    assert result["source_row_index"] == 0


def test_normalize_row_source_field_mapping_covers_all_required_and_nullable_fields():
    assert REQUIRED_NORMALIZED_FIELDS | NULLABLE_NORMALIZED_FIELDS == frozenset(
        SOURCE_FIELD_MAPPING
    )


# ---------------------------------------------------------------------------
# required fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("normalized_field", sorted(REQUIRED_NORMALIZED_FIELDS))
def test_normalize_missing_required_field_raises(normalized_field):
    source_column = SOURCE_FIELD_MAPPING[normalized_field]
    with pytest.raises(StatcastNormalizationError):
        _normalize(**{source_column: ""})


# ---------------------------------------------------------------------------
# nullable optional fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("normalized_field", sorted(NULLABLE_NORMALIZED_FIELDS))
def test_normalize_missing_optional_field_normalizes_to_none(normalized_field):
    source_column = SOURCE_FIELD_MAPPING[normalized_field]
    result = _normalize(**{source_column: ""})
    assert result[normalized_field] is None


def test_normalize_all_optional_fields_blank_still_succeeds():
    overrides = {SOURCE_FIELD_MAPPING[f]: "" for f in NULLABLE_NORMALIZED_FIELDS}
    result = _normalize(**overrides)
    for field in NULLABLE_NORMALIZED_FIELDS:
        assert result[field] is None


# ---------------------------------------------------------------------------
# type coercion
# ---------------------------------------------------------------------------


def test_normalize_coerces_numeric_strings_to_int():
    result = _normalize(balls="2", strikes="1", outs_when_up="1")
    assert result["balls"] == 2 and type(result["balls"]) is int
    assert result["strikes"] == 1 and type(result["strikes"]) is int
    assert result["outs"] == 1 and type(result["outs"]) is int


def test_normalize_coerces_float_string_release_speed():
    result = _normalize(release_speed="88.7")
    assert result["release_speed"] == pytest.approx(88.7)
    assert type(result["release_speed"]) is float


def test_normalize_coerces_whole_number_float_string_to_int():
    result = _normalize(at_bat_number="1.0", pitch_number="2.0")
    assert result["at_bat_number"] == 1
    assert result["pitch_number"] == 2


def test_normalize_rejects_fractional_float_string_for_int_field():
    with pytest.raises(StatcastNormalizationError):
        _normalize(at_bat_number="1.5")


@pytest.mark.parametrize("field", ["balls", "strikes", "outs_when_up", "at_bat_number"])
def test_normalize_rejects_bool_for_numeric_field(field):
    with pytest.raises(StatcastNormalizationError):
        _normalize(**{field: True})


def test_normalize_rejects_bool_for_float_field():
    with pytest.raises(StatcastNormalizationError):
        _normalize(release_speed=True)


# ---------------------------------------------------------------------------
# side / slug normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [("R", "R"), ("r", "R"), ("L", "L"), ("l", "L")])
def test_normalize_batter_stands(raw, expected):
    result = _normalize(stand=raw)
    assert result["batter_stands"] == expected


@pytest.mark.parametrize("raw,expected", [("R", "R"), ("l", "L")])
def test_normalize_pitcher_throws(raw, expected):
    result = _normalize(p_throws=raw)
    assert result["pitcher_throws"] == expected


def test_normalize_rejects_invalid_batter_stands():
    with pytest.raises(StatcastNormalizationError):
        _normalize(stand="X")


@pytest.mark.parametrize(
    "raw,expected", [("Top", "top"), ("top", "top"), ("TOP", "top"), ("Bot", "bottom"), ("bot", "bottom")]
)
def test_normalize_inning_half(raw, expected):
    result = _normalize(inning_topbot=raw)
    assert result["inning_half"] == expected


def test_normalize_rejects_invalid_inning_half():
    with pytest.raises(StatcastNormalizationError):
        _normalize(inning_topbot="Middle")


def test_normalize_team_codes_uppercased():
    result = _normalize(home_team="nyy", away_team="bos")
    assert result["home_team"] == "NYY"
    assert result["away_team"] == "BOS"


@pytest.mark.parametrize("raw,expected", [("S", "S"), ("s", "S"), ("B", "B"), ("X", "X")])
def test_normalize_pitch_result_type(raw, expected):
    result = _normalize(type=raw)
    assert result["pitch_result_type"] == expected


def test_normalize_rejects_invalid_pitch_result_type():
    with pytest.raises(StatcastNormalizationError):
        _normalize(type="Q")


# ---------------------------------------------------------------------------
# pa_event_raw passthrough
# ---------------------------------------------------------------------------


def test_normalize_pa_event_raw_passthrough():
    result = _normalize(events="strikeout")
    assert result["pa_event_raw"] == "strikeout"


def test_normalize_pa_event_raw_accepts_any_nonempty_string_no_taxonomy():
    result = _normalize(events="some_future_statcast_event_code")
    assert result["pa_event_raw"] == "some_future_statcast_event_code"


def test_normalize_pa_event_raw_null_when_blank():
    result = _normalize(events="")
    assert result["pa_event_raw"] is None


# ---------------------------------------------------------------------------
# stable rsb_pitch_id
# ---------------------------------------------------------------------------


def test_rsb_pitch_id_deterministic_for_same_identity():
    id_1 = build_rsb_pitch_id("700001", 1, 1)
    id_2 = build_rsb_pitch_id("700001", 1, 1)
    assert id_1 == id_2


def test_rsb_pitch_id_differs_for_different_pitch_number():
    id_1 = build_rsb_pitch_id("700001", 1, 1)
    id_2 = build_rsb_pitch_id("700001", 1, 2)
    assert id_1 != id_2


def test_normalize_row_rsb_pitch_id_stable_regardless_of_other_fields():
    result_1 = _normalize(release_speed="95.1")
    result_2 = _normalize(release_speed="99.9", pitch_type="SL")
    assert result_1["rsb_pitch_id"] == result_2["rsb_pitch_id"]


def test_normalize_row_rsb_pitch_id_changes_with_at_bat_number():
    result_1 = _normalize(at_bat_number="1")
    result_2 = _normalize(at_bat_number="2")
    assert result_1["rsb_pitch_id"] != result_2["rsb_pitch_id"]


# ---------------------------------------------------------------------------
# baseball sanity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["4", "-1", "abc"])
def test_normalize_rejects_invalid_balls(value):
    with pytest.raises(StatcastNormalizationError):
        _normalize(balls=value)


@pytest.mark.parametrize("value", ["3", "-1", "abc"])
def test_normalize_rejects_invalid_strikes(value):
    with pytest.raises(StatcastNormalizationError):
        _normalize(strikes=value)


@pytest.mark.parametrize("value", ["3", "-1", "abc"])
def test_normalize_rejects_invalid_outs(value):
    with pytest.raises(StatcastNormalizationError):
        _normalize(outs_when_up=value)


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_normalize_rejects_invalid_inning(value):
    with pytest.raises(StatcastNormalizationError):
        _normalize(inning=value)


@pytest.mark.parametrize("column", ["game_pk", "batter", "pitcher"])
def test_normalize_rejects_malformed_ids(column):
    with pytest.raises(StatcastNormalizationError):
        _normalize(**{column: "not_a_number"})


@pytest.mark.parametrize("value", ["04/01/2024", "2024-13-40", "2024-04-32", "not-a-date"])
def test_normalize_rejects_malformed_game_date(value):
    with pytest.raises(StatcastNormalizationError):
        _normalize(game_date=value)


def test_normalize_rejects_non_dict_row():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_row(
            "not-a-dict",
            source_row_index=0,
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
        )


# ---------------------------------------------------------------------------
# snapshot-level normalization
# ---------------------------------------------------------------------------


def _rows(n):
    return [
        _valid_row(at_bat_number=str(i), pitch_number="1", **{})
        for i in range(1, n + 1)
    ]


def test_normalize_snapshot_valid_rows_returns_records():
    records = normalize_statcast_snapshot(
        _rows(3),
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    assert len(records) == 3


def test_normalize_snapshot_empty_rows_returns_empty_list():
    records = normalize_statcast_snapshot(
        [],
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    assert records == []


# ---------------------------------------------------------------------------
# snapshot-level argument validation applies even to rows=[]
# ---------------------------------------------------------------------------


def test_normalize_snapshot_empty_rows_rejects_invalid_snapshot_id():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            [],
            snapshot_id="",
            source_provider=SOURCE_PROVIDER,
            requested_date_range=DATE_RANGE,
        )


def test_normalize_snapshot_empty_rows_rejects_non_string_snapshot_id():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            [],
            snapshot_id=None,
            source_provider=SOURCE_PROVIDER,
            requested_date_range=DATE_RANGE,
        )


def test_normalize_snapshot_empty_rows_rejects_invalid_provider():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            [],
            snapshot_id=SNAPSHOT_ID,
            source_provider="",
            requested_date_range=DATE_RANGE,
        )


def test_normalize_snapshot_empty_rows_rejects_malformed_date():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            [],
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range={"start_date": "not-a-date", "end_date": "2024-04-01"},
        )


def test_normalize_snapshot_empty_rows_rejects_reversed_date_range():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            [],
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range={"start_date": "2024-04-05", "end_date": "2024-04-01"},
        )


def test_normalize_snapshot_empty_rows_rejects_malformed_date_range_shape():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            [],
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range={"start_date": "2024-04-01"},
        )


def test_normalize_snapshot_empty_rows_valid_arguments_still_return_empty_list():
    records = normalize_statcast_snapshot(
        [],
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    assert records == []


def test_normalize_snapshot_row_outside_requested_date_range_fails():
    rows = [_valid_row(game_date="2024-04-05")]
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            rows,
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range=DATE_RANGE,
        )


def test_normalize_snapshot_duplicate_rsb_pitch_id_fails():
    rows = [_valid_row(at_bat_number="1", pitch_number="1")] * 2
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            rows,
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range=DATE_RANGE,
        )


def test_normalize_snapshot_malformed_row_fails_entire_snapshot():
    rows = [
        _valid_row(at_bat_number="1", pitch_number="1"),
        _valid_row(at_bat_number="1", pitch_number="2", balls="9"),
        _valid_row(at_bat_number="1", pitch_number="3"),
    ]
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            rows,
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range=DATE_RANGE,
        )


def test_normalize_snapshot_ordering_stable_regardless_of_input_order():
    rows = [
        _valid_row(at_bat_number="2", pitch_number="1"),
        _valid_row(at_bat_number="1", pitch_number="2"),
        _valid_row(at_bat_number="1", pitch_number="1"),
    ]
    records = normalize_statcast_snapshot(
        rows,
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    ordering = [(r["at_bat_number"], r["pitch_number"]) for r in records]
    assert ordering == [(1, 1), (1, 2), (2, 1)]


def test_normalize_snapshot_rejects_non_list_rows():
    with pytest.raises(StatcastNormalizationError):
        normalize_statcast_snapshot(
            "not-a-list",
            snapshot_id=SNAPSHOT_ID,
            source_provider=SOURCE_PROVIDER,
            requested_date_range=DATE_RANGE,
        )


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------


def test_normalize_snapshot_deterministic_for_same_inputs():
    rows = [
        _valid_row(at_bat_number="1", pitch_number="1"),
        _valid_row(at_bat_number="1", pitch_number="2"),
    ]
    records_1 = normalize_statcast_snapshot(
        rows,
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    records_2 = normalize_statcast_snapshot(
        rows,
        snapshot_id=SNAPSHOT_ID,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    assert records_1 == records_2


def test_normalize_snapshot_different_snapshot_id_changes_rows():
    rows = [_valid_row(at_bat_number="1", pitch_number="1")]
    records_1 = normalize_statcast_snapshot(
        rows,
        snapshot_id="snap_a",
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    records_2 = normalize_statcast_snapshot(
        rows,
        snapshot_id="snap_b",
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    assert records_1 != records_2
    assert records_1[0]["rsb_pitch_id"] == records_2[0]["rsb_pitch_id"]


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_statcast_normalize_has_no_banned_imports():
    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "statcast_normalize.py"
    )
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
