# MLB Plate-Appearance Probability Contract

**Status:** Architecture document, v0.3.3.
**Builds on:** the v0.3.2 MLB Plate-Appearance Contract (`docs/MLB_PLATE_APPEARANCE_CONTRACT.md`) and, through it, the v0.3.1 MLB Statcast Data Foundation. Neither is modified by this version.

---

## 1. Purpose

This document defines the v0.3.3 MLB Plate-Appearance Probability Contract: the outcome space, estimator family, leakage boundary, and output record shape used to turn v0.3.2's leakage-safe prior batter/pitcher/league outcome counts into a single coherent categorical probability distribution. It is implemented by `src/mlb/plate_appearance_probability.py`.

v0.3.3 is a **probability-generation baseline only**. It contains no evaluation, no calibration, no persistence, no simulation, no sportsbook odds/EV/ranking, and no MLB runtime orchestration. See §10 for the complete non-goals list.

## 2. Source contract reuse

This contract redefines nothing v0.3.2 owns. `RATE_CATEGORIES`, the completed-outcome taxonomy, `pitcher_rate_eligible`, the same-day cross-game leakage policy, and the nine `prior_*` fields are all defined by `src/mlb/plate_appearance.py` and `plate_appearance_rates.py`. The modeled outcome space is `RATE_CATEGORIES` verbatim.

The module's only inputs are records of the exact shape `attach_prior_outcome_rates` emits (`RATE_ENRICHED_FIELD_ORDER`); any other shape fails closed. A record's declared `normalized_pa_schema_version` must also equal the upstream `PLATE_APPEARANCE_SCHEMA_VERSION`, checked before the field is stripped away, so a record merely *shaped* like v0.3.2 but declaring an incompatible schema version can never be modeled. Schema metadata is not a realized PA outcome, so consulting it does not weaken the leakage boundary (§7).

## 3. What the probability means

Every distribution this module produces is:

```
P(outcome category | this plate appearance completes)
```

It inherits that conditioning directly from v0.3.2, which only ever counts `pa_status == "completed"` plate appearances into any numerator or denominator. Modeling *whether* a plate appearance completes is a distinct problem and is out of scope (§10).

These are **retrospective** distributions. Every PA record in RSB derives from already-observed pitch data, so this module scores history under strict prior-only information. It is not a live/upcoming-PA predictor; no such input contract exists anywhere in RSB today.

## 4. Outcome space

The modeled outcome space is exactly `RATE_CATEGORIES` (12 categories): `strikeout`, `walk`, `intentional_walk`, `hit_by_pitch`, `single`, `double`, `triple`, `home_run`, `field_out`, `fielders_choice`, `reached_on_error`, `catcher_interference`.

**Mutual exclusivity and exhaustiveness are inherited from v0.3.2, not re-derived.** Chronology-first terminal detection identifies exactly one terminal pitch per PA, and any ambiguity already fails closed at v0.3.2 ingestion. `TERMINAL_EVENT_TAXONOMY` and `DETAILED_TO_CATEGORY` are single-valued mappings, and v0.3.2's module-level assertions guarantee every taxonomy value lands in exactly one `RATE_CATEGORIES` member. Unrecognized terminal events already fail the batch closed upstream. Therefore every completed PA maps to exactly one category — never zero, never more than one.

**`intentional_walk` is modeled as its own categorical outcome**, never merged with `walk`. v0.3.2 preserved the distinction at every layer and explicitly deferred this decision to v0.3.3; this contract resolves it in favor of keeping them separate. IBB is low-frequency and heavily situational rather than a pure batter/pitcher skill draw, which is precisely the case the shrinkage in §5 handles correctly without special-casing: sparse IBB counts are pulled hard toward the league rate by the same mechanism used for every other category. No bespoke IBB logic exists anywhere in the module.

Merging IBB into `walk` for modeling would add a second bookkeeping layer for a problem shrinkage already solves. Excluding it from some distributions would break exhaustiveness, requiring a "completed, non-IBB" denominator that does not exist in v0.3.2 and making the output structurally incompatible with the 12-keyed `prior_league_outcome_rates`.

## 5. Estimator family

A three-level hierarchy. `K = len(RATE_CATEGORIES) = 12`.

**Level 0 — uniform.** `U[k] = 1/K`.

**Level 1 — league, smoothed toward uniform.**

```
L[k] = (c_L[k] + alpha/K) / (n_L + alpha)
```

`alpha` is the **total** league prior strength, spread uniformly across the K categories (`alpha/K` per category). Because `alpha > 0`, every category retains strictly positive support even when never observed, which is what makes Levels 2 and 3 well defined with no epsilon clamping anywhere in the module. At `n_L == 0` this reduces algebraically to `U`, so **there is no separate no-history fallback branch**.

**Level 2 — entity, shrunk toward league.** For entity *e* (batter or pitcher):

```
p_e[k] = (c_e[k] + kappa_e * L[k]) / (n_e + kappa_e)
```

This is the closed-form posterior mean of a multinomial likelihood under a `Dirichlet(kappa_e * L)` prior. Normalization is automatic rather than imposed: the numerators sum to `n_e + kappa_e` because the counts sum to `n_e` and `L` sums to 1. At `n_e == 0` the result is exactly `L`, so unseen entities need no special case; as `n_e` grows the result approaches the raw empirical rate. Tiny samples degrade smoothly — there is no minimum-sample threshold anywhere in the module.

Batters and pitchers share one entity-agnostic implementation (`shrink_entity_distribution`).

**Level 3 — matchup.**

```
r[k] = b[k] * q[k] / L[k]
P[k] = r[k] / sum_j r[j]
```

Computed in log space with max-subtraction for numerical stability; every input is strictly positive, so all logs are finite.

This is **a multiplicative relative-likelihood categorical baseline, equivalent to classical log5 in the binary case**. It is not presented as an exact or uniquely canonical K-category generalization — it is one defensible baseline among several possible ones, and v0.3.4 evaluates it the same as any other candidate.

**Assumptions and known limitations.** The form assumes no interaction beyond each side's additive contribution in log space. It can be **overconfident**, because two same-direction deviations from league compound rather than average. Upstream shrinkage damps this; quantifying what remains is v0.3.4 calibration work, not something this contract asserts away.

**Limiting behavior — exact identities, not approximations:**

| condition | result |
|---|---|
| pitcher at league baseline | matchup = batter distribution |
| batter at league baseline | matchup = pitcher distribution |
| both at league baseline | matchup = league distribution |
| unseen entity (`n_e == 0`) | entity distribution = league distribution |
| no league history (`n_L == 0`) | league distribution = uniform |

## 6. Hyperparameters

| name | default | role |
|---|---|---|
| `league_prior_strength` (alpha) | `1.0` | positivity guarantee for the league baseline |
| `batter_prior_strength` (kappa_b) | `100.0` | batter shrinkage strength |
| `pitcher_prior_strength` (kappa_p) | `100.0` | pitcher shrinkage strength |

**These are not empirically optimized stabilization estimates. They are deterministic v0.3.3 baseline hyperparameters subject to comparative evaluation in v0.3.4.** A single scalar is shared across all 12 categories; per-category strengths are a possible later refinement, not a v0.3.3 baseline.

The values are necessarily provisional because choosing between them requires walk-forward out-of-sample scoring, which is v0.3.4's job. To keep that future retuning safe, all three strengths are explicit keyword arguments and **every output record carries the strengths actually used**, alongside `model_config_version`. Two artifacts both labelled `matchup_combination` can therefore never be silently incomparable.

## 7. Leakage boundary

`_extract_prior_context` strips every input record down to a fixed whitelist (`_PRIOR_CONTEXT_FIELD_ORDER`) before any math runs, and every probability function operates only on that stripped dict. Leakage is prevented by **field-set boundary**, not by trusting function bodies.

Deliberately excluded from the whitelist:

- `pa_status`, `pa_outcome_detailed`, `pa_outcome_category`, `terminal_pa_event_raw` — a predictor must never condition on how the plate appearance resolved, **nor on whether it resolved at all**.
- `prior_*_outcome_rates` — this module re-derives smoothed rates from raw counts, so the precomputed unsmoothed rates are unnecessary and stay outside the boundary.

**Completion status is not a gate.** A historical incomplete or `truncated_pa` plate appearance still has a well-defined pre-PA conditional distribution and receives one. Deciding which records carry a scorable categorical target is v0.3.4 evaluation work:

- completed PA → has a categorical target → eligible for Brier/log-loss
- incomplete/truncated PA → no categorical target → excluded from scoring

**Pitcher attribution is a gate.** For `pitcher_rate_eligible == False`, v0.3.2 records the *terminal* pitcher as `pitcher_id`, and `attach_prior_outcome_rates` attaches that pitcher's history. At the instant before the PA began, RSB could not have known that pitcher would enter, so conditioning on that identity is genuine within-PA future leakage — and generating a contaminated probability cannot be repaired by filtering it downstream.

| `pitcher_rate_eligible` | league_only | batter_shrinkage | pitcher_shrinkage | matchup_combination |
|---|---|---|---|---|
| `True` | allowed | allowed | allowed | allowed |
| `False` | allowed | allowed | raises | raises |

Pitcher-dependent methods raise `PitcherAttributionUnavailableError`, a subclass of the module error so a broad `except` still catches it while callers that want to skip such records can catch the specific type. `supported_methods_for` lets callers select records up front rather than using exceptions for control flow.

The batter side remains valid for these records because v0.3.2 validates `batter_id` as constant across every pitch of a PA, so the batter's identity *is* known before the PA begins.

**The terminal pitcher's identity is withheld, not just unused.** Gating the math is not sufficient on its own: a `league_only` or `batter_shrinkage` record for an ineligible PA would otherwise still carry `pitcher_id`, naming the pitcher who finished the plate appearance. That identity was unknown before the PA began, so embedding it would place future information inside an artifact framed as pre-PA, even though the probability values themselves are clean. Emitted records therefore carry:

| `pitcher_rate_eligible` | emitted `pitcher_id` |
|---|---|
| `True` | the pitcher (start and terminal are the same pitcher) |
| `False` | `None` |

`pitcher_rate_eligible` itself is retained as retrospective metadata, because v0.3.4 needs it to build the intersection sample described below.

**Documented consequence — selection bias.** Pitcher eligibility is itself knowable only after the fact, so any sample selected on it is not a random sample of plate appearances. **v0.3.4 must compare methods on the intersection of records all methods support**, not on each method's own denominator, or its Brier/log-loss comparison is not like-for-like. Every output record carries `pitcher_rate_eligible` so that intersection is trivially identifiable.

**Recorded, not implemented:** `source_pitcher_ids[0]` already *is* the PA-start pitcher (v0.3.2 builds that list in order of first appearance). What is missing is only that `attach_prior_outcome_rates` keys pitcher priors on the terminal `pitcher_id`. Attaching PA-start-pitcher prior state is a **v0.3.2-layer contract change** and is explicitly out of v0.3.3 scope.

## 8. Output contract

A plain dict shaped by `PROBABILITY_FIELD_ORDER`, built by `build_pa_probability_distribution` and checked by `validate_pa_probability_distribution` — the same build-and-validate pattern as v0.3.0's `validate_candidate_evaluation_record` and v0.3.2's shape validators. Value semantics come from plain-dict equality; RSB's immutability convention is procedural (build and return, never mutate), so no dataclass or frozen type is introduced.

`method` is a required keyword argument with no default, so the most complex method can never be selected by accident.

**Enforced invariants:**

- field set is exactly `PROBABILITY_FIELD_ORDER`
- `probabilities` is keyed by exactly `RATE_CATEGORIES`
- every probability is finite, **strictly positive**, and `<= 1`
- probabilities sum to 1 within `PROBABILITY_SUM_TOLERANCE` (`1e-9`), **validated and never silently renormalized**
- `model_method` is a member of `MODEL_METHODS`
- fields a method does not use are exactly `None`; fields it uses are populated
- pitcher-dependent methods require `pitcher_rate_eligible is True`
- `pitcher_id` is present when `pitcher_rate_eligible` is `True` and `None` when it is `False` (§7)
- `model_config_version` and `normalized_pa_probability_schema_version` match the module constants

**Canonical key ordering is a builder guarantee, not a condition of validity.** `build_pa_probability_distribution` always emits `probabilities` in `RATE_CATEGORIES` order, which is what keeps serialization and float summation bit-reproducible (§9). Validation is purely semantic: a mapping with the same 12 categories and the same values is the same distribution, and validates regardless of its insertion order. Python dict equality already ignores insertion order, so treating it as a validity condition would let a validator reject a record equal to one it accepts.

Strict positivity is guaranteed by construction whenever `alpha > 0`, so asserting it turns any future positivity regression into an immediate failure.

**Provenance fields.** Identity (`rsb_pa_id`, `source_game_id`, `at_bat_number`, `batter_id`) is carried through unchanged, and `pitcher_id` subject to the withholding rule in §7; `*_pa_count_used` and `*_prior_strength` record the evidence and hyperparameters behind the number, so any consumer can explain an output without re-running the computation.

**Internal machinery.** The leakage-boundary implementation (`_extract_prior_context`, `_PRIOR_CONTEXT_FIELD_ORDER`, `_BATTER_DEPENDENT_METHODS`) is private and deliberately not exported from `src/mlb/__init__.py`.

**Package-root API is the three entry points plus metadata.** `src/mlb/__init__.py` exports `build_pa_probability_distribution`, `supported_methods_for`, and `validate_pa_probability_distribution`, together with the error types and the model constants. The Level 1-3 estimator functions (`build_league_baseline_distribution`, `shrink_entity_distribution`, `build_batter_shrinkage_distribution`, `build_pitcher_shrinkage_distribution`, `combine_matchup_distribution`) remain module-level and importable from `mlb.plate_appearance_probability`, but are **not** package-root API: they take a `prior_context`, which only the private `_extract_prior_context` can legitimately produce from a rate-enriched record, so exporting them would advertise an entry point no caller can correctly reach. They are implementation and test primitives.

**v0.3.4 must compare estimators through `build_pa_probability_distribution(method=...)`**, not by reaching through these internals — that keeps the leakage boundary, provenance fields, and output validation on every path that produces a scored number.

## 9. Determinism

All iteration goes through the `RATE_CATEGORIES` tuple, never a dict's own key order, so floating-point summation order is fixed and repeated runs are byte-identical. `math.fsum` is used for probability sums. The module has no shared or global state; every function is pure and never mutates its inputs.

## 10. Explicit non-goals

No walk-forward evaluation, Brier score, log loss, or calibration (v0.3.4 — it consumes `probabilities` directly via the existing `brier_score_multiclass`/`log_loss_multiclass` in `src/backtest.py`, which need no changes). No empirical tuning of the prior strengths. No per-category prior strengths. No persisted probability artifact or manifest. No PA-start-pitcher prior contract. No handedness/platoon splits. No situational conditioning on base-out state, score, or inning. No park factors or opponent adjustment. No ML challenger model. No simulation, PA-opportunity/lineup modeling, or market projection. No sportsbook odds/EV/ranking. No MLB runtime orchestration. No prediction-time (upcoming-PA) input contract. No World Cup changes. No NBA changes. No handoff/roadmap/progress-dashboard synchronization — that remains a separate post-merge chore.
