# MLB / NBA Roadmap

Status: Approved roadmap direction. v0.3.1 — MLB Statcast Data Foundation, v0.3.2 — MLB Plate-Appearance Dataset & Rate Foundation, and v0.3.3 — MLB Plate-Appearance Probability Baseline are merged to main (v0.3.1: PR #46, merge commit 3ae353f, implementation commit 765b5ed, 2156 tests passed; v0.3.2: PR #48, merge commit b876eb1, implementation commit 9212c93, real-Savant correction commit ba3ce68, 2307 tests passed; v0.3.3: PR #50, merge commit dcab8bb, implementation commit 72c4a8f, 2380 tests passed; see Handoffs for detail). v0.3.4+ still require their own version-specific implementation-planning approval.
Date: 2026-08-11
Last synchronized: 2026-08-18 — v0.3.3 merge verified.
Current release baseline: v0.3.3
Next roadmap objective (directional, not yet implementation-approved): v0.3.4 — MLB Walk-Forward Evaluation & Calibration

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

**MLB** — has a capability seed (`src/mlb_capability.py`), the v0.3.1 pitch-level Statcast historical data foundation, the v0.3.2 plate-appearance dataset/rate foundation, and the v0.3.3 plate-appearance probability baseline. That baseline is retrospective per-PA probability generation only: MLB still has no walk-forward evaluation or calibration, no simulation, no PA-opportunity/lineup model, no prediction-time (upcoming-PA) input contract, no sportsbook bridge, and no operational runtime/orchestrator.

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

## 7. v0.3.1 — MLB Statcast Data Foundation (merged)

**Status:** Merged and verified. PR #46, merge commit 3ae353f, implementation commit 765b5ed, 2156 tests passed. Feature branch feature/v0.3.1-mlb-statcast-data-foundation deleted locally and remotely.

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

## 8. v0.3.2 — MLB Plate-Appearance Dataset & Rate Foundation (merged)

**Status:** Merged and verified. PR #48, merge commit b876eb1, implementation commit 9212c93, real-Savant correction commit ba3ce68, 2307 tests passed. Feature branch feature/v0.3.2-mlb-plate-appearance-dataset-rate-foundation deleted locally and remotely.

**What shipped:** Transformed v0.3.1's normalized pitch-level Statcast records into leakage-safe plate-appearance (PA) modeling observations and prior empirical outcome rates, per `docs/MLB_PLATE_APPEARANCE_CONTRACT.md` (`src/mlb/plate_appearance.py`, `plate_appearance_rates.py`, `plate_appearance_snapshot.py`).

- One completed-or-incomplete PA per `(source_game_id, at_bat_number)` group, with a deterministic `rsb_pa_id` and contiguous per-group pitch-number chronology validation (fail-closed on gaps/duplicates/context mismatches).
- Chronology-first terminal-pitch detection separates `pa_status = "completed"` (classified into a closed detailed/category outcome taxonomy) from `pa_status = "incomplete"` (null terminal event, or a value in `INCOMPLETE_TERMINAL_EVENTS`).
- `intentional_walk` is kept distinct from ordinary `walk` at every layer — never merged.
- A real-Savant-backed correction (commit ba3ce68) added recognition of the `truncated_pa` terminal marker as `pa_status = "incomplete"`; it is deliberately excluded from the completed taxonomy and every rate denominator, with the raw value preserved (`terminal_pa_event_raw`) for provenance.
- Forward-only mid-PA pitcher substitutions are preserved (not rejected) but excluded from that PA's pitcher-rate attribution (`pitcher_rate_eligible = False`); the PA can still update batter/league history if otherwise completed. A pitcher sequence that reverts to an earlier pitcher fails closed.
- `attach_prior_outcome_rates` attaches leakage-safe prior batter/pitcher/league counts and raw empirical rates (no shrinkage, no priors, no smoothing) to every PA, using a same-day cross-game leakage policy that never lets two different games on the same date inform each other's prior state.
- Strict single-source-snapshot provenance validation and deterministic, content-derived immutable artifact identity (`derived_dataset_id`), consistent with v0.3.1's snapshot-immutability model but not timestamp-salted.
- No predictive/calibrated probabilities, shrinkage, ML, simulation, sportsbook odds/EV/ranking, or MLB runtime wiring — see `docs/MLB_PLATE_APPEARANCE_CONTRACT.md` §14 for the full non-goals list.

**Exit boundary (conceptual, not a schema):** a leakage-safe PA dataset and prior empirical rate foundation exists. Probability generation is v0.3.3 work, not v0.3.2 work.

## 9. v0.3.3 — MLB Plate-Appearance Probability Baseline (merged)

**Status:** Merged and verified. PR #50, merge commit dcab8bb, implementation commit 72c4a8f, 2380 tests passed (73 new probability tests). Feature branch feature/v0.3.3-mlb-pa-probability-baseline deleted locally and remotely.

**What shipped:** Turned v0.3.2's leakage-safe prior batter/pitcher/league outcome counts into one coherent categorical probability distribution per plate appearance, per `docs/MLB_PLATE_APPEARANCE_PROBABILITY_CONTRACT.md` (`src/mlb/plate_appearance_probability.py`).

The expected transparent baseline progression was implemented as four selectable methods, steps 1-4 of the anticipated sequence:

1. `league_only` — league categorical baseline, smoothed toward uniform.
2. `batter_shrinkage` — batter rate shrunk toward the league baseline.
3. `pitcher_shrinkage` — pitcher rate shrunk toward the league baseline.
4. `matchup_combination` — multiplicative batter/pitcher/league matchup baseline.

Step 5, a later ML challenger, remains future work and is not scheduled to any version.

- Batter and pitcher shrinkage share one entity-agnostic Dirichlet posterior-mean implementation; unseen entities reduce exactly to the league baseline, and no minimum-sample threshold exists anywhere in the module.
- **Critical invariant satisfied:** every method emits one coherent distribution over the 12 `RATE_CATEGORIES` — strictly positive, finite, and summing to 1 within `1e-9`, validated and never silently renormalized.
- `intentional_walk` is modeled as its own categorical outcome, never merged into `walk`. v0.3.2 deferred this decision to v0.3.3; this version resolved it in favor of keeping them separate, with sparse IBB counts handled by the same shrinkage as every other category rather than by bespoke logic.
- The matchup method is a multiplicative relative-likelihood categorical baseline, equivalent to classical log5 in the binary case. **`matchup_combination` is an approved, shipped v0.3.3 baseline.** The earlier "not RSB's approved method" caveat described the pre-implementation roadmap state and no longer applies to the implemented method. What is still **not** claimed is uniqueness: it is not the uniquely canonical K-category generalization, it is one defensible baseline among several, and it must still earn its place empirically in v0.3.4 evaluation like any other candidate. RSB's durable documentation never recorded the specification of the external combination formula reviewed during the roadmap reassessment, so this document asserts neither that the shipped method is that formula nor that it is not; any materially different variant would be a separate reference variant/hypothesis, evaluated the same as any other candidate.
- Leakage is enforced by field-set boundary: inputs are stripped to a whitelist before any math runs, excluding `pa_status`, `pa_outcome_detailed`, `pa_outcome_category`, and `terminal_pa_event_raw`. Completion status is deliberately not a gate — a historical incomplete or `truncated_pa` PA still receives a well-defined pre-PA distribution; deciding which records carry a scorable target is evaluation work.
- Pitcher attribution **is** a gate: when `pitcher_rate_eligible = False`, pitcher-dependent methods raise `PitcherAttributionUnavailableError` and the terminal `pitcher_id` is withheld from the emitted record, because that identity was unknowable before the PA began. `pitcher_rate_eligible` itself is retained as retrospective metadata.
- Hyperparameters are provisional and explicitly not empirically optimized (league prior strength 1.0, batter 100.0, pitcher 100.0). Every output record carries the strengths actually used alongside `model_config_version`, so two artifacts labelled with the same method can never be silently incomparable.
- No evaluation, calibration, tuning, persistence, simulation, handedness splits, situational conditioning, sportsbook work, or runtime orchestration — see `docs/MLB_PLATE_APPEARANCE_PROBABILITY_CONTRACT.md` §10 for the full non-goals list.

**Exit boundary (conceptual, not a schema):** coherent, leakage-safe, uncalibrated per-PA probabilities exist. Measuring whether they are any good is v0.3.4 work, not v0.3.3 work.

## 10. Directional v0.3.4 — MLB Walk-Forward Evaluation & Calibration

**Status:** Next roadmap objective, directional planning batch; not yet an independently approved implementation scope — requires its own inspection/planning stage and ChatGPT approval before coding begins.

- Strict chronological (walk-forward) evaluation, no future leakage.
- Multiclass Brier score and log loss. `brier_score_multiclass` and `log_loss_multiclass` already exist in `src/backtest.py` and consume v0.3.3's `probabilities` directly.
- Reliability / calibration assessment.
- Comparison against the baseline progression from v0.3.3.
- Outcome-level and sample-count diagnostics.

**Considerations recorded during v0.3.3, to be carried into v0.3.4 planning (none of them pre-approve an implementation):**

- **Intersection-sample comparison.** Pitcher-dependent methods are unavailable when `pitcher_rate_eligible = False`, and eligibility is knowable only after the fact, so a sample selected on it is not a random sample of plate appearances. Model-vs-model comparison should therefore run on the intersection of records all compared methods support, so competing methods share one evaluation denominator. Coverage should be reported separately rather than folded into the comparison. Every v0.3.3 output record carries `pitcher_rate_eligible` so that intersection is trivially identifiable.
- **Scorable-target selection.** v0.3.3 emits a distribution for incomplete and `truncated_pa` plate appearances as well; only completed PAs carry a categorical target and are eligible for Brier/log-loss scoring. Deciding and enforcing that split is v0.3.4's job.
- **Provisional hyperparameters.** v0.3.3's league/batter/pitcher prior strengths (1.0 / 100.0 / 100.0) are deliberately provisional and not empirically optimized. v0.3.4 should evaluate and tune model configurations chronologically and compare them explicitly, rather than silently changing defaults.
- **Multiplicative matchup overconfidence.** The matchup baseline can compound same-direction batter and pitcher deviations from league rather than averaging them, which may make it overconfident. Upstream shrinkage damps this; how much remains should be measured through calibration, not assumed good or bad in advance.
- **`intentional_walk` visibility.** IBB remains its own category. It is low-frequency and heavily situational, and that should be visible in outcome-level evaluation rather than hidden by merging it into ordinary walks.
- **Compare through the public entry point.** Estimators should be compared through `build_pa_probability_distribution(method=...)`, not by reaching through module internals, so the leakage boundary, provenance fields, and output validation stay on every path that produces a scored number.

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

### Named architectural gaps identified during v0.3.3

These were discovered while building the probability baseline and are recorded here so they are not lost. **None of them is assigned to a version, approved, or scheduled**, including to v0.3.4:

- **PA-start-pitcher prior contract.** `attach_prior_outcome_rates` keys pitcher priors on the *terminal* `pitcher_id`, which is why mid-PA-substitution plate appearances are excluded from pitcher-dependent methods. `source_pitcher_ids[0]` already is the PA-start pitcher, so a future contract could attach PA-start-pitcher prior state and recover that pitcher-dependent coverage. This would be a v0.3.2-layer contract change, not a probability-layer change.
- **Prediction-time (upcoming-PA) input contract.** Every PA record in RSB derives from already-observed pitch data, so v0.3.3 scores history only. No input contract for an upcoming, not-yet-played plate appearance exists anywhere in RSB. This is the architectural gap between historical evaluation and operational prediction.
- **PA-opportunity / lineup / game-sequencing model.** Per-PA probabilities alone do not produce player game-level markets. Something must model how many plate appearances a batter gets, against which pitchers, in what order. This sits between v0.3.3's per-PA distributions and markets such as hits, total bases, or home runs.
- **Handedness / platoon splits.** A strong candidate for a future challenger feature, evaluated the same as any other candidate. It is deliberately not assigned to v0.3.4 or to any other version.

Exact version numbers and ordering for this later work must be reassessed after v0.3.1–v0.3.4 are actually built and have taught RSB what the real next constraints are.

## 12. MLB market-capability note

`src/mlb_capability.py`'s 15 declared MLB markets (moneyline, run_line, total_runs, team_total_runs, player_hits, player_total_bases, player_home_runs, player_rbis, player_runs, player_stolen_bases, pitcher_strikeouts, pitcher_outs_recorded, pitcher_hits_allowed, pitcher_walks_allowed, pitcher_earned_runs_allowed) are declarative capability metadata only — a record of what a market *would* require if supported, not proof RSB can generate probabilities for it today.

This is not an implementation checklist. RSB does not promise all 15 markets as an immediate or near-term target. Market support expands only when the underlying model/state-simulation layer can legitimately generate the outcomes that market requires. Some markets (e.g. batter hits, home runs, total bases; pitcher strikeouts, walks allowed, hits allowed) are plausible early targets once a plate-appearance-level model exists. v0.3.3 delivered a per-PA probability baseline, but that is not yet sufficient on its own: reaching those player game-level markets still requires the PA-opportunity / lineup / game-sequencing gap named in §11, and probability quality still has to be validated. Others (RBIs, runs, stolen bases, team/game totals, moneyline) require richer game-state and baserunner sequencing than a single-plate-appearance model provides, and will come later if and when that state model exists.

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

v0.3.3 — MLB Plate-Appearance Probability Baseline has merged (PR #50). The next step is a separate **v0.3.4 inspection/planning stage** for MLB Walk-Forward Evaluation & Calibration. No v0.3.4 MLB evaluation/calibration code is written until that implementation plan is reviewed and approved by ChatGPT.

## 16. Future MLB operational requirements

**Status:** Directional architectural requirements, recorded here so they are not lost across handoffs. **These are not v0.3.4 implementation scope.** Each requires its own separately scoped and ChatGPT-approved implementation plan when RSB reaches it. Do not implement any part of this section as a side effect of v0.3.4 or any other current chore.

### A. On-run historical synchronization and completeness

When a future operational MLB analysis run starts, RSB must:

- determine the latest successfully stored / complete historical coverage
- determine the missing range through the current run date
- include a configurable recent overlap/backfill window so provider corrections can be rediscovered
- ingest/reconcile that range idempotently
- verify expected games / mandatory data completeness
- refuse downstream model execution when mandatory historical data remains incomplete or conflicted
- perform this at run time; no continuously running/background updater is required

The representative v0.3.2 Savant audit encountered a provider/export result boundary that left partial PA pitch sequences in the oldest included data. The current fail-closed chronology checks correctly rejected that incomplete coverage. This provides concrete evidence for future safe query chunking, coverage verification, overlap/backfill, and completeness controls. (This observation is not connected causally to `truncated_pa` — the audit did not establish why Baseball Savant emits that marker.)

### B. External production persistence

Long-term production MLB history must not depend on Ryan's laptop filesystem as the canonical warehouse.

Direction:

- hosted relational database, preferably **PostgreSQL**, for structured/queryable data
- external **object storage** for large immutable raw/normalized snapshot artifacts
- local files only as temporary ingestion/cache artifacts
- exact hosted vendor remains undecided
- do not implement this in the current docs chore or v0.3.4 unless separately scoped

### C. Multi-source verification / reconciliation

Future approved data sources may independently verify important observations.

RSB should preserve provenance and support concepts such as:

```text
VERIFIED
UNVERIFIED
CONFLICTED
STALE
```

Important unresolved conflicts should be fail-closed where the downstream model requires those fields.

Cross-checking should be field-aware; multiple sites agreeing is not automatically multiple independent observations.

Do not add scraping or a provider integration in this chore.

### D. Simulation-driven MLB analysis

Historical data is the evidence used to estimate and calibrate probability distributions; it is not itself the final prediction.

Future MLB flow should directionally be:

```text
historical data
→ leakage-safe observations/rates/features
→ calibrated PA probabilities
→ current matchup/context
→ MLB-specific simulation
→ game/team/player market probabilities
→ sportsbook EV/ranking
```

Simulation must be sport-specific and should occur only after probability quality is validated/calibrated.

This requirement must remain distinct from v0.3.4; v0.3.2 delivered the PA dataset/rate foundation and v0.3.3 delivered uncalibrated per-PA probabilities. Neither delivered calibrated probabilities or simulation, and reaching market probabilities from per-PA probabilities also requires the PA-opportunity / lineup / game-sequencing gap named in §11.
