# FRP Master Connection — Stage 3.3A Single FRP Clip-Angle Connector Vertical Slice — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.3A establishes the first reusable **single clip-angle connector** family.

The initial topology is:

```text
Connected brace or beam
        ↓
Interface A
        ↓
Single pultruded-FRP clip angle
        ↓
Interface B
        ↓
Supporting W flange
```

The clip angle has two perpendicular physical legs:

- **Connected-member leg**
- **Support leg**

Each leg owns an independent bolted interface.

Stage 3.3A reuses the frozen Stage 3.2 platform foundation and the accepted Stage 2 demand/resistance engines. It does not create a new resistance equation for the clip-angle body.

---

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`
- `HEAD == origin/main`:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`
- subject:
  `chore: freeze Stage 3.2 tee connection baseline`
- commit count: `62`
- worktree/index: clean
- accepted Stage 3.2 product baseline:
  `9aa5706e89639e990a701de965b04fa448d09c26`
- frontend source tree:
  `fbbf52fa5ad719a6f3e434a19df74c236cd25dfb`
- backend source tree:
  `5b46aa0f06e1f2ba51a79141c724997a159f8de4`

Immutable freeze tags:

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

The Stage 3.2 freeze commit passed hosted Backend/Frontend Ubuntu/Windows CI.

---

## 3. Frozen foundation and shared-reuse rule

Stage 3.3A shall reuse, not duplicate, the accepted shared platform capabilities:

- connection-type dropdown;
- unified engineering sidebar / persistent viewer / results shell;
- current / pending / invalid / last-valid preview states;
- explicit `Run Design Check`;
- exact U.S./SI transport;
- backend-authoritative connected-member profile library;
- W-column / W-beam support transforms;
- independent bolt-group layouts;
- group-offset placement and advanced edge-distance placement;
- computed complete-hole clearances;
- solid fastener shank/head/nut/washer presentation;
- arbitrary connected-member inclination;
- profile roll;
- fixed connector-frame bolt grids;
- member-end fabrication trim engine;
- connector length anchoring / body position;
- region-specific FRP material bases;
- region-embedded material-axis visualization;
- frame/material/reference-point inspectors;
- deterministic fingerprints;
- Stage 2.5A / 2.5B / 2.6A / 2.6B calculation integration.

A shared cause shall have one shared implementation and regression coverage across Direct, Tee, and Clip-Angle families.

No Tee-specific copy of shared workspace, profile, fastener, material-axis, trim, anchoring, or preview-state logic is permitted.

---

## 4. Stage 3.2 freeze compatibility

The Stage 3.2 freeze tag and manifest remain immutable.

If Stage 3.3A changes shared production files used by the frozen Tee family, create a narrow freeze-change governance record that states:

- shared file/symbol changed;
- reason for reuse/generalization;
- Stage 3.2 behavior before/after;
- exact Tee regression/fingerprint evidence;
- production behavior change for Tee: `NONE`;
- freeze tag/manifest remain unchanged.

All frozen Tee numerical results, statuses, geometry, controlled fingerprints, U.S./SI equivalence, and visual behavior shall remain exact.

---

## 5. Scope

Stage 3.3A includes:

- one physical clip-angle component;
- pultruded-FRP clip-angle material family;
- unequal connected/support leg widths;
- exact thickness and connector length;
- two independently resolved physical interfaces;
- connected role: Brace and Beam;
- connected profiles:
  - Flat Plate
  - Angle
  - Channel
  - W/I
  - Rectangular Hollow Section
- support:
  - W Column Flange
  - W Beam Flange
- positive/negative selected physical support flange;
- two clip-angle hands/sides;
- arbitrary connected-member inclination and profile roll;
- independent bolt layouts/positions on both legs;
- exact finite-hole containment;
- 316SS F593 initial fastener authority;
- explicit preview/design endpoints;
- exact U.S./SI equivalence;
- member-end trim where the connected member interferes with the clip-angle support leg/heel;
- complete 3D visualization and result trace.

---

## 6. Explicitly outside Stage 3.3A

Stage 3.3A does not include:

- paired/double clip angles;
- assumed 50/50 load sharing;
- W-column web or W-beam web support;
- beam-to-beam web support;
- concrete/anchor interfaces;
- round-hollow direct flat-leg contact;
- welded connections;
- slip-critical friction;
- blind fasteners;
- clip-angle leg bending capacity;
- clip-angle heel/fillet capacity;
- clip-angle torsion;
- prying generation;
- connector-body rupture/yielding;
- moment-connection mechanics;
- new material properties or equations.

These require later controlled stages.

---

# PART A — TOPOLOGY AND GEOMETRY

## 7. Connector topology

Create one backend-authoritative connector component:

```text
SINGLE_CLIP_ANGLE
```

Physical load path:

```text
Connected member
→ Interface A
→ Clip-angle connected-member leg
→ Clip-angle heel/body
→ Clip-angle support leg
→ Interface B
→ Supporting W flange
```

Stable physical interface names:

```text
Interface A:
Connected Member ↔ Clip-Angle Connected Leg

Interface B:
Clip-Angle Support Leg ↔ Support
```

Normal UI shall use the physical names rather than generic `A/B`, while stable diagnostic IDs remain available.

---

## 8. Semantic connector frame

Define a right-handed clip-angle frame:

- `S_C` — support-leg width direction;
- `P_C` — connected-leg projection direction away from the support/heel;
- `L_C` — connector length / pultrusion direction.

Require:

```text
S_C × P_C = L_C
```

The frame is backend-authoritative and independent of camera orientation.

For the controlled right-hand semantic fixture:

```text
S_C = (1,0,0)
P_C = (0,1,0)
L_C = (0,0,1)
```

The heel line is parallel to `L_C`.

---

## 9. Nominal angle solids

Let:

- connected-leg width = `w_c > 0`;
- support-leg width = `w_s > 0`;
- thickness = `t > 0`;
- connector length = `L > 0`.

Require:

```text
t < w_c
t < w_s
```

The nominal controlled geometry uses the accepted sharp-corner Angle profile solids.

In the right-hand semantic fixture:

```text
Connected-leg solid:
0 ≤ S ≤ t
0 ≤ P ≤ w_c
negative_end ≤ L_C ≤ positive_end

Support-leg solid:
0 ≤ S ≤ w_s
0 ≤ P ≤ t
negative_end ≤ L_C ≤ positive_end
```

The heel overlap is the common `t × t` region.

Manufacturing inside/outside radii are not modeled in Stage 3.3A.

Bolt holes must remain in flat broad-face regions and may not enter the heel/junction exclusion.

---

## 10. Clip-angle hand

Add:

```text
clip_angle_hand
```

Allowed values:

- `POSITIVE_S_SIDE`
- `NEGATIVE_S_SIDE`

Normal user labels:

- `Positive side (+S)`
- `Negative side (−S)`

The negative hand is the exact mirror of the positive hand across the `P_C-L_C` plane.

The hand controls:

- which side of the connected member receives the single angle;
- connected-leg contact-face normal;
- support-leg width direction;
- bolt axes and hardware sides.

Hand changes must not change dimensions, materials, loads, or bolt-pattern values.

---

## 11. Physical connector surfaces

Stable physical surfaces shall include at minimum:

### Connected-member leg

- exterior connected-member contact face;
- opposing inner broad face;
- free-edge boundary;
- heel/junction boundary;
- positive/negative connector-length ends.

### Support leg

- exterior support contact face;
- opposing inner broad face;
- free-edge boundary;
- heel/junction boundary;
- positive/negative connector-length ends.

Surface identities, planes, normals, bounds, and geometry fingerprints are backend-authored.

---

## 12. Support placement

Interface B support-leg exterior face is coincident with the explicitly selected W-flange contact face.

Supported roles:

- `W_COLUMN_FLANGE`
- `W_BEAM_FLANGE`

Supported selected physical faces:

- positive local-Z flange;
- negative local-Z flange.

Column and beam roles reuse one W/I profile and differ only by the authoritative support transform.

No duplicated clip-angle engineering logic for Column versus Beam.

---

## 13. Connected-member placement

The connected member contacts the exterior face of the clip-angle connected leg using the existing profile/surface registry.

Supported profiles/surfaces reuse the Stage 3.2 contracts.

The connected-member role is independent from profile family:

- Brace
- Beam

The connected member may use arbitrary accepted inclination within the current planar domain and independent profile roll.

The clip angle and its bolt grids do not rotate merely because the connected member inclination changes.

---

## 14. Connector length anchoring

Reuse/generalize the accepted connector-body length-anchor contract:

- `CENTER`
- `POSITIVE_L_END`
- `NEGATIVE_L_END`

and exact selected-anchor coordinate.

Current vertical-template labels may use:

- Centered
- Keep upper end fixed
- Keep lower end fixed

The clip-angle body may move along `L_C` independently from both bolt groups.

Changing clip-angle length/anchor/body position shall not auto-move either bolt group.

Recompute finite clearances and fail closed when holes leave the connector.

Tee R13 behavior remains exact.

---

# PART B — PHYSICAL INTERFACES AND BOLT GROUPS

## 15. Interface A frame

Interface A is the connected-member leg plane.

For the controlled positive-hand fixture:

```text
in-plane width axis = P_C
in-plane length axis = L_C
bolt-axis direction = +S_C
```

The fixed bolt grid is expressed in the clip-angle connected-leg frame.

Connected-member inclination/roll changes the connected-member solids and bolt-path intersections, not the connector-leg grid.

---

## 16. Interface B frame

Interface B is the support-leg plane.

For the controlled positive-hand fixture:

```text
in-plane width axis = S_C
in-plane length axis = L_C
bolt-axis direction = -P_C
```

The support-leg grid is fixed to the clip-angle/support interface.

Changing Interface A layout does not change Interface B geometry, and vice versa.

---

## 17. Independent bolt groups

Each interface independently owns:

- rows;
- bolts per row;
- pitch;
- gauge;
- group placement mode;
- vertical/length offset;
- horizontal/leg-width offset;
- advanced edge-distance representation;
- bolt coordinates;
- stable IDs;
- holes;
- layer stacks;
- demand/result/fingerprint.

No equality requirement exists between the two groups.

Valid examples include:

```text
Interface A 2 × 1
Interface B 2 × 2
```

and:

```text
Interface A 3 × 2
Interface B 2 × 2
```

subject to physical containment and calculation applicability.

---

## 18. Pattern orientation

Normal rectangular pattern semantics:

- Rows extend along `L_C`;
- pitch is spacing along `L_C`;
- bolts per row extend across the physical leg width;
- gauge is spacing across the leg width.

The group pattern is centered about the authoritative placement datum in group-offset mode.

Row-demand ordering remains backend-resolved from the actual force/free-edge geometry.

---

## 19. Controlled default geometry

The controlled reference clip angle uses:

```text
connector length       8 in
connected-leg width    4 in
support-leg width      4 in
thickness              0.5 in
length anchor          CENTER
anchor position        0 in
hand                   POSITIVE_S_SIDE
bolt diameter          0.5 in
hole diameter          0.563 in
```

Each default interface uses:

```text
rows                   2
bolts per row           2
pitch                   2 in
gauge                   2 in
```

The flat broad-face interval across either leg is:

```text
t ≤ width coordinate ≤ 4 in
```

Its center is:

```text
2.25 in
```

The controlled 2 × 2 centers in each local interface plane are:

```text
width coordinates: 1.25 in, 3.25 in
length coordinates: -1 in, +1 in
```

With hole radius `0.2815 in`, the exact clearances are:

```text
heel-side clearance       0.4685 in
free-edge clearance       0.4685 in
positive-length clearance 2.7185 in
negative-length clearance 2.7185 in
```

---

## 20. Clip-angle leg bolt paths

### Interface A

Each path shall penetrate exactly:

1. selected connected-member physical region/layer;
2. clip-angle connected leg.

The path shall cross the selected connected-member surface and the connected-leg flat broad-face region.

### Interface B

Each path shall penetrate exactly:

1. clip-angle support leg;
2. selected support W flange.

The path shall remain in the support-leg flat broad-face region and selected W-flange patch.

Heel overlap, outside-leg regions, ambiguous opposing faces, wrong patches, and complete-hole boundary violations fail closed.

Reuse/generalize existing Angle/profile wall-path resolvers; do not create a clip-angle-only geometric shortcut.

---

## 21. Complete-hole clearances

For each interface return exact server-authored clearances to:

- heel/junction boundary;
- free leg edge;
- positive connector-length end;
- negative connector-length end.

Report:

- governing bolt;
- governing boundary;
- exact minimum complete-hole clearance;
- exact deficit if invalid.

Geometry containment remains distinct from any code-required minimum.

---

## 22. Fastener system

Initial accepted fastener authority:

```text
STAINLESS_STEEL_316
ASTM_F593_17_GROUP_2_316_316L
```

No strength is inferred from the material label.

Use the existing accepted solid fastener renderer:

- solid shank;
- head;
- nut;
- authoritative washers where present.

Hardware follows the physical bolt axis and layer stack.

One shared fastener authority may serve both groups in Stage 3.3A.

Independent fastener systems per interface are future scope.

---

# PART C — MEMBER END TRIM AND INTERFERENCE

## 23. Clip-angle interference

The backend shall distinguish intended contact from unintended positive-volume interference among:

- connected member;
- clip-angle connected leg;
- clip-angle support leg/heel;
- supporting W flange.

A connected member may extend into the clip-angle support leg/heel region when inclined or rolled.

Trim-disabled interference is reported and fail-closed.

No frontend-only clipping.

---

## 24. Shared end-trim engine

Reuse the R12 solid-trimming engine.

For the clip-angle family define:

```text
CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE
```

This backend-authoritative plane bounds the support-leg/heel obstruction toward the connected member.

User-facing controls:

```text
Apply end trim clearance
End clearance to clip-angle support leg
```

The clearance is the exact perpendicular plane-to-plane gap, not a bolt edge distance and not distance along the member axis.

Trim On clips actual connected-profile solids.

Recompute actual hole/bolt distance to the fabricated cut edge.

Tee R12 behavior/fingerprints remain exact.

---

## 25. Trim resistance boundary

Existing resistance methods may consume a fabricated free edge only when their accepted geometry contract unambiguously identifies that edge.

Otherwise:

- physical trim geometry remains valid;
- affected resistance check is unsupported/not evaluated;
- no old untrimmed edge is silently reused;
- no new equation is invented.

---

# PART D — MATERIAL AND DIRECTIONAL ARCHITECTURE

## 26. Connector material

Stage 3.3A connector family:

```text
PULTRUDED_FRP
DIRECTIONAL_FRP
```

Material authority, source identity, revision, approval, and provenance reuse Stage 3.1 contracts.

Material labels alone provide no strength.

316SS and carbon-steel clip-angle connector bodies are future material-expansion scope.

---

## 27. Clip-angle material regions

The clip angle uses two independent physical material regions:

- connected-member leg;
- support leg.

Pultrusion/LW is along `L_C`.

Each leg receives its correct region-specific CW/TT basis from the shared R14B orientation architecture.

The R14C overlay embeds material indicators on both legs.

No component-wide shared CW/TT basis for perpendicular legs.

---

## 28. Connected/support materials

Connected member and support retain their own independent material axes and controlled sources.

The backend remains authoritative for directional-property selection.

The frontend never selects properties from display orientation.

---

# PART E — ACTIONS AND CALCULATIONS

## 29. Canonical action

Use one canonical global member-end action and one physical reference point.

The backend independently transforms the same action/reference into:

- Interface A local frame;
- Interface B local frame.

Moments and unsupported normal components remain traceable.

No frontend force decomposition.

---

## 30. Preview

Preview executes:

- topology/geometry;
- contact/interference;
- bolt paths;
- material axes;
- frame/action transformation;
- Stage 2.5A demand analysis where geometrically applicable;
- visualization snapshot;
- status/limitations.

Preview executes zero resistance equations.

---

## 31. Explicit design path

`Run Design Check` explicitly executes:

```text
canonical action
→ Stage 2.5A demand
→ Stage 2.5B resistance handoff
→ Stage 2.6A compatible group modes
→ existing Stage 2.4B authorized resistance
→ application aggregation
```

Each interface is evaluated independently.

No application-level demand redistribution or line aggregation is invented.

---

## 32. Controlled equal-force case

For the controlled default groups and a canonical `3 kip` force parallel to `L_C`, with the physical force line passing through both group in-plane centroids:

```text
Interface A:
4 bolts × 0.75 kip

Interface B:
4 bolts × 0.75 kip
```

Expected:

- zero interface-normal force;
- zero residual eccentric moment;
- equal direct per-bolt demand;
- existing resistance paths may execute;
- clip-angle body remains not evaluated.

---

## 33. Independent-count case

For:

```text
Interface A: 2 rows × 1 bolt = 2 bolts
Interface B: 2 rows × 2 bolts = 4 bolts
```

under the same concentric `3 kip` force:

```text
Interface A: 1.5 kip per bolt
Interface B: 0.75 kip per bolt
```

subject to existing method applicability.

No count coupling.

---

## 34. Normal-action boundary

If a transformed interface force contains a nonzero component normal to that interface:

- retain exact normal action;
- do not generate bolt-axis tension;
- do not generate prying;
- keep required normal-path checks incomplete;
- prohibit ordinary whole-connection PASS.

A supported numerical interface failure still governs FAIL.

---

## 35. Member-end moments

Member-end moments remain explicit trace.

They are not automatically distributed as clip-angle prying, torsion, or bolt tension.

If their transfer is required and unsupported, the assembly remains not evaluated.

---

## 36. Clip-angle body limitation

Required check identity:

```text
SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE
```

Stage 3.3A status:

```text
NOT_EVALUATED
```

The limitation includes:

- connected-leg bending;
- support-leg bending;
- heel/fillet action;
- connector shear;
- connector rupture;
- connector torsion;
- prying;
- single-angle eccentric body action.

No ordinary whole-connection PASS is permitted while this required check is unevaluated.

A supported interface failure still governs whole-connection FAIL.

---

## 37. Status aggregation

Required precedence:

1. Known supported numerical failure → `FAIL`.
2. Otherwise any required unsupported/incomplete connector-body/normal-action check → `NOT_EVALUATED`.
3. Ordinary whole-connection `PASS` is prohibited in Stage 3.3A.

Interface results remain visible separately.

---

# PART F — API, APPLICATION, AND FRONTEND

## 38. Public endpoints

Add strict stateless endpoints:

```text
POST /api/v1/calculations/clip-angle/preview
POST /api/v1/calculations/clip-angle/design-check
```

Preview/design contracts shall reject:

- extra fields;
- nonfinite values;
- invalid units;
- invalid enum identities;
- missing trim clearance when trim is enabled;
- unauthorized client-authored IDs/fingerprints;
- impossible leg/bolt geometry.

Suggested versions:

```text
clip-angle integration contract: 3.3A-RC1
clip-angle API schema:           0.1.0-draft
clip-angle visualization schema: 0.1.0-draft
```

---

## 39. Fingerprints

Create deterministic fingerprints for:

- canonical input;
- connector geometry;
- Interface A;
- Interface B;
- preview/result;
- application integration.

Include:

- physical dimensions in canonical units;
- hand;
- length anchor/position;
- selected member/support surfaces;
- both bolt groups;
- material/fastener source identities;
- canonical action/reference;
- trim state/clearance;
- parent engine versions.

Exclude:

- display units;
- rounding;
- camera;
- overlay state;
- material-axis display;
- selected UI panel;
- timestamps/random identity.

Equivalent U.S./SI physical inputs produce identical engineering fingerprints.

---

## 40. Connection selector and naming

Add one connection type to the existing dropdown:

```text
Brace/beam connection — Single clip angle
```

Normal header examples:

```text
FRP Flat Plate Brace → Single FRP Clip Angle → W Column Flange
FRP Channel Beam → Single FRP Clip Angle → W Beam Flange
```

Do not use unclear `two interfaces` naming in the user-facing title.

---

## 41. Unified workspace

Reuse the Stage 3.2 shared workspace shell.

Sidebar sections:

1. General / Case
2. Connection
3. Connected Member
4. Supporting Member
5. Clip-Angle Connector
6. Connected Member ↔ Clip-Angle Connected Leg
7. Clip-Angle Support Leg ↔ Support
8. Materials
9. Fasteners
10. Loads / Member-End Action
11. Factors / Method
12. Model / Geometry Status
13. Design Results
14. Advanced / Diagnostics

The viewer remains persistent while the sidebar scrolls.

---

## 42. Clip-angle connector controls

Normal controls:

```text
Connected-leg width
Support-leg width
Thickness
Connector length
Clip-angle side / hand
Length anchor
Clip-angle vertical/longitudinal position
```

Use clear helper text and show the connector frame in the inspector.

---

## 43. Bolt-group controls

Each interface uses the R11 normal hierarchy:

```text
Bolt pattern
Bolt group position
Center bolt group
Computed clearances
Advanced placement
```

The two groups remain independent.

---

## 44. Visualization

Render:

- real W support;
- real connected member profile;
- actual single clip-angle solids;
- both physical bolt groups;
- full hardware;
- selected contact surfaces;
- trim geometry;
- canonical/global action;
- local/interface frames;
- region-embedded material axes.

No generic plate placeholder.

Clip angle heel and both legs must be recognizable in 3D, Front, Top, Side 1, and Side 2 views.

---

## 45. Selection and highlighting

Selecting/focusing:

- connected member;
- clip angle;
- support;
- Interface A group;
- Interface B group;
- physical bolt;
- material region;

shall highlight the corresponding scene object without engineering mutation.

Presentation-only selection/navigation shall not stale design.

---

## 46. Stale/race behavior

Engineering edits:

- cancel stale in-flight requests;
- request preview;
- stale prior design;
- prevent old responses from becoming current.

Presentation-only interactions do not call APIs or stale results.

Reuse R6 behavior.

---

# PART G — CONTROLLED GOLDEN AND ACCEPTANCE

## 47. Required golden cases

The companion Stage 3.3A golden shall cover at minimum:

- G1 default right-hand 2×2 / 2×2 concentric vertical force;
- G2 independent 2×1 / 2×2 groups;
- G3 column/beam support local invariance;
- G4 positive/negative clip-angle hand mirror;
- G5 inclined connected member with fixed connector-leg grid and explicit trim;
- G6 nonzero support-interface normal action fail-closed;
- G7 exact U.S./SI equivalence;
- G8 connector material-region axes and embedded visualization identities;
- G9 complete hardware counts/sides;
- G10 clip-angle body `NOT_EVALUATED` aggregation.

---

## 48. Required Stage 3.2 regressions

Run and preserve:

- Direct workspace;
- full frozen Tee workspace;
- R4 exact U.S./SI fingerprints;
- R7/R8 profile wall paths;
- R9 hardware/inclination;
- R10/R11 positioning;
- R12 trim;
- R13 anchoring;
- R14B material bases;
- R14C embedded material axes;
- Stage 3.2 freeze audit/tag identities.

No frozen behavior changes.

---

## 49. Visual acceptance

After full QA and hosted 4/4 CI:

### V1 — Default clip angle

Column support, Flat Plate connected member, right-hand clip angle, both 2×2 groups.

Verify actual angle geometry and both interfaces.

### V2 — Independent groups

Set A `2×1`, B `2×2`.

Verify 2 versus 4 bolts and independent movement.

### V3 — Hand mirror

Switch clip-angle hand.

Verify physical mirror without dimension/load mutation.

### V4 — Beam support

Switch W Column Flange → W Beam Flange.

Verify shared local geometry and transformed support.

### V5 — Member profiles

Spot-check Angle, Channel, W/I, and RHS connected members.

### V6 — Inclination and trim

Incline connected member; fixed connector-leg bolt grid remains fixed.

Enable trim and verify exact gap to support leg/heel.

### V7 — Normal action

Apply a force producing a nonzero interface-normal component.

Verify no invented bolt tension/prying and fail-closed design.

### V8 — U.S./SI

Load exact U.S. and SI fixtures.

Verify identical physical geometry/results/fingerprints.

### V9 — Material axes

Verify clip-angle connected/support leg material indicators independently.

### V10 — Body limitation

Run design and verify interface checks remain visible while clip-angle body prevents ordinary PASS.

---

## 50. Acceptance boundary

Stage 3.3A is accepted only if:

- one real single clip angle creates two physical independent interfaces;
- connected/support leg surfaces and paths are exact;
- Stage 3.2 shared features are reused rather than copied;
- frozen Tee behavior remains exact;
- geometry, actions, materials, hardware, trim, anchoring, and U.S./SI are backend-authoritative;
- no new resistance equation is introduced;
- clip-angle body remains visibly `NOT_EVALUATED`;
- all golden cases pass;
- complete QA and 4/4 hosted CI pass;
- V1–V10 pass.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
