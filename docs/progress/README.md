# RSB Progress Dashboard

A standalone, dependency-free dashboard for visualizing RSB's current architecture, delivered milestones, roadmap, and controlled development workflow.

This is permanent developer documentation. It is not the sportsbook product, has no build step, no framework, no npm dependency, and makes no network calls.

## Files

- `index.html` — dashboard layout and rendering logic.
- `progress-data.js` — the only file that normally needs updating after a version is merged.
- `README.md` — this file.

## Use it

Open `index.html` directly in a browser (works from a local `file://` URL).

Or run a local server:

```bash
cd docs/progress
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## What the dashboard distinguishes

- **Repository baseline** — the last verified, merged state of `main`. Only merged work may be described as "Verified complete" — this applies to modules, milestones, readiness areas, and architecture components, not only to the baseline card itself.
- **Active workspace** — an optional snapshot of work outside the verified main baseline. It may be uncommitted local work or committed feature-branch work, but it is never described as merged or verified until it reaches main through the controlled review process. The page renders correctly when this section is absent (e.g., immediately after a merge, before a new version starts).
- **Readiness by capability area** — categorical status per capability area (Foundation contracts, Sport capability profiles, Provider/data ingestion, MLB runtime, NBA runtime, Probability generation, Calibration/backtesting, Operational reporting, Settlement/learning loop). There is no overall completion percentage anywhere on this page, by design — a high count of completed foundation primitives does not mean RSB is close to being an operational betting product.

## Post-merge update routine

After every successful merge, update `progress-data.js` during the same post-version handoff/docs chore:

1. Verify the merge and resulting version.
2. Update `repositoryBaseline`.
3. Clear or replace the prior `activeWorkspace` (set it to `null` or omit it if no new version has started yet).
4. Add verified release evidence (`releaseEvidence: { prNumber, mergeCommit, testCount }` — only fields you can actually verify; omit the rest rather than guessing).
5. Update changed module states.
6. Update readiness and roadmap states.
7. Set the next gate and exact next action.
8. Update `lastVerifiedAt`.
9. Review every page for stale or contradictory claims.
10. Update the dashboard alongside the handoff documents (`Handoffs/ChatGpt_Handoff.txt`, `Handoffs/Claude_handoff.txt`) so the page and the written handoffs cannot drift apart.

Keep routine updates concentrated in `progress-data.js`. Only touch `index.html` when the data shape itself changes (a new field, a new page, a new rendering rule) — and bump `schemaVersion` in `progress-data.js` when you do, so the page's validation can warn about mismatches instead of failing silently.

## Data shape notes

- `repositoryBaseline` and `currentGate` are required.
- `activeWorkspace` is optional. Omit it or set it to `null` when there is no work in progress outside the verified main baseline (whether uncommitted local work or committed, unmerged feature-branch work).
- `releaseEvidence` fields (`prNumber`, `mergeCommit`, `testCount`) are optional per-milestone. Omit fields you cannot verify — the page does not display placeholder text for missing evidence, and does not infer missing values.
- Status values must come from the categorical vocabulary defined in `statusLegend` inside `progress-data.js` (for example `"Verified complete"`, `"Implemented, awaiting review"`, `"Frozen legacy"`). The page derives CSS styling from these exact strings, so keep new entries consistent with the existing vocabulary rather than inventing new status words per field.

The page deliberately does not pull live GitHub data yet. Keeping it static prevents dashboard automation from becoming a distraction from RSB's sportsbook architecture.
