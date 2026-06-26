import json
import uuid
from pathlib import Path

from database import (
    init_db, save_match, save_features, save_prediction,
    save_simulation, load_training_rows, save_model_run,
    save_odds_snapshot
)
from features import make_features
from model import train_model, predict_probability, MODEL_PATH
from simulator import run_monte_carlo
from ev import implied_probability, edge, ev_per_unit
from validation import validate_slate

CONFIG = json.loads(Path("config/model_config.json").read_text())
MODEL_VERSION = CONFIG["version"]
MIN_EDGE = CONFIG["minimum_edge"]
MIN_TRAIN = CONFIG["minimum_completed_matches_to_train"]

def main():
    init_db()

    run_id = str(uuid.uuid4())[:8]
    slate_path = Path("data/input/slate.json")
    output_path = Path("data/output/latest_model_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    slate = json.loads(slate_path.read_text())
    validate_slate(slate)
    training_rows = load_training_rows(CONFIG["target_market"])

    model_status = "existing_model"
    trained_count = len(training_rows)

    if len(training_rows) >= MIN_TRAIN:
        trained_count, feature_cols = train_model(training_rows, minimum_rows=MIN_TRAIN)
        model_status = "retrained"
        save_model_run(run_id, MODEL_VERSION, "retrain_and_predict", trained_count, "Retrained using completed database matches.")
    elif not MODEL_PATH.exists():
        # Bootstrap fallback: use simulation probability only until enough historical data exists.
        model_status = "simulation_only_bootstrap"
        save_model_run(run_id, MODEL_VERSION, "simulation_only", trained_count, "Not enough data to train. Used Monte Carlo only.")
    else:
        save_model_run(run_id, MODEL_VERSION, "predict_existing_model", trained_count, "Used existing model.")

    predictions = []

    for match in slate["matches"]:
        save_match(match)

        features = make_features(match)
        save_features(run_id, MODEL_VERSION, match["match_id"], features)

        simulation_seed = match.get("simulation_seed", CONFIG.get("simulation_seed"))
        sim = run_monte_carlo(match, simulations=match.get("simulations", 10000), seed=simulation_seed)
        save_simulation(run_id, match["match_id"], sim["simulations"], sim)

        if model_status == "simulation_only_bootstrap":
            model_probability = sim["home_win_probability"]
        else:
            ml_probability = predict_probability(features)
            # Blend ML and simulation. Later versions can optimize this blend.
            model_probability = (0.65 * ml_probability) + (0.35 * sim["home_win_probability"])

        odds = int(match["odds"]["home_win"])
        imp = implied_probability(odds)
        edg = edge(model_probability, odds)
        ev = ev_per_unit(model_probability, odds)

        save_odds_snapshot(
            run_id=run_id,
            match_id=match["match_id"],
            sportsbook=match.get("sportsbook"),
            market="home_win",
            selection=f'{match["home_team"]} home win',
            american_odds=odds,
            implied_probability=imp
        )

        recommendation = "bet" if edg >= MIN_EDGE and ev > 0 else "pass"

        pred = {
            "run_id": run_id,
            "model_version": MODEL_VERSION,
            "match_id": match["match_id"],
            "match": f'{match["home_team"]} vs {match["away_team"]}',
            "market": "home_win",
            "selection": f'{match["home_team"]} home win',
            "model_probability": model_probability,
            "simulation_home_win_probability": sim["home_win_probability"],
            "simulation_seed": sim.get("seed_used"),
            "american_odds": odds,
            "implied_probability": imp,
            "edge": edg,
            "ev_per_unit": ev,
            "recommendation": recommendation,
            "simulation_summary": sim
        }

        save_prediction(pred)
        predictions.append(pred)

    report = {
        "run_summary": {
            "run_id": run_id,
            "model_version": MODEL_VERSION,
            "model_status": model_status,
            "trained_on_completed_matches": trained_count,
            "matches_analyzed": len(predictions)
        },
        "predictions": predictions
    }

    output_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
