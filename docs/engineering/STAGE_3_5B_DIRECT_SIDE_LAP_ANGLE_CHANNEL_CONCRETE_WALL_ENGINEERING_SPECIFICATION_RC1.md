# FRP Master Connection — Stage 3.5B Direct Side-Lap Angle/Channel to Concrete Wall — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.5B adds one new Shear Connections product:

**FRP Angle or Channel directly side-lapped and anchored to a finite concrete wall**

The concrete wall has a real free end.

The FRP member continues beyond that free end.

The user controls the physical member/wall overlap through one explicit **Side-lap length**.

No clip angle, Tee, weld, or adhesive is present in this connection.

Concrete and anchor capacity remain external.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `e0534a8da4b7ce3d74cf1bed3d4be4e0c7fcbd12`;
- subject:
  `feat: expand concrete-wall forces and correct axes`;
- commit count: `83`;
- clean worktree/index.

Expected Stage 3.5A-R2 hosted CI:

- GitHub Actions run #78;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

Before mutation, verify current governance records show Stage 3.5A-R2 accepted for implementation/CI. If any required final Stage 3.5A-R2 owner visual-acceptance record is explicitly still open, **STOP before mutation** and report it rather than inferring acceptance.

Expected immutable freeze targets:

- Stage 2.3:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- Stage 3.4:
  `2303ec713d6d038b935e076b909c3b639ced0e09`.

## 3. Product identity

New selector label:

`Brace/beam connection — Direct side-lap Angle/Channel to concrete wall`

Suggested API routes:

- `/api/v1/calculations/direct-side-lap-concrete/preview`;
- `/api/v1/calculations/direct-side-lap-concrete/design-check`.

Current contract:

`3.5B-RC1`.

This is a new product type and shall not replace Stage 3.5A concrete-wall paired angles.

## 4. Side-lap frame

Define one right-handed frame:

- `L_LAP`: connected-member longitudinal axis, positive beyond the wall free end;
- `S_LAP`: transverse direction within the concrete-wall face;
- `N_W`: concrete-wall outward normal.

Require:

`L_LAP × S_LAP = N_W`.

The concrete wall face is at:

`N_W = 0`.

The concrete wall occupies:

`N_W <= 0`.

The connected FRP contact surface is coincident with:

`N_W = 0`.

The FRP member occupies the exterior side:

`N_W >= 0`

except for its finite thickness as defined by exact surface placement.

## 5. Wall free-end geometry

The concrete wall has a real free end at:

`L_LAP = 0`.

The wall extends behind that free end:

`-L_wall <= L_LAP <= 0`.

Controlled default wall run length:

`48 in`.

The wall transverse width is along `S_LAP`.

Controlled default:

`48 in`.

Wall thickness:

`8 in`.

The wall is a finite concrete prism.

Concrete has no FRP LW/CW/TT material axes.

## 6. Side-lap length

Input:

`side_lap_length`.

Controlled default:

`12 in`.

The connected member starts at:

`L_LAP = -side_lap_length`

and continues through the wall free end into positive `L_LAP`.

The physical overlap zone is exactly:

`-side_lap_length <= L_LAP <= 0`.

The side-lap length is engineering geometry and is included in fingerprints.

## 7. Member projection beyond wall

Input:

`member_projection_beyond_wall`.

Controlled default:

`16 in`.

The rendered/physical member extends to:

`L_LAP = +member_projection_beyond_wall`.

Require:

- positive finite value;
- member total visible/physical connection length:
  `side_lap_length + member_projection_beyond_wall`.

Changing projection does not move anchors.

## 8. Connected profiles

Exactly:

- `ANGLE`;
- `CHANNEL`.

Default profile:

`CHANNEL`.

No other profile in RC1.

## 9. Channel physical topology

The Channel **web only** is permitted against concrete.

The selected wall-contact surface shall be one accepted Channel web broad face.

The Channel flanges remain physically present and project away from concrete.

Prohibited:

- top flange against wall;
- bottom flange against wall;
- any flange-to-concrete side-lap request.

Channel flange-to-wall input is rejected, not reinterpreted.

## 10. Channel default

Controlled default:

- depth: `8 in`;
- flange width: `4 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- side-lap length: `12 in`;
- projection beyond wall: `16 in`;
- accepted web face against wall.

Profile orientation shall leave both flanges outside concrete.

## 11. Angle physical topology

One selected Angle leg lies directly against the concrete wall face.

The other leg remains physically present and projects away from concrete.

The user may select either accepted Angle leg.

The placement engine shall orient the member so the unselected leg remains exterior to concrete.

Reject:

- heel embedded in concrete;
- perpendicular leg embedded in concrete;
- outside-leg anchor paths;
- ambiguous selected surface.

## 12. Angle default

Controlled default:

- Leg Y: `6 in`;
- Leg Z: `6 in`;
- thickness: `0.5 in`;
- side-lap length: `12 in`;
- projection beyond wall: `16 in`;
- default selected leg/surface under the shared Angle authority.

## 13. Profile field strictness

For Channel accept only Channel-specific fields.

For Angle accept only Angle-specific fields.

Reject stale incompatible fields when switching profile family.

No generic plate fallback.

## 14. Direct wall-anchor group

There is one physical anchor group.

Stable identity:

`DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP`.

It passes directly through the selected FRP physical region into the concrete.

No intermediate connector component.

## 15. Default anchor group

Controlled default:

- rows: `2`;
- anchors per row: `1`;
- pitch: `4 in`;
- gauge: inactive for 1 column;
- group centroid distance behind wall free end: `6 in`;
- transverse centroid: `0`;
- nominal anchor diameter: `0.5 in`;
- FRP hole diameter: `0.563 in`;
- specified embedment: `4 in`.

In side-lap coordinates:

- group centroid:
  `(-6,0,0) in`;
- anchor centers:
  `(-8,0,0) in`;
  `(-4,0,0) in`.

## 16. Anchor-group position input

Normal UI shall express longitudinal group position as:

`Anchor group distance behind wall free end`

with positive user value.

Backend coordinate:

`L_group = -distance`.

Default user value:

`6 in`.

The user may also control transverse offset under existing fixed-grid conventions.

## 17. Explicit Center action

Provide:

`Center anchor group in overlap`.

This explicit action sets:

`distance behind wall free end = side_lap_length / 2`.

Changing side-lap length itself shall **not** center or move the group.

Changing profile family shall not move the group.

## 18. Anchor layout

Rows/pitch are along `L_LAP`.

Anchors-per-row/gauge are along `S_LAP`.

The user may increase:

- rows;
- anchors per row;
- pitch;
- gauge.

Complete-hole containment is required in the selected FRP physical region.

Anchor centers must lie on the finite concrete face and within the physical overlap interval.

## 19. Overlap-zone containment

For every anchor center require:

`-side_lap_length <= L_anchor <= 0`.

Also require the complete FRP hole to lie within the actual connected FRP region.

The wall may continue behind the member start, but there is no FRP connection outside the overlap.

An anchor outside the overlap is invalid even if it remains inside the concrete wall.

## 20. Overlap change behavior

Changing side-lap length:

- moves the connected-member start/end relative to the wall free end;
- changes the physical overlap boundary;
- does not move the anchor group;
- does not change load values;
- recomputes anchor/member containment;
- recomputes member/wall geometry;
- marks prior design stale.

Example:

Default group anchors at `L=-8` and `-4`.

If side-lap length is reduced below `8 in`, the `L=-8` anchor becomes outside the overlap and geometry fails closed.

No automatic anchor relocation.

## 21. Concrete geometry validation

Validate coordination geometry:

- anchor center on finite concrete face;
- specified embedment positive and <= wall thickness;
- anchor shank inside wall volume;
- member/anchor geometry compatible with wall free end;
- no FRP member penetration into concrete outside intended contact surface.

These are geometry/coordination checks, not concrete capacity.

## 22. External anchor presentation

Each anchor renders:

- one exterior nut/washer against the FRP member;
- one shank entering concrete along `-N_W`;
- specified embedment;
- no fictitious far-side wall hardware;
- no concrete cone/capacity visualization.

## 23. Member material axes

Use the frozen backend-authoritative profile region bases.

Channel:

- web;
- top flange;
- bottom flange.

Angle:

- both legs.

Every physical FRP region receives correct region-embedded LW/CW/TT.

Concrete receives no FRP material axes.

## 24. Three-component force contract

No user moments.

Use member/side-lap frame:

### Axial force

`P_axial` along `L_LAP`.

### Major shear

`V_major` along `S_LAP`.

### Minor shear

`V_minor` along `N_W`.

Complete force:

`F = (P_axial, V_major, V_minor)`

in `(L_LAP,S_LAP,N_W)`.

## 25. Force sign convention

- Axial `+`: along `+L_LAP`, toward/through the member portion continuing beyond the wall free end;
- Major `+`: along `+S_LAP`;
- Minor `+`: along `+N_W`, pull away from concrete;
- Minor `-`: toward concrete.

The UI/axis legend shall display this convention.

## 26. User moment

User free moment remains exactly zero.

No moment input fields.

Any nonzero user moment in API payload is rejected.

This remains a shear-category connection.

## 27. Canonical member-end action reference

The backend derives the action reference from the actual selected profile at the concrete wall free-end plane.

The reference corresponds to the connected member's authoritative section reference/centroid under the shared profile geometry architecture.

No frontend reference calculation.

The reference point is returned explicitly.

## 28. Anchor-group reference

The anchor-group centroid is the normal connection-demand / external-handoff reference.

The backend translates the complete member-end wrench to the actual anchor-group centroid.

With zero user free moment:

`M_anchor = (r_member - r_anchor) × F`.

All generated moments are retained.

## 29. Eccentricity sources

The exact wall/anchor-group wrench may include moments caused by:

- longitudinal distance from the wall free end/member reference to the anchor-group centroid;
- transverse profile-centroid offset;
- profile centroid distance from the concrete contact plane;
- current profile geometry/orientation.

Do not suppress these moments.

Do not simplify Angle/Channel reference geometry to a generic plate.

## 30. In-plane anchor-group demand

Axial force `L_LAP` and Major shear `S_LAP` lie in the selected lap surface.

The accepted Stage 2.5A group-demand mechanics may resolve the in-plane force components and the in-plane-group normal moment component where current applicability holds.

Use actual anchor coordinates and actual backend reference.

No new distribution equation.

## 31. FRP resistance handoff

Where existing Stage 2.5B / Stage 2.6 / accepted geometry methods apply, Stage 3.5B may evaluate:

- FRP pin bearing;
- supported shear-out;
- supported net tension;
- supported block shear;
- other already accepted FRP local layer checks.

The external anchor is treated as the physical fastener/load-transfer point for FRP local demand only.

No anchor steel/concrete capacity.

## 32. Minor-shear / wall-normal action

Minor shear acts along the external anchor axes and through the FRP thickness direction.

Retain exact normal action.

Do not calculate:

- FRP pull-through resistance;
- anchor axial tension capacity;
- prying;
- wall-normal contact/anchor partition.

When `V_minor != 0`, require:

- `DIRECT_SIDE_LAP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`;
- `DIRECT_SIDE_LAP_FRP_PULL_THROUGH = NOT_EVALUATED`;
- `WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

## 33. Out-of-plane transfer moments

Any generated wall/anchor-group moments about axes lying in the wall plane may require:

- anchor tension/compression distribution;
- FRP local bending;
- member-wall prying/contact.

These are retained in the external handoff.

Stage 3.5B does not invent corresponding FRP/global resistance.

Required when such unsupported components are nonzero:

`DIRECT_SIDE_LAP_OUT_OF_PLANE_RESPONSE = NOT_EVALUATED`.

## 34. Connection qualification

Always retain:

`DIRECT_SIDE_LAP_CONNECTION_QUALIFICATION = NOT_EVALUATED`.

This direct FRP-to-concrete connection is not assigned an ordinary whole-connection PASS under RC1.

Supported local FRP failure retains overall `FAIL` precedence.

## 35. External concrete/anchor limitations

Always:

- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

No concrete or anchor capacities.

## 36. External anchor-design handoff

Return one backend-authored immutable handoff.

At minimum include:

### Identity

- schema/version;
- load case;
- factored status;
- units;
- input/geometry/application fingerprints.

### Side-lap frame

- `L_LAP`, `S_LAP`, `N_W`;
- wall free-end origin;
- wall dimensions;
- side-lap length;
- member projection.

### Member action

- selected profile family;
- selected physical connection surface;
- member action reference;
- force vector;
- zero user moment.

### Anchor group

- stable group ID;
- centroid;
- full translated force/moment wrench;
- anchor coordinates;
- nominal diameter;
- hole diameter;
- specified embedment;
- geometric concrete edge distances;
- FRP member-end/free-edge clearances;
- overlap-boundary distances.

### Limitations

All external/not-evaluated statuses.

No camera/presentation state.

## 37. Handoff export

Provide deterministic:

- Copy JSON;
- Download JSON.

Frontend does not calculate or modify engineering values.

Full precision.

## 38. Preview path

Preview:

- strict input validation;
- wall/member/overlap geometry;
- anchor layout;
- overlap containment;
- member/wall interference;
- action reference;
- exact anchor-group wrench;
- supported in-plane demand where applicable;
- Minor normal action;
- local FRP applicability traces;
- external handoff;
- visualization/status;
- zero resistance-engine calls.

## 39. Explicit design path

`Run Design Check`:

- current accepted preview only;
- existing supported FRP local resistance checks;
- no anchor/concrete capacity;
- no pull-through/prying/out-of-plane resistance invention;
- limitations retained.

## 40. API strictness

Current contract:

`3.5B-RC1`.

Strictly accept:

- profile family `ANGLE` or `CHANNEL`;
- family-specific dimensions;
- Angle selected leg/surface;
- Channel web selected surface only;
- side-lap length;
- member projection;
- wall dimensions;
- anchor pattern/position;
- external anchor geometry;
- Axial/Major/Minor forces;
- zero user moment.

Reject:

- Channel flange-to-wall;
- unsupported profile;
- negative/zero lap;
- nonpositive projection;
- invalid anchor group;
- nonzero user moments;
- extra fields;
- client IDs/fingerprints;
- unknown contract versions.

## 41. Frontend workspace

Add under Brace/beam connections:

`Brace/beam connection — Direct side-lap Angle/Channel to concrete wall`

Normal sections:

1. General / Case;
2. Connected Member;
3. Concrete Wall;
4. Side-Lap Geometry;
5. Direct Wall Anchor Group;
6. External Anchor Geometry;
7. Loads;
8. Wall / Anchor Design Handoff;
9. Materials / Fasteners;
10. Geometry / Design Results;
11. Advanced / Diagnostics.

## 42. Connected-member UI

Profile family options exactly:

- Channel;
- Angle.

Default:

Channel.

Channel UI:

- depth;
- flange width;
- web thickness;
- flange thickness;
- web contact face/orientation;
- no flange contact option.

Angle UI:

- Leg Y;
- Leg Z;
- thickness;
- selected leg;
- accepted selected outer face/orientation.

## 43. Side-lap UI

Expose:

- Side-lap length;
- Member projection beyond wall;
- Anchor group distance behind wall free end;
- Center anchor group in overlap.

Show a simple computed summary:

- wall free end at 0;
- overlap start coordinate;
- anchor group coordinate;
- minimum anchor distance to member overlap ends.

Backend values only.

## 44. Anchor editor

Expose:

- rows;
- anchors per row;
- pitch;
- gauge;
- group transverse offset;
- distance behind wall free end;
- Center action.

Default `2 × 1`.

If one anchor per row, gauge is geometrically inactive.

No hidden anchors.

## 45. Loads UI

Expose:

- Axial force;
- Major shear;
- Minor shear.

No moment inputs.

Show side-lap frame directions.

Default:

- Axial `0`;
- Major `-4 kip`;
- Minor `0`.

## 46. Visualization

Render actual:

- finite concrete wall with real free end;
- selected Channel or Angle;
- member start at overlap start;
- member continuing beyond wall free end;
- exact overlap region;
- direct external anchors;
- anchor embedment shanks;
- action/reference overlays;
- side-lap frame;
- material axes on FRP member.

No clip angle/Tee/secondary connector.

No concrete FRP material axes.

## 47. Critical visual geometry

The default 12-in side lap shall visibly show:

- 12 in of Channel/Angle against the concrete wall before the wall stops;
- the member continuing beyond the wall free end;
- anchors located inside that overlap.

Changing side lap from 12 to 18 in shall visibly move the connected-member start farther behind the wall free end while the anchor group remains fixed unless the user explicitly centers it.

## 48. Controlled default fixture

### Concrete wall

- run length behind free end: `48 in`;
- transverse width: `48 in`;
- thickness: `8 in`;
- wall free end: `L=0`.

### Connected member

Default Channel:

- depth `8 in`;
- flange width `4 in`;
- web thickness `0.5 in`;
- flange thickness `0.5 in`;
- web against concrete.

Side-lap length:

`12 in`.

Projection beyond wall:

`16 in`.

### Anchor group

- `2 × 1`;
- pitch `4 in`;
- centroid distance behind free end `6 in`;
- transverse offset `0`;
- anchors at `L=-8` and `L=-4`.

### External anchor

- diameter `0.5 in`;
- hole `0.563 in`;
- embedment `4 in`.

### Loads

- Axial `0 kip`;
- Major shear `-4 kip`;
- Minor shear `0 kip`.

## 49. Controlled golden cases

At minimum:

G1. Default Channel web-to-wall 12-in side lap geometry.
G2. Wall stops at `L=0`; Channel continues beyond wall.
G3. Default anchors at `L=-8,-4` inside 12-in overlap.
G4. Increase lap to 18 in: anchor coordinates unchanged.
G5. Reduce lap below 8 in: far anchor outside overlap -> invalid.
G6. Explicit Center on 18-in lap moves group centroid to `L=-9`.
G7. Center action only; changing lap does not auto-center.
G8. Channel web contact accepted.
G9. Channel flange-to-wall rejected.
G10. Channel flanges remain outside concrete.
G11. Angle selected-leg contact accepted.
G12. Angle perpendicular leg/heel remains outside concrete.
G13. Invalid Angle orientation embedding free leg -> invalid.
G14. Direct anchor path through Channel web.
G15. Direct anchor path through selected Angle leg.
G16. No far-side concrete hardware.
G17. Three force inputs/no moment.
G18. Action reference derived from current profile at wall free end.
G19. Exact full anchor-group wrench equals translated member wrench.
G20. Major+Axial in-plane nominal demand equilibrium where applicable.
G21. Minor shear retained as bolt-axis/normal action.
G22. Minor shear pull-through/anchor/contact limitations.
G23. Generated out-of-plane moments retained in external handoff.
G24. Anchor center outside overlap invalid even if inside concrete.
G25. FRP complete-hole containment invalid case.
G26. Concrete finite-face containment invalid case.
G27. Embedment > wall thickness invalid.
G28. Side-lap material-axis coverage.
G29. Concrete no FRP material axes.
G30. Preview zero resistance.
G31. Supported FRP numerical failure governs FAIL.
G32. Valid geometry + external/qualification limitations -> NOT_EVALUATED.
G33. Deterministic external handoff/export.
G34. Exact U.S./SI representative Channel case.
G35. Angle/Channel selector preserves wall/lap/anchor/load state.
G36. Frozen Stage 3.5A/R1/R2 regressions exact.
G37. Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee regressions exact.

## 50. U.S./SI equivalence

At minimum:

- `48 in = 1219.2 mm`;
- `18 in = 457.2 mm`;
- `16 in = 406.4 mm`;
- `12 in = 304.8 mm`;
- `8 in = 203.2 mm`;
- `6 in = 152.4 mm`;
- `4 in = 101.6 mm`;
- `0.5 in = 12.7 mm`;
- `0.563 in = 14.3002 mm`;
- `4 kip = 17.792886461042 kN`.

Equivalent geometry, overlap boundaries, anchor coordinates, force vectors, wrenches, supported demands, handoff, and fingerprints shall match.

## 51. Fingerprints

Add deterministic identities for:

- input;
- profile family/geometry/surface;
- wall geometry/free end;
- side-lap length;
- member projection;
- anchor layout/position;
- anchor geometry;
- member action/reference;
- anchor-group wrench;
- external handoff;
- preview/design/application.

Presentation excluded.

No historical/frozen fingerprint changes.

## 52. Deliberate exclusions

Stage 3.5B does not authorize:

- Channel flange-to-wall;
- Flat Plate/W-I/RHS/SRS connected profiles;
- clip angles or Tee connector;
- adhesive/epoxy;
- welds;
- through-wall bolts;
- concrete/anchor capacity;
- FRP pull-through capacity;
- anchor axial capacity;
- prying;
- wall-normal contact partition;
- user-applied moments;
- moment-resisting connection;
- automatic anchor repositioning;
- Stage 3.5C/base connection.

## 53. Acceptance boundary

Stage 3.5B is accepted only if:

- Channel web-only side lap is enforced;
- Angle selected-leg side lap is correct;
- wall has a real free end;
- member continues beyond wall;
- side-lap length visibly/physically controls overlap;
- changing lap never silently moves anchors;
- anchors are valid only inside real overlap;
- exact action reference/wrench translation is retained;
- Major/Minor/Axial force contract works;
- no user moment;
- no concrete/anchor capacity;
- external handoff is complete;
- local FRP checks use only accepted methods;
- historical Stage 3.5 and frozen families remain exact;
- full local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
