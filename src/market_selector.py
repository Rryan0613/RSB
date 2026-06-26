import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ev import american_to_decimal
from paths import BET_RULES_CONFIG_PATH


def load_rules_config(path: Path = BET_RULES_CONFIG_PATH) -> dict:
    return json.loads(path.read_text())


def get_active_rules(rules_config: Optional[dict] = None) -> dict:
    rules_config = rules_config or load_rules_config()
    active_profile = rules_config.get("active_profile")
    if not active_profile:
        raise ValueError("bet_rules_config.json is missing active_profile")

    profiles = rules_config.get("profiles", {})
    if active_profile not in profiles:
        raise ValueError(f"Active bet rules profile not found: {active_profile}")

    rules = dict(profiles[active_profile])
    rules["profile_name"] = active_profile
    return rules


def decimal_odds(american_odds: int) -> float:
    return american_to_decimal(int(american_odds))


def price_rank(american_odds: int) -> float:
    """Higher decimal payout is better for the bettor."""
    return decimal_odds(american_odds)


def group_odds_lines(odds_lines: List[dict]) -> Dict[Tuple[str, str, str], List[dict]]:
    grouped: Dict[Tuple[str, str, str], List[dict]] = {}
    for line in odds_lines:
        key = (line["match_id"], line["market"], line["selection"])
        grouped.setdefault(key, []).append(line)
    return grouped


def select_best_price_for_group(lines: List[dict]) -> dict:
    if not lines:
        raise ValueError("Cannot select best price from an empty line group")
    return max(lines, key=lambda line: price_rank(line["american_odds"]))


def select_best_prices(odds_lines: List[dict]) -> List[dict]:
    best = []
    for lines in group_odds_lines(odds_lines).values():
        best.append(select_best_price_for_group(lines))
    return sorted(best, key=lambda line: (line["match_id"], line["market"], line["selection"]))


def _allowed_values(rules: dict, key: str) -> List[str]:
    values = rules.get(key, [])
    return values if isinstance(values, list) else []


def _target_odds_range(rules: dict) -> tuple:
    target = rules.get("target_odds", {})
    return target.get("min_decimal"), target.get("max_decimal")


def evaluate_price_group(lines: List[dict], rules: dict) -> dict:
    best_line = select_best_price_for_group(lines)
    market = best_line["market"]
    selection = best_line["selection"]
    sportsbooks_available = sorted({line["sportsbook"] for line in lines})
    required_books = rules.get("bookmaker_rules", {}).get("required", [])
    minimum_available = rules.get("bookmaker_rules", {}).get("minimum_available", 1)
    missing_books = [book for book in required_books if book not in sportsbooks_available]

    min_decimal, max_decimal = _target_odds_range(rules)
    best_decimal = decimal_odds(best_line["american_odds"])
    reasons = []

    allowed_markets = _allowed_values(rules, "allowed_markets")
    if allowed_markets and market not in allowed_markets:
        reasons.append(f"market_not_allowed:{market}")

    allowed_selections = _allowed_values(rules, "allowed_selections")
    if allowed_selections and selection not in allowed_selections:
        reasons.append(f"selection_not_allowed:{selection}")

    if min_decimal is not None and best_decimal < float(min_decimal):
        reasons.append(f"below_min_decimal_odds:{best_decimal:.4f}")

    if max_decimal is not None and best_decimal > float(max_decimal):
        reasons.append(f"above_max_decimal_odds:{best_decimal:.4f}")

    if len(sportsbooks_available) < int(minimum_available):
        reasons.append(f"not_enough_sportsbooks:{len(sportsbooks_available)}")

    return {
        "status": "qualified" if not reasons else "rejected",
        "reasons": reasons,
        "match_id": best_line["match_id"],
        "sport_key": best_line.get("sport_key"),
        "home_team": best_line.get("home_team"),
        "away_team": best_line.get("away_team"),
        "commence_time": best_line.get("commence_time"),
        "market": market,
        "selection": selection,
        "best_line": best_line,
        "best_decimal_odds": best_decimal,
        "sportsbooks_available": sportsbooks_available,
        "sportsbook_count": len(sportsbooks_available),
        "missing_required_sportsbooks": missing_books,
        "line_count": len(lines),
    }


def evaluate_odds_lines(odds_lines: List[dict], rules: Optional[dict] = None) -> List[dict]:
    rules = rules or get_active_rules()
    decisions = [evaluate_price_group(lines, rules) for lines in group_odds_lines(odds_lines).values()]
    return sorted(decisions, key=lambda item: (item["match_id"], item["market"], item["selection"]))


def qualified_best_prices(market_decisions: List[dict]) -> List[dict]:
    return [decision["best_line"] for decision in market_decisions if decision["status"] == "qualified"]


def rejected_price_groups(market_decisions: List[dict]) -> List[dict]:
    return [decision for decision in market_decisions if decision["status"] != "qualified"]


def summarize_rules(rules: dict) -> dict:
    return {
        "profile_name": rules.get("profile_name"),
        "label": rules.get("label"),
        "allowed_markets": rules.get("allowed_markets", []),
        "allowed_selections": rules.get("allowed_selections", []),
        "target_odds": rules.get("target_odds", {}),
        "bookmaker_rules": rules.get("bookmaker_rules", {}),
        "bet_structure": rules.get("bet_structure", {}),
    }
