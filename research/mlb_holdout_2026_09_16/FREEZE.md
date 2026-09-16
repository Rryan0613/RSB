# MLB Real-Data Evaluation — Experiment Freeze (Pre-Registration)

**Sprint:** MLB real-data evaluation of the frozen v0.3.4 evaluator
**Branch:** `research/mlb-holdout-evaluation-2026-09-16`
**Repository baseline:** `d3d4c8c` (merge of PR #53); v0.3.4 implementation `9ec05cd`, merged `624673d` (PR #52)
**Baseline test state at freeze:** 2629 passed (full `pytest`, clean tree)

This document is written in stages. Stages 1-3 are recorded **before** any
holdout metric is inspected. Stage 4 records what happened afterwards. Nothing
in stages 1-3 may be edited once stage 4 begins.

---

## Stage 1 — Design (recorded before the dataset was built)

### 1.1 Objective

Measure, on real MLB data, how v0.3.3's four shipped probability methods score
and calibrate under v0.3.4's evaluator. This is a measurement exercise. It does
not select a production configuration and does not change any v0.3.3 default.

### 1.2 Methods under test (the pre-registered comparison)

All four shipped `MODEL_METHODS`, at the shipped v0.3.3 defaults:

| method | league_prior_strength | batter_prior_strength | pitcher_prior_strength |
|---|---|---|---|
| `league_only` | 1.0 | n/a (recorded as `None`) | n/a (recorded as `None`) |
| `batter_shrinkage` | 1.0 | 100.0 | n/a (recorded as `None`) |
| `pitcher_shrinkage` | 1.0 | n/a (recorded as `None`) | 100.0 |
| `matchup_combination` | 1.0 | 100.0 | 100.0 |

`config_id` values are recorded in stage 3.

### 1.3 Metric hierarchy (v0.3.4's, unchanged)

- **PRIMARY:** multiclass mean log loss; multiclass mean Brier score.
- **SECONDARY:** descriptive accuracy.
- **DIAGNOSTIC:** top-label reliability / ECE / MCE; 12 classwise reliability
  curves / ECE / MCE; macro classwise ECE; calendar-month diagnostics;
  coverage / method support; cold-start counts.

ECE is diagnostic. It is **not** used alone to rank or select a model. No single
diagnostic declares a winner.

### 1.4 Holdout protocol

- **Development / tuning period:** dataset start through **2026-08-11** inclusive.
- **Prospective holdout:** **2026-08-12** onward.
- `split_date = "2026-08-12"` (v0.3.4 partitions `game_date < split_date` as
  tuning and `game_date >= split_date` as holdout).

Order of operations, binding:

1. Build the dataset over the whole declared range.
2. Validate data quality over the whole range. **Declared exception:** data
   quality is inspected over the whole range, including holdout dates. This is
   contract validation, not model selection; no configuration, strength,
   formula, bin edge, sample rule or scoring rule may be chosen on the basis of
   it. Without it the experiment could not be shown to be valid at all.
3. Run the **exploratory strength sensitivity sweep on development-period
   records only** (`game_date < 2026-08-12`), by passing only those records to
   the evaluator. Inspect it. This answers whether 1 / 100 / 100 are defensible
   baselines without ever touching holdout outcomes.
4. **Freeze** the final configuration list (stage 3) and record it here.
5. Only then run the confirmatory evaluation with `split_date = "2026-08-12"`
   and inspect holdout metrics.

After step 5, the holdout is spent for confirmatory use. If a configuration,
strength, formula, bin edge, sample-selection rule or scoring rule is changed on
the basis of holdout results and the same holdout is scored again, that result
is exploratory, not confirmatory, and is labelled as such.

Chronological walk-forward updating of prior information within the holdout is
**not** contamination and is expected: v0.3.2 attaches to every PA only the
batter/pitcher/league state that existed strictly before it, so an Aug 13
prediction may use Aug 12 outcomes while an Aug 12 prediction may not use Aug 13.

### 1.5 What may not change after stage 4 begins

Configurations, prior strengths, model formulas, calibration bin edges,
sample-selection rules, scoring rules, and the split date.

---

## Stage 2 — Dataset identity (recorded after the build, before holdout inspection)

_Filled in by the build step; see `stage2_dataset_identity.md`._

## Stage 3 — Final frozen configuration list

_Filled in after the development-only sweep, before the confirmatory run; see
`stage3_frozen_configs.md`._

## Stage 4 — Post-holdout record

_Filled in after the confirmatory run; see `FINDINGS.md`._

---

## Stage 1.6 — Dataset-start assessment (recorded before any holdout metric was inspected)

An earlier draft of this sprint planned a **2026-05-30** dataset start, chosen
purely to fit an 8 GB machine. That start would have imposed an artificial
season-history cold start: all batter/pitcher/league history before May 30 would
have been absent, and the optimal shrinkage strength depends on how much history
each entity has, so it would have biased the answer to "are 1 / 100 / 100
reasonable?".

That constraint was re-measured at realistic scale and **does not hold**.

### 1.6.1 Why the first estimate was wrong

The original per-record memory rates were extrapolated from a 9-day, 7,093-PA
sample, where fixed interpreter and import overhead (~60 MB) dominated and
inflated the marginal rate roughly threefold. Re-measuring on a 253,000-pitch /
65,000-PA real sample (2026-03-25..2026-05-29) gave:

| phase | sample | peak RSS | marginal rate | full-season projection |
|---|---|---|---|---|
| build (v0.3.1 snapshot + v0.3.2 PA dataset, one process) | 252,751 pitches | 1.187 GB | ~4.7 KB/pitch | ~3.1 GB |
| evaluate (v0.3.4, 4 configs, tuning+holdout) | 64,998 PAs | 1.190 GB | ~18 KB/PA | ~3.2 GB |

Both fit an 8 GB machine with headroom. **The full 2026 regular season is
processable through the shipped single-snapshot contract path with no
architecture change, no chunked derivation, and no staged artifacts.**

### 1.6.2 Chunked derivation was assessed and is not needed

For completeness, date-chunked grouping was tested and shown to be *exactly*
equivalent to whole-set grouping: a plate appearance cannot span a `game_date`
(v0.3.2 §4 requires `game_date` constant within a group), so date-disjoint
chunks never split one. Grouping 9 days at once and grouping them in 3-day
chunks produced byte-identical PA records and byte-identical enrichment after a
single whole-set `attach_prior_outcome_rates`.

It is not used, because it would require abandoning the persisted,
content-addressed v0.3.1 snapshot and v0.3.2 derived artifact for the full
season — losing exactly the provenance and immutability guarantees that make
this result auditable. It is recorded here only as evidence that the memory
question was assessed on its merits rather than assumed.

### 1.6.3 Decision

**The dataset start is 2026-03-25 — Opening Day of the 2026 regular season.**
The evaluated range is **2026-03-25 .. 2026-09-15** (the last date with
completed games; today is 2026-09-16 and its games are not final).

The artificial cold start is therefore eliminated. The only remaining cold start
is the genuine season-opening one, which is a real property of the domain rather
than an artifact of this machine, and v0.3.4's calendar-month diagnostics and
`zero_*_history_pa_count` fields expose it directly.

Residual limitation, stated plainly: history is **single-season**. No batter or
pitcher carries prior-season history into 2026-03-25, so early-season priors are
genuinely thin and every entity's history depth is bounded by what 2026 itself
supplies. Cross-season history is not available in this dataset and building it
is not in scope here.

### 1.6.4 History depth entering the holdout

Quantified from development-period records only (see `stage2_dataset_identity.md`),
using the prior state attached to the last development date, 2026-08-11 — that
state *is* the history depth carried into the holdout. This is a property of
pre-holdout history, not of holdout outcomes, and cannot inform model selection
in any outcome-dependent way.

### 1.6.5 Fixed reference configuration

The shipped v0.3.3 defaults — `league_prior_strength = 1.0`,
`batter_prior_strength = 100.0`, `pitcher_prior_strength = 100.0` — are retained
as a **fixed reference** in every comparison, including the confirmatory run,
regardless of what the development-only sweep suggests. The confirmatory run
evaluates exactly the four shipped methods at those shipped defaults. The sweep
is exploratory context for question 7 and does not replace the reference.

---

## Stage 1.7 — Pre-registered data exclusion (recorded before any holdout metric was inspected)

A pre-flight audit of 252,790 real pitches / 65,006 real plate appearances found
exactly one class of contract contradiction, and it is the one v0.3.2 §4
explicitly anticipated and deferred:

| condition | PAs affected | v0.3.2 behavior |
|---|---|---|
| `pitcher_substitution_forward_only` | 26 | handled gracefully (§7): PA preserved, `pitcher_rate_eligible = False` |
| `batter_id_varies` | 8 | **fails the whole batch closed** (§4) |
| `batter_stands_varies` | 6 (subset of the 8) | **fails the whole batch closed** (§4) |

Nothing else was found: no `pitch_number` gaps, no game-context mismatches, no
pitcher reversions, no inconsistent `pitcher_throws`, no events on non-terminal
pitches, and **no unrecognized terminal event codes**.

The 8 fatal plate appearances (0.0123%, ~1 in 8,100) are genuine MLB events: a
pinch hitter entering mid-count, typically answering a mid-PA pitching change.
Verified example — game 822918, at-bat 49, 2026-04-06: batter 645302 (R) takes
pitch 1 against pitcher 641302; the pitcher changes to 668390 and the batter is
replaced by 641487 (L) with the count carried over at 0-1; 641487 completes the
PA with a `field_out`.

**Decision:** this is documented contract behavior, not an implementation
defect, so the contract is **not** changed. The affected plate appearances are
dropped from the CSV before ingestion and recorded explicitly.

- **Rule:** drop every `(game_pk, at_bat_number)` group whose pitch rows carry
  more than one distinct `batter` or more than one distinct `stand`.
- **Structural, never outcome-dependent**, and applied identically to
  development and holdout dates.
- Every other fail-closed condition is deliberately left to fail, so a new
  anomaly can never be hidden by this exclusion.
- The exact dropped keys are recorded in the snapshot manifest's
  `declared_query` and reported as a coverage loss.

This is a real architectural gap and is reported as such: v0.3.2 resolved mid-PA
*pitcher* substitution and left mid-PA *batter* substitution unresolved. It is
**not** assigned to any version number here.

---

## Stage 1.8 - Frozen exclusion set (recorded before any holdout metric was inspected)

**Rule.** Drop every (source_game_id, at_bat_number) plate-appearance group whose pitch rows carry more than one distinct `batter` id or more than one distinct `stand` value.

**Reason.** v0.3.2 s4 fails the whole derivation closed on a plate appearance containing multiple batter identities and explicitly defers resolving attribution to a separately scoped future change. These are genuine MLB events (a pinch hitter entering mid-count, typically answering a mid-PA pitching change), not corrupt data. This sprint does not change the contract, so the affected plate appearances are dropped pre-ingestion and reported as coverage loss.

**Outcome independence.** The `events` column is never read by the detector. The rule depends only on batter/stand structure within a group. No realized outcome, no metric, and no model performance influenced this exclusion, and the identical rule is applied to development and holdout dates.

**Declared range.** 2026-03-25 .. 2026-09-15, split 2026-08-12.

| quantity | value |
|---|---|
| source pitch rows in range | 669,982 |
| plate-appearance groups in range | 172,245 |
| excluded plate appearances | 21 |
| excluded fraction | 0.012192% |
| excluded PAs - development | 18 |
| excluded PAs - holdout | 3 |
| excluded pitch rows - development | 90 |
| excluded pitch rows - holdout | 12 |

### Every excluded plate appearance

| game_date | window | source_game_id | at_bat | pitches | batter ids | stands | rsb_pa_id (first 16) |
|---|---|---|---|---|---|---|---|
| 2026-04-06 | development | 822918 | 49 | 4 | 641487, 645302 | L, R | `0c47535c8f41f057` |
| 2026-04-07 | development | 824051 | 44 | 4 | 600869, 624585 | L, R | `a5fe3a4a56fbbe3a` |
| 2026-04-08 | development | 824374 | 14 | 6 | 676694, 694728 | R | `69ae379719823ea6` |
| 2026-04-09 | development | 823565 | 3 | 3 | 667670, 671732 | L, R | `9763d6960605629c` |
| 2026-04-17 | development | 823883 | 59 | 6 | 681715, 688363 | L, R | `44a2a93ac2fd1cc3` |
| 2026-05-12 | development | 823632 | 52 | 8 | 620443, 682626 | R | `e8eed0cb55e384b6` |
| 2026-05-18 | development | 823705 | 66 | 5 | 605170, 680777 | L, R | `df5873cc1c0bbc4e` |
| 2026-05-23 | development | 824674 | 39 | 3 | 670541, 701305 | L, R | `301925818ea6fdb4` |
| 2026-06-06 | development | 823048 | 53 | 4 | 663457, 686780 | L, R | `69e07481773ad907` |
| 2026-06-06 | development | 824915 | 73 | 5 | 664040, 691373 | L, R | `aa894d352e2e23ed` |
| 2026-06-09 | development | 824023 | 51 | 6 | 665861, 681351 | R | `703d987f939b824b` |
| 2026-06-15 | development | 824181 | 16 | 5 | 650402, 701678 | R | `abda48150cc12e80` |
| 2026-06-18 | development | 823533 | 28 | 7 | 665862, 683011 | L, R | `45dfca14d7817e77` |
| 2026-06-22 | development | 822800 | 46 | 4 | 665161, 694728 | R | `f7594b89d212f3f8` |
| 2026-07-10 | development | 823927 | 47 | 2 | 678489, 814439 | L, R | `341499ccfe4f05a4` |
| 2026-07-18 | development | 824169 | 32 | 5 | 572233, 664774 | L, R | `cf44247821f5c2e5` |
| 2026-07-22 | development | 824408 | 45 | 7 | 605170, 668952 | L, R | `7f23931ac84af486` |
| 2026-07-26 | development | 823028 | 37 | 6 | 668715, 695490 | L, R | `7cf397dc4a69c20e` |
| 2026-08-15 | holdout | 823671 | 67 | 2 | 607208, 702222 | L, R | `094ea28aa24bdab8` |
| 2026-08-16 | holdout | 824642 | 21 | 5 | 621020, 701649 | R | `fc987c791e6bb9eb` |
| 2026-09-01 | holdout | 822854 | 10 | 5 | 683021, 695720 | R | `6712a4eb4ab50549` |

Full-length `rsb_pa_id` values, the machine-readable record and the exact
detector are in `exclusion_freeze.json` and `freeze_exclusions.py`.

**Confirmation.** No realized outcome and no model performance influenced this
exclusion. The detector never reads the `events` column; it depends only on
`batter`/`stand` structure within a `(game_pk, at_bat_number)` group. The
identical rule was applied to development and holdout dates, and the exclusion set
was frozen in this document before any holdout metric was computed or inspected.

---

## Stage 5 — Post-sprint packaging record (2026-09-16)

Documentation-only corrections made while preparing this research package for a
durable research-only commit. **Stages 1–4 above were not edited.** No
experiment was rerun, the holdout was not reopened, and no recorded result was
regenerated or reinterpreted.

Two factual errors in `FINDINGS.md`'s earlier draft were found by re-reading the
recorded report JSONs and are corrected there:

1. **Pitcher-signal claim.** The draft said pitcher information is worth
   "approximately 1e-6 log loss" versus `league_only` and "adds almost nothing."
   That figure (8.470494e-07) is real but applies **only** to development log
   loss. On development Brier the gap is 0.001622, and on the holdout
   `pitcher_shrinkage p=100` beats `league_only` on **both** primary metrics by
   ~0.00222. Pitcher information carries real but comparatively weak signal —
   roughly 1/6 of `batter_shrinkage`'s holdout log-loss gain. Corrected in
   `FINDINGS.md` §6.4.

2. **Ordering-reproduction claim.** The draft said development and holdout
   ordering "reproduced exactly on both primary metrics." Recomputed from
   `reports/confirm.json`: true for the four shipped defaults on both metrics,
   and true for all six configurations on Brier — but **false** for all six on
   log loss, where `batter_shrinkage b=200` and `matchup_combination b=100
   p=100` swap ranks 2 and 3. Corrected in `FINDINGS.md` §6.3.

Also recorded in `FINDINGS.md`: the retrieval-provenance distinction between
scripted upstream acquisition and v0.3.1's manual-CSV ingestion contract (§2.1),
logged as an architectural gap (§10.4). The immutable snapshot, its manifest and
its hashes were **not** rewritten.

Holdout status is restated prominently in `FINDINGS.md` §0 and `README.md`:
**SPENT** — available for audit and reproduction, never again as a pristine
confirmatory holdout.
