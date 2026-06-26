# RSB Architecture Notes

RSB is currently World Cup-focused, but it is being built as an extensible analytics platform.

## Core Principle

Keep shared infrastructure separate from sport-specific analysis.

Shared infrastructure:
- Odds provider adapters
- Provider diagnostics
- Provider odds resolution for slate runs
- Data quality guardrails
- Odds normalization
- SQLite persistence
- EV calculations
- Model run tracking
- Prediction output
- Market selection rules
- Review notes
- Tests

World Cup-specific layer:
- Soccer features
- World Cup match schema
- World Cup model config
- World Cup markets
- Availability, lineup, injury, and rotation-risk context
- Tactical matchup context

Future sport-specific layers can be added later without rewriting the shared infrastructure.

## Extension Pattern

When adding something new, prefer this pattern:

```text
new data source -> new adapter -> provider diagnostics -> normalized output -> qualified odds resolution -> existing database shape
new sport -> new sport profile -> new feature module -> availability context -> tactical context -> data quality guardrails -> existing model/run pipeline
new bet type -> new rules config -> existing EV/reporting layer
new tracker -> new ledger tables -> existing predictions/results/odds history
```

## Provider Diagnostics Layer

`src/check_odds_provider.py` is the safety gate between mock odds and live provider odds.

It should be used before routing any live odds into model decisions.

Diagnostics should answer:
- Is the provider reachable?
- Is `ODDS_API_KEY` present locally?
- Is the key hidden from output?
- Can relevant sport keys be listed?
- Are expected sportsbooks returning lines?
- Are provider errors readable?

Mock mode remains the default so tests and local development do not depend on external API availability.

## Provider Odds Resolution Layer

`src/slate_odds.py` connects qualified provider odds into `src/run_slate.py`.

This layer should:
- collect provider odds once per model run
- evaluate odds through market selection rules
- expose only qualified best prices to predictions
- match odds to slate matches by match ID or team/date
- handle reversed provider home/away order safely when the requested target is still the slate home team
- fall back to manual slate odds unless strict provider-only mode is requested
- preserve provider metadata in prediction output and odds snapshots

Manual slate odds remain the default. Live provider odds must be explicitly requested so local development does not accidentally spend API quota.

## Availability Context Layer

`src/availability.py` models the actual expected version of each World Cup team.

This layer should track:
- confirmed versus projected lineup status
- lineup confidence
- expected starters available versus normal starter count
- lineup strength rating
- rotation risk
- B-team risk
- key absences and absence impact
- replacement quality
- returning players from injury
- recent injury-return risk
- minutes restrictions
- fitness concerns

The feature layer converts availability into model inputs such as lineup strength differential, starter availability differential, key absence impact differential, returning player risk differential, and minutes restriction differential.

## Tactical Matchup Layer

`src/tactical_matchup.py` models how two teams attack each other's tactical strengths and weaknesses.

This layer should track:
- pressing intensity
- buildup quality
- press resistance
- vulnerability to press
- defensive line height
- pace threat
- crossing volume
- aerial threat and aerial defense
- set-piece attack and defense
- counterattack threat
- transition defense
- midfield control
- formation flexibility
- manager tactical rating
- low-block comfort
- central and wide chance creation

The feature layer converts tactical context into model inputs such as press versus buildup, pace versus high defensive line, crossing versus aerial defense, set-piece edge, counterattack edge, central/wide chance creation edge, midfield control differential, formation flexibility differential, and manager tactical differential.

Major tactical mismatch flags are review warnings rather than automatic blockers. Missing, unverified, or low-confidence tactical context can block recommendations.

## Data Quality Guardrail Layer

`src/data_quality.py` separates technical EV math from actionable recommendations.

This layer should:
- warn when the model is running in simulation-only bootstrap mode
- warn when completed training data is below the configured minimum
- warn when match features are not marked as verified
- warn when sample, test, mock, or placeholder identifiers are detected
- warn when required feature fields are missing and defaults would otherwise hide the issue
- warn when availability data is missing or unverified
- warn when lineups are unconfirmed or low confidence
- warn when rotation/B-team risk is high
- warn when key players are absent, recently returned, or minutes restricted
- warn when tactical data is missing, unverified, or low confidence
- warn when tactical mismatch flags require review
- warn when manual odds or manual fallback odds are used
- warn when provider odds are stale or sportsbook coverage is weak
- expose `technical_recommendation` separately from final `recommendation`
- block weak technical signals from becoming actionable recommendations

A prediction can have a technical signal while the final guarded recommendation remains `pass`. This is intentional. The system should prefer no play over acting on weak data.

## Current Rules Layer

`config/bet_rules_config.json` is the first home for configurable market rules.

Current World Cup rule categories:
- allowed markets
- allowed selections
- required sportsbooks
- minimum sportsbook availability
- target decimal odds range
- single-leg/parlay/SGP feature flags

The rules layer does not create a recommendation by itself. It only decides whether a price is eligible to be analyzed by the model and EV engine.

## What Should Not Happen

Avoid:
- Hardcoding one sportsbook into prediction logic
- Mixing provider response formats directly into models
- Replacing historical tables when adding new features
- Letting sample data become training data
- Rewriting large modules when a small adapter/config would work
- Turning parlays on before backtesting and calibration exist
- Sending live provider odds into recommendations before diagnostics pass
- Allowing unqualified provider lines to bypass market rules
- Treating simulation-only bootstrap outputs as real-money decisions
- Hiding missing feature values behind silent defaults without warnings
- Treating a national team as full strength when lineups, rotation, or injuries say otherwise
- Treating a tactical matchup as neutral when tactical context is missing or low confidence

## Near-Term Roadmap

v0.1.x foundation:
- Input validation
- Odds provider abstraction
- Provider diagnostics
- Provider odds resolution for slate runs
- Data quality guardrails
- Availability, lineup, injury, and rotation-risk context
- Tactical matchup context
- Best-price shopping
- Configurable market rules
- Target odds filtering

v0.2.x modeling/data:
- Real historical World Cup dataset
- More complete feature engineering
- Backtesting foundation
- Calibration checks

v0.3.x performance analysis:
- Ledger
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
