# Stage 2 - Dataset Identity (frozen before any holdout metric was inspected)

## v0.3.1 Statcast snapshot

| field | value |
|---|---|
| snapshot_id | `20260916T191623976585Z_2b12606c6f66` |
| source_provider | `baseball_savant` |
| retrieval_mechanism | `manual_csv_export` |
| adapter_version | `1` |
| normalized_schema_version | `1` |
| raw_content_sha256 | `2b12606c6f66dde67832113f65bb949b6a90f56c267f19cd494a70e4fe4c4952` |
| normalized_content_sha256 | `bef9e067fffbd2b671b51f4f1c29d73107fcc614f554761ca8a56574d2709063` |
| raw_row_count | `669880` |
| normalized_row_count | `669880` |
| ingestion_started_at | `2026-09-16T19:16:23.976585Z` |
| ingestion_completed_at | `2026-09-16T19:16:30.111959Z` |
| requested_date_range | 2026-03-25 .. 2026-09-15 |

## v0.3.2 derived plate-appearance dataset

| field | value |
|---|---|
| derived_dataset_id | `fcea444a0ae6e9806d2fae34c1c00a3c6bb405296ce27b490b11026472fdca5c` |
| source_snapshot_id | `20260916T191623976585Z_2b12606c6f66` |
| source_normalized_content_sha256 | `bef9e067fffbd2b671b51f4f1c29d73107fcc614f554761ca8a56574d2709063` |
| pa_schema_version | `1` |
| derivation_version | `1` |
| coverage_basis | `normalized_pitch_represented_pa` |
| input_pitch_row_count | `669880` |
| output_pa_count_completed | `171818` |
| output_pa_count_incomplete | `406` |
| derived_content_sha256 | `80d5a44b1eeb96ac57d9a814b124befd94400a4ab00fc5f9de0119c2327da5a7` |
| derived_row_count | `172224` |

## Source completeness against an independent authority

Authority: MLB StatsAPI schedule, gameType=R, detailedState=Final.

| quantity | value |
|---|---|
| normalized pitch rows | 669,880 |
| distinct game dates | 172 |
| distinct games observed | 2,270 |
| games expected (detailedState=Final) | 2,268 |
| games missing | 0 |
| dates with scheduled finals but no pitch data | 0 |
| games observed but not 'Final' | 2 |
| duplicate rsb_pitch_id | 0 |
| game_type values | {'R': 669880} |

The two games observed but not labelled `Final` are gamePk 824295 (2026-04-04) and
824807 (2026-08-02), both `Completed Early` - shortened but official regular-season
games carrying real pitch data. Coverage is therefore exact: 2,268 Final + 2
Completed Early = 2,270 observed, zero missing and zero spurious.

## Plate-appearance layer (structural)

| quantity | value |
|---|---|
| plate appearances | 172,224 |
| duplicate rsb_pa_id | 0 |
| completed | 171,818 |
| incomplete | 406 (0.2357%) |
| incomplete with no terminal event | 100 |
| incomplete marked `truncated_pa` | 306 |
| pitcher_rate_eligible = False (mid-PA pitcher change) | 42 |
| development PAs (game_date < 2026-08-12) | 136,575 |
| holdout PAs (game_date >= 2026-08-12) | 35,649 |
| excluded mid-PA batter-substitution PAs | 21 (18 dev / 3 holdout) |

## History depth entering the holdout (development-only, outcome-blind)

Prior state attached to plate appearances on the last development date,
2026-08-11 (n = 1,092).
This is pre-PA state, never a realized outcome.

| field | min | p10 | p25 | median | p75 | p90 | max | mean |
|---|---|---|---|---|---|---|---|---|
| prior_batter_pa_count | 0 | 98 | 221 | 353 | 466 | 507 | 539 | 331.6 |
| prior_pitcher_pa_count | 0 | 43 | 132 | 270 | 506 | 548 | 645 | 304.2 |
| prior_league_pa_count | 135,159 | 135,166 | 135,177 | 135,195 | 135,213 | 135,224 | 135,242 | 135,195.2 |

At the shipped `batter_prior_strength = 100`, the median batter entering the holdout
carries 353 prior plate appearances, i.e. 353/(353+100) = **78% weight on its own
history** versus the league baseline; the 25th percentile still carries 69%. This is
the concrete justification that the pre-holdout history is deep enough for the
shrinkage comparison to be meaningful rather than league-dominated.

## Genuine season-opening cold start (development-only)

| month | PAs | median prior_batter_pa_count | zero-history PAs |
|---|---|---|---|
| 2026-03 | 5,736 | 8 | 383 |
| 2026-04 | 30,001 | 54 | 77 |
| 2026-05 | 31,562 | 141 | 72 |
| 2026-06 | 29,918 | 219 | 56 |
| 2026-07 | 28,096 | 296 | 25 |
| 2026-08 | 11,262 | 340 | 17 |

This is the real domain cold start, not an artifact of the dataset start: history
depth climbs from a median of 8 prior PAs in March to 340 by August, and zero-history
plate appearances fall from 383 to 17.
