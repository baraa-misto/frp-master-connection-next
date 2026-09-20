# FRP Master Connection — Stage 3.3B Symmetric Paired FRP Clip-Angle Vertical Slice — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.3B establishes the first reusable **symmetric paired / double FRP clip-angle** connection family.

The controlled topology is:

```text
Positive-side FRP clip angle
             ↘
Connected member common through-bolt group
             ↗
Negative-side FRP clip angle

Each clip angle
→ its own mirrored support-leg bolt group
→ the same selected W-support flange
```

The stage is deliberately restricted to a geometry-and-stiffness-symmetric pair. It does not authorize arbitrary asymmetric load sharing.

The paired system reuses the accepted Stage 3.3A single-angle implementation and the frozen Stage 3.2 shared platform. It introduces a controlled symmetric pair-action split and one common three-layer connected-member bolt stack, but no new resistance equation.

---

## 2. Source basis and engineering interpretation

The governing design basis is ASCE/SEI 74-23 with Erratum 1.

Relevant source locators:

- Section 8.1 permits simple frame connections using a single clip angle or a pair of clip angles.
- Section 8.3.4 requires simple framing connections to be proportioned for reaction shear unless otherwise qualified.
- Commentary C8.3.4.1 states that when two clip-angle web shear planes are present, the simple-frame shear force is assumed equally distributed between them.
- Erratum 1 contains no Chapter 8 correction affecting this Stage 3.3B interpretation.

Stage 3.3B applies equal sharing only to the controlled **pure reaction-shear component parallel to `L_P`** after exact pair-symmetry, action, and reference-point eligibility are proven. It does not generalize equal sharing to unequal angles, unequal support groups, asymmetric materials, transverse force components, moments, off-plane loading, or off-symmetry reference points.

No copyrighted standard text is reproduced in repository engineering documents beyond concise source locators and independently expressed engineering interpretation.

---

## 3. Accepted starting baseline

Expected repository state:

- branch: `main`
- `HEAD == origin/main`:
  `f4ae7d308644024ed31bcf0114b550426f4e45ef`
- subject:
  `fix: render clip-angle member end trim`
- commit count: `67`
- worktree/index: clean
- accepted Stage 3.3A baseline:
  `f4ae7d308644024ed31bcf0114b550426f4e45ef`
- backend source tree:
  `e11b3bd90af079afce6cb4e26ed1424d274a75b8`
- frontend source tree:
  `c6056618e25c6ff0c6205cdcf6503f3d85a633b9`

Immutable freeze tags remain:

```text
stage-2.3-interface-geometry-freeze
→ 5bc545ab8251f9bd49dedc776962937ed5e822a2

stage-3.2-tee-connection-freeze
→ d16b354732c90bf3bf7847c62be652c230a9f91e
```

Package identities remain:

```text
package blob:
b753abd55004168eee5844879f0596d435fe4b5a

lock blob:
ae1831268db42005517343bf555f054a673ae520

lock SHA-256:
20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254
```

Stage 3.3A hosted CI and post-CI visual acceptance are accepted.

---

## 4. Mandatory prior-error prevention rules

Stage 3.3B shall not repeat the Stage 3.2/3.3A defects already found and corrected.

Before mutation and in automated regression, prove all of the following:

1. Selected connected profile family, backend geometry, preview payload, and rendered scene agree.
2. Clip-angle connected legs are placed exterior to the selected member faces, not centered through member material.
3. Trim On invokes the shared trim kernel on the complete current profile solids and publishes trimmed meshes without ghost untrimmed primitives.
4. Trim Off restores authoritative untrimmed geometry.
5. Connector-body or method `NOT_EVALUATED` states do not become geometry-invalid reasons.
6. True interference, invalid hole containment, invalid paths, and invalid trim remain fail-closed.
7. Material axes are backend-authored, region-specific, and rendered on their actual physical regions.
8. Connector length/position changes do not auto-move bolt groups.
9. Current/last-valid preview revision identity remains exact; stale responses cannot overwrite newer pair/profile/trim edits.
10. Shared changes preserve Direct, frozen Tee, and accepted single-angle behavior and fingerprints.

A five-profile single-angle regression matrix and the full Stage 3.3A trim/status matrices remain mandatory even though Stage 3.3B has a narrower connected-profile scope.

---

# PART A — CONTROLLED SCOPE

## 5. Included scope

Stage 3.3B includes:

- one positive-side and one negative-side pultruded-FRP clip angle;
- identical angle geometry, material, length anchor, and longitudinal position;
- exact mirror placement about the connected-member mid-surface;
- one common connected-member through-bolt group crossing both angle legs and the connected member;
- one positive-side support-leg bolt group;
- one negative-side support-leg bolt group;
- support groups identical and exact mirrors;
- connected role: Brace or Beam;
- connected physical regions:
  - Flat Plate;
  - W/I Web;
  - Channel Web, only where the finite clear-web region and assembly access are valid;
- W Column Flange and W Beam Flange support roles;
- positive/negative selected support flange;
- arbitrary accepted member inclination and profile roll;
- exact finite geometry, interference, and hole containment;
- shared member-end trimming;
- exact U.S./SI equivalence;
- 316SS F593 initial fastener authority;
- controlled symmetric equal-sharing eligibility;
- layer-specific demand allocation for the common three-layer stack;
- backend-authoritative visualization, hardware, and trace.

---

## 6. Explicitly outside Stage 3.3B

Stage 3.3B does not include:

- unequal left/right clip-angle geometry;
- independent left/right support-bolt patterns;
- different left/right materials or fasteners;
- asymmetric pair placement;
- arbitrary 50/50 load sharing;
- Angle-leg connected members;
- RHS connected members requiring an internal angle;
- round-hollow connected members;
- W-support web connections;
- beam-to-beam web support;
- blind fasteners;
- separate one-sided connected-member bolt groups;
- common-bolt metallic double-shear resistance;
- clip-angle body resistance;
- prying generation;
- pair torsion/warping interaction;
- unequal-stiffness distribution;
- moment-connection mechanics;
- new material properties or resistance equations.

These require later controlled stages.

---

# PART B — PAIRED TOPOLOGY AND GEOMETRY

## 7. Pair topology

Create one backend-authoritative assembly:

```text
SYMMETRIC_PAIRED_CLIP_ANGLES
```

Physical components:

```text
POSITIVE_CLIP_ANGLE
NEGATIVE_CLIP_ANGLE
CONNECTED_MEMBER
W_SUPPORT
```

Physical interfaces / groups:

```text
Interface M:
Positive Connected Leg ↔ Connected Member ↔ Negative Connected Leg
(common through-bolt group; three-layer stack)

Interface S+:
Positive Support Leg ↔ Support

Interface S−:
Negative Support Leg ↔ Support
```

There are three physical bolt groups, not four.

The connected-member group is one common through-bolt pattern. The two support groups are identical mirrored copies in RC1.

---

## 8. Pair semantic frame

Define a right-handed pair frame:

- `S_P` — pair transverse direction, normal to the connected-member plate/web mid-surface;
- `P_P` — projection direction from support toward the connected member;
- `L_P` — connector length / pultrusion direction.

Require:

```text
S_P × P_P = L_P
```

Controlled semantic frame:

```text
S_P = (1,0,0)
P_P = (0,1,0)
L_P = (0,0,1)
```

The pair symmetry plane is:

```text
S_P = 0
```

The connected member mid-surface is coincident with that plane in the controlled fixture.

---

## 9. Symmetric pair geometry

Let:

- connected-member thickness = `t_m > 0`;
- clip-angle thickness = `t_a > 0`;
- connected-leg width = `w_c > t_a`;
- support-leg width = `w_s > t_a`;
- connector length = `L > 0`.

Positive-side connected-leg contact face:

```text
S_P = +t_m/2
```

Positive angle material occupies the exterior side:

```text
S_P ≥ +t_m/2
```

Negative-side connected-leg contact face:

```text
S_P = -t_m/2
```

Negative angle material occupies:

```text
S_P ≤ -t_m/2
```

The two angles are exact mirrors through `S_P = 0`.

The member occupies the interior slab between its two broad faces.

Only zero-volume face contact is intended. Positive-volume member/angle overlap is invalid.

---

## 10. Support-leg geometry

Both support-leg exterior contact faces are coincident with the same selected W-support flange plane.

The positive support leg extends toward `+S_P`.

The negative support leg extends toward `-S_P`.

The angle heels align with the connected-member broad faces and share the same support-plane datum.

The pair remains two separate physical angles; no fictitious connector plate is introduced between them.

---

## 11. Pair symmetry lock

Stage 3.3B RC1 uses a locked symmetric pair.

The user edits one connector definition:

- connected-leg width;
- support-leg width;
- thickness;
- connector length;
- length anchor;
- longitudinal position;
- material/source;
- fastener system;
- common member-side pattern;
- one support-side pattern mirrored to both angles.

The backend creates the positive and negative angle instances by exact mirror transformation.

The API shall reject client-authored unequal left/right geometry or unequal support patterns.

---

## 12. Connected profile qualification

### Flat Plate

Both broad faces are exterior, parallel, finite, and available for the paired legs.

### W/I Web

The positive and negative web broad faces form the paired contact surfaces.

Both angle connected legs must remain inside the finite clear-web region between flange/junction exclusions.

### Channel Web

The two web broad faces may be used only when:

- the internal channel side has sufficient finite geometry;
- angle/support-leg geometry does not collide with flanges/heel regions;
- installation access is explicitly qualified.

If these conditions are not met, geometry is invalid or qualification is required.

### Excluded

Angle and RHS connected profiles are not part of RC1 paired-angle scope.

The UI shall not silently expose unsupported profile options for this connection type.

---

## 13. Support roles

Supported:

- W Column Flange;
- W Beam Flange.

Selected support faces:

- positive local-Z flange;
- negative local-Z flange.

Column/Beam roles reuse one W/I geometry with the existing authoritative transform.

No duplicated pair engineering logic.

---

## 14. Length anchoring and body position

Reuse the accepted connector-body length anchor:

- `CENTER`;
- `POSITIVE_L_END`;
- `NEGATIVE_L_END`.

Both angles share the same anchor mode and exact longitudinal position.

Changing pair length/anchor/body position does not auto-move any of the three bolt groups.

Finite connector-end clearances recompute independently for all groups.

---

# PART C — BOLT GROUPS AND STACKS

## 15. Common connected-member through-bolt group

The common member-side group is fixed in the paired connector frame.

Pattern semantics:

- rows/pitch along `L_P`;
- bolts per row/gauge along `P_P`;
- bolt axis along `S_P`.

Each bolt penetrates exactly:

```text
positive clip-angle connected leg
→ connected-member region
→ negative clip-angle connected leg
```

or the exact reverse order according to head/nut orientation.

The full physical stack is:

```text
outer positive-angle face
positive angle thickness
t_m connected-member thickness
negative angle thickness
outer negative-angle face
```

The common bolt head and nut lie on opposite outer angle faces.

No internal nut/washer is placed between contacting layers.

---

## 16. Mirrored support-side groups

The positive and negative support groups have identical:

- rows;
- bolts per row;
- pitch;
- gauge;
- group offsets;
- advanced edge-distance representation;
- fastener system.

Their coordinates and axes are exact mirrors through the pair symmetry plane.

They remain distinct physical groups with distinct stable bolt IDs and results.

The API rejects unequal support-group inputs in RC1.

---

## 17. Complete-hole clearances

For every angle leg and group, compute exact complete-hole clearances to:

- heel/junction boundary;
- free leg edge;
- positive connector-length end;
- negative connector-length end;
- connected-member finite face boundaries where applicable;
- support finite boundaries where applicable.

For the common stack, complete-hole containment must pass on:

- positive angle leg;
- connected-member region;
- negative angle leg.

Report exact governing bolt/boundary/deficit.

---

## 18. Bolt-path and assembly access

The backend shall prove:

- one finite through-path;
- exact layer order;
- exact thicknesses;
- no heel/junction crossing;
- no unintended flange/wall crossing;
- head/nut access on outer pair faces;
- support-bolt installation access.

Channel interior-side access is explicitly qualified.

RHS and hidden internal-angle topologies are excluded rather than silently approximated.

---

# PART D — SYMMETRIC LOAD-SHARING AUTHORITY

## 19. Pair-symmetry eligibility

Equal sharing may be used only when all conditions are true:

1. positive/negative angle geometry is identical;
2. materials and source identities are identical;
3. connector lengths/anchors/positions are mirrored;
4. common through-bolt geometry is symmetric about `S_P = 0`;
5. positive/negative support groups are identical mirrors;
6. fastener systems are identical;
7. connected-member broad faces are parallel and equidistant from the symmetry plane;
8. support contact geometry is symmetric;
9. canonical action is pair-symmetric;
10. reference point lies on the symmetry plane;
11. no remaining interference or geometry qualification invalidates one branch;
12. no stiffness modifier distinguishes the branches.

Eligibility is backend-authored and fail-closed.

---

## 20. Symmetric action conditions

Stage 3.3B RC1 authorizes equal sharing only for pure reaction shear parallel to `L_P`.

At the pair reference point in the `S_P/P_P/L_P` frame, equal sharing requires exactly:

```text
F_S = 0
F_P = 0
M_S = 0
M_P = 0
M_L = 0
reference_S = 0
```

The only nonzero controlled action component is:

```text
F_L
```

No tolerance-based automatic symmetry is used for controlled exact inputs.

If an antisymmetric component exists, return:

```text
PAIRED_CLIP_ANGLE_EQUAL_SHARING_NOT_PROVEN
```

The geometry may remain current, but design distribution is `NOT_EVALUATED`.

---

## 21. Exact branch split

When symmetry is proven, create two immutable branch actions:

```text
Positive branch force = (0,0,0.5 F_L)
Negative branch force = (0,0,0.5 F_L)
Positive branch moment = (0,0,0)
Negative branch moment = (0,0,0)
```

Each branch uses its mirrored physical reference point and existing action transformation.

The sum of the two branch wrenches about the pair datum must recover the pure-shear parent wrench exactly; offset moments from the mirrored branch reference points cancel.

No application-side redistribution beyond this controlled half split is permitted.

---

## 22. Common member-group demand

The common connected-member bolt group receives the **total pair action** and is resolved once through the existing Stage 2.5A demand engine.

For each common bolt, let total in-plane demand vector be:

```text
d_total
```

The controlled symmetric shear-plane allocation is:

```text
positive angle-leg demand = 0.5 d_total
negative angle-leg demand = 0.5 d_total
connected-member demand   = 1.0 d_total
```

This is a layer-demand allocation, not a new resistance equation.

The total bolt-shank force remains `d_total`.

---

## 23. Support-group demand

Each support group receives its corresponding half branch action and is resolved independently through Stage 2.5A.

For symmetric concentric geometry, positive and negative support-group demand vectors and magnitudes shall mirror exactly.

---

## 24. Resistance handoff

Existing Stage 2.5B/2.6A/2.4B resistance methods may be used where their accepted geometry/material contracts apply.

### Common member stack

Layer-specific demand handoff:

- positive angle connected leg: half demand;
- connected member: full demand;
- negative angle connected leg: half demand.

The handoff shall preserve exact parent demand identity and layer provenance.

### Support groups

Each side uses its half-branch demand with the existing two-layer handoff.

No direct Stage 2.4B bypass.

---

## 25. Unresolved resistance checks

Required checks remain:

```text
PAIRED_CLIP_ANGLE_BODY_RESISTANCE
COMMON_THROUGH_BOLT_DOUBLE_SHEAR_RESISTANCE
PAIRED_CLIP_ANGLE_BRANCH_COMPATIBILITY
PAIRED_FRP_CLIP_ANGLE_QUALIFICATION
```

Stage 3.3B RC1 status:

```text
NOT_EVALUATED
```

The pair body limitation includes:

- both angle-leg body actions;
- heels/fillets;
- pair torsion/warping;
- prying;
- branch compatibility beyond the controlled symmetric split.

The common metallic bolt double-shear capacity is not invented.

The paired FRP clip-angle system remains qualification/review required under the project's accepted coverage model.

Ordinary whole-connection PASS is prohibited.

A supported interface failure still governs overall FAIL.

---

## 26. Status aggregation

Precedence:

1. true geometry invalidity → invalid preview/design unavailable;
2. supported numerical interface failure → `FAIL`;
3. equal-sharing not proven → `NOT_EVALUATED`;
4. required pair body/double-shear checks unsupported → `NOT_EVALUATED`;
5. ordinary whole-connection `PASS` is prohibited in RC1.

Preview geometry validity remains separate from design completeness.

---

# PART E — TRIM, MATERIALS, AND VISUALIZATION

## 27. Paired-angle end trim

Reuse the shared Stage 3.3A/R12 trim engine.

Define:

```text
PAIRED_CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE
```

The pair support-leg/heel obstruction is symmetric and uses one connector-fixed clearance plane.

Controls:

```text
Apply end trim clearance
End clearance to paired clip-angle support legs
```

Trim the complete current connected profile solids.

Publish backend-authored trimmed meshes without untrimmed ghost primitives.

Recompute remaining interference and fabricated-edge geometry.

---

## 28. Material regions

Each clip angle has two independent material regions:

```text
positive connected leg
positive support leg
negative connected leg
negative support leg
```

LW is parallel to `L_P`.

CW/TT use the shared region-specific material-basis architecture.

The R14C renderer embeds one material-axis indicator on each physical leg.

No component-wide shared CW/TT basis across perpendicular legs.

---

## 29. Fasteners and hardware

Initial fastener authority:

```text
STAINLESS_STEEL_316
ASTM_F593_17_GROUP_2_316_316L
```

Common through-bolts:

- one shank per common bolt;
- head on one outer angle face;
- nut on the opposite outer angle face;
- washers only when source-backed.

Support groups use existing two-layer hardware presentation.

Hardware follows authoritative axes/stacks.

---

## 30. Visualization requirements

Render:

- connected member;
- W support;
- positive clip angle;
- negative clip angle;
- common member through-bolt group;
- positive support group;
- negative support group;
- full hardware;
- trim geometry;
- selected contact surfaces;
- pair symmetry plane where requested;
- actions/frames;
- region-embedded material axes.

No generic plates or duplicated/stale profile primitives.

The paired geometry must be recognizable in 3D, Front, Top, Side 1, and Side 2.

---

# PART F — API AND WORKSPACE

## 31. Public endpoints

Add strict stateless endpoints:

```text
POST /api/v1/calculations/paired-clip-angle/preview
POST /api/v1/calculations/paired-clip-angle/design-check
```

Suggested identities:

```text
integration:   3.3B-RC1
API schema:    0.1.0-draft
visualization: 0.1.0-draft
```

Reject:

- extra fields;
- invalid units/nonfinite values;
- unequal left/right geometry;
- unequal support groups;
- client-authored IDs/fingerprints;
- unsupported connected profile/surface;
- invalid common stack;
- impossible geometry.

---

## 32. Fingerprints

Create deterministic fingerprints for:

- pair input;
- pair geometry;
- common member group;
- positive support group;
- negative support group;
- symmetry proof;
- branch actions;
- layer-demand allocation;
- preview/design result;
- application integration.

Include exact physical units, materials, sources, trim, and parent engine versions.

Exclude display units, camera, overlays, selected panel, and timestamps.

Equivalent U.S./SI inputs produce identical engineering fingerprints.

Existing Direct/Tee/Single-Angle fingerprints remain exact.

---

## 33. Connection selector and naming

Add:

```text
Brace/beam connection — Symmetric paired clip angles
```

Normal title examples:

```text
FRP Flat Plate Brace → Symmetric Paired FRP Clip Angles → W Column Flange
FRP W/I Beam Web → Symmetric Paired FRP Clip Angles → W Beam Flange
```

Do not use ambiguous `two interfaces` naming.

---

## 34. Workspace controls

Reuse the unified workspace shell.

Connector section:

```text
Pair symmetry: Locked
Connected-leg width
Support-leg width
Thickness
Connector length
Length anchor
Pair longitudinal position
```

Bolt sections:

```text
Common Connected-Member Through-Bolt Group
Mirrored Support-Leg Bolt Groups
```

The support pattern is edited once and mirrored by the backend.

Show the three physical group results separately.

---

## 35. Preview/design state

Reuse R3 state separation:

- valid geometry remains current even if equal sharing or body checks are unsupported;
- true geometry invalidity alone uses red/last-valid state;
- design readiness depends on symmetry proof and supported prerequisites;
- warnings are not parsed to infer geometry validity.

Presentation-only interactions do not call APIs or stale results.

---

# PART G — CONTROLLED BENCHMARKS

## 36. Controlled default geometry

Default paired fixture:

```text
connected member: Flat Plate
member thickness: 0.5 in
member width: 6 in
member view length: 8 in
support: W Column Flange
angle connected-leg width: 4 in
angle support-leg width: 4 in
angle thickness: 0.5 in
angle length: 8 in
length anchor: CENTER
pair longitudinal position: 0 in
common bolt diameter: 0.5 in
hole diameter: 0.563 in
```

Common member group:

```text
2 rows × 2 bolts per row
pitch 2 in
gauge 2 in
```

Mirrored support groups, each:

```text
2 rows × 2 bolts per row
pitch 2 in
gauge 2 in
```

Use exact safe offsets/edge distances established in the companion golden.

---

## 37. Controlled load case

Default pair action in semantic frame:

```text
F = (0,0,4) kip
M = (0,0,0) kip-in
reference S = 0
```

Expected equal split:

```text
positive branch force = 2 kip along L_P
negative branch force = 2 kip along L_P
```

Common member group, four bolts:

```text
total per-bolt demand = 1.0 kip
positive angle layer  = 0.5 kip
connected member      = 1.0 kip
negative angle layer  = 0.5 kip
```

Each support group, four bolts:

```text
per-bolt demand = 0.5 kip
```

---

## 38. Required golden cases

Companion golden shall include at minimum:

- G1 default symmetric Flat Plate pair;
- G2 common group 2×1 and mirrored support groups 2×2;
- G3 W/I web pair geometry and three-layer stack;
- G4 Column/Beam support invariance;
- G5 exact pair mirror and support-group mirror;
- G6 equal-sharing eligibility pass;
- G7 off-plane force eligibility fail;
- G8 off-symmetry reference-point eligibility fail;
- G9 valid method-unsupported geometry remains current;
- G10 paired trim at 25° and exact 0.5 in gap;
- G11 U.S./SI equivalence;
- G12 common through-bolt hardware and layer order;
- G13 four angle-leg material regions / embedded axes;
- G14 body/double-shear limitations and FAIL precedence.

---

## 39. Required regressions

Preserve exact:

- Direct connection;
- frozen Tee family;
- accepted single clip-angle Stage 3.3A including R1-R4;
- profile binding;
- exterior-side placement;
- preview/design separation;
- trim pipeline;
- material bases/visualization;
- exact units/fingerprints;
- both freeze audits/tags.

---

## 40. Visual acceptance

After full QA and hosted 4/4 CI:

### V1 — Default pair

Verify two real mirrored angles, one common member group, and two support groups.

### V2 — Common through-bolt stack

Inspect head/shank/nut and three-layer path.

### V3 — Symmetric load sharing

Verify 4 kip total → 2 kip per branch, 1 kip per common bolt, 0.5 kip per support bolt.

### V4 — W/I web

Verify angles sit outside both web faces inside the clear-web region.

### V5 — Channel web

Verify valid accessible geometry or explicit qualification/fail-closed state.

### V6 — Column/Beam support

Verify local pair geometry invariance.

### V7 — Symmetry violation

Apply off-plane force or off-symmetry reference point; geometry remains current but equal sharing/design becomes `NOT_EVALUATED`.

### V8 — Inclination and trim

Verify complete connected profile trim and exact gap without ghost geometry.

### V9 — U.S./SI

Verify identical physical geometry, results, and fingerprints.

### V10 — Material axes

Verify four clip-angle leg indicators and correct profile indicators.

### V11 — Body/double-shear limitations

Verify supported checks remain visible while ordinary PASS is prohibited.

---

## 41. Acceptance boundary

Stage 3.3B is accepted only if:

- two exact mirrored angles form one symmetric pair;
- one common three-layer member bolt group is modeled physically;
- support groups are exact mirrors;
- equal sharing is used only after explicit symmetry/action proof;
- layer-specific demand allocation is exact and traceable;
- antisymmetric action fails closed without invalidating valid geometry;
- all previous profile/placement/trim/status errors remain corrected;
- no new resistance equation is introduced;
- pair body and common-bolt double-shear remain explicit `NOT_EVALUATED` checks;
- Direct, frozen Tee, and Stage 3.3A regressions remain exact;
- complete QA and 4/4 hosted CI pass;
- V1–V11 pass.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
