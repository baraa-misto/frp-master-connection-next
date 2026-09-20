# Stage 3.5B-R1 Selector / Action-Arrows / Material-Axes Visual Correction

## Authority and accepted baseline

The controlling correction order was verified byte-for-byte before repository action:

- SHA-256: `9F4BE503F8615663D2DCBF299DE8D755A5F88100EF5D60E3995EA4EC2D5141CB`;
- final sentinel: present and exact;
- accepted baseline: `b17d4adf4cefcd981aef344fc313d7b18c492f54` on clean synchronized `main`;
- Stage 3.5B hosted evidence: GitHub Actions run `#79`, four of four Ubuntu/Windows backend/frontend jobs green, approximately 6 minutes 31 seconds.

The three owner-observed visual defects reopened Stage 3.5B visual acceptance. Direct closure evidence is now accepted: GitHub Actions run `#80` passed all four Ubuntu/Windows backend/frontend jobs, and the owner completed final Stage 3.5B-R1 visual acceptance on 2026-08-29.

## Pre-mutation reproduction and first failure boundaries

1. **Selector grouping:** `DIRECT_SIDE_LAP_CONCRETE` was reproduced under `Brace/beam connections`. The first failure was the option's JSX nesting in `ShearConnectionsWorkspace`; its route, enum, default, and workspace identity were already correct.
2. **Action-arrow placement and sign:** with Axial `+5`, Major `-5`, and Minor `+3`, the backend returned the correct signed force components and authoritative action reference. The first origin loss was `sideLapPoint`, which treated a millimetre reference magnitude as scene inches. The first sign loss was `forceArrow`, which retained fixed positive geometric axes while only changing text metadata.
3. **Material-axis visibility:** the backend returned complete Channel and Angle records, but the scene adapter hard-coded `direct-side-lap-connected-member` while the backend-authored primitives are owned by `clip-angle-connected-member`. Owner-qualified presentation lookup therefore returned no primitive bindings.

## Backend R14B basis stop-rule audit

The backend bases are correct; no backend production correction was authorized or made.

- Channel: `WEB/WEB`, `TOP_FLANGE/FLANGES`, and `BOTTOM_FLANGE/FLANGES` are present with their exact controlled TT vectors.
- Angle: `LEG_1/LEG_1` and `LEG_2/LEG_2` are present with their exact controlled TT vectors.
- Every LW/CW/TT vector is unit length and every pairwise dot product is zero.
- The physical region-normal sign matches the controlled backend record.

## Correction

- Moved the existing stable side-lap selector option under `Beam connections`; no selector value, route, default, or engineering identity changed.
- Normalized backend length quantities into the selected scene length unit before presentation.
- Anchored all applied arrows at `SIDE_LAP_MEMBER_ACTION_REFERENCE` and reversed the geometric arrow axis for negative values.
- Suppressed zero-valued applied arrows.
- Bound Channel web/flange and Angle-leg material axes through the shared owner-qualified material-axis presentation helpers.
- Kept concrete excluded from FRP material-axis presentation.

## Verification

- Focused backend audit: 20 passed.
- Focused frontend regression: 36 passed.
- Real-browser checks: corrected selector taxonomy; attached `+5/-5/+3` arrows; reversed `-5/+5/-3` arrows; zero-valued arrows absent; Channel web/top-flange/bottom-flange and Angle Leg 1/Leg 2 material-axis overlays active.
- Complete backend QA: 2,517 tests, 18,914 statements and 5,540 branches, configured coverage 100%.
- Complete frontend QA: 521 tests in 35 files, 3,586 statements, 2,952 branches, 1,252 functions, and 2,776 lines, configured coverage 100%.
- Ruff, strict mypy, ESLint, strict TypeScript, production build, JSON, whitespace, dependency-tree, full/runtime audit, integrated, historical, golden, G1-G37, and Stage 2.3/3.2/3.3/3.4 freeze gates passed.
- Vulnerabilities: 0 full and 0 runtime.

## Invariance and acceptance state

- Stage 3.5B engineering fingerprint transitions: `0`.
- Historical Stage 3.5A/R1/R2 fingerprint transitions: `0`.
- Frozen-family fingerprint transitions: `0`.
- Backend production changes: `0` files.
- Frontend production changes: `2` files, both presentation bindings.
- New demand, resistance, concrete-capacity, or anchor-capacity equations: `0`.
- Controlled engineering artifact changes: `0`.
- Dependency, lockfile, workflow, freeze-manifest, and freeze-tag changes: `0`.
- Stage 3.5B-R1 hosted CI: accepted — GitHub Actions run `#80`, four of four Ubuntu/Windows backend/frontend jobs green.
- Stage 3.5B-R1 final owner visual acceptance: accepted on 2026-08-29.

No subsequent stage or connection family was started.
