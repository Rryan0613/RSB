from collections import Counter

import numpy as np

from availability import availability_feature_set
from tactical_matchup import tactical_feature_set

MIN_GOALS = 0.15
MAX_GOALS = 4.50


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def bounded_adjustment(value, scale, limit):
    return clamp(float(value) * scale, -limit, limit)


def base_goal_rates(match):
    h = match["home"]
    a = match["away"]

    home_lambda = max(MIN_GOALS, (h.get("xg_for_l5", 1.3) + a.get("xg_against_l5", 1.3)) / 2)
    away_lambda = max(MIN_GOALS, (a.get("xg_for_l5", 1.3) + h.get("xg_against_l5", 1.3)) / 2)

    home_lambda -= 0.08 * h.get("missing_starters", 0)
    away_lambda -= 0.08 * a.get("missing_starters", 0)

    rest_diff = h.get("rest_days", 5) - a.get("rest_days", 5)
    home_lambda += 0.03 * rest_diff
    away_lambda -= 0.03 * rest_diff

    return max(MIN_GOALS, home_lambda), max(MIN_GOALS, away_lambda)


def estimate_goal_context(match):
    home_lambda, away_lambda = base_goal_rates(match)
    availability = availability_feature_set(match)
    tactical = tactical_feature_set(match)

    adjustments = {}

    adjustments["lineup_strength"] = bounded_adjustment(availability["lineup_strength_diff"], 0.006, 0.18)
    adjustments["starter_availability"] = bounded_adjustment(availability["starter_availability_rate_diff"], 0.40, 0.14)
    adjustments["rotation_risk"] = bounded_adjustment(-availability["rotation_risk_diff"], 0.025, 0.12)
    adjustments["b_team_risk"] = bounded_adjustment(-availability["b_team_risk_diff"], 0.020, 0.10)
    adjustments["key_absence_impact"] = bounded_adjustment(-availability["key_absence_impact_diff"], 0.010, 0.15)
    adjustments["returning_player_risk"] = bounded_adjustment(-availability["returning_player_risk_diff"], 0.008, 0.10)
    adjustments["minutes_restricted"] = bounded_adjustment(-availability["minutes_restricted_count_diff"], 0.030, 0.09)

    adjustments["pressing_matchup"] = bounded_adjustment(
        tactical["home_press_vs_away_buildup"] - tactical["away_press_vs_home_buildup"],
        0.010,
        0.12,
    )
    adjustments["pace_high_line"] = bounded_adjustment(
        tactical["home_pace_vs_away_high_line"] - tactical["away_pace_vs_home_high_line"],
        0.012,
        0.15,
    )
    adjustments["crossing_aerial"] = bounded_adjustment(
        tactical["home_crossing_vs_away_aerial_defense"] - tactical["away_crossing_vs_home_aerial_defense"],
        0.012,
        0.10,
    )
    adjustments["set_piece"] = bounded_adjustment(
        tactical["home_set_piece_edge"] - tactical["away_set_piece_edge"],
        0.018,
        0.12,
    )
    adjustments["counterattack"] = bounded_adjustment(
        tactical["home_counterattack_edge"] - tactical["away_counterattack_edge"],
        0.010,
        0.12,
    )
    adjustments["chance_creation"] = bounded_adjustment(
        tactical["home_central_creation_edge"] + tactical["home_wide_creation_edge"]
        - tactical["away_central_creation_edge"] - tactical["away_wide_creation_edge"],
        0.006,
        0.12,
    )
    adjustments["midfield_control"] = bounded_adjustment(tactical["midfield_control_diff"], 0.010, 0.08)
    adjustments["manager_tactical"] = bounded_adjustment(tactical["manager_tactical_diff"], 0.008, 0.06)

    total_home_adjustment = sum(adjustments.values())
    home_lambda = clamp(home_lambda + total_home_adjustment, MIN_GOALS, MAX_GOALS)
    away_lambda = clamp(away_lambda - total_home_adjustment, MIN_GOALS, MAX_GOALS)

    return {
        "home_lambda": home_lambda,
        "away_lambda": away_lambda,
        "goal_rate_adjustments": adjustments,
        "total_home_goal_adjustment": total_home_adjustment,
    }


def estimate_goal_rates(match):
    context = estimate_goal_context(match)
    return context["home_lambda"], context["away_lambda"]


def run_monte_carlo(match, simulations=10000, seed=None):
    if not isinstance(simulations, int) or simulations <= 0:
        raise ValueError("simulations must be a positive integer")

    context = estimate_goal_context(match)
    home_lambda = context["home_lambda"]
    away_lambda = context["away_lambda"]

    rng = np.random.default_rng(seed)
    home_scores = rng.poisson(home_lambda, simulations)
    away_scores = rng.poisson(away_lambda, simulations)

    home_wins = int(np.sum(home_scores > away_scores))
    draws = int(np.sum(home_scores == away_scores))
    away_wins = int(np.sum(home_scores < away_scores))
    btts = int(np.sum((home_scores > 0) & (away_scores > 0)))
    over_25 = int(np.sum((home_scores + away_scores) > 2.5))

    score_counts = Counter(zip(home_scores.tolist(), away_scores.tolist()))
    top_scores = score_counts.most_common(5)

    return {
        "simulations": simulations,
        "seed_used": seed,
        "estimated_home_goals": home_lambda,
        "estimated_away_goals": away_lambda,
        "goal_rate_adjustments": context["goal_rate_adjustments"],
        "total_home_goal_adjustment": context["total_home_goal_adjustment"],
        "home_win_probability": home_wins / simulations,
        "draw_probability": draws / simulations,
        "away_win_probability": away_wins / simulations,
        "btts_probability": btts / simulations,
        "over_25_probability": over_25 / simulations,
        "top_scorelines": [
            {"score": f"{home}-{away}", "probability": count / simulations}
            for (home, away), count in top_scores
        ],
    }
