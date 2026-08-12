import gzip
import hashlib
import json

from paths import (
    get_mlb_normalized_statcast_pitch_dir,
    get_mlb_raw_statcast_dir,
    get_mlb_snapshot_dir,
)

from .statcast_import import load_statcast_export
from .statcast_normalize import STATCAST_PITCH_SCHEMA_VERSION, normalize_statcast_snapshot


class StatcastSnapshotError(ValueError):
    pass


SOURCE_PROVIDER = "baseball_savant"
RETRIEVAL_MECHANISM = "manual_csv_export"
SOURCE_IDENTIFIER = "Baseball Savant Statcast Search, manual export"
ADAPTER_VERSION = "1"

MANIFEST_FIELD_ORDER = (
    "snapshot_id",
    "source_provider",
    "retrieval_mechanism",
    "source_identifier",
    "declared_query",
    "requested_date_range",
    "source_downloaded_at",
    "ingestion_started_at",
    "ingestion_completed_at",
    "adapter_version",
    "normalized_schema_version",
    "raw_content_sha256",
    "normalized_content_sha256",
    "raw_row_count",
    "normalized_row_count",
)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_snapshot_id(ingestion_started_at: str, raw_content_sha256: str) -> str:
    """Content-and-ingestion-event-aware snapshot id.

    Identical raw bytes ingested at a different time yield a different
    snapshot_id (and therefore a different normalized checksum, since
    snapshot_id is embedded in every normalized row). This is intentional.
    """
    timestamp = ingestion_started_at.replace("-", "").replace(":", "").replace(".", "")
    return f"{timestamp}_{raw_content_sha256[:12]}"


def serialize_normalized_records(records) -> bytes:
    lines = [
        json.dumps(record, ensure_ascii=True, separators=(",", ":"))
        for record in records
    ]
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def create_statcast_snapshot(
    path,
    *,
    declared_query,
    requested_date_range,
    source_downloaded_at=None,
    now_fn=None,
) -> dict:
    """Import, normalize, and persist a raw/normalized/manifest Statcast snapshot.

    Reads only the local CSV export at `path`; performs no network access.
    Snapshots are immutable: if the computed snapshot_id already has
    artifacts on disk, this raises rather than overwriting them.

    source_provider is fixed to SOURCE_PROVIDER ("baseball_savant") — v0.3.1
    is a single-provider adapter/snapshot contract, not a multi-provider one,
    so the manifest and every normalized row always agree on source_provider
    by construction rather than by caller-supplied argument.
    """
    export = load_statcast_export(
        path,
        declared_query=declared_query,
        requested_date_range=requested_date_range,
        source_downloaded_at=source_downloaded_at,
        now_fn=now_fn,
    )

    raw_content_sha256 = _sha256_hex(export.raw_bytes)
    snapshot_id = build_snapshot_id(export.ingestion_started_at, raw_content_sha256)

    normalized_records = normalize_statcast_snapshot(
        export.rows,
        snapshot_id=snapshot_id,
        source_provider=SOURCE_PROVIDER,
        requested_date_range=export.requested_date_range,
    )
    normalized_bytes = serialize_normalized_records(normalized_records)
    normalized_content_sha256 = _sha256_hex(normalized_bytes)

    raw_path = get_mlb_raw_statcast_dir() / f"{snapshot_id}.csv.gz"
    normalized_path = get_mlb_normalized_statcast_pitch_dir() / f"{snapshot_id}.jsonl.gz"
    manifest_path = get_mlb_snapshot_dir() / f"{snapshot_id}.manifest.json"

    for existing in (raw_path, normalized_path, manifest_path):
        if existing.exists():
            raise StatcastSnapshotError(
                f"snapshot {snapshot_id!r} already has an artifact at {existing}; "
                "snapshots are immutable, re-ingest to create a new snapshot"
            )

    manifest = {
        "snapshot_id": snapshot_id,
        "source_provider": SOURCE_PROVIDER,
        "retrieval_mechanism": RETRIEVAL_MECHANISM,
        "source_identifier": SOURCE_IDENTIFIER,
        "declared_query": export.declared_query,
        "requested_date_range": export.requested_date_range,
        "source_downloaded_at": export.source_downloaded_at,
        "ingestion_started_at": export.ingestion_started_at,
        "ingestion_completed_at": export.ingestion_completed_at,
        "adapter_version": ADAPTER_VERSION,
        "normalized_schema_version": STATCAST_PITCH_SCHEMA_VERSION,
        "raw_content_sha256": raw_content_sha256,
        "normalized_content_sha256": normalized_content_sha256,
        "raw_row_count": len(export.rows),
        "normalized_row_count": len(normalized_records),
    }
    manifest = {field: manifest[field] for field in MANIFEST_FIELD_ORDER}

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    raw_path.write_bytes(gzip.compress(export.raw_bytes, compresslevel=9, mtime=0))
    normalized_path.write_bytes(gzip.compress(normalized_bytes, compresslevel=9, mtime=0))
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return manifest
