# FRP Master Connection — Stage 3.5A-R1 Concrete-Wall Paired-Angle Completion — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.5A-R1 is a controlled successor to Stage 3.5A.

It completes the concrete-wall paired-angle product by:

- normalizing Brace/beam presentation labels;
- correcting the incomplete 3D scene;
- changing the default wall-anchor pattern to one anchor per clip angle;
- expanding the horizontal connected member to the six accepted shared profile families.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `454f3ae9090f51d45d8efe17ebaf8cd155ec9542`;
- subject:
  `feat: add paired clip-angle concrete-wall connection`;
- commit count: `81`;
- clean worktree/index.

Hosted CI for this commit is accepted after rerun attempt 2:

- GitHub Actions run #76;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

The first attempt had one Frontend Windows timeout in a pre-existing Clip-Angle test; rerun attempt 2 passed without code changes.

Expected Stage 3.5A production source identities:

- backend/src:
  `ec6fd1d6828de423ddd78521102795d55f1ba2b6`;
- frontend/src:
  `8ce23b8990cb1bc5f682bde92d686c2a1cd4c46e`.

All Stage 2.3/3.2/3.3/3.4 freeze tags remain immutable.

## 3. Historical contract

Historical contract:

`3.5A-RC1`

Historical Stage 3.5A behavior remains reproducible.

Stage 3.5A-R1 adds successor contract:

`3.5A-R1-RC1`

The historical Stage 3.5A default and fingerprints shall not be silently rewritten.

## 4. Presentation-label normalization

Presentation only:

Selector group heading:

`Brace/beam connections`

Normalize applicable connection labels:

- `Brace connection — Direct`
  -> `Brace/beam connection — Direct`
- `Brace connection — Tee connector`
  -> `Brace/beam connection — Tee connector`
- `Brace connection — Symmetric paired clip angles`
  -> `Brace/beam connection — Symmetric paired clip angles`

Existing:

- `Brace/beam connection — Single clip angle`
- `Brace/beam node — Multi-member Tee connector`

remain semantically unchanged.

No request enum, API route, stable connection identity, or engineering fingerprint changes due to labels.

## 5. Concrete-wall product label

Connection selector:

`Beam connection — Paired clip angles to concrete wall`

Workspace connected-member section:

`Connected Member`

Stage 3.5A-R1 remains horizontal/shear-only.

## 6. Connected-profile matrix

The horizontal connected member supports exactly:

1. `FLAT_PLATE`
2. `ANGLE`
3. `CHANNEL`
4. `WIDE_FLANGE_I`
5. `RECTANGULAR_HOLLOW_SECTION`
6. `SOLID_RECTANGULAR_SECTION`

Reuse the frozen Stage 3.3C3 paired-angle connected-profile contracts and physical topology.

No new profile geometry authority.

## 7. Horizontal member semantics

Every profile longitudinal axis remains:

`L_M = +N_W`

There is no connected-member inclination input in Stage 3.5A-R1.

Profile roll and selected physical connection surface remain available where supported by the shared profile registry.

A zero-degree Angle/Channel/Plate member is a valid horizontal member.

## 8. Profile defaults

### Flat Plate

- width: `6 in`;
- thickness: `0.5 in`;
- view length: `16 in`;
- default surface: positive plate face.

### Angle

- Leg Y: `6 in`;
- Leg Z: `6 in`;
- thickness: `0.5 in`;
- view length: `16 in`;
- default selected leg/surface: accepted Leg Y outer face;
- roll: `0°`.

### Channel

- depth: `8 in`;
- flange width: `4 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- view length: `16 in`;
- default surface: web positive face;
- roll: `0°`.

### W/I

Preserve Stage 3.5A default:

- depth: `10 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- view length: `16 in`;
- default surface: web positive face.

### RHS

- depth: `6 in`;
- width: `4 in`;
- wall thickness: `0.5 in`;
- view length: `16 in`;
- default surface: positive Y wall;
- roll: `0°`.

### SRS

- depth: `6 in`;
- width: `4 in`;
- view length: `16 in`;
- default surface: positive Y face;
- roll: `0°`.

Changing family does not move the wall-anchor groups or change the shear load.

## 9. Strict family-specific fields

Only selected-family fields are serialized.

Reject stale/incompatible fields.

Examples:

- SRS with wall thickness -> rejected;
- Flat Plate with web/flange dimensions -> rejected;
- RHS without wall thickness -> rejected;
- unknown family -> rejected.

No permissive catch-all payload.

## 10. Paired connection topology — open profiles

Reuse the exact frozen paired-angle physical resolvers.

### Flat Plate

`Positive Clip Connected Leg -> Flat Plate -> Negative Clip Connected Leg`

### Angle

`Positive Clip Connected Leg -> selected Angle leg -> Negative Clip Connected Leg`

Reject heel/perpendicular-leg/outside-leg paths.

### Channel

`Positive Clip Connected Leg -> selected finite Channel region -> Negative Clip Connected Leg`

Reject junction/outside-region paths.

### W/I

`Positive Clip Connected Leg -> selected finite W/I region -> Negative Clip Connected Leg`

Reject junction/outside-region paths.

## 11. Paired connection topology — RHS

One physical common bolt per axis:

`Positive Clip Connected Leg -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall -> Negative Clip Connected Leg`

Requirements:

- both walls independently contained;
- one continuous shank;
- no internal hardware;
- cavity is not material;
- endpoint-based physical hardware orientation;
- R8 corner exclusions.

## 12. Paired connection topology — SRS

One physical common bolt per axis:

`Positive Clip Connected Leg -> full SRS solid depth -> Negative Clip Connected Leg`

No cavity.

Entry/exit containment required.

## 13. Same wall topology

The paired clip angles remain adjacent to the same concrete wall face.

Changing connected profile shall preserve:

- wall frame;
- angle pair wall-leg contact;
- wall-anchor group centroids;
- anchor embedment direction;
- beam/member end gap semantics.

Invalid profile/angle/wall interference fails closed.

## 14. Required scene completeness

For every valid profile, the backend visualization payload and frontend scene shall contain:

- connected member geometry;
- positive clip angle geometry;
- negative clip angle geometry;
- common connected-member hardware;
- positive wall-anchor group;
- negative wall-anchor group;
- finite concrete wall;
- wall anchor embedment shanks.

The user-observed Stage 3.5A defect is prohibited:

- connected member missing;
- one clip angle missing;
- anchor group shown without its owning clip angle.

No frontend geometry reconstruction.

## 15. Scene ownership identities

Positive and negative clip angles are distinct physical owners.

Scene filtering/de-duplication shall use owner-qualified identities.

Do not de-duplicate mirrored angle primitives merely because their physical-element/material-region names match.

Anchor groups shall remain bound to their correct positive/negative angle owners.

## 16. Default wall-anchor pattern

Each mirrored group defaults to:

- rows: `1`;
- anchors per row: `1`;
- positive centroid `(H,V)=(+3,0) in`;
- negative centroid `(H,V)=(-3,0) in`.

Default coordinates:

- positive anchor: `(+3,0) in`;
- negative anchor: `(-3,0) in`.

Nominal diameter/hole/embedment remain:

- anchor diameter `0.5 in`;
- hole `0.563 in`;
- embedment `4 in`.

The user may increase:

- rows;
- anchors per row;
- pitch;
- gauge.

The positive/negative groups remain identical mirrors.

## 17. Pattern editor behavior

For `1 × 1`:

- exactly one anchor exists per group;
- pitch/gauge do not generate hidden anchors;
- inactive spacing dimensions do not alter geometry.

When rows or anchors-per-row increase:

- pitch/gauge apply under the existing fixed-grid pattern;
- positive and negative groups remain exact mirrors;
- anchors remain owned by the correct clip angle.

No automatic group asymmetry.

## 18. Branch and wall wrenches

The default wall-anchor centroids remain unchanged from Stage 3.5A.

Therefore for default reaction shear `-4 kip`:

Positive group:

- `F_+ = (0,-2,0) kip`;
- `M_+ = (8,0,6) kip-in`.

Negative group:

- `F_- = (0,-2,0) kip`;
- `M_- = (8,0,-6) kip-in`.

Combined wall:

- `F_W = (0,-4,0) kip`;
- `M_W = (16,0,0) kip-in`.

Changing anchor count without changing group centroids does not alter these group/combined wrenches.

## 19. One-anchor rigid-group limitation

A `1 × 1` anchor group has one point at its centroid.

The existing rigid point-group demand model cannot equilibrate a nonzero branch moment using a single point-force degree of freedom.

Therefore for `1 × 1`:

- branch force/moment handoff remains exact;
- anchor coordinate remains exact;
- combined wall handoff remains exact;
- specialized anchor software remains authoritative;
- internal nominal point-anchor force distribution is not calculated.

Return:

`WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION = EXTERNAL_DESIGN_REQUIRED`

Do not fabricate a per-anchor force that ignores the branch moment.

## 20. Multi-anchor nominal demand trace

For groups with sufficient geometry for the accepted rigid-group demand engine:

- Stage 2.5A may provide nominal coordination demand;
- force equilibrium required;
- moment equilibrium required;
- output remains labeled external-anchor-software governed.

If the actual group geometry cannot resolve the branch wrench under existing mechanics, return external-design-required rather than inventing demand.

## 21. Shear-only action

No change from Stage 3.5A:

- one signed vertical reaction shear;
- no user moments;
- no axial/horizontal/out-of-plane input.

Eccentricity-induced transfer moments remain retained.

## 22. Beam/member reference

The connected-member action reference remains backend authoritative and consistent with current geometry.

Profile changes may change the actual connected-member thickness/geometry.

Any resulting physical change in reference offset shall be computed by backend geometry, not hard-coded to W/I.

The handoff moment shall follow the current physical reference.

## 23. Beam/member end gap

Retain the gap control for every connected profile.

The gap is between the connected member end and the concrete wall face.

Requirements:

- finite;
- nonnegative;
- no member/wall penetration;
- angles remain physically connected;
- group positions not silently moved.

## 24. Material axes

Material axes shall appear on:

- connected FRP profile physical regions;
- positive clip-angle regions;
- negative clip-angle regions.

Concrete has no FRP LW/CW/TT axes.

Wall H/V/N frame remains available.

RHS cavity has no material axes.

SRS retains its solid basis.

## 25. Preview / design state

Preserve:

- preview zero resistance calls;
- explicit Run Design Check;
- current/invalid/last-valid/request-failure behavior;
- workspace never blanks.

Profile or anchor-pattern edits stale prior design and request preview.

Presentation labels do not call APIs or stale results.

## 26. External anchor-design handoff

Preserve the Stage 3.5A handoff schema and exact branch/combined wrenches.

Update geometry-dependent fields for:

- selected connected profile;
- current anchor coordinates;
- current 1×1 or expanded pattern;
- current edge distances;
- current specified embedment.

For `1 × 1`, explicitly state that internal anchor-force distribution remains external.

No anchor/concrete capacity fields.

## 27. External design limitations

Always preserve:

- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

For default `1 × 1` groups additionally:

- `WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION = EXTERNAL_DESIGN_REQUIRED`.

## 28. Paired-angle limitations

Preserve all existing paired-angle body/common-group/compatibility/qualification limitations.

No ordinary whole-connection PASS.

Known supported FRP/beam-side numerical failure governs FAIL.

## 29. Historical Stage 3.5A backward compatibility

The original `3.5A-RC1` W/I + 2×2 anchor-group fixture remains reproducible.

Its:

- geometry;
- branch wrenches;
- combined wall wrench;
- demand traces;
- fingerprints;

shall remain exact under the historical contract.

Stage 3.5A-R1 default behavior is introduced only under `3.5A-R1-RC1`.

## 30. API

Existing routes remain.

Accept:

- `3.5A-RC1`;
- `3.5A-R1-RC1`.

Historical contract retains W/I-only and historical default anchor pattern.

Successor contract accepts six profiles and 1×1 default anchor pattern.

Unknown future versions fail closed.

## 31. Frontend connected-member editor

Rename panel to:

`Connected Member`

Expose all six profiles using the shared profile editor.

No separate W/I-only editor.

Profile change:

- preserves reaction shear;
- preserves angle dimensions;
- preserves anchor pattern/group centroids;
- preserves wall geometry;
- preserves gap where valid;
- initializes valid family-specific profile defaults;
- removes stale hidden family fields.

## 32. Connection selector labels

Update presentation strings only.

Group heading:

`Brace/beam connections`

Required normalized labels:

- `Brace/beam connection — Direct`
- `Brace/beam connection — Tee connector`
- `Brace/beam connection — Single clip angle`
- `Brace/beam connection — Symmetric paired clip angles`
- `Brace/beam node — Multi-member Tee connector`

Engineering enum/route identities remain exact.

## 33. Visualization acceptance

Every profile shall show:

- connected member;
- both clip angles;
- common bolts;
- both anchor groups;
- concrete wall.

Spot-check:

- Solid;
- X-ray;
- Front;
- Top;
- Side 1;
- Side 2;
- Fit/Reset.

No hidden mirrored component.

No floating anchor group without angle owner.

## 34. Controlled successor default

Stage 3.5A-R1 default:

Connected member:

- `WIDE_FLANGE_I`;
- original W/I dimensions.

Angles/wall/gap/reaction:

- unchanged from Stage 3.5A.

Wall anchor groups:

- `1 × 1` each;
- centroids `±3 in`;
- one anchor at each centroid.

Expected default branch and combined wrenches remain:

- positive `F=(0,-2,0)`, `M=(8,0,6)`;
- negative `F=(0,-2,0)`, `M=(8,0,-6)`;
- combined `F=(0,-4,0)`, `M=(16,0,0)`.

Internal per-anchor distribution:

`EXTERNAL_DESIGN_REQUIRED`.

## 35. Required controlled golden cases

At minimum:

G1. Historical `3.5A-RC1` exact backward compatibility.
G2. Brace/beam selector heading/label presentation does not alter engineering identities.
G3. R1 default wall groups are 1×1 and contain exactly one anchor each.
G4. R1 default branch wrenches unchanged.
G5. R1 combined wall wrench unchanged.
G6. 1×1 internal anchor-force distribution is external-design-required.
G7. Increasing to 2×1 creates exact mirrored groups and allows nominal trace only if equilibrium is applicable.
G8. Increasing to 2×2 reproduces historical group geometry/demand under successor contract.
G9. Flat Plate connected profile.
G10. Angle connected profile.
G11. Channel connected profile.
G12. W/I connected profile.
G13. RHS connected full-through profile.
G14. SRS connected full-depth profile.
G15. Six-profile scene contains connected member and both clip angles.
G16. Positive/negative angle owner identities distinct.
G17. Anchor groups bind to correct clip-angle owners.
G18. No generic Flat Plate fallback.
G19. Profile switch preserves wall/angle/anchor state.
G20. Gap works for all six profiles.
G21. Material-axis matrix; concrete has no FRP axes.
G22. RHS cavity has no axes/material.
G23. External handoff updates anchor coordinates/pattern without capacity.
G24. Historical 2×2 handoff reproducible.
G25. Shear-only/moment rejection unchanged.
G26. Preview zero resistance.
G27. Exact U.S./SI representative RHS and W/I cases.
G28. Supported failure precedence / external limitations.
G29. Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee regressions exact.
G30. Scene regression prevents missing member/second angle/floating anchor group.

## 36. Acceptance boundary

Stage 3.5A-R1 is accepted only if:

- Brace/beam presentation labels are normalized;
- all six connected profiles work;
- default is one wall anchor per clip angle;
- user can increase anchor pattern;
- default 1×1 does not fabricate a moment-equilibrating anchor-force solution;
- connected member and both clip angles always render;
- both wall-anchor groups are correctly owned;
- shear-only input remains strict;
- external anchor handoff remains complete;
- no concrete/anchor capacity is issued;
- historical `3.5A-RC1` is exact;
- all frozen family fingerprints remain exact;
- local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
