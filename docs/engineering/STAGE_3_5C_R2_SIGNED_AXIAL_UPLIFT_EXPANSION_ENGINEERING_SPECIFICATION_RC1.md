# FRP Master Connection — Stage 3.5C-R2 Signed Axial Compression/Uplift Expansion — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.5C-R2 is an additive successor to Stage 3.5C / R1.

It changes the current normal axial input from a nonnegative compression magnitude to one signed axial force:

- positive = uplift/tension;
- negative = compression.

Web-plane and web-normal shear remain signed.

User-applied moments remain zero.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `58a89c52220fd8878b330206b209910008df84e4`;
- subject:
  `fix: correct column-base force presentation`;
- commit count: `87`;
- clean worktree/index.

Expected Stage 3.5C-R1 hosted CI:

- GitHub Actions run #82;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `5m 43s`.

The owner directly accepted Stage 3.5C-R1 visual behavior on 2026-08-29, then explicitly required upward axial force before Stage 3.5 is closed.

If repository governance still records Stage 3.5C-R1 visual acceptance as pending, update that status as governance-only evidence before production mutation and continue. Do not alter Stage 3.5C-R1 production behavior or fingerprints.

Expected immutable freeze targets remain:

- Stage 2.3: `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2: `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3: `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- Stage 3.4: `2303ec713d6d038b935e076b909c3b639ced0e09`.

## 3. Contract evolution

Historical engineering contract:

`3.5C-RC1`.

Historical semantics:

- `Axial compression` is a nonnegative magnitude;
- engineering axial component is `-P_u`.

Stage 3.5C-R1 is presentation-only and does not create a new engineering request contract.

New successor contract:

`3.5C-R2-RC1`.

Successor semantics:

- `Axial force` is signed;
- engineering axial component is the entered value directly.

No silent reinterpretation of historical payloads.

## 4. Column-base frame

Reuse:

- `S_C`: horizontal in column-web plane;
- `T_C`: horizontal normal to column web;
- `L_C`: column longitudinal direction, positive upward.

Require:

`S_C × T_C = L_C`.

Concrete top remains:

`L_C = 0`.

## 5. Signed force contract

Stage 3.5C-R2 normal engineering inputs:

### Axial force

`P_L`, signed along `L_C`.

- `P_L > 0`: uplift/tension;
- `P_L < 0`: compression;
- `P_L = 0`: no axial action.

### Web-plane shear

`V_S`, signed along `S_C`.

### Web-normal shear

`V_T`, signed along `T_C`.

Complete force:

`F = (V_S, V_T, P_L)`.

User free moment:

`M_user = (0,0,0)`.

## 6. Successor default

Normal R2 default:

- Axial force `P_L = -20 kip`;
- Web-plane shear `V_S = +4 kip`;
- Web-normal shear `V_T = 0 kip`.

This is physically identical to the historical Stage 3.5C default compression case.

Expected combined base reaction remains:

- `F_B = (4,0,-20) kip`;
- `M_B = (0,16,0) kip-in`.

## 7. Axial load UI

Normal current UI field:

`Axial force (+ uplift / - compression)`.

Help text shall state:

- positive acts upward along `+L_C`;
- negative acts downward/compression along `-L_C`;
- zero removes the axial action.

The old `Axial compression (positive magnitude)` UI remains only under historical-contract reproduction/testing, not the current normal R2 workspace.

## 8. User moments

No user-applied moment fields in R2.

Any nonzero user free moment is rejected.

This remains a shear-category connection.

## 9. Column action reference

Preserve backend-authoritative action reference.

Controlled default:

`r_C = (0,0,4) in`.

Base reference:

`r_B = (0,0,0)`.

No frontend reference calculation.

## 10. Exact base wrench

For any R2 signed force:

`F_B = F`.

With zero user free moment:

`M_B = (r_C-r_B) × F`.

For the controlled centered default reference:

`M_B = (-4 V_T, 4 V_S, 0) kip-in`.

The signed axial component alone generates no base moment when the action line is centered on the base reference normal axis.

No tolerance-based moment suppression.

## 11. Pure compression regression

Input:

- `P_L = -20 kip`;
- `V_S = 0`;
- `V_T = 0`.

Expected:

- `F_B = (0,0,-20) kip`;
- `M_B = (0,0,0)`.

Component design traces:

- column web: 20 kip, signed direction `-LW`, material axis classification `LW`;
- base-angle system: 20 kip, vertical-leg signed direction `-CW`, material axis classification `CW`.

## 12. Pure uplift case

Input:

- `P_L = +20 kip`;
- `V_S = 0`;
- `V_T = 0`.

Expected:

- `F_B = (0,0,+20) kip`;
- `M_B = (0,0,0)`.

Component design traces:

- column web: 20 kip, signed direction `+LW`;
- base-angle system: 20 kip, vertical-leg signed direction `+CW`.

Direct column-end bearing is not assigned to the uplift component.

## 13. Uplift-plus-shear benchmark

Controlled uplift benchmark:

- `P_L = +20 kip`;
- `V_S = +4 kip`;
- `V_T = 0`.

Expected combined base:

- `F_B = (4,0,20) kip`;
- `M_B = (0,16,0) kip-in`.

## 14. Component-design demand policy — signed

For both compression and uplift:

### Column web

Signed axial component assigned:

`P_web = P_L`.

Design magnitude:

`|P_L|`.

Demand fraction:

`1.0`.

### Base-angle system

Signed axial component assigned:

`P_angle_system = P_L`.

Design magnitude:

`|P_L|`.

Demand fraction:

`1.0`.

These are separate component adequacy demands and are not summed for foundation equilibrium.

## 15. Single-angle signed branch

Single angle:

`P_angle = P_L`.

For:

- compression: signed branch is negative `L_C`;
- uplift: signed branch is positive `L_C`.

Magnitude:

`|P_L|`.

No symmetry reduction.

## 16. Double-angle signed branch

Under exact symmetry and `V_T=0`:

`P_positive = P_negative = P_L/2`.

Thus:

- `P_L=-20` -> each branch `-10 kip`;
- `P_L=+20` -> each branch `+10 kip`.

The pair/system remains 100% of the signed axial action.

## 17. Double-angle symmetry — unchanged

Exact half sharing requires:

- mirrored angle geometry;
- centered web group;
- mirrored anchor groups;
- identical materials/sources;
- centered column;
- `V_T=0`.

Signed axial force may be positive or negative.

No tolerance.

## 18. Web-normal shear — unchanged

`V_T` acts along the common web-bolt axes.

For nonzero `V_T`:

- retain normal action;
- no generated bolt-axis tension resistance;
- no generated prying.

Required:

`COMMON_WEB_GROUP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

For double angles:

`WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION = NOT_EVALUATED`.

The combined base wrench remains exact.

## 19. In-plane physical web-group demand

Use the accepted Stage 2.5A mechanics exactly once for the physical web-bolt group using:

`F_in_plane = (V_S, P_L)`

in the web/vertical-leg plane under the existing geometry mapping.

No new group-demand equation.

Signed axial reversal reverses the local in-plane force direction but not the group geometry.

## 20. Double common-layer provenance

When exact symmetry applies, for each per-bolt in-plane demand vector `Q_i`:

- positive angle layer = `0.5 Q_i`;
- column web layer = `1.0 Q_i`;
- negative angle layer = `0.5 Q_i`.

The sign/direction of `Q_i` is preserved.

## 21. Single layer provenance

Single-angle group:

- column web = `1.0 Q_i`;
- angle vertical leg = `1.0 Q_i`.

## 22. Material direction — axial sign

### Column web

Axial action lies on the web `LW` axis:

- compression: `-LW`;
- uplift: `+LW`.

Both are longitudinal-axis directional classification.

### Angle vertical leg

Axial action lies on the angle vertical-leg `CW` axis:

- compression: `-CW`;
- uplift: `+CW`.

Both are crosswise/transverse-axis directional classification relative to `LW`.

Reversing sign does not convert LW to CW or CW to LW.

## 23. Directional local checks

Existing accepted local bolted checks may execute only where current signed-force / loaded-edge / bypass-path applicability maps the actual action correctly.

At minimum:

- directional pin bearing uses actual force direction and material basis;
- net tension/shear-out/block-shear checks retain their existing sign/edge applicability;
- no check is forced to run by using `abs(P_L)` alone.

If a reversed axial action cannot be mapped to an existing accepted local failure path:

return the existing/appropriate `NOT_EVALUATED` state rather than inventing a new method.

## 24. Compression-specific contact boundary

When:

`P_L < 0`

retain:

`COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

Also retain:

`BASE_ANGLE_TO_CONCRETE_BEARING_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`.

The base-angle system still receives 100% compression design demand under the controlled component-envelope philosophy.

## 25. Uplift-specific contact rule

When:

`P_L > 0`

direct column-end bearing is not a tensile load path.

Return:

`COLUMN_END_BEARING_FOR_UPLIFT = NOT_REQUIRED`.

Do not assign uplift resistance to column-end contact.

The uplift physical handoff proceeds through the base-angle/anchor system subject to unsupported/external limits.

## 26. Uplift base-angle body / heel limitation

When `P_L > 0`, always require:

`BASE_ANGLE_CW_BODY_AND_HEEL_UPLIFT_TRANSFER = NOT_EVALUATED`.

Do not infer uplift capacity from compression or local plate bearing checks.

The existing general angle-body/heel limitation remains visible as appropriate.

## 27. Uplift horizontal-leg / prying limitation

When `P_L > 0`, require:

`BASE_ANGLE_HORIZONTAL_LEG_UPLIFT_PRYING = NOT_EVALUATED`.

No prying resistance is calculated.

## 28. Anchor uplift boundary

When `P_L > 0`, require:

- `ANCHOR_TENSION_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `CONCRETE_UPLIFT_ANCHORAGE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`.

The complete anchor-group/base wrench is exported.

No anchor tension capacity.

## 29. Concrete / anchor limitations — always

Always retain:

- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

No concrete/anchor capacities.

## 30. Compression double-angle branch wrenches

Historical compression + shear case:

- `P_L=-20`;
- `V_S=+4`;
- `V_T=0`.

Branch force each:

`F_±=(2,0,-10) kip`.

At:

- `r_+=(0,+3.25,0)`;
- `r_-=(0,-3.25,0)`,

retain historical moments:

Positive:

`M_+=(32.5,8,6.5) kip-in`.

Negative:

`M_-=(-32.5,8,-6.5) kip-in`.

## 31. Uplift double-angle branch wrenches

Controlled uplift + shear case:

- `P_L=+20`;
- `V_S=+4`;
- `V_T=0`.

Branch force each:

`F_±=(2,0,+10) kip`.

Expected at group centroids:

Positive:

`M_+=(-32.5,8,6.5) kip-in`.

Negative:

`M_-=(32.5,8,-6.5) kip-in`.

Shifted to the base reference, exact branch sum recovers:

- `F_B=(4,0,20) kip`;
- `M_B=(0,16,0) kip-in`.

## 32. Pure uplift double-angle branch wrenches

For:

- `P_L=+20`;
- `V_S=0`;
- `V_T=0`,

each branch force:

`(0,0,10) kip`.

Expected branch moments:

Positive:

`(-32.5,0,0) kip-in`.

Negative:

`(32.5,0,0) kip-in`.

Shifted branch sum at base:

- force `(0,0,20)`;
- moment `(0,0,0)`.

## 33. Single positive angle compression wrench

Historical:

- `P_L=-20`;
- `V_S=+4`.

At positive anchor centroid:

- force `(4,0,-20)`;
- moment `(65,16,13) kip-in`.

Preserve exactly under the historical and R2 compression fixture.

## 34. Single positive angle uplift wrench

R2 uplift + shear:

- `P_L=+20`;
- `V_S=+4`.

At positive anchor centroid:

- force `(4,0,20) kip`;
- moment `(-65,16,13) kip-in`.

Shifted to base reference:

- force `(4,0,20)`;
- moment `(0,16,0)`.

No eccentricity component is suppressed.

## 35. Single negative angle uplift mirror

For the exact negative-side mirror with uplift + shear:

- force `(4,0,20) kip`;
- moment `(65,16,-13) kip-in`.

Shifted to base reference recovers the same combined base wrench.

## 36. Foundation reaction counted once

For any signed axial input:

`Foundation axial reaction = P_L`

once.

Examples:

- compression `P_L=-20` -> foundation axial component `-20`;
- uplift `P_L=+20` -> foundation axial component `+20`.

Never:

- `P_web + P_angle_system`;
- `2 P_L`.

## 37. Component transfer UI

Current R2 UI shall display signed action and magnitude distinctly.

### Compression example

Column Web:

- signed axial action `-20 kip`;
- design magnitude `20 kip (100%)`;
- material axis `LW`;
- mode `Compression`.

Base-Angle Pair:

- system signed axial action `-20 kip`;
- design magnitude `20 kip (100%)`;
- each branch `-10 kip (50%)`;
- vertical-leg material axis `CW`.

### Uplift example

Column Web:

- signed axial action `+20 kip`;
- design magnitude `20 kip (100%)`;
- material axis `LW`;
- mode `Uplift/Tension`.

Base-Angle Pair:

- system signed axial action `+20 kip`;
- design magnitude `20 kip (100%)`;
- each branch `+10 kip (50%)`;
- vertical-leg material axis `CW`.

Foundation reaction shows the signed axial action once.

## 38. External handoff

Extend the deterministic handoff for R2 to include:

- signed axial force;
- axial mode `COMPRESSION`, `UPLIFT`, or `ZERO`;
- component design magnitudes and signed actions;
- branch wrenches when authorized;
- combined base wrench;
- column-end contact applicability;
- uplift-specific limitations.

No capacity.

Historical handoff remains exact under `3.5C-RC1`.

## 39. Web-normal + uplift combined-layout mode

For double angles when `V_T != 0`:

- no complete positive/negative branch allocation;
- no fabricated anchor tension distribution;
- retain full combined base wrench;
- retain both physical angle/anchor layouts;
- include uplift and web-normal limitations.

## 40. Preview path

R2 preview shall:

- accept signed axial force;
- validate force/moment schema;
- construct unchanged geometry;
- classify axial mode;
- compute signed component demand provenance;
- compute existing supported in-plane group demand;
- preserve local signed force directions;
- retain `V_T` normal action;
- prove symmetry where applicable;
- compute exact branch/base wrenches where authorized;
- build external handoff;
- return visualization/status.

Preview resistance calls:

`0`.

## 41. Explicit design path

Run Design Check:

- current R2 preview only;
- existing supported local FRP/bolt checks only;
- signed local action passed without absolute-value corruption;
- no angle body/heel uplift capacity;
- no horizontal-leg prying capacity;
- no anchor/concrete capacity;
- limitations retained.

## 42. API strictness

Existing historical contract remains:

`3.5C-RC1`.

Add successor:

`3.5C-R2-RC1`.

### Historical request

Retains:

`axial_compression >= 0`.

### R2 request

Uses:

`signed_axial_force`

or repository-consistent equivalent.

Accept any finite signed value.

Reject:

- simultaneous historical and successor axial fields;
- nonzero user moments;
- extra fields;
- unsupported versions.

Do not reinterpret `axial_compression=-20` under the historical contract as uplift.

## 43. Frontend current workspace

Current normal Stage 3.5C workspace uses:

`3.5C-R2-RC1`.

Replace:

`Axial compression (positive magnitude)`

with:

`Axial force (+ uplift / - compression)`.

Default value:

`-20 kip`.

Help text shall state the sign convention.

No moment fields.

## 44. Signed axial arrow

R2 display:

- `P_L > 0`: arrow along `+L_C`;
- `P_L < 0`: arrow along `-L_C`;
- `P_L = 0`: no axial arrow.

Arrow origin remains backend action reference.

Web-plane/web-normal signed arrows retain R1 behavior.

## 45. Material axes

No material-basis change.

With axes enabled, visually confirm:

- column web vertical axial axis = LW;
- base-angle vertical-leg vertical axial axis = CW.

For uplift and compression, only signed direction reverses; the material axis classification remains LW/CW respectively.

## 46. Status aggregation

Required precedence:

1. invalid geometry/input -> invalid/rejected;
2. supported numerical local failure -> `FAIL`;
3. otherwise unsupported/external angle/anchor/concrete checks -> `NOT_EVALUATED` / external design required;
4. ordinary whole-connection PASS prohibited.

Uplift is no longer invalid merely because `P_L>0`.

## 47. Required controlled golden cases

At minimum:

G1. Historical `3.5C-RC1` compression request exact.
G2. Historical R1 presentation regression exact.
G3. R2 default `P_L=-20`, `V_S=4`, `V_T=0` reproduces historical engineering results.
G4. R2 axial field sign convention.
G5. Pure compression combined base wrench.
G6. Pure uplift combined base wrench.
G7. Uplift+shear combined base wrench `(4,0,20); (0,16,0)`.
G8. Column web compression = 100% magnitude, `-LW`.
G9. Column web uplift = 100% magnitude, `+LW`.
G10. Base-angle system compression = 100% magnitude, `-CW`.
G11. Base-angle system uplift = 100% magnitude, `+CW`.
G12. Double compression branches `-10/-10`.
G13. Double uplift branches `+10/+10`.
G14. Single compression branch `-20`.
G15. Single uplift branch `+20`.
G16. No doubled foundation reaction in compression.
G17. No doubled foundation reaction in uplift.
G18. Compression directional pin-bearing classification web LW / angle CW.
G19. Uplift directional pin-bearing axis classification remains web LW / angle CW.
G20. Signed reversal preserved into per-layer demand vectors.
G21. Reverse-load net/shear-out applicability fail-closed where existing method does not map.
G22. Compression bearing partition external.
G23. Uplift column-end bearing not required.
G24. Uplift angle body/heel transfer NOT_EVALUATED.
G25. Uplift horizontal-leg prying NOT_EVALUATED.
G26. Anchor tension external.
G27. Concrete uplift anchorage limit states external.
G28. Compression double positive branch historical wrench.
G29. Compression double negative branch historical wrench.
G30. Uplift double positive branch wrench.
G31. Uplift double negative branch wrench.
G32. Pure uplift branch moments cancel at base.
G33. Single positive compression historical wrench.
G34. Single positive uplift wrench.
G35. Single negative uplift mirror wrench.
G36. Web-normal shear still blocks double branch allocation.
G37. Uplift+web-normal combined base handoff retained.
G38. Signed axial arrow + / - / zero.
G39. No user moment.
G40. Preview zero resistance.
G41. Supported local failure precedence.
G42. Valid uplift geometry remains current but whole status NOT_EVALUATED.
G43. External handoff deterministic compression/uplift.
G44. Exact U.S./SI compression default.
G45. Exact U.S./SI uplift representative.
G46. Historical Stage 3.5C fingerprint exact.
G47. Historical Stage 3.5A/R1/R2/B/R1 regressions exact.
G48. Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee regressions exact.

## 48. U.S./SI

At minimum:

- `20 kip = 88.96443230521 kN`;
- `10 kip = 44.482216152605 kN`;
- `4 kip = 17.792886461042 kN`;
- `65 kip-in = 7.344013886795085 kN-m`;
- `32.5 kip-in = 3.6720069433975425 kN-m`;
- `16 kip-in = 1.807757264441867 kN-m`;
- `13 kip-in = 1.468802777359017 kN-m`;
- `6.5 kip-in = 0.7344013886795085 kN-m`.

Equivalent signed actions, geometry, demand provenance, wrenches, handoff, and engineering fingerprints shall match.

## 49. Fingerprints

New R2 engineering identity includes:

- signed axial force;
- axial mode;
- signed component-demand provenance;
- branch signed actions;
- contact applicability status;
- uplift limitations;
- contract version.

Historical `3.5C-RC1` fingerprints remain exact.

Presentation-only R1 correction remains fingerprint-neutral.

Frozen/historical Stage 3.5 fingerprints remain exact.

## 50. Deliberate exclusions

Stage 3.5C-R2 does not authorize:

- user-applied moments;
- moment-resisting base design;
- full base-angle body/heel compression capacity;
- full base-angle body/heel uplift capacity;
- horizontal-leg uplift prying capacity;
- anchor tension capacity;
- concrete uplift capacity;
- anchor/concrete compression capacity;
- stiffness-based bearing partition;
- web-normal bolt tension/prying capacity;
- unequal double angles;
- non-W/I column;
- beam web splice.

## 51. Acceptance boundary

Stage 3.5C-R2 is accepted only if:

- signed axial force accepts both compression and uplift;
- current default is `-20 kip` compression;
- upward `+20 kip` is valid, not rejected;
- axial arrow reverses correctly;
- web receives 100% `|P_L|` on LW axis;
- angle system receives 100% `|P_L|` on CW axis;
- double branches receive signed half actions only after symmetry;
- physical foundation reaction is counted once;
- uplift does not use column-end bearing;
- unsupported angle body/heel/prying remains NOT_EVALUATED;
- anchor/concrete uplift capacities remain external;
- historical Stage 3.5C contract remains exact;
- Stage 3.5 historical and frozen families remain exact;
- full local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
