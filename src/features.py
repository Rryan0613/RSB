from availability import availability_feature_set
from tactical_matchup import tactical_feature_set


def make_features(match):
    """
    World Cup v0.1 feature set.

    Current expected match schema:
    {
      "home": {...},
      "away": {...},
      "availability": {
        "home": {...},
        "away": {...}
      },
      "tactical": {
        "home": {...},
        "away": {...}
      },
      "odds": {"home_win": -120}
    }
    """

    h = match["home"]
    a = match["away"]

    features = {
        "fifa_rank_diff": h.get("fifa_rank", 50) - a.get("fifa_rank", 50),
        "elo_diff": h.get("elo", 1700) - a.get("elo", 1700),

        "xg_for_l5_diff": h.get("xg_for_l5", 1.3) - a.get("xg_for_l5", 1.3),
        "xg_against_l5_diff": h.get("xg_against_l5", 1.3) - a.get("xg_against_l5", 1.3),
        "shots_l5_diff": h.get("shots_l5", 10.0) - a.get("shots_l5", 10.0),
        "sog_l5_diff": h.get("sog_l5", 4.0) - a.get("sog_l5", 4.0),
        "big_chances_l5_diff": h.get("big_chances_l5", 2.0) - a.get("big_chances_l5", 2.0),
        "possession_l5_diff": h.get("possession_l5", 50.0) - a.get("possession_l5", 50.0),
        "pass_completion_l5_diff": h.get("pass_completion_l5", 80.0) - a.get("pass_completion_l5", 80.0),
        "ppda_l5_diff": h.get("ppda_l5", 10.0) - a.get("ppda_l5", 10.0),

        "rest_days_diff": h.get("rest_days", 5) - a.get("rest_days", 5),
        "injury_count_diff": h.get("injuries", 0) - a.get("injuries", 0),
        "suspension_count_diff": h.get("suspensions", 0) - a.get("suspensions", 0),
        "missing_starters_diff": h.get("missing_starters", 0) - a.get("missing_starters", 0),

        "motivation_diff": h.get("motivation", 7) - a.get("motivation", 7),
        "tournament_experience_diff": h.get("tournament_experience", 5) - a.get("tournament_experience", 5),
        "squad_value_diff": h.get("squad_value_millions", 250) - a.get("squad_value_millions", 250),

        "home_attack_vs_away_defense": h.get("xg_for_l5", 1.3) - a.get("xg_against_l5", 1.3),
        "away_attack_vs_home_defense": a.get("xg_for_l5", 1.3) - h.get("xg_against_l5", 1.3),
        "home_chance_pressure": h.get("sog_l5", 4.0) + h.get("big_chances_l5", 2.0),
        "away_chance_pressure": a.get("sog_l5", 4.0) + a.get("big_chances_l5", 2.0),

        "neutral_site": int(match.get("neutral_site", True))
    }
    features.update(availability_feature_set(match))
    features.update(tactical_feature_set(match))
    return features
