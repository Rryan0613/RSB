# MLB Real-Data Evaluation — Research Package (2026-09-16)

Research-only evidence package for the first run of the frozen v0.3.4 evaluator
against real MLB data. **Nothing here is production code**, nothing here is
imported by `src/`, and nothing here changes a model default.

> ## ⚠ The 2026-08-12 → 2026-09-15 holdout is SPENT
> It has been opened and scored. It remains valid for **audit and reproduction
> of this experiment**, but must never again be presented as a pristine
> confirmatory holdout for choices influenced by these results. Future
> confirmatory selection requires new untouched data / a new pre-registered
> temporal window. See `FINDINGS.md` §0.

## Read in this order

| file | what it is |
|---|---|
| `FREEZE.md` | Pre-registration. Stages 1–3 were written **before** any holdout metric was inspected; stage 4 records what happened after. Includes the dataset-start assessment (1.6), the exclusion rationale (1.7) and the frozen exclusion set with every key (1.8). |
| `stage2_dataset_identity.md` | Dataset identity, hashes, source-completeness reconciliation, history depth entering the holdout. |
| `stage3_frozen_configs.md` | The development-only strength sweep and the frozen confirmatory configuration list. |
| `FINDINGS.md` | Results, diagnostics, conclusions, corrections, architectural gaps. |

## Scripts, in execution order

| script | role |
|---|---|
| `download_savant.py` | Upstream acquisition: scripted HTTP GETs against the public Baseball Savant CSV endpoint, in bounded ≤3-day `game_date` chunks, with a row-cap truncation check. |
| `freeze_exclusions.py` | Freezes the mid-PA batter-substitution exclusion set. Outcome-blind: never reads `events`. |
| `build_dataset.py` | Projects to RSB-mapped columns, concatenates to one CSV, applies the frozen exclusion, then hands it to the **existing v0.3.1 ingestion path** and derives the v0.3.2 PA dataset. |
| `preflight_audit.py` | Read-only diagnostic. Detects the conditions v0.3.2 fails closed on, without raising, so their frequency can be characterized. |
| `validate_data.py` | Structural QC over the whole range; realized-outcome aggregation hard-filtered to development. |
| `history_depth.py` | Development-only prior-history depth entering the holdout. |
| `run_evaluation.py` | `--mode dev-sweep` (development-only, 16 configs) and `--mode confirm` (the single confirmatory run). |
| `analyze_report.py`, `overconfidence_view.py` | Presentation only. Compute no new metric, select no winner. |

## Reports (`reports/`)

All evaluation reports are **aggregate**. Verified to contain no `rsb_pa_id`,
`source_game_id`, `at_bat_number`, `batter_id` or `pitcher_id`; `game_date`
appears only as window boundary metadata. 136,214 scored plate appearances
compress to 12 category rows + 6 month rows + 11 reliability bins per config.

| file | contents |
|---|---|
| `confirm.json` | The confirmatory run: 6 configs × {tuning, holdout}. |
| `dev_sweep.json` | Development-only strength sweep: 16 configs × {full}. |
| `season_validation.json` | Structural QC + schedule reconciliation. |
| `exclusion_freeze.json` | The 21 excluded PAs (row-level **by design** — this is the frozen exclusion evidence). |
| `history_depth.json` | Prior-history percentiles, development only. |
| `preflight_scale.json` | Contract-condition audit over a 253k-pitch sample. |
| `statcast_manifest.json`, `pa_manifest.json` | Copies of the immutable artifact manifests. |
| `schedule_final_2026.json` | The independent MLB StatsAPI reference used for completeness checking. |

## Deliberately NOT in this package

Downloaded Savant CSV chunks (438 MB), normalized pitch datasets, derived PA
datasets, `data/mlb/` (gitignored), logs containing row-level data, caches and
temporary files. The immutable data artifacts live under gitignored
`data/mlb/`; this package carries their **identities and hashes**, not their
bytes.

## Reproducing

```
python3 download_savant.py    --start 2026-03-25 --end 2026-09-15 --width 3 --out-dir <chunks>
python3 freeze_exclusions.py  --chunk-dir <chunks> --start 2026-03-25 --end 2026-09-15 \
                              --split 2026-08-12 --out exclusion_freeze.json
python3 build_dataset.py      --chunk-dir <chunks> --start 2026-03-25 --end 2026-09-15 --work-dir <work>
python3 validate_data.py      --snapshot-id <id> --pa-dataset-id <id> \
                              --schedule-json <schedule> --outcome-blind-from 2026-08-12 --out <out>
python3 run_evaluation.py     --pa-dataset-id <id> --mode dev-sweep --split 2026-08-12 --out <out>
python3 run_evaluation.py     --pa-dataset-id <id> --mode confirm   --split 2026-08-12 --out <out>
```

Scripts take all paths as arguments and contain no user-specific absolute paths,
no credentials and no destructive file operations. Data locations resolve
through the existing `src/paths.py` (`RSB_MLB_DATA_DIR` honoured).

## Known reproducibility limitations

Documented rather than silently "fixed", so the committed source matches what
actually produced the evidence.

1. **Snapshot hashes are not reproducible from a fresh download alone.**
   `snapshot_id` embeds the ingestion timestamp by v0.3.1 design, and
   `raw_content_sha256` is taken over the *projected, concatenated, exclusion-
   filtered* CSV — not over the raw Savant responses. A re-run reproduces the
   same **PA-level content** and the same metrics, but different snapshot
   identity strings.

2. **Upstream data is not pinned.** Baseball Savant may revise historical rows.
   A future download of the same date range is not guaranteed byte-identical.

3. **`--mode dev-sweep` reads the full PA dataset file**, which physically
   contains holdout rows, and discards them during parsing
   (`if record["game_date"] >= args.split: continue`). It never scores them and
   never passes them to the evaluator, and `split_date=None` means no holdout
   window is constructed. The blindness is enforced at load, not by a separate
   development-only artifact — worth knowing when auditing the guarantee.

4. **`validate_data.py` holds the full PA id set in memory** for duplicate
   detection; it is not streaming-safe for multi-season data.

5. **No random seeds are involved.** Every step is deterministic, so no seed
   needs pinning.
