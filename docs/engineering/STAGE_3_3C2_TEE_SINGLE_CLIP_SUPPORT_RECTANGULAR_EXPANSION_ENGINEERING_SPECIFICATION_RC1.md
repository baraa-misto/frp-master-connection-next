# FRP Master Connection — Stage 3.3C2 Tee + Single Clip-Angle Supporting-Member and Rectangular-Section Expansion — Engineering Specification RC1

## 1. Status

Controlled owner engineering specification — RC1.

Stage 3.3C2 integrates the accepted Stage 3.3C1 rectangular-section/full-through-bolt core into:
- the FRP Tee family; and
- the Single FRP Clip-Angle family.

C2 adds the user-confirmed supporting-member options:
- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

It also adds `Solid Rectangular Section` wherever these two families currently offer `Rectangular Hollow Section` as a connected member.

For any C2-integrated RHS member/support path, the normal accepted geometry is one continuous full-through bolt crossing both opposing walls and the cavity, with head/washer and nut/washer outside opposite exterior sides and no internal hardware.

This intentionally supersedes the historical single-wall RHS product behavior for affected Tee and Single Clip-Angle requests.

No new resistance equation is introduced.

Paired/double clip-angle integration is Stage 3.3C3 and is outside C2.

## 2. Accepted starting baseline

Expected repository:
`C:\Users\green\Documents\New project\frp-master-connection`

Expected branch: `main`

Expected `HEAD == origin/main`:
`657ebb00ec48fbfb9869ba7ced193f967daf0ded`

Expected subject:
`feat: add full-through rectangular bolt architecture`

Expected commit count: `69`
Expected worktree/index: clean.

Expected source trees:
- backend `44274f7399082b7e69f852f795e035bc4a494968`
- frontend `d51bd05103a2530ea3bea9bdb10e020cc18deb57`

Package identities:
- package blob `b753abd55004168eee5844879f0596d435fe4b5a`
- lock blob `ae1831268db42005517343bf555f054a673ae520`
- lock SHA-256 `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254`

Freeze tags remain:
- Stage 2.3 -> `5bc545ab8251f9bd49dedc776962937ed5e822a2`
- Stage 3.2 -> `d16b354732c90bf3bf7847c62be652c230a9f91e`

Stage 3.3C1 hosted CI is accepted 4/4 green.

## 3. Product scope

C2 modifies only:
1. Tee connector workspace/API/application.
2. Single Clip-Angle workspace/API/application.

C2 shall not modify Paired Clip-Angle production topology or selectors.

## 4. Shared support choices

Both Tee and Single Clip-Angle workspaces shall expose exactly:
- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

Do not add W Beam Web.

Use one shared support-target contract and one shared support editor; do not duplicate separate hard-coded lists.

## 5. Connected rectangular profile pairing

Where Tee or Single Clip-Angle offers `Rectangular Hollow Section`, also offer `Solid Rectangular Section`.

Normal UI shall use `Solid Rectangular Section`, not `solid tube`.

## 6. Shared supporting-member editor

The shared editor shall render target-specific fields:

### W Column Flange / W Beam Flange
Retain existing W/I dimensions and flange selector.

### W Column Web
- member/view length
- depth
- flange width
- web thickness
- flange thickness
- positive/negative web broad face

### Channel Column Web
- member/view length
- depth
- flange width
- web thickness
- flange thickness
- selected web broad face

### Angle Column Leg
- member/view length
- Leg Y
- Leg Z
- thickness
- orientation/roll where required
- selected leg
- selected exterior broad face

### Rectangular Hollow Column Wall
- member/view length
- outside width
- outside depth
- wall thickness
- selected exterior wall

### Solid Rectangular Column Face
- member/view length
- width
- depth
- selected exterior face

## 7. Support visualization

Render the complete actual supporting profile:
- W/I
- Channel
- Angle
- RHS
- SRS

No generic plate placeholder.

RHS remains visibly hollow.
SRS is visibly solid.

## 8. Support material axes

Use backend-authoritative material regions/bases.

W/Channel/Angle/RHS retain accepted region semantics.
SRS uses the C1 stable volume basis.
R14C region-embedded material-axis visualization remains shared.

# PART A — TEE SUPPORT INTEGRATION

## 9. Tee support interface

Tee Interface B remains:
`Tee Flange ↔ Support`

Existing Tee body placement, Tee length anchoring, and non-RHS connected-member behavior remain unchanged except where this specification explicitly supersedes historical RHS behavior.

## 10. Tee -> W Column Web

Path:
`Tee flange -> W column web`

One web material thickness.
Finite clear-web and junction exclusions apply.

## 11. Tee -> Channel Column Web

Path:
`Tee flange -> Channel web`

One web thickness.
Flange/junction overlap invalid.

## 12. Tee -> Angle Column Leg

Path:
`Tee flange -> selected support Angle leg`

Heel/perpendicular-leg paths invalid.
Reuse R7 leg authority.

## 13. Tee -> RHS Column Wall

Physical stack:
`Tee flange -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

One continuous physical bolt.
Head/washer outside Tee side; washer/nut outside far RHS wall.
No internal hardware.

## 14. Tee -> Solid Rectangular Column Face

Physical stack:
`Tee flange -> full SRS solid depth`

One physical bolt with far washer/nut outside opposite SRS face.

# PART B — SINGLE CLIP-ANGLE SUPPORT INTEGRATION

## 15. Single Clip-Angle support interface

Interface B remains:
`Clip-Angle Support Leg ↔ Support`

R2 exterior-side placement remains authoritative.

## 16. Single Angle -> W Column Web

Path:
`clip-angle support leg -> W column web`

One web thickness.
Connector leg remains outside selected web face.

## 17. Single Angle -> Channel Column Web

Path:
`clip-angle support leg -> Channel web`

One web thickness.
Junction collision invalid.

## 18. Single Angle -> Angle Column Leg

Path:
`clip-angle support leg -> selected support Angle leg`

Heel/perpendicular-leg collision invalid.

## 19. Single Angle -> RHS Column Wall

Path:
`clip-angle support leg -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

One physical bolt; external hardware only.

## 20. Single Angle -> Solid Rectangular Column Face

Path:
`clip-angle support leg -> full SRS solid depth`

One physical bolt.

# PART C — CONNECTED RECTANGULAR PROFILE EXPANSION

## 21. Tee connected RHS successor

Historical Stage 3.2 Tee RHS connected-member behavior used a single-wall path with internal-access qualification.

C2 intentionally supersedes it.

New Tee Interface A:
`Tee stem -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

One physical bolt.
No internal nut/washer.
R12 trim continues on the complete RHS profile.

## 22. Single Clip-Angle connected RHS successor

Historical accepted single-angle RHS behavior becomes:
`clip-angle connected leg -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

One physical bolt with external head/nut.

R1 profile binding, R2 exterior contact, R3 preview-state separation, and R4 full-profile trim remain authoritative.

## 23. Tee connected SRS

New Tee Interface A:
`Tee stem -> full SRS solid depth`

No cavity.

## 24. Single Clip-Angle connected SRS

New Interface A:
`clip-angle connected leg -> full SRS solid depth`

No cavity.

# PART D — FULL-THROUGH GEOMETRY / HARDWARE

## 25. One physical bolt

Every RHS/SRS C2 path owns one stable physical bolt ID and one continuous shank.

Do not duplicate near/far wall bolts.

## 26. RHS hole alignment

Near and far wall holes lie on exactly one bolt axis.

Both walls independently pass complete-hole containment.

R8 corner exclusions apply to both.

If either wall invalid: `INVALID_GEOMETRY`.

## 27. SRS hole alignment

Entry/exit holes lie on one exact axis and each exterior face satisfies containment.

## 28. Hardware

For C2 RHS/SRS paths:
- no internal nut
- no internal washer
- cavity contains shank only
- head/nut remain outside complete stack

Viewer shall visibly show the continuous shank through the complete section.

## 29. Shank length

Use C1 physical path span including connector thickness plus:
- RHS near wall + cavity + far wall; or
- full SRS depth.

Presentation-only head/nut dimensions remain excluded from engineering fingerprints.

# PART E — RESISTANCE / APPLICABILITY

## 30. Open-section support targets

For W web, Channel web, and Angle leg, existing accepted methods may execute only where existing geometry/material applicability proves them.

No new equation.

## 31. RHS local mechanics

Required limitations include:
- `RHS_LOCAL_WALL_RESPONSE`
- `RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT`

These remain `NOT_EVALUATED`.

Cavity receives no demand/resistance.
Do not infer far-wall bearing demand from near-wall demand.

Existing metallic bolt shear may execute only if its current physical shear-plane contract clearly applies.

Unsupported RHS local response prohibits ordinary PASS.

## 32. SRS resistance applicability

Required limitation:
`SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY`

remains `NOT_EVALUATED` unless an existing accepted method explicitly proves applicability without new interpretation.

No ordinary PASS while required SRS local checks remain unsupported.

## 33. Geometry vs design limitation

Preserve R3 semantics:
- valid full-through geometry stays current
- unsupported RHS/SRS mechanics are design limitations
- true path/containment/interference failures are geometry invalid

# PART F — TRIM / POSITION REGRESSION

## 34. Tee trim

R12 behavior remains exact.

Add SRS full-profile trim using the shared solid trim kernel where applicable.

RHS trimmed geometry remains hollow.
SRS trimmed geometry remains solid.

## 35. Single-angle trim

R4 behavior remains exact.

Add SRS trim.
RHS full-through hole/path geometry recomputes after trim.
Trim never auto-moves bolt groups.

## 36. Positioning

Tee R13 anchoring remains exact.
Single-angle connector anchoring/placement remains exact.

Changing support target does not silently move bolt groups to preserve validity.

# PART G — API / FINGERPRINT / SUCCESSOR CONTROL

## 37. Shared support-target API identity

Tee and Single-Angle APIs consume the same shared support-target identity.

Do not maintain incompatible per-family support enums.

Strict validation rejects dimensions/fields inconsistent with selected target.

## 38. Existing routes

Do not create new family routes.

Evolve existing Tee and Single Clip-Angle preview/design schemas under repository conventions.

Legacy valid W-flange requests remain accepted.

## 39. Unaffected legacy fingerprints

For all non-RHS existing Tee and Single-Angle requests that are physically unchanged:
- geometry fingerprints unchanged
- engineering fingerprints unchanged
- results unchanged

This includes W Column Flange and W Beam Flange.

## 40. Intentional RHS fingerprint successor

C2 authorizes exact engineering fingerprint transitions for existing Tee and Single-Angle RHS requests whose physical path changes from historical single-wall to full-through.

For every affected controlled fixture:
1. recover exact pre-C2 fingerprint
2. compute exact post-C2 fingerprint
3. diff canonical payloads
4. prove differences are limited to:
   - full-through path identity
   - far-wall material geometry
   - cavity FREE_SHANK_SPAN
   - external far hardware/access identity
   - removal of historical single-wall/internal-access identity
5. prove unrelated inputs unchanged
6. commit full exact before/after assertions

No unrelated transition is authorized.

## 41. Stage 3.2 Tee RHS successor governance

Create a controlled record equivalent to:
`STAGE_3_3C2_STAGE_3_2_TEE_RHS_FULL_THROUGH_SUCCESSOR.md`

Record:
- frozen historical Tee RHS behavior
- user-confirmed full-through successor rule
- affected request classes
- exact fingerprint transitions
- unchanged non-RHS Tee behavior
- immutable Stage 3.2 tag/manifest

Do not move the freeze tag.

## 42. Single-angle RHS successor governance

Record exact Stage 3.3A RHS single-wall -> C2 full-through transitions.

Historical accepted single-angle baseline remains evidence; no tag move.

# PART H — FRONTEND PRODUCT INTEGRATION

## 43. Supporting-member dropdown

Tee and Single-Angle shall each expose the exact seven targets.

Titles use clear wording, e.g.:
- `FRP Angle Brace -> FRP Tee -> W Column Web`
- `FRP Channel Beam -> Single FRP Clip Angle -> Rectangular Hollow Column Wall`

## 44. Dynamic support controls

Changing support type:
- shows only relevant fields
- requests a new preview
- stales prior design
- preserves camera
- preserves explicit current/last-valid semantics

No stale W dimensions under Channel/Angle/RHS/SRS.

## 45. Connected SRS option

Both connected-profile selectors show:
- Rectangular Hollow Section
- Solid Rectangular Section

SRS has width/depth/length and no wall-thickness field.
RHS retains wall thickness.

Scene changes hollow <-> solid.

## 46. Full-through visualization

RHS:
- near wall
- cavity
- far wall
- one continuous shank
- external head/washer
- external nut/washer
- no internal hardware

SRS:
- solid body
- one full-depth shank
- external hardware

No duplicate bolt.

## 47. Material axes

R14C embedded material-axis behavior remains:
- region-specific on RHS walls
- stable volume basis on SRS

# PART I — CONTROLLED GOLDENS / REGRESSION

## 48. Required C2 golden coverage

At minimum:
1. Tee -> W Column Web
2. Tee -> Channel Column Web
3. Tee -> Angle Column Leg
4. Tee -> RHS Column Wall full-through
5. Tee -> SRS Column Face full-through
6. Single Angle -> W Column Web
7. Single Angle -> Channel Column Web
8. Single Angle -> Angle Column Leg
9. Single Angle -> RHS Column Wall full-through
10. Single Angle -> SRS Column Face full-through
11. Tee connected RHS full-through successor
12. Single Angle connected RHS full-through successor
13. Tee connected SRS
14. Single Angle connected SRS
15. RHS hardware/no-internal-hardware
16. exact U.S./SI
17. legacy W-flange fingerprint invariance
18. RHS/SRS limitation vs geometry-valid state

## 49. Regression boundary

Direct remains unchanged.

Frozen Tee non-RHS behavior remains exact.

Only Tee RHS requests intentionally transition under C2.

Single-angle non-RHS R1-R4 remains exact.

Stage 3.3B production behavior/fingerprints remain exact.

C1 G1-G12 remain exact.

## 50. Visual acceptance

After 4/4 hosted CI verify:

### Tee support matrix
All seven support targets.

### Single-angle support matrix
All seven support targets.

### Connected rectangular profiles
RHS and SRS in both families.

### RHS full-through
One bolt through near wall/cavity/far wall, no internal hardware.

### SRS
Solid body and full-depth bolt.

### Trim
RHS stays hollow after trim; SRS stays solid.

### Status
Unsupported RHS/SRS mechanics appear as design limitations, not geometry errors.

## 51. Acceptance boundary

C2 accepted only if:
- Tee and Single-Angle share one support-target contract/editor
- all seven support options are real physical profiles
- RHS full-through uses both walls and no internal hardware
- SRS is a real solid profile
- SRS appears wherever RHS appears in the two integrated connected-member selectors
- non-RHS frozen Tee behavior exact
- Tee RHS successor transitions exact and explicit
- non-RHS single-angle behavior exact
- Stage 3.3B unchanged
- no new resistance equation
- unsupported RHS/SRS mechanics fail closed
- local + isolated QA + hosted 4/4 CI pass
- visual acceptance passes

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
