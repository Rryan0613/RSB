# RSB Project Instructions

RSB is a sportsbook analytics / +EV simulation project.

Current project status:
- Version: v0.3.2
- Python: 3.13 virtual environment
- Tests: pytest, verified baseline 2307 passing tests
- Verified release base: b876eb1 — v0.3.2 merge (PR #48)
- Latest numbered release: v0.3.2 — MLB Plate-Appearance Dataset & Rate Foundation (PR #48, merge commit b876eb1, implementation commit 9212c93, real-Savant correction commit ba3ce68)
- Current roadmap: v0.3.3 — MLB Plate-Appearance Probability Baseline is the next roadmap objective (directional). It is not yet implementation-approved — a separate v0.3.3 inspection/planning stage requires ChatGPT approval before coding begins.
- Future goal: automation-first sportsbook analytics website/app

Architecture:
- The World Cup runtime (`run_slate.py` and everything it orchestrates) is the only operational, end-to-end pipeline today. It is frozen for new feature development — maintenance/bug fixes only. It will not become a generic multi-sport orchestrator. See docs/LEGACY_PIPELINE_ARCHITECTURE_AUDIT.md.
- A separate, reusable pure-primitives foundation (candidate identity, odds snapshot, evaluation, EV enrichment, ranking, reporting, settlement, sport/market capability profiles, backtest math) exists independently and is not wired into any runtime yet. See docs/CANDIDATE_EVALUATION_CONTRACT.md.
- MLB now has a v0.3.1 pitch-level Statcast historical data foundation and a v0.3.2 plate-appearance dataset/rate foundation built on top of it. MLB still has no probability model, no calibration pipeline, no simulation, no sportsbook bridge, and no operational MLB runtime/orchestrator.
- New sports get their own data/features/model/runtime built on the pure-primitives foundation — never by extending run_slate.py.

Final sport scope:
- MLB is the next active modeling domain (first new sport engine).
- NBA is planned as the second and final new sport engine, after MLB.
- No NFL, NHL, or further sport expansion is currently planned.
- See docs/MLB_NBA_ROADMAP.md for the full roadmap, including the directional v0.3.3-v0.3.4 MLB batch.

Long-term:
- After MLB and NBA reach a defined finished RSB state, a separate, non-sports probabilistic forecasting/quantitative project may follow — not a fork or rebrand of RSB. Do not add finance-specific abstractions to RSB.

Completed foundation (v0.1.8.x – v0.3.1):
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
- v0.2.7: pure prop result / settlement record normalization primitives — PropResultValidationError, VALID_SETTLEMENT_STATUSES, FINAL_SETTLEMENT_STATUSES, normalize_market_type, normalize_selection, normalize_settlement_status, build_prop_result (src/prop_result.py)
- v0.2.8: pure candidate EV enrichment primitives — CandidateEVValidationError, build_candidate_ev_enrichment (src/candidate_ev.py)
- v0.2.9: pure candidate ranking primitives — CandidateRankingValidationError, rank_candidate_ev_enrichments (src/candidate_ranking.py)
- v0.2.10: pure ranked candidate report primitives — CandidateReportValidationError, build_candidate_report (src/candidate_report.py)
- v0.2.11: pure sport/market capability profile primitives — MarketCapabilityValidationError, normalize_sport/league/market_type/selection_type, build_market_capability, build_sport_market_profile (src/market_capability.py)
- v0.2.12: pure MLB capability profile seed — 15 declared MLB markets built on v0.2.11 (src/mlb_capability.py)
- v0.3.0: Candidate Evaluation Contract — validate_candidate_evaluation_record(), the canonical whole-record validator; candidate_ranking.py delegates to it (src/candidate_evaluation.py; docs/CANDIDATE_EVALUATION_CONTRACT.md)
- v0.3.1: MLB Statcast Data Foundation — manual-CSV-only historical MLB Statcast ingestion (no automated Baseball Savant/MLB access), RSB-owned normalized pitch-level contract, and immutable raw/normalized/manifest snapshots with SHA-256 provenance (src/mlb/statcast_import.py, statcast_normalize.py, statcast_snapshot.py; MLB data root in src/paths.py via RSB_MLB_DATA_DIR). Merged to main (PR #46, merge commit 3ae353f, implementation commit 765b5ed, 2156 passing tests). Feature branch feature/v0.3.1-mlb-statcast-data-foundation deleted locally and remotely. No plate-appearance aggregation, modeling, or MLB runtime wiring — that is v0.3.2+ scope.
- v0.3.2: MLB Plate-Appearance Dataset & Rate Foundation — derives plate-appearance (PA) records and leakage-safe prior batter/pitcher/league empirical outcome rates from v0.3.1's normalized pitch-level snapshots (src/mlb/plate_appearance.py, plate_appearance_rates.py, plate_appearance_snapshot.py; docs/MLB_PLATE_APPEARANCE_CONTRACT.md). Deterministic `(source_game_id, at_bat_number)` PA grouping with contiguous chronology validation; completed vs. incomplete PA semantics via chronology-first terminal-pitch detection; a closed completed-event taxonomy with `intentional_walk` kept distinct from ordinary `walk`; forward-only mid-PA pitcher substitutions preserved but excluded from pitcher-rate attribution (`pitcher_rate_eligible = False`), while still allowed to update batter/league history when otherwise completed; raw empirical prior counts/rates only, no shrinkage or modeling; strict single-source-snapshot provenance and deterministic immutable derived artifacts. A real-Savant-backed correction (commit ba3ce68) added recognition of the `truncated_pa` terminal marker as `pa_status = "incomplete"` (never a completed taxonomy/rate category), with the raw value preserved for provenance. Merged to main (PR #48, merge commit b876eb1, implementation commit 9212c93, real-Savant correction commit ba3ce68, 2307 passing tests). Feature branch feature/v0.3.2-mlb-plate-appearance-dataset-rate-foundation deleted locally and remotely. No probability model, calibration, simulation, or MLB runtime wiring — that is v0.3.3+ scope.

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
