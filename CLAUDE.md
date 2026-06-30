# RSB Project Instructions

RSB is a sportsbook analytics / +EV simulation project.

Current project status:
- Version: v0.2.6
- Python: 3.13 virtual environment
- Tests: pytest, currently 1125 passing tests
- Current focus: World Cup simulation engine
- Next modeling target: v0.2.7 (candidate)
- Future goal: automation-first sportsbook analytics website/app

Completed foundation (v0.1.8.x – v0.2.6):
- v0.1.8.2: centralized absolute path resolution via src/paths.py
- v0.1.8.3: runtime path overrides (RSB_DB_PATH, RSB_SLATE_PATH, RSB_MODEL_OUTPUT_PATH) for safe test isolation
- v0.1.8.4: dependency-free config validation (ConfigValidationError, load_json_config, validate_*_config)
- v0.1.8.5: project metadata/docs cleanup — synchronized versions across pyproject.toml, CLAUDE.md, README.md, model_config.json
- v0.1.8.6: pure backtest metric primitives (brier_score_binary, log_loss_binary, brier_score_multiclass, log_loss_multiclass, mean, accuracy) — no DB dependency
- v0.1.8.7: results ingestion safety — RSB_RESULTS_PATH override, get_results_path() helper, subprocess test isolation for update_results.py
- v0.1.8.8: historical replay read-only loader — ReplayRow dataclass, load_replay_rows(), SQLite mode=ro, actual-label derivation, evaluation plumbing only
- v0.1.8.9: training data leakage guard — hardened load_training_rows() with SQL null/empty/timestamp filters, Python malformed-JSON exclusion, and 26 targeted tests
- v0.1.9.0: backtest report output — build_backtest_report(rows) -> dict, pure in-memory selected-outcome binary metrics, no DB/filesystem/CLI
- v0.1.9.1: World Cup feature variable upgrade — 4 derived ratio features (sot_accuracy_diff, xg_per_shot_diff, pressing_efficiency_diff, big_chance_rate_diff), additive only, no new schema fields
- v0.1.9.2: pure tournament stage and market semantics validation (StageMarketValidationError, normalize_stage, normalize_market_type, allows_draw, validate_stage_market)
- v0.1.9.3: pure prediction review taxonomy primitives (ReviewTaxonomyValidationError, normalize_review_category, normalize_review_severity, normalize_data_quality, validate_review_taxonomy)
- v0.1.9.4: pure prediction review note primitives (ReviewNoteValidationError, build_review_note)
- v0.2.0: pure odds and implied probability conversion primitives (OddsValidationError, american_to_implied_probability, decimal_to_implied_probability, fractional_to_implied_probability, validate_probability)
- v0.2.1: pure edge calculation primitives (calculate_edge)
- v0.2.2: pure candidate evaluation record and pass reason primitives (CandidateEvaluationValidationError, normalize_candidate_status, normalize_pass_reason, validate_pass_reasons, build_candidate_evaluation)
- v0.2.3: pure backtest review overlay primitives (BacktestReviewValidationError, build_backtest_review)
- v0.2.4: odds expansion / EV math primitives — american_to_decimal_odds, decimal_to_american_odds (src/odds.py); EVValidationError, calculate_expected_value, validated backward-compatible wrappers (src/ev.py)
- v0.2.5: pure prop/pick candidate schema primitives — PropCandidateValidationError, normalize_sport, normalize_league, normalize_market_type, normalize_selection, build_prop_candidate (src/prop_candidate.py)
- v0.2.6: pure odds snapshot / provider record normalization primitives — OddsSnapshotValidationError, VALID_ODDS_FORMATS, normalize_provider, normalize_sportsbook, normalize_market_type, normalize_selection, normalize_odds_format, build_odds_snapshot (src/odds_snapshot.py)

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
