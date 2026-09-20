# FRP Master Connection — Stage 3.3C1 Shared Rectangular-Section + Full-Through-Bolt Architecture — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.3C1 establishes the shared physical architecture required before expanding Tee, single clip-angle, and paired clip-angle connections to additional supporting profiles and rectangular sections.

It adds:
1. `RECTANGULAR_HOLLOW_SECTION` full-through-bolt architecture.
2. New `SOLID_RECTANGULAR_SECTION` geometry.
3. A shared supporting-member target registry for:
   - W Column Flange
   - W Beam Flange
   - W Column Web
   - Channel Column Web
   - Angle Column Leg
   - Rectangular Hollow Column Wall
   - Solid Rectangular Column Face

Stage 3.3C1 is a shared/core stage. It does not yet wire every new option into every production connection selector; Stage 3.3C2/C3 perform family integration.

No new resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository:
`C:\Users\green\Documents\New project\frp-master-connection`

Expected branch: `main`

Expected `HEAD == origin/main`:
`cb87761bf4298cd78f6b538e5fe2c84a385fd780`

Expected subject:
`feat: add symmetric paired clip-angle connector`

Expected commit count: `68`
Expected clean worktree/index.

Expected source trees:
- backend: `958aa28676620c3a162c7c320a377f553ab388cd`
- frontend: `d51bd05103a2530ea3bea9bdb10e020cc18deb57`

Package identities:
- package blob `b753abd55004168eee5844879f0596d435fe4b5a`
- lock blob `ae1831268db42005517343bf555f054a673ae520`
- lock SHA-256 `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254`

Freeze tags:
- `stage-2.3-interface-geometry-freeze` -> `5bc545ab8251f9bd49dedc776962937ed5e822a2`
- `stage-3.2-tee-connection-freeze` -> `d16b354732c90bf3bf7847c62be652c230a9f91e`

If baseline differs: STOP before mutation.

## 3. User-confirmed requirements

### Supporting-member options for Tee, single clip-angle, and paired clip-angle families

Future integration shall support:
- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

No W Beam Web is introduced by this specification.

### Rectangular-section pairing rule

Whenever a compatible workflow offers `Rectangular Hollow Section`, it shall also offer `Solid Rectangular Section` unless a later family-specific physical exclusion is explicitly controlled.

### Hollow rectangular full-through bolt rule

The normal supported RHS path is one continuous physical bolt:

`external head/washer -> external connector layer(s), if any -> near RHS wall -> hollow cavity -> far RHS wall -> external connector layer(s), if any -> external washer/nut`

No internal nut. No internal washer. No normal single-wall bolt path.

### Solid rectangular full-through bolt rule

The normal SRS path is:

`external head/washer -> external connector layer(s), if any -> full solid depth -> external connector layer(s), if any -> external washer/nut`

Head and nut remain outside opposite exterior faces.

# PART A — PROFILE ARCHITECTURE

## 4. Shared profile families

Shared member-profile registry shall contain:
- `RECTANGULAR_HOLLOW_SECTION`
- `SOLID_RECTANGULAR_SECTION`

RHS reuses existing accepted R8 wall/corner geometry.

SRS is new geometry authority under C1 and shall not be modeled as an RHS with a hidden/zero cavity.

## 5. Solid rectangular geometry

Backend-authoritative solid rectangular prism:
- longitudinal axis `L_M`
- cross-section axes `Y_M`, `Z_M`
- width `b > 0`
- depth `d > 0`
- finite member length `L > 0`

Controlled semantic frame:
- `L_M=(1,0,0)`
- `Y_M=(0,1,0)`
- `Z_M=(0,0,1)`

Cross-section:
- `-b/2 <= Y_M <= +b/2`
- `-d/2 <= Z_M <= +d/2`

Stable broad faces:
- `Y_POS_FACE`
- `Y_NEG_FACE`
- `Z_POS_FACE`
- `Z_NEG_FACE`

## 6. Solid rectangular material basis

Controlled semantic basis:
- `LW = +L_M`
- `CW = +Y_M`
- `TT = +Z_M`

This is a stable volume basis, not a wall-specific laminate basis.

C1 introduces no CW/TT property equality or new material property.

## 7. Opposing-face/wall registry

RHS:
- `Y_POS_FACE <-> Y_NEG_FACE`
- `Z_POS_FACE <-> Z_NEG_FACE`

SRS:
- `Y_POS_FACE <-> Y_NEG_FACE`
- `Z_POS_FACE <-> Z_NEG_FACE`

Selected and opposite faces/walls are finite, parallel, and separated by the exact outside dimension along the bolt axis.

# PART B — SHARED SUPPORT TARGET REGISTRY

## 8. Target identities

Create shared stable targets equivalent to:
- `W_COLUMN_FLANGE`
- `W_BEAM_FLANGE`
- `W_COLUMN_WEB`
- `CHANNEL_COLUMN_WEB`
- `ANGLE_COLUMN_LEG`
- `RECTANGULAR_HOLLOW_COLUMN_WALL`
- `SOLID_RECTANGULAR_COLUMN_FACE`

Each target maps:
- support role
- profile family
- selected physical region
- selected exterior contact surface
- opposite/exiting surface where applicable
- bolt-path class
- access qualification
- finite-boundary rules

C1 establishes these contracts; C2/C3 integrate them into connection families.

## 9. Existing W flange targets

Preserve W Column Flange and W Beam Flange behavior exactly.

No frozen geometry/result/fingerprint change.

## 10. W Column Web

Selected region: `WEB`.

Bolt crosses exactly one W web thickness and exits the opposite broad web face.

It shall not pass through W flanges.

Clear-web bounds and junction exclusions remain authoritative.

## 11. Channel Column Web

Bolt crosses exactly one Channel web thickness and exits the opposite web broad face.

Flange/junction overlap is invalid.

## 12. Angle Column Leg

User selects one Angle leg.

Bolt crosses that leg thickness and exits its opposite broad face.

Heel overlap, perpendicular leg, and outside-leg paths are invalid.

Reuse R7 authority.

## 13. Rectangular Hollow Column Wall

Selected wall -> near wall -> cavity -> far opposite wall.

Far wall is mandatory.

Normal single-wall RHS attachment is not authorized.

## 14. Solid Rectangular Column Face

Selected face -> continuous full solid depth -> opposite exterior face.

# PART C — FULL-THROUGH BOLT PATH

## 15. Segment model

Generalize physical bolt paths to ordered segment kinds:
- `MATERIAL_LAYER`
- `FREE_SHANK_SPAN`

`FREE_SHANK_SPAN`:
- has exact positive length
- contains no material
- contributes no bearing layer
- receives no material demand allocation
- is included in physical shank length

RHS cavity is a `FREE_SHANK_SPAN`, never an FRP layer.

## 16. RHS core path

Let outside bolt-axis dimension be `D > 0`, wall thickness `t > 0`, and require `2t < D`.

Exact core path:
- near wall = `t`
- cavity = `D - 2t`
- far wall = `t`

Exact total:
`t + (D - 2t) + t = D`

## 17. SRS core path

Let outside bolt-axis dimension be `D > 0`.

Exact core path:
- one continuous `MATERIAL_LAYER` of thickness `D`

No cavity and no artificial split.

## 18. External connector layers

Architecture permits family integrations to prepend/append external connector layers.

Examples:

RHS one-sided:
`connector -> near wall -> cavity -> far wall`

RHS paired:
`positive connector -> near wall -> cavity -> far wall -> negative connector`

SRS paired:
`positive connector -> full solid depth -> negative connector`

C1 establishes capability; C2/C3 authorize specific family stacks.

## 19. One physical bolt

A full-through path is one physical bolt with one stable ID and one continuous axis.

Forbidden:
- separate near-wall/far-wall bolts
- coincident duplicate shanks
- internal hardware pairs

## 20. Hole alignment

Near and far holes must lie on one exact bolt axis.

Their projected in-plane coordinates on paired opposing faces must match exactly.

No tolerance-based alignment.

## 21. Hole containment

RHS:
- near wall hole independently valid
- far wall hole independently valid
- R8 corner exclusions apply to both

SRS:
- entry and exit face holes independently contained

One valid side cannot excuse an invalid opposite side.

## 22. Hardware location

Normal full-through hardware:
- head + washer outside one exterior side
- washer + nut outside opposite exterior side

RHS cavity may contain only bolt shank.

## 23. Shank span

Shank span includes every connector/material/free-span segment between external hardware sides.

No shortening at the cavity.

# PART D — VALIDATION AND ACCESS

## 24. RHS validation

Reject:
- near-wall corner overlap
- far-wall corner overlap
- wrong opposing wall
- ambiguous opposite wall
- thickness mismatch
- nonparallel wall pair
- bolt axis missing far wall

## 25. SRS validation

Reject:
- axis missing opposite face
- outside-face hole
- ambiguous opposite face
- invalid/nonfinite dimensions

## 26. W/Channel/Angle support validation

Reuse exact W web, Channel web, and Angle leg physical geometry.

No generic plate approximation.

## 27. Installation access

RHS normal full-through path has externally accessible head and nut.

The earlier single-wall `INTERNAL_FASTENER_ACCESS_REQUIRED` condition is not the normal C1 full-through installation state.

If actual geometry blocks exterior access, expose a separate explicit access limitation.

SRS likewise requires access at both exterior ends.

# PART E — RESISTANCE BOUNDARY

## 28. Unsupported RHS local mechanics

C1 does not authorize:
- wall local bending
- wall crushing/crippling
- ovalization
- local face deformation
- sleeve/crush-tube design
- local reinforcement
- preload effects

Future connection designs remain fail-closed where these checks are required.

## 29. Unsupported SRS full-depth mechanics

C1 creates no new full-depth solid rectangular bearing/block/net/shear-out method.

Existing methods may consume SRS only when their accepted applicability contract unambiguously covers it.

Otherwise not evaluated.

## 30. Cavity demand rule

RHS cavity:
- no material ID
- no material axes
- no bearing demand
- no resistance check
- no FRP layer allocation

It is geometry/free shank span only.

# PART F — FUTURE UI RULE

## 31. Rectangular option pairing

C2/C3 integrations shall expose:
- `Rectangular Hollow Section`
- `Solid Rectangular Section`

together for compatible connected/support profile selectors unless a controlled physical exclusion says otherwise.

Do not expose SRS in current production selectors during C1 unless the complete family topology/path is already implemented and tested.

## 32. Terminology

Use:
- `Rectangular Hollow Section`
- `Solid Rectangular Section`
- `Rectangular Hollow Column Wall`
- `Solid Rectangular Column Face`

Do not use normal UI wording `solid tube`.

# PART G — CONTROLLED NUMERICAL GEOMETRY

## 33. RHS reference section

Use:
- bolt-axis outside depth `D=6 in`
- orthogonal width `4 in`
- wall thickness `0.5 in`
- member length `8 in`

Expected:
- near wall `0.5 in`
- cavity `5 in`
- far wall `0.5 in`
- total `6 in`

## 34. SRS reference section

Use:
- bolt-axis depth `6 in`
- orthogonal width `4 in`
- member length `8 in`

Expected:
- continuous material traversal `6 in`
- cavity `0`

## 35. External-layer examples

One-sided RHS with 0.5 in connector:
`0.5 + 0.5 + 5 + 0.5 = 6.5 in`

Paired RHS with 0.5 in connectors both sides:
`0.5 + 0.5 + 5 + 0.5 + 0.5 = 7 in`

Paired SRS:
`0.5 + 6 + 0.5 = 7 in`

# PART H — REGRESSION / FREEZE

## 36. Frozen Tee protection

If shared frozen Tee files change:
- create/update Stage 3.2 freeze-change record
- prove Tee geometry/result/fingerprint unchanged
- freeze manifest/tag unchanged

## 37. Clip-angle regressions

All accepted Stage 3.3A R1-R4 behavior remains exact.

Current Stage 3.3B behavior/fingerprints remain exact unless C1 adds only dormant shared architecture.

No paired-angle sharing logic changes.

## 38. Direct regression

Direct reference behavior remains unchanged.

## 39. Acceptance

C1 accepted only if:
- SRS is real solid geometry, not hidden RHS
- RHS/SRS opposing faces are exact
- RHS path = near wall + free cavity span + far wall
- SRS path = one continuous solid layer
- head/nut remain external
- no internal hardware
- near/far holes align exactly
- both RHS walls independently pass containment
- cavity is not material
- support-target registry contains exactly the user-confirmed options
- no new resistance equation
- frozen Tee / accepted clip-angle behavior exact
- full QA and hosted 4/4 CI pass

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
