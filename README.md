# WorldCup AI v0.1.6

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
- Provider diagnostics
- Qualified provider odds for slate runs
- Data quality guardrails
- Normalized odds snapshots
- Database persistence
- EV calculations
- Model run tracking
- Market selection rules
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
2. Run with manual slate odds:

```bash
python src/run_slate.py
```

3. Or run with qualified provider odds:

```bash
python src/run_slate.py --odds-source provider --odds-provider mock
```

4. The model writes predictions to:

```text
data/output/latest_model_output.json
```

5. Paste that JSON into Claude with the prompt in:

```text
prompts/claude_worldcup_prompt.md
```

6. After games finish, add final results to:

```text
data/input/results.json
```

7. Run:

```bash
python src/update_results.py
```

8. Next slate run retrains using the updated database.

## Odds Collection

v0.1.2 added an odds provider abstraction. v0.1.3 added market selection rules on top of those odds. v0.1.4 added safe provider diagnostics. v0.1.5 lets `run_slate.py` use qualified provider odds. v0.1.6 adds data quality guardrails.

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

## Provider Diagnostics

v0.1.4 adds:

```text
src/check_odds_provider.py
```

Run mock diagnostics without any API key:

```bash
python src/check_odds_provider.py
```

Run live The Odds API diagnostics after setting a local key:

```bash
export ODDS_API_KEY="your_key_here"
python src/check_odds_provider.py --provider the_odds_api
```

The diagnostics script writes:

```text
data/output/latest_provider_diagnostics.json
```

Safety rules:
- The API key is never printed in full.
- The API key should never be committed.
- Mock mode remains the default.
- Live provider errors are captured into readable JSON.
- The script can list matching soccer/FIFA/World Cup sport keys when the provider supports sport listing.

## Provider Odds in Slate Runs

v0.1.5 adds:

```text
src/slate_odds.py
```

Manual slate odds remain the default so normal development does not accidentally spend live API quota:

```bash
python src/run_slate.py
```

Use provider odds with the mock provider:

```bash
python src/run_slate.py --odds-source provider --odds-provider mock
```

Use provider odds with The Odds API:

```bash
python src/run_slate.py --odds-source provider --odds-provider the_odds_api
```

Provider odds mode:
- collects provider odds once per run
- applies market selection rules
- uses only qualified best prices
- matches provider lines to slate matches by match ID or team/date
- supports reversed provider team order when the target is still the slate home team
- falls back to manual slate odds unless `--no-manual-odds-fallback` is provided
- records provider metadata in prediction output and odds snapshots

For strict provider-only runs:

```bash
python src/run_slate.py --odds-source provider --odds-provider the_odds_api --no-manual-odds-fallback
```

## Data Quality Guardrails

v0.1.6 adds:

```text
src/data_quality.py
```

Each prediction now includes:

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

The model can still calculate a technical EV signal, but weak data can block that signal from becoming an actionable bet. For example, a technical `bet` becomes a final `pass` when guardrails identify simulation-only bootstrap mode, insufficient training data, unverified manual features, manual odds fallback, stale odds, or missing feature fields.

To mark slate features as verified, add metadata like this to a match:

```json
"data_quality": {
  "feature_source": "verified_dataset"
}
```

Trusted feature sources are:

```text
official_feed
verified_dataset
historical_backfill
model_feature_store
```

Until a match has enough completed training data and verified feature inputs, treat model output as research-only.

## Market Selection Rules

v0.1.3 adds configurable market rules in:

```text
config/bet_rules_config.json
```

The initial World Cup default profile supports:

- allowed markets
- allowed selections
- required sportsbooks
- minimum sportsbook availability
- minimum decimal odds
- maximum decimal odds
- single-leg enablement flag
- future parlay/SGP configuration placeholders

The current rules layer does **not** claim a bet is +EV by itself. It only decides whether a sportsbook price is eligible for analysis based on your configured market rules.

Later versions can add:

- single-leg filters
- 2-leg / 3-leg parlay rules
- same-game parlay rules
- target odds windows
- player-specific filters
- stake sizing
- P&L tracking

## The Odds API

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
- Optional odds validation for provider mode
- Monte Carlo reproducibility
- Empty slate execution
- Odds provider normalization
- Best-price selection
- Mock odds collection
- Market selection rules
- Target odds filtering
- Minimum sportsbook availability
- Provider diagnostics
- API key masking
- Safe live-provider missing-key behavior
- Provider odds resolution for slate runs
- Manual odds fallback
- Reversed team-order provider matching
- Data quality warnings
- Recommendation guardrails
- Stale odds detection

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
