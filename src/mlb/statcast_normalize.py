import hashlib
import math
from datetime import datetime


class StatcastNormalizationError(ValueError):
    pass


STATCAST_PITCH_SCHEMA_VERSION = "1"

# normalized_field -> source (Baseball Savant Statcast Search) column
SOURCE_FIELD_MAPPING = {
    "source_game_id": "game_pk",
    "source_play_id": "sv_id",
    "game_date": "game_date",
    "game_year": "game_year",
    "at_bat_number": "at_bat_number",
    "pitch_number": "pitch_number",
    "inning": "inning",
    "inning_half": "inning_topbot",
    "game_type": "game_type",
    "home_team": "home_team",
    "away_team": "away_team",
    "home_score": "home_score",
    "away_score": "away_score",
    "batter_id": "batter",
    "pitcher_id": "pitcher",
    "batter_stands": "stand",
    "pitcher_throws": "p_throws",
    "on_1b": "on_1b",
    "on_2b": "on_2b",
    "on_3b": "on_3b",
    "balls": "balls",
    "strikes": "strikes",
    "outs": "outs_when_up",
    "pitch_type": "pitch_type",
    "pitch_name": "pitch_name",
    "release_speed": "release_speed",
    "zone": "zone",
    "pitch_result_type": "type",
    "pa_event_raw": "events",
    "bb_type": "bb_type",
    "launch_speed": "launch_speed",
    "launch_angle": "launch_angle",
    "hit_distance": "hit_distance",
}

# Required identity/chronology/game-context/pre-pitch fields: missing or
# malformed values fail the whole snapshot (v0.3.1 is fail-closed).
REQUIRED_NORMALIZED_FIELDS = frozenset({
    "source_game_id",
    "game_date",
    "game_year",
    "at_bat_number",
    "pitch_number",
    "inning",
    "inning_half",
    "game_type",
    "home_team",
    "away_team",
    "batter_id",
    "pitcher_id",
    "batter_stands",
    "pitcher_throws",
    "balls",
    "strikes",
    "outs",
})

# Legitimately provider-nullable fields: absent/empty normalizes to None.
NULLABLE_NORMALIZED_FIELDS = frozenset({
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
})

assert REQUIRED_NORMALIZED_FIELDS | NULLABLE_NORMALIZED_FIELDS == frozenset(SOURCE_FIELD_MAPPING)

VALID_INNING_HALVES = frozenset({"top", "bottom"})
_INNING_HALF_ALIASES = {"top": "top", "bot": "bottom", "bottom": "bottom"}

VALID_BATTER_STANDS = frozenset({"L", "R"})
VALID_PITCHER_THROWS = frozenset({"L", "R"})
VALID_PITCH_RESULT_TYPES = frozenset({"B", "S", "X"})

NORMALIZED_PITCH_FIELD_ORDER = (
    "rsb_pitch_id",
    "source_game_id",
    "source_play_id",
    "game_date",
    "game_year",
    "at_bat_number",
    "pitch_number",
    "inning",
    "inning_half",
    "game_type",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "batter_id",
    "pitcher_id",
    "batter_stands",
    "pitcher_throws",
    "on_1b",
    "on_2b",
    "on_3b",
    "balls",
    "strikes",
    "outs",
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
    "snapshot_id",
    "source_provider",
    "normalized_schema_version",
    "source_row_index",
)


def _raw_is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _parse_required_digit_id(value, name: str) -> str:
    if _raw_is_blank(value):
        raise StatcastNormalizationError(f"{name} is required and must not be empty")
    if isinstance(value, bool):
        raise StatcastNormalizationError(f"{name} must not be a bool")
    text = str(value).strip()
    if not text.isdigit():
        raise StatcastNormalizationError(f"{name} must be a numeric id, got {value!r}")
    return text


def _parse_optional_digit_id(value, name: str) -> "str | None":
    if _raw_is_blank(value):
        return None
    if isinstance(value, bool):
        raise StatcastNormalizationError(f"{name} must not be a bool")
    text = str(value).strip()
    if not text.isdigit():
        raise StatcastNormalizationError(f"{name} must be a numeric id, got {value!r}")
    return text


def _parse_int(value, name: str, *, required: bool) -> "int | None":
    if _raw_is_blank(value):
        if required:
            raise StatcastNormalizationError(f"{name} is required and must not be empty")
        return None
    if isinstance(value, bool):
        raise StatcastNormalizationError(f"{name} must not be a bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise StatcastNormalizationError(f"{name} must be a whole number, got {value!r}")
        return int(value)
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        pass
    # Some CSV export tools coerce integer columns containing gaps elsewhere
    # in the column to a float representation (e.g. "3.0").
    try:
        as_float = float(text)
    except ValueError as exc:
        raise StatcastNormalizationError(f"{name} must be an integer, got {value!r}") from exc
    if not as_float.is_integer():
        raise StatcastNormalizationError(f"{name} must be a whole number, got {value!r}")
    return int(as_float)


def _parse_float(value, name: str, *, required: bool) -> "float | None":
    if _raw_is_blank(value):
        if required:
            raise StatcastNormalizationError(f"{name} is required and must not be empty")
        return None
    if isinstance(value, bool):
        raise StatcastNormalizationError(f"{name} must not be a bool")
    if not isinstance(value, (int, float, str)):
        raise StatcastNormalizationError(
            f"{name} must be numeric, got {type(value).__name__!r}"
        )
    try:
        parsed = float(value)
    except ValueError as exc:
        raise StatcastNormalizationError(f"{name} must be a number, got {value!r}") from exc
    if math.isnan(parsed):
        raise StatcastNormalizationError(f"{name} must not be NaN")
    if math.isinf(parsed):
        raise StatcastNormalizationError(f"{name} must not be infinite")
    return parsed


def _parse_required_str(value, name: str) -> str:
    if _raw_is_blank(value):
        raise StatcastNormalizationError(f"{name} is required and must not be empty")
    if not isinstance(value, str):
        raise StatcastNormalizationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    return value.strip()


def _parse_optional_str(value, name: str) -> "str | None":
    if _raw_is_blank(value):
        return None
    if not isinstance(value, str):
        raise StatcastNormalizationError(
            f"{name} must be a string or None, got {type(value).__name__!r}"
        )
    return value.strip()


def normalize_inning_half(value) -> str:
    text = _parse_required_str(value, "inning_half")
    normalized = _INNING_HALF_ALIASES.get(text.lower())
    if normalized is None:
        raise StatcastNormalizationError(
            f"inning_half must be one of {sorted(_INNING_HALF_ALIASES)}, got {value!r}"
        )
    return normalized


def normalize_game_date(value) -> str:
    text = _parse_required_str(value, "game_date")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise StatcastNormalizationError(
            f"game_date must be an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc
    return text


def normalize_batter_stands(value) -> str:
    text = _parse_required_str(value, "batter_stands").upper()
    if text not in VALID_BATTER_STANDS:
        raise StatcastNormalizationError(
            f"batter_stands must be one of {sorted(VALID_BATTER_STANDS)}, got {value!r}"
        )
    return text


def normalize_pitcher_throws(value) -> str:
    text = _parse_required_str(value, "pitcher_throws").upper()
    if text not in VALID_PITCHER_THROWS:
        raise StatcastNormalizationError(
            f"pitcher_throws must be one of {sorted(VALID_PITCHER_THROWS)}, got {value!r}"
        )
    return text


def normalize_pitch_result_type(value) -> "str | None":
    text = _parse_optional_str(value, "pitch_result_type")
    if text is None:
        return None
    upper = text.upper()
    if upper not in VALID_PITCH_RESULT_TYPES:
        raise StatcastNormalizationError(
            f"pitch_result_type must be one of {sorted(VALID_PITCH_RESULT_TYPES)}, got {value!r}"
        )
    return upper


def build_rsb_pitch_id(source_game_id: str, at_bat_number: int, pitch_number: int) -> str:
    identity = f"{source_game_id}:{at_bat_number}:{pitch_number}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def normalize_statcast_row(row, *, source_row_index: int, snapshot_id: str, source_provider: str) -> dict:
    if not isinstance(row, dict):
        raise StatcastNormalizationError(
            f"row must be a dict, got {type(row).__name__!r}"
        )

    def raw(field_name):
        return row.get(SOURCE_FIELD_MAPPING[field_name])

    source_game_id = _parse_required_digit_id(raw("source_game_id"), "source_game_id")
    source_play_id = _parse_optional_str(raw("source_play_id"), "source_play_id")

    game_date = normalize_game_date(raw("game_date"))
    game_year = _parse_int(raw("game_year"), "game_year", required=True)
    if game_year < 1800 or game_year > 2200:
        raise StatcastNormalizationError(f"game_year is out of range: {game_year!r}")

    at_bat_number = _parse_int(raw("at_bat_number"), "at_bat_number", required=True)
    if at_bat_number < 1:
        raise StatcastNormalizationError(f"at_bat_number must be >= 1, got {at_bat_number!r}")

    pitch_number = _parse_int(raw("pitch_number"), "pitch_number", required=True)
    if pitch_number < 1:
        raise StatcastNormalizationError(f"pitch_number must be >= 1, got {pitch_number!r}")

    inning = _parse_int(raw("inning"), "inning", required=True)
    if inning < 1:
        raise StatcastNormalizationError(f"inning must be >= 1, got {inning!r}")

    inning_half = normalize_inning_half(raw("inning_half"))

    game_type = _parse_required_str(raw("game_type"), "game_type").upper()
    home_team = _parse_required_str(raw("home_team"), "home_team").upper()
    away_team = _parse_required_str(raw("away_team"), "away_team").upper()

    home_score = _parse_int(raw("home_score"), "home_score", required=False)
    if home_score is not None and home_score < 0:
        raise StatcastNormalizationError(f"home_score must not be negative, got {home_score!r}")
    away_score = _parse_int(raw("away_score"), "away_score", required=False)
    if away_score is not None and away_score < 0:
        raise StatcastNormalizationError(f"away_score must not be negative, got {away_score!r}")

    batter_id = _parse_required_digit_id(raw("batter_id"), "batter_id")
    pitcher_id = _parse_required_digit_id(raw("pitcher_id"), "pitcher_id")
    batter_stands = normalize_batter_stands(raw("batter_stands"))
    pitcher_throws = normalize_pitcher_throws(raw("pitcher_throws"))

    on_1b = _parse_optional_digit_id(raw("on_1b"), "on_1b")
    on_2b = _parse_optional_digit_id(raw("on_2b"), "on_2b")
    on_3b = _parse_optional_digit_id(raw("on_3b"), "on_3b")

    balls = _parse_int(raw("balls"), "balls", required=True)
    if not (0 <= balls <= 3):
        raise StatcastNormalizationError(f"balls must be in 0..3, got {balls!r}")
    strikes = _parse_int(raw("strikes"), "strikes", required=True)
    if not (0 <= strikes <= 2):
        raise StatcastNormalizationError(f"strikes must be in 0..2, got {strikes!r}")
    outs = _parse_int(raw("outs"), "outs", required=True)
    if not (0 <= outs <= 2):
        raise StatcastNormalizationError(f"outs must be in 0..2, got {outs!r}")

    pitch_type = _parse_optional_str(raw("pitch_type"), "pitch_type")
    pitch_name = _parse_optional_str(raw("pitch_name"), "pitch_name")
    release_speed = _parse_float(raw("release_speed"), "release_speed", required=False)
    zone = _parse_int(raw("zone"), "zone", required=False)
    pitch_result_type = normalize_pitch_result_type(raw("pitch_result_type"))

    pa_event_raw = _parse_optional_str(raw("pa_event_raw"), "pa_event_raw")

    bb_type = _parse_optional_str(raw("bb_type"), "bb_type")
    launch_speed = _parse_float(raw("launch_speed"), "launch_speed", required=False)
    launch_angle = _parse_float(raw("launch_angle"), "launch_angle", required=False)
    hit_distance = _parse_float(raw("hit_distance"), "hit_distance", required=False)

    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise StatcastNormalizationError("snapshot_id must be a non-empty string")
    if not isinstance(source_provider, str) or not source_provider.strip():
        raise StatcastNormalizationError("source_provider must be a non-empty string")
    if not isinstance(source_row_index, int) or isinstance(source_row_index, bool) or source_row_index < 0:
        raise StatcastNormalizationError("source_row_index must be a non-negative int")

    values = {
        "rsb_pitch_id": build_rsb_pitch_id(source_game_id, at_bat_number, pitch_number),
        "source_game_id": source_game_id,
        "source_play_id": source_play_id,
        "game_date": game_date,
        "game_year": game_year,
        "at_bat_number": at_bat_number,
        "pitch_number": pitch_number,
        "inning": inning,
        "inning_half": inning_half,
        "game_type": game_type,
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "batter_stands": batter_stands,
        "pitcher_throws": pitcher_throws,
        "on_1b": on_1b,
        "on_2b": on_2b,
        "on_3b": on_3b,
        "balls": balls,
        "strikes": strikes,
        "outs": outs,
        "pitch_type": pitch_type,
        "pitch_name": pitch_name,
        "release_speed": release_speed,
        "zone": zone,
        "pitch_result_type": pitch_result_type,
        "pa_event_raw": pa_event_raw,
        "bb_type": bb_type,
        "launch_speed": launch_speed,
        "launch_angle": launch_angle,
        "hit_distance": hit_distance,
        "snapshot_id": snapshot_id.strip(),
        "source_provider": source_provider.strip(),
        "normalized_schema_version": STATCAST_PITCH_SCHEMA_VERSION,
        "source_row_index": source_row_index,
    }
    return {field: values[field] for field in NORMALIZED_PITCH_FIELD_ORDER}


def _validate_snapshot_id_arg(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StatcastNormalizationError("snapshot_id must be a non-empty string")
    return value.strip()


def _validate_source_provider_arg(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StatcastNormalizationError("source_provider must be a non-empty string")
    return value.strip()


def _validate_requested_date_range_arg(value) -> dict:
    if not isinstance(value, dict) or set(value.keys()) != {"start_date", "end_date"}:
        raise StatcastNormalizationError(
            "requested_date_range must be a dict with exactly 'start_date' and 'end_date' keys"
        )
    start_date = value["start_date"]
    end_date = value["end_date"]
    for name, date_value in (("start_date", start_date), ("end_date", end_date)):
        if not isinstance(date_value, str):
            raise StatcastNormalizationError(
                f"requested_date_range.{name} must be a string, got {type(date_value).__name__!r}"
            )
        try:
            datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError as exc:
            raise StatcastNormalizationError(
                f"requested_date_range.{name} must be an ISO date (YYYY-MM-DD): {date_value!r}"
            ) from exc
    if start_date > end_date:
        raise StatcastNormalizationError(
            f"requested_date_range.start_date {start_date!r} must not be after "
            f"requested_date_range.end_date {end_date!r}"
        )
    return {"start_date": start_date, "end_date": end_date}


def normalize_statcast_snapshot(rows, *, snapshot_id: str, source_provider: str, requested_date_range: dict) -> list:
    if not isinstance(rows, (list, tuple)):
        raise StatcastNormalizationError(
            f"rows must be a list or tuple, got {type(rows).__name__!r}"
        )
    # Validated before any row is touched so an empty (zero-row) snapshot
    # still enforces snapshot-level identity/date-range invariants.
    validated_snapshot_id = _validate_snapshot_id_arg(snapshot_id)
    validated_source_provider = _validate_source_provider_arg(source_provider)
    validated_date_range = _validate_requested_date_range_arg(requested_date_range)
    start_date = validated_date_range["start_date"]
    end_date = validated_date_range["end_date"]

    records = []
    seen_pitch_ids = set()
    for source_row_index, row in enumerate(rows):
        record = normalize_statcast_row(
            row,
            source_row_index=source_row_index,
            snapshot_id=validated_snapshot_id,
            source_provider=validated_source_provider,
        )
        if not (start_date <= record["game_date"] <= end_date):
            raise StatcastNormalizationError(
                f"row {source_row_index} game_date {record['game_date']!r} is outside "
                f"requested_date_range [{start_date}, {end_date}]"
            )
        pitch_id = record["rsb_pitch_id"]
        if pitch_id in seen_pitch_ids:
            raise StatcastNormalizationError(
                f"duplicate rsb_pitch_id within snapshot at row {source_row_index}: {pitch_id}"
            )
        seen_pitch_ids.add(pitch_id)
        records.append(record)

    records.sort(
        key=lambda r: (
            int(r["source_game_id"]),
            r["at_bat_number"],
            r["pitch_number"],
            r["source_row_index"],
        )
    )
    return records
