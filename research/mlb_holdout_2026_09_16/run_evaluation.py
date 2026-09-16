"""Run the frozen v0.3.4 evaluator against a persisted real PA dataset.

Two modes, matching the freeze protocol:

  --mode dev-sweep   Exploratory prior-strength sensitivity. Only records with
                     game_date < --split are passed to the evaluator, so no
                     holdout outcome can influence the result. No split_date is
                     given, so the evaluator reports one `full` window over the
                     development period.

  --mode confirm     Confirmatory run. All records are passed with
                     split_date = --split, producing `tuning` and `holdout`
                     windows for the pre-registered configurations only.

Scoring, bin edges, sample selection and the metric hierarchy all come from
v0.3.4 unchanged; this script only selects records and configurations.
"""

import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from paths import get_mlb_normalized_plate_appearance_dir  # noqa: E402
from mlb import (  # noqa: E402
    MODEL_METHODS,
    build_evaluation_model_config,
    evaluate_pa_walk_forward,
    validate_pa_evaluation_report,
)

# Exploratory sweep grid. Only consulted in --mode dev-sweep.
SWEEP_STRENGTHS = (25.0, 50.0, 100.0, 200.0, 400.0)


def baseline_configs():
    """The frozen confirmatory list (freeze stage 3).

    The four shipped v0.3.3 methods at the shipped defaults (1 / 100 / 100) are
    the FIXED REFERENCE and are always present. Two development-selected
    candidates at strength 200 are appended to test whether the development
    log-loss optimum generalizes out of sample. Both were chosen from the
    development-only sweep, before any holdout metric existed.

    Adding these two does not move the denominator: the intersection sample is
    already restricted by the pitcher-dependent shipped methods.
    """
    configs = [build_evaluation_model_config(model_method=method)
               for method in MODEL_METHODS]
    configs.append(build_evaluation_model_config(
        model_method="batter_shrinkage", batter_prior_strength=200.0))
    configs.append(build_evaluation_model_config(
        model_method="matchup_combination",
        batter_prior_strength=200.0, pitcher_prior_strength=200.0))
    return configs


def sweep_configs():
    configs = [build_evaluation_model_config(model_method="league_only")]
    for strength in SWEEP_STRENGTHS:
        configs.append(build_evaluation_model_config(
            model_method="batter_shrinkage", batter_prior_strength=strength))
    for strength in SWEEP_STRENGTHS:
        configs.append(build_evaluation_model_config(
            model_method="pitcher_shrinkage", pitcher_prior_strength=strength))
    for strength in SWEEP_STRENGTHS:
        configs.append(build_evaluation_model_config(
            model_method="matchup_combination",
            batter_prior_strength=strength, pitcher_prior_strength=strength))
    return configs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pa-dataset-id", required=True)
    parser.add_argument("--mode", choices=("dev-sweep", "confirm"), required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    path = get_mlb_normalized_plate_appearance_dir() / f"{args.pa_dataset_id}.jsonl.gz"
    records = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if args.mode == "dev-sweep" and record["game_date"] >= args.split:
                continue
            records.append(record)
    print(f"loaded {len(records)} PA records (mode={args.mode})", flush=True)

    if args.mode == "dev-sweep":
        configs = sweep_configs()
        split = None
    else:
        configs = baseline_configs()
        split = args.split
    print(f"{len(configs)} configurations", flush=True)

    report = evaluate_pa_walk_forward(records, model_configs=configs, split_date=split)
    validate_pa_evaluation_report(report)

    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}", flush=True)

    for result in report["results"]:
        config = result["config"]
        label = (f"{config['model_method']}"
                 f" b={config['batter_prior_strength']}"
                 f" p={config['pitcher_prior_strength']}")
        for window in result["windows"]:
            print(f"  {label:52s} {window['window']:8s} "
                  f"n={window['scored_pa_count']:7d} "
                  f"LL={window['mean_log_loss']:.6f} "
                  f"BS={window['mean_brier_score']:.6f} "
                  f"acc={window['accuracy']:.5f} "
                  f"macroECE={window['macro_classwise_expected_calibration_error']:.6f}",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
