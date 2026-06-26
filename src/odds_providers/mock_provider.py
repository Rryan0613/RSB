from typing import List, Optional

from .base import OddsProvider, NormalizedOddsLine, make_normalized_line


class MockOddsProvider(OddsProvider):
    """
    Deterministic local provider for tests and development.
    Does not call any external API or spend API credits.
    """

    provider_name = "mock"

    def __init__(self, fixtures: Optional[list] = None):
        self.fixtures = fixtures or self._default_fixtures()

    def fetch_odds(
        self,
        sport_key: str,
        bookmakers: Optional[list] = None,
        markets: Optional[list] = None,
        **kwargs,
    ) -> List[NormalizedOddsLine]:
        requested_books = set(bookmakers or [])
        requested_markets = set(markets or ["h2h"])
        lines = []

        for event in self.fixtures:
            for book in event["bookmakers"]:
                if requested_books and book["key"] not in requested_books:
                    continue
                for market in book["markets"]:
                    if market["key"] not in requested_markets:
                        continue
                    for outcome in market["outcomes"]:
                        lines.append(make_normalized_line(
                            provider=self.provider_name,
                            provider_event_id=event["id"],
                            sport_key=sport_key,
                            commence_time=event["commence_time"],
                            home_team=event["home_team"],
                            away_team=event["away_team"],
                            sportsbook=book["key"],
                            market=market["key"],
                            selection=outcome["selection"],
                            american_odds=outcome["price"],
                            raw_json={
                                "event_id": event["id"],
                                "bookmaker": book["key"],
                                "market": market["key"],
                                "outcome": outcome,
                            },
                        ))
        return lines

    @staticmethod
    def _default_fixtures():
        return [
            {
                "id": "mock_event_001",
                "commence_time": "2026-06-26T20:00:00Z",
                "home_team": "Canada",
                "away_team": "France",
                "bookmakers": [
                    {
                        "key": "fanduel",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"selection": "home_win", "price": 225},
                                    {"selection": "draw", "price": 260},
                                    {"selection": "away_win", "price": -105},
                                ],
                            }
                        ],
                    },
                    {
                        "key": "draftkings",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"selection": "home_win", "price": 215},
                                    {"selection": "draw", "price": 255},
                                    {"selection": "away_win", "price": 100},
                                ],
                            }
                        ],
                    },
                    {
                        "key": "betmgm",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"selection": "home_win", "price": 230},
                                    {"selection": "draw", "price": 250},
                                    {"selection": "away_win", "price": -110},
                                ],
                            }
                        ],
                    },
                ],
            }
        ]
