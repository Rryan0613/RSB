import hashlib
import itertools

from .statcast_normalize import NORMALIZED_PITCH_FIELD_ORDER


class PlateAppearanceValidationError(ValueError):
    pass


PLATE_APPEARANCE_SCHEMA_VERSION = "1"

# Terminal detection is chronology-driven (max pitch_number in a PA group), not
# taxonomy-driven — this table only classifies whatever pitch chronology has
# already identified as the terminal candidate. Baseball Savant's CSV
# documentation defines `events` as "the event of the resulting plate
# appearance"; a non-null value on any earlier pitch is therefore treated as
# an unexpected source condition (see group_pitches_into_plate_appearances),
# not as a benign, catalogued mid-PA event. There is deliberately no
# non-terminal event whitelist in this version.
#
# raw pa_event_raw -> detailed canonical outcome. intent_walk is kept
# distinct from walk at every layer, including the category taxonomy below —
# the historical foundation must never erase that distinction.
TERMINAL_EVENT_TAXONOMY = {
    "strikeout": "strikeout",
    "strikeout_double_play": "strikeout_double_play",
    "walk": "walk",
    "intent_walk": "intent_walk",
    "hit_by_pitch": "hit_by_pitch",
    "single": "single",
    "double": "double",
    "triple": "triple",
    "home_run": "home_run",
    "field_out": "field_out",
    "force_out": "force_out",
    "grounded_into_double_play": "grounded_into_double_play",
    "double_play": "double_play",
    "triple_play": "triple_play",
    "fielders_choice": "fielders_choice",
    "fielders_choice_out": "fielders_choice_out",
    "field_error": "field_error",
    "sac_fly": "sac_fly",
    "sac_fly_double_play": "sac_fly_double_play",
    "sac_bunt": "sac_bunt",
    "sac_bunt_double_play": "sac_bunt_double_play",
    "catcher_interf": "catcher_interf",
}

# detailed canonical outcome -> smaller mutually-exclusive modeling category.
# intent_walk maps to its own intentional_walk category rather than being
# folded into walk. Whether a future model combines them is v0.3.3 scope;
# this version never erases the distinction.
DETAILED_TO_CATEGORY = {
    "strikeout": "strikeout",
    "strikeout_double_play": "strikeout",
    "walk": "walk",
    "intent_walk": "intentional_walk",
    "hit_by_pitch": "hit_by_pitch",
    "single": "single",
    "double": "double",
    "triple": "triple",
    "home_run": "home_run",
    "field_out": "field_out",
    "force_out": "field_out",
    "grounded_into_double_play": "field_out",
    "double_play": "field_out",
    "triple_play": "field_out",
    "sac_fly": "field_out",
    "sac_fly_double_play": "field_out",
    "sac_bunt": "field_out",
    "sac_bunt_double_play": "field_out",
    "fielders_choice": "fielders_choice",
    "fielders_choice_out": "fielders_choice",
    "field_error": "reached_on_error",
    "catcher_interf": "catcher_interference",
}

assert set(TERMINAL_EVENT_TAXONOMY.values()) == set(DETAILED_TO_CATEGORY)

RATE_CATEGORIES = (
    "strikeout",
    "walk",
    "intentional_walk",
    "hit_by_pitch",
    "single",
    "double",
    "triple",
    "home_run",
    "field_out",
    "fielders_choice",
    "reached_on_error",
    "catcher_interference",
)

assert set(RATE_CATEGORIES) == set(DETAILED_TO_CATEGORY.values())

# Closed set of raw terminal pa_event_raw values that represent a genuinely
# interrupted/incomplete plate appearance rather than a completed outcome.
# These are deliberately kept out of TERMINAL_EVENT_TAXONOMY, DETAILED_TO_CATEGORY,
# and RATE_CATEGORIES: they must never classify as a completed outcome or
# contribute to any historical rate denominator. Established from a manual
# Baseball Savant review sample; unknown future non-null terminal codes still
# fail closed rather than being silently added here.
INCOMPLETE_TERMINAL_EVENTS = frozenset({
    "truncated_pa",
})

assert INCOMPLETE_TERMINAL_EVENTS.isdisjoint(TERMINAL_EVENT_TAXONOMY)

PLATE_APPEARANCE_FIELD_ORDER = (
    "rsb_pa_id",
    "source_game_id",
    "game_date",
    "game_year",
    "game_type",
    "home_team",
    "away_team",
    "inning",
    "inning_half",
    "at_bat_number",
    "batter_id",
    "batter_stands",
    "pitcher_id",
    "pitcher_throws",
    "source_pitcher_ids",
    "pitcher_rate_eligible",
    "outs_before_pa",
    "on_1b_before_pa",
    "on_2b_before_pa",
    "on_3b_before_pa",
    "home_score_before_pa",
    "away_score_before_pa",
    "pa_status",
    "pa_outcome_detailed",
    "pa_outcome_category",
    "terminal_pa_event_raw",
    "pitch_count",
    "source_pitch_ids",
    "source_snapshot_id",
    "normalized_pa_schema_version",
)

_EXPECTED_PITCH_FIELDS = frozenset(NORMALIZED_PITCH_FIELD_ORDER)

# Context fields that must not vary across the pitches of a single plate
# appearance. batter_id/batter_stands are included: v0.3.2 does not resolve
# attribution when multiple batter identities or batting sides appear inside
# one grouped PA, so any variation here fails closed rather than guessing
# historical credit.
_CONSTANT_CONTEXT_FIELDS = (
    "game_date",
    "game_year",
    "game_type",
    "home_team",
    "away_team",
    "inning",
    "inning_half",
    "batter_id",
    "batter_stands",
    "snapshot_id",
    "source_provider",
    "normalized_schema_version",
)


def build_rsb_pa_id(source_game_id: str, at_bat_number: int) -> str:
    identity = f"{source_game_id}:{at_bat_number}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def classify_terminal_event(pa_event_raw: str) -> tuple:
    """Classify a non-null terminal pa_event_raw value.

    Callers must not pass None — a null terminal pa_event_raw means the PA is
    incomplete, which is decided by the caller before this is invoked.
    Raises PlateAppearanceValidationError for any value not in the closed
    terminal taxonomy, rather than guessing.
    """
    if pa_event_raw not in TERMINAL_EVENT_TAXONOMY:
        raise PlateAppearanceValidationError(
            f"unrecognized terminal pa_event_raw: {pa_event_raw!r}"
        )
    detailed = TERMINAL_EVENT_TAXONOMY[pa_event_raw]
    category = DETAILED_TO_CATEGORY[detailed]
    return (detailed, category)


def _validate_pitch_record_shape(record, index: int) -> None:
    if not isinstance(record, dict):
        raise PlateAppearanceValidationError(
            f"pitch record {index} must be a dict, got {type(record).__name__!r}"
        )
    actual = set(record)
    if actual != _EXPECTED_PITCH_FIELDS:
        missing = _EXPECTED_PITCH_FIELDS - actual
        extra = actual - _EXPECTED_PITCH_FIELDS
        raise PlateAppearanceValidationError(
            f"pitch record {index} does not match the normalized pitch contract; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )


def _build_pa_record(source_game_id, at_bat_number, group: list) -> dict:
    n = len(group)
    pitch_numbers = [p["pitch_number"] for p in group]
    if pitch_numbers != list(range(1, n + 1)):
        raise PlateAppearanceValidationError(
            f"plate appearance {source_game_id}:{at_bat_number} has a non-contiguous "
            f"pitch_number sequence: {pitch_numbers}"
        )

    for field in _CONSTANT_CONTEXT_FIELDS:
        values = {p[field] for p in group}
        if len(values) > 1:
            raise PlateAppearanceValidationError(
                f"plate appearance {source_game_id}:{at_bat_number} has inconsistent "
                f"{field} across its pitches: {sorted(map(str, values))}"
            )

    first = group[0]

    # Pitcher sequence: a legitimate mid-PA substitution is one or more
    # forward-only pitcher changes (e.g. A,A,B,B, or A,B,C). A sequence that
    # reverts to an earlier pitcher (A,B,A) cannot represent a real
    # substitution and is treated as a genuine contradiction. Any number of
    # forward-only substitutions is preserved as valid, but the PA becomes
    # ineligible for pitcher-rate attribution — see plate_appearance_rates.py.
    # Each distinct pitcher_id must also map to exactly one pitcher_throws
    # value within the PA; a pitcher whose recorded throwing hand changes
    # mid-PA indicates contradictory source data, not a real substitution.
    source_pitcher_ids = []
    pitcher_throws_by_id = {}
    for pitch in group:
        pitcher_id = pitch["pitcher_id"]
        pitcher_throws_value = pitch["pitcher_throws"]

        if pitcher_id in pitcher_throws_by_id:
            if pitcher_throws_by_id[pitcher_id] != pitcher_throws_value:
                raise PlateAppearanceValidationError(
                    f"plate appearance {source_game_id}:{at_bat_number} has pitcher "
                    f"{pitcher_id} associated with inconsistent pitcher_throws "
                    f"values: {pitcher_throws_by_id[pitcher_id]!r} and "
                    f"{pitcher_throws_value!r}"
                )
        else:
            pitcher_throws_by_id[pitcher_id] = pitcher_throws_value

        if source_pitcher_ids and source_pitcher_ids[-1] == pitcher_id:
            continue
        if pitcher_id in source_pitcher_ids:
            raise PlateAppearanceValidationError(
                f"plate appearance {source_game_id}:{at_bat_number} has a pitcher "
                f"sequence that reverts to an earlier pitcher: "
                f"{[p['pitcher_id'] for p in group]}"
            )
        source_pitcher_ids.append(pitcher_id)
    pitcher_rate_eligible = len(source_pitcher_ids) == 1

    terminal_pitch = group[-1]

    # Chronology-first terminal detection: the max-pitch_number pitch is the
    # only terminal candidate. Per Baseball Savant's CSV documentation,
    # `events` is the event of the resulting plate appearance — a non-null
    # value on any earlier pitch is an unexpected source condition, not a
    # recognized mid-PA event, and fails closed rather than being silently
    # absorbed or treated as a second terminal outcome.
    for pitch in group[:-1]:
        if pitch["pa_event_raw"] is not None:
            raise PlateAppearanceValidationError(
                f"plate appearance {source_game_id}:{at_bat_number} has a non-null "
                f"pa_event_raw on a non-terminal pitch (pitch_number="
                f"{pitch['pitch_number']}): {pitch['pa_event_raw']!r}"
            )

    terminal_event_raw = terminal_pitch["pa_event_raw"]
    if terminal_event_raw is None or terminal_event_raw in INCOMPLETE_TERMINAL_EVENTS:
        pa_status = "incomplete"
        pa_outcome_detailed = None
        pa_outcome_category = None
    else:
        pa_outcome_detailed, pa_outcome_category = classify_terminal_event(terminal_event_raw)
        pa_status = "completed"

    values = {
        "rsb_pa_id": build_rsb_pa_id(source_game_id, at_bat_number),
        "source_game_id": source_game_id,
        "game_date": first["game_date"],
        "game_year": first["game_year"],
        "game_type": first["game_type"],
        "home_team": first["home_team"],
        "away_team": first["away_team"],
        "inning": first["inning"],
        "inning_half": first["inning_half"],
        "at_bat_number": at_bat_number,
        "batter_id": first["batter_id"],
        "batter_stands": first["batter_stands"],
        "pitcher_id": terminal_pitch["pitcher_id"],
        "pitcher_throws": terminal_pitch["pitcher_throws"],
        "source_pitcher_ids": source_pitcher_ids,
        "pitcher_rate_eligible": pitcher_rate_eligible,
        "outs_before_pa": first["outs"],
        "on_1b_before_pa": first["on_1b"],
        "on_2b_before_pa": first["on_2b"],
        "on_3b_before_pa": first["on_3b"],
        "home_score_before_pa": first["home_score"],
        "away_score_before_pa": first["away_score"],
        "pa_status": pa_status,
        "pa_outcome_detailed": pa_outcome_detailed,
        "pa_outcome_category": pa_outcome_category,
        "terminal_pa_event_raw": terminal_event_raw,
        "pitch_count": n,
        "source_pitch_ids": [p["rsb_pitch_id"] for p in group],
        "source_snapshot_id": first["snapshot_id"],
        "normalized_pa_schema_version": PLATE_APPEARANCE_SCHEMA_VERSION,
    }
    return {field: values[field] for field in PLATE_APPEARANCE_FIELD_ORDER}


def group_pitches_into_plate_appearances(pitch_records) -> list:
    """Group normalized v0.3.1 pitch records into canonical PA records.

    Operates on the output of a single normalized snapshot (or an already
    caller-deduplicated list of normalized pitch dicts) — multi-snapshot
    merge/reconciliation is out of scope for this version. Every pitch
    record must match the exact v0.3.1 normalized pitch contract shape.
    """
    if not isinstance(pitch_records, (list, tuple)):
        raise PlateAppearanceValidationError(
            f"pitch_records must be a list or tuple, got {type(pitch_records).__name__!r}"
        )

    for index, record in enumerate(pitch_records):
        _validate_pitch_record_shape(record, index)

    seen_pitch_ids = set()
    for record in pitch_records:
        pitch_id = record["rsb_pitch_id"]
        if pitch_id in seen_pitch_ids:
            raise PlateAppearanceValidationError(
                f"duplicate rsb_pitch_id across input: {pitch_id}"
            )
        seen_pitch_ids.add(pitch_id)

    sorted_records = sorted(
        pitch_records,
        key=lambda r: (int(r["source_game_id"]), r["at_bat_number"], r["pitch_number"]),
    )

    pa_records = []
    for (source_game_id, at_bat_number), group_iter in itertools.groupby(
        sorted_records, key=lambda r: (r["source_game_id"], r["at_bat_number"])
    ):
        group = list(group_iter)
        pa_records.append(_build_pa_record(source_game_id, at_bat_number, group))

    pa_records.sort(key=lambda r: (r["game_date"], int(r["source_game_id"]), r["at_bat_number"]))
    return pa_records
