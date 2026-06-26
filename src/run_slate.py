import argparse
import json
import uuid
from pathlib import Path

from data_quality import (
    apply_recommendation_guardrail,
    assess_data_quality,
    summarize_data_quality,
)
from database import (
    init_db, save_match, save_features, save_prediction,
    save_simulation, load_training_rows, save_model_run,
    save_odds_snapshot, save_odds_lines
)
from features import make_features
from model import model_path_for_version, train_model, predict_probability
from simulator import run_monte_carlo
from ev import implied_probability, edge, ev_per_unit
from slate_odds import PREDICTION_MARKET, build_provider_odds_context, resolve_odds_for_match
from validation import validate_slate

CONFIG = json.loads(Path("config/model_config.json").read_text())
MODEL_VERSION = CONFIG["version"]
MIN_EDGE = CONFIG["minimum_edge"]
MIN_TRAIN = CONFIG["minimum_completed_matches_to_train"]
TARGET_MARKET = CONFIG["target_market"]
MODEL_PATH = model_path_for_version(MODEL_VERSION, TARGET_MARKET)


def parse_args():
    parser = argparse.ArgumentParser(description="Run the World Cup model against the current slate.")
    parser.add_argument(
        "--odds-source",
        choices=["manual", "provider"],
        default="manual",
        help="Use manual slate odds or qualified provider odds. Defaults to manual to avoid accidental API usage.",
    )
    parser.add_argument(
        "--odds-provider",
        choices=["mock", "the_odds_api"],
        default=None,
        help="Provider to use when --odds-source provider is selected. Defaults to config/model_config.json.",
    )
    parser.add_argument(
        "--no-manual-odds-fallback",
        action="store_true",
        help="Fail if qualified provider odds are unavailable for a slate match.",
    )
    return parser.parse_args()


def build_empty_provider_summary(provider_name=None):
    return {
        "provider": provider_name or CONFIG.get("odds_collection", {}).get("provider", "mock"),
        "odds_lines_collected": 0,
        "qualified_price_count": 0,
        "rejected_price_group_count": 0,
        "bookmaker_summary": {
            "line_counts_by_bookmaker": {},
            "missing_expected_bookmakers": [],
        },
        "notes": "Slate was empty, so provider odds were not collected.",
    }


def odds_resolution_payload(odds_choice: dict) -> dict:
    line = odds_choice["line"]
    return {
        "source": odds_choice["source"],
        "match_strategy": odds_choice["match_strategy"],
        "requested_selection": odds_choice["requested_selection"],
        "provider_selection": odds_choice["provider_selection"],
        "provider": line.get("provider"),
        "provider_event_id": line.get("provider_event_id"),
        "provider_match_id": line.get("match_id"),
        "sportsbook": line.get("sportsbook"),
    }


def main():
    args = parse_args()
    init_db()

    run_id = str(uuid.uuid4())[:8]
    slate_path = Path("data/input/slate.json")
    output_path = Path("data/output/latest_model_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    slate = json.loads(slate_path.read_text())
    validate_slate(slate, require_odds=args.odds_source == "manual")
    training_rows = load_training_rows(TARGET_MARKET)

    provider_context = None
    provider_odds_summary = None
    if args.odds_source == "provider":
        if slate["matches"]:
            provider_context = build_provider_odds_context(provider_name=args.odds_provider)
            save_odds_lines(run_id, provider_context["odds_lines"])
            provider_odds_summary = provider_context["summary"]
        else:
            provider_odds_summary = build_empty_provider_summary(args.odds_provider)

    model_status = "existing_model"
    trained_count = len(training_rows)

    if len(training_rows) >= MIN_TRAIN:
        trained_count, feature_cols = train_model(
            training_rows,
            minimum_rows=MIN_TRAIN,
            model_version=MODEL_VERSION,
            target_market=TARGET_MARKET,
            model_path=MODEL_PATH,
        )
        model_status = "retrained"
        save_model_run(run_id, MODEL_VERSION, "retrain_and_predict", trained_count, f"Retrained using completed database matches. Model path: {MODEL_PATH}")
    elif not MODEL_PATH.exists():
        # Bootstrap fallback: use simulation probability only until enough historical data exists.
        model_status = "simulation_only_bootstrap"
        save_model_run(run_id, MODEL_VERSION, "simulation_only", trained_count, "Not enough data to train. Used Monte Carlo only.")
    else:
        save_model_run(run_id, MODEL_VERSION, "predict_existing_model", trained_count, f"Used existing versioned model: {MODEL_PATH}")

    predictions = []
    provider_odds_matches = 0
    manual_odds_matches = 0

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
            ml_probability = predict_probability(features, model_path=MODEL_PATH)
            # Blend ML and simulation. Later versions can optimize this blend through backtesting.
            model_probability = (0.65 * ml_probability) + (0.35 * sim["home_win_probability"])

        odds_choice = resolve_odds_for_match(
            match=match,
            provider_context=provider_context,
            requested_selection=TARGET_MARKET,
            market=PREDICTION_MARKET,
            allow_manual_fallback=not args.no_manual_odds_fallback,
        )
        odds_line = odds_choice["line"]
        odds = int(odds_line["american_odds"])
        imp = implied_probability(odds)
        edg = edge(model_probability, odds)
        ev = ev_per_unit(model_probability, odds)
        odds_resolution = odds_resolution_payload(odds_choice)

        if odds_choice["source"] == "provider_qualified":
            provider_odds_matches += 1
        else:
            manual_odds_matches += 1

        save_odds_snapshot(
            run_id=run_id,
            match_id=match["match_id"],
            sportsbook=odds_line.get("sportsbook"),
            market=PREDICTION_MARKET,
            selection=TARGET_MARKET,
            american_odds=odds,
            implied_probability=imp,
            provider=odds_line.get("provider"),
            provider_event_id=odds_line.get("provider_event_id"),
            sport_key=odds_line.get("sport_key"),
            home_team=odds_line.get("home_team"),
            away_team=odds_line.get("away_team"),
            commence_time=odds_line.get("commence_time"),
            raw_json={
                "odds_resolution": odds_resolution,
                "provider_raw_json": odds_line.get("raw_json"),
            },
        )

        technical_recommendation = "bet" if edg >= MIN_EDGE and ev > 0 else "pass"
        quality_assessment = assess_data_quality(
            match=match,
            model_status=model_status,
            trained_count=trained_count,
            min_train=MIN_TRAIN,
            odds_choice=odds_choice,
            provider_context=provider_context,
        )
        recommendation = apply_recommendation_guardrail(technical_recommendation, quality_assessment)

        pred = {
            "run_id": run_id,
            "model_version": MODEL_VERSION,
            "match_id": match["match_id"],
            "match": f'{match["home_team"]} vs {match["away_team"]}',
            "target_market": TARGET_MARKET,
            "market": PREDICTION_MARKET,
            "selection": f'{match["home_team"]} home win',
            "model_probability": model_probability,
            "simulation_home_win_probability": sim["home_win_probability"],
            "simulation_seed": sim.get("seed_used"),
            "american_odds": odds,
            "implied_probability": imp,
            "edge": edg,
            "ev_per_unit": ev,
            "technical_recommendation": technical_recommendation,
            "recommendation": recommendation,
            "data_quality": quality_assessment["data_quality"],
            "quality_warnings": quality_assessment["warnings"],
            "actionable": quality_assessment["actionable"],
            "recommendation_guardrail": quality_assessment["recommendation_guardrail"],
            "guardrail_reasons": quality_assessment["guardrail_reasons"],
            "do_not_bet_real_money": quality_assessment["do_not_bet_real_money"],
            "odds_source": odds_choice["source"],
            "odds_match_strategy": odds_choice["match_strategy"],
            "sportsbook": odds_line.get("sportsbook"),
            "provider": odds_line.get("provider"),
            "provider_event_id": odds_line.get("provider_event_id"),
            "provider_match_id": odds_line.get("match_id"),
            "requested_selection": odds_choice["requested_selection"],
            "provider_selection": odds_choice["provider_selection"],
            "simulation_summary": sim,
        }

        save_prediction(pred)
        predictions.append(pred)

    report = {
        "run_summary": {
            "run_id": run_id,
            "model_version": MODEL_VERSION,
            "model_status": model_status,
            "model_path": str(MODEL_PATH),
            "trained_on_completed_matches": trained_count,
            "matches_analyzed": len(predictions),
            "odds_source_requested": args.odds_source,
            "odds_provider_requested": args.odds_provider,
            "provider_odds_matches": provider_odds_matches,
            "manual_odds_matches": manual_odds_matches,
            "data_quality_summary": summarize_data_quality(predictions),
        },
        "provider_odds_summary": provider_odds_summary,
        "predictions": predictions,
    }

    output_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
