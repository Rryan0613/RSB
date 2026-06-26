# Changelog

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
