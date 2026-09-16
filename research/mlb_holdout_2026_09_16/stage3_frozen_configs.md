# Stage 3 - Frozen Configuration List

Written after the development-only sweep and **before** any holdout metric was
computed or inspected. Nothing below may change on the basis of holdout results.

## Development-only sweep that informed this freeze

Scope: `game_date < 2026-08-12`, records physically filtered at load. The
evaluator was called with `split_date=None`, so no holdout window was ever
materialized. Scored intersection sample: n = 136,214.

| configuration | log loss | Brier | accuracy | macro classwise ECE |
|---|---|---|---|---|
| matchup_combination b=200 p=200 | 1.549369 **(best)** | 0.711073 | 0.45205 | 0.002567 |
| matchup_combination b=400 p=400 | 1.549933 | 0.712205 | 0.45185 | 0.002594 |
| batter_shrinkage b=200 | 1.552274 | 0.712795 | 0.45182 | 0.002430 |
| batter_shrinkage b=400 | 1.553376 | 0.713650 | 0.45182 | 0.002272 |
| matchup_combination b=100 p=100 | 1.553470 | 0.710770 **(best)** | 0.45249 | 0.003069 |
| batter_shrinkage b=100 | 1.553545 | 0.712384 | 0.45185 | 0.002732 |
| batter_shrinkage b=50 | 1.557910 | 0.712569 | 0.45176 | 0.003223 |
| pitcher_shrinkage p=400 | 1.558684 | 0.715393 | 0.45181 | 0.001301 |
| pitcher_shrinkage p=200 | 1.559245 | 0.715119 | 0.45181 | 0.001616 |
| pitcher_shrinkage p=100 | 1.562093 | 0.715201 | 0.45189 | 0.002304 |
| league_only | 1.562094 | 0.716823 | 0.45182 | 0.001203 |
| matchup_combination b=50 p=50 | 1.563824 | 0.711650 | 0.45253 | 0.004977 |
| batter_shrinkage b=25 | 1.565480 | 0.713335 | 0.45172 | 0.005000 |
| pitcher_shrinkage p=50 | 1.568076 | 0.715791 | 0.45176 | 0.003690 |
| pitcher_shrinkage p=25 | 1.577553 | 0.716929 | 0.45153 | 0.005752 |
| matchup_combination b=25 p=25 | 1.580912 | 0.713786 | 0.45152 | 0.008162 |

### What the development data shows

1. **Both primary metrics reject weak shrinkage.** Strength 25 is worst or near-worst
   everywhere, and `matchup_combination b=25 p=25` is the single worst log loss in the
   sweep (1.580912) despite being the most complex estimator.
2. **The two primary metrics do not agree on an optimum.** Log loss prefers strength
   200 (`matchup b=200 p=200`, 1.549369); Brier prefers strength 100 (`matchup b=100
   p=100`, 0.710770). v0.3.4 declares both primary and neither breaks the tie, so no
   single winner is declared here.
3. **The shipped 100 is near-optimal on development data.** `matchup b=100 p=100` is
   the best configuration on Brier outright, and is 0.0041 (0.26%) behind the best on
   log loss.
4. **Pitcher information adds almost nothing at the shipped strength.**
   `pitcher_shrinkage p=100` log loss is 1.562093 against `league_only` 1.562094 - a
   difference of 1e-6, i.e. indistinguishable. Batter information clearly helps.
5. **Accuracy does not discriminate.** Every configuration lands in 0.4515-0.4525.
6. **Overconfidence is a weak-shrinkage phenomenon, not an inherent matchup defect.**
   In the classwise high-confidence region (bins with lower edge >= 0.2), the signed
   observed-minus-predicted gap is -0.00619 for `matchup b=25 p=25` (overconfident) but
   **+0.00226** for `matchup b=100 p=100` - slightly *under*-confident. The v0.3.3
   contract's warning that same-direction deviations compound is borne out only when
   upstream shrinkage is too weak to damp it.

## The frozen confirmatory configuration list

Six configurations. The four shipped v0.3.3 defaults are the **fixed reference** and
are present unconditionally. Two development-selected candidates at strength 200 are
appended to test out of sample whether the development log-loss optimum generalizes.

| # | model_method | league | batter | pitcher | role | config_id |
|---|---|---|---|---|---|---|
| 1 | league_only | 1 | None | None | shipped reference | `f63530a9649aca2c...` |
| 2 | batter_shrinkage | 1 | 100 | None | shipped reference | `4fec7dd7aa27db15...` |
| 3 | pitcher_shrinkage | 1 | None | 100 | shipped reference | `51c1145007e79508...` |
| 4 | matchup_combination | 1 | 100 | 100 | shipped reference | `3b31bf1bd734333c...` |
| 5 | batter_shrinkage | 1 | 200 | None | development-selected | `8335f8c097c0271c...` |
| 6 | matchup_combination | 1 | 200 | 200 | development-selected | `916dc41fba7d318b...` |

Adding the two candidates does not move the denominator: the intersection sample is
already constrained by the pitcher-dependent shipped methods, so all six are scored on
one identical sample.

## Frozen experiment parameters

| parameter | frozen value |
|---|---|
| PA dataset | `fcea444a0ae6e9806d2fae34c1c00a3c6bb405296ce27b490b11026472fdca5c` |
| snapshot | `20260916T191623976585Z_2b12606c6f66` |
| split_date | `2026-08-12` |
| development window | 2026-03-25 .. 2026-08-11 |
| holdout window | 2026-08-12 .. 2026-09-15 |
| sample basis | intersection (v0.3.4 fixed) |
| classwise bin edges | v0.3.4 fixed constant, not a caller argument |
| top-label bin edges | v0.3.4 fixed constant, not a caller argument |
| scoring rules | v0.3.4 multiclass log loss, Brier; unchanged |
| exclusion set | the 21 frozen mid-PA batter substitutions (stage 1.8) |
| repository state | branch `research/mlb-holdout-evaluation-2026-09-16` at `d3d4c8c`, clean |

The holdout may now be opened **exactly once**, for the confirmatory evaluation.
