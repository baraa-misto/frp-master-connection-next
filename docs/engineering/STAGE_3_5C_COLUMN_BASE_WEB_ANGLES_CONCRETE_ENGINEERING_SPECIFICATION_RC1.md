# FRP Master Connection — Stage 3.5C FRP W/I Column Base Using Single/Double Web Angles to Concrete — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.5C adds one new Shear Connections product:

**FRP W/I Column -> Single or Symmetric Double FRP Web Base Angles -> Concrete Base**

The connection transfers:

- axial compression;
- web-plane horizontal shear;
- web-normal horizontal shear.

No user-applied moment is accepted.

No axial uplift/tension is accepted in RC1.

No concrete or anchor-system capacity is calculated.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `f72663a54700d84ac03a06e82a0e5fd39b4a0120`;
- subject:
  `fix: correct side-lap presentation and axes`;
- commit count: `85`;
- clean worktree/index.

Expected Stage 3.5B-R1 hosted CI:

- GitHub Actions run #80;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

The owner directly accepted Stage 3.5B-R1 visual behavior on 2026-08-29. If repository governance still records Stage 3.5B-R1 visual acceptance as pending, update that status as governance-only evidence before Stage 3.5C production mutation. Do not alter Stage 3.5B-R1 production behavior or fingerprints.

Expected immutable freeze targets:

- Stage 2.3:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- Stage 3.4:
  `2303ec713d6d038b935e076b909c3b639ced0e09`.

## 3. Source boundary

ASCE/SEI 74-23 Section 8.4 requires column bases to transfer column forces and moments to footings/foundations under the referenced concrete/steel-base framework.

Commentary C8.4 recognizes column-base detailing with web/flange clip elements and states that anchor-system design is outside the standard's scope.

Stage 3.5C therefore:

- models the FRP column/web/base-angle load path;
- uses accepted Chapter 8 FRP local bolted checks where applicable;
- exports concrete/base/anchor demands;
- does not claim concrete/anchor capacity;
- does not invent full FRP base-angle body/heel capacity where the standard does not provide a directly applicable method.

## 4. Product identity

New selector group under Shear Connections:

`Column connections`

New selector label:

`Column connection — Single/double web base angles to concrete`

Suggested routes:

- `/api/v1/calculations/column-base-web-angles/preview`;
- `/api/v1/calculations/column-base-web-angles/design-check`.

Current contract:

`3.5C-RC1`.

Existing connection selector identities remain unchanged.

## 5. Column-base frame

Define one right-handed frame:

- `S_C`: horizontal in the column-web plane;
- `T_C`: horizontal normal to the web;
- `L_C`: column longitudinal direction, positive upward.

Require:

`S_C × T_C = L_C`.

Concrete top surface:

`L_C = 0`.

Concrete occupies:

`L_C <= 0`.

Column extends:

`L_C >= 0`.

## 6. W/I column

Only connected column profile in RC1:

`WIDE_FLANGE_I`.

Controlled default:

- depth along `S_C`: `10 in`;
- flange width along `T_C`: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- displayed/member height: `24 in`.

The column is centered at:

`S_C = 0`, `T_C = 0`.

The column web plane is:

`L_C-S_C`.

Web normal:

`±T_C`.

## 7. Column material basis

The column pultrusion/member longitudinal axis is `L_C`.

For the column web:

- `LW` is parallel to `L_C`;
- `CW` lies in the web plane, parallel to the accepted transverse web direction;
- `TT` is normal to the web.

For pure axial compression:

`-L_C` is the web's longitudinal material direction.

The column-web local connection shall therefore use existing longitudinal directional properties where the accepted check is applicable.

## 8. Concrete base geometry

Finite concrete prism.

Controlled default:

- dimension along `S_C`: `36 in`;
- dimension along `T_C`: `36 in`;
- thickness/depth along `-L_C`: `12 in`;
- top surface at `L_C=0`.

Concrete has no FRP LW/CW/TT material axes.

Expose the column-base frame separately.

## 9. Assembly options

Exactly:

1. `SINGLE_BASE_ANGLE`
2. `SYMMETRIC_DOUBLE_BASE_ANGLES`

Default:

`SYMMETRIC_DOUBLE_BASE_ANGLES`.

## 10. Single-angle side

For `SINGLE_BASE_ANGLE`, user selects:

- positive web face `+T_C`; or
- negative web face `-T_C`.

The angle lies outside the selected web face.

No angle embedding into the web/flanges.

The selected angle system receives 100% of the connection design demand.

## 11. Symmetric double-angle topology

One positive angle is placed on the `+T_C` web face.

One negative angle is its exact mirror on the `-T_C` web face.

Require identical:

- angle geometry;
- materials;
- web-bolt pattern;
- base-anchor pattern;
- base elevation;
- longitudinal `S_C` position.

No unequal pair input in RC1.

## 12. Base-angle geometry

Use the accepted FRP Angle geometry authority with a column-base orientation.

Controlled default each angle:

- vertical leg height: `6 in`;
- horizontal leg width: `6 in`;
- thickness: `0.5 in`;
- angle length along `S_C`: `6 in`;
- centered along `S_C`.

The angle pultrusion direction / `LW` is along `S_C`.

## 13. Angle vertical-leg material basis

For each angle vertical leg:

- `LW` parallel to `S_C`;
- `CW` parallel to `L_C` with the exact controlled sign;
- `TT` normal to the vertical leg.

Therefore pure column compression `-L_C` is a **CW-direction** load in the angle vertical leg.

This is a controlling owner requirement.

## 14. Angle horizontal-leg material basis

For each horizontal leg:

- `LW` remains parallel to `S_C`;
- `CW` lies horizontally along the leg width in `±T_C`;
- `TT` is normal to the horizontal leg, parallel to `±L_C`.

Region-specific material axes remain backend authoritative.

## 15. Column-end contact

No artificial column-bottom clearance is introduced.

The column end is geometrically located at the concrete top/base plane under the current product geometry.

Stage 3.5C does not calculate stiffness-based compression sharing between:

- direct column-end bearing;
- base-angle bearing.

Required:

`COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

The component-design demand policy in Section 28 remains controlling and does not duplicate the physical foundation reaction.

## 16. Column-web-to-angle bolt group

### Single angle

Physical path:

`Base Angle Vertical Leg -> Column Web`.

### Double angles

One common physical through-bolt group:

`Positive Angle Vertical Leg -> Column Web -> Negative Angle Vertical Leg`.

Default group:

- rows along `L_C`: `2`;
- bolts per row along `S_C`: `2`;
- pitch: `3 in`;
- gauge: `2 in`;
- centroid height above base: `3 in`;
- nominal bolt diameter: `0.5 in`;
- hole diameter: `0.563 in`;
- accepted 316SS ASTM F593 fastener source.

## 17. Single-angle web-bolt hardware

For the single-angle option:

- one physical bolt/shank per axis;
- angle vertical leg and column web are the two FRP layers;
- head/washer and nut/washer external to the two-layer stack;
- no duplicate bolt identity.

Use the existing single-lap resistance applicability/factors where already authorized.

## 18. Double-angle common-bolt hardware

For the double-angle option:

- one physical bolt/shank per axis;
- positive angle / column web / negative angle three-layer path;
- head/nut outside the outer angle faces;
- no internal hardware;
- exact accepted paired-angle common-group layer provenance.

## 19. Base-anchor groups

### Single angle

One external anchor group in the angle horizontal leg.

### Double angles

Two separate mirrored external anchor groups:

- `POSITIVE_BASE_ANCHOR_GROUP`;
- `NEGATIVE_BASE_ANCHOR_GROUP`.

The two double-angle groups are locked identical/mirrored in RC1.

## 20. Default anchor-group geometry

Each angle's horizontal leg extends outward from the column web.

Default anchor-group centroid:

- positive side:
  `(S_C,T_C,L_C) = (0,+3.25,0) in`;
- negative side:
  `(0,-3.25,0) in`.

Default pattern each angle:

- rows along `S_C`: `2`;
- anchors per row across horizontal leg: `1`;
- pitch: `3 in`;
- transverse gauge inactive for one column;
- anchor coordinates:
  - positive: `S=±1.5 in`, `T=+3.25 in`;
  - negative: `S=±1.5 in`, `T=-3.25 in`;
- nominal anchor diameter: `0.5 in`;
- FRP hole diameter: `0.563 in`;
- specified embedment: `4 in`.

## 21. Anchor presentation

Each external anchor is represented as:

- exterior nut/washer above/on the horizontal angle leg;
- one shank into concrete along `-L_C`;
- specified embedment;
- no fictitious far-side concrete hardware.

Concrete/anchor capacity is not calculated.

## 22. Angle bearing footprint

Return the exact horizontal-leg contact polygon/footprint for each angle on the concrete top surface.

The footprint is geometric coordination data.

Do not calculate:

- concrete bearing capacity;
- grout capacity;
- bearing pressure resistance.

## 23. User actions

Normal Stage 3.5C inputs:

### Axial compression

`P_u >= 0`.

Engineering direction:

`-L_C`.

### Web-plane shear

`V_S`, signed along `S_C`.

### Web-normal shear

`V_T`, signed along `T_C`.

No user-applied moments.

Complete force in `(S_C,T_C,L_C)`:

`F = (V_S, V_T, -P_u)`.

## 24. Default action

Controlled default:

- axial compression `P_u = 20 kip`;
- web-plane shear `V_S = +4 kip`;
- web-normal shear `V_T = 0 kip`;
- user moment `(0,0,0)`.

## 25. Axial tension / uplift

RC1 does not accept axial tension/uplift.

Negative compression magnitude or a force component acting in `+L_C` is rejected.

A later stage may add uplift under separate authority.

## 26. User moments

No moment input fields.

Any nonzero user free moment is rejected.

Generated moments from reference translation remain mandatory.

## 27. Column action reference

The backend-authoritative column action reference is the current column-web group centroid.

Controlled default:

`r_C = (0,0,4) in`

in `(S_C,T_C,L_C)`.

If actual group geometry changes, the backend updates the reference consistently.

No frontend reference calculation.

## 28. Serial component-design demand policy

This is controlling.

The physical column action enters foundation equilibrium once.

For component design:

### Column web local transfer

Demand assigned:

- axial compression: `100% P_u`;
- web-plane shear: `100% V_S`;
- web-normal action: `100% V_T`.

### Base-angle system

Demand assigned:

- axial compression: `100% P_u` at system level;
- supported shears: `100%` at system level.

These component-design demands are **not summed** to form a foundation reaction.

## 29. Single-angle branch demand

Single-angle system:

`P_angle = P_u`.

The one angle receives the full assigned system action.

No symmetry reduction.

Its web-bolt/vertical-leg local checks use the full applicable action.

## 30. Double-angle system demand

Double-angle pair system:

`P_pair = P_u`.

When exact symmetry eligibility in Section 31 passes:

`P_positive = P_negative = P_u/2`.

Similarly for the symmetry-eligible web-plane shear:

`V_S,+ = V_S,- = V_S/2`.

The pair system is still checked as a 100% `P_u` transfer system.

## 31. Double-angle symmetry eligibility

Exact half sharing is authorized only when:

- angle geometry exact mirror;
- web group centered;
- base anchor groups exact mirrors;
- materials/sources identical;
- column centered;
- `V_T = 0`.

The eligible action plane is the column web / mirror plane:

`S_C-L_C`.

No tolerance-based proof.

## 32. Web-normal shear

`V_T` acts along the column web-bolt axes.

For either assembly:

- retain exact normal action;
- do not generate bolt-axis tension resistance;
- do not generate prying.

Required when `V_T != 0`:

`COMMON_WEB_GROUP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

For double angles also:

`WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION = NOT_EVALUATED`.

The combined foundation handoff remains exact.

## 33. Common web-group demand

For the in-plane vector:

`F_in_plane = (V_S, -P_u)` in the web plane,

call the accepted Stage 2.5A demand engine exactly once for the physical web-bolt group.

No new demand equation.

For the default concentric `2 × 2` group:

- physical bolts: `4`;
- direct equal share before any accepted eccentric correction.

## 34. Double-angle layer allocation

Reuse the accepted three-layer common-group provenance.

For any symmetry-eligible per-bolt in-plane demand `Q_i`:

- positive angle vertical leg receives `0.5 Q_i`;
- column web receives `1.0 Q_i`;
- negative angle vertical leg receives `0.5 Q_i`.

Thus:

- the web local connection transfers the whole system demand;
- the two angle branches sum to the whole system demand.

## 35. Single-angle layer allocation

For the two-layer single-angle group:

- column web receives `1.0 Q_i`;
- single angle vertical leg receives `1.0 Q_i`.

Both are local connection layers in series.

## 36. Material direction — pure axial compression

For pure `P_u`:

### Column web

Connection force direction is parallel to web `LW`.

Existing directional pin-bearing classification shall select the longitudinal bearing property where applicable.

### Angle vertical leg

Connection force direction is parallel to angle-leg `CW` and perpendicular to angle `LW`.

Existing directional pin-bearing classification shall select the transverse bearing property where applicable.

Automated tests shall prove the same physical force is classified differently by the two actual material bases.

## 37. Material direction — pure web-plane shear

For pure `V_S`:

### Column web

The action is transverse to web `LW`.

### Angle vertical leg

The action is parallel to angle `LW`.

The accepted direction-aware pin-bearing/FRP handoff shall use the actual local material direction for each layer.

## 38. Combined in-plane direction

For simultaneous `P_u` and `V_S`, use the actual resultant force direction relative to each region's own `LW/CW` basis.

Do not reuse the column-web angle for the angle layer or vice versa.

## 39. Column-web local FRP checks

Use existing accepted local bolted-connection methods where applicable, including:

- metallic bolt shear where applicable;
- FRP pin bearing;
- supported shear-out;
- supported net/block-shear modes where their current force/sign/geometry applicability requires them.

The column-web layer demand uses 100% of the physical group in-plane demand.

Stage 3.5C does not claim a separate web-only global column compression-member capacity.

## 40. Angle vertical-leg local FRP checks

Use existing accepted local bolted-connection methods where applicable.

For pure axial compression, use the angle vertical leg's CW/transverse directional bearing classification.

For double angles, each angle layer uses its proven branch share.

For single angle, the angle layer uses the full system demand.

## 41. Angle body / heel / horizontal-leg limitation

The full load path from vertical leg through the FRP angle body/heel into the horizontal leg is not fully covered by the existing bolted local checks.

Always retain:

`BASE_ANGLE_CW_BODY_AND_HEEL_COMPRESSION_TRANSFER = NOT_EVALUATED`.

Also retain where applicable:

`BASE_ANGLE_HORIZONTAL_LEG_BENDING_AND_PRYING = NOT_EVALUATED`.

Do not fabricate an FRP shape transverse-compression capacity from a plate property.

## 42. Concrete bearing / column-end partition

Always:

- `BASE_ANGLE_TO_CONCRETE_BEARING_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

The internal component-design envelope still assigns full `P_u` to the angle system.

## 43. Anchor-system limitations

Always:

- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

No concrete/anchor capacities.

## 44. Combined foundation reaction

Define one common base reference:

`r_B = (0,0,0)`.

The physical foundation reaction handoff uses the column action **once**:

`F_B = F_column`.

With zero user free moment:

`M_B = (r_C-r_B) × F_column`.

For the controlled default:

`F_B = (4,0,-20) kip`.

`M_B = (0,16,0) kip-in`.

Do not add web-design demand and angle-system-design demand together.

## 45. Double-angle branch anchor wrenches

For the controlled default and exact symmetric pair:

Branch force each:

`F_± = (2,0,-10) kip`.

Positive anchor-group centroid:

`r_+ = (0,+3.25,0) in`.

Negative:

`r_- = (0,-3.25,0) in`.

Expected branch wrenches at their own anchor-group centroids:

Positive:

`M_+ = (32.5,8,6.5) kip-in`.

Negative:

`M_- = (-32.5,8,-6.5) kip-in`.

When shifted to the common base reference, the branch wrenches recover exactly:

`F_B = (4,0,-20) kip`.

`M_B = (0,16,0) kip-in`.

These are external anchor/bearing handoff wrenches, not anchor capacities.

## 46. Single-angle anchor wrench

For the controlled default force assigned to a single positive-side angle:

`F_single = (4,0,-20) kip`.

At:

`r_single = (0,+3.25,0) in`

the expected exact translated wrench is:

`M_single = (65,16,13) kip-in`.

When shifted to the base reference it recovers:

`M_B = (0,16,0) kip-in`.

The large eccentric branch moments are retained.

## 47. Angle-system compression-demand trace

Return explicit demand provenance:

### Single

- system axial compression demand: `P_u`;
- angle branch demand: `P_u`;
- material transfer direction: `CW`.

### Double

- system axial compression demand: `P_u`;
- positive branch: `P_u/2` after symmetry;
- negative branch: `P_u/2` after symmetry;
- each vertical-leg material transfer direction: `CW`.

No utilization is issued for the unsupported body/heel transfer.

## 48. Column-web axial-demand trace

Return explicit:

- local transfer axial demand: `P_u`;
- demand fraction: `1.0`;
- material transfer direction: `LW`;
- supported local connection checks/results.

This demand is not reduced because the angle system is also checked.

## 49. External concrete/base handoff

Return immutable backend-authored handoff containing:

### Identity

- schema/version;
- units;
- load case/factored status;
- fingerprints/method versions.

### Base frame / concrete

- `S_C,T_C,L_C`;
- base reference;
- concrete dimensions/top plane.

### Column

- W/I geometry;
- web physical region;
- column action reference;
- input forces;
- zero user moment;
- column-end contact footprint.

### Web connection

- assembly type;
- web-bolt coordinates/axes;
- full system group demand;
- web local demand fraction 1.0;
- angle layer fractions.

### Base angles

- geometry/material bases;
- bearing footprints;
- system compression demand;
- branch demands where authorized.

### Anchors

- group IDs/centroids;
- coordinates;
- exact group wrenches where branch allocation is authorized;
- diameter/hole/embedment;
- geometric edge distances.

### Foundation

- combined base reaction wrench once.

### Limitations

All NOT_EVALUATED / EXTERNAL_DESIGN_REQUIRED states.

## 50. External handoff mode with web-normal shear

When `V_T != 0` for the double-angle option:

- do not fabricate full positive/negative branch wrenches;
- retain full combined foundation wrench;
- retain both angle/anchor geometries and owner IDs;
- return branch allocation limitation;
- external software receives the complete layout/action.

For single angle, the full physical action remains assigned to the one system, while bolt-axis/prying response remains NOT_EVALUATED.

## 51. Handoff export

Provide deterministic:

- Copy JSON;
- Download JSON.

No frontend engineering calculations.

Full precision.

## 52. Preview path

Preview shall:

- validate strict geometry/action inputs;
- construct column/base/angle(s);
- resolve web-bolt group;
- resolve anchor groups;
- validate containment/interference;
- compute material-direction classifications;
- compute supported in-plane web-group demand;
- retain `V_T` normal action;
- prove double-angle symmetry where applicable;
- produce component design-demand traces;
- compute exact external branch/base wrenches where authorized;
- build external handoff;
- return visualization/status.

Preview executes zero resistance-engine calls.

## 53. Explicit design path

`Run Design Check` shall:

- consume current accepted preview;
- execute existing supported local FRP/metallic web-group checks;
- preserve full demand provenance;
- issue no angle-body/heel capacity;
- issue no concrete bearing capacity;
- issue no anchor capacity;
- retain all limitations.

## 54. API strictness

Current contract:

`3.5C-RC1`.

Accept:

- W/I column dimensions;
- assembly single/double;
- single side where applicable;
- base-angle geometry;
- web-bolt group;
- base-anchor pattern;
- concrete geometry;
- external anchor geometry;
- axial compression magnitude;
- web-plane shear;
- web-normal shear;
- zero user moment.

Reject:

- axial tension/uplift;
- user moments;
- unequal double angles;
- unequal double anchor groups;
- unsupported column profile;
- invalid geometry;
- extra fields;
- client IDs/fingerprints;
- unknown contract version.

## 55. Frontend selector/workspace

Under Shear Connections add group:

`Column connections`.

Add:

`Column connection — Single/double web base angles to concrete`.

Use shared workspace/viewer conventions.

Normal sections:

1. General / Case;
2. FRP Column;
3. Concrete Base;
4. Base-Angle Assembly;
5. Column Web ↔ Base Angle(s);
6. Base Anchor Group(s);
7. External Anchor Geometry;
8. Loads;
9. Component Transfer Trace;
10. Concrete / Anchor Handoff;
11. Materials / Fasteners;
12. Geometry / Design Results;
13. Advanced / Diagnostics.

## 56. Load UI

Expose:

- Axial compression;
- Web-plane shear;
- Web-normal shear.

No moment inputs.

Axial compression is entered as a nonnegative magnitude.

Show direction mapping:

- compression -> `-L_C`;
- web-plane shear -> `S_C`;
- web-normal shear -> `T_C`.

## 57. Component transfer UI

Display distinctly:

### Column web

`100% axial demand — LW direction`

### Base-angle system

`100% axial demand — CW transfer direction`

For double angles:

`System = 100% P_u`

and:

`Angle + = 50%`, `Angle - = 50%`

only after symmetry proof.

Do not visually imply the foundation reaction is doubled.

## 58. Visualization

Render actual:

- finite concrete base;
- vertical W/I column;
- column web/flanges;
- single or mirrored double base angles;
- vertical legs bolted to column web;
- horizontal legs bearing on concrete;
- web bolts;
- external anchors/embedment shanks;
- column/base action references;
- force arrows;
- base frame;
- FRP material axes.

No fictitious far-side concrete anchor hardware.

## 59. Material-axis visualization

Show:

### Column

- web;
- both flanges.

### Each base angle

- vertical leg;
- horizontal leg.

The visual material directions shall make the owner-required distinction evident:

- column web axial compression parallel to LW;
- base-angle vertical-leg compression parallel to CW.

Concrete has no FRP axes.

## 60. Status aggregation

Required precedence:

1. invalid geometry/input -> invalid/rejected;
2. supported numerical FRP/bolt failure -> `FAIL`;
3. otherwise unsupported/external base-angle/concrete/anchor checks -> `NOT_EVALUATED` / external design required;
4. ordinary whole-connection PASS prohibited.

## 61. Controlled default fixture

### Column

- W/I `10 × 8`;
- web `0.5`;
- flange `0.5`;
- displayed height `24`.

### Concrete base

- `36 × 36 × 12 in`.

### Assembly

- symmetric double angles.

### Each angle

- vertical leg `6 in`;
- horizontal leg `6 in`;
- thickness `0.5 in`;
- length along `S_C` `6 in`.

### Web group

- `2 × 2`;
- pitch `3 in`;
- gauge `2 in`;
- centroid height `3 in`;
- bolt `0.5 in`;
- hole `0.563 in`.

### Each anchor group

- `2 × 1`;
- pitch `3 in`;
- centroid `T=±3.25 in`;
- anchor coordinates `S=±1.5 in`;
- anchor `0.5 in`;
- hole `0.563 in`;
- embedment `4 in`.

### Loads

- axial compression `20 kip`;
- web-plane shear `+4 kip`;
- web-normal shear `0`.

### Column action reference

- `(S,T,L)=(0,0,4) in`.

### Base reference

- `(0,0,0)`.

## 62. Controlled default expected equilibrium

Combined foundation:

- `F=(4,0,-20) kip`;
- `M=(0,16,0) kip-in`.

Double-angle branch forces:

- positive `(2,0,-10) kip`;
- negative `(2,0,-10) kip`.

Positive anchor-group moment:

- `(32.5,8,6.5) kip-in`.

Negative:

- `(-32.5,8,-6.5) kip-in`.

Shifted branch sum at base:

- exact combined force `(4,0,-20)`;
- exact combined moment `(0,16,0)`.

## 63. Controlled directional expectations

### Pure axial compression

Column web:

- demand `20 kip`;
- material direction `LW`;
- directional pin bearing uses longitudinal classification where applicable.

Double-angle pair:

- system demand `20 kip`;
- each angle `10 kip`;
- vertical-leg material direction `CW`;
- directional pin bearing uses transverse classification where applicable.

### Pure web-plane shear

Column web:

- action direction transverse to web LW.

Angle vertical leg:

- action direction parallel to angle LW.

Automated tests shall prove both.

## 64. Required golden cases

At minimum:

G1. Default double-angle geometry.
G2. Single positive angle geometry.
G3. Single negative angle mirror.
G4. Double-angle exact mirror.
G5. Column web pure compression demand = 100% Pu, direction LW.
G6. Double-angle system pure compression demand = 100% Pu.
G7. Double-angle branch pure compression = Pu/2 each.
G8. Single-angle pure compression = Pu.
G9. Same physical pure compression classified web LW vs angle CW.
G10. Pure web-plane shear classified web CW vs angle LW.
G11. Combined P+V_S uses actual per-layer bearing angles.
G12. Default common 2×2 group demand/equilibrium.
G13. Double common-layer allocations `0.5 / 1.0 / 0.5`.
G14. Single common-layer allocations `1.0 / 1.0`.
G15. Web-normal shear retained as bolt-axis action.
G16. Double V_T nonzero branch allocation NOT_EVALUATED.
G17. No generated bolt tension/prying.
G18. Base-angle body/heel transfer NOT_EVALUATED.
G19. Horizontal-leg bearing capacity external.
G20. Column-end vs angle-bearing partition external.
G21. Default combined foundation wrench.
G22. Default positive branch anchor wrench.
G23. Default negative branch anchor wrench.
G24. Default double branch sum recovers base wrench.
G25. Single positive anchor wrench exact.
G26. Single anchor wrench shifted to base recovers base wrench.
G27. No doubled foundation reaction despite duplicate component design demands.
G28. Concrete/anchor capacities absent.
G29. Angle bearing footprints exported.
G30. External handoff deterministic.
G31. Axial tension/uplift rejected.
G32. User moment rejected.
G33. Material axes show web Pu || LW.
G34. Material axes show angle vertical-leg Pu || CW.
G35. Double-angle symmetry invalid case fail-closed.
G36. Anchor/hole containment invalid case.
G37. Web-bolt containment/interference invalid case.
G38. Preview zero resistance.
G39. Supported local FRP failure governs FAIL.
G40. Valid geometry with external/unsupported checks -> NOT_EVALUATED.
G41. Exact U.S./SI default equivalence.
G42. Historical Stage 3.5A/R1/R2/B/R1 regressions exact.
G43. Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee regressions exact.

## 65. U.S./SI equivalence

At minimum:

- `36 in = 914.4 mm`;
- `24 in = 609.6 mm`;
- `20 kip = 88.96443230521 kN`;
- `16 kip-in = 1.807757264441867 kN-m`;
- `10 in = 254 mm`;
- `8 in = 203.2 mm`;
- `6 in = 152.4 mm`;
- `4 in = 101.6 mm`;
- `3.25 in = 82.55 mm`;
- `3 in = 76.2 mm`;
- `2 in = 50.8 mm`;
- `1.5 in = 38.1 mm`;
- `0.563 in = 14.3002 mm`;
- `0.5 in = 12.7 mm`.

Equivalent geometry, material-direction classification, demand traces, wrenches, handoff, and fingerprints shall match.

## 66. Fingerprints

Create deterministic identities for:

- input;
- base frame/concrete;
- column geometry/material basis;
- angle assembly/geometry/material basis;
- web-bolt group;
- anchor group(s);
- component-design demand policy;
- symmetry proof;
- per-layer demand provenance;
- foundation wrench;
- external handoff;
- preview/design/application.

Presentation excluded.

Historical/frozen fingerprints remain exact.

## 67. Deliberate exclusions

Stage 3.5C does not authorize:

- column axial tension/uplift;
- user-applied moments;
- moment-resisting base design;
- concrete bearing capacity;
- grout capacity;
- anchor capacity;
- base-angle full CW body/heel capacity;
- horizontal-leg bending/prying capacity;
- stiffness-based column-end/angle bearing load split;
- web-normal bolt tension/prying capacity;
- unequal double-angle pair;
- flange-attached base angles;
- non-W/I column;
- welds;
- adhesive/epoxy;
- beam web splice.

## 68. Acceptance boundary

Stage 3.5C is accepted only if:

- single/double web-angle geometry is physically correct;
- column web receives 100% axial local-transfer demand in LW;
- base-angle system receives 100% axial system demand;
- double-angle branches receive 50/50 only after exact symmetry;
- angle vertical-leg axial transfer is classified in CW;
- foundation equilibrium contains the physical column action once;
- no doubled foundation reaction is created;
- no unsupported base-angle body/heel capacity is fabricated;
- concrete/anchor capacity remains external;
- no user moment or axial uplift is accepted;
- historical Stage 3.5 and frozen families remain exact;
- full local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
