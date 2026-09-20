# FRP Master Connection — Stage 4.5 W/I, RHS and SRS Column Moment Bases Freeze — Codex Order

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Freeze the fully implemented, corrected, hosted-CI-green, and owner-visually-accepted:

`WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION`

Contract: `4.5-RC1`.

This is a governance-first freeze task. Do not begin 316SS expansion or another stage. Do not change Stage 4.5 production engineering behavior except under the expressly bounded nonproduction maintenance rules below.

## 1. Accepted baseline

Require exactly:

`HEAD == origin/main == remote main == 7e81a64d587d5dcfaa13b0936de2b6aabe95a8a5`

Expected subject:

`test: stabilize Windows Stage 4.5 parameterized timing`

Expected commit count: `122`.

Require clean worktree/index.

Engineering implementation:

`45d4a13590f4551926cae5762982284dfd6dc591`

Accepted product/UI correction:

`36f4979e2a4e1ef4cf144c9640974614e18bce03`

Tests-only timing successor:

`7e81a64d587d5dcfaa13b0936de2b6aabe95a8a5`

If refs/count/worktree differ: **STOP before mutation and report one consolidated discrepancy.**

## 2. Accepted QA / CI / owner evidence

Accepted baseline evidence:

- backend: `5,021` tests passed;
- frontend: `848` tests passed;
- configured coverage: `100%`;
- static/build checks passed;
- full/runtime audits: zero findings;
- object-isolated verification passed.

Hosted CI:

- run `#117`;
- attempt `1`;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

Owner final visual/result acceptance is explicitly granted:

`Stage 4.5 visual accepted`

Owner acceptance includes review of:

- independent Units / Column Shape / Connector Layout controls;
- exactly three user-facing shape families;
- no nominal-size shape selection;
- 2x1 member-bolt defaults per active angle;
- 1x1 foundation-attachment default per active angle;
- zero-offset face-centered angle placement;
- W/I, RHS and SRS geometry;
- TWO_X / TWO_Y / FOUR_XY layouts;
- shared-through-bolt identities;
- perpendicular-family clearance;
- correct action-arrow signs;
- LAST VALID / recovery behavior;
- source-limited branch response;
- required total foundation action.

Do not repeat owner visual acceptance unless production behavior changes.

## 3. Freeze supported profile/layout modes

Freeze all nine RC1 modes:

### W/I Shape Column
- `TWO_X`
- `TWO_Y`
- `FOUR_XY`

### Hollow Rectangular Tube / RHS
- `TWO_X`
- `TWO_Y`
- `FOUR_XY`

### Solid Rectangular Tube / SRS
- `TWO_X`
- `TWO_Y`
- `FOUR_XY`

Freeze separation of Units, Column Shape, and Connector Layout. User geometry remains editable and is not constrained to nominal catalog sizes.

## 4. Freeze corrected default geometry

### Member bolts
Each active angle defaults to:

- `Across extrusion count = 2`
- `Along leaf count = 1`

The pair is symmetric about the angle extrusion centerline. No third/center bolt exists by default.

### Foundation attachments
Each active angle defaults to:

- `Across extrusion count = 1`
- `Along leaf count = 1`

Gauge/pitch are N/A/noncontrolling where count is one.

### Centered angle placement
For every active angle:

`tangential extrusion center offset = 0`

means the angle extrusion is centered on the geometric tangential centerline of its selected column face.

Positive/negative offsets remain user-editable relative to that centered position.

Freeze this for W/I web/flange faces, RHS exterior faces, and SRS exterior faces.

## 5. Freeze physical bolt paths

### W/I
Preserve accepted web-face and flange-face connection paths, including shared web shanks where applicable.

### RHS
Preserve near wall / cavity / far wall topology and actual exterior-to-exterior shared through-bolt identity. Do not infer cavity material or equal-wall participation.

### SRS
Preserve continuous solid through-bolt paths. Do not substitute thin-wall behavior.

### FOUR_XY
Preserve distinct perpendicular bolt families and accepted elevation staggering so shanks do not intersect.

Connector count does not establish load-sharing fractions.

## 6. Freeze actions and total foundation handoff

Freeze accepted RC1 actions:

- signed axial `N`;
- signed `Vx`;
- signed `Vy`;
- signed `Mx`;
- signed `My`.

Independent user-input vertical-axis torsion remains outside RC1. Reference-generated `Mz` remains retained.

Freeze exact required total foundation wrench authority independent of unresolved connector sharing.

## 7. Freeze branch/contact/source boundaries

Freeze:

- no automatic 50/50 or quarter sharing;
- complete connector/contact/shank response requires applicable complete-base-response authority;
- unresolved branch demand remains unavailable/source-required;
- individual per-bolt/anchor demand is not fabricated;
- unknown demand is never treated as zero;
- direct column-end contact remains separate;
- compression sign alone does not establish active contact distribution;
- foundation anchor/concrete capacity remains external;
- overall column/member strength/stability remains outside this connection contribution.

## 8. Native numerical authority

Freeze integration with accepted native engines, including where applicable:

- Calculation Slice 7;
- Calculation Slice 8;
- Stage 2.5A;
- accepted bolt/vector/local-FRP consumers;
- exact wrench/reference transport;
- complete-base-response source validation.

Freeze the rule:

**each accepted engine owns its native numerical output.**

No cross-engine tolerance, residual redistribution, or forced reserialization is authorized.

## 9. Frontend / preview / action rendering

Freeze:

- backend-authoritative geometry;
- backend-bound action arrows and labels;
- Units / Shape / Layout independence;
- editable profile dimensions;
- centered zero-offset semantics;
- 2x1 / 1x1 defaults;
- count-aware N/A controls;
- current-preview fingerprint trace;
- explicit design check;
- source/result trace;
- required total foundation action;
- direct-contact panel;
- branch/source limitation panels.

Freeze action-sign consistency among editor, backend preview record, reference inspector, scene arrow vector, and scene label.

Freeze LAST VALID behavior:

- invalid current inputs do not fabricate current engineering geometry;
- last-valid geometry is explicitly marked;
- stale arrows are hidden/noncurrent;
- validation reasons are visible;
- invalid -> valid automatically recovers;
- stale responses cannot overwrite newer current preview.

Frontend remains presentation-only.

## 10. Future scope remains open

Do not freeze or begin:

- 316SS connector provider;
- additional moment/base families;
- generalized unqualified contact/sharing models;
- full anchor/concrete design;
- full column strength/stability;
- stiffness/rotation/full-strength classification.

## 11. Historical freeze tags

Verify all **twelve existing freeze tags** locally/remotely and their peeled targets, including:

`stage-4.4-angle-column-two-leg-moment-base-freeze`

which must peel to:

`99befa9780e7c7abf72c8a33e5eb45b9e368d916`

Do not move/recreate/delete/retarget any existing tag.

Any mismatch: STOP.

## 12. Stage 4.5 controlled artifacts

Verify repository-controlled artifacts:

Original Stage 4.5 order/spec SHA-256:

`6D6CCA01C8AE979BF00F369D6D36317AE98E41BC8BF0F2DA4020F429B1614135`

Original acceptance matrix SHA-256:

`68695DFC75C51E85982ED07E76ED7A4D0B344F1CCE7AE4425A9842260967074D`

R1 UI/action correction order SHA-256:

`06EEA4B207E55763C522622F148938EA5F006C51124B33CD8A532A06C07B693C`

R2 centering/two-bolt correction order SHA-256:

`4E9663E11EE3654FC5B46FC1D28BD68D10ACEA4F30418DF41906911C4A024D58`

R3 Windows timing correction order SHA-256:

`59B466EFB3621AC442B3FC926FD1D2035BBCD7C2B6AF513D5B42A29DEF19288D`

Do not rewrite controlled engineering artifacts merely to freeze.

## 13. Exhaustive pre-mutation freeze audit

Perform one consolidated read-only sweep before mutation. Verify at minimum:

1. Stage 4.5 product exists exactly once.
2. All nine profile/layout modes exist.
3. Units has exactly U.S./S.I. choices.
4. Shape has exactly W/I / Hollow Rectangular Tube / Solid Rectangular Tube choices.
5. Layout remains separate.
6. No nominal-size production shape selectors remain.
7. Active angle defaults are 2x1 member bolts.
8. Active angle defaults are 1x1 foundation attachment.
9. Offset zero centers every active angle on its selected face.
10. User +/- offsets behave correctly.
11. Shared shank identities remain correct.
12. Perpendicular bolt families remain collision-free.
13. Total foundation action remains exact.
14. No automatic half/quarter sharing exists.
15. Source-limited branch response remains fail-closed.
16. Action-sign matrix passes.
17. Acceptance matrix passes.
18. All 24 reference fixtures pass.
19. Prescribed source-absent/source-present sweeps pass.
20. Slice 7 / Slice 8 / Stage 2.5A regressions pass.
21. Stage 4.4 freeze remains exact.
22. All twelve historical freeze audits/tags pass.
23. Valid preview refresh passes.
24. LAST VALID / recovery passes.
25. Full/runtime audits zero.
26. Dependency/workflow state unchanged.
27. No 316SS/later-stage work exists.

Collect all safe preflight blockers into one report rather than stopping at the first known maintenance issue.

# Bounded standing maintenance authority

## 14. Historical-test successor safety

Without further owner approval, Codex may make tests-only repository-wide corrections for the known brittle historical/current identity pattern.

Required:

- preserve original historical digest/object authority;
- preserve tamper detection;
- preserve tags/manifests;
- unauthorized production/engineering/dependency/workflow changes still fail;
- never replace historical hashes with current hashes;
- never skip/xfail/delete protection.

If required, consolidate into one tests-only maintenance successor, run full QA/object isolation, push normally, require hosted 4/4 green, then resume freeze automatically.

Suggested subject:

`test: make Stage 4.5 freeze guards successor-safe`

If production/engineering changes are required: STOP.

## 15. Security maintenance

Standing npm-audit network permission remains valid.

If a new dev-only full-audit finding appears while runtime audit remains zero, Codex may automatically make a minimal lockfile/patch/compatible-minor successor only when there is no major/toolchain migration, new dependency, production-code change, or workflow change.

Full QA/object isolation/hosted 4/4 green is required before freeze resumes.

Major/breaking/production changes require STOP.

## 16. Windows timing maintenance

For hosted Windows frontend:

- retry once for a timing-only 5-second timeout;
- if repeated and diagnosed as timing-only, use per-test timeout up to 15,000 ms;
- require 10/10 local Windows passes;
- no global timeout, sleeps, skipped tests, weakened assertions, or production changes.

For one parameterized test body, all cases count as one timing-maintenance unit.

Up to three distinct test bodies in this freeze cycle may be stabilized without another owner approval.

## 17. Verification-environment authority

Previously approved equivalents remain valid:

- `python -m mypy` if wrapper blocked;
- existing trusted WSL/Linux for equivalent verification;
- Git-aware blob checks instead of false CRLF comparisons.

No QA reduction.

## 18. Freeze manifest

On the final accepted pre-freeze baseline after any bounded maintenance successors, create:

`docs/governance/STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_FREEZE_MANIFEST.json`

Bind at minimum:

- stage `4.5`;
- product ID `WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION`;
- contract `4.5-RC1`;
- engineering implementation `45d4a13590f4551926cae5762982284dfd6dc591`;
- accepted product/UI correction `36f4979e2a4e1ef4cf144c9640974614e18bce03`;
- tests-only timing successor `7e81a64d587d5dcfaa13b0936de2b6aabe95a8a5`;
- actual current pre-freeze baseline/count;
- accepted CI #117 attempt 1, 4/4 green;
- accepted product QA `5021/848`;
- 100% coverage;
- zero audits;
- owner visual acceptance;
- all nine profile/layout modes;
- Units/Shape/Layout separation;
- 2x1 member-bolt defaults;
- 1x1 foundation defaults;
- zero-offset face centering;
- shared-shank/elevation rules;
- action-sign correction;
- total foundation action authority;
- no-sharing rule;
- source/qualification/foundation boundaries;
- Stage 4.4 freeze verification;
- all twelve existing freeze tags;
- future 316SS/later-stage boundary;
- any bounded maintenance successor provenance.

Compute/report manifest SHA-256.

## 19. Governance updates and scope gate

Update only narrow governance/documentation records required to register the Stage 4.5 freeze.

Normal freeze-governance commit must change zero:

- backend/frontend production files;
- engineering calculation files;
- dependencies/lockfiles;
- workflows;
- tests;
- controlled Stage 4.5 engineering artifacts;
- existing tags.

Only governance/docs/freeze-manifest paths are authorized in the normal governance commit.

## 20. QA and governance commit

Run complete QA:

- full backend/frontend;
- 100% configured coverage;
- Ruff / strict mypy;
- ESLint / strict TypeScript;
- production build;
- pip check;
- both npm audits zero;
- JSON/whitespace/dependency checks;
- Stage 4.5 acceptance matrix;
- all 24 fixtures;
- prescribed sweeps;
- Slice 7/8 / Stage 2.5A regressions;
- Stage 4.4 freeze;
- all twelve historical freeze audits;
- manifest/register integrity.

Normal governance commit:

`chore: freeze Stage 4.5 W/I RHS SRS column moment bases baseline`

Normal expected final count:

`123`

If bounded maintenance successors are needed, use the same governance subject afterward and report actual later count.

Do not amend accepted prior commits.

No tag yet.

## 21. Object-isolated verification / push / hosted CI

After governance commit:

- fresh depth-one / no-tags / no-alternates clone;
- complete QA again;
- clean tree.

Owner pre-authorizes a normal non-force push of the exact verified governance/finalization commit.

No force. No tag yet.

Require:

`HEAD == origin/main == remote main`

Then direct hosted:

- Backend Ubuntu PASS
- Backend Windows PASS
- Frontend Ubuntu PASS
- Frontend Windows PASS

Apply §16 only under its exact timing-only conditions.

## 22. Freeze tag

After the **final accepted freeze-governance/finalization commit** has direct hosted 4/4 green, create and normally push:

`stage-4.5-wi-rhs-srs-column-moment-bases-freeze`

Annotation:

`Stage 4.5 W/I RHS SRS column moment bases freeze`

The tag must point to the final accepted freeze-governance/finalization commit.

Verify local/remote tag object and peeled commit.

## 23. Final frozen identity

After tag verification:

Stage 4.5 = `FROZEN`

Record separately:

- engineering implementation `45d4a13590f4551926cae5762982284dfd6dc591`;
- accepted product correction `36f4979e2a4e1ef4cf144c9640974614e18bce03`;
- tests-only timing successor `7e81a64d587d5dcfaa13b0936de2b6aabe95a8a5`;
- any bounded maintenance successors;
- final freeze-governance/finalization commit and count;
- freeze tag object/peeled commit.

Confirm no 316SS/later stage began.

## 24. Completion report

Report starting baseline/count; owner acceptance; product CI; twelve historical tags; Stage 4.5 artifact hashes; acceptance matrix/fixtures/sweeps; nine modes; Units/Shape/Layout controls; 2x1 / 1x1 defaults; centered placement; shared-shank/perpendicular-clearance rules; action-sign audit; total foundation wrench; no-sharing/source/foundation boundaries; LAST VALID behavior; bounded maintenance if any; manifest path/hash; governance paths; production/dependency/test/workflow counts; complete QA; governance/finalization commit; object-isolated verification; push refs; hosted CI; freeze tag object/peeled commit; final clean state; no 316SS/later stage; final frozen status.

**END OF STAGE 4.5 W/I RHS SRS COLUMN MOMENT BASES FREEZE ORDER — DO NOT PROCEED IF THIS LINE IS MISSING**
