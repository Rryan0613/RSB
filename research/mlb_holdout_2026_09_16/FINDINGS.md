# MLB Real-Data Evaluation — Findings

**Sprint:** first empirical run of the frozen v0.3.4 evaluator against real MLB data
**Branch:** `research/mlb-holdout-evaluation-2026-09-16` at `d3d4c8c`, working tree clean
**Date:** 2026-09-16
**Status:** complete. Holdout opened exactly once, after the configuration freeze.

Every number below is FACT (measured this sprint, traceable to a report JSON in
`reports/`) unless explicitly labelled INFERENCE.

---

## 0. HOLDOUT STATUS — READ FIRST

> ### The 2026-08-12 → 2026-09-15 window is a SPENT HOLDOUT.
>
> It has been opened and scored. Six configurations were evaluated against it,
> two of which (`batter_shrinkage b=200`, `matchup_combination b=200 p=200`)
> were chosen using development data from this same experiment.
>
> It remains valid for **audit and reproduction of this experiment**.
>
> It must **never** be presented again as a pristine confirmatory holdout for
> any model or hyperparameter choice influenced by these results.
>
> **Any future confirmatory selection requires new untouched data — a new
> pre-registered temporal window (2026-09-16 onward, or a later season).**

---

## 1. Headline

v0.3.4 shipped a measurement capability. Until this sprint it had never been run
on real data, so RSB had **no** empirical evidence about any MLB method. It now
has one season of evidence.

**FACT.** On a full 2026 regular season (669,880 real Statcast pitches →
172,224 plate appearances) with a prospective 35-day holdout,
`matchup_combination` outperforms the simpler baselines on both primary metrics
in both windows.

**FACT.** No configuration was selected as a production default, no v0.3.3
default was changed, `PROBABILITY_MODEL_CONFIG_VERSION` is untouched, and no
contract was modified.

---

## 2. Experiment identity

| | |
|---|---|
| Statcast snapshot | `20260916T191623976585Z_2b12606c6f66` |
| raw sha256 | `2b12606c6f66dde67832113f65bb949b6a90f56c267f19cd494a70e4fe4c4952` |
| normalized sha256 | `bef9e067fffbd2b671b51f4f1c29d73107fcc614f554761ca8a56574d2709063` |
| PA dataset | `fcea444a0ae6e9806d2fae34c1c00a3c6bb405296ce27b490b11026472fdca5c` |
| derived sha256 | `80d5a44b1eeb96ac57d9a814b124befd94400a4ab00fc5f9de0119c2327da5a7` |
| evaluation input sha256 | `d22f9fbe4dd4496a0ec9d832cf3b8b8aa14402e3353a8f7a7cb5d8d49275238d` |
| range | 2026-03-25 .. 2026-09-15 (172 dates, 2,270 games) |
| development | 2026-03-25 .. 2026-08-11 — 136,214 scored PAs |
| holdout | 2026-08-12 .. 2026-09-15 — 35,562 scored PAs |
| split_date | `2026-08-12` |

Source reports: `reports/confirm.json` (confirmatory, tuning + holdout),
`reports/dev_sweep.json` (development-only sweep, 16 configs),
`reports/statcast_manifest.json`, `reports/pa_manifest.json`,
`reports/season_validation.json`, `reports/exclusion_freeze.json`,
`reports/history_depth.json`, `reports/preflight_scale.json`.

### 2.1 Retrieval provenance — and a contract gap

**Two distinct steps must not be conflated.**

**Upstream acquisition (outside RSB).** Pitch data was acquired by **scripted
HTTP GET requests against the public Baseball Savant Statcast Search CSV
endpoint**, issued in 59 bounded, non-overlapping `game_date` chunks of up to
three days (`download_savant.py`). Each chunk was checked against Savant's
25,000-row export cap; the largest was 13,830 rows, so no chunk was silently
truncated. This step is **not** manual.

**RSB ingestion (inside the contract).** The downloaded chunks were projected to
the 33 RSB-mapped columns, concatenated into one CSV, and passed to the existing
v0.3.1 ingestion path (`load_statcast_export` → `create_statcast_snapshot`),
which performs no network access and reads an already-downloaded local CSV.
That is exactly the input contract v0.3.1 was built for.

**The gap.** v0.3.1 hard-codes `retrieval_mechanism = "manual_csv_export"` and
`source_identifier = "Baseball Savant Statcast Search, manual export"`. Those
constants accurately describe **RSB's ingestion mechanism** (ingest a local CSV,
no network). They are **ambiguous and incomplete as a description of upstream
acquisition**, because the manifest has no field that distinguishes "a human
clicked download" from "a script issued 59 GETs against the public endpoint."

**This is recorded as an architectural provenance-contract gap** (see §10). The
immutable snapshot and its manifest/hashes were **not** rewritten to make the
field look cleaner — that would defeat the purpose of immutable provenance. The
full upstream acquisition detail (endpoint, every query parameter, all 59 chunk
ranges, the projection, the exclusion set) is recorded in the manifest's
caller-supplied `declared_query`, which is the only vehicle v0.3.1 provides.

---

## 3. Research question 1 — does real data pass the v0.3.1–v0.3.4 contracts?

**FACT. Yes, with exactly one documented exception.** (`reports/season_validation.json`,
`reports/preflight_scale.json`)

| check | result |
|---|---|
| games missing vs MLB StatsAPI | **0** |
| duplicate `rsb_pitch_id` | **0** |
| duplicate `rsb_pa_id` | **0** |
| `game_type` values | 100% `R` |
| unrecognized terminal event codes | **0** across 171,818 completed PAs |
| `pitch_number` gaps / duplicates | **0** |
| game-context mismatches within a PA | **0** |
| pitcher reversion (A,B,A) | **0** |
| inconsistent `pitcher_throws` | **0** |
| events on non-terminal pitches | **0** |
| mid-PA batter substitution | **21 PAs — fails closed by design** |

Coverage is exact: 2,268 `Final` + 2 `Completed Early` (gamePk 824295, 824807 —
shortened but official) = 2,270 observed.

**The v0.3.2 event taxonomy is complete against a full real season.** This could
not be established from synthetic fixtures and is the strongest single
validation result of this sprint.

`truncated_pa` appeared **306** times (plus 100 null-terminal incompletes),
confirming the v0.3.2 `ba3ce68` real-Savant correction was necessary and behaves
correctly at scale.

### 3.1 The one exception — mid-PA batter substitution

**FACT.** 21 plate appearances (0.0122%, ~1 in 8,200) carry more than one batter
identity. v0.3.2 §4 fails the **whole batch** closed on these and explicitly
defers resolving attribution.

These are **genuine MLB events, not corrupt data**. Verified example — game
822918, at-bat 49, 2026-04-06: batter 645302 (R) takes pitch 1 against pitcher
641302; the pitcher changes to 668390 and a pinch hitter 641487 (L) enters with
the count carried over at 0-1 and completes the PA with a `field_out`. 18 of 21
involve a handedness change, consistent with platoon-driven pinch hitting.

The contract was **not** changed. The 21 PAs were dropped pre-ingestion under a
structural, outcome-independent rule frozen before any holdout metric existed
(18 development / 3 holdout). Every key and `rsb_pa_id` is in `FREEZE.md`
stage 1.8 and `reports/exclusion_freeze.json`.

---

## 4. Research question 3 — scored sample sizes

**FACT.**

| quantity | value |
|---|---|
| input PAs | 172,224 |
| completed (scorable) | 171,818 |
| incomplete (unscorable) | 406 (0.236%) |
| intersection sample | 171,776 |
| scored — development | 136,214 |
| scored — holdout | 35,562 |

---

## 5. Research question 4 — coverage lost to pitcher-dependent methods

**FACT. Negligible: 42 plate appearances, 0.024%.**

| method | natively supported completed PAs |
|---|---|
| `league_only` | 171,818 |
| `batter_shrinkage` | 171,818 |
| `pitcher_shrinkage` | 171,776 |
| `matchup_combination` | 171,776 |

**INFERENCE.** v0.3.3 §7 documented pitcher-eligibility selection bias as a real
concern requiring intersection-only comparison. The intersection discipline
remains correct, but on real data the cost of including pitcher-dependent
methods is ~1 PA in 4,100 — far too small to distort a comparison.

---

## 6. Research question 5 — method comparison

All values below are read directly from `reports/confirm.json`. Both windows use
one shared intersection denominator.

### 6.1 Development window (tuning) — 2026-03-25 .. 2026-08-11, n = 136,214

| configuration | log loss | Brier | accuracy | macro classwise ECE |
|---|---|---|---|---|
| `matchup_combination` b=200 p=200 | **1.549369** | 0.711073 | 0.45205 | 0.002567 |
| `batter_shrinkage` b=200 | 1.552274 | 0.712795 | 0.45182 | 0.002430 |
| `matchup_combination` b=100 p=100 *(shipped)* | 1.553470 | **0.710770** | 0.45249 | 0.003069 |
| `batter_shrinkage` b=100 *(shipped)* | 1.553545 | 0.712384 | 0.45185 | 0.002732 |
| `pitcher_shrinkage` p=100 *(shipped)* | 1.562093 | 0.715201 | 0.45189 | 0.002304 |
| `league_only` *(shipped)* | 1.562094 | 0.716823 | 0.45182 | 0.001203 |

### 6.2 Holdout window — 2026-08-12 .. 2026-09-15, n = 35,562

| configuration | log loss | Brier | accuracy | macro classwise ECE |
|---|---|---|---|---|
| `matchup_combination` b=200 p=200 | **1.541291** | 0.708497 | 0.45349 | 0.002648 |
| `matchup_combination` b=100 p=100 *(shipped)* | 1.544774 | **0.708377** | **0.45397** | 0.003007 |
| `batter_shrinkage` b=200 | 1.546005 | 0.710828 | 0.45248 | 0.002318 |
| `batter_shrinkage` b=100 *(shipped)* | 1.547102 | 0.710581 | 0.45253 | 0.002125 |
| `pitcher_shrinkage` p=100 *(shipped)* | 1.558233 | 0.714237 | 0.45284 | 0.002706 |
| `league_only` *(shipped)* | 1.560448 | 0.716457 | 0.45248 | 0.000755 |

A 16-configuration development-only strength sweep (strengths 25/50/100/200/400)
is recorded separately in `reports/dev_sweep.json` and tabulated in
`stage3_frozen_configs.md`.

### 6.3 Did the ordering reproduce? — precise, mechanically checked

**This was overstated in an earlier draft and is corrected here.** The rankings
below were recomputed by sorting the recorded metric values in
`reports/confirm.json`.

| comparison set | metric | tuning ordering == holdout ordering? |
|---|---|---|
| the 4 shipped defaults | log loss | **YES** |
| the 4 shipped defaults | Brier | **YES** |
| all 6 evaluated configs | Brier | **YES** |
| all 6 evaluated configs | log loss | **NO** |

**FACT.** For the four shipped methods at shipped strengths, the ordering is
identical in both windows on both primary metrics:

```
matchup_combination  <  batter_shrinkage  <  pitcher_shrinkage  <  league_only
        (better)                                                      (worse)
```

**FACT.** Across all six configurations, Brier ordering is identical in both
windows. Log-loss ordering is **not**: `batter_shrinkage b=200` and
`matchup_combination b=100 p=100` **swap ranks 2 and 3** between windows.

| log-loss rank | tuning | holdout |
|---|---|---|
| 1 | `matchup_combination` b=200 p=200 | `matchup_combination` b=200 p=200 |
| 2 | `batter_shrinkage` b=200 | `matchup_combination` b=100 p=100 |
| 3 | `matchup_combination` b=100 p=100 | `batter_shrinkage` b=200 |
| 4 | `batter_shrinkage` b=100 | `batter_shrinkage` b=100 |
| 5 | `pitcher_shrinkage` p=100 | `pitcher_shrinkage` p=100 |
| 6 | `league_only` | `league_only` |

**INFERENCE.** The *method-family* ordering is stable out of sample; the
*strength* ordering within a family is not fully stable. The two swapped entries
differ by 0.0012 in tuning log loss — small enough that the swap is
unsurprising, and it is direct evidence that fine strength distinctions are not
resolved by one season.

### 6.4 Improvement over `league_only` (the informative-signal question)

**FACT.** Reduction versus `league_only`; positive = better.

| configuration | Δ log loss (tuning) | Δ Brier (tuning) | Δ log loss (holdout) | Δ Brier (holdout) |
|---|---|---|---|---|
| `batter_shrinkage` b=100 | 0.008549 | 0.004439 | 0.013346 | 0.005877 |
| `batter_shrinkage` b=200 | 0.009820 | 0.004028 | 0.014443 | 0.005629 |
| `pitcher_shrinkage` p=100 | **0.000001** | 0.001622 | 0.002215 | 0.002221 |
| `matchup_combination` b=100 p=100 | 0.008624 | 0.006052 | 0.015674 | 0.008081 |
| `matchup_combination` b=200 p=200 | 0.012725 | 0.005750 | 0.019157 | 0.007960 |

**Correction of an earlier claim.** An earlier draft stated that "pitcher
information is worth approximately 1e-6 log loss versus `league_only`" and that
it "adds almost nothing." **That was cherry-picked from one metric in one
window and is wrong as a general statement.**

The accurate position, from the recorded values:

- The near-tie is real but *narrow in scope*: development **log loss** only,
  where `league_only` − `pitcher_shrinkage p=100` = **8.470494e-07**
  (1.562094133396976 vs 1.5620932863475736).
- On development **Brier**, `pitcher_shrinkage` improves on `league_only` by
  **0.001622** — not negligible.
- On the **holdout**, `pitcher_shrinkage` improves on `league_only` on **both**
  primary metrics, by **0.002215** (log loss) and **0.002221** (Brier).

**FACT.** Pitcher information therefore does carry real predictive signal. It is
simply the **weakest** of the informative methods: on the holdout it delivers
about **1/6** of `batter_shrinkage`'s log-loss improvement (0.002215 vs
0.013346) and about **1/3** of its Brier improvement (0.002221 vs 0.005877).

**INFERENCE.** Batter identity carries substantially more signal than pitcher
identity at these shrinkage levels. A plausible contributing cause is that the
pitcher prior is keyed on the **terminal** pitcher (v0.3.3 §7's "recorded, not
implemented" gap) rather than the PA-start pitcher. This sprint did not test
that, and the data cannot separate it from the simpler explanation that pitcher
effects are genuinely smaller.

### 6.5 Secondary — accuracy

**FACT. Accuracy does not discriminate.** All six configurations land in
0.45248–0.45397 on the holdout; all sixteen development sweep configurations
land in 0.4515–0.4525. **INFERENCE:** the top label is almost always
`field_out` (45.2% of outcomes), so accuracy measures little more than the
marginal rate and should not be used to compare these estimators.

### 6.6 Calibration — and a decisive warning about ECE

**FACT. `league_only` has the BEST calibration on every calibration statistic
and the WORST performance on both primary metrics.**

Holdout: `league_only` top-label ECE 0.00054, MCE 0.00054, macro classwise ECE
0.000755 — best in the field. It is also last on log loss and last on Brier.

The mechanism is visible in the classwise table. For `league_only`, ECE **equals**
MCE **equals** |gap| for all twelve categories, because it emits an identical
distribution for every plate appearance, so every observation falls into a single
bin per category. Perfect reliability, zero resolution.

| category | `league_only` ECE | `league_only` MCE | `matchup b=100` ECE |
|---|---|---|---|
| strikeout | 0.001759 | 0.001759 | 0.004051 |
| single | 0.002773 | 0.002773 | 0.003090 |
| field_out | 0.000539 | 0.000539 | 0.002966 |

**This is empirical proof of v0.3.4's own rule that ECE is diagnostic and must
never rank models.** A model that refuses to discriminate wins on ECE.

**FACT. Top-label MCE is not a usable comparison statistic.** In an early
development-era run it was pinned at exactly 0.91667 (= 1 − 1/12) for all
sixteen configurations, driven by a **single** cold-start plate appearance
sitting alone in the `[0.00, 0.10)` bin with a near-uniform top probability of
0.0833. MCE is a max over bins and saturates on any sparse bin.

### 6.7 Monthly stability and cold start

**FACT.** Development, mean log loss by month:

| configuration | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 |
|---|---|---|---|---|---|---|
| `league_only` | 1.5717 | 1.5678 | 1.5520 | 1.5689 | 1.5640 | 1.5472 |
| `batter_shrinkage` b=100 | 1.5695 | 1.5627 | 1.5441 | 1.5587 | 1.5520 | 1.5376 |
| `pitcher_shrinkage` p=100 | 1.5716 | 1.5695 | 1.5529 | 1.5693 | 1.5626 | 1.5429 |
| `matchup_combination` b=100 p=100 | 1.5698 | 1.5646 | 1.5448 | 1.5589 | 1.5503 | 1.5331 |
| `matchup_combination` b=200 p=200 | 1.5691 | 1.5605 | 1.5402 | 1.5543 | 1.5465 | 1.5294 |

**FACT. Cold start is real and self-correcting.** In 2026-03 the spread between
best and worst is 0.0026 — every method collapses toward `league_only`, exactly
as v0.3.3 §5's limiting identity predicts (`n_e = 0` ⇒ entity distribution =
league distribution). By 2026-08 the spread is 0.0178, **6.8× wider**.

**FACT.** Prior-history depth entering the holdout (state on 2026-08-11,
n = 1,092): `prior_batter_pa_count` median **353** (p10 98, p25 221, p75 466);
`prior_pitcher_pa_count` median **270**. At the shipped `batter_prior_strength =
100` the median batter carries 78% weight on its own history.

**FACT.** Zero-history plate appearances fall from 383 (March) to 17 (August);
only **1** plate appearance in the whole season has zero league history.

**FACT. Holdout months are internally stable**: 2026-08 log loss is uniformly
better than 2026-09 for every configuration (e.g. `matchup b=200`: 1.5382 vs
1.5454), with the ordering preserved in both months.

---

## 7. Research question 6 — is `matchup_combination` overconfident?

**FACT. Not at the shipped strengths. Overconfidence is a weak-shrinkage
phenomenon.**

Signed observed−predicted gap in the classwise high-confidence region (bins with
lower edge ≥ 0.2). Negative = overconfident.

| configuration | development | holdout |
|---|---|---|
| `matchup_combination` b=25 p=25 | **−0.00619** | not evaluated (dev-only sweep) |
| `matchup_combination` b=50 p=50 | −0.00166 | not evaluated |
| `matchup_combination` b=100 p=100 | +0.00226 | **+0.00012** |
| `matchup_combination` b=200 p=200 | +0.00451 | +0.00254 |
| `pitcher_shrinkage` p=100 | −0.00089 | −0.00277 |
| `batter_shrinkage` b=100 | +0.00442 | +0.00358 |
| `league_only` | +0.00037 | −0.00061 |

**FACT.** At the shipped 100/100, `matchup_combination` is the best-calibrated
configuration in the high-confidence region on the holdout (+0.00012). At
strength 25 it is clearly overconfident and is also the **worst log loss in the
entire development sweep** (1.580912) despite being the most complex estimator.

**INFERENCE.** v0.3.3 §5's warning — that two same-direction deviations from
league compound multiplicatively rather than averaging — is real and measurable,
but upstream shrinkage at the shipped strength fully damps it. The mildly
overconfident method on the holdout is `pitcher_shrinkage`, not
`matchup_combination`.

---

## 8. Research question 7 — should 1 / 100 / 100 be retained? — MODEL CONCLUSION

**No new default is selected by this experiment.** Recorded conclusions:

1. **FACT.** `matchup_combination` has empirical support over the simpler
   baselines on this experiment: it leads on both primary metrics in both
   windows, and the shipped-defaults ordering reproduced out of sample (§6.3).
2. **FACT.** `matchup_combination` b=200 p=200 produced the **best reported
   holdout log loss** (1.541291).
3. **FACT.** The shipped `matchup_combination` b=100 p=100 produced the **better
   holdout Brier score** of those two (0.708377 vs 0.708497) — and the best
   holdout Brier of all six configurations.
4. **The shipped 1 / 100 / 100 configuration remains the fixed reference and the
   default.** It was not replaced, and `PROBABILITY_MODEL_CONFIG_VERSION` is
   unchanged.
5. **FACT. This experiment does not establish a unique hyperparameter winner.**
   The two primary metrics select different strengths, reproducibly, in both
   windows; v0.3.4 declares both primary and provides no tie-break. The one
   log-loss rank swap between windows (§6.3) further shows fine strength
   distinctions are not resolved by one season.
6. **Changing any default would require a separately approved model-version
   decision.** It is explicitly out of scope here, and v0.3.4 forbids automatic
   selection.

**FACT.** Strength 25 is decisively rejected by both primary metrics. Strengths
100/200/400 are close together.

**INFERENCE.** 1 / 100 / 100 is a defensible baseline to retain. It is not
demonstrably optimal, and the optimum plausibly depends on history depth, of
which this dataset has exactly one season.

This assessment used **no holdout information**: the sweep ran on development
records only, physically filtered at load, with `split_date=None`, so no holdout
window was ever materialized.

---

## 9. Research question 8 — pathologies to solve before simulation

**FACT / blocking.**

1. **Mid-PA batter substitution has no resolution.** v0.3.2 fails the whole
   batch closed. Any pipeline ingesting a real season must currently drop these
   or crash. 21 PAs/season is tiny, but "the whole derivation fails" is not an
   acceptable production posture.

**FACT / structural.**

2. **Pitcher priors key on the terminal pitcher, not the PA-start pitcher**
   (v0.3.3 §7, recorded and unimplemented). Pitcher signal is real but weakest
   (§6.4); whether this gap is a cause is untested.
3. **Evaluation requires the entire history in memory.** v0.3.4's prior-state
   coherence check regenerates priors over exactly the records supplied, so a
   late-season window cannot be scored against full-season priors unless the
   whole season is passed in. Full season peaked at 2.66 GB (build) and 1.89 GB
   (evaluate) — fine now, but this will not survive multi-season data on
   commodity hardware.
4. **`hit_distance` is a dead mapping.** RSB maps source column `hit_distance`;
   real Savant exports emit `hit_distance_sc`. It is nullable and unused
   downstream, so nothing here is affected, but it normalizes to `None` on every
   real row and therefore silently carries no data.
5. **Provenance contract cannot describe upstream acquisition** (§2.1).

**FACT / constraints on interpretation.**

6. **Accuracy and ECE are both unusable for ranking these models** (§6.5, §6.6).
7. **No simulation input exists.** These are retrospective distributions
   conditioned on `the PA completes`. There is still no PA-opportunity/lineup
   model and no prediction-time input contract.

---

## 10. Research question 9 — most important next architectural gaps

Evidence-based, ordered by support from this sprint's data. **No version number
is assigned to any of these.**

1. **Mid-PA batter-substitution attribution in v0.3.2.** The only real-data
   condition that fails the pipeline closed. v0.3.2 already solved the symmetric
   problem for pitchers (preserve the PA, attribute to terminal, mark
   `pitcher_rate_eligible = False`); the batter side has no equivalent.

2. **PA-start-pitcher prior contract.** Pitcher signal is real but weakest
   (§6.4). Either the prior is keyed wrongly, or pitcher identity matters less
   at this granularity. Both answers matter and the current design cannot
   distinguish them.

3. **A tie-break rule for the primary metrics.** Log loss and Brier selected
   different optima in both windows, reproducibly. "Which configuration is
   better" is currently undecidable by RSB's own hierarchy when they disagree.

4. **Provenance contract: distinguish acquisition from ingestion.** v0.3.1 has
   no field to record how bytes were obtained upstream, only how RSB ingested
   them (§2.1).

5. **Handedness/platoon splits.** 18 of 21 mid-PA batter substitutions were
   handedness changes — direct evidence platoon is a first-class effect managers
   act on. The model ignores `batter_stands`/`pitcher_throws` entirely.

6. **Cross-season history.** Every entity starts cold on Opening Day; the March
   method spread is 0.0026 versus 0.0178 in August.

7. **Streaming/windowed evaluation.** See §9.3.

---

## 11. Holdout integrity

**FACT. The holdout was not contaminated during the experiment.**

- Configurations, strengths, split date, bin edges, sample rules and scoring
  rules were frozen in `FREEZE.md` / `stage3_frozen_configs.md` **before** the
  confirmatory run.
- The exploratory sweep physically filtered to `game_date < 2026-08-12` at load
  and called the evaluator with `split_date=None`. No holdout window was
  materialized and then ignored — it was never computed.
- Pre-freeze QC on holdout dates was restricted to outcome-blind properties.
  Realized-target aggregation was hard-filtered to development records.
- The 21-PA exclusion rule never reads the `events` column.
- The holdout was opened **once**. Nothing was changed and re-scored afterwards.
- It was **not** rerun during post-sprint packaging.

**And it is now spent — see §0.**

---

## 12. Implementation bugs

**FACT. None found in v0.3.1–v0.3.4, and nothing in `src/` or `tests/` was
modified.**

The one pipeline failure encountered (`inconsistent batter_id across its
pitches`) is documented contract behavior, not a defect — v0.3.2 §4 specifies
failing closed and explicitly defers the resolution. No regression test was
added because no defect was fixed.

Full suite: **2629 passed**, identical to the documented baseline. No test was
weakened, skipped or modified.

**Errors in this document's own earlier drafts** (corrected above, recorded for
honesty): the claim that pitcher information is worth ~1e-6 log loss was
cherry-picked from one metric in one window (§6.4); the claim that development
and holdout ordering reproduced exactly on both primary metrics was false for
log loss across all six configurations (§6.3). Both were corrected against the
recorded JSON without rerunning anything.

---

## 13. What this sprint does NOT establish

- **One season, one sport.** No cross-season or cross-sport claim.
- **No production default was selected.** v0.3.3 defaults are unchanged.
- **Statistical significance was not computed.** No confidence intervals, no
  paired significance test. Ordering stability is evidence, not a p-value.
- **No unique hyperparameter winner** (§8).
- **Nothing here is live-ready.** No simulation, no PA-opportunity model, no
  prediction-time contract, no sportsbook/EV/runtime wiring.
