"""Freeze the exact mid-PA batter-substitution exclusion set.

Runs on the downloaded CSV chunks BEFORE ingestion and records, for the frozen
record: the rule, every excluded (source_game_id, at_bat_number) key, its
deterministic rsb_pa_id, its game_date, and the development/holdout split of the
excluded records.

Outcome-blind by construction: the `events` column is never read. Detection uses
only `batter` and `stand` structure within a (game_pk, at_bat_number) group, so
no realized outcome and no model performance can influence the exclusion.
"""

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mlb import build_rsb_pa_id  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-dir", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    batters = collections.defaultdict(set)
    stands = collections.defaultdict(set)
    dates = {}
    pitch_rows = collections.Counter()
    total_rows = 0

    for path in sorted(Path(args.chunk_dir).glob("chunk_*.csv")):
        _, chunk_start, chunk_end = path.stem.split("_", 2)
        if not (chunk_start >= args.start and chunk_end <= args.end):
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if not (args.start <= row["game_date"] <= args.end):
                    continue
                total_rows += 1
                key = (row["game_pk"], row["at_bat_number"])
                batters[key].add(row["batter"])
                stands[key].add(row["stand"])
                dates[key] = row["game_date"]
                pitch_rows[key] += 1

    excluded = sorted(
        {k for k, v in batters.items() if len(v) > 1}
        | {k for k, v in stands.items() if len(v) > 1},
        key=lambda k: (dates[k], int(k[0]), int(k[1])),
    )

    records = []
    window_counts = collections.Counter()
    pitch_counts = collections.Counter()
    for key in excluded:
        game_pk, at_bat = key
        window = "development" if dates[key] < args.split else "holdout"
        window_counts[window] += 1
        pitch_counts[window] += pitch_rows[key]
        records.append({
            "source_game_id": game_pk,
            "at_bat_number": int(at_bat),
            "rsb_pa_id": build_rsb_pa_id(game_pk, int(at_bat)),
            "game_date": dates[key],
            "window": window,
            "pitch_row_count": pitch_rows[key],
            "distinct_batter_ids": sorted(batters[key]),
            "distinct_stands": sorted(stands[key]),
        })

    report = {
        "rule": (
            "Drop every (source_game_id, at_bat_number) plate-appearance group "
            "whose pitch rows carry more than one distinct `batter` id or more "
            "than one distinct `stand` value."
        ),
        "reason": (
            "v0.3.2 s4 fails the whole derivation closed on a plate appearance "
            "containing multiple batter identities and explicitly defers "
            "resolving attribution to a separately scoped future change. These "
            "are genuine MLB events (a pinch hitter entering mid-count, "
            "typically answering a mid-PA pitching change), not corrupt data. "
            "This sprint does not change the contract, so the affected plate "
            "appearances are dropped pre-ingestion and reported as coverage loss."
        ),
        "outcome_independence": (
            "The `events` column is never read by the detector. The rule depends "
            "only on batter/stand structure within a group. No realized outcome, "
            "no metric, and no model performance influenced this exclusion, and "
            "the identical rule is applied to development and holdout dates."
        ),
        "declared_range": {"start_date": args.start, "end_date": args.end},
        "development_holdout_split_date": args.split,
        "total_source_pitch_rows_in_range": total_rows,
        "total_pa_groups_in_range": len(dates),
        "excluded_pa_count": len(excluded),
        "excluded_pa_fraction_of_range": len(excluded) / len(dates) if dates else None,
        "excluded_pa_count_by_window": dict(window_counts),
        "excluded_pitch_row_count_by_window": dict(pitch_counts),
        "excluded_plate_appearances": records,
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    printable = dict(report)
    printable["excluded_plate_appearances"] = f"<{len(records)} records, see {args.out}>"
    print(json.dumps(printable, indent=2))
    print()
    print(f"{'game_date':12s} {'game_pk':10s} {'ab':>4s} {'window':12s} "
          f"{'pitches':>8s}  batters -> stands")
    for r in records:
        print(f"{r['game_date']:12s} {r['source_game_id']:10s} {r['at_bat_number']:4d} "
              f"{r['window']:12s} {r['pitch_row_count']:8d}  "
              f"{r['distinct_batter_ids']} {r['distinct_stands']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
