import argparse
import json
import os
from typing import List, Optional

from market_selector import get_active_rules, summarize_rules
from odds_collector import collect_odds, load_runtime_config, summarize_bookmakers
from odds_providers import MockOddsProvider, TheOddsAPIProvider
from odds_providers.base import OddsProviderError, lines_to_dicts
from paths import DEFAULT_PROVIDER_DIAGNOSTICS_PATH

OUTPUT_PATH = DEFAULT_PROVIDER_DIAGNOSTICS_PATH


def mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def api_key_status(env_var: str = "ODDS_API_KEY") -> dict:
    value = os.getenv(env_var)
    return {
        "env_var": env_var,
        "present": bool(value),
        "masked": mask_secret(value),
    }


def create_provider(provider_name: str):
    if provider_name == "mock":
        return MockOddsProvider()
    if provider_name == "the_odds_api":
        return TheOddsAPIProvider()
    raise ValueError(f"Unsupported provider for diagnostics: {provider_name}")


def find_sports(provider, search_terms: List[str]) -> dict:
    if not hasattr(provider, "list_sports"):
        return {
            "supported": False,
            "matches": [],
            "error": None,
        }

    try:
        sports = provider.list_sports()
    except OddsProviderError as exc:
        return {
            "supported": True,
            "matches": [],
            "error": str(exc),
        }

    lowered_terms = [term.lower() for term in search_terms]
    matches = []
    for sport in sports:
        combined = " ".join(str(sport.get(field, "")) for field in ["key", "group", "title", "description"]).lower()
        if any(term in combined for term in lowered_terms):
            matches.append({
                "key": sport.get("key"),
                "group": sport.get("group"),
                "title": sport.get("title"),
                "description": sport.get("description"),
                "active": sport.get("active"),
            })

    return {
        "supported": True,
        "matches": matches,
        "error": None,
    }


def run_mock_diagnostics(runtime_config: dict) -> dict:
    odds_lines = collect_odds(runtime_config)
    sport_profile = runtime_config["sport_profile"]
    odds_config = runtime_config["odds_config"]
    expected_books = odds_config.get("bookmakers", sport_profile.get("bookmakers", []))

    return {
        "connection_status": "ok",
        "provider_notes": "Mock provider only. No external API call was made.",
        "odds_lines_collected": len(odds_lines),
        "bookmaker_summary": summarize_bookmakers(odds_lines, expected_books),
        "sample_lines": odds_lines[:3],
    }


def run_live_diagnostics(runtime_config: dict, list_sports: bool = True) -> dict:
    provider = create_provider("the_odds_api")
    sport_profile = runtime_config["sport_profile"]
    odds_config = runtime_config["odds_config"]
    expected_books = odds_config.get("bookmakers", sport_profile.get("bookmakers", []))

    sports_result = find_sports(provider, ["world cup", "soccer", "fifa"]) if list_sports else {
        "supported": False,
        "matches": [],
        "error": None,
    }

    lines = provider.fetch_odds(
        sport_key=sport_profile["provider_sport_key"],
        regions=odds_config.get("regions", "us"),
        bookmakers=expected_books,
        markets=odds_config.get("markets", sport_profile.get("markets", ["h2h"])),
        odds_format=odds_config.get("odds_format", "american"),
    )
    odds_lines = lines_to_dicts(lines)

    return {
        "connection_status": "ok",
        "provider_notes": "Live provider call completed. API key was not printed.",
        "sports_search": sports_result,
        "odds_lines_collected": len(odds_lines),
        "bookmaker_summary": summarize_bookmakers(odds_lines, expected_books),
        "sample_lines": odds_lines[:3],
    }


def build_diagnostics(provider_name: str, list_sports: bool = True) -> dict:
    runtime_config = load_runtime_config()
    runtime_config["odds_config"] = dict(runtime_config.get("odds_config", {}))
    runtime_config["odds_config"]["provider"] = provider_name
    rules = runtime_config.get("bet_rules") or get_active_rules()

    report = {
        "diagnostics_summary": {
            "model_version": runtime_config["model_config"].get("version"),
            "active_sport": runtime_config["active_sport"],
            "sport_label": runtime_config["sport_profile"].get("label"),
            "provider_sport_key": runtime_config["sport_profile"].get("provider_sport_key"),
            "provider": provider_name,
        },
        "api_key_status": api_key_status(),
        "rules_summary": summarize_rules(rules),
        "provider_result": None,
    }

    try:
        if provider_name == "mock":
            report["provider_result"] = run_mock_diagnostics(runtime_config)
        elif provider_name == "the_odds_api":
            report["provider_result"] = run_live_diagnostics(runtime_config, list_sports=list_sports)
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")
    except (OddsProviderError, ValueError) as exc:
        report["provider_result"] = {
            "connection_status": "error",
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "provider_notes": "No API key value was printed. Check ODDS_API_KEY, sport key, provider availability, or quota.",
        }

    return report


def parse_args():
    parser = argparse.ArgumentParser(description="Run safe odds provider diagnostics.")
    parser.add_argument(
        "--provider",
        choices=["mock", "the_odds_api"],
        default="mock",
        help="Provider to diagnose. Defaults to mock so no external API call is made.",
    )
    parser.add_argument(
        "--skip-sports-list",
        action="store_true",
        help="Skip live provider sports-list lookup.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    report = build_diagnostics(provider_name=args.provider, list_sports=not args.skip_sports_list)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
