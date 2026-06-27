# RSB Project Instructions

RSB is a sportsbook analytics / +EV simulation project.

Current project status:
- Version: v0.1.9.0
- Python: 3.13 virtual environment
- Tests: pytest, currently 347 passing tests
- Current focus: World Cup simulation engine
- Next modeling target: audit checkpoint before v0.1.9.1 — metric validity, report wording, selected-outcome limitations, calibration gaps, feature-upgrade readiness
- Future goal: automation-first sportsbook analytics website/app

Completed foundation (v0.1.8.x – v0.1.9.x):
- v0.1.8.2: centralized absolute path resolution via src/paths.py
- v0.1.8.3: runtime path overrides (RSB_DB_PATH, RSB_SLATE_PATH, RSB_MODEL_OUTPUT_PATH) for safe test isolation
- v0.1.8.4: dependency-free config validation (ConfigValidationError, load_json_config, validate_*_config)
- v0.1.8.5: project metadata/docs cleanup — synchronized versions across pyproject.toml, CLAUDE.md, README.md, model_config.json
- v0.1.8.6: pure backtest metric primitives (brier_score_binary, log_loss_binary, brier_score_multiclass, log_loss_multiclass, mean, accuracy) — no DB dependency
- v0.1.8.7: results ingestion safety — RSB_RESULTS_PATH override, get_results_path() helper, subprocess test isolation for update_results.py
- v0.1.8.8: historical replay read-only loader — ReplayRow dataclass, load_replay_rows(), SQLite mode=ro, actual-label derivation, evaluation plumbing only
- v0.1.8.9: training data leakage guard — hardened load_training_rows() with SQL null/empty/timestamp filters, Python malformed-JSON exclusion, and 26 targeted tests
- v0.1.9.0: backtest report output — build_backtest_report(rows) -> dict, pure in-memory selected-outcome binary metrics, no DB/filesystem/CLI

Long-term product goal:
The final workflow should not require manual match/team/player/odds input. The user should specify sport, date range/week, markets, sportsbooks, and number of legs. The system should automatically collect fixtures, odds, props, stats, injuries, lineups, build features, run simulations/models, compare EV, rank singles/parlays, and recommend the best sportsbook for each card.

Core betting rules:
- Never call anything a lock.
- Prefer pass/no bet over forced action.
- Only recommend a bet when model probability is meaningfully higher than sportsbook implied probability.
- Guardrails must block weak, stale, incomplete, or research-only predictions.
- Completed matches should become permanent training data.
- Historical data should be appended, not overwritten.
- All predictions should be explainable and auditable.

Development rules:
- Do not rewrite the whole project.
- Do not remove existing functionality.
- Keep manual slate.json as a dev/testing fallback.
- Do not delete database files or historical data without explicit approval.
- Do not expose API keys, tokens, sportsbook credentials, or secrets.
- Use .env for secrets and ensure .env is gitignored.
- Before editing, explain the plan.
- Make small, testable changes.
- Run tests after changes.
- Summarize changed files before committing.

Preferred workflow:
1. Audit or plan first.
2. Ask before making major changes.
3. Implement one small task at a time.
4. Run tests.
5. Show changed files and summary.
6. Commit only after approval.
