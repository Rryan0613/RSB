# Candidate Evaluation Contract

**Status:** Architecture document, v0.3.0.
**Refines:** `docs/LEGACY_PIPELINE_ARCHITECTURE_AUDIT.md` (merged architectural baseline). This document does not contradict or replace the audit — it specifies the contract the audit identified as RSB's leading canonical eligibility option (audit §4).

---

## 1. Purpose

This document defines the Candidate Evaluation Contract: the canonical vocabulary and record shape for RSB's pure-primitives and future-sport architecture, expressing whether a betting opportunity is eligible, rejected, or could not be evaluated. It gives every pure-primitives consumer one shared place to validate a complete evaluation record instead of re-deriving the rules independently.

The legacy World Cup runtime (`run_slate.py` and everything it orchestrates) does **not** use this contract today and is not translated into it by this version. Legacy expresses eligibility through its own, separate `qualified`/`rejected` model (`market_selector.py`). This document exists to give the pure-primitives side and future sports one canonical contract to build on, and to prevent a third, independent eligibility taxonomy from emerging alongside legacy's untranslated model — not to describe legacy's current behavior. Any future convergence between the two is a deferred, explicit translation step (§18), never an implicit or assumed one.

## 2. Architectural contract versus current module implementation

**The Candidate Evaluation Contract is an architectural concept, not a file.** Its current implementation lives in `src/candidate_evaluation.py`, but the contract — the status vocabulary, the pass-reason vocabulary, the record invariants, and the validation rules — is what other modules depend on conceptually. If this implementation is ever refactored or relocated, the contract itself (this document's definitions) remains stable; only the import path changes.

## 3. Canonical record shape

A complete Candidate Evaluation Contract record is a plain dict with exactly three keys, in this order:

- `status` — one of the three approved statuses (§4).
- `edge` — `float` in `[-1.0, 1.0]`, or `None`.
- `pass_reasons` — a `list[str]` drawn from the closed pass-reason vocabulary (§5); empty when `status == "candidate"`.

`candidate_evaluation.validate_candidate_evaluation_record(value) -> dict` is the canonical whole-record validator: it requires `value` to be a `dict` with exactly these three keys (rejecting missing or unexpected keys), delegates all normalization and invariant enforcement to `build_candidate_evaluation()`, and returns a freshly constructed, normalized copy — deterministic key order, no shared mutable state with the caller's input, and no shared mutable state between separate calls.

`build_candidate_evaluation(status, edge=None, pass_reasons=None) -> dict` remains the constructor for building a record from individual fields (e.g., inside `candidate_ev.py`, which computes edge itself). `validate_candidate_evaluation_record` is for the complementary case: a consumer that has already received or embedded a `{status, edge, pass_reasons}`-shaped dict and needs to validate it as a whole. Both ultimately enforce the same single set of invariants — there is exactly one place (`build_candidate_evaluation`) that owns invariant logic; the whole-record validator is a thin shape-checking wrapper around it, not a second implementation.

## 4. Status definitions

- `candidate` — the opportunity was successfully evaluated and remains eligible under the applied evaluation criteria.
- `rejected` — the opportunity was successfully evaluated but failed one or more evaluation criteria.
- `not_evaluable` — the system could not perform a valid evaluation because required information was missing, invalid, ambiguous, or insufficient.

These three statuses are exhaustive and closed (`VALID_CANDIDATE_STATUSES`). No fourth status may be added without a scoped decision.

## 5. Pass-reason ownership

`VALID_PASS_REASONS` is a closed frozenset owned exclusively by `candidate_evaluation.py`. `status == "candidate"` requires `pass_reasons == []`; `status in ("rejected", "not_evaluable")` requires at least one pass reason. Legacy's dynamic, value-interpolated rejection strings (e.g. `below_min_decimal_odds:2.10`) are a different, incompatible shape and are not admitted into this vocabulary by this version — reconciling them is a deferred, separately-scoped decision (audit §8 step 1–2).

## 6. Structural validation errors versus domain statuses

Invalid function input (wrong type, missing key, unexpected key, out-of-vocabulary string, out-of-range numeric value) is **not** itself a candidate status. It raises `CandidateEvaluationValidationError` (or, when validated through `candidate_ranking.py`, `CandidateRankingValidationError`, see §10) and must never be silently coerced into `not_evaluable` or any other status. `not_evaluable` is a domain outcome describing a *validly-shaped* record whose evaluation could not be completed — it is not a fallback for malformed input.

## 7. Identity ownership

Candidate identity (sport, league, event, market, selection, line, player/team context) is owned by `src/prop_candidate.py`. The Candidate Evaluation Contract does not model identity; it only models the outcome of evaluating an identified opportunity.

## 8. Odds-snapshot ownership

Sportsbook odds observations are owned by `src/odds_snapshot.py`. The contract consumes implied probability and edge derived from odds elsewhere; it does not model odds capture, provider identity, or odds format.

## 9. Probability, edge, and EV ownership

Model probability is caller-supplied (from a model, simulation, or future sport-specific runtime) — the pure-primitives side has no probability generator by design. Implied probability, edge, and expected value are computed by `src/odds.py`, `src/edge.py`, and `src/ev.py`, and assembled by `src/candidate_ev.py`, which embeds a `candidate_evaluation` record built via `build_candidate_evaluation()`.

## 10. Ranking and reporting boundaries

`src/candidate_ranking.py` ranks records whose embedded `candidate_evaluation.status == "candidate"` and excludes all others; `rank` is a derived output, not intrinsic candidate identity or evaluation state. As of v0.3.0, ranking delegates complete embedded-record validation to `candidate_evaluation.validate_candidate_evaluation_record()` rather than re-implementing status/edge/pass-reason/invariant checks itself. When the embedded record is invalid, `candidate_ranking.py` catches the resulting `CandidateEvaluationValidationError` and re-raises `CandidateRankingValidationError` (via `raise ... from exc`, preserving the original error as `__cause__`), identifying the offending `candidate_evs[index]` record — keeping ranking's public exception boundary self-contained and consistent across every embedded-record failure mode.

`src/candidate_report.py` does not own the Candidate Evaluation Contract and does not receive or validate a complete embedded `candidate_evaluation` record. It consumes already-ranked, *flattened* report fields (`candidate_status` and `pass_reasons` as separate top-level keys, not a nested `candidate_evaluation` dict) and may validate those flattened fields using shared field-level primitives — today it calls `candidate_evaluation.validate_pass_reasons()` directly on the flattened `pass_reasons` list. This field-level validation does not make it an owner of the contract: it never sees or validates the `status`/`edge`/`pass_reasons` triple as a single record, and it is unchanged by this version.

## 11. Data-quality boundary

`src/review_taxonomy.py` defines a separate `strong`/`okay`/`weak`/`unknown` data-quality vocabulary. It is a distinct concept from candidate evaluation status and is not merged into the Candidate Evaluation Contract in this or any prior version. Reconciling `review_taxonomy.py` with legacy's `data_quality.py` tri-state is a deferred, separately-scoped decision (audit §3.3, §4).

## 12. Settlement boundary

Settlement is a separate post-event lifecycle record, implemented by `src/prop_result.py` (`pending` → `won`/`lost`/`push`/`void`/`unknown`). Settlement must never mutate the original pre-event `candidate_evaluation` snapshot; the two are linked only by shared identity fields, never by shared mutable state.

## 13. Review boundary

Review findings are a separate record, implemented by `src/review_notes.py`. Review notes must never overwrite the original evaluation record; they are an independent annotation, not a correction applied in place.

## 14. Persistence boundary

Persistence is deferred to a future, separately-scoped version. When it arrives, persistence must store Candidate Evaluation Contract records as-is; it must not define or alter their semantics. No database or schema changes are introduced by this version.

## 15. Legacy World Cup isolation

`candidate_evaluation.py` (and every module in this document's scope) must never import from `run_slate.py`, `data_quality.py`, `market_selector.py`, or any other legacy World Cup runtime module. This is enforced today by AST-based banned-import tests in the corresponding test files and must remain true after any future refactor. Legacy World Cup translation into this contract remains an optional, deferred future bridge (audit §7d, §8 step 3) — for reporting/backtest comparison only, never as shared runtime wiring.

## 16. Backward-compatibility guarantees

- `build_candidate_evaluation`'s signature, output shape, and key order are unchanged.
- `normalize_candidate_status`, `normalize_pass_reason`, and `validate_pass_reasons` are unchanged.
- `rank_candidate_ev_enrichments`'s output shape, key order, sort order, and successful-path behavior are unchanged.
- `build_candidate_report`'s output shape is unchanged.
- All existing status strings and pass-reason strings are unchanged.

## 17. Explicit non-goals

This version does not introduce: a `CanonicalCandidate` aggregate; a new EV-enrichment aggregate; protocols or abstract interfaces; dataclasses; TypedDict migrations; new dependencies; legacy World Cup translation or vocabulary mapping; new legacy-specific pass reasons; imports from legacy modules into the pure pipeline; MLB runtime orchestration; provider ingestion; database/schema changes; persistence repositories; candidate or database IDs; a model-version registry; settlement-rule execution; result-ingestion wiring; post-event review wiring; CLV calculation; recommendations, picks, locks, or parlays; staking or Kelly calculations; or any API/UI behavior.

## 18. Future translation boundary

Any future convergence between the legacy World Cup runtime and this contract must occur through an explicit, separately-scoped translation function — never by merging the two runtimes, and never by extending `run_slate.py` to understand this contract directly. See audit §7d and §8 step 3 for the sanctioned shape of that future bridge.
