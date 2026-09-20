# FRP Master Connection — Stage 3.2 Tee Connector Vertical Slice — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.2 introduces the first reusable multi-interface connector assembly after the Stage 3.1 material/fastener architecture.

This specification authorizes **assembly geometry, interface decomposition, and orchestration only**. It does **not** authorize a new resistance equation.

## 2. Accepted starting baseline

- commit: `3720719533e60ba80b899e0c8f68ee6d02e43572`
- subject: `feat: establish connector and fastener material architecture`
- commit count: `45`
- tracked files: `286`
- Stage 2.3 freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

Stage 3.1 material architecture remains controlling.

## 3. Product objective

Implement one reusable **FRP Tee connector assembly** and prove that the same connector implementation can be instantiated for:

1. `Brace -> Column flange -> FRP Tee -> 316SS bolts`
2. `Brace -> Beam flange -> FRP Tee -> 316SS bolts`

The beam and column cases shall differ through supporting-member geometry, local-frame placement, and selected flange surface — not through duplicated Tee engineering code.

The existing direct/reference brace-to-column connection remains unchanged.

## 4. Scope boundary

Stage 3.2 includes:

- Tee connector topology;
- canonical Tee geometry;
- two physical bolted interfaces;
- column-flange and beam-flange support placement;
- global-to-interface local-frame transformation;
- per-interface force decomposition;
- reuse of accepted Stage 2.5A in-plane eccentric bolt-group demand;
- reuse of accepted Stage 2.5B supported resistance handoff;
- reuse of accepted Stage 2.6A eccentric bolt-line shear-out compatibility;
- Stage 3.1 material/fastener authority gating;
- application/API/frontend integration in the existing unified workspace;
- 3D visualization of the real Tee and both bolt groups;
- fail-closed connector-body and unsupported-action qualification.

Stage 3.2 does **not** authorize:

- a new Tee-body strength equation;
- a new clip-angle equation;
- metallic Tee/angle resistance;
- custom FRP bolt resistance;
- automatic bolt-axis tension distribution;
- prying;
- moment-transfer connection mechanics;
- semi-rigid/moment-rotation mechanics;
- concrete anchorage;
- a second independent workspace.

## 5. Tee connector topology

A Tee connector assembly contains exactly one connector component with two orthogonal connection interfaces.

### Interface A — Brace to Tee stem

`BRACE_TO_TEE_STEM`

The selected brace connection face bears against one face of the Tee stem. Bolt axes are normal to the stem interface plane.

### Interface B — Tee flange to supporting-member flange

`TEE_FLANGE_TO_SUPPORT_FLANGE`

The outer Tee flange contact face bears against the selected W-shape supporting-member flange face. Bolt axes are normal to the support-flange interface plane.

Physical load path:

`brace -> Interface A -> Tee connector -> Interface B -> supporting member`

Both interfaces are explicit engineering entities with separate IDs, local frames, bolt groups, layer stacks, geometry, demands, results, and trace.

## 6. Tee local frame and geometry

Use an orthonormal right-handed Tee local frame:

- `L` — Tee longitudinal/extrusion axis;
- `F` — Tee flange transverse axis;
- `S` — Tee stem-depth axis.

The flange mid-surface lies in the `L-F` plane.
The stem mid-surface lies in the `L-S` plane.
The flange and stem planes are perpendicular and intersect on the Tee longitudinal axis.

Required positive Decimal engineering dimensions:

- `connector_length`
- `flange_width`
- `flange_thickness`
- `stem_depth`
- `stem_thickness`

Meanings:

- `connector_length`: cut length measured along `L`;
- `flange_width`: full flange width along `F`;
- `flange_thickness`: flange thickness normal to the flange contact plane;
- `stem_depth`: clear stem projection from the inner flange face to the stem free edge along `S`;
- `stem_thickness`: full stem thickness normal to the stem mid-surface.

No binary float is authoritative. No manufacturer size table or default strength is implied.

## 7. Tee geometry validity

At minimum require:

- every dimension > 0;
- stem thickness < flange width;
- connector length sufficient to contain each assigned bolt group plus controlled edge distances;
- flange width sufficient to contain Interface B bolt layout plus controlled side edge distances;
- stem depth sufficient to contain Interface A bolt layout plus controlled edge distances;
- no bolt center outside its physical Tee interface surface;
- no bolt-hole overlap;
- existing minimum geometry rules remain enforced where applicable.

Do not invent minimum edge-distance equations not already authorized. If an existing geometry rule does not apply to a new Tee surface, expose the missing qualification rather than inventing a criterion.

## 8. Supporting-member reuse

The same Tee connector domain object and geometry implementation shall support both W-column and W-beam placement.

### Column-flange template

The selected W-column flange face is the supporting contact plane. The Tee flange contact face is coincident with that selected column-flange contact plane. The Tee is oriented within the flange plane using the existing canonical connection orientation controls.

### Beam-flange template

The selected W-beam flange face is the supporting contact plane. The Tee flange contact face is coincident with that selected beam-flange contact plane. The supporting member is transformed as a beam in the engineering frame and 3D scene; the Tee implementation itself is unchanged.

The beam template must expose an explicit selected beam flange face when more than one physical flange face is available. Do not silently attach to an arbitrary hidden face.

Equivalent local connection geometry and equivalent local action shall produce identical local interface demand results regardless of whether support role is `COLUMN` or `BEAM`.

## 9. Material system for the Stage 3.2 production slice

Initial production configuration:

- brace/member: existing controlled FRP;
- Tee connector: `PULTRUDED_FRP`;
- supporting member: existing controlled FRP unless the current template already represents another controlled material;
- bolts: `STAINLESS_STEEL_316`;
- bolt strength/property values: explicit accepted existing fastener snapshot/property data only.

The label `STAINLESS_STEEL_316` supplies no strength.
The label `PULTRUDED_FRP` supplies no manufacturer Tee strength.

Stage 3.2 shall use Stage 3.1 resistance-authority gating. No metallic Tee material selector is required yet.

## 10. Canonical action and physical reference

The existing canonical member-end action remains the source for automatic demand.

Member-end moments remain subject to the existing Stage 2.5C scope boundary; Stage 3.2 does not automatically distribute unsupported member-end moments.

For each interface:

1. transform the transmitted force into the interface local frame;
2. transform the same physical force-line/reference point into the interface local frame;
3. decompose the force into in-plane and interface-normal components;
4. pass only the in-plane component and physical reference point to the accepted Stage 2.5A eccentric bolt-group demand engine.

Do not replace the physical reference with a guessed scalar eccentricity when canonical point/vector data is available.

## 11. Interface action convention

Use the existing Stage 2 canonical **transmitted connection-demand direction** consistently at every interface.

Action/reaction sign on physical bodies may be retained in trace, but shall not silently reverse the engineering-demand convention between interfaces.

Changing support role from column to beam must not change this convention.

## 12. In-plane demand handoff

For an interface with in-plane force `Fp`, reuse Stage 2.5A mechanics without modification:

- accepted direct row/bolt shares;
- accepted physical reference point;
- accepted residual moment;
- accepted equal-stiffness rational elastic moment correction;
- exact force equilibrium;
- exact moment equilibrium.

No new bolt-group distribution equation is authorized. Each Tee interface is solved as its own physical bolt group.

## 13. Interface-normal action

Let `Fn` be the transmitted force component normal to an interface plane.

Stage 3.2 does **not** authorize automatic distribution of nonzero `Fn` into bolt-axis tension, prying, or connector bending.

Required:

- retain exact `Fn` in demand trace;
- mark the required axis-demand path unsupported/not evaluated;
- do not fabricate bolt tension;
- do not discard `Fn`;
- do not report ordinary full PASS while a nonzero required `Fn` path is unsupported.

If `Fn == 0` exactly, this rule creates no unsupported normal-force requirement.

## 14. Existing supported resistance reuse

Existing resistance families may run per interface only when current prerequisites are satisfied, including where applicable:

- metallic bolt shear using explicit accepted bolt properties;
- FRP pin bearing;
- conditionally matched block shear;
- Stage 2.6A eccentric bolt-line shear-out;
- explicit bolt-axis-tension resistance only where an accepted explicit resolved axis demand already exists.

Stage 3.2 shall not broaden applicability merely because the interface belongs to a Tee.

## 15. Tee connector body

The Tee is an engineering component in the load path.

Stage 3.2 does not establish a general automatic Tee-body strength method.

Every Tee design result shall therefore include a required connector-component item equivalent to:

`TEE_CONNECTOR_BODY_RESISTANCE — NOT EVALUATED / ENGINEERING METHOD NOT YET AUTHORIZED`

unless a pre-existing accepted authority already evaluates the exact same component and prerequisites, which is not expected.

Aggregation:

- supported bolt/interface failure => assembly `FAIL`;
- no supported failure but required Tee-body or other required checks unsupported => assembly `NOT EVALUATED`;
- ordinary whole-connection `PASS` is prohibited while Tee-body resistance remains unsupported.

## 16. Existing first-row and group-mode limitations

Unchanged:

- general nonzero-residual eccentric first-row net tension remains unsupported;
- Stage 2.6A shear-out runs only under accepted parallel/positive compatibility;
- zero line demand is `Not required — zero line demand`;
- nonparallel and reversed states remain distinctly unsupported;
- no scalar eccentric first-row `L_br` may be invented.

## 17. Two independent bolt-group layouts

The assembly shall carry separate layout objects for:

### Interface A — brace to stem

At minimum:

- row count;
- bolts per row;
- pitch;
- gauge where applicable;
- loaded-boundary-to-Row-1 distance;
- relevant edge distances.

### Interface B — Tee flange to support flange

At minimum the same layout capabilities.

Changing one layout must not mutate the other. Existing canonical row/bolt identity rules apply separately per interface.

## 18. API/application result structure

Expose:

- assembly identity;
- support role;
- selected support flange face;
- Tee geometry;
- exact connector material identity;
- exact fastener material identity;
- Interface A geometry/demand/results;
- Interface B geometry/demand/results;
- interface-normal demand trace;
- connector-body qualification item;
- aggregate result;
- deterministic fingerprints/provenance.

Existing reference-connection API behavior remains backward compatible.

## 19. Unified workspace UI

Do not create a separate Tee page or separate 2D workspace.

Extend the existing unified connection workspace.

Required:

- existing reference connection remains selectable;
- new Tee-connected brace template;
- Tee template support role: column or beam;
- selected physical flange face where required;
- Tee engineering dimensions;
- Interface A bolt-group controls;
- Interface B bolt-group controls;
- existing load/demand-source controls;
- same Run Design Check workflow;
- results grouped by physical interface.

The optional 2D diagnostic may be extended, but the 3D canonical view remains primary.

## 20. 3D visualization

The Tee must be a real solid connector representation.

Required:

- flange solid;
- stem solid;
- correct perpendicular relationship;
- correct engineering dimensions;
- correct contact with brace and support;
- both bolt groups on their real axes;
- bolt diameter scales from engineering diameter;
- schematic head/nut ratios remain presentation-only;
- no hollow/cage bolt regression;
- column support visually vertical;
- beam support visually a beam;
- one Tee geometry implementation reused for both support roles.

Frontend may transform backend-authoritative geometry for display but shall not invent engineering placement.

## 21. Stale-result behavior

Engineering changes stale/clear Tee results, including:

- support role;
- selected flange face;
- Tee dimensions;
- either bolt-group layout;
- connector material;
- fastener system;
- member geometry;
- connection orientation;
- load/reference point.

Pure camera/display changes do not stale engineering results.

## 22. Deterministic identity

Stage 3.2 fingerprints include engineering-relevant:

- Tee topology and dimensions;
- connector material and authority/source identity;
- support role and selected support surface;
- both interface geometries/layouts;
- fastener-system identity;
- canonical action/reference data.

Display mode, camera state, colors, and labels do not.

No existing Stage 2 fingerprint may change.

## 23. Required compatibility tests

At minimum prove:

1. current reference connection is unchanged;
2. one Tee implementation supports column-flange placement;
3. the same Tee implementation supports beam-flange placement;
4. equivalent local geometry/action gives equivalent local demands for column vs beam support;
5. two interface layouts are independent;
6. in-plane demand reuses Stage 2.5A unchanged;
7. nonzero interface-normal action is retained and fail-closed;
8. no automatic bolt-axis tension is invented;
9. current first-row limitations remain;
10. Stage 2.6A group-mode states remain;
11. Tee-body resistance prevents ordinary PASS;
12. supported interface failure still gives assembly FAIL;
13. custom FRP fastener without authority remains blocked;
14. 316SS label does not infer strength;
15. no new resistance equation is introduced.

## 24. Controlled numerical benchmarks

The companion Stage 3.2 golden file controls orchestration tests.

Its values derive only from already accepted Stage 2.5A mechanics and exact vector decomposition.

No new strength value or resistance equation is introduced.

## 25. Visual acceptance

### V1 — Brace to column flange via Tee

Verify physical Tee, Tee-to-column contact, brace-to-stem contact, both bolt groups, geometry controls, grouped results, and visible Tee-body limitation.

### V2 — Brace to beam flange via same Tee

Switch support role to beam and verify beam visualization, correct selected flange contact, unchanged Tee implementation, correct bolt groups, and equivalent local demands for equivalent local inputs.

### V3 — Independent interface layout

Change Interface A layout and verify Interface B does not move. Then change Interface B and verify Interface A does not move.

### V4 — Unsupported normal action

Create nonzero interface-normal force. Verify it remains visible in trace/results, no automatic bolt-axis tension is fabricated, and ordinary PASS is prohibited.

## 26. Acceptance boundary

Accept only if:

- backend/frontend QA green on Windows and Ubuntu;
- dependency/security gates green;
- freeze tag unchanged;
- all controlled Stage 2 hashes exact;
- Stage 3.1 material architecture intact;
- V1-V4 pass;
- no new resistance equation was introduced.

Stage 3.2 acceptance does not authorize connector-component strength mechanics.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
