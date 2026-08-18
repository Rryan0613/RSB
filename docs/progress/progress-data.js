window.RSB_PROGRESS = {
  schemaVersion: "2.0.0",
  lastVerifiedAt: "2026-08-18",

  sourceOfTruth: [
    "Handoffs/ChatGpt_Handoff.txt",
    "Handoffs/Claude_handoff.txt",
    "docs/LEGACY_PIPELINE_ARCHITECTURE_AUDIT.md (merged, PR #42)",
    "docs/CANDIDATE_EVALUATION_CONTRACT.md (merged, PR #43)",
    "docs/MLB_PLATE_APPEARANCE_CONTRACT.md (merged, PR #48)",
    "docs/MLB_PLATE_APPEARANCE_PROBABILITY_CONTRACT.md (merged, PR #50)",
    "docs/MLB_NBA_ROADMAP.md (current MLB/NBA roadmap; updated through v0.3.3)"
  ],

  project: {
    name: "RSB",
    subtitle: "Disciplined sportsbook analytics and +EV simulation research project",
    repository: "https://github.com/Rryan0613/RSB",
    productFocus: "Long-term target: MLB and NBA singles, PASS always a valid result. Today: pure decision-contract primitives plus a historical MLB Statcast data foundation, a plate-appearance dataset/rate foundation, and an uncalibrated per-plate-appearance probability baseline — no sport runtime is wired to them yet, and probability quality has not been measured. See Readiness."
  },

  statusLegend: [
    { key: "Verified complete", description: "Merged to main and supported by the repository's recorded review, validation, or test evidence as applicable." },
    { key: "Implemented, awaiting review", description: "Implementation exists outside the verified main baseline and is awaiting gatekeeper review or merge. It may be local or committed to a feature branch, as described by the active workspace." },
    { key: "Active planning", description: "Scope is being defined. No implementation exists yet." },
    { key: "Approved next", description: "Roadmap/objective scope is approved as next. Implementation may still require a version-specific plan review before coding begins." },
    { key: "Directional future", description: "Long-term intent recorded in project docs. Not a scoped or approved version." },
    { key: "Not built", description: "The target reusable or multi-sport operational capability does not exist. Isolated primitives, schemas, or frozen legacy components may exist, as described in the accompanying note." },
    { key: "Frozen legacy", description: "Fully functional and actively maintained, but closed to new feature development by an explicit architectural decision." }
  ],

  repositoryBaseline: {
    label: "Repository baseline (merged, verified)",
    latestMergedVersion: "v0.3.3",
    latestMergedVersionTitle: "MLB Plate-Appearance Probability Baseline",
    latestMergedVersionStatus: "Verified complete",
    latestMergedArchitectureChore: {
      title: "Legacy Pipeline Architecture Audit",
      identifier: "PR #42",
      note: "Read-only architecture audit reconciling the legacy World Cup runtime against the pure-primitives candidate contract. No source, config, schema, test, or CI changes were made by this chore — it is documentation only, not a version bump. Merged immediately before v0.3.0."
    },
    releaseEvidence: {
      prNumber: 50,
      mergeCommit: "dcab8bb",
      testCount: 2380,
      note: "Implementation commit 72c4a8f; 73 new probability-model tests; GitHub CI passed."
    },
    note: "The v0.3.3 release merge commit is dcab8bb (PR #50, implementation commit 72c4a8f). main is synchronized with origin/main; feature/v0.3.3-mlb-pa-probability-baseline was deleted locally and remotely after merge. This baseline card describes the verified v0.3.3 release. There is no active workspace beyond this baseline as of the post-v0.3.3 documentation sync."
  },

  activeWorkspace: null,

  currentGate: {
    version: "v0.3.4",
    title: "MLB Walk-Forward Evaluation & Calibration",
    status: "Active planning",
    owner: "ChatGPT (roadmap/gatekeeper) + Ryan (approval)",
    summary: "v0.3.3 — MLB Plate-Appearance Probability Baseline merged to main (PR #50, merge commit dcab8bb, implementation commit 72c4a8f, 2380 tests passed, GitHub CI passed). v0.3.4 — MLB Walk-Forward Evaluation & Calibration is now the next roadmap objective at the directional level — it was already recorded as a directional planning-batch entry. It is not yet implementation-approved: a separate v0.3.4 inspection/planning stage requires ChatGPT review of the detailed implementation architecture before coding begins. No v0.3.4 implementation has started. Considerations recorded during v0.3.3 for that planning stage: compare methods on an intersection sample so competing methods share one evaluation denominator (pitcher-dependent methods exclude pitcher_rate_eligible = false PAs) and report coverage separately; only completed PAs carry a scorable categorical target; v0.3.3 hyperparameters are provisional and should be evaluated chronologically rather than silently changed; the multiplicative matchup baseline may be overconfident and should be measured through calibration; intentional_walk should stay visible at the outcome level. See docs/MLB_NBA_ROADMAP.md §10.",
    nextActions: [
      "Perform the v0.3.4 inspection/planning stage for MLB Walk-Forward Evaluation & Calibration; ChatGPT must review and approve the detailed implementation plan before Claude begins coding."
    ]
  },

  principles: [
    "ChatGPT is the architecture reviewer, roadmap owner, and gatekeeper.",
    "Claude Code is the implementation agent and starts in plan mode.",
    "Ryan creates and verifies the feature branch before launching Claude.",
    "Ryan runs git validation commands and controls commit, push, PR, and merge actions.",
    "Sport-specific models share infrastructure, not one generic modeling layer.",
    "No automatic betting; weak evidence should produce PASS.",
    "The legacy World Cup runtime and the pure-primitives candidate pipeline are currently two disconnected systems — see Architecture."
  ],

  readiness: [
    {
      area: "Foundation contracts",
      status: "Verified complete",
      note: "The pure candidate identity/evaluation/enrichment/ranking/reporting/settlement chain (prop_candidate.py, candidate_evaluation.py, candidate_ev.py, candidate_ranking.py, candidate_report.py, prop_result.py) is merged but not wired into any operational runtime. The narrow verified exceptions are ev.py and odds.py, the shared leaf math the World Cup legacy runtime also uses — ev.py directly, odds.py only transitively through ev.py (see the architecture bridge for the exact import relationship). The Candidate Evaluation Contract's whole-record validator, candidate_evaluation.validate_candidate_evaluation_record(), merged to main in v0.3.0 (PR #43, commit 151010b) and is now part of this verified baseline."
    },
    {
      area: "Sport capability profiles",
      status: "Verified complete",
      note: "A generic sport/market capability schema (market_capability.py) and an MLB capability seed (mlb_capability.py) are merged. No World Cup, NBA, or NFL capability profile exists. A capability profile only declares supported market shapes — it is not a data pipeline or a runtime."
    },
    {
      area: "Provider and data ingestion",
      status: "Not built",
      note: "No provider source contract, canonical ID normalization, or coverage/staleness diagnostics exist for the pure-primitives pipeline. The legacy World Cup runtime has its own working odds_collector.py and odds_providers/ package, but it is scoped to World Cup only and frozen for new development. The v0.3.1 MLB Statcast data foundation (below) is a separate, MLB-specific, manual-CSV-only historical data pipeline — not a generic provider/ingestion contract."
    },
    {
      area: "MLB operational runtime",
      status: "Not built",
      note: "MLB has a capability profile seed (declared market shapes), a v0.3.1 manual-CSV-only historical Statcast data foundation (src/mlb/statcast_import.py, statcast_normalize.py, statcast_snapshot.py) that produces immutable, provenance-tagged raw/normalized pitch-level snapshots, a v0.3.2 plate-appearance dataset/rate foundation built on top of it (src/mlb/plate_appearance.py, plate_appearance_rates.py, plate_appearance_snapshot.py) that derives leakage-safe PA records and prior batter/pitcher/league empirical outcome rates, and a v0.3.3 per-PA probability baseline built on top of that (src/mlb/plate_appearance_probability.py). MLB still has no walk-forward evaluation or calibration pipeline, no simulation, no PA-opportunity/lineup model, no prediction-time (upcoming-PA) input contract, no sportsbook bridge, and no operational MLB runtime/orchestrator. None of the capability profile, the Statcast data foundation, the PA dataset/rate foundation, or the probability baseline is an operational runtime."
    },
    {
      area: "NBA operational runtime",
      status: "Not built",
      note: "No NBA-specific code exists at any layer — no capability profile, no data, no model, no orchestration."
    },
    {
      area: "Probability generation",
      status: "Frozen legacy",
      note: "The World Cup legacy runtime has a working sklearn model (model.py) and a Monte Carlo simulator (simulator.py), both frozen for new feature development. The pure-primitives pipeline has no probability generator by design — candidate_ev.py takes model_probability as caller-supplied input only. MLB gained a v0.3.3 per-plate-appearance categorical probability baseline (src/mlb/plate_appearance_probability.py), but it scores history retrospectively, is uncalibrated and unevaluated, has no prediction-time (upcoming-PA) input contract, and produces no market-level probabilities — so it is not an MLB probability engine in the operational sense. No NBA probability engine exists at any layer."
    },
    {
      area: "Calibration and backtesting",
      status: "Not built",
      note: "No MLB or NBA calibration/backtesting pipeline exists. Reusable statistical primitives are merged (backtest.py, backtest_report.py, backtest_review.py) and World Cup results ingestion works (update_results.py writes into the results table, and historical_replay.py can read predictions/results back out) — but no code in src/ currently chains historical_replay.py's output into backtest_report.py/backtest_review.py; each is callable but must be invoked by hand today. This is a partially-wired, World Cup-only capability, not an MLB/NBA operational pipeline. v0.3.3 now produces MLB per-PA probabilities that brier_score_multiclass/log_loss_multiclass could consume directly, but nothing scores them yet — that is the directional v0.3.4 objective."
    },
    {
      area: "Operational reporting",
      status: "Not built",
      note: "No MLB or NBA operational reporting exists. candidate_report.py is merged but unwired to any runtime. Separately, run_slate.py has its own working World Cup-only report/data-quality summary. The two exist independently of each other, and neither produces a cross-sport operational report."
    },
    {
      area: "Settlement and learning loop",
      status: "Not built",
      note: "prop_result.py defines a six-state settlement schema (pure, unwired). The legacy results table only stores boolean match outcomes with no void/push states and no lifecycle. No post-event review engine, miss-reason taxonomy, or controlled retraining loop exists at any layer."
    }
  ],

  architecture: [
    {
      id: "legacy",
      title: "World Cup legacy runtime",
      status: "Frozen legacy",
      description: "The only existing end-to-end runtime in the repository. Fully wired: config → slate → features → simulation/model → odds → data-quality guardrails → persistence → report. Frozen for new World Cup feature development per the architecture audit — bug fixes only. It is not planned to evolve into a general multi-sport orchestrator, ever.",
      nodes: [
        { title: "run_slate.py", detail: "World Cup-specific orchestration. The pipeline shape is reusable in the abstract, but current wiring and every stage call are hardcoded to soccer modules and constants." },
        { title: "features.py / simulator.py / tactical_matchup.py", detail: "Soccer-specific feature building and Monte Carlo goal simulation. Not reusable for other sports without new sport-specific modules." },
        { title: "model.py / availability.py / data_quality.py / market_selector.py", detail: "Artifact versioning, lineup context, guardrails, and price qualification. The mechanics are reusable patterns; the current fields and rules are World Cup-shaped." },
        { title: "database.py + odds_collector.py", detail: "SQLite persistence and provider odds collection. Runs today; the results table's outcome columns are soccer-specific." }
      ]
    },
    {
      id: "primitives",
      title: "Reusable pure-primitives foundation",
      status: "Verified complete",
      description: "Sport-agnostic records and calculations, independently built and tested. This foundation has no operational runtime or orchestrator of its own — the candidate identity/evaluation/enrichment/ranking/reporting/settlement chain is not invoked by any daily or sport-specific runtime. Some primitives import one another internally (for example candidate_ev.py calling candidate_evaluation.py, edge.py, and ev.py). ev.py and odds.py are the narrow legacy-connected leaf exceptions — see the architecture bridge below for the exact relationship. At the candidate-record, evaluation, ranking, reporting, persistence, and orchestration levels, this foundation is not integrated with the World Cup runtime above.",
      nodes: [
        { title: "Identity + capability", detail: "prop_candidate.py, market_capability.py, mlb_capability.py — candidate identity and declared market shapes." },
        { title: "Odds + evaluation", detail: "odds_snapshot.py, candidate_evaluation.py — price observation and eligibility/rejection semantics." },
        { title: "Enrichment + ranking", detail: "candidate_ev.py, candidate_ranking.py — edge/EV attachment and ordering. Does not force a bet." },
        { title: "Reporting + settlement", detail: "candidate_report.py, prop_result.py — reviewable summaries and post-event settlement lifecycle." }
      ]
    },
    {
      id: "future-runtimes",
      title: "Future sport-specific runtimes",
      status: "Not built",
      description: "No MLB or NBA runtime exists today — shown here as intended direction only, never as a built system. When a future runtime is built, it must own its own sport-specific data, features, probability model, simulation assumptions, calibration, and market support, while reusing the shared infrastructure named below. It will be new, independent orchestration — not an extension of run_slate.py.",
      nodes: [
        { title: "MLB runtime (not built)", detail: "Would need orchestration, calibrated probabilities, and a prediction-time input path built on top of the existing MLB capability profile seed, the v0.3.1 Statcast data foundation, the v0.3.2 plate-appearance dataset/rate foundation, and the v0.3.3 per-PA probability baseline." },
        { title: "NBA runtime (not built)", detail: "Would need a capability profile, data ingestion, features, and probability model — none exist yet." },
        { title: "Shared infrastructure it would reuse", detail: "Identity, odds-snapshot, EV/edge math, candidate evaluation, ranking, and reporting primitives from the foundation lane above." }
      ]
    }
  ],

  architectureBridge: {
    title: "The only current bridge between the two systems",
    description: "The legacy World Cup runtime and the pure-primitives foundation share no orchestration, no eligibility vocabulary, and no persistence. The verified exception is the low-level math leaf. src/ev.py is imported directly by both sides: by run_slate.py, slate_odds.py, market_selector.py, and odds_providers/base.py on the legacy side, and by candidate_ev.py on the pure side. src/odds.py is imported directly only on the pure side (by edge.py, by candidate_ev.py, and by ev.py itself) — no legacy file imports odds.py directly; the legacy runtime reaches its logic only transitively, through ev.py's internal use of it. No other file, record shape, or status vocabulary is shared. This is not drawn as a connector between the two lanes above because no higher-level integration exists — only this narrow leaf dependency does."
  },

  modules: [
    { name: "run_slate.py", area: "Legacy orchestration", status: "Frozen legacy", purpose: "Orchestrates the full World Cup prediction pipeline: config → slate → train/predict → simulate → odds → data-quality → persist. The sequence shape is a reusable pattern in the abstract, but every stage call is hardcoded to World Cup modules and constants, and this file is not planned to become a shared multi-sport orchestrator." },
    { name: "simulator.py", area: "Legacy probability", status: "Frozen legacy", purpose: "Vectorized Monte Carlo Poisson goal-rate simulation. Soccer-specific (goals, both-teams-to-score, over/under 2.5); not reusable for other sports without a new simulation model." },
    { name: "features.py", area: "Legacy features", status: "Frozen legacy", purpose: "Builds the World Cup model feature dict (FIFA rank diff, Elo diff, xG diffs). Soccer-specific inputs." },
    { name: "tactical_matchup.py", area: "Legacy features", status: "Frozen legacy", purpose: "Pressing, build-up, and set-piece matchup ratings and mismatch flags. Fully soccer-tactical vocabulary with no cross-sport analog yet." },
    { name: "availability.py", area: "Legacy features", status: "Frozen legacy", purpose: "Lineup, injury, and rotation-risk context and derived features. The trusted-source and confidence/risk accessor pattern is reusable; the specific fields assume an 11-starter sport (soccer)." },
    { name: "model.py", area: "Legacy probability", status: "Frozen legacy", purpose: "Trains/loads/predicts a per-market sklearn model and manages versioned artifacts with feature-schema safety checks. The artifact-versioning mechanics are a reusable pattern; the trained feature set and default target market are World Cup-specific." },
    { name: "data_quality.py", area: "Legacy guardrails", status: "Frozen legacy", purpose: "Master guardrail engine: warnings, severity, data-quality tri-state, and the recommendation gate separating technical EV signal from an actionable recommendation. The pattern is reusable; some specific warning codes are soccer-specific." },
    { name: "market_selector.py", area: "Legacy guardrails", status: "Frozen legacy", purpose: "Price qualification against allowed markets, odds bands, and book-count rules, producing qualified/rejected plus dynamic reason strings. The mechanics are reusable; the active config is hardcoded to World Cup markets." },
    { name: "database.py", area: "Legacy persistence", status: "Frozen legacy", purpose: "SQLite persistence across 8 tables (matches, feature_snapshots, predictions, simulation_outputs, odds_snapshots, results, model_runs, review_notes) plus the training-data leakage guard. Most of the framework is reusable; the results table's outcome columns (home_win/draw/away_win/btts/over_25) are soccer-specific." },
    { name: "slate_odds.py", area: "Legacy odds", status: "Frozen legacy", purpose: "Resolves qualified provider odds lines onto slate matches by match ID or team/date. The resolution strategy is reusable; the hardcoded prediction market assumes a 3-outcome soccer market." },
    { name: "odds_collector.py", area: "Legacy odds", status: "Frozen legacy", purpose: "CLI that collects, qualifies, and persists provider odds. Provider-agnostic orchestration; not itself World Cup-coupled beyond reading the current sports config." },
    { name: "odds_providers/ (base, mock, the_odds_api)", area: "Legacy odds", status: "Frozen legacy", purpose: "Provider adapter interface and implementations. base.py and the_odds_api.py are sport-agnostic; mock_provider.py's fixture data is World Cup-specific." },
    { name: "validation.py", area: "Legacy validation", status: "Frozen legacy", purpose: "Slate and result JSON schema validation. The validation pattern generalizes; the required-field list assumes a soccer match shape (home_team/away_team)." },
    { name: "update_results.py", area: "Legacy persistence", status: "Frozen legacy", purpose: "CLI that ingests results.json into the database. Thin and generic." },
    { name: "historical_replay.py", area: "Legacy backtesting", status: "Frozen legacy", purpose: "Read-only SQLite replay loader for backtesting. The query pattern is generic; the derived outcome labels (home_win/draw/away_win) are soccer-shaped." },
    { name: "check_odds_provider.py", area: "Legacy diagnostics", status: "Frozen legacy", purpose: "Diagnostics CLI gating live odds before they reach model decisions. Sport-agnostic." },
    { name: "import_claude_review.py", area: "Legacy utility", status: "Frozen legacy", purpose: "CLI that imports a review JSON into the review_notes table. Small and generic." },

    { name: "odds.py", area: "Shared leaf dependency", status: "Verified complete", purpose: "Odds format conversion and implied-probability primitives. Imported directly by the pure-primitives side (edge.py, candidate_ev.py) and by ev.py itself. No legacy file imports odds.py directly — the legacy runtime reaches it only transitively, through ev.py." },
    { name: "edge.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "calculate_edge(model_probability, implied_probability). Its only current importer is candidate_ev.py — not imported by any legacy module, so this is a pure-primitives-only primitive, not a shared leaf." },
    { name: "ev.py", area: "Shared leaf dependency", status: "Verified complete", purpose: "Expected-value math plus validated backward-compatible wrappers. Imported directly by both systems: by run_slate.py, slate_odds.py, market_selector.py, and odds_providers/base.py on the legacy side, and by candidate_ev.py on the pure side." },
    { name: "backtest.py", area: "Reusable backtesting primitive", status: "Verified complete", purpose: "Pure statistical primitives: Brier score, log loss, accuracy. Fully sport-agnostic. Its only current importer is backtest_report.py; it is not called by any runtime, legacy or pure." },
    { name: "backtest_report.py", area: "Reusable backtesting primitive", status: "Verified complete", purpose: "Aggregates replay rows into a backtest report. Duck-typed, no sport coupling. Its own docstring documents that rows must already be loaded by the caller (e.g. via historical_replay.load_replay_rows()); no file in src/ currently calls it — fully unwired, not part of any automated World Cup pipeline." },
    { name: "backtest_review.py", area: "Reusable backtesting primitive", status: "Verified complete", purpose: "Classifies a backtest report into strong/mixed/weak/insufficient_data. Pure thresholds, sport-agnostic. No file in src/ currently calls it — fully unwired." },
    { name: "config_validation.py", area: "Legacy-connected reusable primitive", status: "Verified complete", purpose: "Dependency-free JSON config loading and schema validation. Imported directly by 3 legacy runtime modules (run_slate.py, odds_collector.py, market_selector.py). No pure-primitives module imports it — legacy-connected, not shared between both architectural systems." },
    { name: "paths.py", area: "Legacy-connected reusable primitive", status: "Verified complete", purpose: "Central absolute path resolution and environment-variable overrides. Imported directly by 9 legacy runtime modules (run_slate.py, database.py, model.py, market_selector.py, odds_collector.py, check_odds_provider.py, update_results.py, historical_replay.py, import_claude_review.py). No pure-primitives module imports it — broadly used across the legacy runtime, but not shared between both architectural systems." },

    { name: "prop_candidate.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Prop/pick candidate identity schema (sport, league, event, market, selection, player/team context)." },
    { name: "odds_snapshot.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Sportsbook price observation schema, including odds_found_at for future closing-line-value comparison." },
    { name: "candidate_evaluation.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Candidate eligibility (candidate/rejected/not_evaluable) and closed pass-reason vocabulary. build_candidate_evaluation() and the field-level normalizers are unchanged since their original merge. validate_candidate_evaluation_record(), the whole-record validator, merged to main in v0.3.0 (PR #43, commit 151010b)." },
    { name: "candidate_ev.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Merges a candidate and an odds snapshot with a caller-supplied model_probability into edge, expected value, and an embedded candidate_evaluation record." },
    { name: "candidate_ranking.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Ranks candidate EV records by expected value, edge, and optional quality scores. Output shape, sort order, and successful-path behavior are documented as unchanged; the internal validation delegation to candidate_evaluation.validate_candidate_evaluation_record() merged to main in v0.3.0 (PR #43, commit 151010b)." },
    { name: "candidate_report.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Aggregates ranked candidate records into a reviewable report (ranked/excluded counts, pass-reason counts)." },
    { name: "prop_result.py", area: "Candidate pipeline (pure, unwired)", status: "Verified complete", purpose: "Six-state settlement lifecycle schema (pending/won/lost/push/void/unknown), independent of the legacy boolean results table." },
    { name: "review_taxonomy.py", area: "Review vocabulary (pure, unwired)", status: "Verified complete", purpose: "Review category, severity, and data-quality vocabulary. Independently defines a strong/okay/weak/unknown tri-state that is not reconciled with data_quality.py's tri-state yet." },
    { name: "review_notes.py", area: "Review vocabulary (pure, unwired)", status: "Verified complete", purpose: "Builds a single structured review note using review_taxonomy.py. Same domain concept as the legacy review_notes table but no code linkage." },
    { name: "stage_market.py", area: "Review vocabulary (pure, unwired)", status: "Verified complete", purpose: "Tournament stage and market-type vocabulary. Built with soccer tournament structure in mind; currently unwired and imported by no other module." },

    { name: "market_capability.py", area: "Capability profile", status: "Verified complete", purpose: "Generic sport/market capability schema builder — declares what a market requires (player/team/line/settlement fields), not a data pipeline." },
    { name: "mlb_capability.py", area: "Capability profile", status: "Verified complete", purpose: "MLB capability profile seed built on market_capability.py — declares 15 supported MLB market shapes. This is metadata only: no live provider integration, no odds ingestion, no predictive MLB modeling, and no runtime wiring." },

    { name: "mlb/statcast_import.py", area: "MLB data foundation", status: "Verified complete", purpose: "Reads a local, manually supplied Baseball Savant CSV export and validates file existence/readability/UTF-8/header structure. No automated Baseball Savant/MLB access — the operator supplies the file path. No baseball-semantic normalization at this layer." },
    { name: "mlb/statcast_normalize.py", area: "MLB data foundation", status: "Verified complete", purpose: "Builds the RSB-owned normalized pitch-level contract from the raw import. Fail-closed on missing/malformed required identity, chronology, game-context, or pre-pitch-state fields; provider-nullable fields normalize to null. No terminal-PA taxonomy derivation yet." },
    { name: "mlb/statcast_snapshot.py", area: "MLB data foundation", status: "Verified complete", purpose: "Orchestrates import to normalize to persist, writing three immutable artifacts per snapshot (raw .csv.gz, normalized .jsonl.gz, .manifest.json) with SHA-256 content hashes and full source provenance. Existing snapshot artifacts are never overwritten." },
    { name: "mlb/plate_appearance.py", area: "MLB data foundation", status: "Verified complete", purpose: "Groups v0.3.1 normalized pitches into one plate appearance per (source_game_id, at_bat_number), with contiguous chronology validation, chronology-first terminal-pitch detection, a closed completed-event taxonomy (intentional_walk kept distinct from walk), truncated_pa recognized as an incomplete-status marker (never a completed outcome), and forward-only mid-PA pitcher-substitution handling that excludes the PA from pitcher-rate attribution without discarding it." },
    { name: "mlb/plate_appearance_rates.py", area: "MLB data foundation", status: "Verified complete", purpose: "Attaches leakage-safe prior batter/pitcher/league empirical outcome counts and rates to every plate appearance, using a same-day cross-game leakage policy so two games on the same date can never inform each other's prior state. Raw empirical counting only — no shrinkage, priors, or modeling." },
    { name: "mlb/plate_appearance_snapshot.py", area: "MLB data foundation", status: "Verified complete", purpose: "Validates strict single-source-snapshot provenance against a v0.3.1 manifest before deriving anything, then persists a deterministic, content-derived plate-appearance dataset artifact (derived_dataset_id is not timestamp-salted, unlike v0.3.1's snapshot_id)." },

    { name: "mlb/plate_appearance_probability.py", area: "MLB probability baseline", status: "Verified complete", purpose: "Turns v0.3.2's prior batter/pitcher/league counts into one coherent categorical distribution over the 12 RATE_CATEGORIES via four methods: a league baseline smoothed toward uniform, batter and pitcher Dirichlet shrinkage toward that league baseline, and a multiplicative matchup combination (log5-equivalent in the binary case) computed in log space. intentional_walk stays its own outcome. Probabilities are strictly positive and validated to sum to 1 within 1e-9, never silently renormalized. Leakage is prevented by stripping inputs to a field whitelist that withholds the realized outcome and pa_status; pitcher-dependent methods fail closed and the terminal pitcher_id is withheld when pitcher_rate_eligible is false. Prior strengths (1.0 / 100.0 / 100.0) are provisional, not empirically optimized, and recorded on every output record. Retrospective scoring only — no evaluation, calibration, persistence, or runtime wiring." }
  ],

  milestones: [
    { version: "v0.1.8.6", title: "Backtest metric primitives", status: "Verified complete", group: "Backtesting" },
    { version: "v0.1.8.7", title: "Results ingestion safety", status: "Verified complete", group: "Backtesting" },
    { version: "v0.1.8.8", title: "Historical replay loader", status: "Verified complete", group: "Backtesting" },
    { version: "v0.1.8.9", title: "Training leakage guard", status: "Verified complete", group: "Validation" },
    { version: "v0.1.9.0", title: "Backtest report output", status: "Verified complete", group: "Reporting" },
    { version: "v0.1.9.1", title: "Feature variable upgrade", status: "Verified complete", group: "Features" },
    { version: "v0.1.9.2", title: "Stage and market semantics", status: "Verified complete", group: "Contracts" },
    { version: "v0.1.9.3", title: "Prediction review taxonomy", status: "Verified complete", group: "Review" },
    { version: "v0.1.9.4", title: "Prediction review notes", status: "Verified complete", group: "Review" },
    { version: "v0.2.0", title: "Odds and implied probability", status: "Verified complete", group: "Math" },
    { version: "v0.2.1", title: "Edge calculation primitives", status: "Verified complete", group: "Math" },
    { version: "v0.2.2", title: "Candidate evaluation record", status: "Verified complete", group: "Candidate" },
    { version: "v0.2.3", title: "Backtest review overlay", status: "Verified complete", group: "Review" },
    { version: "v0.2.4", title: "Odds expansion / EV math", status: "Verified complete", group: "Math" },
    { version: "v0.2.5", title: "Prop candidate schema", status: "Verified complete", group: "Candidate" },
    { version: "v0.2.6", title: "Odds snapshot / provider records", status: "Verified complete", group: "Candidate" },
    { version: "v0.2.7", title: "Prop result and settlement", status: "Verified complete", group: "Settlement" },
    { version: "v0.2.8", title: "Candidate EV enrichment", status: "Verified complete", group: "Candidate" },
    { version: "v0.2.9", title: "Candidate ranking primitives", status: "Verified complete", group: "Candidate" },
    { version: "v0.2.10", title: "Ranked candidate report primitives", status: "Verified complete", group: "Reporting" },
    { version: "v0.2.11", title: "Sport/market capability profile primitives", status: "Verified complete", group: "Capability" },
    { version: "v0.2.12", title: "MLB capability profile seed", status: "Verified complete", group: "Capability" },
    { version: "PR #42", title: "Legacy Pipeline Architecture Audit (merged, docs-only chore, no version bump)", status: "Verified complete", group: "Architecture" },
    { version: "v0.3.0", title: "Candidate Evaluation Contract", status: "Verified complete", group: "Architecture" },
    { version: "v0.3.1", title: "MLB Statcast data foundation", status: "Verified complete", group: "MLB data" },
    { version: "v0.3.2", title: "MLB plate-appearance dataset and rate foundation", status: "Verified complete", group: "MLB data" },
    { version: "v0.3.3", title: "MLB plate-appearance probability baseline", status: "Verified complete", group: "MLB modeling" }
  ],

  roadmap: [
    {
      phase: 1,
      title: "Capability and market understanding",
      status: "Verified complete",
      description: "Define the supported betting markets, the data shape each market requires, and one canonical eligibility contract. Sport/market capability profiles and the Candidate Evaluation Contract's whole-record validator are merged to main (v0.3.0, PR #43).",
      deliverables: ["Sport capability profiles", "Market field requirements", "Candidate Evaluation Contract"]
    },
    {
      phase: 2,
      title: "Provider and identity contracts",
      status: "Directional future",
      description: "Normalize providers, sportsbooks, leagues, teams, players, events, timestamps, and freshness. Earlier handoffs predicted this as the v0.3.0 scope; v0.3.0 instead delivered the Candidate Evaluation Contract (phase 1). As of the 2026-08-11 roadmap reassessment, v0.3.1 may establish MLB-specific source/provenance patterns that inform later generic provider and identity contracts. Generic provider/identity work remains separately unscoped.",
      deliverables: ["Provider source contract", "Canonical IDs", "Freshness and provenance metadata"]
    },
    {
      phase: 3,
      title: "Coverage and staleness diagnostics",
      status: "Not built",
      description: "Prevent incomplete, conflicting, or stale information from silently reaching the model.",
      deliverables: ["Coverage reports", "Staleness checks", "Missing-data policy"]
    },
    {
      phase: 4,
      title: "Automated historical and current ingestion",
      status: "Directional future",
      description: "Build the trustworthy data layer required by MLB and NBA models. This does not extend run_slate.py — it is new orchestration built on the pure-primitives foundation. v0.3.1 — MLB Statcast Data Foundation delivered the first concrete subset of this broader directional ingestion phase: a manual-CSV-only, provenance-tagged historical MLB/Statcast data pipeline (merged, PR #46). The rest of this phase — later games/results, player/team data, odds history, injuries/lineups, automated (non-manual-CSV) MLB ingestion, and eventual NBA ingestion — remains directional and not approved as a complete phase.",
      deliverables: ["MLB Statcast historical data foundation (v0.3.1, merged)", "Games and results", "Player and team data", "Odds history", "Injuries and lineups"]
    },
    {
      phase: 5,
      title: "Feature engineering and validation",
      status: "Directional future",
      description: "Keep variables that improve out-of-sample performance; reject fake-smart noise. v0.3.2 — MLB Plate-Appearance Dataset & Rate Foundation delivered a verified completed MLB deliverable within this phase: leakage-safe plate-appearance records and prior batter/pitcher/league empirical outcome rates (merged, PR #48). This phase remains broader than that one MLB release — it also covers future feature work and eventual NBA applicability — so the phase-level status stays directional future even though this specific deliverable is complete.",
      deliverables: ["MLB plate-appearance dataset and rate foundation (v0.3.2, merged)", "Sport-specific features", "Feature ablation", "Leakage-safe validation"]
    },
    {
      phase: 6,
      title: "Probability generation engines",
      status: "Directional future",
      description: "Generate RSB probabilities for supported MLB and NBA markets. v0.3.3 — MLB Plate-Appearance Probability Baseline delivered a verified completed MLB deliverable within this phase: one coherent, leakage-safe categorical distribution per plate appearance, with league/batter/pitcher/matchup methods (merged, PR #50). It is retrospective and uncalibrated, produces no market-level probabilities, and reaching player game-level markets additionally requires a PA-opportunity/lineup/game-sequencing model that does not exist. No NBA probability engine exists at any layer. The phase-level status therefore stays directional future.",
      deliverables: ["MLB plate-appearance probability baseline (v0.3.3, merged)", "Baseline models", "Simulation or ensemble models", "Probability calibration"]
    },
    {
      phase: 7,
      title: "Backtesting, calibration, and CLV",
      status: "Directional future",
      description: "Measure whether stated probabilities are accurate and whether prices beat the closing market, for MLB/NBA. Reusable backtesting/statistical primitives already exist (Verified complete). The World Cup system separately has working results ingestion and historical replay capability. Those pieces are not currently chained into one automated calibration/backtesting pipeline for World Cup, and no operational MLB or NBA calibration/backtesting system exists at all. Next roadmap objective for MLB: v0.3.4 — MLB Walk-Forward Evaluation & Calibration, still a directional planning batch entry, not yet an independently approved implementation scope. v0.3.4 also carries an open design question on whether to generalize historical_replay.py's read-only pattern or build a separate MLB-specific replay component, plus the comparison considerations recorded during v0.3.3 — see docs/MLB_NBA_ROADMAP.md §10.",
      deliverables: ["Brier score", "Log loss", "Calibration buckets", "Closing-line value"]
    },
    {
      phase: 8,
      title: "Decision policy and daily report",
      status: "Not built",
      description: "Return credible singles, acceptable price thresholds, and explicit PASS decisions.",
      deliverables: ["Eligibility policy", "Uncertainty controls", "Operational slate report"]
    },
    {
      phase: 9,
      title: "Settlement and controlled learning loop",
      status: "Not built",
      description: "Use aggregate evidence from settled predictions to recalibrate and improve future versions.",
      deliverables: ["Prediction log", "Settlement log", "Model-version tracking", "Review and retraining policy"]
    },
    {
      phase: 10,
      title: "NBA second-sport expansion and product interface",
      status: "Directional future",
      description: "After the MLB architecture is proven, build NBA as RSB's second and final new sport engine, then mature the product/interface layer. No NFL, NHL, or additional sport expansion is currently planned.",
      deliverables: ["NBA capability/runtime", "CLI/API/dashboard", "Scheduled operation"]
    }
  ],

  workflow: [
    { step: 1, actor: "Ryan", title: "Create feature branch", detail: "Switch to the approved feature branch and verify it before launching Claude." },
    { step: 2, actor: "Claude", title: "Inspect and plan", detail: "Plan mode only; no implementation before ChatGPT review." },
    { step: 3, actor: "ChatGPT", title: "Review the plan", detail: "Check scope, dependencies, ownership boundaries, and test strategy." },
    { step: 4, actor: "Claude", title: "Implement approved scope", detail: "Edit only the approved files and preserve established contracts." },
    { step: 5, actor: "Ryan", title: "Run git and test validation", detail: "Ryan runs branch, status, diff, and test verification commands himself." },
    { step: 6, actor: "ChatGPT", title: "Gatekeep completion", detail: "Review diffs and evidence before authorizing commit and PR." },
    { step: 7, actor: "Ryan", title: "Commit, push, and open PR", detail: "GitHub Actions must pass before merge." },
    { step: 8, actor: "Ryan + ChatGPT", title: "Post-merge verification", detail: "Confirm clean main, update handoffs, and advance the dashboard data." }
  ],

  updateChecklist: [
    "Verify the merge and resulting version.",
    "Update repositoryBaseline.",
    "Clear or replace the prior activeWorkspace.",
    "Add verified release evidence.",
    "Update changed module states.",
    "Update readiness and roadmap states.",
    "Set the next gate and exact next action.",
    "Update lastVerifiedAt.",
    "Review every page for stale or contradictory claims.",
    "Update the dashboard alongside the handoff documents."
  ]
};
