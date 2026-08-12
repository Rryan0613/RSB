import csv
import gzip
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mlb.statcast_import import EXPECTED_SOURCE_COLUMNS, StatcastImportError
from mlb.statcast_normalize import StatcastNormalizationError, normalize_statcast_snapshot
from mlb.statcast_snapshot import (
    MANIFEST_FIELD_ORDER,
    SOURCE_PROVIDER,
    StatcastSnapshotError,
    build_snapshot_id,
    create_statcast_snapshot,
    serialize_normalized_records,
)

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

SNAPSHOT_ID_PATTERN = re.compile(r"^\d{8}T\d{12}Z_[0-9a-f]{12}$")


def _fixed_now(fixed):
    def now_fn():
        return fixed

    return now_fn


def _paths_for(tmp_path, snapshot_id):
    return (
        tmp_path / "raw" / "statcast" / f"{snapshot_id}.csv.gz",
        tmp_path / "normalized" / "statcast_pitch" / f"{snapshot_id}.jsonl.gz",
        tmp_path / "snapshots" / f"{snapshot_id}.manifest.json",
    )


def _read_fixture_rows():
    with FIXTURE_PATH.open(newline="", encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


def _create(tmp_path, monkeypatch, *, when=None, **kwargs):
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path))
    now_fn = _fixed_now(when or datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc))
    return create_statcast_snapshot(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=now_fn,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


def test_create_snapshot_returns_manifest_with_canonical_keys(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert list(manifest.keys()) == list(MANIFEST_FIELD_ORDER)


def test_create_snapshot_writes_all_three_artifacts(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    raw_path, normalized_path, manifest_path = _paths_for(tmp_path, manifest["snapshot_id"])
    assert raw_path.exists()
    assert normalized_path.exists()
    assert manifest_path.exists()


def test_create_snapshot_id_matches_expected_shape(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert SNAPSHOT_ID_PATTERN.match(manifest["snapshot_id"])
    assert manifest["snapshot_id"].startswith("20260811T120000000000Z_")


def test_create_snapshot_retrieval_mechanism_is_manual_csv_export(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert manifest["retrieval_mechanism"] == "manual_csv_export"


def test_create_snapshot_source_provider_is_baseball_savant(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert manifest["source_provider"] == "baseball_savant"
    assert manifest["source_provider"] == SOURCE_PROVIDER


def test_create_snapshot_row_counts(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert manifest["raw_row_count"] == 4
    assert manifest["normalized_row_count"] == 4


def test_create_snapshot_source_downloaded_at_null_by_default(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert manifest["source_downloaded_at"] is None


def test_create_snapshot_source_downloaded_at_populated_when_supplied(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch, source_downloaded_at="2024-04-02T08:00:00Z")
    assert manifest["source_downloaded_at"] == "2024-04-02T08:00:00.000000Z"


def test_create_snapshot_declared_query_preserved_as_dict(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    assert manifest["declared_query"] == DECLARED_QUERY
    assert isinstance(manifest["declared_query"], dict)


# ---------------------------------------------------------------------------
# checksums
# ---------------------------------------------------------------------------


def test_raw_content_sha256_matches_original_uncompressed_bytes(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    expected = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert manifest["raw_content_sha256"] == expected


def test_normalized_content_sha256_matches_canonical_jsonl(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    records = normalize_statcast_snapshot(
        _read_fixture_rows(),
        snapshot_id=manifest["snapshot_id"],
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    expected_bytes = serialize_normalized_records(records)
    assert manifest["normalized_content_sha256"] == hashlib.sha256(expected_bytes).hexdigest()


# ---------------------------------------------------------------------------
# round-trip preservation
# ---------------------------------------------------------------------------


def test_raw_gzip_round_trips_to_exact_original_bytes(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    raw_path, _, _ = _paths_for(tmp_path, manifest["snapshot_id"])
    assert gzip.decompress(raw_path.read_bytes()) == FIXTURE_PATH.read_bytes()


def test_normalized_gzip_round_trips_to_canonical_jsonl_bytes(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    _, normalized_path, _ = _paths_for(tmp_path, manifest["snapshot_id"])
    records = normalize_statcast_snapshot(
        _read_fixture_rows(),
        snapshot_id=manifest["snapshot_id"],
        source_provider=SOURCE_PROVIDER,
        requested_date_range=DATE_RANGE,
    )
    expected_bytes = serialize_normalized_records(records)
    assert gzip.decompress(normalized_path.read_bytes()) == expected_bytes


def test_manifest_written_correctly(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    _, _, manifest_path = _paths_for(tmp_path, manifest["snapshot_id"])
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == manifest


# ---------------------------------------------------------------------------
# immutability
# ---------------------------------------------------------------------------


def test_existing_snapshot_not_silently_overwritten(tmp_path, monkeypatch):
    fixed = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)
    _create(tmp_path, monkeypatch, when=fixed)
    with pytest.raises(StatcastSnapshotError):
        _create(tmp_path, monkeypatch, when=fixed)


def test_overlapping_snapshots_may_coexist(tmp_path, monkeypatch):
    manifest_1 = _create(
        tmp_path, monkeypatch, when=datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)
    )
    manifest_2 = _create(
        tmp_path, monkeypatch, when=datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc)
    )
    assert manifest_1["snapshot_id"] != manifest_2["snapshot_id"]
    for snapshot_id in (manifest_1["snapshot_id"], manifest_2["snapshot_id"]):
        raw_path, normalized_path, manifest_path = _paths_for(tmp_path, snapshot_id)
        assert raw_path.exists() and normalized_path.exists() and manifest_path.exists()


def test_reingesting_identical_bytes_later_same_raw_hash_different_snapshot(tmp_path, monkeypatch):
    manifest_1 = _create(
        tmp_path, monkeypatch, when=datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)
    )
    manifest_2 = _create(
        tmp_path, monkeypatch, when=datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc)
    )
    assert manifest_1["raw_content_sha256"] == manifest_2["raw_content_sha256"]
    assert manifest_1["snapshot_id"] != manifest_2["snapshot_id"]
    assert manifest_1["normalized_content_sha256"] != manifest_2["normalized_content_sha256"]


def test_snapshot_id_differs_for_same_second_different_microseconds(tmp_path, monkeypatch):
    manifest_1 = _create(
        tmp_path,
        monkeypatch,
        when=datetime(2026, 8, 11, 12, 0, 0, 100000, tzinfo=timezone.utc),
    )
    manifest_2 = _create(
        tmp_path,
        monkeypatch,
        when=datetime(2026, 8, 11, 12, 0, 0, 900000, tzinfo=timezone.utc),
    )
    assert manifest_1["snapshot_id"] != manifest_2["snapshot_id"]
    assert manifest_1["ingestion_started_at"] == "2026-08-11T12:00:00.100000Z"
    assert manifest_2["ingestion_started_at"] == "2026-08-11T12:00:00.900000Z"


def test_snapshot_id_includes_microsecond_resolution_timestamp_component(tmp_path, monkeypatch):
    manifest = _create(
        tmp_path,
        monkeypatch,
        when=datetime(2026, 8, 11, 12, 0, 0, 123456, tzinfo=timezone.utc),
    )
    assert manifest["snapshot_id"].startswith("20260811T120000123456Z_")


def test_build_snapshot_id_deterministic_for_same_inputs():
    id_1 = build_snapshot_id("2026-08-11T12:00:00.123456Z", "a" * 64)
    id_2 = build_snapshot_id("2026-08-11T12:00:00.123456Z", "a" * 64)
    assert id_1 == id_2


def test_build_snapshot_id_differs_for_different_timestamps():
    id_1 = build_snapshot_id("2026-08-11T12:00:00.123456Z", "a" * 64)
    id_2 = build_snapshot_id("2026-08-11T13:00:00.123456Z", "a" * 64)
    assert id_1 != id_2


def test_build_snapshot_id_differs_for_different_microseconds():
    id_1 = build_snapshot_id("2026-08-11T12:00:00.100000Z", "a" * 64)
    id_2 = build_snapshot_id("2026-08-11T12:00:00.900000Z", "a" * 64)
    assert id_1 != id_2


# ---------------------------------------------------------------------------
# empty valid export
# ---------------------------------------------------------------------------


def test_create_snapshot_from_header_only_csv(tmp_path, monkeypatch):
    header_only = tmp_path / "header_only.csv"
    header_only.write_text(",".join(sorted(EXPECTED_SOURCE_COLUMNS)) + "\n", encoding="utf-8")
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path / "mlb_data"))
    manifest = create_statcast_snapshot(
        header_only,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=_fixed_now(datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)),
    )
    assert manifest["raw_row_count"] == 0
    assert manifest["normalized_row_count"] == 0
    _, normalized_path, _ = _paths_for(tmp_path / "mlb_data", manifest["snapshot_id"])
    assert gzip.decompress(normalized_path.read_bytes()) == b""


def test_create_snapshot_from_header_only_csv_carries_correct_provider(tmp_path, monkeypatch):
    header_only = tmp_path / "header_only.csv"
    header_only.write_text(",".join(sorted(EXPECTED_SOURCE_COLUMNS)) + "\n", encoding="utf-8")
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path / "mlb_data"))
    manifest = create_statcast_snapshot(
        header_only,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=_fixed_now(datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)),
    )
    assert manifest["source_provider"] == "baseball_savant"
    assert manifest["retrieval_mechanism"] == "manual_csv_export"


# ---------------------------------------------------------------------------
# provider consistency
# ---------------------------------------------------------------------------


def test_manifest_provider_matches_every_normalized_row_provider(tmp_path, monkeypatch):
    manifest = _create(tmp_path, monkeypatch)
    _, normalized_path, _ = _paths_for(tmp_path, manifest["snapshot_id"])
    lines = gzip.decompress(normalized_path.read_bytes()).decode("utf-8").splitlines()
    assert len(lines) == 4
    for line in lines:
        row = json.loads(line)
        assert row["source_provider"] == manifest["source_provider"]


def test_create_snapshot_does_not_accept_source_provider_override(tmp_path, monkeypatch):
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path))
    with pytest.raises(TypeError):
        create_statcast_snapshot(
            FIXTURE_PATH,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
            source_provider="some_other_provider",
        )


# ---------------------------------------------------------------------------
# error propagation
# ---------------------------------------------------------------------------


def test_create_snapshot_propagates_import_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path))
    with pytest.raises(StatcastImportError):
        create_statcast_snapshot(
            tmp_path / "does_not_exist.csv",
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


def test_create_snapshot_propagates_normalization_error_for_malformed_row(tmp_path, monkeypatch):
    header = sorted(EXPECTED_SOURCE_COLUMNS)
    row = {col: "" for col in header}
    row.update(
        {
            "game_pk": "700001",
            "game_date": "2024-04-01",
            "game_year": "2024",
            "at_bat_number": "1",
            "pitch_number": "1",
            "inning": "1",
            "inning_topbot": "Top",
            "game_type": "R",
            "home_team": "NYY",
            "away_team": "BOS",
            "batter": "600001",
            "pitcher": "700010",
            "stand": "R",
            "p_throws": "L",
            "balls": "9",
            "strikes": "0",
            "outs_when_up": "0",
        }
    )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header)
    writer.writeheader()
    writer.writerow(row)
    malformed_path = tmp_path / "malformed.csv"
    malformed_path.write_text(buf.getvalue(), encoding="utf-8")

    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path / "mlb_data"))
    with pytest.raises(StatcastNormalizationError):
        create_statcast_snapshot(
            malformed_path,
            declared_query=DECLARED_QUERY,
            requested_date_range=DATE_RANGE,
        )


def test_statcast_snapshot_error_is_value_error():
    assert issubclass(StatcastSnapshotError, ValueError)


# ---------------------------------------------------------------------------
# serialize_normalized_records
# ---------------------------------------------------------------------------


def test_serialize_normalized_records_empty_list_returns_empty_bytes():
    assert serialize_normalized_records([]) == b""


def test_serialize_normalized_records_one_json_object_per_line():
    records = [{"a": 1}, {"a": 2}]
    result = serialize_normalized_records(records)
    lines = result.decode("utf-8").splitlines()
    assert lines == ['{"a":1}', '{"a":2}']


def test_serialize_normalized_records_ends_with_newline():
    result = serialize_normalized_records([{"a": 1}])
    assert result.endswith(b"\n")


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_statcast_snapshot_has_no_banned_imports():
    import ast

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mlb"
        / "statcast_snapshot.py"
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
