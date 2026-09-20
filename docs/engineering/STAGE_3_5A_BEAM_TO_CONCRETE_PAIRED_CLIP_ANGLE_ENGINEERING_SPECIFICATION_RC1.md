# FRP Master Connection — Stage 3.5A Beam-to-Concrete Wall Using Symmetric Paired FRP Clip Angles — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.5A adds one new Shear Connections product:

**FRP W/I Beam -> Symmetric Paired FRP Clip Angles -> Concrete Wall**

The concrete wall and anchor system are represented for geometry, load transfer, and external-design handoff only.

FRP Master Connection does not design the concrete or anchors.

No new demand or resistance equation is introduced.

## 2. Source hierarchy

1. ASCE/SEI 74-23 and effective errata.
2. Accepted Stage 2 demand/resistance authorities.
3. Frozen Stage 3.3 Symmetric Paired Clip-Angle family.
4. Frozen Stage 3.4 shared successor-safe governance and visualization platform.
5. This Stage 3.5A specification.
6. Companion golden benchmarks.

Relevant source interpretation:

- Chapter 8 covers bearing-type bolted connections and simple frame connections using single or paired clip angles.
- Simple framing connections are proportioned for reaction shear, not moment-resisting behavior.
- FRP clip-angle connecting components require Section 2.3.2 qualification.
- Anchor-system design is outside this Stage 3.5A calculation authority.
- Erratum 1 does not modify the relevant Chapter 8 provisions.

## 3. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `2303ec713d6d038b935e076b909c3b639ced0e09`;
- subject:
  `chore: freeze Stage 3.4 multi-member tee family baseline`;
- commit count: `80`;
- worktree/index: clean.

Expected immutable freeze targets:

- Stage 2.3:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- Stage 3.4:
  `2303ec713d6d038b935e076b909c3b639ced0e09`.

Expected accepted Stage 3.4 freeze-commit hosted CI:

- run #75;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

## 4. Product identity

Normal connection selector label:

`Beam connection — Paired clip angles to concrete wall`

Suggested route identities:

- `/api/v1/calculations/beam-concrete-paired-angle/preview`;
- `/api/v1/calculations/beam-concrete-paired-angle/design-check`.

Current contract:

`3.5A-RC1`

This is a new connection type.

It shall not replace or alter the frozen `Symmetric paired clip angles -> W support` product.

## 5. Physical topology

The connection contains:

- one horizontal FRP W/I beam;
- one positive FRP clip angle;
- one negative FRP clip angle;
- one common beam-web through-bolt group;
- one positive wall-anchor group;
- one negative wall-anchor group;
- one finite concrete wall.

Physical chain:

`Positive Clip Connected Leg -> Beam Web -> Negative Clip Connected Leg`

and:

`Positive Clip Wall Leg -> Positive Anchor Group -> Concrete Wall`

`Negative Clip Wall Leg -> Negative Anchor Group -> Concrete Wall`

The wall-anchor groups are physically separate mirrored groups.

## 6. Concrete-wall local frame

Define one right-handed wall frame:

- `H_W`: horizontal along the wall face;
- `V_W`: vertical upward along the wall face;
- `N_W`: wall outward normal from concrete toward the beam/connection.

Require:

`H_W × V_W = N_W`

The concrete wall face is at:

`N_W = 0`

The beam extends in the `+N_W` direction.

The beam web lies in the `N_W-V_W` plane and is centered at `H_W = 0`.

The positive clip angle is on the `+H_W` side of the beam web.

The negative clip angle is on the `-H_W` side.

## 7. Concrete wall geometry

One finite rectangular concrete prism.

Inputs:

- wall width along `H_W`;
- wall height along `V_W`;
- wall thickness along `-N_W`;
- connection origin horizontal position;
- connection origin vertical position.

Controlled default:

- width: `48 in`;
- height: `48 in`;
- thickness: `8 in`;
- connection origin centered on the wall face.

The wall is visualized as concrete, not as FRP.

No LW/CW/TT material axes are assigned to concrete.

The wall frame may be displayed separately.

## 8. Concrete geometry validation

Stage 3.5A validates coordination geometry only:

- every anchor axis intersects the selected wall face;
- every anchor center lies inside the finite wall face;
- specified anchor embedment is positive;
- specified embedment does not exceed wall thickness;
- anchor shanks remain within the wall volume for the specified coordination geometry;
- anchor groups do not overlap invalidly;
- clip-angle wall legs do not penetrate the wall.

This is not concrete edge-distance or embedment capacity design.

Computed geometric distances to wall edges are output for external design.

## 9. Connected beam

Initial and only RC1 beam profile:

`WIDE_FLANGE_I`

Controlled default:

- depth: `10 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- member/view length: `16 in`;
- beam roll: `0°`;
- beam inclination: fixed horizontal/normal to wall.

The beam longitudinal axis is:

`L_B = +N_W`

The selected beam connection surfaces are the two opposite web broad faces.

No Flat Plate, Angle, Channel, RHS, SRS, or second beam profile in RC1.

## 10. Beam end and wall clearance

Input:

`beam_end_gap`

Default:

`0.5 in`

The gap is the physical distance between the beam end and the concrete wall face.

Requirements:

- finite;
- nonnegative;
- no beam/wall positive-volume interference;
- clip-angle geometry remains physically connected to both beam web and wall.

Stage 3.5A does not claim a complete rotational-capacity design from this gap.

Required limitation:

`SIMPLE_CONNECTION_ROTATIONAL_CAPACITY = NOT_EVALUATED`

## 11. Symmetric paired FRP clip angles

Reuse the frozen Stage 3.3 paired clip-angle topology.

Controlled default:

- connected-leg width: `4 in`;
- wall-leg width: `4 in`;
- angle thickness: `0.5 in`;
- angle length: `8 in`;
- pair longitudinal position: `0 in`;
- length anchor: `CENTER`.

The two angles are:

- identical;
- exact mirrors about `H_W = 0`;
- made from the accepted controlled FRP material source;
- independently represented as positive and negative physical components.

No unequal pair geometry in RC1.

## 12. Common beam-web group

One common physical through-bolt group crosses:

`Positive Clip Connected Leg -> Beam Web -> Negative Clip Connected Leg`

The group is edited once.

Controlled default:

- rows: `2`;
- bolts per row: `2`;
- pitch: `2 in`;
- gauge: `2 in`;
- bolt nominal diameter: `0.5 in`;
- hole diameter: `0.563 in`.

Reuse the accepted 316SS ASTM F593 bearing-type fastener system.

One physical shank/head/nut per common bolt axis.

No duplicate coincident beam-side bolts.

## 13. Common group frame

Use the accepted paired-angle semantic frame mapped to the wall frame.

For RC1:

- rows/pitch are along `V_W`;
- bolts per row/gauge are along `N_W` or the accepted paired-angle projection axis as physically mapped;
- bolt axes cross the beam web along `H_W`.

The exact existing paired-angle mapping remains authoritative.

Do not reconstruct the group in the frontend.

## 14. Wall-anchor groups

There are two physical wall-anchor groups:

- `POSITIVE_WALL_ANCHOR_GROUP`;
- `NEGATIVE_WALL_ANCHOR_GROUP`.

They are:

- identical;
- mirrored about `H_W = 0`;
- edited through one shared pattern;
- positioned from backend connector/wall geometry;
- independently identified in results and handoff.

Controlled default for each group:

- rows: `2`;
- anchors per row: `2`;
- pitch: `2 in`;
- gauge: `2 in`;
- group centroid vertical position: `V_W = 0`;
- mirrored group centroid horizontal positions:
  - positive `H_W = +3 in`;
  - negative `H_W = -3 in`.

No unequal wall-anchor groups in RC1.

## 15. External anchor geometry inputs

Shared anchor-system coordination inputs:

- nominal anchor diameter;
- clip-angle hole diameter;
- specified embedment depth;
- washer outside diameter/thickness for visualization where current shared hardware supports it;
- external anchor system description/classification as a controlled enum or nonengineering identifier where repository convention allows.

Controlled default:

- nominal diameter: `0.5 in`;
- hole diameter: `0.563 in`;
- embedment depth: `4 in`.

The embedment is a user-specified coordination input.

It is not calculated or certified.

## 16. Wall-anchor physical presentation

Each anchor is rendered as:

- exterior nut/washer at the clip-angle wall leg;
- one shank entering the concrete along `-N_W`;
- specified embedment length;
- no fictitious far-side wall hardware;
- no internally generated concrete cone/capacity geometry.

The presentation shall be labeled/schematized as an externally designed anchor.

Do not reuse through-bolt hardware that implies a far-side nut.

## 17. Wall-anchor group layout geometry

Rows/pitch use `V_W`.

Anchors per row/gauge use `H_W` within the finite clip-angle wall leg.

Validate complete hole containment in the FRP wall leg.

Validate anchor-center containment on the finite concrete wall face.

Report:

- FRP wall-leg clearances;
- wall-face geometric edge distances;
- group centroids;
- anchor coordinates.

Do not convert wall edge distances into concrete capacity.

## 18. Shear-only action contract

The only user-applied engineering action in RC1 is one signed factored vertical reaction shear:

`V_R`

The beam action applied to the connection is:

`F_B = (0, V_R, 0)` in `(H_W, V_W, N_W)`

with:

- `F_H = 0`;
- `F_N = 0`;
- user-applied `M_H = M_V = M_N = 0`.

Controlled default:

`V_R = -4 kip`

The negative sign denotes downward action along `-V_W`.

The user does not enter moments in RC1.

Any nonzero disallowed action component in an API request is rejected.

## 19. Beam action reference

The beam reaction reference point is the common beam-web group centroid.

Controlled default:

`r_B = (0, 0, 4) in`

in wall-frame coordinates.

The `N_W = 4 in` default is derived/controlled by the accepted connector geometry for the benchmark.

The frontend does not author this reference independently.

## 20. No moment connection

Stage 3.5A is not a moment-resisting connection.

No user-applied moment is accepted.

No connection rotational stiffness or moment capacity is calculated.

No automatic prying or bolt-axis tension capacity is generated.

However, exact moments created by translating a shear force between physical reference points are retained in the wall/anchor handoff.

These transfer moments do not reclassify the connection as moment-resisting.

## 21. Pair symmetry and branch split

Reuse the exact Stage 3.3B pair/action symmetry proof.

RC1 eligibility requires:

- identical mirrored angles;
- centered beam;
- identical mirrored anchor groups;
- symmetric material/source identities;
- pure vertical reaction shear;
- centered beam action reference.

When eligible:

`F_+ = 0.5 F_B`

`F_- = 0.5 F_B`

and each branch retains its exact source identity.

No tolerance-based inference.

If symmetry proof fails, branch allocation is `NOT_EVALUATED`; the combined wall handoff remains available only if it can be derived without inventing allocation. Because RC1 locks symmetry, asymmetric inputs are rejected.

## 22. Common beam-group demand

Call the accepted Stage 2.5A demand engine exactly once for the common beam-web group using the total beam reaction.

For the controlled default:

- total reaction magnitude: `4 kip`;
- common physical bolts: `4`;
- concentric common-group demand: `1 kip per bolt`.

Retain accepted common-group layer allocation/provenance:

- positive clip-angle layer;
- beam web layer;
- negative clip-angle layer.

No new demand equation.

## 23. Positive wall-group wrench

Let positive wall-anchor centroid be:

`r_+ = (+3, 0, 0) in`

Controlled positive branch:

`F_+ = (0, -2, 0) kip`

At `r_+`, exact translated moment is:

`M_+ = (8, 0, 6) kip-in`

using:

`M_+ = (r_B - r_+) × F_+`

for the zero free-moment default.

## 24. Negative wall-group wrench

Let negative wall-anchor centroid be:

`r_- = (-3, 0, 0) in`

Controlled negative branch:

`F_- = (0, -2, 0) kip`

At `r_-`:

`M_- = (8, 0, -6) kip-in`

The opposite `M_N` terms are required and preserve branch provenance.

## 25. Combined wall-interface wrench

Controlled common wall reference:

`r_W = (0, 0, 0) in`

The exact combined wall-interface wrench is obtained by shifting both branch wrenches to `r_W` and summing.

Expected default:

`F_W = (0, -4, 0) kip`

`M_W = (16, 0, 0) kip-in`

The opposite torsional branch contributions cancel.

The `16 kip-in` wall moment is an eccentricity-induced transfer moment from the shear line offset, not a user-applied connection moment.

## 26. Wall-group nominal demand trace

The application may call Stage 2.5A once for each wall-anchor group using its exact branch wrench and anchor coordinates to provide:

- nominal rigid-group anchor-point demand trace;
- FRP wall-leg local demand handoff where existing methods apply;
- force/moment equilibrium proof.

This nominal demand is not an anchor-system design result.

It shall be labeled:

`COORDINATION / FRP-SIDE DEMAND — EXTERNAL ANCHOR SOFTWARE GOVERNS`

No anchor steel or concrete capacity is calculated.

If an action component is outside accepted FRP-side methods, it remains explicit and fail-closed.

## 27. External anchor-design handoff

The backend shall return one immutable structured handoff object.

At minimum:

### Identity

- schema/version;
- load case ID;
- factored/unfactored status;
- unit system;
- connection/application fingerprint.

### Wall

- wall-frame origin;
- `H_W`, `V_W`, `N_W`;
- wall width/height/thickness;
- connection origin;
- common wall reference point.

### Combined action

- combined wall force;
- combined wall moment;
- sign convention.

### Positive group

- stable group ID;
- centroid;
- group force;
- group moment;
- anchor coordinates;
- nominal diameter;
- hole diameter;
- specified embedment;
- FRP wall-leg thickness;
- geometric wall-edge distances.

### Negative group

Same fields.

### Limitations

Explicit external-design-required statuses.

Do not omit moments from the handoff merely because the input is shear-only.

## 28. Anchor handoff export

Frontend shall provide a controlled copy/download action for the backend-authored handoff JSON.

The export:

- contains no camera/presentation state;
- preserves full precision;
- includes units/sign convention;
- is deterministic;
- does not calculate or modify engineering data in the frontend.

## 29. Concrete/anchor design limitations

Required:

- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

These limitations shall state that specialized anchor software must independently verify anchor forces and all anchor/concrete limit states.

No ordinary whole-connection PASS.

## 30. Existing paired-angle limitations

Preserve:

- `PAIRED_CLIP_ANGLE_BODY_RESISTANCE = NOT_EVALUATED`;
- `COMMON_THROUGH_BOLT_DOUBLE_SHEAR_RESISTANCE = NOT_EVALUATED`;
- `PAIRED_CLIP_ANGLE_BRANCH_COMPATIBILITY = NOT_EVALUATED`;
- `PAIRED_FRP_CLIP_ANGLE_QUALIFICATION = NOT_EVALUATED`;
- accepted prying/normal-action limitations.

Known supported beam-side numerical failure retains overall `FAIL` precedence.

Otherwise overall status remains `NOT_EVALUATED` / external design required.

## 31. Beam end trim / gap

Reuse the accepted connected-member end geometry/trim architecture where applicable.

The beam end shall remain clear of the wall by the specified gap.

Changing gap:

- updates beam end geometry;
- updates physical reference offset and wall handoff moment where applicable;
- does not silently move bolt or anchor groups;
- recomputes interference;
- does not claim rotational capacity.

## 32. Preview path

Preview shall:

- validate strict inputs;
- construct beam/angles/wall;
- resolve common beam group;
- resolve mirrored anchor groups;
- validate wall-leg and wall-face geometry;
- compute common-group demand;
- prove symmetry/branch split;
- compute exact branch wrenches;
- compute exact combined wall wrench;
- optionally compute nominal wall-group demand trace;
- create external anchor handoff;
- return visualization/status/limitations.

Preview executes zero resistance equations.

## 33. Explicit design path

`Run Design Check` shall:

- consume current accepted preview;
- execute existing supported beam-side/FRP-side resistance checks where applicable;
- preserve exact demand identities;
- retain all external anchor/concrete and paired-body limitations.

No anchor/concrete resistance engine is called.

No external result is fabricated.

## 34. API strictness

Suggested strict request fields:

- `contract_version = 3.5A-RC1`;
- unit system;
- W/I beam dimensions;
- beam end gap;
- paired-angle dimensions/position;
- common beam group;
- mirrored wall-anchor pattern;
- wall dimensions/origin;
- external anchor coordination geometry;
- reaction shear;
- material/fastener sources.

Reject:

- non-W/I beam profile;
- unequal clip angles;
- unequal anchor groups;
- nonvertical/nonzero disallowed force components;
- any user-applied moment;
- invalid embedment;
- invalid wall dimensions;
- extra fields;
- client-authored IDs/fingerprints;
- unsupported versions.

## 35. Frontend workspace

Add under Shear Connections:

`Beam connection — Paired clip angles to concrete wall`

Normal sections:

1. General / Case;
2. Connected Beam;
3. Concrete Wall;
4. Paired Clip-Angle Connector;
5. Beam Web ↔ Paired Clip Angles;
6. Mirrored Wall Anchor Groups;
7. External Anchor Geometry;
8. Loads;
9. Wall / Anchor Design Handoff;
10. Materials / Fasteners;
11. Geometry / Design Results;
12. Advanced / Diagnostics.

Use the persistent shared viewer.

## 36. Load UI

Normal input:

`Reaction shear`

Show sign and wall vertical direction.

Do not expose user moment fields in RC1.

The result/trace shall separately show:

- beam reaction;
- positive branch;
- negative branch;
- combined wall wrench;
- eccentricity-induced wall moment.

Label the generated wall moment clearly so it is not mistaken for a moment-resisting connection input.

## 37. Visualization

Render:

- finite concrete wall;
- horizontal W/I beam;
- positive and negative FRP clip angles;
- common beam through-bolts;
- positive/negative wall anchors;
- anchor embedment shanks;
- wall frame;
- action/reference overlays;
- material axes on beam and both clip angles.

Do not assign FRP material axes to concrete.

Do not render far-side nuts inside/behind the wall for blind embedded anchors.

## 38. Selection / inspection

Selection shall distinguish:

- beam;
- positive angle;
- negative angle;
- wall;
- common beam group;
- positive anchor group;
- negative anchor group;
- individual anchors;
- handoff reference points.

Inspectors shall expose:

- frames;
- surfaces;
- path layers;
- action contributions;
- anchor coordinates;
- wall edge distances;
- handoff fingerprint.

## 39. Controlled default fixture

### Wall

- width: `48 in`;
- height: `48 in`;
- thickness: `8 in`;
- origin centered.

### Beam

- W/I depth: `10 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- view length: `16 in`;
- beam end gap: `0.5 in`.

### Paired angles

- connected-leg width: `4 in`;
- wall-leg width: `4 in`;
- thickness: `0.5 in`;
- length: `8 in`;
- centered.

### Common beam group

- `2 × 2`;
- pitch/gauge: `2 in`;
- bolt: `0.5 in`;
- hole: `0.563 in`.

### Each wall-anchor group

- `2 × 2`;
- pitch/gauge: `2 in`;
- centroid `H_W = ±3 in`;
- centroid `V_W = 0`.

### External anchor geometry

- nominal diameter: `0.5 in`;
- hole: `0.563 in`;
- embedment: `4 in`.

### Action

- reaction shear: `-4 kip`;
- beam reference: `(0,0,4) in`;
- wall reference: `(0,0,0) in`.

## 40. Controlled default expected results

### Pair split

- positive branch force: `(0,-2,0) kip`;
- negative branch force: `(0,-2,0) kip`.

### Common beam group

- four physical bolts;
- `1 kip` total demand per common bolt for the concentric default.

### Positive wall group at its centroid

- force: `(0,-2,0) kip`;
- moment: `(8,0,6) kip-in`.

### Negative wall group at its centroid

- force: `(0,-2,0) kip`;
- moment: `(8,0,-6) kip-in`.

### Combined wall interface at wall origin

- force: `(0,-4,0) kip`;
- moment: `(16,0,0) kip-in`.

Force and moment equilibrium shall be exact.

## 41. U.S./SI equivalence

At minimum:

- `48 in = 1219.2 mm`;
- `16 in = 406.4 mm`;
- `10 in = 254 mm`;
- `8 in = 203.2 mm`;
- `4 in = 101.6 mm`;
- `3 in = 76.2 mm`;
- `2 in = 50.8 mm`;
- `0.5 in = 12.7 mm`;
- `0.563 in = 14.3002 mm`;
- `4 kip = 17.792886461042 kN`;
- `16 kip-in = 1.807757264441867 kN-m`.

Equivalent physical requests shall produce identical geometry, branch split, wall handoff, demands, and engineering fingerprints.

## 42. Fingerprints

Create deterministic identities for:

- complete input;
- wall geometry/frame;
- beam geometry;
- paired connector geometry;
- common beam group;
- positive anchor group;
- negative anchor group;
- external anchor geometry;
- beam action;
- branch split;
- combined wall handoff;
- preview/design result;
- application integration.

Include contract/method/source versions.

Exclude camera, display mode, and presentation units.

Equivalent U.S./SI requests match.

Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee fingerprints remain exact.

## 43. Required controlled golden cases

At minimum:

G1. Default 4 kip reaction: common group `1 kip/bolt`.
G2. Exact half branch split.
G3. Positive group wrench `(0,-2,0); (8,0,6)`.
G4. Negative group wrench `(0,-2,0); (8,0,-6)`.
G5. Combined wall wrench `(0,-4,0); (16,0,0)`.
G6. Zero user-applied moment with nonzero eccentricity-induced wall moment.
G7. Nonzero user-applied moment rejected.
G8. Nonvertical/nonzero disallowed force component rejected.
G9. Symmetry proof and mirrored geometry.
G10. Unequal anchor-group input rejected.
G11. Common group `2 × 1`; exact demand and branch invariance.
G12. Wall group rigid-demand equilibrium trace.
G13. Anchor centers outside finite wall invalid.
G14. Specified embedment greater than wall thickness invalid.
G15. Beam/wall interference or negative gap invalid.
G16. Wall-leg hole containment invalid.
G17. Concrete/anchor capacities never issued.
G18. Anchor handoff complete/deterministic.
G19. Supported beam-side failure governs `FAIL`.
G20. Valid supported checks plus external limitations -> `NOT_EVALUATED`.
G21. Preview zero resistance calls.
G22. Exact U.S./SI equivalence.
G23. Material axes on beam/angles; wall frame only.
G24. Frozen Stage 3.3 paired-angle and Stage 3.4 regressions exact.

## 44. Deliberate exclusions

Not authorized in Stage 3.5A:

- concrete capacity;
- anchor capacity;
- anchor product selection;
- adhesive-anchor design;
- cast-in-place anchor design;
- concrete reinforcement design;
- anchor seismic qualification;
- beam axial force;
- horizontal wall shear input;
- out-of-plane force input;
- user-applied moment;
- moment-resisting connection;
- single clip angle;
- unequal paired angles;
- unequal wall-anchor groups;
- Channel/Angle/Flat Plate/RHS/SRS beam;
- floor slab;
- wall return/corner geometry;
- through-wall bolts;
- base connection;
- persistence/import of external anchor-software results.

## 45. Acceptance boundary

Stage 3.5A is accepted only if:

- the physical beam/paired-angle/wall topology is correct;
- shear-only input is strict;
- unavoidable eccentricity moments are retained in the handoff;
- exact pair sharing and equilibrium pass;
- beam-side supported checks reuse accepted methods;
- no anchor/concrete capacity is issued;
- anchor handoff is complete and deterministic;
- concrete/anchor limitations remain explicit;
- no frozen family fingerprints change;
- full local/object-isolated QA passes;
- hosted four-job CI passes;
- user visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
