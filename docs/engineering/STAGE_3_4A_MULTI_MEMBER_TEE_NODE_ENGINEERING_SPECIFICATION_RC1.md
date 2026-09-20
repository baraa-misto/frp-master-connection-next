# FRP Master Connection — Stage 3.4A Multi-Member Tee Node Vertical Slice — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.4A adds a new product connection type:

**Brace/beam node — Multi-member Tee connector**

It is a controlled successor/expansion of the frozen Stage 3.2 Tee family, but it does not replace or silently modify the existing single-member Tee connection.

The new node supports up to three independently defined connected members attached to the same exposed face of one Tee stem:

- optional Upper Brace;
- optional Middle Beam;
- optional Lower Brace.

The Tee flange connects to one W Column Flange support.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository baseline:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- subject:
  `chore: freeze Stage 3.3 clip-angle family baseline`;
- commit count: `75`;
- tracked files: `432`;
- worktree/index: clean.

Expected immutable freeze targets:

- Stage 2.3:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`.

The Stage 3.3 freeze-commit hosted CI is accepted 4/4 green.

## 3. Product identity and frozen-family separation

Normal connection selector label:

`Brace/beam node — Multi-member Tee connector`

The existing frozen connection remains separately available:

`Brace connection — Tee connector`

Historical Stage 3.2 Tee requests, routes, defaults, results, controlled fingerprints, and visual behavior shall remain exact.

Stage 3.4A receives new request/result contracts and new fingerprints.

## 4. Physical topology

The physical load path is:

`Upper Brace (optional) -> Upper bolt group -> Tee stem`

`Middle Beam (optional) -> Middle bolt group -> Tee stem`

`Lower Brace (optional) -> Lower bolt group -> Tee stem`

`Tee stem/flange body -> Tee flange/support bolt group -> W Column Flange`

All active connected members attach to the same selected exposed face of the Tee stem.

The Tee support group is one independent physical group.

At least one connected-member slot must be active.

Any valid one-slot, two-slot, or three-slot combination is permitted.

## 5. Node semantic frame

Define one right-handed Tee-node frame:

- `H_T`: in-plane horizontal axis, positive from the supporting member toward connected members;
- `V_T`: in-plane vertical axis, positive upward along the Tee length;
- `N_T`: Tee-stem normal, positive toward the side containing all connected members.

Require:

`H_T × V_T = N_T`

The selected connected-member contact face is the Tee stem face whose outward normal is `+N_T`.

All three slots attach on the `+N_T` side.

The support-side Tee flange uses the existing frozen Tee/support transform.

## 6. Tee connector geometry

Reuse the accepted Tee connector geometry, material architecture, surface registry, length anchoring, body position, and support placement.

Stage 3.4A normal Tee controls include:

- Tee length;
- flange width;
- flange thickness;
- stem depth;
- stem thickness;
- length anchor:
  - `CENTER`;
  - `POSITIVE_L_END`;
  - `NEGATIVE_L_END`;
- anchor/position coordinate.

Changing Tee length/anchor/body position shall not silently move any connected-member bolt group or the support group.

Every group may be explicitly centered by its own user action.

## 7. Controlled default Tee fixture

The controlled all-three-member benchmark uses:

- Tee length: `30 in`;
- Tee flange width: `8 in`;
- Tee flange thickness: `0.5 in`;
- Tee stem depth: `6 in`;
- Tee stem thickness: `0.5 in`;
- length anchor: `CENTER`;
- body position: `0 in`.

The fixture is intentionally generous enough to separate three independent stem groups.

## 8. Connected-member slots

Stable slot identities:

- `UPPER_BRACE`;
- `MIDDLE_BEAM`;
- `LOWER_BRACE`.

Each slot owns:

- enabled/disabled state;
- connected role;
- profile family/dimensions;
- selected physical surface;
- inclination;
- profile roll;
- connection anchor on the Tee stem;
- independent end-trim state/clearance;
- independent bolt-group layout/position;
- independent member-end wrench/reference point;
- independent geometry/result/fingerprint identities.

A disabled slot contributes exactly zero and creates:

- no connected-member geometry;
- no bolt group;
- no holes/hardware;
- no action;
- no demand/result;
- no hidden warnings;
- no slot engineering fingerprint.

## 9. Upper Brace slot

Profile family:

`ANGLE`

Default profile:

- Leg Y: `6 in`;
- Leg Z: `6 in`;
- thickness: `0.5 in`;
- member/view length: `12 in`;
- selected leg: existing shared Angle-leg surface authority;
- profile roll: `0°`.

Inclination:

`0° <= θ_U <= +90°`

Member longitudinal unit direction:

`L_U = cos(θ_U) H_T + sin(θ_U) V_T`

Default inclination:

`+30°`

Default slot connection anchor:

- `H = 3 in`;
- `V = +10 in`.

## 10. Middle Beam slot

Profile family:

`WIDE_FLANGE_I`

Default profile:

- depth: `10 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.75 in`;
- member/view length: `12 in`;
- selected physical surface: one W/I web broad face;
- profile roll: `0°`.

Inclination is fixed:

`θ_M = 0°`

Member longitudinal direction:

`L_M = +H_T`

Default slot connection anchor:

- `H = 3 in`;
- `V = 0 in`.

The middle slot shall not accept a nonzero inclination in RC1.

## 11. Lower Brace slot

Profile family:

`ANGLE`

Default dimensions match the Upper Brace.

Inclination:

`-90° <= θ_L <= 0°`

Member longitudinal direction:

`L_L = cos(θ_L) H_T + sin(θ_L) V_T`

Default inclination:

`-30°`

Default slot connection anchor:

- `H = 3 in`;
- `V = -10 in`.

## 12. Semantic slot ordering

When active:

- Upper Brace anchor must be above Middle Beam anchor;
- Middle Beam anchor must be above Lower Brace anchor;
- if Middle Beam is disabled, Upper Brace must remain above Lower Brace.

Invalid semantic ordering fails strict validation.

The system shall not silently relabel slots based on position.

## 13. Connected-member physical placement

Reuse the accepted Tee connected-member placement architecture.

For every active slot:

- selected member broad face is coincident with the same Tee stem face;
- member solid lies outside the Tee stem on the connected-member side;
- bolt group remains fixed in the Tee-stem frame;
- member inclination/roll changes the member solid and path intersections, not the group frame;
- positive-volume member/Tee or member/member interference is prohibited except intended face contact and bolt holes.

No frontend placement authority.

## 14. Member-to-member interference

Active connected-member solids are mutually independent.

Reject:

- positive-volume overlap between Upper Brace and Middle Beam;
- overlap between Middle Beam and Lower Brace;
- overlap between Upper and Lower Brace;
- hardware collisions between slot groups;
- unsupported connector/member contact outside intended Tee-stem interfaces.

Zero-volume boundary contact may be retained only where the physical geometry kernel identifies it unambiguously and it does not create an unsupported load path.

## 15. Independent member bolt groups

Stable group identities:

- `UPPER_BRACE_TO_TEE_STEM`;
- `MIDDLE_BEAM_TO_TEE_STEM`;
- `LOWER_BRACE_TO_TEE_STEM`.

Every active group independently owns:

- rows;
- bolts per row;
- pitch;
- gauge;
- group horizontal offset;
- group vertical offset;
- Center action;
- Advanced Placement / edge-distance representation;
- computed complete-hole clearances;
- stable bolt/hole/path IDs;
- demand/result/fingerprint.

No count, pitch, gauge, or position coupling between groups.

## 16. Stem group frame

Every connected-member group is expressed in the fixed Tee-stem plane.

For the semantic node frame:

- group horizontal axis: `H_T`;
- group vertical axis: `V_T`;
- bolt axis: `N_T` or its accepted physical stack sign.

Rows and pitch use `V_T`.

Bolts per row and gauge use `H_T`.

Connected-member inclination shall not rotate the bolt grid.

## 17. Default connected-member groups

Each active default group uses:

- rows: `2`;
- bolts per row: `2`;
- pitch: `2 in`;
- gauge: `2 in`;
- group centered at the slot connection anchor.

Default bolt diameter:

`0.5 in`

Default hole diameter:

`0.563 in`

Complete-hole containment applies independently to:

- selected connected-member region;
- Tee stem;
- finite Tee ends/free edges;
- relevant Angle/W-I profile boundaries.

## 18. Cross-group hole separation

Holes belonging to different stem groups share the same physical Tee stem.

Require exact non-overlap of complete hole disks.

For every pair of holes from different groups:

`center_distance >= radius_1 + radius_2`

unless a stricter existing physical minimum controls.

Coincident or overlapping slot holes are invalid.

No automatic group repositioning.

## 19. Slot-specific trim

Each active slot independently supports the accepted connected-member end-trim contract.

Normal controls:

- `Apply end trim clearance`;
- exact clearance value.

Reuse the backend trim engine and the Tee connector-specific obstruction plane.

Requirements:

- Upper/Lower Angle: actual legs trimmed as applicable;
- Middle W/I: actual web/flanges trimmed as applicable;
- each slot receives independent trim geometry/status;
- trim does not move any bolt group;
- trimmed-edge hole clearances recompute;
- member/member and member/Tee interference recomputes;
- no ghost untrimmed geometry.

Disabled slots have no trim state in the engineering payload.

## 20. Tee-to-support group

Stable identity:

`TEE_FLANGE_TO_SUPPORT`

Reuse the frozen Tee Interface B physical group and W Column Flange support.

The support group independently owns:

- rows;
- bolts per row;
- pitch;
- gauge;
- position;
- Center;
- Advanced Placement;
- exact clearances;
- stable IDs/fingerprint.

Changing any connected-member group shall not move the support group.

## 21. Supporting member

RC1 support:

`W_COLUMN_FLANGE`

Reuse the shared/frozen W Column Flange profile editor, geometry, placement, material axes, surface selection, bolt paths, hardware, and validation.

No other support target is exposed in Stage 3.4A.

## 22. Fastener system

Use the accepted controlled 316SS ASTM F593 system.

One physical bolt per path.

Reuse:

- exact holes;
- endpoint-based shank geometry;
- external head/nut/washer presentation;
- existing source/provenance;
- no internal/duplicate hardware.

No new fastener standard or slip-critical method.

## 23. Slot action contract

Every active slot owns one canonical global action applied by that member to the connection:

- `F_X`, `F_Y`, `F_Z`;
- `M_X`, `M_Y`, `M_Z`;
- physical reference point `r_i`.

The action is immutable and independently traceable.

The frontend shall not decompose, rotate, split, or sum engineering actions.

## 24. Slot action applicability

The full global wrench is retained for traceability.

Existing design methods execute only where their current applicability contracts hold.

RC1 ordinary intended action:

- Upper/Lower brace force primarily along the member axis;
- Middle beam reaction compatible with the horizontal framing condition;
- no automatic member-end moment transfer into prying/tension mechanics;
- no generated bolt-axis tension;
- no invented out-of-plane distribution.

Unsupported components remain explicit limitations while valid geometry stays current.

## 25. Per-slot demand

For each active member group, call the accepted Stage 2.5A demand engine using:

- that slot's action;
- that slot's reference point;
- actual group coordinates;
- actual interface frame.

Do not pass the assembled support wrench back into a member group.

Each slot demand is independent.

## 26. Support transfer wrench

Let active slots be `A`.

Let each slot action applied by the member to the connection be:

- force `F_i`;
- free moment `M_i`;
- reference point `r_i`.

Let the support group reference point be `r_S`.

The exact transferred connection wrench at the support group is:

`F_S = Σ(i in A) F_i`

`M_S = Σ(i in A) [ M_i + (r_i - r_S) × F_i ]`

Use exact Decimal/vector mechanics.

Disabled slots are excluded from the set `A`.

No tolerance-based zeroing.

No scalar-only force addition.

No hidden load redistribution between slots.

The external support reaction on the complete isolated joint is equal and opposite; the support bolt-group demand uses the transferred connection wrench above under existing application sign conventions.

## 27. Wrench-assembly trace

The preview/design result shall expose:

- each active slot force/moment/reference;
- each shifted moment term;
- force sum;
- moment sum;
- support reference point;
- exact assembled support wrench;
- source slot/result fingerprints.

The trace shall prove equilibrium and provenance.

## 28. Support-group demand

Call Stage 2.5A exactly once for the Tee support group using the assembled support wrench and actual support-group coordinates/reference.

Do not separately apply each slot force to the support group and add per-bolt demands.

The support group receives one assembled wrench.

## 29. Same resultant, different decomposition

Two different member-action decompositions may produce the same support transfer wrench.

In that case:

- support-group numerical demand may be identical;
- slot-specific demands differ;
- application/provenance identity shall retain the source decomposition;
- no source slot information is discarded.

## 30. Resistance handoff

Reuse Stage 2.5B, Stage 2.6, and accepted Stage 2.4B methods only where existing applicability contracts hold.

No new demand or resistance equation.

Connected member, Tee stem, Tee flange, support, and metallic bolt layers remain independently traceable.

Existing normal-action, row-distribution, trim-edge, and qualification limitations remain fail-closed.

## 31. Tee-body and intergroup limitations

Required checks include:

- `TEE_CONNECTOR_BODY_RESISTANCE`;
- `MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY`.

Both remain:

`NOT_EVALUATED`

The second limitation includes, without inventing methods:

- Tee stem load transfer between separated member groups;
- interaction of member groups on the Tee stem;
- Tee stem/flange global stress field;
- local connector bending;
- connector buckling/stability;
- connector rupture/yielding outside already accepted layer checks;
- support-side transfer compatibility;
- multi-member connector qualification.

Ordinary whole-connection `PASS` is prohibited.

A supported numerical failure retains overall `FAIL` precedence.

## 32. Status aggregation

Required precedence:

1. True invalid geometry -> `INVALID_GEOMETRY`; design unavailable.
2. Any supported numerical failure -> overall `FAIL`.
3. Otherwise required Tee-body/intergroup or other unsupported checks -> `NOT_EVALUATED`.
4. Ordinary overall `PASS` is prohibited in Stage 3.4A.

Valid geometry with unsupported connector mechanics remains a current preview.

## 33. Preview path

Preview shall:

- validate active slots and slot ordering;
- construct Tee/member/support geometry;
- detect interference;
- resolve all active member paths;
- resolve support group;
- compute exact clearances;
- compute each active slot demand where applicable;
- assemble the exact support transfer wrench;
- compute support demand where applicable;
- return visualization, traces, statuses, and limitations.

Preview executes zero resistance equations.

Add exact call-count proof.

## 34. Explicit design path

`Run Design Check` shall:

- consume current accepted preview geometry/actions;
- execute existing resistance handoff exactly once per required supported physical check;
- preserve parent-demand identities;
- aggregate supported failures and limitations.

No direct bypass of accepted Stage 2 seams.

## 35. API

Add strict stateless endpoints under repository conventions:

- `POST /api/v1/calculations/multi-member-tee/preview`;
- `POST /api/v1/calculations/multi-member-tee/design-check`.

Suggested current contract:

`3.4A-RC1`

Strictly reject:

- zero active slots;
- invalid slot/profile role;
- upper/lower angle domain violation;
- nonzero middle-beam inclination;
- incompatible fields for disabled slots;
- invalid units/nonfinite values;
- client-authored IDs/fingerprints;
- unsupported contract versions;
- extra fields.

No persistence.

## 36. Connection selector and naming

Add under Shear Connections:

`Brace/beam node — Multi-member Tee connector`

Do not rename or replace the frozen single-member Tee option.

Dynamic title shall identify active slots and W Column Flange support without ambiguous `two interfaces` wording.

## 37. Unified workspace

Reuse the persistent viewer and scrollable sidebar.

Normal sections:

1. General / Case;
2. Tee Connector;
3. Active Member Slots;
4. Upper Brace;
5. Upper Brace ↔ Tee Stem;
6. Middle Beam;
7. Middle Beam ↔ Tee Stem;
8. Lower Brace;
9. Lower Brace ↔ Tee Stem;
10. Tee Flange ↔ Support;
11. Materials;
12. Fasteners;
13. Member Actions;
14. Joint Equilibrium;
15. Geometry / Design Results;
16. Advanced / Diagnostics.

Inactive-slot sections are hidden or explicitly disabled without emitting engineering state.

## 38. Slot controls

Upper/Lower Angle slots expose:

- enabled;
- Leg Y;
- Leg Z;
- thickness;
- member/view length;
- selected leg/surface;
- inclination;
- profile roll;
- connection H/V position;
- independent trim;
- independent bolt group.

Middle W/I slot exposes:

- enabled;
- depth;
- flange width;
- web thickness;
- flange thickness;
- member/view length;
- selected web surface;
- profile roll;
- fixed `0°` inclination;
- connection H/V position;
- independent trim;
- independent bolt group.

## 39. Actions UI

Every active slot exposes full global:

- Force X/Y/Z;
- Moment X/Y/Z;
- Reference X/Y/Z.

The Joint Equilibrium section displays:

- slot contribution summaries;
- shifted moments;
- assembled support wrench;
- support-group reference point.

No frontend engineering calculation; display backend-authored values.

## 40. Visualization

Render actual:

- W column;
- Tee flange/stem;
- every active connected member;
- each active member bolt group;
- one support bolt group;
- complete hardware;
- trimmed solids where enabled;
- action/reference overlays;
- local/member/interface frames;
- region-embedded material axes.

No generic member placeholder.

No hidden inactive geometry.

## 41. Selection and material axes

Selection/focus shall distinguish:

- Upper Brace;
- Middle Beam;
- Lower Brace;
- Tee connector;
- support;
- each bolt group;
- each material region.

Material axes shall appear on:

- each active member region;
- Tee stem/flange regions;
- support regions.

The axes toggle remains presentation-only.

## 42. Stale/race behavior

Engineering edits:

- cancel obsolete requests;
- request preview;
- stale prior design;
- latest response wins.

Presentation-only interactions do not call APIs or stale results.

Switching a slot off removes its engineering state only after the current backend preview is accepted.

## 43. Controlled default all-three-member fixture

Tee:
- length `30 in`;
- flange width `8 in`;
- flange thickness `0.5 in`;
- stem depth `6 in`;
- stem thickness `0.5 in`;
- anchor `CENTER`;
- position `0 in`.

Upper Brace:
- Angle `6 × 6 × 0.5 in`;
- length `12 in`;
- inclination `+30°`;
- roll `0°`;
- anchor `(H,V)=(3,+10) in`;
- group `2 × 2`, pitch/gauge `2 in`.

Middle Beam:
- W/I depth `10 in`;
- flange width `8 in`;
- web thickness `0.5 in`;
- flange thickness `0.75 in`;
- length `12 in`;
- inclination `0°`;
- roll `0°`;
- anchor `(3,0) in`;
- group `2 × 2`, pitch/gauge `2 in`.

Lower Brace:
- Angle `6 × 6 × 0.5 in`;
- length `12 in`;
- inclination `-30°`;
- roll `0°`;
- anchor `(3,-10) in`;
- group `2 × 2`, pitch/gauge `2 in`.

Support group:
- `2 × 2`;
- pitch/gauge `2 in`;
- valid centered support zone.

Fasteners:
- `0.5 in` bolts;
- `0.563 in` holes;
- controlled 316SS ASTM F593 source.

## 44. Controlled default all-three-member actions

Actions applied by members to the connection in the semantic `H_T/V_T/N_T` basis:

Upper Brace:
- force `(3.4641016151377544, 2.0, 0) kip`;
- moment `(0,0,0) kip-in`;
- reference `(3,10,0) in`.

Middle Beam:
- force `(6,0,0) kip`;
- moment `(0,0,0) kip-in`;
- reference `(3,0,0) in`.

Lower Brace:
- force `(3.4641016151377544,-2.0,0) kip`;
- moment `(0,0,0) kip-in`;
- reference `(3,-10,0) in`.

Support reference:
- `(0,0,0) in`.

Expected assembled support transfer wrench:

- force `(12.9282032302755088,0,0) kip`;
- moment `(0,0,0) kip-in`.

The Upper and Lower shifted moment contributions cancel exactly.

Default concentric per-bolt magnitudes:

- Upper group: `1 kip`;
- Middle group: `1.5 kip`;
- Lower group: `1 kip`;
- Support group: `3.2320508075688772 kip`.

## 45. Exact U.S./SI equivalence

Use exact conversions, including:

- `30 in = 762 mm`;
- `12 in = 304.8 mm`;
- `10 in = 254 mm`;
- `8 in = 203.2 mm`;
- `6 in = 152.4 mm`;
- `3 in = 76.2 mm`;
- `2 in = 50.8 mm`;
- `0.75 in = 19.05 mm`;
- `0.5 in = 12.7 mm`;
- `0.563 in = 14.3002 mm`;
- `4 kip = 17.792886461042 kN`;
- `6 kip = 26.689329691563 kN`.

Equivalent physical inputs shall have identical engineering geometry/results/fingerprints.

## 46. Fingerprints

Create deterministic identities for:

- complete input;
- each active slot input;
- each active member geometry;
- each active member interface;
- Tee connector geometry;
- support interface;
- each slot action;
- assembled support wrench;
- preview/result;
- application integration.

Disabled slots are absent from canonical engineering payloads except for an explicit slot-enabled mask if required by schema identity.

Presentation state excluded.

Equivalent U.S./SI requests match.

Frozen single-member Tee, Clip-Angle, Direct, and earlier Stage 2 fingerprints remain exact.

## 47. Required controlled golden cases

At minimum:

G1. Upper-only, 4 kip axial, Upper and support groups `2 × 2` -> `1 kip/bolt`.
G2. Middle-only, 6 kip, Middle `2 × 1`, support `2 × 2` -> `3 kip/bolt` and `1.5 kip/bolt`.
G3. Lower-only, 4 kip axial, Lower and support groups `2 × 2` -> `1 kip/bolt`.
G4. Default all-three-member action -> exact assembled `(12.9282032302755088,0,0)` kip and zero moment.
G5. Equal/opposite separated forces -> zero net force and nonzero exact couple.
G6. Disabled slot contributes no geometry/action/result/fingerprint.
G7. Semantic slot ordering/domain validation.
G8. Independent group edits do not move other groups/support.
G9. Cross-group Tee-stem hole overlap invalid.
G10. Connected-member positive-volume interference invalid.
G11. Upper/lower inclination sign and middle `0°` constraints.
G12. Same support wrench from different decompositions -> same support numerical demand, different source provenance.
G13. Nonzero unsupported normal action remains current geometry but design-limited.
G14. Member-end moments retained; no generated prying/bolt-axis tension.
G15. Exact U.S./SI equivalence.
G16. Material axes on every active member/Tee/support.
G17. Preview zero resistance calls.
G18. Tee-body/intergroup limitations prohibit ordinary PASS.
G19. Supported member/support numerical failure governs overall FAIL.
G20. Frozen single-member Tee / Clip-Angle / Direct regressions exact.

## 48. Deliberate exclusions

Not authorized in Stage 3.4A:

- connected profile expansion beyond Angle braces / W-I middle beam;
- support target beyond W Column Flange;
- members on opposite Tee-stem faces;
- more than three connected slots;
- two beams;
- crossed brace semantics;
- shared/common bolt group between connected members;
- automatic load redistribution between slots;
- Tee-body global resistance method;
- intergroup connector stress-field method;
- moment connection;
- generated prying or bolt-axis tension;
- adhesive/epoxy or welds;
- persistence/reporting/authentication changes.

## 49. Acceptance boundary

Stage 3.4A is accepted only if:

- any valid one/two/three-slot combination works;
- all active members attach to the same Tee-stem face;
- each active member group remains independent;
- exact multi-wrench assembly is proven;
- support group uses one assembled wrench;
- disabled slots are truly absent;
- slot ordering/interference/hole overlap fail closed;
- frozen single-member Tee behavior remains exact;
- no new demand/resistance equation is introduced;
- Tee-body/intergroup limitations remain explicit;
- full local and object-isolated QA pass;
- hosted Backend/Frontend Ubuntu/Windows CI passes;
- user visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
