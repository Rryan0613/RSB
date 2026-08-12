import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mlb.plate_appearance import PLATE_APPEARANCE_SCHEMA_VERSION
from mlb.plate_appearance_snapshot import (
    COVERAGE_BASIS,
    PA_MANIFEST_FIELD_ORDER,
    PLATE_APPEARANCE_DERIVATION_VERSION,
    PlateAppearanceSnapshotError,
    build_derived_dataset_id,
    create_plate_appearance_dataset,
    serialize_plate_appearance_records,
)
from mlb.statcast_normalize import STATCAST_PITCH_SCHEMA_VERSION, normalize_statcast_snapshot
from mlb.statcast_snapshot import SOURCE_PROVIDER, create_statcast_snapshot

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "mlb" / "statcast_sample.csv"
)
DECLARED_QUERY = {"team": "NYY"}
DATE_RANGE = {"start_date": "2024-04-01", "end_date": "2024-04-01"}


def _fixed_now(fixed):
    def now_fn():
        return fixed

    return now_fn


def _read_fixture_rows():
    with FIXTURE_PATH.open(newline="", encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


def _pa_paths(tmp_path, derived_dataset_id):
    return (
        tmp_path / "normalized" / "plate_appearances" / f"{derived_dataset_id}.jsonl.gz",
        tmp_path / "snapshots" / f"{derived_dataset_id}.pa_manifest.json",
    )


def _create_source(tmp_path, monkeypatch, *, when=None):
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path))
    now_fn = _fixed_now(when or datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc))
    manifest = create_statcast_snapshot(
        FIXTURE_PATH,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=now_fn,
    )
    records = normalize_statcast_snapshot(
        _read_fixture_rows(),
        snapshot_id=manifest["snapshot_id"],
        source_provider=manifest["source_provider"],
        requested_date_range=DATE_RANGE,
    )
    return manifest, records


def _create_pa_dataset(tmp_path, monkeypatch, *, source_when=None, pa_when=None):
    manifest, records = _create_source(tmp_path, monkeypatch, when=source_when)
    now_fn = _fixed_now(pa_when or datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    pa_manifest = create_plate_appearance_dataset(manifest, records, now_fn=now_fn)
    return manifest, records, pa_manifest


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


def test_returns_manifest_with_canonical_keys(tmp_path, monkeypatch):
    _, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    assert list(pa_manifest.keys()) == list(PA_MANIFEST_FIELD_ORDER)


def test_writes_both_artifacts(tmp_path, monkeypatch):
    _, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    pa_path, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    assert pa_path.exists()
    assert manifest_path.exists()


def test_pa_counts_from_fixture(tmp_path, monkeypatch):
    # fixture: at_bat 1 (3 pitches, terminal field_out) is completed;
    # at_bat 2 (1 pitch, no terminal event) is incomplete.
    _, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    assert pa_manifest["output_pa_count_completed"] == 1
    assert pa_manifest["output_pa_count_incomplete"] == 1
    assert pa_manifest["input_pitch_row_count"] == 4
    assert pa_manifest["derived_row_count"] == 2


def test_coverage_basis_stamped(tmp_path, monkeypatch):
    _, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    assert pa_manifest["coverage_basis"] == COVERAGE_BASIS


def test_pa_schema_and_derivation_version_stamped(tmp_path, monkeypatch):
    _, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    assert pa_manifest["pa_schema_version"] == PLATE_APPEARANCE_SCHEMA_VERSION
    assert pa_manifest["derivation_version"] == PLATE_APPEARANCE_DERIVATION_VERSION


def test_source_provenance_carried_from_source_manifest(tmp_path, monkeypatch):
    source_manifest, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    assert pa_manifest["source_snapshot_id"] == source_manifest["snapshot_id"]
    assert pa_manifest["source_provider"] == source_manifest["source_provider"]
    assert (
        pa_manifest["source_normalized_content_sha256"]
        == source_manifest["normalized_content_sha256"]
    )


# ---------------------------------------------------------------------------
# deterministic, content-derived identity
# ---------------------------------------------------------------------------


def test_derived_dataset_id_matches_build_function(tmp_path, monkeypatch):
    source_manifest, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    expected = build_derived_dataset_id(
        source_manifest["normalized_content_sha256"],
        PLATE_APPEARANCE_SCHEMA_VERSION,
        PLATE_APPEARANCE_DERIVATION_VERSION,
    )
    assert pa_manifest["derived_dataset_id"] == expected


def test_identical_inputs_reproduce_identical_id_regardless_of_creation_time(
    tmp_path, monkeypatch
):
    manifest, records = _create_source(tmp_path, monkeypatch)
    id_1 = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )["derived_dataset_id"]
    id_2 = build_derived_dataset_id(
        manifest["normalized_content_sha256"],
        PLATE_APPEARANCE_SCHEMA_VERSION,
        PLATE_APPEARANCE_DERIVATION_VERSION,
    )
    assert id_1 == id_2


def test_build_derived_dataset_id_deterministic():
    id_1 = build_derived_dataset_id("a" * 64, "1", "1")
    id_2 = build_derived_dataset_id("a" * 64, "1", "1")
    assert id_1 == id_2


def test_build_derived_dataset_id_differs_for_different_source_content():
    id_1 = build_derived_dataset_id("a" * 64, "1", "1")
    id_2 = build_derived_dataset_id("b" * 64, "1", "1")
    assert id_1 != id_2


def test_build_derived_dataset_id_differs_for_different_derivation_version():
    id_1 = build_derived_dataset_id("a" * 64, "1", "1")
    id_2 = build_derived_dataset_id("a" * 64, "1", "2")
    assert id_1 != id_2


# ---------------------------------------------------------------------------
# idempotence / immutability
# ---------------------------------------------------------------------------


def test_rerunning_identical_derivation_is_idempotent_no_op(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    first = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    second = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 14, 0, 0, tzinfo=timezone.utc))
    )
    assert first == second
    assert second["derived_at"] == first["derived_at"]  # unchanged: no-op returns existing manifest


def test_existing_artifact_with_different_content_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    _, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    on_disk["derived_content_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(on_disk), encoding="utf-8")

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )


def test_orphan_pa_artifact_with_missing_manifest_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    pa_path, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    assert pa_path.exists() and manifest_path.exists()
    manifest_path.unlink()

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )
    # refuses to overwrite/repair: the orphaned PA artifact is left untouched
    assert not manifest_path.exists()


def test_orphan_manifest_with_missing_pa_artifact_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    pa_path, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    assert pa_path.exists() and manifest_path.exists()
    pa_path.unlink()

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )
    assert not pa_path.exists()


def test_existing_manifest_with_tampered_provenance_metadata_fails_closed(tmp_path, monkeypatch):
    # Data bytes are untouched, but an immutable metadata field (not
    # derived_at) has been tampered with — must still fail closed rather
    # than accepting a stale/wrong provenance claim as an idempotent match.
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    _, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    on_disk["source_snapshot_id"] = "some_other_snapshot_id"
    manifest_path.write_text(json.dumps(on_disk), encoding="utf-8")

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )


def test_existing_manifest_with_tampered_coverage_basis_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    _, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    on_disk["coverage_basis"] = "something_else"
    manifest_path.write_text(json.dumps(on_disk), encoding="utf-8")

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )


def test_existing_manifest_with_invalid_shape_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    _, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    manifest_path.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )


def test_existing_manifest_with_malformed_json_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    _, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    manifest_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )


def test_existing_pa_artifact_with_malformed_gzip_fails_closed(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    pa_path, _ = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    pa_path.write_bytes(b"not a valid gzip stream")

    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(
            manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc))
        )


def test_normal_identical_rerun_still_succeeds_as_idempotent_no_op(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    first = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    second = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 20, 0, 0, tzinfo=timezone.utc))
    )
    third = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 12, 9, 0, 0, tzinfo=timezone.utc))
    )
    assert first == second == third


# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------


def test_pa_gzip_round_trips_to_expected_bytes(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    pa_manifest = create_plate_appearance_dataset(
        manifest, records, now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    pa_path, _ = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    on_disk = gzip.decompress(pa_path.read_bytes())
    import hashlib

    assert hashlib.sha256(on_disk).hexdigest() == pa_manifest["derived_content_sha256"]


def test_manifest_written_correctly(tmp_path, monkeypatch):
    _, _, pa_manifest = _create_pa_dataset(tmp_path, monkeypatch)
    _, manifest_path = _pa_paths(tmp_path, pa_manifest["derived_dataset_id"])
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == pa_manifest


# ---------------------------------------------------------------------------
# strict single-snapshot provenance validation
# ---------------------------------------------------------------------------


def test_rejects_row_count_mismatch(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(manifest, list(records) + [dict(records[0])])


def test_rejects_content_hash_mismatch(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    mutated = list(records)
    mutated[0] = dict(mutated[0])
    mutated[0]["release_speed"] = 999.9
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(manifest, mutated)


def test_rejects_record_snapshot_id_mismatch(tmp_path, monkeypatch):
    # Field-level provenance checks run before the canonical content-hash
    # comparison (see create_plate_appearance_dataset), so this genuinely
    # exercises the per-record snapshot_id branch rather than being masked
    # by the hash check firing first.
    manifest, records = _create_source(tmp_path, monkeypatch)
    mutated = list(records)
    mutated[0] = dict(mutated[0])
    mutated[0]["snapshot_id"] = "some_other_snapshot"
    with pytest.raises(PlateAppearanceSnapshotError, match="snapshot_id"):
        create_plate_appearance_dataset(manifest, mutated)


def test_rejects_record_source_provider_mismatch(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    mutated = list(records)
    mutated[0] = dict(mutated[0])
    mutated[0]["source_provider"] = "some_other_provider"
    with pytest.raises(PlateAppearanceSnapshotError, match="source_provider"):
        create_plate_appearance_dataset(manifest, mutated)


def test_rejects_record_normalized_schema_version_mismatch(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    mutated = list(records)
    mutated[0] = dict(mutated[0])
    mutated[0]["normalized_schema_version"] = "999"
    with pytest.raises(PlateAppearanceSnapshotError, match="normalized_schema_version"):
        create_plate_appearance_dataset(manifest, mutated)


# ---------------------------------------------------------------------------
# strict v0.3.1 source manifest semantics
# ---------------------------------------------------------------------------


def test_rejects_empty_snapshot_id(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["snapshot_id"] = "   "
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_source_provider_not_equal_to_supported_provider(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["source_provider"] = "some_other_provider"
    assert broken["source_provider"] != SOURCE_PROVIDER
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_normalized_schema_version_not_equal_to_statcast_pitch_schema_version(
    tmp_path, monkeypatch
):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["normalized_schema_version"] = "999"
    assert broken["normalized_schema_version"] != STATCAST_PITCH_SCHEMA_VERSION
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_non_int_normalized_row_count(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["normalized_row_count"] = "4"
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_bool_normalized_row_count(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["normalized_row_count"] = True
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_negative_normalized_row_count(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["normalized_row_count"] = -1
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_malformed_normalized_content_sha256_wrong_length(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["normalized_content_sha256"] = "abc123"
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_malformed_normalized_content_sha256_uppercase(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["normalized_content_sha256"] = broken["normalized_content_sha256"].upper()
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_malformed_source_manifest_missing_keys(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    del broken["snapshot_id"]
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_malformed_source_manifest_extra_keys(tmp_path, monkeypatch):
    manifest, records = _create_source(tmp_path, monkeypatch)
    broken = dict(manifest)
    broken["unexpected_extra_field"] = "x"
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(broken, records)


def test_rejects_non_dict_source_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path))
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset("not-a-dict", [])


def test_rejects_non_list_normalized_pitch_records(tmp_path, monkeypatch):
    manifest, _ = _create_source(tmp_path, monkeypatch)
    with pytest.raises(PlateAppearanceSnapshotError):
        create_plate_appearance_dataset(manifest, "not-a-list")


# ---------------------------------------------------------------------------
# empty valid input
# ---------------------------------------------------------------------------


def test_empty_source_snapshot_produces_empty_pa_dataset(tmp_path, monkeypatch):
    from mlb.statcast_import import EXPECTED_SOURCE_COLUMNS

    header_only = tmp_path / "header_only.csv"
    header_only.write_text(",".join(sorted(EXPECTED_SOURCE_COLUMNS)) + "\n", encoding="utf-8")
    monkeypatch.setenv("RSB_MLB_DATA_DIR", str(tmp_path / "mlb_data"))
    manifest = create_statcast_snapshot(
        header_only,
        declared_query=DECLARED_QUERY,
        requested_date_range=DATE_RANGE,
        now_fn=_fixed_now(datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)),
    )
    pa_manifest = create_plate_appearance_dataset(
        manifest, [], now_fn=_fixed_now(datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc))
    )
    assert pa_manifest["output_pa_count_completed"] == 0
    assert pa_manifest["output_pa_count_incomplete"] == 0
    assert pa_manifest["derived_row_count"] == 0
    pa_path, _ = _pa_paths(tmp_path / "mlb_data", pa_manifest["derived_dataset_id"])
    assert gzip.decompress(pa_path.read_bytes()) == b""


# ---------------------------------------------------------------------------
# serialize_plate_appearance_records
# ---------------------------------------------------------------------------


def test_serialize_empty_list_returns_empty_bytes():
    assert serialize_plate_appearance_records([]) == b""


def test_serialize_one_json_object_per_line():
    result = serialize_plate_appearance_records([{"a": 1}, {"a": 2}])
    assert result.decode("utf-8").splitlines() == ['{"a":1}', '{"a":2}']


# ---------------------------------------------------------------------------
# architecture isolation
# ---------------------------------------------------------------------------


def test_plate_appearance_snapshot_has_no_banned_imports():
    import ast

    src = Path(__file__).resolve().parents[1] / "src" / "mlb" / "plate_appearance_snapshot.py"
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
