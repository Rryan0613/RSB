# WorldCup AI v0.1.2

A focused World Cup +EV prediction framework.

This project is designed to:
- Store every match, feature snapshot, prediction, odds line, simulation output, and final result.
- Retrain from the local database as completed results are added.
- Estimate model probability.
- Compare model probability to sportsbook implied probability.
- Calculate edge and expected value.
- Generate structured JSON that can be pasted into Claude or ChatGPT for review.

This is not a "lock" generator. It is a disciplined sports analytics research project.

## Design Direction

The project is World Cup-focused right now, but the codebase is being built as a long-term analytics platform. Shared infrastructure should stay reusable:

- Odds provider adapters
- Normalized odds snapshots
- Database persistence
- EV calculations
- Model run tracking
- Reporting
- Tests

Sport-specific logic should stay isolated. When NBA, NFL, MLB, player props, parlays, or P&L tracking are added later, they should be added as new modules/configs rather than by rewriting the World Cup foundation.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
python src/run_slate.py
```

The default live slate is intentionally empty. An empty run should complete safely and write a report with zero analyzed matches.

## Live Inputs vs Samples

Use `data/input/` for live working files:

```text
data/input/slate.json
data/input/results.json
```

Use `data/samples/` for sample/dev data:

```text
data/samples/slate_sample.json
data/samples/results_sample.json
```

Do not leave fake sample matches in `data/input/` when running real analysis. Completed matches become training data through the SQLite database.

## Main Workflow

1. Add upcoming matches to `data/input/slate.json`.
2. Run:

```bash
python src/run_slate.py
```

3. The model writes predictions to:

```text
data/output/latest_model_output.json
```

4. Paste that JSON into Claude with the prompt in:

```text
prompts/claude_worldcup_prompt.md
```

5. After games finish, add final results to:

```text
data/input/results.json
```

6. Run:

```bash
python src/update_results.py
```

7. Next slate run retrains using the updated database.

## Odds Collection

v0.1.2 adds an odds provider abstraction.

The default provider is `mock`, which is deterministic and does not call external APIs or spend API credits:

```bash
python src/odds_collector.py
```

The collector writes:

```text
data/output/latest_odds_output.json
```

It also saves normalized sportsbook lines into `odds_snapshots`.

Current sportsbook targets:

```text
fanduel
draftkings
betmgm
```

Current active sport:

```text
worldcup
```

The active sport profile is configured in:

```text
config/sports_config.json
```

To use The Odds API later, set your local environment variable and change the odds provider config from `mock` to `the_odds_api`:

```bash
export ODDS_API_KEY="your_key_here"
```

Do not commit API keys to GitHub.

## Database

SQLite database path:

```text
data/worldcup_ai.db
```

The database is the model's memory.

Current core tables:
- `matches`
- `feature_snapshots`
- `predictions`
- `simulation_outputs`
- `odds_snapshots`
- `results`
- `model_runs`
- `review_notes`

## Reproducible Simulations

`run_monte_carlo` accepts an optional `seed`:

```python
run_monte_carlo(match, simulations=10000, seed=42)
```

You can also add `simulation_seed` to a match in `slate.json`. If no seed is provided, simulations run with non-deterministic randomness.

## Tests

Run the test suite with:

```bash
python -m pytest
```

The tests cover:
- American odds conversion
- Implied probability
- EV calculation
- Feature generation
- Input validation
- Monte Carlo reproducibility
- Empty slate execution
- Odds provider normalization
- Best-price selection
- Mock odds collection

## Future Roadmap

Planned future modules include:
- Best-price shopping and line movement analysis
- Configurable single-leg and parlay rules
- Same-game parlay rules
- Target odds ranges
- Player-specific filters
- Historical backtesting
- Bet ledger and P&L tracking
- W/L ratio and ROI dashboards
- Closing line value tracking
- Future sport profiles after the World Cup foundation is stable
