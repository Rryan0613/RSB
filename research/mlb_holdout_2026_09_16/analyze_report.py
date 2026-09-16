"""Render a v0.3.4 evaluation report JSON as readable analysis tables.

Pure presentation. Computes no new metric and selects no winner.
"""

import argparse
import json
from pathlib import Path


def label(config):
    parts = [config["model_method"]]
    if config["batter_prior_strength"] is not None:
        parts.append(f"b={config['batter_prior_strength']:g}")
    if config["pitcher_prior_strength"] is not None:
        parts.append(f"p={config['pitcher_prior_strength']:g}")
    return " ".join(parts)


def window_of(result, name):
    for window in result["windows"]:
        if window["window"] == name:
            return window
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--window", default=None,
                        help="window name; default = every window present")
    parser.add_argument("--classwise-for", default=None,
                        help="render the 12 classwise rows for this method label")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text())
    coverage = report["coverage"]

    print("=" * 96)
    print("REPORT IDENTITY")
    print("=" * 96)
    for key in ("pa_evaluation_schema_version", "normalized_pa_schema_version",
                "normalized_pa_probability_schema_version", "sample_basis",
                "split_date", "source_snapshot_id", "input_content_sha256"):
        print(f"  {key:44s} {report[key]}")

    print()
    print("=" * 96)
    print("COVERAGE")
    print("=" * 96)
    for key in ("input_pa_count", "completed_pa_count", "incomplete_pa_count",
                "pitcher_rate_eligible_pa_count", "pitcher_rate_ineligible_pa_count",
                "intersection_pa_count", "zero_league_history_pa_count",
                "zero_batter_history_pa_count", "zero_pitcher_history_pa_count",
                "first_game_date", "last_game_date", "distinct_game_date_count",
                "distinct_calendar_month_count", "coverage_basis"):
        print(f"  {key:44s} {coverage[key]}")
    print("  method_support (native, before intersection):")
    for row in coverage["method_support"]:
        print(f"    {row['model_method']:24s} {row['natively_supported_completed_pa_count']}")

    windows = args.window and [args.window] or [
        w["window"] for w in report["results"][0]["windows"]]

    for window_name in windows:
        print()
        print("=" * 96)
        print(f"WINDOW: {window_name}")
        print("=" * 96)
        rows = []
        for result in report["results"]:
            window = window_of(result, window_name)
            if window is None:
                continue
            rows.append((label(result["config"]), window))
        if not rows:
            continue
        first = rows[0][1]
        print(f"  dates {first['first_game_date']}..{first['last_game_date']}  "
              f"scored n={first['scored_pa_count']}")
        print()
        print(f"  {'configuration':34s} {'log_loss':>11s} {'brier':>10s} "
              f"{'accuracy':>9s} {'topECE':>9s} {'topMCE':>9s} {'macroECE':>10s}")
        print("  " + "-" * 92)
        best_ll = min(w["mean_log_loss"] for _, w in rows)
        best_bs = min(w["mean_brier_score"] for _, w in rows)
        for name, window in sorted(rows, key=lambda r: r[1]["mean_log_loss"]):
            rel = window["top_label_reliability"]
            mark_ll = "*" if window["mean_log_loss"] == best_ll else " "
            mark_bs = "*" if window["mean_brier_score"] == best_bs else " "
            print(f"  {name:34s} {window['mean_log_loss']:11.6f}{mark_ll}"
                  f"{window['mean_brier_score']:9.6f}{mark_bs}"
                  f"{window['accuracy']:9.5f} "
                  f"{rel['expected_calibration_error']:9.5f} "
                  f"{rel['maximum_calibration_error']:9.5f} "
                  f"{window['macro_classwise_expected_calibration_error']:10.6f}")

        print()
        print("  monthly diagnostics:")
        for name, window in rows:
            months = window["calendar_month_diagnostics"]
            cells = "  ".join(
                f"{m['calendar_month']}:n={m['scored_pa_count']},LL={m['mean_log_loss']:.4f}"
                for m in months)
            print(f"    {name:34s} {cells}")
            print(f"    {'':34s} zero-league-history by month: "
                  + ", ".join(f"{m['calendar_month']}:{m['zero_league_history_pa_count']}"
                              for m in months))

        if args.classwise_for:
            for name, window in rows:
                if name != args.classwise_for:
                    continue
                print()
                print(f"  classwise diagnostics — {name}")
                print(f"    {'category':22s} {'actual_n':>9s} {'actual_freq':>12s} "
                      f"{'mean_pred':>11s} {'gap':>11s} {'ECE':>10s} {'MCE':>10s}")
                print("    " + "-" * 88)
                for row in window["category_diagnostics"]:
                    rel = row["reliability"]
                    print(f"    {row['category']:22s} {row['actual_count']:9d} "
                          f"{row['actual_frequency']:12.6f} "
                          f"{row['mean_predicted_probability']:11.6f} "
                          f"{row['calibration_gap']:+11.6f} "
                          f"{rel['expected_calibration_error']:10.6f} "
                          f"{rel['maximum_calibration_error']:10.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
