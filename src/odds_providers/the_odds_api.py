import json
import os
from typing import List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from .base import (
    OddsProvider,
    OddsProviderError,
    NormalizedOddsLine,
    make_normalized_line,
    market_selection_from_outcome,
)


class TheOddsAPIProvider(OddsProvider):
    """Provider adapter for The Odds API v4."""

    provider_name = "the_odds_api"
    base_url = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        if not self.api_key:
            raise OddsProviderError("ODDS_API_KEY is not set. Export it locally before using The Odds API provider.")

    def fetch_odds(
        self,
        sport_key: str,
        regions: str = "us",
        bookmakers: Optional[list] = None,
        markets: Optional[list] = None,
        odds_format: str = "american",
        date_format: str = "iso",
    ) -> List[NormalizedOddsLine]:
        markets = markets or ["h2h"]
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": ",".join(markets),
            "oddsFormat": odds_format,
            "dateFormat": date_format,
        }

        if bookmakers:
            params["bookmakers"] = ",".join(bookmakers)

        url = f"{self.base_url}/sports/{sport_key}/odds?{urlencode(params)}"
        data = self._get_json(url)
        return self._normalize_events(data, sport_key)

    def list_sports(self) -> list:
        url = f"{self.base_url}/sports?{urlencode({'apiKey': self.api_key})}"
        return self._get_json(url)

    def _get_json(self, url: str):
        try:
            with urlopen(url, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OddsProviderError(f"The Odds API HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise OddsProviderError(f"The Odds API request failed: {exc}") from exc

    def _normalize_events(self, events: list, sport_key: str) -> List[NormalizedOddsLine]:
        lines = []
        for event in events:
            event_id = event.get("id")
            commence_time = event.get("commence_time")
            home_team = event.get("home_team")
            away_team = event.get("away_team")

            for book in event.get("bookmakers", []):
                sportsbook = book.get("key")
                for market in book.get("markets", []):
                    market_key = market.get("key")
                    for outcome in market.get("outcomes", []):
                        outcome_name = outcome.get("name")
                        price = outcome.get("price")
                        if price is None or outcome_name is None:
                            continue

                        selection = market_selection_from_outcome(outcome_name, home_team, away_team)
                        lines.append(make_normalized_line(
                            provider=self.provider_name,
                            provider_event_id=event_id,
                            sport_key=sport_key,
                            commence_time=commence_time,
                            home_team=home_team,
                            away_team=away_team,
                            sportsbook=sportsbook,
                            market=market_key,
                            selection=selection,
                            american_odds=int(price),
                            raw_json={
                                "event": event_id,
                                "bookmaker": sportsbook,
                                "last_update": book.get("last_update"),
                                "market": market_key,
                                "outcome": outcome,
                            },
                        ))
        return lines
