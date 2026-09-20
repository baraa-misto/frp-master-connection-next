# FRP Master Connection — Stage 4.5 Centered Angles and Two-Bolt Default Correction — Order R2

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Apply the owner-requested Stage 4.5 corrections before visual acceptance:

1. Default to **two horizontal member bolts per active base angle**, not three.
2. Default every active base angle to be **centered on its selected column face**, not shifted.
3. Preserve the already-corrected independent Units / Column Shape / Connector Layout controls, one-anchor-per-angle default, action-sign rendering, source boundaries, and LAST VALID behavior.

Do not freeze Stage 4.5 in this order. Do not begin 316SS or another stage.

## 1. Starting baseline

Require exactly:

`HEAD == origin/main == remote main == 636cfd133c3f88a09c22063d6428713fa818cb3d`

Expected subject:

`fix: separate Stage 4.5 profile controls and defaults`

Expected commit count: `120`.

Require clean worktree/index.

Accepted evidence:

- 4,958 backend tests;
- 846 frontend tests;
- 100% configured coverage;
- hosted CI #115 attempt 1: 4/4 green;
- all twelve existing freeze tags unchanged.

If baseline differs: STOP and report one consolidated discrepancy.

## 2. Preserve accepted Stage 4.5 behavior

Preserve:

- Units selector with only `U.S. Units` / `S.I. Units`;
- Column Shape selector with:
  - `W/I Shape Column`;
  - `Hollow Rectangular Tube`;
  - `Solid Rectangular Tube`;
- Connector Layout selector with `TWO_X`, `TWO_Y`, `FOUR_XY`;
- editable profile dimensions;
- one foundation attachment per active angle by default;
- count-aware N/A controls;
- backend-bound action rendering/signs;
- complete-base-response qualification;
- no automatic half/quarter sharing;
- exact total foundation action;
- direct contact separation;
- native numerical authority;
- external anchor/concrete boundary;
- current / LAST VALID / recovery behavior.

Do not reintroduce nominal-size production selectors.

# A. Two member bolts per active angle

## 3. Default bolt count

For every newly initialized active Stage 4.5 base angle, default to:

- `Across extrusion count = 2`
- `Along leaf count = 1`

This means **two horizontal bolts in one row per angle**.

Apply to all nine modes:

- W/I TWO_X / TWO_Y / FOUR_XY;
- RHS TWO_X / TWO_Y / FOUR_XY;
- SRS TWO_X / TWO_Y / FOUR_XY.

Inactive branches create no hidden hardware.

This is a default only; user edits remain allowed within valid geometry.

## 4. Bolt symmetry

The two bolts shall be centered symmetrically about the base-angle extrusion centerline.

For center `s_c` and gauge `g`:

- bolt 1 = `s_c - g/2`
- bolt 2 = `s_c + g/2`

No center/third bolt.

The gauge remains the editable center-to-center spacing.

With `Along leaf count = 1`, along-leaf pitch is N/A/noncontrolling.

## 5. Shared-shank behavior

Preserve accepted physical shared-shank identity for:

- W/I web-face opposite-angle bolts;
- RHS opposite-face through-bolts;
- SRS opposite-face through-bolts.

Reducing 3 -> 2 bolts shall not create phantom shanks, break shared identity, change branch-sharing authority, or disturb perpendicular-family elevation staggering.

# B. Center angles on the column

## 6. Controlling centering rule

For every active base angle, default placement shall center the angle extrusion on the geometric centerline of the selected receiving column face in the face-tangential direction.

User meaning:

`tangential extrusion center offset = 0`

means:

**centered on the selected column face.**

It must not mean:

- start-of-angle coordinate;
- face-edge coordinate;
- pedestal/global origin.

If the column itself has X/Y placement offsets, centering follows the actual shifted column face.

## 7. Backend placement formula

For each selected face, backend geometry shall identify:

- face center/reference;
- face tangent/extrusion axis;
- face normal.

For angle length `L_A` and user tangential center offset `e_t`:

`angle_center = face_center + e_t * face_tangent`

and endpoints:

`angle_center ± (L_A/2) * face_tangent`.

Default `e_t = 0`.

If the current code already stores zero but renders shifted, correct the backend interpretation/placement math rather than changing the displayed zero to an arbitrary compensating number.

## 8. Shape-specific centering

### W/I
- X/web-face angles: center on the selected web-face tangential midline.
- Y/flange-face angles: center on the selected exterior flange-face tangential midline.
- FOUR_XY: all four independently centered on their own faces.

### RHS
- center each active exterior-face angle on that face's tangential midline;
- preserve near wall / cavity / far wall and through-bolt topology.

### SRS
- center each active exterior-face angle on that face's tangential midline;
- preserve continuous solid through-bolt paths and perpendicular bolt-family elevation separation.

## 9. User offset remains editable

Keep tangential center offset user-editable.

Semantics:

- `0` = centered;
- positive = shift along positive face tangent;
- negative = shift along negative face tangent.

Changing the offset updates the complete connector assembly coherently:

- angle solid;
- member bolts;
- foundation attachment geometry where tied to the angle;
- hardware paths;
- validation;
- fingerprint;
- scene.

Do not silently recenter explicit nonzero user offsets.

# C. Preserve one anchor per angle

## 10. Foundation default

Keep:

- `Across extrusion count = 1`
- `Along leaf count = 1`

for each active angle.

The single attachment remains at its configured centroid/reference.

Gauge/pitch are N/A/noncontrolling when counts are one.

Concrete/anchor capacity remains external.

# D. Engineering behavior and viewer signs

## 11. Preserve action rendering fix

Do not regress the accepted sign/rendering correction from:

`636cfd133c3f88a09c22063d6428713fa818cb3d`.

For every current valid preview, editor value, backend action record, reference inspector, scene arrow vector, and scene label must agree for:

- Fx;
- Fy;
- Fz/N;
- Mx;
- My.

## 12. No engineering-method change

Do not change:

- total foundation action mechanics;
- branch allocation;
- complete-base-response source requirement;
- contact response;
- Slice 7 / Slice 8 / Stage 2.5A;
- local FRP checks;
- bolt strength authority;
- status precedence;
- foundation external-design boundary.

If centered geometry exposes a real engineering incompatibility, report it instead of altering accepted mechanics.

# E. Preview / validation

## 13. Valid edits

For valid current edits prove:

`editor -> preview request -> backend geometry/actions -> current fingerprint -> rendered scene`

Test independently:

- shape;
- layout;
- column dimensions;
- angle length;
- tangential offset;
- member bolt gauge/count;
- foundation attachment position;
- loads;
- units.

## 14. Invalid geometry

Preserve fail-closed behavior.

Invalid examples include:

- centered angle exceeds selected face;
- 2-bolt gauge violates edge/spacing;
- through-bolt misses member region;
- perpendicular shanks collide;
- anchor/foot geometry invalid.

On invalid input:

- retain marked `LAST VALID`;
- hide/noncurrent-label stale arrows;
- show reasons;
- stale design;
- valid correction automatically restores current preview.

Do not auto-shift a centered angle merely to make invalid geometry pass.

# F. Mandatory regression coverage

## 15. Tests

Add tests proving:

1. every active angle defaults to 2x1 member bolts;
2. no third bolt exists;
3. every active angle defaults to 1x1 foundation attachment;
4. inactive branches create no hidden hardware;
5. zero offset centers W/I web-face angles;
6. zero offset centers W/I flange-face angles;
7. zero offset centers RHS X/Y faces;
8. zero offset centers SRS X/Y faces;
9. FOUR_XY centers all four independently;
10. TWO_X/TWO_Y center only active pairs;
11. positive/negative user offsets move in correct tangent direction;
12. offset survives U.S./S.I. round trip;
13. two bolts are symmetric about extrusion center;
14. shared-shank identities remain correct;
15. perpendicular shanks remain collision-free;
16. one-anchor group remains coherent with centered angle;
17. valid edits refresh;
18. invalid -> LAST VALID;
19. invalid -> valid recovery;
20. stale request cannot overwrite newer scene;
21. full action-sign matrix remains green.

Update Stage 4.5 acceptance records only as required by this owner-authorized correction. Do not weaken existing engineering requirements.

# G. Browser review

## 16. Visual QA

Review all nine modes in browser:

- W/I TWO_X / TWO_Y / FOUR_XY;
- RHS TWO_X / TWO_Y / FOUR_XY;
- SRS TWO_X / TWO_Y / FOUR_XY.

For each confirm:

- zero-offset active angles are visually centered on selected faces;
- exactly two member bolts per active angle by default;
- exactly one foundation attachment per active angle by default;
- no hidden inactive hardware;
- through-bolt/shared-shank paths are correct;
- perpendicular shanks do not collide;
- current action arrows match inputs/reference inspector;
- valid edit refresh;
- invalid LAST VALID;
- recovery works.

Capture representative screenshots for W/I, RHS and SRS, plus centered 2-bolt and 1-anchor defaults.

Leave application running.

# H. QA / publication

## 17. Historical maintenance authority

Use the standing repository-wide tests-only successor-safety authority for the already-known brittle historical/current identity test pattern. Preserve historical digests, tamper detection and all twelve freeze tags.

No dependency/workflow changes are authorized.

## 18. Complete QA

Require:

- full backend suite;
- full frontend suite;
- 100% configured coverage;
- Ruff / strict mypy;
- ESLint / strict TypeScript;
- production build;
- pip check;
- full/runtime npm audits zero;
- Stage 4.5 acceptance matrix;
- all 24 reference fixtures;
- prescribed source-absent/source-present sweeps;
- Slice 7 / Slice 8 / Stage 2.5A regressions;
- Stage 4.4 freeze regression;
- all twelve historical freeze audits.

## 19. Commit

Create a new successor commit; do not amend:

`636cfd133c3f88a09c22063d6428713fa818cb3d`

Required subject:

`fix: center Stage 4.5 base angles and use two member bolts`

Expected commit count:

`121`

No tag.

## 20. Object-isolated verification and push

After commit:

- fresh depth-one / no-tags / no-alternates clone;
- complete QA again;
- verify authorized diff scope;
- clean tree.

If all gates pass, owner authorizes a normal non-force push of the exact successor to `main`.

No tags.

Require:

`HEAD == origin/main == remote main`

Then obtain direct hosted:

- Backend Ubuntu PASS
- Backend Windows PASS
- Frontend Ubuntu PASS
- Frontend Windows PASS

Use existing bounded Windows timing rules only for genuine timing-only failures.

## 21. Owner acceptance

Do not freeze Stage 4.5 automatically.

Do not begin 316SS or another stage.

Owner final visual/result acceptance remains required.

## 22. Completion report

Report:

1. baseline/count;
2. 2-bolt default;
3. centering root cause;
4. centering implementation;
5. W/I centering;
6. RHS centering;
7. SRS centering;
8. user offsets;
9. 2-bolt symmetry/shared shanks;
10. 1-anchor preservation;
11. action-sign regression;
12. valid/invalid preview behavior;
13. acceptance-matrix changes;
14. browser evidence;
15. changed paths;
16. historical/freeze protection;
17. backend/frontend QA;
18. coverage/static/build/security;
19. commit hash/subject/count;
20. isolated verification;
21. push/final refs;
22. hosted CI;
23. running application URL;
24. confirmation no freeze/316SS/later stage began.

**END OF STAGE 4.5 CENTERED ANGLES AND TWO-BOLT DEFAULT CORRECTION ORDER R2 — DO NOT PROCEED IF THIS LINE IS MISSING**
