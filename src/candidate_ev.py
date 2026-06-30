import math

from candidate_evaluation import build_candidate_evaluation
from edge import calculate_edge
from ev import calculate_expected_value
from odds import (
    american_to_decimal_odds,
    american_to_implied_probability,
    decimal_to_implied_probability,
    validate_probability,
)


class CandidateEVValidationError(ValueError):
    pass


def _validate_line(value, name: str) -> "float | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise CandidateEVValidationError(f"{name} must not be a bool")
    if not isinstance(value, (int, float)):
        raise CandidateEVValidationError(
            f"{name} must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise CandidateEVValidationError(f"{name} must not be NaN")
    if math.isinf(value):
        raise CandidateEVValidationError(f"{name} must not be infinite")
    return float(value)


def _validate_minimum_edge(value) -> float:
    if isinstance(value, bool):
        raise CandidateEVValidationError("minimum_edge must not be a bool")
    if not isinstance(value, (int, float)):
        raise CandidateEVValidationError(
            f"minimum_edge must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise CandidateEVValidationError("minimum_edge must not be NaN")
    if math.isinf(value):
        raise CandidateEVValidationError("minimum_edge must not be infinite")
    if value < 0.0:
        raise CandidateEVValidationError(
            f"minimum_edge must be >= 0.0, got {value!r}"
        )
    if value > 1.0:
        raise CandidateEVValidationError(
            f"minimum_edge must be <= 1.0, got {value!r}"
        )
    return float(value)


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CandidateEVValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def build_candidate_ev_enrichment(
    *,
    candidate,
    odds_snapshot,
    model_probability,
    minimum_edge=0.0,
    metadata=None,
) -> dict:
    # 1. candidate must be dict
    if not isinstance(candidate, dict):
        raise CandidateEVValidationError(
            f"candidate must be a dict, got {type(candidate).__name__!r}"
        )
    # 2. odds_snapshot must be dict
    if not isinstance(odds_snapshot, dict):
        raise CandidateEVValidationError(
            f"odds_snapshot must be a dict, got {type(odds_snapshot).__name__!r}"
        )

    # 3. Extract candidate required keys
    try:
        cand_event_id = candidate["event_id"]
        cand_market_type = candidate["market_type"]
        cand_selection = candidate["selection"]
        cand_line_raw = candidate["line"]
    except KeyError as exc:
        raise CandidateEVValidationError(
            f"candidate is missing required key: {exc}"
        ) from exc

    # 4. Extract odds_snapshot required keys
    try:
        snap_event_id = odds_snapshot["event_id"]
        snap_market_type = odds_snapshot["market_type"]
        snap_selection = odds_snapshot["selection"]
        snap_line_raw = odds_snapshot["line"]
        snap_odds = odds_snapshot["odds"]
        snap_odds_format = odds_snapshot["odds_format"]
    except KeyError as exc:
        raise CandidateEVValidationError(
            f"odds_snapshot is missing required key: {exc}"
        ) from exc

    # 5. Identity matching
    if cand_event_id != snap_event_id:
        raise CandidateEVValidationError(
            f"candidate event_id {cand_event_id!r} does not match "
            f"odds_snapshot event_id {snap_event_id!r}"
        )
    if cand_market_type != snap_market_type:
        raise CandidateEVValidationError(
            f"candidate market_type {cand_market_type!r} does not match "
            f"odds_snapshot market_type {snap_market_type!r}"
        )
    if cand_selection != snap_selection:
        raise CandidateEVValidationError(
            f"candidate selection {cand_selection!r} does not match "
            f"odds_snapshot selection {snap_selection!r}"
        )

    # 6. Validate candidate line
    cand_line = _validate_line(cand_line_raw, "candidate line")
    # 7. Validate odds_snapshot line
    snap_line = _validate_line(snap_line_raw, "odds_snapshot line")
    # 8. Line mismatch check
    if cand_line is not None and snap_line is not None and cand_line != snap_line:
        raise CandidateEVValidationError(
            f"candidate line {cand_line!r} does not match "
            f"odds_snapshot line {snap_line!r}"
        )
    # 9. Resolve line
    if cand_line is not None:
        resolved_line = cand_line
    elif snap_line is not None:
        resolved_line = snap_line
    else:
        resolved_line = None

    # 10. Validate model_probability (OddsValidationError propagates)
    validated_model_probability = validate_probability(model_probability)

    # 11. Validate odds_format
    if not isinstance(snap_odds_format, str):
        raise CandidateEVValidationError(
            f"odds_format must be a string, got {type(snap_odds_format).__name__!r}"
        )
    normalized_format = snap_odds_format.strip().lower()
    if normalized_format not in ("american", "decimal"):
        raise CandidateEVValidationError(
            f"odds_format {snap_odds_format!r} is not supported; "
            f"must be 'american' or 'decimal'"
        )

    # 12. Validate minimum_edge
    validated_minimum_edge = _validate_minimum_edge(minimum_edge)

    # 13. Calculate implied_probability and decimal_odds
    #     OddsValidationError from odds.py propagates for invalid odds values
    if normalized_format == "american":
        implied_probability = american_to_implied_probability(snap_odds)
        decimal_odds = american_to_decimal_odds(snap_odds)
    else:
        implied_probability = decimal_to_implied_probability(snap_odds)
        decimal_odds = float(snap_odds)

    # 14. Calculate edge (OddsValidationError propagates)
    computed_edge = calculate_edge(validated_model_probability, implied_probability)

    # 15. Calculate expected_value (EVValidationError propagates)
    expected_value = calculate_expected_value(validated_model_probability, decimal_odds)

    # 16. Build candidate_evaluation
    if computed_edge >= validated_minimum_edge:
        candidate_eval = build_candidate_evaluation(
            "candidate",
            edge=computed_edge,
            pass_reasons=[],
        )
    else:
        candidate_eval = build_candidate_evaluation(
            "rejected",
            edge=computed_edge,
            pass_reasons=["edge_below_minimum"],
        )

    # 17. Validate and copy metadata
    validated_metadata = _validate_metadata(metadata)

    return {
        "candidate": dict(candidate),
        "odds_snapshot": dict(odds_snapshot),
        "event_id": cand_event_id,
        "market_type": cand_market_type,
        "selection": cand_selection,
        "line": resolved_line,
        "model_probability": validated_model_probability,
        "implied_probability": implied_probability,
        "edge": computed_edge,
        "expected_value": expected_value,
        "minimum_edge": validated_minimum_edge,
        "candidate_evaluation": candidate_eval,
        "metadata": validated_metadata,
    }
