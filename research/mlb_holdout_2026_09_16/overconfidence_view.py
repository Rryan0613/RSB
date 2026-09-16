"""Descriptive overconfidence view over a v0.3.4 report's classwise curves.

Answers "is this configuration systematically more confident than the outcomes
justify?" using only numbers v0.3.4 already computed. It introduces no new
scoring rule and ranks nothing; the v0.3.4 metric hierarchy remains
authoritative for comparison.

For each configuration it reports, over the 12 classwise reliability curves:

  high-confidence mass   count-weighted mean predicted probability, and the
                         observed frequency, restricted to bins at or above
                         --edge. Overconfidence shows up as observed < predicted.
  signed gap             observed - predicted over that region (negative =
                         overconfident).
  sharpness proxy        share of all classwise observations landing at or
                         above --edge. A sharper model puts more mass there.
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--window", required=True)
    parser.add_argument("--edge", type=float, default=0.2)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text())

    print(f"classwise high-confidence region: bins with lower_edge >= {args.edge}")
    print(f"window: {args.window}")
    print()
    print(f"  {'configuration':34s} {'obs_n':>9s} {'share':>8s} "
          f"{'pred':>9s} {'observed':>9s} {'gap':>10s}")
    print("  " + "-" * 84)

    rows = []
    for result in report["results"]:
        window = next((w for w in result["windows"]
                       if w["window"] == args.window), None)
        if window is None:
            continue
        total_obs = 0
        high_n = 0
        pred_sum = 0.0
        obs_sum = 0.0
        for diagnostic in window["category_diagnostics"]:
            for b in diagnostic["reliability"]["bins"]:
                total_obs += b["count"]
                if b["count"] == 0 or b["lower_edge"] < args.edge:
                    continue
                high_n += b["count"]
                pred_sum += b["mean_predicted_probability"] * b["count"]
                obs_sum += b["observed_frequency"] * b["count"]
        if high_n == 0:
            rows.append((label(result["config"]), 0, 0.0, None, None, None))
            continue
        pred = pred_sum / high_n
        obs = obs_sum / high_n
        rows.append((label(result["config"]), high_n, high_n / total_obs,
                     pred, obs, obs - pred))

    for name, high_n, share, pred, obs, gap in rows:
        if pred is None:
            print(f"  {name:34s} {high_n:9d} {share:8.5f} "
                  f"{'-':>9s} {'-':>9s} {'-':>10s}")
            continue
        print(f"  {name:34s} {high_n:9d} {share:8.5f} "
              f"{pred:9.5f} {obs:9.5f} {gap:+10.5f}")
    print()
    print("  negative gap = observed below predicted = overconfident in this region")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
