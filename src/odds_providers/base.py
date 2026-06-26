from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from ev import implied_probability


class OddsProviderError(RuntimeError):
    """Raised when an odds provider cannot fetch or normalize odds."""


@dataclass(frozen=True)
class NormalizedOddsLine:
    provider: str
    provider_event_id: str
    match_id: str
    sport_key: str
    commence_time: str
    home_team: str
    away_team: str
    sportsbook: str
    market: str
    selection: str
    american_odds: int
    implied_probability: float
    captured_at: str
    raw_json: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)


class OddsProvider:
    provider_name = "base"

    def fetch_odds(self, *args, **kwargs) -> List[NormalizedOddsLine]:
        raise NotImplementedError


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_team_slug(team_name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in team_name.strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def build_match_id(commence_time: str, home_team: str, away_team: str) -> str:
    date_part = (commence_time or "unknown_date").split("T")[0]
    return f"{date_part}_{normalize_team_slug(home_team)}_{normalize_team_slug(away_team)}"


def market_selection_from_outcome(outcome_name: str, home_team: str, away_team: str) -> str:
    if outcome_name == home_team:
        return "home_win"
    if outcome_name == away_team:
        return "away_win"
    if outcome_name.lower() == "draw":
        return "draw"
    return normalize_team_slug(outcome_name)


def make_normalized_line(
    provider: str,
    provider_event_id: str,
    sport_key: str,
    commence_time: str,
    home_team: str,
    away_team: str,
    sportsbook: str,
    market: str,
    selection: str,
    american_odds: int,
    raw_json: Optional[dict] = None,
) -> NormalizedOddsLine:
    match_id = build_match_id(commence_time, home_team, away_team)
    return NormalizedOddsLine(
        provider=provider,
        provider_event_id=provider_event_id,
        match_id=match_id,
        sport_key=sport_key,
        commence_time=commence_time,
        home_team=home_team,
        away_team=away_team,
        sportsbook=sportsbook,
        market=market,
        selection=selection,
        american_odds=int(american_odds),
        implied_probability=implied_probability(int(american_odds)),
        captured_at=now_utc(),
        raw_json=raw_json,
    )


def lines_to_dicts(lines: Iterable[NormalizedOddsLine]) -> List[dict]:
    return [line.to_dict() for line in lines]
