# Changelog

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
