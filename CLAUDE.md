# RSB Project Instructions

RSB is a sportsbook analytics / +EV simulation project.

Current project status:
- Version: v0.1.8.1
- Python: 3.13 virtual environment
- Tests: pytest, currently 77 passing tests
- Current focus: World Cup simulation engine
- Future goal: automation-first sportsbook analytics website/app

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
