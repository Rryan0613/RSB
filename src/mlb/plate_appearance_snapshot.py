import gzip
import hashlib
import json
import re
import zlib
from datetime import datetime, timezone

from paths import get_mlb_normalized_plate_appearance_dir, get_mlb_snapshot_dir

from .plate_appearance import PLATE_APPEARANCE_SCHEMA_VERSION, group_pitches_into_plate_appearances
from .plate_appearance_rates import attach_prior_outcome_rates
from .statcast_normalize import STATCAST_PITCH_SCHEMA_VERSION
from .statcast_snapshot import MANIFEST_FIELD_ORDER, SOURCE_PROVIDER, serialize_normalized_records


class PlateAppearanceSnapshotError(ValueError):
    pass


# Version of the grouping/rate-derivation algorithm itself, distinct from
# PLATE_APPEARANCE_SCHEMA_VERSION (the PA record shape). Mirrors v0.3.1's
# split between STATCAST_PITCH_SCHEMA_VERSION (statcast_normalize.py) and
# ADAPTER_VERSION (statcast_snapshot.py).
PLATE_APPEARANCE_DERIVATION_VERSION = "1"

# This dataset's denominators mean "completed PAs represented by the
# normalized pitch source," not an authoritative ledger of every official
# MLB plate appearance. See docs/MLB_PLATE_APPEARANCE_CONTRACT.md.
COVERAGE_BASIS = "normalized_pitch_represented_pa"

PA_MANIFEST_FIELD_ORDER = (
    "derived_dataset_id",
    "source_snapshot_id",
    "source_provider",
    "source_normalized_content_sha256",
    "pa_schema_version",
    "derivation_version",
    "coverage_basis",
    "input_pitch_row_count",
    "output_pa_count_completed",
    "output_pa_count_incomplete",
    "derived_content_sha256",
    "derived_row_count",
    "derived_at",
)

_REQUIRED_SOURCE_MANIFEST_FIELDS = frozenset(MANIFEST_FIELD_ORDER)
_MANIFEST_IMMUTABLE_FIELDS = tuple(
    field for field in PA_MANIFEST_FIELD_ORDER if field != "derived_at"
)
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _default_now_fn():
    return datetime.now(timezone.utc)


def _format_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise PlateAppearanceSnapshotError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_derived_dataset_id(
    source_normalized_content_sha256: str,
    pa_schema_version: str,
    derivation_version: str,
) -> str:
    """Deterministic, content-derived derived-artifact identity.

    Identical canonical inputs (source normalized content) and identical
    transformation versions (PA schema + derivation version) always
    reproduce the identical identity — unlike v0.3.1's snapshot_id, this is
    deliberately not salted by a creation timestamp, because a PA dataset is
    a pure function of an already-immutable normalized snapshot plus fixed
    derivation code, not a raw external ingestion event.
    """
    identity = f"{source_normalized_content_sha256}:{pa_schema_version}:{derivation_version}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def serialize_plate_appearance_records(records) -> bytes:
    lines = [
        json.dumps(record, ensure_ascii=True, separators=(",", ":"))
        for record in records
    ]
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def _validate_source_manifest(source_manifest) -> None:
    if not isinstance(source_manifest, dict):
        raise PlateAppearanceSnapshotError(
            f"source_manifest must be a dict, got {type(source_manifest).__name__!r}"
        )
    actual_keys = set(source_manifest)
    missing = _REQUIRED_SOURCE_MANIFEST_FIELDS - actual_keys
    extra = actual_keys - _REQUIRED_SOURCE_MANIFEST_FIELDS
    if missing or extra:
        raise PlateAppearanceSnapshotError(
            f"source_manifest does not match the v0.3.1 manifest contract; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    snapshot_id = source_manifest["snapshot_id"]
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise PlateAppearanceSnapshotError(
            "source_manifest snapshot_id must be a non-empty string"
        )

    if source_manifest["source_provider"] != SOURCE_PROVIDER:
        raise PlateAppearanceSnapshotError(
            f"source_manifest source_provider must be {SOURCE_PROVIDER!r}, got "
            f"{source_manifest['source_provider']!r}"
        )

    if source_manifest["normalized_schema_version"] != STATCAST_PITCH_SCHEMA_VERSION:
        raise PlateAppearanceSnapshotError(
            f"source_manifest normalized_schema_version must be "
            f"{STATCAST_PITCH_SCHEMA_VERSION!r}, got "
            f"{source_manifest['normalized_schema_version']!r}"
        )

    row_count = source_manifest["normalized_row_count"]
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
        raise PlateAppearanceSnapshotError(
            f"source_manifest normalized_row_count must be a non-negative int, got "
            f"{row_count!r}"
        )

    content_sha256 = source_manifest["normalized_content_sha256"]
    if not isinstance(content_sha256, str) or not _SHA256_HEX_PATTERN.match(content_sha256):
        raise PlateAppearanceSnapshotError(
            "source_manifest normalized_content_sha256 must be a 64-character "
            f"lowercase hex SHA-256 string, got {content_sha256!r}"
        )


def _load_existing_manifest(manifest_path) -> dict:
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlateAppearanceSnapshotError(
            f"could not read existing manifest at {manifest_path}: {exc}"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlateAppearanceSnapshotError(
            f"existing manifest at {manifest_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict) or set(data) != set(PA_MANIFEST_FIELD_ORDER):
        raise PlateAppearanceSnapshotError(
            f"existing manifest at {manifest_path} does not match the PA manifest "
            "contract shape"
        )
    return data


def _load_existing_pa_bytes(pa_path) -> bytes:
    try:
        compressed = pa_path.read_bytes()
    except OSError as exc:
        raise PlateAppearanceSnapshotError(
            f"could not read existing PA artifact at {pa_path}: {exc}"
        ) from exc
    try:
        return gzip.decompress(compressed)
    except (OSError, EOFError, zlib.error) as exc:
        raise PlateAppearanceSnapshotError(
            f"existing PA artifact at {pa_path} is not valid gzip: {exc}"
        ) from exc


def _validate_existing_artifact(manifest_path, pa_path, fresh_manifest, serialized) -> dict:
    """Treat an existing manifest+artifact pair as an idempotent no-op only if
    every immutable field and every content byte agrees with the freshly
    computed derivation. derived_at is exempt — it is creation-time metadata,
    never regenerated on an idempotent re-run.
    """
    existing_manifest = _load_existing_manifest(manifest_path)
    for field in _MANIFEST_IMMUTABLE_FIELDS:
        if existing_manifest[field] != fresh_manifest[field]:
            raise PlateAppearanceSnapshotError(
                f"derived dataset {fresh_manifest['derived_dataset_id']!r} already "
                f"exists with a different {field!r} "
                f"({existing_manifest[field]!r} != {fresh_manifest[field]!r}); this "
                "indicates a derivation-version/content mismatch bug"
            )

    existing_bytes = _load_existing_pa_bytes(pa_path)
    if existing_bytes != serialized:
        raise PlateAppearanceSnapshotError(
            f"derived dataset {fresh_manifest['derived_dataset_id']!r} already exists "
            "with different PA artifact bytes despite matching manifest metadata; "
            "this indicates a derivation-version/content mismatch bug"
        )

    return existing_manifest


def create_plate_appearance_dataset(
    source_manifest,
    normalized_pitch_records,
    *,
    now_fn=None,
) -> dict:
    """Derive and persist an immutable, content-addressed PA/rate dataset.

    Validates that `normalized_pitch_records` is exactly the set of records
    described by `source_manifest` (a v0.3.1 statcast_snapshot manifest) —
    matching row count, recomputed normalized_content_sha256, and per-record
    snapshot_id/source_provider/normalized_schema_version — before deriving
    anything. Any mismatch fails closed. This version persists a derived
    artifact from exactly one source normalized snapshot; multi-snapshot
    merge/reconciliation remains out of scope.
    """
    _validate_source_manifest(source_manifest)

    if not isinstance(normalized_pitch_records, (list, tuple)):
        raise PlateAppearanceSnapshotError(
            f"normalized_pitch_records must be a list or tuple, got "
            f"{type(normalized_pitch_records).__name__!r}"
        )

    if len(normalized_pitch_records) != source_manifest["normalized_row_count"]:
        raise PlateAppearanceSnapshotError(
            f"normalized_pitch_records length {len(normalized_pitch_records)} does not "
            f"match source_manifest normalized_row_count "
            f"{source_manifest['normalized_row_count']}"
        )

    # Field-level provenance checks run before the canonical content-hash
    # comparison so a single mutated provenance field is diagnosed by its own
    # specific error rather than being masked by the whole-content hash
    # mismatch that would also, incidentally, be true.
    for index, record in enumerate(normalized_pitch_records):
        if record.get("snapshot_id") != source_manifest["snapshot_id"]:
            raise PlateAppearanceSnapshotError(
                f"record {index} snapshot_id does not match source_manifest snapshot_id"
            )
        if record.get("source_provider") != source_manifest["source_provider"]:
            raise PlateAppearanceSnapshotError(
                f"record {index} source_provider does not match source_manifest source_provider"
            )
        if record.get("normalized_schema_version") != source_manifest["normalized_schema_version"]:
            raise PlateAppearanceSnapshotError(
                f"record {index} normalized_schema_version does not match "
                f"source_manifest normalized_schema_version"
            )

    recomputed_bytes = serialize_normalized_records(normalized_pitch_records)
    recomputed_sha256 = _sha256_hex(recomputed_bytes)
    if recomputed_sha256 != source_manifest["normalized_content_sha256"]:
        raise PlateAppearanceSnapshotError(
            "recomputed normalized_content_sha256 does not match source_manifest; "
            "normalized_pitch_records do not match the declared source snapshot"
        )

    pa_records = group_pitches_into_plate_appearances(normalized_pitch_records)
    enriched_records = attach_prior_outcome_rates(pa_records)

    serialized = serialize_plate_appearance_records(enriched_records)
    derived_content_sha256 = _sha256_hex(serialized)

    derived_dataset_id = build_derived_dataset_id(
        source_manifest["normalized_content_sha256"],
        PLATE_APPEARANCE_SCHEMA_VERSION,
        PLATE_APPEARANCE_DERIVATION_VERSION,
    )

    clock = now_fn or _default_now_fn
    derived_at = _format_utc_iso(clock())

    output_completed = sum(1 for r in pa_records if r["pa_status"] == "completed")
    output_incomplete = sum(1 for r in pa_records if r["pa_status"] == "incomplete")

    manifest = {
        "derived_dataset_id": derived_dataset_id,
        "source_snapshot_id": source_manifest["snapshot_id"],
        "source_provider": source_manifest["source_provider"],
        "source_normalized_content_sha256": source_manifest["normalized_content_sha256"],
        "pa_schema_version": PLATE_APPEARANCE_SCHEMA_VERSION,
        "derivation_version": PLATE_APPEARANCE_DERIVATION_VERSION,
        "coverage_basis": COVERAGE_BASIS,
        "input_pitch_row_count": len(normalized_pitch_records),
        "output_pa_count_completed": output_completed,
        "output_pa_count_incomplete": output_incomplete,
        "derived_content_sha256": derived_content_sha256,
        "derived_row_count": len(enriched_records),
        "derived_at": derived_at,
    }
    manifest = {field: manifest[field] for field in PA_MANIFEST_FIELD_ORDER}

    pa_path = get_mlb_normalized_plate_appearance_dir() / f"{derived_dataset_id}.jsonl.gz"
    manifest_path = get_mlb_snapshot_dir() / f"{derived_dataset_id}.pa_manifest.json"

    manifest_exists = manifest_path.exists()
    pa_exists = pa_path.exists()

    if manifest_exists != pa_exists:
        raise PlateAppearanceSnapshotError(
            f"derived dataset {derived_dataset_id!r} has an orphaned artifact "
            f"(manifest_exists={manifest_exists}, pa_data_exists={pa_exists}); "
            "refusing to overwrite or repair automatically"
        )

    if manifest_exists and pa_exists:
        return _validate_existing_artifact(manifest_path, pa_path, manifest, serialized)

    pa_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    pa_path.write_bytes(gzip.compress(serialized, compresslevel=9, mtime=0))
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return manifest
