import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from database import init_db, save_odds_lines
from ev import american_to_decimal
from odds_providers import MockOddsProvider, TheOddsAPIProvider
from odds_providers.base import lines_to_dicts

MODEL_CONFIG_PATH = Path("config/model_config.json")
SPORTS_CONFIG_PATH = Path("config/sports_config.json")
OUTPUT_PATH = Path("data/output/latest_odds_output.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_runtime_config() -> dict:
    model_config = load_json(MODEL_CONFIG_PATH)
    sports_config = load_json(SPORTS_CONFIG_PATH)
    active_sport = sports_config.get("active_sport", "worldcup")
    sport_profile = sports_config["sports"][active_sport]
    odds_config = model_config.get("odds_collection", {})

    return {
        "model_config": model_config,
        "sports_config": sports_config,
        "active_sport": active_sport,
        "sport_profile": sport_profile,
        "odds_config": odds_config,
    }


def create_odds_provider(provider_name: str, provider_config: Optional[dict] = None):
    provider_config = provider_config or {}
    if provider_name == "mock":
        return MockOddsProvider()
    if provider_name == "the_odds_api":
        return TheOddsAPIProvider(api_key=provider_config.get("api_key"))
    raise ValueError(f"Unsupported odds provider: {provider_name}")


def collect_odds(runtime_config: Optional[dict] = None) -> List[dict]:
    runtime_config = runtime_config or load_runtime_config()
    sport_profile = runtime_config["sport_profile"]
    odds_config = runtime_config["odds_config"]

    provider_name = odds_config.get("provider", "mock")
    provider = create_odds_provider(provider_name, odds_config)

    lines = provider.fetch_odds(
        sport_key=sport_profile["provider_sport_key"],
        regions=odds_config.get("regions", "us"),
        bookmakers=odds_config.get("bookmakers", sport_profile.get("bookmakers", [])),
        markets=odds_config.get("markets", sport_profile.get("markets", ["h2h"])),
        odds_format=odds_config.get("odds_format", "american"),
    )
    return lines_to_dicts(lines)


def price_rank(american_odds: int) -> float:
    """Higher decimal payout is better for the bettor."""
    return american_to_decimal(int(american_odds))


def select_best_prices(odds_lines: List[dict]) -> List[dict]:
    best_by_market: Dict[Tuple[str, str, str], dict] = {}

    for line in odds_lines:
        key = (line["match_id"], line["market"], line["selection"])
        current = best_by_market.get(key)
        if current is None or price_rank(line["american_odds"]) > price_rank(current["american_odds"]):
            best_by_market[key] = line

    return sorted(
        best_by_market.values(),
        key=lambda line: (line["match_id"], line["market"], line["selection"]),
    )


def summarize_bookmakers(odds_lines: List[dict], expected_bookmakers: List[str]) -> dict:
    counts = {book: 0 for book in expected_bookmakers}
    observed = set()

    for line in odds_lines:
        book = line["sportsbook"]
        counts[book] = counts.get(book, 0) + 1
        observed.add(book)

    missing = [book for book in expected_bookmakers if book not in observed]
    return {
        "line_counts_by_bookmaker": counts,
        "missing_expected_bookmakers": missing,
    }


def build_report(run_id: str, runtime_config: dict, odds_lines: List[dict]) -> dict:
    sport_profile = runtime_config["sport_profile"]
    odds_config = runtime_config["odds_config"]
    expected_books = odds_config.get("bookmakers", sport_profile.get("bookmakers", []))
    best_prices = select_best_prices(odds_lines)

    return {
        "run_summary": {
            "run_id": run_id,
            "model_version": runtime_config["model_config"].get("version"),
            "active_sport": runtime_config["active_sport"],
            "sport_label": sport_profile.get("label"),
            "provider_sport_key": sport_profile.get("provider_sport_key"),
            "provider": odds_config.get("provider", "mock"),
            "markets": odds_config.get("markets", sport_profile.get("markets", [])),
            "bookmakers_requested": expected_books,
            "odds_lines_collected": len(odds_lines),
            "best_price_count": len(best_prices),
        },
        "bookmaker_summary": summarize_bookmakers(odds_lines, expected_books),
        "best_prices": best_prices,
        "odds_lines": odds_lines,
    }


def main():
    init_db()
    runtime_config = load_runtime_config()
    run_id = str(uuid.uuid4())[:8]

    odds_lines = collect_odds(runtime_config)
    save_odds_lines(run_id, odds_lines)

    report = build_report(run_id, runtime_config, odds_lines)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
