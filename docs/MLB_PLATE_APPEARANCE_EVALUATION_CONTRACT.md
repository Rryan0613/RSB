# MLB Plate-Appearance Evaluation Contract

**Status:** Architecture document, v0.3.4.
**Builds on:** the v0.3.3 MLB Plate-Appearance Probability Contract (`docs/MLB_PLATE_APPEARANCE_PROBABILITY_CONTRACT.md`), the v0.3.2 MLB Plate-Appearance Contract (`docs/MLB_PLATE_APPEARANCE_CONTRACT.md`), and through them the v0.3.1 MLB Statcast Data Foundation. None of the three is modified by this version.

---

## 1. Purpose

This document defines the v0.3.4 MLB Plate-Appearance Evaluation Contract: the scorable-target rule, prior-state coherence validation, sampling and coverage semantics, metric hierarchy, calibration measurement, and report shape used to measure how well v0.3.3's per-plate-appearance categorical probabilities score and calibrate against realized outcomes. It is implemented by `src/mlb/plate_appearance_evaluation.py`, built on the generic diagnostic primitives in `src/calibration.py`.

v0.3.4 is a **measurement layer only**. It measures; it never adjusts a probability, selects a winning configuration, or changes a v0.3.3 default. It contains no recalibration, no automatic tuning, no persistence, no database access, no simulation, no sportsbook odds/EV/ranking, and no MLB runtime orchestration. See §16 for the complete non-goals list.

**Capability, not evidence.** Shipping this version establishes the leakage-safe evaluation and calibration-measurement capability. It does not, by itself, provide empirical evidence sufficient to select a winning method or hyperparameter configuration. That requires a real historical dataset to be separately supplied and evaluated.

## 2. Source contract reuse

This contract redefines nothing v0.3.2 or v0.3.3 owns. `RATE_CATEGORIES`, the completed-outcome taxonomy, `pa_status`, `pitcher_rate_eligible`, the same-day cross-game leakage policy, and the nine `prior_*` fields belong to `src/mlb/plate_appearance.py` and `plate_appearance_rates.py`. The four methods, the prior strengths, the field-set leakage whitelist, and the positivity/normalization guarantees belong to `plate_appearance_probability.py`.

**Walk-forward safety is inherited, not reimplemented.** `attach_prior_outcome_rates` already attaches, to every plate appearance, the batter/pitcher/league state that existed strictly before it, with counters frozen at each `game_date` boundary (v0.3.2 §9). The rate-enriched record *is* the walk-forward state. This module never re-derives priors, maintains its own counters, or reimplements the temporal policy — doing so would silently create a second, divergent definition of the same rule.

Because these are closed-form empirical estimators with no fitting step, walk-forward evaluation here requires **no refit loop**: it is chronological consumption of already-prior state, not repeated retraining.

The module's only record input is the exact shape `attach_prior_outcome_rates` emits (`RATE_ENRICHED_FIELD_ORDER`); any other shape fails closed. A record's declared `normalized_pa_schema_version` must equal the upstream `PLATE_APPEARANCE_SCHEMA_VERSION`.

**Estimators are reached only through the public entry point.** Every scored number is produced by `build_pa_probability_distribution(pa_record, method=...)`, never by reaching through v0.3.3's internal estimator functions, so the leakage boundary, provenance fields, and output validation stay on every path.

Scoring reuses `brier_score_multiclass` and `log_loss_multiclass` from `src/backtest.py` unchanged. Their `dict[str, float]` input shape is exactly what v0.3.3 emits, keyed by `RATE_CATEGORIES`.

## 3. What is measured

```
P(outcome category | this plate appearance completes)
```

evaluated against the category the plate appearance actually produced. The conditioning is inherited from v0.3.3 §3 and is not re-derived. Nothing here models *whether* a plate appearance completes.

These are **retrospective** measurements over already-observed history. RSB has no prediction-time (upcoming-PA) input contract, so this version cannot and does not measure live predictive performance.

## 4. Scorable target selection

**A plate appearance is scorable if and only if `pa_status == "completed"`.**

That is the whole rule. v0.3.2 already guarantees the cross-field invariant: a completed PA carries a `TERMINAL_EVENT_TAXONOMY` terminal event and a `pa_outcome_category` inside `RATE_CATEGORIES`, while an incomplete PA carries `None` for both. `truncated_pa` is a member of `INCOMPLETE_TERMINAL_EVENTS`, so it resolves to `incomplete` and is never scorable. The target label is `pa_outcome_category`.

**Completion status is read only at scoring time, and never flows backwards.** v0.3.3 emits a well-defined pre-PA distribution for incomplete and truncated plate appearances too, and withholds `pa_status` from the probability math through its field whitelist. Selecting scorable targets therefore cannot contaminate prediction even in principle. This version does not retroactively change v0.3.3 generation because a plate appearance later turned out to be truncated.

## 5. Prior-state coherence validation

Before anything is scored, the supplied prior state is verified against the upstream implementation:

```
supplied enriched history
        -> project each record to PLATE_APPEARANCE_FIELD_ORDER
        -> attach_prior_outcome_rates()
        -> compare all nine regenerated prior_* fields
        -> must match exactly
```

The regenerated state is used **only for validation**. Scoring continues to consume the supplied records.

Comparison is exact equality. Float equality is safe here because each rate is a single deterministic `count / pa_count` division on identical integers through the same code path, with no accumulation and no reordering.

Reusing `attach_prior_outcome_rates` also re-validates record shape, `pa_status`, and the terminal-event taxonomy for free, so this module does not duplicate those checks. A `PlateAppearanceRateError` from that call propagates unwrapped: it is the authoritative diagnosis of a malformed plate-appearance history.

**The guarantee is effect-based, not position-based.** An omission, edit, or splice is detected **when it causes at least one retained record's regenerated `prior_*` state to differ from its supplied state**. A change that leaves every retained record's prior state untouched is invisible. In practice this catches hand-edited or corrupted prior state, records spliced from two different enrichment runs, and head- and mid-history omissions.

**What this does not prove.** This is **prior-state coherence validation, not artifact-completeness validation.** Known blind spots:

- **Tail truncation may be undetectable.** No retained record's prior state depends on a dropped final date.
- **Omitted incomplete plate appearances may be undetectable.** They never update any counter, so their absence leaves every other record's prior state unchanged.
- **Some final-date omissions are undetectable even when they are not the last record in canonical order.** Because same-date games are deliberately frozen from each other (v0.3.2 §9), a plate appearance dropped from one game on the final retained date can leave every remaining record — including records from a later-sorting game on that same date — completely unchanged.

It proves the supplied records are mutually consistent under v0.3.2's own algorithm. It does not prove the history is globally complete. Each limitation is asserted by test, alongside a complementary test showing that an omission which *does* change retained prior state is still rejected.

## 6. Intersection sample and coverage

**Comparative metrics are intersection-only.** The scored sample is the set of completed plate appearances that **every** supplied model configuration natively supports. There is no sample-basis parameter and no per-method denominator option: permitting one would make cross-configuration numbers silently incomparable.

- If every configuration is `league_only` or `batter_shrinkage`, the intersection is **every completed plate appearance** — there is no pitcher restriction.
- As soon as one pitcher-dependent configuration is present, records with `pitcher_rate_eligible = False` leave the sample, so all configurations share one denominator.

**Coverage is reported separately and never folded into a metric.** The `coverage` block carries input/completed/incomplete counts, pitcher eligibility counts, the intersection size, cold-start counts, the date and calendar-month span, and `method_support` — each method's natively supported completed-PA count. A reader can therefore see exactly what `pitcher_shrinkage` gives up without being tempted to score it on its own denominator.

The `zero_*_history_pa_count` fields are computed over the **scored intersection sample**, not the whole input: they exist to expose cold-start distortion in the metrics, and only scored records reach a metric.

**Documented consequence — selection bias.** Per v0.3.3 §7, pitcher eligibility is knowable only after the fact. When a pitcher-dependent configuration is present, the intersection is not a random sample of plate appearances. Its metrics are like-for-like **between methods**, and must never be presented as generalizing to all plate appearances.

**Coverage basis.** `coverage_basis` is `"normalized_pitch_represented_pa"`, inherited verbatim from v0.3.2 §10. Every denominator means completed plate appearances *represented by the normalized pitch source*, not an authoritative MLB total. The constant is duplicated rather than imported, because `plate_appearance_snapshot.py` pulls in the filesystem layer and this module is pure; a test asserts the two never drift.

**Temporal resolution.** Walk-forward here is **date-granular across games, not PA-granular**. The plate-appearance contract carries no game-start timestamp, so two games on the same date never inform each other's prior state in either direction. This is v0.3.2's deliberate under-use of same-day history, and reports state it rather than implying finer resolution.

## 7. Metric hierarchy

The hierarchy is part of the contract, because a diagnostic used as a verdict is a misuse of the report.

| tier | metric | role |
|---|---|---|
| primary | `mean_log_loss` | proper scoring rule; model comparison |
| primary | `mean_brier_score` | proper scoring rule; model comparison |
| secondary | `accuracy` | descriptive only |
| diagnostic | top-label reliability, ECE, MCE | calibration |
| diagnostic | 12 classwise reliability curves, ECE, MCE | calibration, per outcome |
| summary diagnostic | `macro_classwise_expected_calibration_error` | calibration overview |

**Model configurations are compared by the two proper scoring rules.** `mean_brier_score` is the sum-of-squares form over all 12 categories (range `[0, 2]`), not divided by K.

**Log loss is computed with a clamp that cannot bind on any valid v0.3.3 probability.** v0.3.3 guarantees strict positivity (`p > 0`), *not* any particular magnitude: its prior strengths accept every finite positive value, so a small but entirely valid `league_prior_strength` can drive the realized category's probability far below `backtest.py`'s default `epsilon = 1e-15`. Clamping there would silently floor `-log(p)` and understate log loss for exactly the overconfident configurations this version exists to detect — and log loss is a primary comparison metric, so the distortion would change which configuration looks better. The evaluator therefore passes `epsilon = math.nextafter(0.0, 1.0)`, the smallest positive representable float, so every valid v0.3.3 probability passes through unchanged. `src/backtest.py` is not modified; the epsilon is supplied at the call site.

Strict positivity alone is **not** sufficient to conclude that the default clamp is inert. That inference holds only near the default prior strengths, not across the configuration space this version is built to explore.

**Accuracy is descriptive.** In an outcome space where `field_out` alone is roughly 42% of plate appearances, argmax accuracy largely measures whether the model said `field_out`. Argmax ties break by `RATE_CATEGORIES` order so the number is deterministic.

**Calibration error must never rank configurations.** ECE and MCE are bin-dependent: different edges give different numbers for the same model. A model can also be well calibrated and still have poor discriminatory quality. Both facts are recorded in the report's own `notes`.

## 8. Calibration measurement

Two complementary views, both built from `calibration.build_reliability_bins`.

**Classwise, one-vs-rest, 12 curves.** For category `c`, the pairs are `(p[c], actual == c)`. This is what keeps `intentional_walk` visible as its own row rather than averaged into invisibility, and it is how v0.3.3 §5's flagged risk — that `matchup_combination` compounds same-direction deviations and may be overconfident — becomes measurable per outcome rather than asserted either way.

**Top-label confidence, 1 curve.** The pairs are `(max(p), actual == argmax(p))`. The direct test of overconfidence.

**A category with zero positive occurrences is still fully diagnosed.** Its one-vs-rest pairs are all `(p, False)`, which are valid reliability observations: `observed_frequency = 0.0` and `calibration_gap = -mean_predicted_probability`. A category predicted at 3% that never happens is measurably miscalibrated, and returning `None` would conceal that. Calibration statistics are `None` only when a bin set holds no observations at all, which cannot occur in a report because an empty sample raises (§14).

**Bin edges are fixed constants, not caller arguments.** `evaluate_pa_walk_forward` exposes no `bin_edges` parameter. Allowing one would leave an obvious researcher degree of freedom — trying different bins until a model looks better — in a version whose whole purpose is a standardized report. Both tuples are recorded in every report.

The two schemes are deliberately different, because the two probability distributions are different:

| constant | shape | why |
|---|---|---|
| `PA_CLASSWISE_CALIBRATION_BIN_EDGES` | skewed hard toward zero | one-vs-rest probabilities span roughly 0.0006 (`catcher_interference`) to 0.42 (`field_out`), with 8 of 12 categories below 0.05 |
| `PA_TOP_LABEL_CALIBRATION_BIN_EDGES` | concentrated on 0.10–0.60 | the max of K probabilities summing to 1 cannot fall below `1/K` (≈0.083 for K=12) and in practice clusters near 0.30–0.55 |

A single shared scheme cannot serve both: zero-skewed edges collapse every top-label observation into one bin, and top-label-shaped edges collapse every rare category into the first.

**The frequencies above are expected league-typical values, not measurements RSB has taken.** No real historical dataset has been evaluated at the time of writing (§1), so the edge placement is a justified prior judgement about the shape of the two distributions, not a fitted choice. The `1/K` floor on top-label probability is the one part that is arithmetic rather than assumption. Both tuples are fixed constants recorded in every report, so revising them later is an explicit, visible change rather than a silent one.

**`macro_classwise_expected_calibration_error`** is the **arithmetic mean** of the 12 per-category ECE values. It is unweighted deliberately: every classwise curve is built from the same scored sample and therefore holds the same number of observations, so weighting by count across classes would be an identity dressed up as a weighting. Within each class, ECE remains the standard count-weighted mean of `|calibration_gap|` across its non-empty bins.

**This summary statistic is weak in this outcome space and is not a verdict.** With 8 of 12 categories below 5% frequency, the macro average is dominated by correctly predicting near-zero for rare outcomes and will look good almost regardless of model quality.

## 9. Chronological diagnostics

Every window carries `calendar_month_diagnostics`: one row per calendar month, ascending, with exactly six fields — `calendar_month`, `scored_pa_count`, `mean_log_loss`, `mean_brier_score`, `accuracy`, `zero_league_history_pa_count`.

This exists because there is deliberately **no burn-in filter**. An arbitrary caller-controlled minimum-history threshold would be another researcher degree of freedom, so cold start is exposed descriptively instead: the earliest plate appearances have thin or empty league history, and without a breakdown that distortion would hide inside a single full-history mean.

The breakdown never filters a record — month counts always sum to the window total — and the bucket size is not a parameter. Calendar months are a natural temporal boundary, not a tunable analysis knob. Monthly rows carry no reliability curves; they are descriptive scoring only. A history spanning one month emits one row.

## 10. Split and holdout semantics

`split_date` is **measurement-only**.

- `split_date = None` — a single `full` window. Exploratory full-history measurement.
- `split_date` supplied — `tuning` (`game_date < split_date`) and `holdout` (`game_date >= split_date`), aggregated independently.

A hyperparameter sweep is simply N entries in `model_configs`. There is no search loop, no optimizer, and no automatic selection. `DEFAULT_LEAGUE_PRIOR_STRENGTH`, `DEFAULT_BATTER_PRIOR_STRENGTH`, `DEFAULT_PITCHER_PRIOR_STRENGTH`, and `PROBABILITY_MODEL_CONFIG_VERSION` are not changed by this version; adopting new defaults is a separate, separately-approved decision that would bump `PROBABILITY_MODEL_CONFIG_VERSION`.

**The rule code cannot enforce, stated here instead.** A configuration chosen by reading tuning-window metrics must be reported on the holdout window, and the holdout must not be consulted while choosing. **Once holdout metrics have been inspected and the compared configurations are then changed on the basis of those metrics, that holdout is contaminated for confirmatory use, and a fresh, untouched future holdout is required.**

## 11. Model configuration and dispatch

`build_evaluation_model_config(*, model_method, ...)` builds a validated, self-describing configuration. `model_method` is required and has no default, matching v0.3.3's rule that the most complex method can never be selected by accident.

All three strengths are validated even when the chosen method does not consume them, because each has a valid default and overriding one is a deliberate claim. Strengths the method does not use are then recorded as exactly `None`, both in the record and in `config_id`, so `league_only` at two different batter strengths is one configuration rather than two.

**Unused strengths are never forwarded to v0.3.3.** `build_pa_probability_distribution` validates every strength argument it receives *before* dispatching on method, and `None` fails that validation. The evaluator therefore passes only method-relevant keyword arguments and lets v0.3.3's own defaults apply to the rest. **v0.3.3 is not modified to accommodate this**; the dispatch boundary belongs to the caller.

`config_id = sha256(f"{model_method}:{alpha!r}:{batter!r}:{pitcher!r}:{model_config_version}")`, content-derived and never timestamp-salted, following `build_derived_dataset_id`'s precedent (v0.3.2 §12). Duplicate `config_id` values within one evaluation are rejected.

## 12. Output contract

A plain dict shaped by `REPORT_FIELD_ORDER`, built by `evaluate_pa_walk_forward` and checked by `validate_pa_evaluation_report` — the same build-and-validate pattern as v0.3.3. Because the validator is public and a report may arrive from anywhere, it fails closed on an internally **inconsistent** report, not merely a misshapen one: stored summary statistics are recomputed from the report's own contents, and counts must reconcile across coverage, windows, categories, calibration bins, and calendar months. It deliberately does not rescore the raw plate-appearance history — that would be a second evaluation, not validation — so it verifies self-consistency only. Every nested record is likewise a plain dict shaped by its own `*_FIELD_ORDER` tuple. No dataclasses are introduced; RSB's immutability convention is procedural.

**Enforced invariants:**

- field set is exactly `REPORT_FIELD_ORDER`
- all three schema versions match their module constants
- `sample_basis` is `"intersection"`
- `classwise_bin_edges` and `top_label_bin_edges` match the module constants
- `source_snapshot_id` is a non-empty string; `input_content_sha256` is a 64-character digest
- `coverage` matches `COVERAGE_FIELD_ORDER` and carries one `method_support` row per `MODEL_METHODS` member
- `results` carries exactly one entry per model configuration, and each `config_id` matches its embedded config
- window names are exactly `("full",)` or `("tuning", "holdout")`, consistent with `split_date`
- every window has at least one scored plate appearance
- `category_diagnostics` carries every `RATE_CATEGORIES` member in canonical order — always all twelve, never filtered
- calendar-month scored counts sum to the window total
- `notes` is a non-empty list of non-empty strings
- `input_content_sha256` is 64 lowercase hexadecimal characters; `split_date` is a real calendar date
- every result's embedded config is exactly the report's own `model_configs` entry for its `config_id`
- coverage counts reconcile: completed + incomplete equals input, eligible + ineligible equals input, intersection never exceeds completed, zero-history counts never exceed the intersection
- `method_support` carries every `MODEL_METHODS` member in canonical order, with counts never exceeding `completed_pa_count`
- window scored counts sum to `intersection_pa_count`, and every configuration shares identical denominators and date ranges
- category `actual_count` values sum to the window's scored count, and every `calibration_gap` agrees with `actual_frequency - mean_predicted_probability`
- reliability blocks carry the expected fixed edges, their bins validate as a contiguous partition of `[0, 1]`, their counts sum to the window's scored count, and stored ECE/MCE agree with recomputation
- `macro_classwise_expected_calibration_error` agrees with the arithmetic mean of the 12 category ECEs
- calendar-month rows are chronological, unique, and their scored counts sum to the window total

**`sample_basis` is recorded, not selectable.** A future version that adds another basis must bump `PA_EVALUATION_SCHEMA_VERSION`.

**Package-root API is the three entry points plus metadata.** `src/mlb/__init__.py` exports `build_evaluation_model_config`, `evaluate_pa_walk_forward`, and `validate_pa_evaluation_report`, together with `PlateAppearanceEvaluationError` and the public constants and field orders. Private helpers — the coherence check, the canonicalization helper, the sampling and windowing functions — are deliberately not exported.

## 13. Provenance and input identity

**Exactly one `source_snapshot_id` is required**, matching v0.3.2 §11's single-source-snapshot guarantee. Multi-snapshot splicing is rejected rather than silently accepted.

**`input_content_sha256`** is computed by a private pure helper: canonical chronological sort, each record rebuilt against `RATE_ENRICHED_FIELD_ORDER`, deterministic stdlib JSON serialization with recursive key sorting, SHA-256 over those bytes.

Recursive key sorting matters: the `prior_*_outcome_counts` and `prior_*_outcome_rates` fields are mappings, and two semantically identical histories must hash identically regardless of the insertion order of any mapping at any depth. List-valued fields such as `source_pitch_ids` and `source_pitcher_ids` keep their order, which is meaningful.

The hash identifies **the exact canonical rate-enriched input supplied to this evaluation**. It is deliberately *not* the persisted PA artifact's own content hash, and this module never claims to have verified an artifact it did not read. Two reports carrying the same digest were computed over the same input content.

Provenance carried in every report: the three schema versions, the single `source_snapshot_id`, `input_content_sha256`, both bin-edge tuples, `sample_basis`, `split_date`, and per configuration the `model_config_version` and the strengths actually used.

## 14. Failure semantics summary

| condition | behavior |
|---|---|
| `pa_records` not a list/tuple, or empty | `PlateAppearanceEvaluationError` |
| record is not a dict, or key set ≠ `RATE_ENRICHED_FIELD_ORDER` | fail closed |
| `normalized_pa_schema_version` mismatch | fail closed |
| duplicate `rsb_pa_id` | fail closed |
| `source_snapshot_id` not a non-empty string | fail closed (validated before set membership, so an unhashable value never leaks a `TypeError`) |
| more than one distinct `source_snapshot_id` | fail closed |
| prior-state coherence mismatch | fail closed, naming the `rsb_pa_id` and the first mismatched field |
| malformed plate-appearance history surfaced during coherence validation | `PlateAppearanceRateError` propagates unwrapped |
| `model_configs` empty, not a sequence, or duplicate `config_id` | fail closed |
| config record not self-consistent when rebuilt from its own fields | fail closed |
| `model_method` outside `MODEL_METHODS` | fail closed |
| prior strength non-numeric, non-finite, or ≤ 0 | fail closed |
| `split_date` not a string or `None`, not shaped `YYYY-MM-DD`, or not a real Gregorian date (e.g. `2024-02-31`, `2023-02-29`) | fail closed |
| no completed plate appearances at all | fail closed, naming completion as the cause |
| intersection empty because no completed PA is pitcher-attributable | fail closed, naming pitcher eligibility and the offending methods |
| `split_date` leaves the tuning window empty | fail closed, reporting the observed scored date range |
| `split_date` leaves the holdout window empty | fail closed, reporting the observed scored date range |
| a category has zero positive occurrences | **valid** — full calibration statistics still computed; not an empty sample |
| tail-truncated history | **accepted** — a stated limitation of §5, not an error |
| omitted incomplete plate appearances | **accepted** — a stated limitation of §5, not an error |
| `PitcherAttributionUnavailableError` escapes | not caught — propagates as a bug signal |

Records supported by every configuration are selected up front through `supported_methods_for`, exactly as v0.3.3 recommends, so exceptions are never used for control flow.

## 15. Determinism

All iteration goes through the `RATE_CATEGORIES`, `MODEL_METHODS`, and bin-edge tuples, never a dict's own key order. Input is sorted by `(game_date, int(source_game_id), at_bat_number)` — the same canonical key v0.3.2 uses — so supplied order never affects a result. Argmax ties break by `RATE_CATEGORIES` order. `config_id` and `input_content_sha256` are content-derived.

`math.fsum` is used for the aggregation **introduced by this version** — window and calendar-month mean log loss and Brier score, category mean predicted probability, and macro ECE. It is **not** claimed for the whole pipeline: `src/backtest.py` is unchanged, and the per-record metrics it computes still accumulate with ordinary addition. For the same reason this version does not call `backtest.mean`.

**The report carries no timestamp** and no clock is consulted anywhere, so a report is a pure function of its inputs and repeated runs are byte-identical. Every function is pure and never mutates its inputs.

## 16. Explicit non-goals

No recalibration or probability adjustment of any kind — no Platt scaling, isotonic regression, temperature or Dirichlet scaling. No automatic hyperparameter selection and no change to the v0.3.3 prior-strength defaults or `PROBABILITY_MODEL_CONFIG_VERSION`. No persisted evaluation artifact, manifest, or path helper. No supported read-only loader for persisted plate-appearance datasets. No database access. No `historical_replay.py` reuse or generalization. No changes to `src/backtest.py` or to any existing MLB module's logic. No new dependency. No user-configurable calibration bins, sample basis, burn-in threshold, or temporal bucket size. No per-category prior strengths. No situational conditioning on base-out state, score, or inning. No handedness/platoon splits, park factors, or opponent adjustment. No ML challenger model. No simulation, PA-opportunity/lineup/game-sequencing modeling, or market projection. No sportsbook odds/EV/ranking. No MLB runtime orchestration. No prediction-time (upcoming-PA) input contract. No PA-start-pitcher prior contract. No changes to `pyproject.toml`, `config/model_config.json`, or `CHANGELOG.md`. No World Cup changes. No NBA changes. No handoff/roadmap/progress-dashboard synchronization — that remains a separate post-merge chore.

## 17. Recorded, not implemented

Named here so they are not lost. **None is assigned to a version, approved, or scheduled.**

- **Supported read-only loader for persisted PA datasets.** `create_plate_appearance_dataset` writes `.jsonl.gz`, but nothing in RSB reads it back — `_load_existing_manifest` and `_load_existing_pa_bytes` are private idempotency checks. Until such a loader exists, evaluating a real persisted history requires the operator to load the records. Deliberately deferred so this version remains probability evaluation rather than probability evaluation plus a persisted-dataset consumption API.
- **Project-version metadata drift.** `pyproject.toml`, `config/model_config.json`, and `CHANGELOG.md` have fallen behind the release version. This is known metadata drift, not a separate version axis, and belongs to a dedicated maintenance chore.
- The v0.3.3 gaps remain unchanged: PA-start-pitcher prior contract; prediction-time input contract; PA-opportunity/lineup/game-sequencing model; handedness/platoon splits.
