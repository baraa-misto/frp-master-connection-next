# FRP Master Connection — Stage 3.4B Multi-Member Tee Connected-Profile and Support Expansion — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.4B expands the accepted Stage 3.4A Multi-Member Tee Node to the common connected-profile and supporting-member matrices already proven by the frozen Tee and Clip-Angle platforms.

Stage 3.4B does not change:

- the maximum of three optional connected-member slots;
- the same-face Tee-stem topology;
- independent connected-member bolt groups;
- one independent Tee-to-support group;
- exact member-wrench translation and support-wrench assembly;
- Stage 2 demand/resistance seams;
- Tee-body/intergroup engineering limitations.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `51fd10ffe269fd4b07000eb3dd234411315d7429`;
- subject:
  `fix: render multi-member tee workspace`;
- commit count: `78`;
- worktree/index: clean.

Accepted Stage 3.4A-R2 hosted CI:

- GitHub Actions run #73;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- total duration approximately `4m 52s`.

Expected source identities:

- backend source tree:
  `969fbd62975c958e3bb5d909b8f656dee0aed2c3`;
- frontend source tree:
  `6f75da7944281c4e4b78af40934738d9fa5404f2`.

Expected immutable freeze targets:

- Stage 2.3:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`.

## 3. Connection identity

Existing connection type:

`Brace/beam node — Multi-member Tee connector`

No new selector option is created.

Historical contract:

`3.4A-RC1`

Expanded contract:

`3.4B-RC1`

Both contracts remain strict and explicitly versioned.

Existing valid `3.4A-RC1` requests shall remain accepted with exact geometry, results, and fingerprints.

## 4. Slot identities and semantics

Stable slot identities remain:

- `UPPER_BRACE`;
- `MIDDLE_BEAM`;
- `LOWER_BRACE`.

Normal UI labels may use:

- Upper Brace;
- Middle Member (horizontal);
- Lower Brace.

The profile family does not redefine slot orientation semantics.

Inclination domains:

- Upper: `0° <= θ_U <= +90°`;
- Middle: `θ_M = 0°`;
- Lower: `-90° <= θ_L <= 0°`.

Profile roll remains independently controlled where supported.

## 5. Connected-profile matrix

Every slot shall offer exactly:

1. `FLAT_PLATE`
2. `ANGLE`
3. `CHANNEL`
4. `WIDE_FLANGE_I`
5. `RECTANGULAR_HOLLOW_SECTION`
6. `SOLID_RECTANGULAR_SECTION`

The same shared connected-profile registry/editor shall be used across all three slots.

Do not create three independently maintained profile enumerations/editors.

## 6. Connected-profile defaults

When a user changes an active slot profile family, initialize a deterministic valid family-specific default without moving the slot connection anchor or any other bolt group.

### Flat Plate
- width: `6 in`;
- thickness: `0.5 in`;
- member/view length: `12 in`;
- default surface: positive plate face.

### Angle
- Leg Y: `6 in`;
- Leg Z: `6 in`;
- thickness: `0.5 in`;
- member/view length: `12 in`;
- default surface: Leg Y outer face;
- profile roll: `0°`.

### Channel
- depth: `8 in`;
- flange width: `4 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- member/view length: `12 in`;
- default surface: web positive face;
- profile roll: `0°`.

### Wide-Flange / I
- depth: `10 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.75 in`;
- member/view length: `12 in`;
- default surface: web positive face;
- profile roll: `0°`.

### Rectangular Hollow Section
- depth: `6 in`;
- width: `4 in`;
- wall thickness: `0.5 in`;
- member/view length: `12 in`;
- default surface: positive Y face;
- profile roll: `0°`.

### Solid Rectangular Section
- depth: `6 in`;
- width: `4 in`;
- member/view length: `12 in`;
- default surface: positive Y face;
- profile roll: `0°`.

Family changes shall not alter:

- enabled state;
- slot inclination;
- slot H/V anchor;
- slot action/reference;
- other slot state;
- other group geometry;
- support group geometry.

## 7. Shared profile field contract

Only fields applicable to the selected profile may appear in the engineering request.

Strictly reject stale incompatible fields.

Examples:

- SRS request contains no wall thickness;
- Flat Plate contains no web/flange fields;
- Channel/W-I contain web/flange dimensions;
- Angle contains two legs and selected leg/surface;
- RHS contains wall thickness.

Frontend hidden fields shall not leak into requests.

## 8. Connection surfaces

Use the existing shared physical-surface registry.

Permitted surfaces are exactly those already accepted for the selected profile family.

At minimum:

- Flat Plate: positive/negative plate face;
- Angle: accepted outer face of selected leg;
- Channel: accepted web/flange broad faces already supported by the shared registry;
- W/I: accepted web/flange broad faces already supported by the shared registry;
- RHS: one selected exterior wall with exact opposite wall;
- SRS: one selected exterior face with exact opposite face.

No generic plate approximation.

## 9. Same-face placement

All active connected members continue to attach to the same selected Tee-stem face.

For each profile:

- selected profile surface is coincident with the Tee-stem contact plane;
- connected-member solid lies outside the Tee stem;
- slot anchor is expressed in the fixed Tee-node H/V frame;
- inclination/roll changes the member solid;
- the bolt grid remains fixed in the Tee-stem frame.

No frontend placement offsets.

## 10. Open-profile physical paths

### Flat Plate

Path:

`selected Flat Plate layer -> Tee stem`

### Angle

Path:

`selected Angle leg -> Tee stem`

Reject heel/perpendicular-leg/outside-leg paths.

### Channel

Path:

`selected finite Channel region -> Tee stem`

Reject flange/web-junction or outside-region paths.

### W/I

Path:

`selected finite W/I region -> Tee stem`

Reject flange/web-junction or outside-region paths.

Reuse exact accepted profile targeting/path resolvers.

## 11. RHS connected-member path

For any active slot using RHS:

`Tee stem -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

Use one continuous physical bolt per axis.

Requirements:

- near and far holes on one exact axis;
- both walls independently contained;
- R8 corner exclusions on both walls;
- cavity receives no material/demand/resistance;
- no internal nut or washer;
- endpoint-based shank geometry;
- external hardware only.

Preserve the accepted Tee connected-RHS successor architecture.

## 12. SRS connected-member path

For any active slot using SRS:

`Tee stem -> full solid rectangular depth`

Use one continuous physical bolt.

No cavity.

Entry and exit faces independently satisfy complete-hole containment.

## 13. Slot inclination and profile independence

Upper/lower inclination domains apply to every selected profile family.

Middle inclination remains exactly `0°` for every family, including:

- Flat Plate;
- Angle;
- Channel;
- W/I;
- RHS;
- SRS.

Do not infer inclination constraints from profile names.

## 14. Slot ordering

Preserve Stage 3.4A semantic ordering:

- Upper anchor above Middle when both active;
- Middle above Lower when both active;
- Upper above Lower when Middle disabled.

Profile geometry may still cause interference even when semantic ordering is valid.

## 15. Member/member and member/Tee interference

Evaluate actual current solids for every mixed-profile combination.

Reject positive-volume:

- Upper/Middle overlap;
- Middle/Lower overlap;
- Upper/Lower overlap;
- member/Tee embedding;
- profile flange/leg/wall collision with another member;
- hardware collision between groups.

No automatic slot repositioning.

## 16. Independent connected-member groups

The four Stage 3.4A physical groups remain:

- Upper member ↔ Tee stem;
- Middle member ↔ Tee stem;
- Lower member ↔ Tee stem;
- Tee flange ↔ Support.

Each group retains independent:

- count;
- pitch;
- gauge;
- offsets;
- Center action;
- advanced placement;
- clearances;
- paths;
- demand;
- result;
- fingerprint.

Changing profile family does not move any group automatically.

## 17. Cross-group hole validation

All active connected groups share the Tee stem.

Continue exact cross-group complete-hole non-overlap checks.

Profile changes may alter member-side containment but do not relax Tee-stem overlap validation.

No automatic group spacing.

## 18. Independent trim

Each active slot supports trim for all six profiles through the accepted shared trim architecture.

Requirements:

- Flat Plate: real plate trim;
- Angle: both physical legs as applicable;
- Channel: web/flanges;
- W/I: web/flanges;
- RHS: all relevant walls; hollow cavity retained;
- SRS: solid body retained.

Trim:

- is slot-specific;
- does not move groups;
- recomputes fabricated-edge clearances;
- recomputes interference;
- recomputes RHS/SRS endpoint hardware;
- produces no ghost untrimmed geometry.

## 19. Supporting-member matrix

Expose exactly the shared seven support targets:

1. `W_COLUMN_FLANGE`
2. `W_BEAM_FLANGE`
3. `W_COLUMN_WEB`
4. `CHANNEL_COLUMN_WEB`
5. `ANGLE_COLUMN_LEG`
6. `RECTANGULAR_HOLLOW_COLUMN_WALL`
7. `SOLID_RECTANGULAR_COLUMN_FACE`

No W Beam Web.

Use the same shared support-target identity/editor already accepted by Tee and Clip-Angle families.

## 20. Support target defaults

Use deterministic valid generous defaults from the shared support editor.

At minimum:

### W Column / Beam Flange and W Column Web
- member/view length: `16 in`;
- depth: `8 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.75 in`.

### Channel Column Web
- member/view length: `16 in`;
- depth: `8 in`;
- flange width: `4 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`.

### Angle Column Leg
- member/view length: `16 in`;
- Leg Y: `8 in`;
- Leg Z: `8 in`;
- thickness: `0.5 in`.

### RHS Column Wall
- member/view length: `16 in`;
- outside width: `10 in`;
- outside depth: `6 in`;
- wall thickness: `0.5 in`.

### SRS Column Face
- member/view length: `16 in`;
- width: `10 in`;
- depth: `6 in`.

Switching target shall not move connected-member groups.

## 21. Support physical paths

### W Column Flange / W Beam Flange

Preserve accepted Tee flange/support behavior.

### W Column Web

`Tee flange -> W web`

One web thickness; no flange penetration.

### Channel Column Web

`Tee flange -> Channel web`

One web thickness; reject flange/junction paths.

### Angle Column Leg

`Tee flange -> selected Angle leg`

Reject heel/perpendicular-leg paths.

### RHS Column Wall

`Tee flange -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

One physical bolt per axis; no internal hardware.

### SRS Column Face

`Tee flange -> full SRS depth`

One continuous physical bolt.

## 22. Support transform and node frame

The shared support target determines the authoritative global placement/transform of the Tee node.

The semantic Tee-node H/V/N frame is mapped exactly once from the selected support target.

All active connected members remain on the same Tee-stem face after any support-target change.

No double transform.

No camera-dependent engineering orientation.

## 23. Support group independence

The Tee-to-support group remains independent.

Changing support target may alter the physical support path and hardware span, but shall not:

- change connected-member bolt-group H/V coordinates;
- recenter connected groups;
- alter slot actions;
- alter slot profile selections;
- couple group patterns.

Invalid new support geometry fails closed.

## 24. Rectangular support hardware

RHS support:

- Tee flange;
- near wall;
- cavity;
- far wall;
- one shank;
- no internal hardware;
- far nut/washer external.

SRS support:

- Tee flange;
- full solid depth;
- external far hardware.

Reuse endpoint-based hardware placement.

## 25. Actions and exact support-wrench assembly

Stage 3.4A action and equilibrium contracts remain exact.

Profile family and support target do not alter the meaning of:

- slot force;
- slot moment;
- slot reference;
- shifted moment;
- assembled support transfer wrench.

At support reference `r_S`:

`F_S = Σ F_i`

`M_S = Σ [M_i + (r_i - r_S) × F_i]`

The support reference point shall be the actual selected support-group reference under the current support transform.

No new load distribution.

## 26. Demand and resistance

Per-slot demand:

- Stage 2.5A exactly once per active slot.

Support demand:

- Stage 2.5A exactly once using one assembled support wrench.

Resistance:

- existing accepted Stage 2.5B / 2.6 / 2.4B methods only where applicability holds.

No new equation.

No automatic prying or bolt-axis tension.

## 27. Required limitations

Always retain:

- `TEE_CONNECTOR_BODY_RESISTANCE`;
- `MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY`.

When RHS is active as connected member or support, also retain:

- `RHS_LOCAL_WALL_RESPONSE`;
- `RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT`.

When SRS is active as connected member or support, retain:

- `SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY`.

All remain `NOT_EVALUATED`.

These are design limitations, not geometry-invalid reasons.

Ordinary whole-connection PASS remains prohibited.

## 28. Preview and design paths

Preserve Stage 3.4A preview/design separation.

Preview:

- validates fields;
- builds actual profiles/support;
- resolves paths/hardware/trims/interference;
- computes per-slot demand;
- assembles support wrench;
- computes support demand;
- executes zero resistance engines.

Design check:

- executes existing supported resistance checks exactly once;
- retains all limitations and failure precedence.

## 29. API evolution

Existing routes remain:

- `/api/v1/calculations/multi-member-tee/preview`;
- `/api/v1/calculations/multi-member-tee/design-check`.

Accept:

- historical `3.4A-RC1`;
- expanded `3.4B-RC1`.

For `3.4A-RC1`:

- preserve original fixed profile/support matrix;
- preserve exact payload meaning;
- preserve exact fingerprints.

For `3.4B-RC1`:

- accept profile family and target-specific fields;
- reject stale/incompatible fields;
- reject unknown profiles/targets;
- reject W Beam Web;
- preserve strict extra-field rejection.

Unknown future versions fail closed.

## 30. Frontend connected-profile editor

Use one shared slot profile editor for Upper/Middle/Lower.

The editor shall:

- expose all six families;
- render only selected-family fields;
- preserve slot semantics/actions/anchor/group on family change;
- omit stale hidden fields from requests;
- preserve current/last-valid behavior.

Do not implement separate hard-coded editors per slot.

## 31. Frontend support editor

Reuse the shared seven-target support editor already accepted in Stage 3.3C2.

No Multi-Member-Tee-only duplicate.

## 32. Workspace and titles

The existing Multi-Member Tee workspace remains.

Dynamic title shall identify active slot profile families and selected support target without becoming excessively long.

The Middle slot normal UI label should be:

`Middle Member (horizontal)`

while stable contract identity may remain `MIDDLE_BEAM`.

## 33. Visualization

Render actual backend-authored geometry for:

- every active selected profile;
- Tee connector;
- selected support profile;
- four independent groups;
- full-through RHS/SRS bolts;
- trims;
- hardware;
- actions;
- material axes.

No generic Flat Plate fallback.

No inactive/stale profile geometry after a family switch.

## 34. Material axes

Use backend-authored region bases and C3-R1 owner-qualified binding.

Coverage:

- Flat Plate: plate;
- Angle: both legs;
- Channel: web/flanges;
- W/I: web/flanges;
- RHS: walls only, never cavity;
- SRS: stable solid-volume basis;
- Tee stem/flange;
- support profile regions.

Toggle remains presentation-only.

## 35. Default and backward compatibility

The Stage 3.4A all-three default remains exactly:

- Upper Angle;
- Middle W/I;
- Lower Angle;
- W Column Flange.

Its geometry, actions, support wrench, demands, results, and fingerprints remain exact.

Stage 3.4B shall not silently update that default to another profile/support combination.

## 36. Fingerprints

Existing Stage 3.4A request fingerprints remain exact.

New deterministic fingerprints include:

- each slot's profile family and family-specific dimensions/surface;
- support target/profile/surface;
- physical full-through path identities;
- material/source identities;
- trim geometry;
- support transform;
- actions/references;
- assembled wrench;
- methods/versions.

Presentation state excluded.

Equivalent U.S./SI requests match.

Frozen Direct, Stage 3.2 Tee, and Stage 3.3 Clip-Angle fingerprints remain exact.

## 37. Controlled profile/support matrix

Automated backend/frontend coverage shall include:

### Upper slot
All six connected profiles.

### Middle slot
All six connected profiles, including Flat Plate and Angle at exactly `0°`.

### Lower slot
All six connected profiles.

### Support
All seven support targets.

Use valid generous fixtures.

Not every cross product needs a user-facing golden, but automated matrix tests shall cover every profile in every slot and every support target.

## 38. Required controlled golden cases

At minimum:

G1. Historical Stage 3.4A default exact.
G2. Upper-slot six-profile matrix.
G3. Middle-slot six-profile matrix.
G4. Lower-slot six-profile matrix.
G5. Middle Flat Plate accepted at `0°`.
G6. Middle Angle accepted at `0°`.
G7. Middle nonzero inclination rejected for all six profiles.
G8. Upper/lower inclination domains apply to all six profiles.
G9. Connected RHS full-through path in each slot.
G10. Connected SRS full-depth path in each slot.
G11. Open-profile physical-surface/path matrix.
G12. Seven support targets.
G13. RHS support full-through path/no internal hardware.
G14. SRS support full-depth path.
G15. W-web/Channel-web/Angle-leg support paths.
G16. Mixed Flat Plate / Angle / Channel all-three node with exact unchanged wrench assembly.
G17. One/two/three-slot combinations with expanded profiles.
G18. Mixed-profile member interference fails closed.
G19. Cross-group Tee-stem hole overlap fails closed.
G20. Trim matrix across six profiles.
G21. Material-axis matrix across profiles/supports.
G22. Exact U.S./SI representative mixed node.
G23. Profile/support changes preserve unaffected group independence.
G24. Disabled slot remains absent after profile-family changes.
G25. Rectangular local limitations remain current geometry, `NOT_EVALUATED`.
G26. Strict target/profile field validation.
G27. No duplicate/incorrectly oriented RHS/SRS hardware.
G28. Stage 3.4A, frozen Tee, Clip-Angle, and Direct regressions exact.

## 39. Deliberate exclusions

Stage 3.4B does not authorize:

- more than three slots;
- members on opposite Tee-stem faces;
- independent slot semantic angles outside existing domains;
- W Beam Web support;
- new connected profile families beyond the six;
- support targets beyond the seven;
- automatic load redistribution;
- shared common bolts between member groups;
- Tee-body/intergroup engineering equations;
- adhesives/epoxy;
- welds;
- moment connection;
- persistence/reporting/auth changes.

## 40. Acceptance boundary

Stage 3.4B is accepted only if:

- all six profiles work in all three slots;
- Middle Flat Plate and Angle work at `0°`;
- all seven support targets use real geometry;
- rectangular full-through/full-depth hardware is correct;
- all slot combinations remain valid where geometry permits;
- group/action/wrench mechanics remain exact;
- Stage 3.4A historical requests remain exact;
- frozen Direct/Tee/Clip-Angle behavior/fingerprints remain exact;
- no new equation is introduced;
- limitations remain explicit;
- full local/object-isolated QA and hosted four-job CI pass;
- user visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
