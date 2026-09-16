"""Acquire 2026 MLB regular-season pitch-level Statcast CSV chunks.

Research support script for the MLB real-data evaluation sprint. It performs
the network acquisition step only: it writes plain Baseball Savant Statcast
Search CSV exports to a local directory, exactly as a browser download would.

It deliberately lives outside src/ and imports nothing from RSB. v0.3.1 owns
ingestion and explicitly performs no network access; this script hands it an
already-downloaded local CSV, which is the input contract load_statcast_export
was built for.

Chunks are non-overlapping closed date ranges. Savant's CSV export truncates
at 25,000 rows, so chunk width is chosen to stay far below that and every
chunk is checked against the cap after download.
"""

import argparse
import csv
import io
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

SAVANT_CSV_ENDPOINT = "https://baseballsavant.mlb.com/statcast_search/csv"
ROW_CAP = 25000

# Fixed query parameters shared by every chunk. Only the two date bounds vary.
BASE_QUERY = {
    "all": "true",
    "type": "details",
    "hfGT": "R|",          # regular season only
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "player_event_sort": "api_p_release_speed",
    "sort_order": "desc",
}


def build_url(start_date: str, end_date: str) -> str:
    params = dict(BASE_QUERY)
    params["game_date_gt"] = start_date
    params["game_date_lt"] = end_date
    return f"{SAVANT_CSV_ENDPOINT}?{urllib.parse.urlencode(params)}"


def daterange_chunks(start: date, end: date, width: int):
    cursor = start
    while cursor <= end:
        stop = min(cursor + timedelta(days=width - 1), end)
        yield cursor.isoformat(), stop.isoformat()
        cursor = stop + timedelta(days=1)


def fetch(url: str, attempts: int = 4, timeout: int = 300) -> bytes:
    last = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "RSB-research/0.3.4 (+local evaluation sprint)"}
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                return response.read()
        except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"failed after {attempts} attempts: {url}: {last}")


def count_rows(raw: bytes) -> int:
    text = raw.decode("utf-8-sig")
    return sum(1 for _ in csv.DictReader(io.StringIO(text)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--width", type=int, default=3)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    chunks = list(daterange_chunks(start, end, args.width))
    print(f"{len(chunks)} chunks of up to {args.width} day(s): {args.start}..{args.end}", flush=True)

    truncation_suspects = []
    for index, (chunk_start, chunk_end) in enumerate(chunks, start=1):
        target = out_dir / f"chunk_{chunk_start}_{chunk_end}.csv"
        if target.exists() and target.stat().st_size > 0:
            print(f"[{index}/{len(chunks)}] {chunk_start}..{chunk_end} cached", flush=True)
            continue
        url = build_url(chunk_start, chunk_end)
        raw = fetch(url)
        rows = count_rows(raw)
        if rows >= ROW_CAP:
            truncation_suspects.append((chunk_start, chunk_end, rows))
        target.write_bytes(raw)
        print(
            f"[{index}/{len(chunks)}] {chunk_start}..{chunk_end} "
            f"rows={rows} bytes={len(raw)}",
            flush=True,
        )
        time.sleep(1.0)

    if truncation_suspects:
        print("TRUNCATION SUSPECTS (rows >= cap):", truncation_suspects, file=sys.stderr)
        return 2
    print("download complete, no chunk hit the row cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
