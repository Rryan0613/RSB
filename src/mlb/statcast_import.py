import copy
import csv
import io
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .statcast_normalize import REQUIRED_NORMALIZED_FIELDS, SOURCE_FIELD_MAPPING


class StatcastImportError(ValueError):
    pass


# All 33 provider CSV columns the adapter recognizes and maps into the
# normalized pitch contract. A Baseball Savant Statcast Search export
# carries many more columns than this; unmapped columns are allowed and
# preserved only in the raw snapshot layer. This is NOT the set of columns
# required to be present in the header — see REQUIRED_SOURCE_COLUMNS below.
EXPECTED_SOURCE_COLUMNS = frozenset(SOURCE_FIELD_MAPPING.values())

# The subset of EXPECTED_SOURCE_COLUMNS backing a mandatory normalized field
# (statcast_normalize.REQUIRED_NORMALIZED_FIELDS). Only these must be present
# in the CSV header. A mapped column backing a provider-nullable normalized
# field may be entirely absent from the header; the corresponding row value
# is then treated as missing and normalizes to None, same as a present-but-
# blank cell.
REQUIRED_SOURCE_COLUMNS = frozenset(
    SOURCE_FIELD_MAPPING[field] for field in REQUIRED_NORMALIZED_FIELDS
)


@dataclass(frozen=True)
class StatcastExport:
    raw_bytes: bytes
    header: tuple
    rows: tuple
    declared_query: dict
    requested_date_range: dict
    source_downloaded_at: "str | None"
    ingestion_started_at: str
    ingestion_completed_at: str


def _default_now_fn():
    return datetime.now(timezone.utc)


def _format_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise StatcastImportError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _validate_json_serializable(value, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise StatcastImportError(
                    f"{path} keys must be strings, got {type(key).__name__!r} for key {key!r}"
                )
            _validate_json_serializable(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_serializable(item, f"{path}[{index}]")
        return
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            raise StatcastImportError(f"{path} must not be NaN or infinite")
        return
    raise StatcastImportError(
        f"{path} contains a non-JSON-serializable value of type {type(value).__name__!r}"
    )


def _validate_declared_query(value) -> dict:
    if not isinstance(value, dict):
        raise StatcastImportError(
            f"declared_query must be a dict, got {type(value).__name__!r}"
        )
    _validate_json_serializable(value, "declared_query")
    return copy.deepcopy(value)


def _validate_iso_date(value, name: str) -> str:
    if not isinstance(value, str):
        raise StatcastImportError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    try:
        datetime.strptime(stripped, "%Y-%m-%d")
    except ValueError as exc:
        raise StatcastImportError(f"{name} must be an ISO date (YYYY-MM-DD): {value!r}") from exc
    return stripped


def _validate_requested_date_range(value) -> dict:
    if not isinstance(value, dict):
        raise StatcastImportError(
            f"requested_date_range must be a dict, got {type(value).__name__!r}"
        )
    if set(value.keys()) != {"start_date", "end_date"}:
        raise StatcastImportError(
            "requested_date_range must have exactly keys 'start_date' and 'end_date', "
            f"got {sorted(value.keys())}"
        )
    start_date = _validate_iso_date(value["start_date"], "requested_date_range.start_date")
    end_date = _validate_iso_date(value["end_date"], "requested_date_range.end_date")
    if start_date > end_date:
        raise StatcastImportError(
            f"requested_date_range.start_date {start_date!r} must not be after "
            f"requested_date_range.end_date {end_date!r}"
        )
    return {"start_date": start_date, "end_date": end_date}


def _validate_source_downloaded_at(value) -> "str | None":
    if value is None:
        return None
    if not isinstance(value, str):
        raise StatcastImportError(
            f"source_downloaded_at must be a string or None, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise StatcastImportError("source_downloaded_at must not be empty or whitespace-only")
    parseable = stripped[:-1] + "+00:00" if stripped[-1:] in ("Z", "z") else stripped
    try:
        parsed = datetime.fromisoformat(parseable)
    except ValueError as exc:
        raise StatcastImportError(
            f"source_downloaded_at must be an ISO 8601 datetime string: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise StatcastImportError(
            f"source_downloaded_at must include an explicit UTC offset or 'Z': {value!r}"
        )
    return _format_utc_iso(parsed)


def load_statcast_export(
    path,
    *,
    declared_query,
    requested_date_range,
    source_downloaded_at=None,
    now_fn=None,
) -> StatcastExport:
    """Read an already-downloaded Baseball Savant CSV export from local disk.

    Performs no network access and no baseball-semantic normalization. Raw
    bytes and source row order are preserved exactly for downstream snapshot
    checksumming and normalization.
    """
    clock = now_fn or _default_now_fn

    validated_declared_query = _validate_declared_query(declared_query)
    validated_requested_date_range = _validate_requested_date_range(requested_date_range)
    validated_source_downloaded_at = _validate_source_downloaded_at(source_downloaded_at)

    resolved_path = Path(path)
    if not resolved_path.exists():
        raise StatcastImportError(f"file not found: {resolved_path}")
    if not resolved_path.is_file():
        raise StatcastImportError(f"not a file: {resolved_path}")

    ingestion_started_at = _format_utc_iso(clock())

    try:
        raw_bytes = resolved_path.read_bytes()
    except OSError as exc:
        raise StatcastImportError(f"could not read file {resolved_path}: {exc}") from exc

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StatcastImportError(f"file is not valid UTF-8: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames
    if not header:
        raise StatcastImportError("CSV file has no header row")

    missing_columns = REQUIRED_SOURCE_COLUMNS - set(header)
    if missing_columns:
        raise StatcastImportError(
            f"CSV header is missing required columns: {sorted(missing_columns)}"
        )

    try:
        rows = tuple(reader)
    except csv.Error as exc:
        raise StatcastImportError(f"CSV file could not be parsed: {exc}") from exc

    ingestion_completed_at = _format_utc_iso(clock())

    return StatcastExport(
        raw_bytes=raw_bytes,
        header=tuple(header),
        rows=rows,
        declared_query=validated_declared_query,
        requested_date_range=validated_requested_date_range,
        source_downloaded_at=validated_source_downloaded_at,
        ingestion_started_at=ingestion_started_at,
        ingestion_completed_at=ingestion_completed_at,
    )
