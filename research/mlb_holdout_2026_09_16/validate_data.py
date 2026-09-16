"""Real-data validation of the ingested snapshot and derived PA dataset.

Checks the things a synthetic fixture cannot establish: source completeness
against an independent authority (MLB StatsAPI schedule), date coverage,
duplicate behavior, incomplete/truncated PA behavior, pitcher-attribution
eligibility, and outcome-category frequencies.

Reads only persisted artifacts. Writes a JSON report. Changes nothing.

HOLDOUT BLINDNESS. Structural QC (coverage, counts, chronology, duplicates,
provenance, completion status, attribution eligibility, prior-history depth)
runs over the WHOLE range, including holdout dates: it is required to show the
dataset is contract-valid at all, and none of it derives from a realized target
outcome. Anything that DOES derive from the realized target -- the
pa_outcome_category / pa_outcome_detailed distributions -- is aggregated ONLY
over records with game_date < --outcome-blind-from. Holdout outcome counts are
never read, never summed, and never written to the report.
"""

import argparse
import collections
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from paths import (  # noqa: E402
    get_mlb_normalized_plate_appearance_dir,
    get_mlb_normalized_statcast_pitch_dir,
    get_mlb_snapshot_dir,
)
from mlb import RATE_CATEGORIES, INCOMPLETE_TERMINAL_EVENTS  # noqa: E402


def load_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--pa-dataset-id", required=True)
    parser.add_argument("--schedule-json", required=True)
    parser.add_argument("--outcome-blind-from", required=True,
                        help="ISO date; realized-outcome aggregation is "
                             "restricted to game_date strictly before this")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = {}

    # ---- pitch layer -----------------------------------------------------
    pitch_path = get_mlb_normalized_statcast_pitch_dir() / f"{args.snapshot_id}.jsonl.gz"
    per_date_games = collections.defaultdict(set)
    game_types = collections.Counter()
    pitch_count = 0
    pitch_ids = set()
    duplicate_pitch_ids = 0
    null_events_on_nonterminal = 0
    for record in load_jsonl_gz(pitch_path):
        pitch_count += 1
        per_date_games[record["game_date"]].add(record["source_game_id"])
        game_types[record["game_type"]] += 1
        pid = record["rsb_pitch_id"]
        if pid in pitch_ids:
            duplicate_pitch_ids += 1
        pitch_ids.add(pid)
    del pitch_ids

    report["pitch_layer"] = {
        "normalized_pitch_count": pitch_count,
        "distinct_game_dates": len(per_date_games),
        "distinct_games": sum(len(v) for v in per_date_games.values()),
        "game_type_counts": dict(game_types),
        "duplicate_rsb_pitch_id_count": duplicate_pitch_ids,
        "first_game_date": min(per_date_games),
        "last_game_date": max(per_date_games),
    }

    # ---- source completeness vs independent schedule authority -----------
    schedule = json.loads(Path(args.schedule_json).read_text())
    start, end = min(per_date_games), max(per_date_games)
    expected_dates = {d: set(str(g) for g in pks)
                      for d, pks in schedule.items() if start <= d <= end}
    missing_games, extra_games, missing_dates = {}, {}, []
    for day, expected in sorted(expected_dates.items()):
        observed = per_date_games.get(day, set())
        if not observed:
            missing_dates.append(day)
        miss = expected - observed
        extra = observed - expected
        if miss:
            missing_games[day] = sorted(miss)
        if extra:
            extra_games[day] = sorted(extra)
    expected_total = sum(len(v) for v in expected_dates.values())
    observed_total = sum(len(per_date_games.get(d, set())) for d in expected_dates)

    report["source_completeness"] = {
        "authority": "MLB StatsAPI schedule, gameType=R, detailedState=Final",
        "expected_final_game_count": expected_total,
        "observed_game_count_in_range": observed_total,
        "game_coverage_fraction": (observed_total / expected_total) if expected_total else None,
        "dates_with_scheduled_finals_but_no_pitch_data": missing_dates,
        "missing_game_count": sum(len(v) for v in missing_games.values()),
        "missing_games_by_date": missing_games,
        "unexpected_game_count": sum(len(v) for v in extra_games.values()),
        "unexpected_games_by_date": dict(list(extra_games.items())[:20]),
    }
    del per_date_games

    # ---- PA layer --------------------------------------------------------
    pa_path = get_mlb_normalized_plate_appearance_dir() / f"{args.pa_dataset_id}.jsonl.gz"
    status = collections.Counter()
    categories = collections.Counter()
    detailed = collections.Counter()
    terminal_raw_on_incomplete = collections.Counter()
    eligible = collections.Counter()
    multi_pitcher = 0
    pa_total = 0
    pa_ids = set()
    dup_pa_ids = 0
    per_month = collections.Counter()
    window_counts = collections.Counter()
    pitches_per_pa = collections.Counter()
    zero_batter_history = 0
    zero_pitcher_history = 0
    for record in load_jsonl_gz(pa_path):
        pa_total += 1
        pid = record["rsb_pa_id"]
        if pid in pa_ids:
            dup_pa_ids += 1
        pa_ids.add(pid)
        status[record["pa_status"]] += 1
        per_month[record["game_date"][:7]] += 1
        window_counts["development" if record["game_date"] < args.outcome_blind_from
                      else "holdout"] += 1
        eligible[record["pitcher_rate_eligible"]] += 1
        if len(record["source_pitcher_ids"]) > 1:
            multi_pitcher += 1
        pitches_per_pa[len(record["source_pitch_ids"])] += 1
        if record["pa_status"] == "completed":
            # Realized-target aggregation is development-only (holdout blindness).
            if record["game_date"] < args.outcome_blind_from:
                categories[record["pa_outcome_category"]] += 1
                detailed[record["pa_outcome_detailed"]] += 1
        else:
            terminal_raw_on_incomplete[record["terminal_pa_event_raw"]] += 1
        if record["prior_batter_pa_count"] == 0:
            zero_batter_history += 1
        if record["prior_pitcher_pa_count"] == 0:
            zero_pitcher_history += 1
    del pa_ids

    completed = status["completed"]
    dev_completed = sum(categories.values())
    report["pa_layer"] = {
        "pa_count": pa_total,
        "duplicate_rsb_pa_id_count": dup_pa_ids,
        "status_counts": dict(status),
        "incomplete_fraction": (status["incomplete"] / pa_total) if pa_total else None,
        "terminal_raw_on_incomplete": {str(k): v for k, v in terminal_raw_on_incomplete.items()},
        "recognized_incomplete_markers": sorted(INCOMPLETE_TERMINAL_EVENTS),
        "pitcher_rate_eligible_counts": {str(k): v for k, v in eligible.items()},
        "multi_pitcher_pa_count": multi_pitcher,
        "pa_count_by_month": dict(sorted(per_month.items())),
        "pitches_per_pa_distribution": dict(sorted(pitches_per_pa.items())),
        "pa_count_by_window": dict(window_counts),
        "zero_prior_batter_history_pa_count": zero_batter_history,
        "zero_prior_pitcher_history_pa_count": zero_pitcher_history,
    }
    report["outcome_frequencies_development_only"] = {
        "scope": f"game_date < {args.outcome_blind_from} (holdout outcomes not read)",
        "completed_pa_count_whole_range": completed,
        "completed_pa_count_development": dev_completed,
        "category_counts": {c: categories.get(c, 0) for c in RATE_CATEGORIES},
        "category_frequencies": {
            c: (categories.get(c, 0) / dev_completed if dev_completed else None)
            for c in RATE_CATEGORIES
        },
        "categories_never_observed_in_development": [
            c for c in RATE_CATEGORIES if categories.get(c, 0) == 0
        ],
        "detailed_counts": dict(detailed.most_common()),
    }

    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_completeness"},
                     indent=2)[:4000])
    sc = report["source_completeness"]
    print(json.dumps({k: v for k, v in sc.items()
                      if k not in ("missing_games_by_date", "unexpected_games_by_date")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
