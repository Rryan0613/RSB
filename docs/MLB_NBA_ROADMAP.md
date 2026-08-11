# MLB / NBA Roadmap

Status: Approved roadmap direction; version-specific implementation still requires ChatGPT approval.
Date: 2026-08-11
Current release baseline: v0.3.0
Next approved objective: v0.3.1 — MLB Statcast Data Foundation

This is a durable project-direction document, not an implementation spec. It records the roadmap decision made on 2026-08-11 and the reasoning behind it. It does not define any version's detailed schema, data contract, or code — those are separately scoped and approved at implementation-planning time for each version.

---

## 1. Purpose / why the roadmap changed

By v0.3.0, RSB had accumulated substantial reusable downstream decision infrastructure: candidate identity, odds conversion, implied probability, edge, EV, the Candidate Evaluation Contract, ranking, reporting, settlement primitives, backtest metric primitives, and sport/market capability primitives, including an MLB capability seed. That work is not wasted — it becomes valuable exactly when a real sport-specific probability engine exists to feed it.

What RSB does not yet have is the modeling middle that would make any of that infrastructure operationally useful for a new sport:

```
MLB historical data
  → modeling observations / features
  → probabilities
  → calibration
  → simulation
  → market projections
  → existing EV / candidate infrastructure
```

The previous tentative post-v0.3.0 sequence (Legacy Candidate Translation → Canonical Odds Snapshot Reconciliation → Candidate Persistence Framework → First MLB Runtime Skeleton) over-prioritized infrastructure around the frozen legacy World Cup system while this missing probability-generation middle still did not exist for any new sport. Reviewing an external MLB modeling reference highlighted that RSB's reusable decision infrastructure had advanced further than its sport-specific probability-generation layer. That comparison is the origin of this reassessment, not a template RSB is copying — the roadmap below is derived from RSB's own architecture and needs.

That missing middle is now RSB's critical path, and MLB is where RSB builds it first.

## 2. Current architecture

**World Cup runtime** — operational, the only fully-wired end-to-end pipeline in the repository today. Frozen for new feature development: maintenance and bug fixes only. `run_slate.py` will not become a generic multi-sport orchestrator. See `docs/LEGACY_PIPELINE_ARCHITECTURE_AUDIT.md`.

**Pure-primitives foundation** — shared candidate identity, odds-snapshot, evaluation, EV enrichment, ranking, reporting, settlement, backtest-metric, and sport/market capability infrastructure. Sport-agnostic by design, and architecturally separate from the World Cup runtime above the shared math leaf (`ev.py`, transitively `odds.py`). See `docs/CANDIDATE_EVALUATION_CONTRACT.md`.

**MLB** — a capability seed only (`src/mlb_capability.py`, 15 declared market shapes built on `src/market_capability.py`). No data ingestion, no features, no probability model, no runtime exist today.

**NBA** — no implementation exists at any layer today.

## 3. Final sport scope

RSB's planned sport scope is:

- **World Cup** — existing, frozen legacy/reference implementation.
- **MLB** — first new sport engine.
- **NBA** — second and final new sport engine.

No NFL. No NHL. No additional sports are currently planned beyond World Cup, MLB, and NBA.

This is the approved current project scope. It should only change through an explicit future architecture decision, not by default drift or accumulation.

## 4. Why MLB first

MLB gives RSB an event-driven forecasting problem with a natural, well-bounded unit of observation — the plate appearance — and mature public historical data (Statcast/pitch-level history). That combination lets RSB build its first serious end-to-end sport-specific forecasting architecture on top of the existing shared foundation:

```
Statcast / pitch / plate-appearance history
  → normalized historical data
  → plate-appearance modeling observations
  → batter / pitcher / league context
  → probability generation
  → chronological evaluation / calibration
  → eventual game simulation
  → market projections
```

MLB is intended to teach RSB, concretely, how to take raw event data all the way through to a calibrated probability — the piece that has been missing regardless of how much downstream infrastructure existed.

## 5. Why NBA second

NBA is structurally different enough from MLB to serve as a genuine test of which RSB infrastructure actually generalizes, rather than infrastructure that happened to only ever see one sport. Directional NBA concepts, none of them scoped or approved:

- play-by-play / possessions
- minutes and rotations
- pace and usage
- player stat distributions (points, rebounds, assists, etc.)
- stronger correlation / joint-distribution requirements than a single plate appearance
- a larger, more compound prop surface (e.g. PRA-style combined props)

No NBA implementation roadmap is defined by this document. NBA will not share a mathematical model with MLB — each sport owns its own probability model, feature set, and simulation assumptions.

## 6. Abstraction rule

Build MLB concretely first. Reuse only infrastructure that is genuinely sport-agnostic — proven by actual reuse, not assumed in advance. Use NBA, once it starts, to test which abstractions from MLB's build actually generalize.

Do not build a universal sports-model abstraction prematurely. Sport-specific probability models, feature engineering, and simulation assumptions remain sport-specific; only the shared decision/reporting/math infrastructure is intended to be common.

## 7. v0.3.1 — MLB Statcast Data Foundation (approved next objective)

**Status:** Approved next at the roadmap/objective level. The detailed implementation plan still requires a separate inspection/planning stage and ChatGPT review before coding begins.

**Goal:** Obtain, normalize, provenance-tag, and locally snapshot trustworthy historical MLB/Statcast data for later modeling.

**Key architectural principles:**

- Evaluate Baseball Savant / Statcast as the historical data source.
- PyBaseball may be evaluated as a source adapter — not yet approved as a dependency.
- RSB's internal data contract must not simply be "whatever DataFrame the provider/library returns." The intended shape is: external provider/library → adapter → RSB-owned normalized representation.
- Preserve source, provenance, and as-of information on every normalized record.
- Design for reproducibility and historical snapshots, not a single mutable live pull.
- No plate-appearance probability model in this version.
- No simulation in this version.
- No sportsbook odds work in this version.
- No XGBoost, SciPy, or other new dependency added simply because an external reference project used it.

**Exit boundary (conceptual, not a schema):** a normalized raw historical MLB data foundation exists. Plate-appearance modeling and rate construction is v0.3.2 work, not v0.3.1 work.

The exact data contract, schema, and adapter design are v0.3.1 implementation-planning decisions, not defined by this roadmap document.

## 8. Directional v0.3.2 — MLB Plate-Appearance Dataset & Rate Foundation

**Status:** Directional planning batch; not an independently approved implementation scope.

- Transform normalized historical data (v0.3.1 output) into leakage-safe modeling observations.
- Likely one completed plate appearance per modeling observation.
- Prior-only batter/pitcher/league features — no information from after the observation's own timestamp.
- The terminal outcome taxonomy must become a mutually exclusive set suitable for later categorical probability modeling. The exact taxonomy is version-specific design work, not decided here.

## 9. Directional v0.3.3 — MLB Plate-Appearance Probability Baseline

**Status:** Directional planning batch; not an independently approved implementation scope.

A transparent baseline progression is expected, roughly:

1. League-only baseline.
2. Batter rate, with shrinkage toward league baseline.
3. Pitcher rate, with shrinkage toward league baseline.
4. Batter + pitcher + league matchup combination.
5. A later ML challenger, only if it earns its place.

**Critical invariant:** terminal plate-appearance probabilities must form one coherent probability distribution over mutually exclusive outcomes — not a set of independently produced event probabilities that sum to more or less than one.

An external batter/pitcher/league combination formula was reviewed as one possible reference hypothesis during the roadmap reassessment. It is not codified here as RSB's approved method — it may later be tested as one baseline among several, evaluated the same as any other candidate.

## 10. Directional v0.3.4 — MLB Walk-Forward Evaluation & Calibration

**Status:** Directional planning batch; not an independently approved implementation scope.

- Strict chronological (walk-forward) evaluation, no future leakage.
- Brier score and log loss.
- Reliability / calibration assessment.
- Comparison against the baseline progression from v0.3.3.
- Event-level and sample-count diagnostics.

**Important principle:** RSB should validate probability quality before investing in a large Monte Carlo simulation runtime. Simulation count does not compensate for a poorly calibrated probability model.

**Open design question, recorded but not resolved here:** `src/historical_replay.py` is a generally reusable, read-only SQLite replay pattern except for one function, `_derive_actual_label`, which hardcodes a soccer-specific `home_win`/`draw`/`away_win` outcome vocabulary (confirmed by direct code review; also classified "B — reusable concept, needs adaptation" by `docs/LEGACY_PIPELINE_ARCHITECTURE_AUDIT.md`). At v0.3.4 planning time, a decision is needed: reuse/generalize the safe read-only replay pattern with an MLB-appropriate label function, or introduce a separate MLB-specific replay component. This document intentionally does not resolve that question — it belongs to v0.3.4 implementation planning.

## 11. Directional later MLB work

No exact versions are locked after v0.3.4. Directionally, and in no fixed order yet:

- MLB game-state / Monte Carlo simulation runtime.
- MLB market probability projection.
- Sportsbook odds / candidate-EV bridge, connecting MLB probabilities to the existing `candidate_ev.py` / `candidate_ranking.py` / `candidate_report.py` infrastructure.
- Settlement and persistence.
- Daily/operational orchestration.
- Model tracking, calibration monitoring, CLV, and learning-loop infrastructure, as justified by evidence at the time.

Exact version numbers and ordering for this later work must be reassessed after v0.3.1–v0.3.4 are actually built and have taught RSB what the real next constraints are.

## 12. MLB market-capability note

`src/mlb_capability.py`'s 15 declared MLB markets (moneyline, run_line, total_runs, team_total_runs, player_hits, player_total_bases, player_home_runs, player_rbis, player_runs, player_stolen_bases, pitcher_strikeouts, pitcher_outs_recorded, pitcher_hits_allowed, pitcher_walks_allowed, pitcher_earned_runs_allowed) are declarative capability metadata only — a record of what a market *would* require if supported, not proof RSB can generate probabilities for it today.

This is not an implementation checklist. RSB does not promise all 15 markets as an immediate or near-term target. Market support expands only when the underlying model/state-simulation layer can legitimately generate the outcomes that market requires. Some markets (e.g. batter hits, home runs, total bases; pitcher strikeouts, walks allowed, hits allowed) are plausible early targets once a plate-appearance-level model exists; others (RBIs, runs, stolen bases, team/game totals, moneyline) require richer game-state and baserunner sequencing than a single-plate-appearance model provides, and will come later if and when that state model exists.

## 13. Dependency policy

**Current dependencies:** NumPy, pandas, scikit-learn, joblib.

**Potential future dependencies, none approved yet:**

- **PyBaseball** — evaluate only as part of v0.3.1 implementation planning (maintenance status, licensing/ToS, rate limits, API stability).
- **SciPy** — add only when an approved statistical method actually requires functionality not already available cleanly from NumPy/scikit-learn.
- **XGBoost** — a later optional challenger model only, never automatically preferred for being more sophisticated.

Sophistication alone is not a promotion criterion. Any model, statistical baseline or ML, is evaluated using leakage-safe, out-of-sample probability quality (Brier score, log loss, calibration) — not by reputation or by what an external reference project used.

## 14. Post-RSB direction

After MLB and NBA reach an explicitly defined finished RSB state:

- RSB does not default to adding further sports.
- Lessons from RSB (data engineering, statistical modeling, calibration, walk-forward evaluation, simulation, versioning, provenance) may inform a **new, separate** non-sports probabilistic forecasting / quantitative project.
- A possible future domain — financial markets, or another forecasting problem — is only an illustrative example, not a decision.
- RSB itself does not gain finance-specific abstractions (tickers, assets, trading signals, portfolios) now or as part of this transition. RSB does not become a stock project.

## 15. Immediate next action

After this documentation chore merges, the next step is a separate **v0.3.1 inspection/planning stage** for MLB Statcast Data Foundation. No MLB code is written until that implementation plan is reviewed and approved by ChatGPT.
