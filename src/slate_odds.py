from typing import List, Optional

from ev import implied_probability
from market_selector import evaluate_odds_lines, get_active_rules
from odds_collector import collect_odds, load_runtime_config, summarize_bookmakers
from odds_providers.base import build_match_id, normalize_team_slug

PREDICTION_MARKET = "h2h"
SELECTION_FLIP = {
    "home_win": "away_win",
    "away_win": "home_win",
    "draw": "draw",
}


def build_provider_odds_context(
    provider_name: Optional[str] = None,
    runtime_config: Optional[dict] = None,
) -> dict:
    runtime_config = runtime_config or load_runtime_config()
    runtime_config["odds_config"] = dict(runtime_config.get("odds_config", {}))
    if provider_name:
        runtime_config["odds_config"]["provider"] = provider_name

    odds_lines = collect_odds(runtime_config)
    rules = runtime_config.get("bet_rules") or get_active_rules()
    market_decisions = evaluate_odds_lines(odds_lines, rules)
    qualified_decisions = [decision for decision in market_decisions if decision["status"] == "qualified"]
    rejected_decisions = [decision for decision in market_decisions if decision["status"] != "qualified"]
    sport_profile = runtime_config["sport_profile"]
    odds_config = runtime_config["odds_config"]
    expected_books = odds_config.get("bookmakers", sport_profile.get("bookmakers", []))

    return {
        "runtime_config": runtime_config,
        "odds_lines": odds_lines,
        "market_decisions": market_decisions,
        "qualified_decisions": qualified_decisions,
        "rejected_decisions": rejected_decisions,
        "summary": {
            "provider": odds_config.get("provider", "mock"),
            "odds_lines_collected": len(odds_lines),
            "qualified_price_count": len(qualified_decisions),
            "rejected_price_group_count": len(rejected_decisions),
            "bookmaker_summary": summarize_bookmakers(odds_lines, expected_books),
        },
    }


def candidate_provider_match_id(match: dict) -> Optional[str]:
    date = match.get("date")
    home_team = match.get("home_team")
    away_team = match.get("away_team")
    if not date or not home_team or not away_team:
        return None
    return build_match_id(f"{date}T00:00:00Z", home_team, away_team)


def _line_date(line: dict) -> Optional[str]:
    commence_time = line.get("commence_time")
    if not commence_time:
        return None
    return commence_time.split("T")[0]


def _same_match_date(match: dict, line: dict) -> bool:
    match_date = match.get("date")
    provider_date = _line_date(line)
    if not match_date or not provider_date:
        return True
    return match_date == provider_date


def _team_slug(team_name: Optional[str]) -> str:
    return normalize_team_slug(team_name or "")


def _teams_match_direct(match: dict, line: dict) -> bool:
    return (
        _team_slug(match.get("home_team")) == _team_slug(line.get("home_team"))
        and _team_slug(match.get("away_team")) == _team_slug(line.get("away_team"))
    )


def _teams_match_reversed(match: dict, line: dict) -> bool:
    return (
        _team_slug(match.get("home_team")) == _team_slug(line.get("away_team"))
        and _team_slug(match.get("away_team")) == _team_slug(line.get("home_team"))
    )


def _decision_line(decision: dict) -> dict:
    return decision["best_line"]


def find_provider_price(
    match: dict,
    qualified_decisions: List[dict],
    requested_selection: str = "home_win",
    market: str = PREDICTION_MARKET,
) -> Optional[dict]:
    direct_match_id = match.get("match_id")
    generated_match_id = candidate_provider_match_id(match)

    for decision in qualified_decisions:
        line = _decision_line(decision)
        if decision["market"] != market:
            continue
        if decision["selection"] != requested_selection:
            continue
        if line.get("match_id") in {direct_match_id, generated_match_id}:
            return {
                "decision": decision,
                "line": line,
                "match_strategy": "match_id",
                "requested_selection": requested_selection,
                "provider_selection": decision["selection"],
            }

    for decision in qualified_decisions:
        line = _decision_line(decision)
        if decision["market"] != market:
            continue
        if decision["selection"] != requested_selection:
            continue
        if _same_match_date(match, line) and _teams_match_direct(match, line):
            return {
                "decision": decision,
                "line": line,
                "match_strategy": "team_date_direct",
                "requested_selection": requested_selection,
                "provider_selection": decision["selection"],
            }

    reversed_selection = SELECTION_FLIP.get(requested_selection)
    if reversed_selection:
        for decision in qualified_decisions:
            line = _decision_line(decision)
            if decision["market"] != market:
                continue
            if decision["selection"] != reversed_selection:
                continue
            if _same_match_date(match, line) and _teams_match_reversed(match, line):
                return {
                    "decision": decision,
                    "line": line,
                    "match_strategy": "team_date_reversed",
                    "requested_selection": requested_selection,
                    "provider_selection": decision["selection"],
                }

    return None


def manual_odds_choice(match: dict, requested_selection: str = "home_win") -> Optional[dict]:
    odds = match.get("odds") or {}
    if requested_selection not in odds:
        return None

    american_odds = int(odds[requested_selection])
    line = {
        "provider": "manual",
        "provider_event_id": None,
        "match_id": match["match_id"],
        "sport_key": None,
        "commence_time": None,
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "sportsbook": match.get("sportsbook"),
        "market": PREDICTION_MARKET,
        "selection": requested_selection,
        "american_odds": american_odds,
        "implied_probability": implied_probability(american_odds),
        "captured_at": None,
        "raw_json": {
            "source": "slate_manual_odds",
            "odds": odds,
        },
    }
    return {
        "decision": None,
        "line": line,
        "match_strategy": "manual_slate_odds",
        "requested_selection": requested_selection,
        "provider_selection": requested_selection,
    }


def resolve_odds_for_match(
    match: dict,
    provider_context: Optional[dict] = None,
    requested_selection: str = "home_win",
    market: str = PREDICTION_MARKET,
    allow_manual_fallback: bool = True,
) -> dict:
    if provider_context:
        provider_choice = find_provider_price(
            match=match,
            qualified_decisions=provider_context.get("qualified_decisions", []),
            requested_selection=requested_selection,
            market=market,
        )
        if provider_choice:
            provider_choice["source"] = "provider_qualified"
            return provider_choice

    if allow_manual_fallback:
        manual_choice = manual_odds_choice(match, requested_selection=requested_selection)
        if manual_choice:
            manual_choice["source"] = "manual_fallback" if provider_context else "manual"
            return manual_choice

    match_id = match.get("match_id", "<unknown_match>")
    raise ValueError(
        f"No qualified provider odds found for {match_id} selection {requested_selection}, "
        "and no usable manual fallback odds were available."
    )
