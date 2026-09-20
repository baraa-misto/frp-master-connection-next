# FRP Master Connection — Stage 4.5 UI Defaults and Action Rendering Correction — Order R1

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Correct three owner-review issues in the implemented Stage 4.5 product before visual acceptance:

1. separate units, column shape and connector layout into independent controls;
2. change the Stage 4.5 default fastener arrangement to three horizontal member bolts per active angle and one foundation anchor per active angle;
3. correct the 3D action-arrow/label sign mapping so the viewer exactly matches the current backend preview, including positive `Vy`.

This is a Stage 4.5 successor correction.

Do not freeze Stage 4.5 in this order.

Do not begin 316SS or another stage.

## 1. Starting baseline

Require exactly:

`HEAD == origin/main == remote main == 45d4a13590f4551926cae5762982284dfd6dc591`

Expected subject:

`feat: add W/I RHS SRS column moment bases`

Expected commit count:

`119`

Require clean worktree/index.

Accepted implementation evidence:

- 4,814 backend tests;
- 800 frontend tests;
- 100% configured coverage;
- local/object-isolated QA passed;
- hosted CI #114 attempt 1: 4/4 green;
- all twelve existing freeze tags unchanged.

If baseline differs: STOP and report.

## 2. Owner-review evidence / current behavior

The current Stage 4.5 left panel mixes three independent concepts:

- display/input unit system;
- profile/column shape;
- named constructive size presets such as `WI12`, `RHS8`, `RHS10X8`, `SRS8`, `SRS10X8`.

Owner requires these concerns to be separated.

The reviewed W/I `FOUR_XY` case also shows a viewer action-sign defect.

Current input/reference trace:

- `N = +30 kip`;
- `Vx = -10 kip`;
- `Vy = +4 kip`;
- `Mx = -50 kip-in`;
- `My = +30 kip-in`.

The backend reference inspector correctly reports:

- `FX = -10 kip`;
- `FY = +4 kip`;
- `FZ = +30 kip`;
- `MX = -50 kip-in`;
- `MY = +30 kip-in`.

But the 3D viewer label displays approximately:

`Column Fy = -4.00 kip`

for the same current preview.

This is a frontend/current-scene action-rendering inconsistency. Do not change backend action signs merely to match the viewer.

## 3. Units control

Replace the current mixed/preset presentation with one explicit unit-system control containing exactly two user-facing choices:

- `U.S. Units`
- `S.I. Units`

Internal enum/contract identifiers may remain unchanged if already frozen/used by APIs.

Changing units shall:

- preserve the same physical geometry, actions and hardware;
- convert editable display/input values consistently;
- not change column shape;
- not load a named size/preset;
- not change connector layout;
- not silently reset source references except where existing unit-conversion contract explicitly requires a deterministic equivalent representation.

Add U.S. -> S.I. -> U.S. round-trip tests for all three column shapes and each applicable layout.

## 4. Column-shape control

Add one independent user-facing column-shape selector with exactly these three choices:

1. `W/I Shape Column`
2. `Hollow Rectangular Tube`
3. `Solid Rectangular Tube`

Preserve existing internal profile IDs where appropriate:

- `WI`;
- `RHS`;
- `SRS`;

or the exact repository equivalents.

Do not include nominal/default dimensions in the shape label.

Remove the size-named Stage 4.5 load buttons/presets from the normal product UI:

- `WI12`;
- `RHS8`;
- `RHS10X8`;
- `SRS8`;
- `SRS10X8`;
- and their U.S./S.I. duplicate buttons.

Named-size constructive fixtures may remain in test-only/backend fixture infrastructure if required by acceptance tests, but they shall not be presented as the user's shape-selection model.

Changing shape shall select the correct profile family/schema. Geometry dimensions remain user-editable.

If a deterministic initial geometry is needed when switching profile family, use one generic constructive default per family without exposing a nominal size name. It remains only a starting geometry, not a catalog section or design restriction.

## 5. Connector-layout control remains separate

Keep connector arrangement as its own independent selector.

Preserve the accepted layout identities/applicability:

- `TWO_X`;
- `TWO_Y`;
- `FOUR_XY`;

with profile-specific physical meaning exactly as already implemented.

Changing units must not change layout.

Changing shape shall not silently choose a different layout unless the previously selected layout is genuinely inapplicable; if so, use existing explicit validation/controlled fallback behavior and make it visible.

Do not infer load sharing from connector count.

## 6. Default member-bolt arrangement

For every newly initialized Stage 4.5 active base angle, change the default member attachment to:

**three horizontal bolts in one row per angle.**

Under the current UI/local-coordinate terminology this means:

- `Across extrusion count = 3`;
- `Along leaf count = 1`.

The three bolts shall be centered symmetrically across the angle extrusion about the configured member-bolt centroid/reference.

The controlling spacing/gauge must satisfy the existing geometry/hole/edge validation.

Do not invent a second row.

Do not imply that three bolts establish branch-sharing authority.

This is a default only; the user may subsequently edit the bolt group within valid geometry.

### Count-aware input behavior

When `Along leaf count = 1`, an along-leaf pitch has no physical pair to space.

The UI shall either:

- disable/hide the irrelevant pitch input and show it as not applicable; or
- retain it as noncontrolling stored UI state but prove it is excluded from geometry/fingerprint/mechanics while count is one.

Prefer explicit disabled/N/A presentation.

Spacing values shall become active again deterministically if count increases.

## 7. Default foundation attachment arrangement

For every newly initialized Stage 4.5 active base angle, change the default foundation attachment to:

**one anchor/attachment per angle.**

Under the current controls:

- `Across extrusion count = 1`;
- `Along leaf count = 1`.

The single attachment is placed at the configured foundation-attachment centroid/reference.

Do not create phantom gauge/pitch offsets for a one-anchor group.

Gauge and pitch controls shall be disabled/hidden/N/A, or proven noncontrolling while both counts equal one.

This is only the connection-model default geometry.

Concrete/anchor capacity remains external exactly as before.

One anchor per angle does not imply connector sharing or complete base-response qualification.

## 8. Inactive-angle / two-angle layout behavior

For `TWO_X` / `TWO_Y`:

- only physically active angle groups participate in geometry/results;
- inactive angle inputs shall not create hidden bolts/anchors;
- default initialization shall not create four-angle hardware behind a two-angle layout.

For `FOUR_XY`:

- all four active angles receive the three-member-bolt / one-foundation-anchor defaults.

Preserve the accepted perpendicular through-bolt elevation/clearance rules for RHS/SRS and the accepted W/I physical paths.

## 9. Viewer action sign correction

Diagnose the action payload from backend preview through frontend scene mapping before mutation.

For the owner case:

- current backend `FY = +4 kip`;
- viewer must display `Column Fy = +4.00 kip` and the arrow vector must point in the positive current `BASE_XYZ` Y direction.

Do not fix this by changing the backend sign.

Identify the first frontend mapping/rendering layer that changes `+4` into `-4`.

Correct both:

- numeric label sign;
- arrow vector/direction.

## 10. Complete action-rendering sign matrix

Add explicit regression coverage for current-preview action rendering.

For each of the three shapes and each applicable layout, test positive and negative values independently for:

- `Fx`;
- `Fy`;
- `Fz/N`;
- `Mx`;
- `My`.

For every case require:

1. editor value;
2. backend preview action record;
3. reference/action inspector;
4. scene arrow vector;
5. scene arrow label

to represent the same physical signed action under the documented coordinate convention.

Test zero actions as zero/no misleading direction.

Do not conflate applied column action with opposite foundation reaction.

If the viewer intentionally shows a reaction anywhere, it must be separately labeled as reaction rather than `Column F...`.

## 11. Owner screenshot review invariants

Preserve the reviewed correct behavior:

- required total foundation action remains exact;
- branch response remains `SOURCE_REQUIRED` where qualification is absent;
- no automatic half/quarter sharing;
- W/I frames remain right-handed orthonormal;
- material axes remain profile-specific;
- reference inspector remains backend authoritative;
- direct contact remains separate;
- concrete/anchor design remains external;
- LAST VALID / current-preview behavior remains as accepted in Stage 4.4/4.5.

The owner screenshots show no justification for changing the engineering calculation engines.

## 12. Preview / editing behavior

After correction, verify all of these independently:

- unit change;
- shape change;
- layout change;
- column dimension edit;
- active-angle dimension edit;
- member bolt count/spacing edit;
- foundation attachment count/location edit;
- load edit.

For every valid current edit:

`input -> preview request -> current backend response -> scene fingerprint -> rendered geometry/actions`

must remain synchronized.

For invalid edits preserve the accepted `LAST VALID` behavior and hide/noncurrent-label stale arrows.

## 13. API / backend authority

Backend remains authoritative for:

- physical profile geometry;
- active angle topology;
- actual bolt/anchor points/paths;
- frames/material axes;
- action/reference records;
- validation;
- fingerprints.

Frontend shall not reconstruct engineering geometry or signs independently.

If the UI needs descriptive labels, map only display names to existing backend IDs.

## 14. Regression / acceptance matrix impact

Update Stage 4.5 tests and controlled acceptance records only if required by the owner-authorized product correction.

Do not silently rewrite independent engineering fixtures to hide a regression.

Preserve all native-engine numerical authority.

At minimum add tests proving:

- exactly two unit choices;
- exactly three user-facing shape choices;
- no size name in shape choices;
- named-size load buttons removed from production UI;
- shape dimensions remain editable;
- generic default initialization by shape;
- default 3x1 member bolts per active angle;
- default 1x1 foundation attachment per active angle;
- count-aware spacing inputs;
- correct active/inactive hardware by layout;
- full action-sign matrix;
- owner `Vy=+4` W/I case renders `+4`;
- unit round-trip preserves physical state;
- shape/layout independence.

## 15. Historical / maintenance authority

Use the standing repository-wide successor-safety authority already established for known brittle historical-test identity patterns.

Preserve original historical digests/tamper detection/freeze tags.

Do not stop file-by-file for the known tests-only pattern if the correction stays within that established class.

All twelve existing freeze tags must remain unchanged.

No dependency/workflow change is authorized.

## 16. Local browser QA

After complete local QA:

- start or safely reuse the repository servers;
- open Stage 4.5 in the approved browser;
- inspect console/network/runtime state.

Manually verify:

### W/I
- `TWO_X`;
- `TWO_Y`;
- `FOUR_XY`.

### RHS
- `TWO_X`;
- `TWO_Y`;
- `FOUR_XY`.

### SRS
- `TWO_X`;
- `TWO_Y`;
- `FOUR_XY`.

For each profile verify:

- U.S./S.I. control independent of shape;
- shape label contains no nominal size;
- geometry remains editable;
- default bolt/anchor arrangement correct;
- load arrows/signs match editor and reference inspector;
- X-ray/hardware paths remain valid;
- valid edit refresh;
- invalid LAST VALID;
- invalid -> valid recovery.

Capture focused screenshots of:

1. the corrected control grouping;
2. default 3x1 member bolts;
3. default 1x1 foundation anchor;
4. positive `Vy` viewer action;
5. one negative `Vy` viewer action;
6. representative W/I, RHS and SRS layouts.

Leave the verified application running for owner review.

## 17. Complete QA

Require:

- full backend suite;
- full frontend suite;
- 100% configured coverage;
- Ruff;
- strict mypy;
- ESLint;
- strict TypeScript;
- production build;
- pip check;
- full/runtime npm audits zero;
- Stage 4.5 acceptance matrix;
- all 24 reference fixtures;
- prescribed sweeps/source-present integrations;
- Slice 7/8;
- Stage 2.5A;
- Stage 4.4 freeze regression;
- all twelve historical freeze audits;
- clean dependency/workflow state.

## 18. Commit

Create a new successor commit; do not amend:

`45d4a13590f4551926cae5762982284dfd6dc591`

Required subject:

`fix: separate Stage 4.5 profile controls and defaults`

Expected commit count:

`120`

No tag.

## 19. Object-isolated verification / push

After commit:

- fresh depth-one / no-tags / no-alternates clone;
- complete QA again;
- verify diff scope and clean tree.

If all gates pass, owner authorizes a normal non-force push of the exact successor to `main`.

No tags.

Then require direct hosted:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

Use established bounded Windows timing rules only for genuine timing-only flakes.

## 20. Owner acceptance

Do not freeze Stage 4.5 automatically.

Leave application running.

Owner final visual/result acceptance remains required after this correction.

Do not begin 316SS or another stage.

## 21. Completion report

Report:

1. starting baseline/count;
2. UI control root cause;
3. action-sign root cause;
4. units control;
5. shape control;
6. layout control;
7. removed production size-preset controls;
8. generic shape defaults;
9. 3x1 member-bolt defaults;
10. 1x1 foundation defaults;
11. count-aware spacing behavior;
12. active/inactive layout hardware;
13. W/I action-sign matrix;
14. RHS action-sign matrix;
15. SRS action-sign matrix;
16. positive-Vy owner fixture;
17. backend/reference/scene equality;
18. unit round-trip;
19. valid/invalid preview behavior;
20. acceptance-matrix/regression updates;
21. browser screenshots;
22. changed paths;
23. historical/freeze protection;
24. backend QA;
25. frontend QA;
26. coverage/static/build/security;
27. commit hash/subject/count;
28. object-isolated verification;
29. push/final refs;
30. hosted CI;
31. running application URL;
32. confirmation no freeze/316SS/later stage started.

**END OF STAGE 4.5 UI DEFAULTS AND ACTION RENDERING CORRECTION ORDER R1 — DO NOT PROCEED IF THIS LINE IS MISSING**
