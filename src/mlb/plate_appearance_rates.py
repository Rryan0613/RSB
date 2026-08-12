import copy
import itertools

from .plate_appearance import (
    DETAILED_TO_CATEGORY,
    INCOMPLETE_TERMINAL_EVENTS,
    PLATE_APPEARANCE_FIELD_ORDER,
    PLATE_APPEARANCE_SCHEMA_VERSION,
    RATE_CATEGORIES,
    TERMINAL_EVENT_TAXONOMY,
)


class PlateAppearanceRateError(ValueError):
    pass


RATE_ENRICHED_FIELD_ORDER = PLATE_APPEARANCE_FIELD_ORDER + (
    "prior_batter_pa_count",
    "prior_batter_outcome_counts",
    "prior_batter_outcome_rates",
    "prior_pitcher_pa_count",
    "prior_pitcher_outcome_counts",
    "prior_pitcher_outcome_rates",
    "prior_league_pa_count",
    "prior_league_outcome_counts",
    "prior_league_outcome_rates",
)

_EXPECTED_PA_FIELDS = frozenset(PLATE_APPEARANCE_FIELD_ORDER)


def _validate_pa_record_shape(record, index: int) -> None:
    if not isinstance(record, dict):
        raise PlateAppearanceRateError(
            f"PA record {index} must be a dict, got {type(record).__name__!r}"
        )
    actual = set(record)
    if actual != _EXPECTED_PA_FIELDS:
        missing = _EXPECTED_PA_FIELDS - actual
        extra = actual - _EXPECTED_PA_FIELDS
        raise PlateAppearanceRateError(
            f"PA record {index} does not match the plate appearance contract; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
    if not isinstance(record["pitcher_rate_eligible"], bool):
        raise PlateAppearanceRateError(
            f"PA record {index} pitcher_rate_eligible must be a bool, got "
            f"{type(record['pitcher_rate_eligible']).__name__!r}"
        )

    if record["normalized_pa_schema_version"] != PLATE_APPEARANCE_SCHEMA_VERSION:
        raise PlateAppearanceRateError(
            f"PA record {index} normalized_pa_schema_version must be "
            f"{PLATE_APPEARANCE_SCHEMA_VERSION!r}, got "
            f"{record['normalized_pa_schema_version']!r}"
        )

    if record["pa_status"] not in ("completed", "incomplete"):
        raise PlateAppearanceRateError(
            f"PA record {index} has an invalid pa_status: {record['pa_status']!r}"
        )

    if record["pa_status"] == "incomplete":
        if record["pa_outcome_detailed"] is not None:
            raise PlateAppearanceRateError(
                f"PA record {index} is incomplete but has a non-null pa_outcome_detailed"
            )
        if record["pa_outcome_category"] is not None:
            raise PlateAppearanceRateError(
                f"PA record {index} is incomplete but has a non-null pa_outcome_category"
            )
        terminal_raw = record["terminal_pa_event_raw"]
        if terminal_raw is not None and terminal_raw not in INCOMPLETE_TERMINAL_EVENTS:
            raise PlateAppearanceRateError(
                f"PA record {index} is incomplete but has a terminal_pa_event_raw that "
                f"is neither None nor a recognized incomplete-terminal marker: "
                f"{terminal_raw!r}"
            )
    else:
        terminal_raw = record["terminal_pa_event_raw"]
        if terminal_raw not in TERMINAL_EVENT_TAXONOMY:
            raise PlateAppearanceRateError(
                f"PA record {index} is completed but terminal_pa_event_raw is not a "
                f"valid terminal taxonomy key: {terminal_raw!r}"
            )
        expected_detailed = TERMINAL_EVENT_TAXONOMY[terminal_raw]
        if record["pa_outcome_detailed"] != expected_detailed:
            raise PlateAppearanceRateError(
                f"PA record {index} pa_outcome_detailed "
                f"{record['pa_outcome_detailed']!r} does not match the classification "
                f"of terminal_pa_event_raw: {expected_detailed!r}"
            )
        expected_category = DETAILED_TO_CATEGORY[expected_detailed]
        if record["pa_outcome_category"] != expected_category:
            raise PlateAppearanceRateError(
                f"PA record {index} pa_outcome_category "
                f"{record['pa_outcome_category']!r} does not match the expected "
                f"category {expected_category!r}"
            )
        if record["pa_outcome_category"] not in RATE_CATEGORIES:
            raise PlateAppearanceRateError(
                f"PA record {index} has an invalid pa_outcome_category: "
                f"{record['pa_outcome_category']!r}"
            )


def _empty_counts() -> dict:
    return {category: 0 for category in RATE_CATEGORIES}


def _rates_from_counts(counts: dict, pa_count: int) -> dict:
    # Undefined (no-history) rates are represented as None, never 0.0 — a
    # zero rate and an unknown rate are not the same thing, and this
    # version performs no smoothing/shrinkage that would otherwise paper
    # over the distinction.
    if pa_count == 0:
        return {category: None for category in RATE_CATEGORIES}
    return {category: counts[category] / pa_count for category in RATE_CATEGORIES}


def _new_entity_state() -> dict:
    return {"pa_count": 0, "counts": _empty_counts()}


def attach_prior_outcome_rates(pa_records) -> list:
    """Attach leakage-safe prior batter/pitcher/league outcome state to each PA.

    Same-day cross-game leakage policy: a PA may treat an earlier PA as prior
    if that earlier PA's game_date is strictly earlier, or if they share the
    same source_game_id and the earlier PA has a smaller at_bat_number. A PA
    never treats another PA from a different source_game_id on the same
    game_date as prior in either direction, because the normalized pitch
    contract carries no game-start timestamp and their relative chronology
    is unknown. This is implemented as a two-level pass: counters are frozen
    at each date boundary and shared as a common baseline by every game on
    that date; only after all of a date's games are processed are that
    date's completed outcomes merged into the counters carried into the next
    date.

    Pure empirical counts and raw rates only — no smoothing, shrinkage,
    Bayesian priors, or minimum-sample thresholds.
    """
    if not isinstance(pa_records, (list, tuple)):
        raise PlateAppearanceRateError(
            f"pa_records must be a list or tuple, got {type(pa_records).__name__!r}"
        )

    for index, record in enumerate(pa_records):
        _validate_pa_record_shape(record, index)

    seen_pa_ids = set()
    for record in pa_records:
        pa_id = record["rsb_pa_id"]
        if pa_id in seen_pa_ids:
            raise PlateAppearanceRateError(f"duplicate rsb_pa_id across input: {pa_id}")
        seen_pa_ids.add(pa_id)

    sorted_records = sorted(
        pa_records,
        key=lambda r: (r["game_date"], int(r["source_game_id"]), r["at_bat_number"]),
    )

    global_batter: dict = {}
    global_pitcher: dict = {}
    global_league: dict = _new_entity_state()

    output = []

    for _game_date, date_group_iter in itertools.groupby(
        sorted_records, key=lambda r: r["game_date"]
    ):
        date_records = list(date_group_iter)
        date_start_batter = copy.deepcopy(global_batter)
        date_start_pitcher = copy.deepcopy(global_pitcher)
        date_start_league = copy.deepcopy(global_league)

        for _source_game_id, game_group_iter in itertools.groupby(
            date_records, key=lambda r: r["source_game_id"]
        ):
            local_batter = copy.deepcopy(date_start_batter)
            local_pitcher = copy.deepcopy(date_start_pitcher)
            local_league = copy.deepcopy(date_start_league)

            for record in game_group_iter:
                batter_state = local_batter.setdefault(record["batter_id"], _new_entity_state())
                pitcher_state = local_pitcher.setdefault(record["pitcher_id"], _new_entity_state())

                enriched = dict(record)
                enriched["prior_batter_pa_count"] = batter_state["pa_count"]
                enriched["prior_batter_outcome_counts"] = dict(batter_state["counts"])
                enriched["prior_batter_outcome_rates"] = _rates_from_counts(
                    batter_state["counts"], batter_state["pa_count"]
                )
                enriched["prior_pitcher_pa_count"] = pitcher_state["pa_count"]
                enriched["prior_pitcher_outcome_counts"] = dict(pitcher_state["counts"])
                enriched["prior_pitcher_outcome_rates"] = _rates_from_counts(
                    pitcher_state["counts"], pitcher_state["pa_count"]
                )
                enriched["prior_league_pa_count"] = local_league["pa_count"]
                enriched["prior_league_outcome_counts"] = dict(local_league["counts"])
                enriched["prior_league_outcome_rates"] = _rates_from_counts(
                    local_league["counts"], local_league["pa_count"]
                )
                output.append({field: enriched[field] for field in RATE_ENRICHED_FIELD_ORDER})

                if record["pa_status"] == "completed":
                    category = record["pa_outcome_category"]
                    batter_state["pa_count"] += 1
                    batter_state["counts"][category] += 1
                    local_league["pa_count"] += 1
                    local_league["counts"][category] += 1
                    if record["pitcher_rate_eligible"]:
                        pitcher_state["pa_count"] += 1
                        pitcher_state["counts"][category] += 1

        for record in date_records:
            if record["pa_status"] != "completed":
                continue
            category = record["pa_outcome_category"]
            batter_state = global_batter.setdefault(record["batter_id"], _new_entity_state())
            batter_state["pa_count"] += 1
            batter_state["counts"][category] += 1
            global_league["pa_count"] += 1
            global_league["counts"][category] += 1
            if record["pitcher_rate_eligible"]:
                pitcher_state = global_pitcher.setdefault(
                    record["pitcher_id"], _new_entity_state()
                )
                pitcher_state["pa_count"] += 1
                pitcher_state["counts"][category] += 1

    return output
