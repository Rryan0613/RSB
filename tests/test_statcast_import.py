import csv
import io
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mlb.statcast_import import (
    EXPECTED_SOURCE_COLUMNS,
    REQUIRED_SOURCE_COLUMNS,
    StatcastExport,
    StatcastImportError,
    load_statcast_export,
)
from mlb.statcast_normalize import normalize_statcast_row

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "mlb" / "statcast_sample.csv"
)

DECLARED_QUERY = {
    "game_type": ["R"],
    "game_date_gt": "2024-04-01",
    "game_date_lt": "2024-04-01",
    "team": "NYY",
}
DATE_RANGE = {"start_date": "2024-04-01", "end_date": "2024-04-01"}


def _fixed_now(fixed):
    def now_fn():
        return fixed

    return now_fn


def _counting_now(values):
    it = iter(values)

    def now_fn():
        return next(it)

    return now_fn


def _write_csv(tmp_path, header, rows, name="custom.csv"):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path = tmp_path / name
    path.write_text(buf.getvalue(), encoding="utf-8")
    return path


def _minimal_row():
    return {col: "" for col in EXPECTED_SOURCE_COLUMNS}


def _valid_full_row():
    return {
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
        "launch_angle": "88.8",
        "hit_distance": "310.0",
    }


# ---------------------------------------------------------------------------
# valid CSV
# ---------------------------------------------------------------------------


def test_load_valid_fixture_returns_statcast_export():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert isinstance(export, StatcastExport)
    assert len(export.rows) == 4


def test_load_valid_fixture_preserves_raw_bytes_exactly():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.raw_bytes == FIXTURE_PATH.read_bytes()


def test_load_valid_fixture_header_includes_unmapped_columns():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert "release_spin_rate" in export.header
    assert "player_name" in export.header
    assert EXPECTED_SOURCE_COLUMNS.issubset(set(export.header))


def test_load_valid_fixture_rows_are_plain_dicts_in_source_order():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert [row["pitch_number"] for row in export.rows] == ["1", "2", "3", "1"]


def test_load_valid_fixture_declared_query_preserved():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.declared_query == DECLARED_QUERY


def test_load_valid_fixture_requested_date_range_preserved():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.requested_date_range == DATE_RANGE


def test_load_valid_fixture_source_downloaded_at_defaults_to_none():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.source_downloaded_at is None


def test_load_valid_fixture_source_downloaded_at_preserved_when_supplied():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        source_downloaded_at="2024-04-02T08:00:00Z",
    )
    assert export.source_downloaded_at == "2024-04-02T08:00:00.000000Z"


def test_load_uses_now_fn_for_ingestion_timestamps():
    fixed = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=_fixed_now(fixed),
    )
    assert export.ingestion_started_at == "2026-08-11T12:00:00.000000Z"
    assert export.ingestion_completed_at == "2026-08-11T12:00:00.000000Z"


def test_load_ingestion_timestamp_has_microsecond_precision():
    fixed = datetime(2026, 8, 11, 12, 0, 0, 123456, tzinfo=timezone.utc)
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=_fixed_now(fixed),
    )
    assert export.ingestion_started_at == "2026-08-11T12:00:00.123456Z"


def test_load_now_fn_called_separately_for_start_and_completion():
    start = datetime(2026, 8, 11, 12, 0, 0, 123456, tzinfo=timezone.utc)
    end = datetime(2026, 8, 11, 12, 0, 0, 654321, tzinfo=timezone.utc)
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=_counting_now([start, end]),
    )
    assert export.ingestion_started_at == "2026-08-11T12:00:00.123456Z"
    assert export.ingestion_completed_at == "2026-08-11T12:00:00.654321Z"


def test_load_now_fn_naive_datetime_rejected():
    naive = datetime(2026, 8, 11, 12, 0, 0)
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            FIXTURE_PATH,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
            now_fn=_fixed_now(naive),
        )


def test_load_does_not_invent_source_downloaded_at():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.source_downloaded_at is None
    assert export.source_downloaded_at != export.ingestion_started_at


# ---------------------------------------------------------------------------
# empty valid export
# ---------------------------------------------------------------------------


def test_load_header_only_csv_is_valid_with_zero_rows(tmp_path):
    path = _write_csv(tmp_path, sorted(EXPECTED_SOURCE_COLUMNS), [])
    export = load_statcast_export(
        path,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.rows == ()


# ---------------------------------------------------------------------------
# nonexistent / invalid file
# ---------------------------------------------------------------------------


def test_load_nonexistent_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            missing,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


def test_load_directory_path_raises(tmp_path):
    directory = tmp_path / "a_directory"
    directory.mkdir()
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            directory,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
def test_load_unreadable_file_raises(tmp_path):
    path = _write_csv(tmp_path, sorted(EXPECTED_SOURCE_COLUMNS), [])
    path.chmod(0o000)
    try:
        with pytest.raises(StatcastImportError):
            load_statcast_export(
                path,
                declared_query=DECLARED_QUERY,
                requested_date_range=DATE_RANGE,
            )
    finally:
        path.chmod(0o644)


def test_load_empty_file_with_no_header_raises(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            path,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


def test_load_non_utf8_file_raises(tmp_path):
    path = tmp_path / "bad_encoding.csv"
    path.write_bytes(b"game_pk\n\xff\xfe\x00\x01")
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            path,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


# ---------------------------------------------------------------------------
# required vs optional CSV header columns
#
# REQUIRED_SOURCE_COLUMNS backs statcast_normalize.REQUIRED_NORMALIZED_FIELDS
# and must be present in the header. EXPECTED_SOURCE_COLUMNS - REQUIRED_
# SOURCE_COLUMNS backs provider-nullable normalized fields and may be
# entirely absent from the header; a missing optional column behaves the
# same as a present-but-blank cell (normalizes to None downstream).
# ---------------------------------------------------------------------------


def test_required_and_optional_source_columns_partition_all_mapped_columns():
    assert REQUIRED_SOURCE_COLUMNS.issubset(EXPECTED_SOURCE_COLUMNS)
    assert "game_pk" in REQUIRED_SOURCE_COLUMNS
    assert "launch_angle" in EXPECTED_SOURCE_COLUMNS - REQUIRED_SOURCE_COLUMNS


def test_load_missing_required_header_column_raises(tmp_path):
    header = sorted(EXPECTED_SOURCE_COLUMNS - {"game_pk"})
    path = _write_csv(tmp_path, header, [])
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            path,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


def test_load_missing_required_header_column_error_names_the_column(tmp_path):
    header = sorted(EXPECTED_SOURCE_COLUMNS - {"at_bat_number"})
    path = _write_csv(tmp_path, header, [])
    with pytest.raises(StatcastImportError, match="at_bat_number"):
        load_statcast_export(
            path,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


@pytest.mark.parametrize(
    "optional_column",
    ["launch_angle", "hit_distance", "pitch_name", "sv_id", "zone", "on_1b"],
)
def test_load_missing_optional_header_column_succeeds(tmp_path, optional_column):
    header = sorted(EXPECTED_SOURCE_COLUMNS - {optional_column})
    row = {k: v for k, v in _valid_full_row().items() if k in header}
    path = _write_csv(tmp_path, header, [row])
    export = load_statcast_export(
        path,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert len(export.rows) == 1
    assert optional_column not in export.rows[0]


def test_missing_optional_header_column_normalizes_to_none(tmp_path):
    header = sorted(EXPECTED_SOURCE_COLUMNS - {"launch_angle"})
    row = {k: v for k, v in _valid_full_row().items() if k in header}
    path = _write_csv(tmp_path, header, [row])
    export = load_statcast_export(
        path,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    record = normalize_statcast_row(
        export.rows[0],
        source_row_index=0,
        snapshot_id="snap_test",
        source_provider="baseball_savant",
    )
    assert record["launch_angle"] is None
    # Confirms the None comes from the column being entirely absent, not from
    # a blank value: _valid_full_row() supplies a real launch_angle string.
    assert _valid_full_row()["launch_angle"] == "88.8"


def test_multiple_missing_optional_header_columns_all_normalize_to_none(tmp_path):
    missing = {"launch_angle", "hit_distance", "pitch_name", "sv_id"}
    header = sorted(EXPECTED_SOURCE_COLUMNS - missing)
    row = {k: v for k, v in _valid_full_row().items() if k in header}
    path = _write_csv(tmp_path, header, [row])
    export = load_statcast_export(
        path,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    record = normalize_statcast_row(
        export.rows[0],
        source_row_index=0,
        snapshot_id="snap_test",
        source_provider="baseball_savant",
    )
    assert record["launch_angle"] is None
    assert record["hit_distance"] is None
    assert record["pitch_name"] is None
    assert record["source_play_id"] is None
    # Fields whose header columns are still present are unaffected.
    assert record["batter_id"] == "600001"
    assert record["game_type"] == "R"


def test_missing_all_optional_header_columns_still_succeeds(tmp_path):
    header = sorted(REQUIRED_SOURCE_COLUMNS)
    row = {k: v for k, v in _valid_full_row().items() if k in header}
    path = _write_csv(tmp_path, header, [row])
    export = load_statcast_export(
        path,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    record = normalize_statcast_row(
        export.rows[0],
        source_row_index=0,
        snapshot_id="snap_test",
        source_provider="baseball_savant",
    )
    all_nullable_normalized_fields = [
        "source_play_id",
        "home_score",
        "away_score",
        "on_1b",
        "on_2b",
        "on_3b",
        "pitch_type",
        "pitch_name",
        "release_speed",
        "zone",
        "pitch_result_type",
        "pa_event_raw",
        "bb_type",
        "launch_speed",
        "launch_angle",
        "hit_distance",
    ]
    for normalized_field in all_nullable_normalized_fields:
        assert record[normalized_field] is None
    # Required fields still normalize correctly from the reduced header.
    assert record["batter_id"] == "600001"
    assert record["game_type"] == "R"


def test_load_header_with_extra_unmapped_columns_is_accepted(tmp_path):
    header = sorted(EXPECTED_SOURCE_COLUMNS) + ["some_future_statcast_column"]
    row = _minimal_row()
    row["some_future_statcast_column"] = "x"
    path = _write_csv(tmp_path, header, [row])
    export = load_statcast_export(
        path,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert len(export.rows) == 1


# ---------------------------------------------------------------------------
# declared_query validation (structured dict)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        None,
        42,
        "Statcast Search: 2024-04-01 to 2024-04-01, NYY vs BOS",
        ["query"],
        {1: "not a string key"},
        {"nested": {2: "not a string key"}},
        {"bad": object()},
        {"bad": {"nested": object()}},
        {"bad": float("nan")},
        {"bad": float("inf")},
    ],
)
def test_load_rejects_invalid_declared_query(value):
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            FIXTURE_PATH,
            declared_query=value,
            requested_date_range=DATE_RANGE,
        )


def test_load_declared_query_accepts_structured_dict():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
    )
    assert export.declared_query == DECLARED_QUERY


def test_load_declared_query_empty_dict_is_valid():
    # An empty declared_query means "no additional filters beyond
    # requested_date_range" — a legitimate, explicitly supported state.
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query={},
        requested_date_range=DATE_RANGE,
    )
    assert export.declared_query == {}


def test_load_declared_query_accepts_nested_structures():
    query = {"filters": {"game_type": ["R", "F"]}, "limit": 500, "verified": True}
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=query,
        requested_date_range=DATE_RANGE,
    )
    assert export.declared_query == query


def test_load_declared_query_is_isolated_from_caller_mutation():
    query = {"team": "NYY"}
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=query,
        requested_date_range=DATE_RANGE,
    )
    query["team"] = "MUTATED"
    assert export.declared_query == {"team": "NYY"}


# ---------------------------------------------------------------------------
# requested_date_range validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        None,
        "2024-04-01",
        {"start_date": "2024-04-01"},
        {"start_date": "2024-04-01", "end_date": "2024-04-01", "extra": "x"},
        {"start_date": "not-a-date", "end_date": "2024-04-01"},
        {"start_date": "2024-04-01", "end_date": "not-a-date"},
        {"start_date": "2024-04-05", "end_date": "2024-04-01"},
    ],
)
def test_load_rejects_invalid_requested_date_range(value):
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            FIXTURE_PATH,
            declared_query=DECLARED_QUERY,
            requested_date_range=value,
        )


def test_load_accepts_equal_start_and_end_date():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range={"start_date": "2024-04-01", "end_date": "2024-04-01"},
    )
    assert export.requested_date_range == {
        "start_date": "2024-04-01",
        "end_date": "2024-04-01",
    }


# ---------------------------------------------------------------------------
# source_downloaded_at validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [42, "", "   ", "not-a-datetime", "2024-04-02T08:00:00", "2024-04-02"],
)
def test_load_rejects_invalid_source_downloaded_at(value):
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            FIXTURE_PATH,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
            source_downloaded_at=value,
        )


def test_load_source_downloaded_at_naive_datetime_rejected():
    with pytest.raises(StatcastImportError):
        load_statcast_export(
            FIXTURE_PATH,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
            source_downloaded_at="2024-04-02T08:00:00",
        )


def test_load_source_downloaded_at_utc_z_accepted():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        source_downloaded_at="2024-04-02T08:00:00Z",
    )
    assert export.source_downloaded_at == "2024-04-02T08:00:00.000000Z"


def test_load_source_downloaded_at_non_utc_offset_normalized_to_utc():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        source_downloaded_at="2024-04-02T04:00:00-04:00",
    )
    assert export.source_downloaded_at == "2024-04-02T08:00:00.000000Z"


def test_load_source_downloaded_at_none_still_accepted():
    export = load_statcast_export(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        source_downloaded_at=None,
    )
    assert export.source_downloaded_at is None


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_statcast_import_has_no_banned_imports():
    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "statcast_import.py"
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
