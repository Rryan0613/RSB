"""Read-only pre-flight audit of normalized pitch records.

v0.3.2's derivation fails the WHOLE batch closed on the first contradiction, so
it cannot answer "how many plate appearances in this season are affected, and by
what?". This script answers that by detecting the same conditions without
raising, purely for characterization.

It is a DIAGNOSTIC, not a second implementation of the contract. It never writes
a PA record and nothing downstream consumes its output. The authoritative
derivation remains group_pitches_into_plate_appearances / the v0.3.2 contract.
"""

import argparse
import collections
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from paths import get_mlb_normalized_statcast_pitch_dir  # noqa: E402
from mlb import TERMINAL_EVENT_TAXONOMY, INCOMPLETE_TERMINAL_EVENTS  # noqa: E402

CONTEXT_FIELDS = (
    "game_date", "game_year", "game_type", "home_team", "away_team",
    "inning", "inning_half", "snapshot_id", "source_provider",
    "normalized_schema_version",
)


def audit_group(group):
    """Return a list of (condition, detail) for one (game, at_bat) group."""
    group = sorted(group, key=lambda r: r["pitch_number"])
    problems = []

    numbers = [r["pitch_number"] for r in group]
    if numbers != list(range(1, len(group) + 1)):
        problems.append(("pitch_number_not_contiguous", str(numbers)))

    for field in CONTEXT_FIELDS:
        values = {r[field] for r in group}
        if len(values) > 1:
            problems.append((f"context_mismatch:{field}", str(sorted(map(str, values)))))

    batters = {r["batter_id"] for r in group}
    if len(batters) > 1:
        problems.append(("batter_id_varies", str(sorted(batters))))
    stands = {r["batter_stands"] for r in group}
    if len(stands) > 1:
        problems.append(("batter_stands_varies", str(sorted(stands))))

    seen, order = set(), []
    for r in group:
        if r["pitcher_id"] not in seen:
            seen.add(r["pitcher_id"])
            order.append(r["pitcher_id"])
    positions = {}
    reverted = False
    last = None
    for r in group:
        pid = r["pitcher_id"]
        if last is not None and pid != last and pid in positions:
            reverted = True
        positions[pid] = True
        last = pid
    if reverted:
        problems.append(("pitcher_reverts", str(order)))
    elif len(order) > 1:
        problems.append(("pitcher_substitution_forward_only", str(order)))

    throws = collections.defaultdict(set)
    for r in group:
        throws[r["pitcher_id"]].add(r["pitcher_throws"])
    for pid, values in throws.items():
        if len(values) > 1:
            problems.append(("pitcher_throws_inconsistent", f"{pid}:{sorted(values)}"))

    for r in group[:-1]:
        if r["pa_event_raw"] is not None:
            problems.append(("event_on_non_terminal_pitch",
                             f"p#{r['pitch_number']}={r['pa_event_raw']}"))
    terminal = group[-1]["pa_event_raw"]
    if terminal is not None and terminal not in TERMINAL_EVENT_TAXONOMY \
            and terminal not in INCOMPLETE_TERMINAL_EVENTS:
        problems.append(("unrecognized_terminal_event", str(terminal)))

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    path = get_mlb_normalized_statcast_pitch_dir() / f"{args.snapshot_id}.jsonl.gz"
    groups = collections.defaultdict(list)
    total_pitches = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            r = json.loads(line)
            total_pitches += 1
            groups[(r["source_game_id"], r["at_bat_number"])].append(r)

    counts = collections.Counter()
    examples = collections.defaultdict(list)
    affected_games = collections.defaultdict(set)
    affected_pas = collections.defaultdict(set)
    fatal_pa_keys = set()
    FATAL = {"pitch_number_not_contiguous", "batter_id_varies", "batter_stands_varies",
             "pitcher_reverts", "pitcher_throws_inconsistent",
             "event_on_non_terminal_pitch", "unrecognized_terminal_event"}

    for key, group in groups.items():
        for condition, detail in audit_group(group):
            base = condition.split(":")[0]
            counts[condition] += 1
            affected_games[condition].add(key[0])
            affected_pas[condition].add(key)
            if len(examples[condition]) < 5:
                examples[condition].append({
                    "source_game_id": key[0], "at_bat_number": key[1],
                    "game_date": group[0]["game_date"], "detail": detail})
            if base in FATAL or condition.startswith("context_mismatch"):
                fatal_pa_keys.add(key)

    report = {
        "snapshot_id": args.snapshot_id,
        "total_pitches": total_pitches,
        "total_pa_groups": len(groups),
        "condition_counts": dict(counts.most_common()),
        "condition_affected_pa_counts": {k: len(v) for k, v in affected_pas.items()},
        "condition_affected_game_counts": {k: len(v) for k, v in affected_games.items()},
        "examples": {k: v for k, v in examples.items()},
        "fatal_pa_count": len(fatal_pa_keys),
        "fatal_pa_fraction": len(fatal_pa_keys) / len(groups) if groups else None,
        "fatal_game_count": len({k[0] for k in fatal_pa_keys}),
        "fatal_pa_keys": sorted([[g, a] for g, a in fatal_pa_keys],
                                key=lambda x: (int(x[0]), x[1])),
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    printable = {k: v for k, v in report.items() if k != "fatal_pa_keys"}
    print(json.dumps(printable, indent=2)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
