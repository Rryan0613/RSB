# WorldCup AI v0.2.0

A focused World Cup +EV prediction framework. This is a disciplined sports analytics research project, not a lock generator.

**This project is not live-betting-ready.** The model is currently in bootstrap/simulation-only mode with no completed training data. Historical replay, backtesting, and calibration must be completed before any recommendation should be treated as actionable.

## Current Foundation

The project currently supports:

- SQLite model memory
- input validation
- reproducible, vectorized Monte Carlo simulation
- availability and tactical goal-rate adjustments during bootstrap simulation
- odds provider abstraction
- provider diagnostics
- qualified provider odds in `run_slate.py`
- market selection rules
- data quality guardrails
- availability, lineup, injury, and rotation-risk context
- tactical matchup context
- versioned model artifacts
- model feature schema validation
- fuller prediction JSON persistence
- pinned dependency ranges
- GitHub Actions pytest CI
- absolute path resolution independent of working directory (`src/paths.py`)
- runtime path overrides via `RSB_DB_PATH`, `RSB_SLATE_PATH`, `RSB_MODEL_OUTPUT_PATH` for safe test isolation
- dependency-free config validation with clear error messages (`src/config_validation.py`)
- pure tournament stage and market semantics validation (`src/stage_market.py`)
- pure prediction review taxonomy primitives (`src/review_taxonomy.py`)
- pure prediction review note primitives (`src/review_notes.py`)
- pure odds and implied probability conversion primitives (`src/odds.py`)
- pure edge calculation primitives (`src/edge.py`)

## Runtime Target

Project metadata lives in:

```text
pyproject.toml
```

The project target is:

```text
Python >=3.10,<3.15
```

Use a modern Python version before installing fresh dependencies.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/run_slate.py
```

Run tests:

```bash
python -m pytest
```

Run with qualified mock provider odds:

```bash
python src/run_slate.py --odds-source provider --odds-provider mock
```

Run with The Odds API after setting a local key:

```bash
export ODDS_API_KEY="your_key_here"
python src/run_slate.py --odds-source provider --odds-provider the_odds_api
```

Do not commit API keys to GitHub.

## Live Inputs

Live working files:

```text
data/input/slate.json
data/input/results.json
```

Sample/dev files:

```text
data/samples/slate_sample.json
data/samples/results_sample.json
```

Do not leave fake sample matches in `data/input/` when running real analysis.

## Provider Odds

Provider odds mode:

- collects provider odds once per run
- applies market selection rules
- uses only qualified best prices
- matches provider lines to slate matches by match ID or team/date
- supports reversed provider home/away order when the target is still the slate home team
- falls back to manual slate odds unless `--no-manual-odds-fallback` is provided
- records provider metadata in prediction output and odds snapshots

Strict provider-only run:

```bash
python src/run_slate.py --odds-source provider --odds-provider the_odds_api --no-manual-odds-fallback
```

## Guardrails

Each prediction includes:

```text
data_quality
actionable
quality_warnings
technical_recommendation
recommendation
recommendation_guardrail
guardrail_reasons
do_not_bet_real_money
```

The model can calculate a technical EV signal, but weak data can block that signal from becoming actionable. Guardrails currently cover simulation-only bootstrap mode, insufficient training data, unverified features, stale odds, manual fallback odds, missing availability, unverified injury data, unconfirmed lineups, rotation risk, key absences, missing tactical context, unverified tactical data, and low tactical confidence.

## Bootstrap Simulation

`src/simulator.py` now uses NumPy vectorized Poisson draws and applies controlled goal-rate adjustments from availability and tactical matchup context.

The simulation output includes:

```text
goal_rate_adjustments
total_home_goal_adjustment
estimated_home_goals
estimated_away_goals
```

This means availability and tactical values now affect bootstrap probability, not just guardrail status.

## Model Safety

`src/model.py` now saves versioned model artifacts such as:

```text
models/home_win_model_0_1_8_1.joblib
```

Model artifacts store:

```text
feature_cols
feature_schema_hash
model_version
target_market
trained_rows
trained_at
```

Before prediction, the feature schema is validated so an older model cannot silently score a newer feature set with missing or non-numeric features.

## Availability Context

`src/availability.py` models the actual expected version of each team. It supports:

```text
lineup_status
lineup_confidence
normal_starter_count
expected_starters_available
lineup_strength_rating
rotation_risk
b_team_risk
replacement_quality_rating
key_absences
returning_players
fitness_concerns
```

It creates features such as:

```text
lineup_strength_diff
starter_availability_rate_diff
expected_starters_available_diff
rotation_risk_diff
b_team_risk_diff
key_absence_impact_diff
returning_player_risk_diff
minutes_restricted_count_diff
```

Trusted availability sources:

```text
official_feed
official_lineup
verified_dataset
verified_team_news
historical_backfill
model_availability_store
```

## Tactical Matchup Engine

`src/tactical_matchup.py` models how the teams match up tactically. It supports:

```text
tactical_confidence
pressing_intensity
build_up_quality
defensive_line_height
pace_threat
crossing_volume
aerial_threat
aerial_defense
set_piece_attack
set_piece_defense
counterattack_threat
transition_defense
midfield_control
formation_flexibility
manager_tactical_rating
low_block_comfort
chance_creation_centrality
wide_creation
press_resistance
vulnerability_to_press
```

It creates features such as:

```text
home_press_vs_away_buildup
away_press_vs_home_buildup
home_pace_vs_away_high_line
away_pace_vs_home_high_line
home_crossing_vs_away_aerial_defense
away_crossing_vs_home_aerial_defense
home_set_piece_edge
away_set_piece_edge
home_counterattack_edge
away_counterattack_edge
home_central_creation_edge
away_central_creation_edge
home_wide_creation_edge
away_wide_creation_edge
midfield_control_diff
formation_flexibility_diff
manager_tactical_diff
transition_defense_diff
```

Tactical guardrails can block for:

```text
tactical_data_missing
tactical_data_unverified
low_tactical_confidence
```

The system can also emit non-blocking review warnings for major tactical mismatches, such as pace versus high line, press versus buildup, and set-piece edge.

Trusted tactical sources:

```text
official_feed
verified_dataset
verified_scouting_report
historical_backfill
model_tactical_store
```

## Database

SQLite database path:

```text
data/worldcup_ai.db
```

Core tables:

```text
matches
feature_snapshots
predictions
simulation_outputs
odds_snapshots
results
model_runs
review_notes
```

The `predictions` table now stores the full prediction JSON payload in `prediction_json`, including quality warnings, guardrail status, provider metadata, and simulation summary.

## CI

GitHub Actions runs pytest on:

```text
Python 3.10
Python 3.11
Python 3.12
Python 3.13
```

Workflow file:

```text
.github/workflows/tests.yml
```

## Roadmap

Near-term (v0.1.8.x – v0.1.9.x):

```text
v0.1.8.6 - pure backtest metric primitives (Brier score, log loss, calibration) — no DB dependency
v0.1.8.7 - results ingestion safety (update_results env override + tests)
v0.1.8.8 - historical replay read-only loader
v0.1.8.9 - training data leakage guard (database.load_training_rows SQL filter)
v0.1.9.0 - backtest report output
v0.1.9.1 - World Cup feature variable upgrade (4 derived ratio features)
v0.1.9.2 - Tournament Stage and Market Semantics Validation
v0.1.9.3 - Prediction Review Taxonomy Primitives
```

Later (v0.2.x+):

```text
v0.2.0 - pure odds and implied probability conversion primitives
v0.2.1 - pure edge calculation primitives (src/edge.py)
v0.2.2 - candidate evaluation / pass reason primitives
v0.2.3 - backtest review overlay
v0.3.x - parlays only after confirmed calibration on sufficient historical matches
v0.4.x - API backend
v0.5.x - dashboard/frontend
```
