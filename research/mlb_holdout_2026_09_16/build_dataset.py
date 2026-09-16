"""Assemble downloaded Savant chunks into ONE immutable RSB v0.3.1 snapshot,
then derive the v0.3.2 plate-appearance dataset from it.

Single-snapshot by construction: the chunk CSVs are concatenated into one CSV
file and handed to create_statcast_snapshot once. No multi-snapshot merge is
performed anywhere, so v0.3.2 §11's single-source-snapshot gate applies
unmodified.

Column projection: the Savant export carries ~118 columns; RSB maps 33
(statcast_import.EXPECTED_SOURCE_COLUMNS). This script projects the CSV to the
mapped columns before ingestion because holding every column for a full season
does not fit in this machine's memory. The projection is deterministic and the
retained column list is recorded in declared_query.

Mid-PA batter-substitution exclusion: real MLB data contains plate appearances
whose pitch rows carry more than one batter identity (a pinch hitter entering
mid-count, typically answering a mid-PA pitching change). v0.3.2 s4 fails the
WHOLE derivation closed on this and explicitly defers resolving it to "a
separately scoped future change". This sprint does not change that contract, so
the affected plate appearances are dropped from the CSV before ingestion and the
exact dropped keys are recorded in declared_query and reported as a coverage
loss. The rule is structural (more than one distinct `batter` or `stand` within
one (game_pk, at_bat_number)), never outcome-dependent, and is applied
identically across development and holdout dates. Every OTHER fail-closed
condition is deliberately left to fail, so a new anomaly is never hidden.
"""

import argparse
import collections
import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mlb.statcast_import import EXPECTED_SOURCE_COLUMNS  # noqa: E402
from mlb.statcast_snapshot import create_statcast_snapshot  # noqa: E402
from mlb import (  # noqa: E402
    attach_prior_outcome_rates,
    create_plate_appearance_dataset,
    group_pitches_into_plate_appearances,
)

ENDPOINT = "https://baseballsavant.mlb.com/statcast_search/csv"
BASE_QUERY = {
    "all": "true",
    "type": "details",
    "hfGT": "R|",
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "player_event_sort": "api_p_release_speed",
    "sort_order": "desc",
}


def chunk_files(chunk_dir: Path, start: str, end: str):
    """Chunk CSVs whose whole date range lies inside [start, end], in order."""
    selected = []
    for path in sorted(chunk_dir.glob("chunk_*.csv")):
        stem = path.stem                       # chunk_<start>_<end>
        _, chunk_start, chunk_end = stem.split("_", 2)
        if chunk_start >= start and chunk_end <= end:
            selected.append((chunk_start, chunk_end, path))
    return selected


def find_multi_batter_pas(selected, start: str, end: str) -> list:
    """Keys of (game_pk, at_bat_number) groups carrying >1 batter or stand.

    Streaming and read-only. Detection mirrors the condition v0.3.2 s4 fails
    closed on; it does not reimplement any other part of the contract.
    """
    batters = collections.defaultdict(set)
    stands = collections.defaultdict(set)
    for _, _, path in selected:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if not (start <= row["game_date"] <= end):
                    continue
                key = (row["game_pk"], row["at_bat_number"])
                batters[key].add(row["batter"])
                stands[key].add(row["stand"])
    keys = {k for k, v in batters.items() if len(v) > 1}
    keys |= {k for k, v in stands.items() if len(v) > 1}
    return sorted(keys, key=lambda k: (int(k[0]), int(k[1])))


def concatenate(selected, start: str, end: str, out_path: Path,
                excluded_keys=frozenset()) -> dict:
    """Project to mapped columns and concatenate into one CSV; report stats."""
    columns = [c for c in sorted(EXPECTED_SOURCE_COLUMNS)]
    written = 0
    skipped_out_of_range = 0
    skipped_excluded_rows = 0
    seen_header = None
    missing_columns = set()

    with out_path.open("w", newline="", encoding="utf-8") as sink:
        writer = csv.DictWriter(sink, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for chunk_start, chunk_end, path in selected:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if seen_header is None:
                    seen_header = reader.fieldnames
                    missing_columns = set(columns) - set(reader.fieldnames or [])
                for row in reader:
                    if not (start <= row["game_date"] <= end):
                        skipped_out_of_range += 1
                        continue
                    if (row["game_pk"], row["at_bat_number"]) in excluded_keys:
                        skipped_excluded_rows += 1
                        continue
                    writer.writerow({c: row.get(c, "") for c in columns})
                    written += 1
    return {
        "retained_columns": columns,
        "source_header_column_count": len(seen_header or []),
        "mapped_columns_absent_from_source": sorted(missing_columns),
        "rows_written": written,
        "rows_skipped_out_of_range": skipped_out_of_range,
        "rows_skipped_multi_batter_pa": skipped_excluded_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-dir", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--concat-only", action="store_true")
    args = parser.parse_args()

    chunk_dir = Path(args.chunk_dir)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    selected = chunk_files(chunk_dir, args.start, args.end)
    if not selected:
        print("no chunk files selected", file=sys.stderr)
        return 1
    print(f"selected {len(selected)} chunks "
          f"{selected[0][0]}..{selected[-1][1]}", flush=True)

    excluded = find_multi_batter_pas(selected, args.start, args.end)
    print(f"mid-PA batter-substitution plate appearances excluded: {len(excluded)}",
          flush=True)
    for key in excluded:
        print(f"    excluded PA game_pk={key[0]} at_bat_number={key[1]}", flush=True)

    combined = work_dir / f"combined_{args.start}_{args.end}.csv"
    stats = concatenate(selected, args.start, args.end, combined,
                        excluded_keys=set(excluded))
    print(json.dumps({k: v for k, v in stats.items()
                      if k != "retained_columns"}, indent=2), flush=True)
    print(f"combined csv: {combined} "
          f"({combined.stat().st_size/1e6:.1f} MB)", flush=True)
    if args.concat_only:
        return 0

    declared_query = {
        "endpoint": ENDPOINT,
        "base_parameters": BASE_QUERY,
        "acquisition": "scripted HTTP GET of the public Statcast Search CSV export",
        "acquisition_script": "research/mlb_holdout_2026_09_16/download_savant.py",
        "chunking": "non-overlapping closed game_date ranges of up to 3 days",
        "chunk_ranges": [[s, e] for s, e, _ in selected],
        "post_download_transform": (
            "projected to the 33 columns RSB maps "
            "(statcast_import.EXPECTED_SOURCE_COLUMNS) and concatenated into "
            "one CSV; no row filtering beyond the declared date range"
        ),
        "retained_columns": stats["retained_columns"],
        "mapped_columns_absent_from_source": stats["mapped_columns_absent_from_source"],
        "game_type_filter": "R (regular season) via hfGT",
        "excluded_multi_batter_plate_appearances": [
            {"source_game_id": key[0], "at_bat_number": int(key[1])}
            for key in excluded
        ],
        "exclusion_rationale": (
            "v0.3.2 s4 fails closed on a plate appearance whose pitch rows carry "
            "more than one batter identity and defers resolving it; these PAs are "
            "dropped pre-ingestion rather than changing the contract. Structural "
            "rule, never outcome-dependent, applied identically to all dates."
        ),
    }

    print("creating statcast snapshot...", flush=True)
    manifest = create_statcast_snapshot(
        combined,
        declared_query=declared_query,
        requested_date_range={"start_date": args.start, "end_date": args.end},
    )
    print(json.dumps(manifest, indent=2)[:1500], flush=True)
    (work_dir / "statcast_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("regrouping into plate appearances...", flush=True)
    import gzip
    from paths import get_mlb_normalized_statcast_pitch_dir
    normalized_path = (get_mlb_normalized_statcast_pitch_dir()
                       / f"{manifest['snapshot_id']}.jsonl.gz")
    with gzip.open(normalized_path, "rt", encoding="utf-8") as handle:
        normalized = [json.loads(line) for line in handle]
    print(f"normalized records: {len(normalized)}", flush=True)

    pa_manifest = create_plate_appearance_dataset(manifest, normalized)
    print(json.dumps(pa_manifest, indent=2)[:1500], flush=True)
    (work_dir / "pa_manifest.json").write_text(
        json.dumps(pa_manifest, indent=2) + "\n", encoding="utf-8")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
