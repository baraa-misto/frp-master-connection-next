# Stage 3.5C-R1 Signed Shear-Arrows and Axial-Compression UI Clarification

## Authority and accepted baseline

The controlling correction order was verified before repository mutation:

- SHA-256: `181345321788B4D4F8632B17B720B35CB63886AB6A91DD02B8DCEF16772DB1DA`;
- final sentinel: present and exact;
- accepted baseline: `af12eafd5b97696ae4272ba13a2933eefaac36d9` on clean synchronized `main`;
- Stage 3.5C hosted evidence: GitHub Actions run `#81`, all four Ubuntu/Windows backend/frontend jobs green, approximately 5 minutes 37 seconds.

The two owner comments reopened final Stage 3.5C visual acceptance: signed shear
labels changed while their physical arrows did not reverse, and the axial field did
not plainly state its positive-compression-magnitude convention.

## Pre-mutation reproduction and first failure boundary

For `P_u = 20 kip`, `V_S = +4 kip`, and `V_T = +10 kip`, the backend and API
returned force `(4, 10, -20) kip` at authoritative reference `(0, 0, 4) in. For
`V_S = -4 kip` and `V_T = -10 kip`, they returned `(-4, -10, -20) kip` at the
same reference. The combined foundation force changed identically and no backend
action/reference value was lost.

The first signed-arrow failure boundary was
`buildColumnBaseWebAngleSceneModel()` → `appliedArrows()`. It retained signed
values and senses but assigned fixed `+S_C`, `+T_C`, and `+L_C` presentation axes.
The shared renderer correctly drew those supplied axes. Real-browser projected
arrow endpoints were therefore identical before correction when only shear signs
changed, even though labels changed from positive to negative.

The axial field was labeled only `Axial compression`; the help was abbreviated;
and the scene presented backend longitudinal `-20` as a `−20` label on a fixed
`+L_C` arrow. Negative entry was already rejected and retained the last-valid
scene, but its validation message did not state the complete magnitude convention.
Exact-zero actions also remained in the scene model and could be exposed through
the shared zero-action overlay.

## Correction

- `appliedArrows()` now derives each physical arrow axis from the sign of the
  backend-authored component while retaining the authoritative action origin.
- Exact-zero components are omitted from the Stage 3.5C scene model; no epsilon,
  rounding, or engineering-value adjustment is used.
- Axial compression remains backend engineering component `-P_u L_C`, but its
  presentation arrow points along `-L_C` and displays the positive compression
  magnitude.
- The normal field is labeled `Axial compression (positive magnitude)` and its
  adjacent help states the direction, allowed magnitude range, and excluded
  uplift/tension scope.
- Negative entry remains locally invalid, keeps the workspace mounted, and uses
  the existing last-valid preview behavior with the controlled clarification.
- The inline arrow editor and sidebar field use the same positive-magnitude axial
  request state; no signed axial-force field or duplicate state was added.

## Browser verification

- Positive `V_S/V_T` arrows followed `+S_C/+T_C`; negative values moved their
  projected endpoints to the exact opposing sides while preserving signed labels.
- `P_u = 20 kip` displayed `+20.00 kip` on the arrow along `-L_C` from the backend
  action reference.
- Exact-zero axial, web-plane, and web-normal components produced no action label
  or arrow.
- `P_u = -20 kip` produced the controlled nonnegative-compression message, retained
  the last-valid scene, and kept the workspace mounted.
- Signed arrows remained unchanged across Single `+T_C`, Single `-T_C`, symmetric
  Double, 3D, Front, Top, Side 1, Side 2, Fit, Reset, Solid, and X-ray presentation.
- Navigation remained presentation-only and did not stale engineering results.

## Engineering invariance and acceptance state

- Backend production changes: `0` files.
- Frontend production changes: `2` files, both Stage 3.5C presentation/UI bindings.
- Stage 3.5C engineering fingerprint transitions: `0`.
- Historical Stage 3.5 fingerprint transitions: `0`.
- Frozen-family fingerprint transitions: `0`.
- Controlled engineering artifact changes: `0`.
- New demand, resistance, uplift/tension, bolt-tension, prying, concrete, or anchor
  authority: `0`.
- Dependency, lockfile, workflow, freeze-manifest, and freeze-tag changes: `0`.
- Complete frontend QA: 547 tests in 37 files; 3,882 statements, 3,176 branches,
  1,363 functions, and 2,967 lines at configured 100% coverage.
- Complete backend QA: 2,540 tests; 19,579 statements and 5,636 branches at
  configured 100% coverage.
- Integrated QA, strict lint/type/build gates, freeze audits, whitespace checks,
  and both npm audits pass; full/runtime vulnerability counts are zero.
- Fresh object-isolated depth-one verification is required after the exact commit
  and is recorded in the Stage 3.5C-R1 completion report.
- Stage 3.5C-R1 hosted CI: GitHub Actions run `#82` accepted four of four
  Ubuntu/Windows backend/frontend jobs green in approximately 5 minutes 43 seconds.
- Final owner visual acceptance: accepted directly by the owner on 2026-08-29.

No subsequent stage or connection family was started.
