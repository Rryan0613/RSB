# WorldCup AI v0.1.1

A focused World Cup +EV prediction framework.

This project is designed to:
- Store every match, feature snapshot, prediction, odds line, simulation output, and final result.
- Retrain from the local database as completed results are added.
- Estimate model probability.
- Compare model probability to sportsbook implied probability.
- Calculate edge and expected value.
- Generate structured JSON that can be pasted into Claude or ChatGPT for review.

This is not a "lock" generator. It is a disciplined sports analytics research project.

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
pytest
```

The v0.1.1 tests cover:
- American odds conversion
- Implied probability
- EV calculation
- Feature generation
- Input validation
- Monte Carlo reproducibility
- Empty slate execution
