# Changelog

## v0.1.9.0
- Added `src/backtest_report.py` with a pure in-memory reporting layer: `build_backtest_report(rows) -> dict`.
- Accepts already-loaded `ReplayRow` objects; no database, filesystem, or external I/O.
- Evaluates each row as a selected-outcome binary prediction: `model_probability` vs. `(1 if selection == actual_label else 0)`. Correctness is recomputed from the validated `selection` and `actual_label` fields; `row.correct` is not used for scoring.
- Skips rows with missing/invalid `market`, `selection`, `actual_label`, or `model_probability` out of `[0, 1]`; records a warning and skipped count.
- Computes overall and per-market: `correct_count`, `accuracy`, `mean_selected_brier_score`, `mean_selected_log_loss` using primitives from `src/backtest.py`.
- Returns `None` for all metrics when no evaluable rows are present.
- `by_market` includes all markets with a valid non-empty name, even if all rows for that market are skipped; those entries show `evaluated_rows=0`, `skipped_rows=total_rows`, and `None` for all metric fields.
- Report includes explicit notes: metrics are selected-outcome binary, not full three-way soccer calibration; full calibration requires complete probability distributions; report is retrospective evaluation plumbing and does not produce betting recommendations; passing metrics does not mean the model is live-betting-ready.
- Added `tests/test_backtest_report.py` with tests covering: empty input; one correct row (known-value brier and log-loss); one incorrect row (known-value brier and log-loss); mixed rows (mean correctness); market grouping; skipped rows for None probability, out-of-range probability, empty selection, empty actual_label; warning/notes content; no betting recommendation language in report keys; no banned imports (sqlite3, database, json); `model_probability` used, not a `predicted_probability` field; no filesystem or database access needed; recompute-correctness contract (matching labels scored correct even when `row.correct=False`; mismatched labels scored incorrect even when `row.correct=True`); all-skipped market appears in `by_market` with zero evaluated rows.
- Updated model version to `0.1.9.0`.

## v0.1.8.9
- Hardened `database.load_training_rows()` with explicit training-data leakage guards.
- Added SQL filters: `features_json IS NOT NULL AND features_json != ''`; `r.{target_market} IS NOT NULL`; timestamp boundary `fs.created_at < r.updated_at` (rows with NULL timestamps on either side pass through as a legacy-compatible fallback for pre-existing data without timestamps).
- Added Python-level guards: malformed `features_json` rows are silently excluded (skip, not crash); non-dict JSON objects (arrays, scalars) are excluded.
- Timestamp limitation documented in code: both `created_at` / `updated_at` are our own insertion timestamps, not actual match times. Guard catches snapshots written after results were recorded but cannot detect intra-second races or manually backdated timestamps. No schema changes made.
- `ValueError` error message now includes `!r` quoting for the invalid market name.
- Added `tests/test_training_leakage_guard.py` with 26 tests covering: empty DB; both/one/neither side of the join; all five target markets; unsupported market raises `ValueError`; malformed/null/empty/non-dict features JSON excluded; null target column excluded; timestamp guard (before/after/null); output shape (no prediction, odds, or score fields); no writes to DB; no schema changes; `historical_replay` import boundary. All tests use isolated temporary SQLite databases only.
- Updated model version to `0.1.8.9`.

## v0.1.8.8
- Added `src/historical_replay.py` with a read-only loader: `ReplayRow` dataclass and `load_replay_rows(db_path=None)`.
- Joins `predictions` to `results` on `match_id` using a SQLite read-only URI (`mode=ro`). Does not call `init_db()`, create tables, or write anything.
- Derives `actual_label` ("home_win" / "draw" / "away_win") from pre-computed `results.home_win` / `results.draw` columns.
- Sets `correct = (selection == actual_label)` and `probability_assigned_to_actual = model_probability` when correct, `None` otherwise (full 3-way probability assignment requires future schema work).
- Respects `db_path` argument when provided; falls back to `get_db_path()` (→ `RSB_DB_PATH` env var) when omitted.
- Returns empty list for missing DB, pre-init DB, or no joined rows.
- Added `tests/test_historical_replay.py` with 12 tests covering: empty DB, home-win join, actual-label derivation (all three outcomes), miss/correct logic, non-matching IDs, read-only proof (mtime invariant on isolated temp DB), explicit path, env-var path, missing DB, and banned-import check. All tests use isolated temporary SQLite databases only.
- This module is evaluation plumbing only. Training leakage guard (`load_training_rows` SQL review) is v0.1.8.9.
- Updated model version to `0.1.8.8`.

## v0.1.8.7
- Added `get_results_path()` to `src/paths.py`, checking `RSB_RESULTS_PATH` environment variable and falling back to `DEFAULT_RESULTS_PATH`, mirroring the existing DB/slate/model-output override pattern.
- Updated `src/update_results.py` to call `get_results_path()` instead of using `DEFAULT_RESULTS_PATH` directly, making the results input path safely overridable at runtime.
- Added `tests/test_update_results.py` with two subprocess tests verifying `update_results.py` runs against a `tmp_path` results file via `RSB_RESULTS_PATH` and `RSB_DB_PATH` without touching `data/input/results.json` or `data/worldcup_ai.db`.
- Added two tests to `tests/test_paths.py` covering `get_results_path()` default and env-override behavior.
- Updated model version to `0.1.8.7`.

## v0.1.8.6
- Added `src/backtest.py` with pure, dependency-free backtest metric primitives: `clamp_probability`, `brier_score_binary`, `log_loss_binary`, `prediction_correct`, `probability_assigned_to_actual`, `brier_score_multiclass`, `log_loss_multiclass`, `mean`, and `accuracy`.
- No database access, no filesystem access, no imports from `database.py`, `run_slate.py`, or path modules.
- Added `tests/test_backtest.py` with deterministic unit tests covering known-value binary and multiclass Brier score and log loss, epsilon clamping edge cases at p=0 and p=1, rejection of invalid inputs (NaN, infinity, out-of-range, non-numeric, missing labels, empty containers), and proof of no database/filesystem dependency.
- Updated model version to `0.1.8.6`.

## v0.1.8.5
- Updated `pyproject.toml` version to `0.1.8.5`.
- Updated `config/model_config.json` version to `0.1.8.5` and replaced version-specific notes with a generic, non-stale project note.
- Updated `CLAUDE.md` with current version (`v0.1.8.5`), accurate test count (`119`), completed foundation summary for v0.1.8.2–v0.1.8.5, and the next modeling target (pure backtest metric primitives, not API/frontend/parlay).
- Updated `README.md` with current version, expanded current foundation section to include path resolution, runtime path overrides, test isolation, and config validation; added explicit not-live-betting-ready statement; updated roadmap to reflect revised versioning plan through v0.5.x.

## v0.1.8.4
- Added `src/config_validation.py` with a dependency-free config validation layer: `ConfigValidationError`, `load_json_config`, `validate_required_keys`, `validate_model_config`, `validate_sports_config`, and `validate_bet_rules_config`.
- Updated `src/run_slate.py` to replace raw `json.loads(MODEL_CONFIG_PATH.read_text())` at module level with `load_json_config` + `validate_model_config`, so invalid or incomplete config fails immediately on import with a clear error.
- Updated `src/odds_collector.py` to validate `model_config.json` via `validate_model_config` and `sports_config.json` via `validate_sports_config` inside `load_runtime_config`.
- Updated `src/market_selector.py` to validate `bet_rules_config.json` via `validate_bet_rules_config` inside `load_rules_config`.
- Added `tests/test_config_validation.py` with 30 tests covering: valid configs pass, missing required keys raise `ConfigValidationError` with the key name, wrong types raise with the field name, invalid JSON raises a clear error, validated loading does not mutate the config dict, and all three real config files pass validation.
- Updated model version to `0.1.8.4`.

## v0.1.8.3
- Added `get_db_path()`, `get_slate_path()`, and `get_model_output_path()` helper functions to `src/paths.py` that check `RSB_DB_PATH`, `RSB_SLATE_PATH`, and `RSB_MODEL_OUTPUT_PATH` environment variables and fall back to the existing `DEFAULT_*` constants.
- Updated `src/database.py` to resolve `DB_PATH` via `get_db_path()` at import time so subprocess tests can redirect the database without touching `data/worldcup_ai.db`.
- Updated `src/run_slate.py` to call `get_slate_path()` and `get_model_output_path()` inside `main()` so subprocess tests can redirect slate and model-output file IO to `tmp_path`.
- Rewrote `tests/test_run_slate.py` to run the subprocess with `RSB_*` env overrides pointing to `tmp_path`; the real `data/worldcup_ai.db`, `data/input/slate.json`, and `data/output/latest_model_output.json` are never touched during tests.
- Added four tests to `tests/test_paths.py` verifying default paths still resolve to project-root files and that each env override redirects the resolved path to the provided override.
- Updated model version to `0.1.8.3`.

## v0.1.8.2
- Added `src/paths.py` with all project-root-relative path constants derived from the module's own location, not the working directory.
- Replaced every `Path("relative/...")` constant in `src/database.py`, `src/model.py`, `src/odds_collector.py`, `src/run_slate.py`, `src/market_selector.py`, `src/check_odds_provider.py`, `src/import_claude_review.py`, and `src/update_results.py` with imports from `src/paths.py`.
- Scripts can now be invoked from any working directory and still resolve config, input, and output files from the project root.
- Added `tests/test_paths.py` to verify `PROJECT_ROOT` resolves to the repo root, all path constants are absolute, key paths point to expected locations, config files exist at their resolved paths, and `run_slate.py` succeeds when launched from outside the project root.
- Updated model version to `0.1.8.2`.

## v0.1.8.1
- Added `pyproject.toml` with Python `>=3.10,<3.15` project metadata.
- Pinned dependency ranges in `requirements.txt`.
- Added GitHub Actions pytest CI across Python 3.10, 3.11, 3.12, and 3.13.
- Updated `src/simulator.py` to use vectorized NumPy Poisson draws.
- Updated bootstrap simulation so availability and tactical matchup context now adjust estimated goal rates instead of only affecting guardrails.
- Added goal-rate adjustment details to simulation output.
- Added versioned model artifact paths and model metadata in `src/model.py`.
- Added feature schema hash and feature schema validation before ML prediction.
- Updated `src/run_slate.py` to use version-specific model artifacts.
- Extended prediction persistence with technical recommendation, data quality, actionable status, guardrail status, do-not-bet flag, and full prediction JSON.
- Added tests for simulator adjustments, model schema safety, model path versioning, and full prediction persistence.
- Updated model version to `0.1.8.1`.

## v0.1.8
- Added `src/tactical_matchup.py` for World Cup tactical matchup context.
- Added tactical matchup features for pressing versus buildup, pace versus high defensive line, crossing and aerial matchups, set-piece edges, counterattack edges, central/wide chance creation, midfield control, formation flexibility, transition defense, low-block comfort, and manager tactical rating.
- Updated `src/features.py` so tactical features are included in every feature snapshot.
- Added tactical data guardrails for missing tactical context, unverified tactical sources, and low tactical confidence.
- Added non-blocking tactical review warnings for major matchup flags such as pace versus high line, press versus buildup, and set-piece edge.
- Added tests for tactical feature extraction, tactical review flags, tactical rating clamping, feature integration, and tactical guardrails.
- Updated model version to `0.1.8`.

## v0.1.7
- Added `src/availability.py` for World Cup lineup, injury, availability, and rotation-risk context.
- Added availability-derived features to `src/features.py`, including lineup strength, starter availability, lineup confidence, rotation risk, B-team risk, replacement quality, key absence impact, returning player risk, minutes restrictions, and fitness concern differentials.
- Added availability guardrails to `src/data_quality.py` for missing availability data, unverified injury data, unconfirmed lineups, low lineup confidence, B-team rotation risk, key player absences, recent injury returns, and minutes restrictions.
- Updated data quality blocking logic so research outputs remain non-actionable when the expected version of either team is unclear.
- Added tests for availability defaults, availability feature extraction, returning-player risk, availability guardrails, and updated feature generation.
- Updated model version to `0.1.7`.

## v0.1.6
- Added `src/data_quality.py` for data quality warnings and recommendation guardrails.
- Added prediction-level fields for `data_quality`, `quality_warnings`, `actionable`, `recommendation_guardrail`, `guardrail_reasons`, and `do_not_bet_real_money`.
- Added `technical_recommendation` so the raw EV signal is preserved separately from the final guarded recommendation.
- Added guardrail logic that converts technical `bet` signals into final `pass` recommendations when data is weak or research-only.
- Added warnings for simulation-only bootstrap mode, insufficient training data, unverified manual features, placeholder features, missing feature fields, manual odds usage, manual odds fallback, stale odds, missing provider odds, and low sportsbook coverage.
- Added run-level data quality summary with warning counts, blocked prediction counts, and actionable prediction counts.
- Added tests for data quality assessment, stale odds detection, manual fallback blocking, missing features, guardrail application, and quality summaries.
- Updated README and architecture docs with data quality guardrail workflow.

## v0.1.5
- Added `src/slate_odds.py` to resolve qualified provider odds for `run_slate.py` predictions.
- Added `--odds-source manual|provider` and `--odds-provider mock|the_odds_api` CLI options to `src/run_slate.py`.
- Kept manual slate odds as the default to avoid accidental live API quota usage.
- Added provider-odds mode that collects odds once, applies market rules, uses qualified best prices, and records provider metadata.
- Added manual fallback behavior and `--no-manual-odds-fallback` for strict provider-only runs.
- Added team/date matching and reversed team-order handling so provider home/away ordering can still map to the slate target selection.
- Added optional slate odds validation for provider-odds mode.
- Added tests for provider odds resolution, manual fallback, reversed team-order matching, and optional odds validation.
- Updated README with provider odds workflow for slate runs.

## v0.1.4
- Added `src/check_odds_provider.py` for safe mock and live odds provider diagnostics.
- Added API key presence checks with masked output so `ODDS_API_KEY` is never printed in full.
- Added live The Odds API diagnostic mode without changing mock mode as the default.
- Added provider diagnostics output to `data/output/latest_provider_diagnostics.json`.
- Added readable provider error reporting for missing keys, provider failures, unavailable sport keys, or quota issues.
- Added tests for API key masking, mock diagnostics, and safe missing-key behavior.
- Updated README with provider diagnostic workflow.

## v0.1.3
- Added configurable World Cup market selection rules in `config/bet_rules_config.json`.
- Added `src/market_selector.py` for best-price qualification, target odds filtering, allowed market/selection checks, and sportsbook availability checks.
- Updated `src/odds_collector.py` to include rules summary, qualified best prices, rejected price groups, and market decisions in latest odds output.
- Kept parlay and same-game parlay logic disabled while adding config placeholders for future expansion.
- Added tests for market selection rules, target odds filtering, minimum sportsbook requirements, and active rules loading.
- Updated README with market rules workflow and future bet-structure roadmap.

## v0.1.2
- Added World Cup-focused odds provider abstraction.
- Added `config/sports_config.json` with a single active `worldcup` profile.
- Added normalized odds provider interface under `src/odds_providers/`.
- Added deterministic mock odds provider for tests and development without API calls.
- Added The Odds API provider adapter that reads `ODDS_API_KEY` from the local environment.
- Added `src/odds_collector.py` to collect odds, save snapshots, select best prices, and write latest odds output.
- Extended `odds_snapshots` with provider metadata, sport key, event ID, teams, commence time, and raw provider JSON.
- Added tests for provider normalization, mock odds collection, bookmaker filtering, and best-price selection.
- Documented future roadmap for parlays, player filters, P&L tracking, CLV, and future sport expansion.

## v0.1.1
- Moved fake Alpha/Beta sample data out of live input files into `data/samples/`.
- Cleared live `data/input/slate.json` and `data/input/results.json`.
- Added slate/result input validation with clear error messages.
- Added reproducible Monte Carlo seeding via `run_monte_carlo(..., seed=...)`.
- Added `odds_snapshots` to preserve point-in-time odds context.
- Added pytest coverage for EV math, feature generation, validation, simulation reproducibility, and empty slate execution.
- Updated README with live input, sample data, reproducibility, and test instructions.

## v0.1.0
- Initial World Cup-only framework.
- SQLite database memory.
- Feature snapshots.
- Prediction logging.
- Result logging.
- Retraining loop.
- EV engine.
- Claude JSON prompt.
