# RSB Architecture Notes

RSB is currently World Cup-focused, but it is being built as an extensible analytics platform.

## Core Principle

Keep shared infrastructure separate from sport-specific analysis.

Shared infrastructure:
- Odds provider adapters
- Odds normalization
- SQLite persistence
- EV calculations
- Model run tracking
- Prediction output
- Review notes
- Tests

World Cup-specific layer:
- Soccer features
- World Cup match schema
- World Cup model config
- World Cup markets

Future sport-specific layers can be added later without rewriting the shared infrastructure.

## Extension Pattern

When adding something new, prefer this pattern:

```text
new data source -> new adapter -> normalized output -> existing database shape
new sport -> new sport profile -> new feature module -> existing model/run pipeline
new bet type -> new rules config -> existing EV/reporting layer
new tracker -> new ledger tables -> existing predictions/results/odds history
```

## What Should Not Happen

Avoid:
- Hardcoding one sportsbook into prediction logic
- Mixing provider response formats directly into models
- Replacing historical tables when adding new features
- Letting sample data become training data
- Rewriting large modules when a small adapter/config would work

## Near-Term Roadmap

v0.1.x foundation:
- Input validation
- Odds provider abstraction
- Best-price shopping
- Configurable bet rules

v0.2.x modeling/data:
- Real historical World Cup dataset
- More complete feature engineering
- Backtesting foundation
- Calibration checks

v0.3.x betting analysis:
- Bet ledger
- P&L tracking
- ROI
- W/L ratio
- Closing line value
- Performance by market/confidence tier

v0.4.x API layer:
- FastAPI service
- `/matches`
- `/odds`
- `/predictions`
- `/value-bets`
- `/model-runs`
- `/ledger`

## Current Scope

The active scope remains World Cup only. Future sports should be added only when the World Cup engine is stable enough to serve as a template.
