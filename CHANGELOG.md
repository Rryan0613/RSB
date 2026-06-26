# Changelog

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
