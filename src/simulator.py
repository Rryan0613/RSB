import random
import math

def poisson_sample(lam, rng=None):
    """
    Simple Poisson sampler without external dependencies.
    Good enough for starter Monte Carlo.
    """
    rng = rng or random
    L = math.exp(lam * -1)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1

def estimate_goal_rates(match):
    h = match["home"]
    a = match["away"]

    home_lambda = max(0.15, (h.get("xg_for_l5", 1.3) + a.get("xg_against_l5", 1.3)) / 2)
    away_lambda = max(0.15, (a.get("xg_for_l5", 1.3) + h.get("xg_against_l5", 1.3)) / 2)

    # Missing starters penalty
    home_lambda -= 0.08 * h.get("missing_starters", 0)
    away_lambda -= 0.08 * a.get("missing_starters", 0)

    # Rest advantage adjustment
    rest_diff = h.get("rest_days", 5) - a.get("rest_days", 5)
    home_lambda += 0.03 * rest_diff
    away_lambda -= 0.03 * rest_diff

    return max(0.15, home_lambda), max(0.15, away_lambda)

def run_monte_carlo(match, simulations=10000, seed=None):
    if not isinstance(simulations, int) or simulations <= 0:
        raise ValueError("simulations must be a positive integer")

    rng = random.Random(seed) if seed is not None else random
    home_lambda, away_lambda = estimate_goal_rates(match)

    home_wins = 0
    draws = 0
    away_wins = 0
    btts = 0
    over_25 = 0

    score_counts = {}

    for _ in range(simulations):
        hs = poisson_sample(home_lambda, rng)
        as_ = poisson_sample(away_lambda, rng)

        score_counts[f"{hs}-{as_}"] = score_counts.get(f"{hs}-{as_}", 0) + 1

        if hs > as_:
            home_wins += 1
        elif hs == as_:
            draws += 1
        else:
            away_wins += 1

        if hs > 0 and as_ > 0:
            btts += 1

        if hs + as_ > 2.5:
            over_25 += 1

    top_scores = sorted(score_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "simulations": simulations,
        "seed_used": seed,
        "estimated_home_goals": home_lambda,
        "estimated_away_goals": away_lambda,
        "home_win_probability": home_wins / simulations,
        "draw_probability": draws / simulations,
        "away_win_probability": away_wins / simulations,
        "btts_probability": btts / simulations,
        "over_25_probability": over_25 / simulations,
        "top_scorelines": [{"score": s, "probability": c / simulations} for s, c in top_scores]
    }
