# MLB Plate-Appearance Contract

**Status:** Architecture document, v0.3.2.
**Builds on:** `docs/CANDIDATE_EVALUATION_CONTRACT.md`'s precedent that a new contract ships its own architecture doc as part of the implementing version, and on the v0.3.1 MLB Statcast Data Foundation (`src/mlb/statcast_import.py`, `statcast_normalize.py`, `statcast_snapshot.py`), which this document builds directly on top of without modifying.

---

## 1. Purpose

This document defines the v0.3.2 MLB Plate-Appearance Contract: the canonical vocabulary, grouping algorithm, taxonomy, leakage-safety policy, and provenance rules used to derive plate-appearance (PA) records and prior empirical outcome rates from v0.3.1's normalized Statcast pitch-level records. It is implemented by `src/mlb/plate_appearance.py`, `src/mlb/plate_appearance_rates.py`, and `src/mlb/plate_appearance_snapshot.py`.

v0.3.2 is a **dataset/rate foundation only**. It contains no predictive probability model, no calibration, no shrinkage/Bayesian priors, no simulation, no sportsbook odds/EV/ranking, no MLB runtime orchestration, and no automated Baseball Savant network access. See §14 for the complete non-goals list.

## 2. Source contract reuse

This contract does not redefine anything v0.3.1 already owns. `source_game_id`, `at_bat_number`, `pitch_number`, `rsb_pitch_id`, `batter_id`, `pitcher_id`, `batter_stands`/`pitcher_throws`, `pa_event_raw`, `snapshot_id`/`source_provider`/`normalized_schema_version`, deterministic pitch ordering, and duplicate-pitch rejection are all defined by `src/mlb/statcast_normalize.py` and `statcast_snapshot.py`. Every PA-record field with a pitch-level source is a direct carry-forward from an already-normalized pitch dict, never a re-derivation.

## 3. Plate-appearance identity and grouping

A plate appearance is identified by `(source_game_id, at_bat_number)`. `source_game_id` (Statcast `game_pk`) is unique across MLB's history; `at_bat_number` is a monotonic, per-game counter validated `>= 1` by v0.3.1. No additional identifier is required.

`build_rsb_pa_id(source_game_id, at_bat_number) = sha256(f"{source_game_id}:{at_bat_number}")` is the deterministic PA identity, stable regardless of any other field.

Grouping operates on the pitch records produced by a **single** v0.3.1 normalized snapshot (or an already caller-deduplicated equivalent list). Multi-snapshot merge/reconciliation is out of scope for this version (§14).

## 4. Chronology validation

Within each `(source_game_id, at_bat_number)` group, `pitch_number` values must be exactly `1..N` with no gaps or duplicates. Any violation fails the whole derivation closed.

The following context fields must be constant across every pitch in a group, and any mismatch fails the whole derivation closed: `game_date`, `game_year`, `game_type`, `home_team`, `away_team`, `inning`, `inning_half`, `batter_id`, `batter_stands`, `snapshot_id`, `source_provider`, `normalized_schema_version`. No legitimate MLB scenario allows a plate appearance to span innings or span two different normalized snapshots, so those mismatches are unconditional contradictions. This version does not resolve attribution for a PA that appears to contain multiple batter identities or batting sides — rather than guess which identity should receive historical credit, any `batter_id`/`batter_stands` variation within a group fails closed. If verified real source data later shows a legitimate reason for this to vary, that can be handled in a separately scoped future change.

## 5. Terminal-pitch detection (chronology-first)

Terminal detection depends only on pitch-number chronology, not on maintaining an exhaustive event-code vocabulary:

1. The pitch with the maximum `pitch_number` in the group is the **only** terminal candidate.
2. Every other (non-last) pitch in the group must have `pa_event_raw is None`. Baseball Savant's own CSV export documentation defines `events` as "the event of the resulting plate appearance" — a non-null value on any earlier pitch is therefore an **unexpected source condition**, not a recognized mid-PA event, and fails the whole derivation closed rather than being silently absorbed, ignored, or treated as a second terminal outcome.
3. The terminal pitch's `pa_event_raw` is then classified:
   - `None` → `pa_status = "incomplete"`, `pa_outcome_detailed`/`pa_outcome_category` are `None`. This version makes no claim about *why* the terminal pitch is missing (a snapshot date-range boundary is one possible cause among others) — it is recorded as an observed fact, not attributed to a specific cause.
   - a value present in `INCOMPLETE_TERMINAL_EVENTS` (currently just `truncated_pa`) → `pa_status = "incomplete"`, `pa_outcome_detailed`/`pa_outcome_category` are `None`, but `terminal_pa_event_raw` **preserves the raw value exactly** for provenance/audit. A manual review of a real Baseball Savant export surfaced `truncated_pa` as a provider marker on an interrupted/incomplete plate appearance. That review established the observed status behavior but did not establish why Baseball Savant emits the marker, so this contract does not attribute a specific cause. It is a status marker, not a completed outcome, and is deliberately excluded from `TERMINAL_EVENT_TAXONOMY`, `DETAILED_TO_CATEGORY`, and `RATE_CATEGORIES` (§6) so it can never classify as a completed outcome or contribute to any historical rate denominator (§8).
   - a value present in `TERMINAL_EVENT_TAXONOMY` (§6) → `pa_status = "completed"`, classified into a detailed outcome and a category.
   - any other non-null value → fails the whole derivation closed. An unrecognized terminal event is surfaced explicitly for review; it is never guessed. This applies to any future non-null terminal code not already covered by `TERMINAL_EVENT_TAXONOMY` or `INCOMPLETE_TERMINAL_EVENTS` — the set of recognized incomplete-status markers is closed and deliberately small, not a catch-all.

There is deliberately no separate "known non-terminal event code" whitelist in this version — the whole detection algorithm depends on chronology, not on a hand-maintained list staying complete.

## 6. Event taxonomy

Two closed vocabularies, both fail-closed on unmapped input, with no catch-all `"other"` bucket at either layer:

**`pa_outcome_detailed`** (raw `pa_event_raw` → detailed canonical outcome, consulted only for the chronologically-identified terminal pitch): `strikeout`, `strikeout_double_play`, `walk`, `intent_walk`, `hit_by_pitch`, `single`, `double`, `triple`, `home_run`, `field_out`, `force_out`, `grounded_into_double_play`, `double_play`, `triple_play`, `fielders_choice`, `fielders_choice_out`, `field_error`, `sac_fly`, `sac_fly_double_play`, `sac_bunt`, `sac_bunt_double_play`, `catcher_interf`.

**`pa_outcome_category`** (detailed → smaller mutually-exclusive modeling bucket):

| category | detailed values |
|---|---|
| strikeout | strikeout, strikeout_double_play |
| walk | walk |
| intentional_walk | intent_walk |
| hit_by_pitch | hit_by_pitch |
| single | single |
| double | double |
| triple | triple |
| home_run | home_run |
| field_out | field_out, force_out, grounded_into_double_play, double_play, triple_play, sac_fly, sac_fly_double_play, sac_bunt, sac_bunt_double_play |
| fielders_choice | fielders_choice, fielders_choice_out |
| reached_on_error | field_error |
| catcher_interference | catcher_interf |

`intent_walk` maps to its own `intentional_walk` category, **kept distinct from `walk`** at every layer of this contract. Whether a future model combines, excludes, or separately models them is v0.3.3 scope — this dataset never erases the distinction.

This taxonomy was built from general Statcast domain knowledge and has since been checked against a representative manual Baseball Savant export sample (the review that surfaced `truncated_pa`, §5). That review was a sample, not an exhaustive audit — it is not a claim that every historical or future event code is already known. Because detection (§5) never depends on this table's completeness — only classification of an already-identified terminal pitch does — an incomplete taxonomy fails loudly on real data rather than silently misclassifying it.

## 7. Mid-PA pitcher substitution

A plate appearance's pitchers are validated by walking the per-pitch `pitcher_id` sequence and recording the distinct values in order of first appearance (`source_pitcher_ids`):

- If the sequence contains exactly one distinct pitcher, the PA is normal: `pitcher_rate_eligible = True`.
- If the sequence contains more than one distinct pitcher but never reverts to an earlier one (e.g. `A,A,B,B`, or `A,B,C`), this is recognized as a legitimate mid-PA substitution — a rare but real MLB scenario (for example, an injury mid-at-bat). The PA is **preserved**, not rejected. `pitcher_id`/`pitcher_throws` on the resulting record are the **terminal pitcher's** values (the pitcher on the mound for the last pitch); `pitcher_rate_eligible = False`; `source_pitcher_ids` records every distinct pitcher involved for later diagnosis.
- If the sequence reverts to an earlier pitcher (e.g. `A,B,A`), this cannot represent a real substitution and is treated as a genuine contradiction — fails the whole derivation closed.

Each distinct pitcher_id must also map to exactly one `pitcher_throws` value within the PA. If the same `pitcher_id` appears with two different `pitcher_throws` values, this is treated as contradictory source data (not a real substitution, since a given pitcher's throwing hand does not change mid-game) and fails the whole derivation closed.

`batter_id`/`batter_stands` have no equivalent relaxation (§4): this version does not resolve multi-batter attribution, so any variation fails closed rather than being guessed (§4).

`pitcher_rate_eligible = False` means this PA's outcome is excluded from that pitcher's future prior-rate history (§8) because true pitcher-of-record attribution is ambiguous and this version does not resolve it. It does **not** exclude the PA from batter or league history, and it does **not** prevent the PA from being *read* as part of another PA's `prior_pitcher_*` state.

## 8. Prior-rate foundation

`attach_prior_outcome_rates` attaches, to every PA (completed or incomplete), the batter/pitcher/league outcome state that existed **strictly before** that PA:

- `prior_batter_pa_count`, `prior_batter_outcome_counts` (`{category: int}` over the full `RATE_CATEGORIES` set), `prior_batter_outcome_rates` (`{category: float | None}`)
- `prior_pitcher_pa_count`, `prior_pitcher_outcome_counts`, `prior_pitcher_outcome_rates`
- `prior_league_pa_count`, `prior_league_outcome_counts`, `prior_league_outcome_rates`

Rates are `count / pa_count` when `pa_count > 0`; when `pa_count == 0`, every category's rate is `None` — **never `0.0`** — because an undefined (no-history) rate and an observed zero rate are not the same thing, and this version performs no smoothing that would otherwise blur the distinction.

Only `pa_status == "completed"` PAs update the running counters. An incomplete PA still receives a `prior_*` state snapshot (useful for context/audit) but never contributes an outcome to anyone's future state. Batter and league counters update on every otherwise-valid completed PA regardless of `pitcher_rate_eligible`; the pitcher counter updates only when `pitcher_rate_eligible == True` (§7).

This is deliberately raw empirical counting: integer numerators, a plain denominator, a raw rate. No shrinkage, no Bayesian priors, no minimum-sample thresholds, no probability model. Whether and how to smooth or combine these numbers is v0.3.3 scope.

## 9. Same-day cross-game leakage policy

A PA may treat an earlier PA as **prior** under exactly two conditions:

- the earlier PA's `game_date` is strictly before this PA's `game_date`, **or**
- the two PAs share the same `source_game_id` and the earlier PA has a smaller `at_bat_number` (a fully trustworthy ordering, since `at_bat_number` is a validated, monotonic, per-game counter).

A PA **never** treats another PA from a *different* `source_game_id` on the *same* `game_date` as prior, in either direction. The normalized pitch contract carries no game-start timestamp, so the relative real-world chronology of two different games on the same date is genuinely unknown.

This is implemented as a two-level pass: running counters are frozen at each date boundary and every game on that date starts from the same frozen baseline; only after all of a date's games are processed are that date's completed outcomes merged into the counters carried into the next date. Two same-day games can never influence each other's `prior_*` fields by construction, while within a single game the `at_bat_number` order still gives full leakage-safe granularity.

This intentionally under-uses some same-day doubleheader history (a batter's game-1 PAs never inform that same batter's game-2 `prior_*` state on the same date) in exchange for a guarantee that no `prior_*` field can ever depend on chronology RSB cannot verify.

## 10. Coverage limitation

This dataset is derived entirely from v0.3.1's normalized **pitch-level** Statcast records. It is **not** claimed to be an authoritative, complete ledger of every official MLB plate appearance. If Baseball Savant's pitch-level export does not include a pitch row for some official PA — for any reason, verified or not — that PA simply does not appear in this dataset; this version does not investigate or characterize how often that happens.

Every rate denominator in this dataset (§8) therefore means **completed PAs represented by the normalized pitch source**, not completed PAs against an independent, authoritative MLB total. Every persisted PA-dataset manifest carries `coverage_basis = "normalized_pitch_represented_pa"` to make this basis explicit and machine-readable rather than assumed.

This version does not automate Baseball Savant access to investigate or close this gap — see §14, the non-goals list.

## 11. Provenance and single-snapshot validation

`create_plate_appearance_dataset(source_manifest, normalized_pitch_records, ...)` persists a derived artifact from **exactly one** v0.3.1 normalized source snapshot. Before any derivation runs, it validates:

1. `source_manifest` has exactly the v0.3.1 `MANIFEST_FIELD_ORDER` key set (no missing, no extra keys).
2. `len(normalized_pitch_records) == source_manifest["normalized_row_count"]`.
3. Re-serializing `normalized_pitch_records` with the existing v0.3.1 canonical serialization (`serialize_normalized_records`) and hashing the result equals `source_manifest["normalized_content_sha256"]`.
4. Every record's `snapshot_id`, `source_provider`, and `normalized_schema_version` equal the corresponding `source_manifest` fields.

Any mismatch fails the whole call closed. Multi-snapshot merge/deduplication remains explicitly out of scope; the pure grouping and rate functions never attempt to reconcile multiple snapshots themselves — that responsibility, to the extent it exists at all in this version, is this single validation gate.

Because exactly one source snapshot is guaranteed by this gate, every PA record in a persisted dataset carries a **singular** `source_snapshot_id` (not a list).

## 12. Derived-artifact identity

`derived_dataset_id = sha256(f"{source_normalized_content_sha256}:{pa_schema_version}:{derivation_version}")` — deterministic and content-derived, **not** salted by a creation timestamp. Identical canonical inputs and identical transformation versions (`PLATE_APPEARANCE_SCHEMA_VERSION`, `PLATE_APPEARANCE_DERIVATION_VERSION`) always reproduce the identical artifact identity and content. Creation time (`derived_at`) is separate manifest metadata only and plays no role in identity.

This deliberately departs from v0.3.1's ingestion-timestamp-salted `snapshot_id`: a raw external ingestion event's "when we pulled it" is itself meaningful provenance, but a PA dataset is a pure function of an already-immutable normalized snapshot plus fixed derivation code, so determinism is the correct property here.

Re-running the derivation against an artifact that already exists at the same id: if the freshly computed content matches byte-for-byte, this is an idempotent no-op success (the existing manifest is returned, nothing is rewritten). If content differs at the same id — only possible if derivation code changed without bumping `PLATE_APPEARANCE_DERIVATION_VERSION` or `PLATE_APPEARANCE_SCHEMA_VERSION` — this is a hard error, fail closed.

## 13. Failure semantics summary

| condition | behavior |
|---|---|
| duplicate `rsb_pitch_id` across combined input | fail closed, whole batch |
| non-contiguous / duplicate `pitch_number` within a PA group | fail closed, whole batch |
| batter/stands/game-context/snapshot-provenance mismatch within a PA group | fail closed, whole batch |
| one or more forward-only mid-PA pitcher substitutions | not fatal — PA preserved, `pitcher_rate_eligible = False` |
| a pitcher's `pitcher_throws` value is inconsistent across its pitches in one PA | fail closed, whole batch |
| pitcher sequence reverts to an earlier pitcher | fail closed, whole batch |
| non-null `pa_event_raw` on a non-terminal pitch | fail closed, whole batch |
| terminal pitch's `pa_event_raw` is null | `pa_status = "incomplete"`, not fatal |
| terminal pitch's `pa_event_raw` is a member of `INCOMPLETE_TERMINAL_EVENTS` (e.g. `truncated_pa`) | `pa_status = "incomplete"`, not fatal; raw value preserved in `terminal_pa_event_raw`, never counted in any rate denominator |
| terminal pitch's `pa_event_raw` is a known terminal code | `pa_status = "completed"` |
| terminal pitch's `pa_event_raw` is non-null and unrecognized (not in `TERMINAL_EVENT_TAXONOMY` or `INCOMPLETE_TERMINAL_EVENTS`) | fail closed, whole batch |
| a `pa_status == "incomplete"` PA record has a `terminal_pa_event_raw` that is neither `None` nor a member of `INCOMPLETE_TERMINAL_EVENTS` | fail closed (rate-attachment input validation) |
| a `pa_status == "completed"` PA record has `terminal_pa_event_raw == "truncated_pa"` (or any other `INCOMPLETE_TERMINAL_EVENTS` member) | fail closed (rate-attachment input validation) — never valid as a completed outcome |
| malformed pitch/PA record shape | fail closed, whole batch |
| empty input | returns `[]`, no error |
| source manifest / normalized records mismatch (row count, content hash, per-record provenance fields) | fail closed |
| derived artifact id collision, identical content | idempotent no-op success |
| derived artifact id collision, different content | fail closed |

## 14. Explicit non-goals

No predictive/calibrated probabilities, no shrinkage/Bayesian priors, no ML, no simulation, no sportsbook odds/EV/ranking/parlays, no MLB runtime/orchestration, no automated Baseball Savant network ingestion, no PostgreSQL/object storage, no multi-source reconciliation, no World Cup changes, no NBA changes, no handedness-split or park/opponent-adjusted rates, no minimum-sample betting policy, and no post-merge roadmap/handoff/progress-dashboard state synchronization (that remains a separate, later chore).
