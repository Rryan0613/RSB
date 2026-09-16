"""Quantify prior-history depth entering the holdout.

Development-only and outcome-blind: it reads `prior_*_pa_count` (pre-PA state)
and `game_date`, never a realized outcome. The prior state attached to plate
appearances on the LAST development date is, by construction, the history depth
carried into the first holdout date.
"""

import argparse
import gzip
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from paths import get_mlb_normalized_plate_appearance_dir  # noqa: E402

FIELDS = ("prior_batter_pa_count", "prior_pitcher_pa_count", "prior_league_pa_count")


def percentiles(values):
    if not values:
        return None
    ordered = sorted(values)
    def pct(p):
        idx = min(len(ordered) - 1, max(0, int(round(p / 100 * (len(ordered) - 1)))))
        return ordered[idx]
    return {
        "n": len(ordered), "min": ordered[0], "p10": pct(10), "p25": pct(25),
        "median": pct(50), "p75": pct(75), "p90": pct(90), "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pa-dataset-id", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    path = get_mlb_normalized_plate_appearance_dir() / f"{args.pa_dataset_id}.jsonl.gz"

    last_dev_date = None
    by_month = {}
    last_day = []
    dev_total = 0
    zero_batter_by_month = {}

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            r = json.loads(line)
            if r["game_date"] >= args.split:
                continue          # development-only, hard filter
            dev_total += 1
            month = r["game_date"][:7]
            by_month.setdefault(month, []).append(r["prior_batter_pa_count"])
            if r["prior_batter_pa_count"] == 0:
                zero_batter_by_month[month] = zero_batter_by_month.get(month, 0) + 1
            if last_dev_date is None or r["game_date"] > last_dev_date:
                last_dev_date = r["game_date"]

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            r = json.loads(line)
            if r["game_date"] == last_dev_date:
                last_day.append(r)

    report = {
        "scope": f"development only, game_date < {args.split}",
        "development_pa_count": dev_total,
        "last_development_date": last_dev_date,
        "plate_appearances_on_last_development_date": len(last_day),
        "history_depth_entering_holdout": {
            field: percentiles([r[field] for r in last_day]) for field in FIELDS
        },
        "monthly_prior_batter_pa_count": {
            month: percentiles(values) for month, values in sorted(by_month.items())
        },
        "zero_prior_batter_history_pa_by_month": dict(sorted(zero_batter_by_month.items())),
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"development PAs: {dev_total:,}   last development date: {last_dev_date}")
    print(f"PAs on last development date: {len(last_day):,}")
    print()
    print("History depth entering the holdout (prior state on the last development date):")
    print(f"  {'field':28s} {'n':>7s} {'min':>6s} {'p10':>6s} {'p25':>6s} "
          f"{'med':>7s} {'p75':>7s} {'p90':>7s} {'max':>8s} {'mean':>9s}")
    for field in FIELDS:
        s = report["history_depth_entering_holdout"][field]
        print(f"  {field:28s} {s['n']:7d} {s['min']:6d} {s['p10']:6d} {s['p25']:6d} "
              f"{s['median']:7d} {s['p75']:7d} {s['p90']:7d} {s['max']:8d} {s['mean']:9.1f}")
    print()
    print("Monthly warm-up of prior_batter_pa_count (development only):")
    print(f"  {'month':9s} {'n':>8s} {'median':>8s} {'p25':>7s} {'p75':>7s} {'zero-history PAs':>18s}")
    for month, s in report["monthly_prior_batter_pa_count"].items():
        print(f"  {month:9s} {s['n']:8d} {s['median']:8d} {s['p25']:7d} {s['p75']:7d} "
              f"{report['zero_prior_batter_history_pa_by_month'].get(month,0):18d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
