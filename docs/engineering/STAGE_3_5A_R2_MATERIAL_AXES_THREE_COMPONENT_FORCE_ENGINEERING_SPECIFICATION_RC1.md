# FRP Master Connection — Stage 3.5A-R2 Material-Axis Correction and Three-Component Force Expansion — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.5A-R2 is an additive successor to the accepted Stage 3.5A-R1 concrete-wall paired clip-angle product.

It authorizes:

1. correction of region-embedded material-axis visualization in the Stage 3.5A scene;
2. three signed user force components:
   - Major shear;
   - Minor shear;
   - Axial force.

It does not authorize user-applied moments or a moment-resisting connection.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `23129f4cba11fb8e12001b0f450b83f9cf24dc08`;
- subject:
  `fix: complete concrete-wall paired-angle connection`;
- commit count: `82`;
- clean worktree/index.

Hosted CI for this commit is accepted 4/4 green:

- GitHub Actions run #77;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `4m 56s`.

Expected current source trees from the Stage 3.5A-R1 completion report:

- backend/src:
  `7cd4d9ba337f6d10af23e73be2978b34c13d6010`;
- frontend/src:
  `84dd59f2e83f21d2d68bd59addcb0749db7d64eb`.

All Stage 2.3 / 3.2 / 3.3 / 3.4 freeze tags remain immutable.

## 3. Contract evolution

Accepted historical contracts:

- `3.5A-RC1`;
- `3.5A-R1-RC1`.

New successor contract:

`3.5A-R2-RC1`.

Historical contracts retain exact:

- request meaning;
- default loads;
- geometry;
- branch/wall wrenches;
- engineering fingerprints.

No silent translation that changes canonical identities.

## 4. Concrete-wall local frame

Reuse:

- `H_W`: horizontal along wall;
- `V_W`: vertical upward along wall;
- `N_W`: outward normal from concrete toward the connected member.

Require:

`H_W × V_W = N_W`.

Stage 3.5A-R2 force components are defined directly in this wall frame.

## 5. User force components

Normal UI inputs:

### Major shear

Symbolic component:

`V_major`

Direction:

`V_W`

### Minor shear

Symbolic component:

`V_minor`

Direction:

`H_W`

### Axial force

Symbolic component:

`P_axial`

Direction:

`N_W`

Complete force:

`F = (V_minor, V_major, P_axial)`.

Units:

- U.S.: kip;
- SI: kN.

## 6. Force sign convention

- `V_major > 0`: upward along `+V_W`;
- `V_major < 0`: downward;
- `V_minor > 0`: along `+H_W`;
- `V_minor < 0`: along `-H_W`;
- `P_axial > 0`: tension/pull away from wall along `+N_W`;
- `P_axial < 0`: compression toward wall along `-N_W`.

The UI shall show this sign convention adjacent to the inputs or in the axis/action legend.

## 7. User moment contract

User-applied moment remains exactly:

`M_user = (0,0,0)`.

No moment inputs in the normal Stage 3.5A-R2 UI.

Any API request containing a nonzero user free-moment component is rejected.

This remains a shear-category/simple connection.

## 8. Controlled successor default

Default:

- Major shear: `-4 kip`;
- Minor shear: `0 kip`;
- Axial force: `0 kip`.

All existing R1 default geometry remains unchanged.

Expected default branch and wall wrenches remain:

Positive branch:

- `F_+ = (0,-2,0) kip`;
- `M_+ = (8,0,6) kip-in`.

Negative branch:

- `F_- = (0,-2,0) kip`;
- `M_- = (8,0,-6) kip-in`.

Combined wall:

- `F_W = (0,-4,0) kip`;
- `M_W = (16,0,0) kip-in`.

## 9. Beam/member action reference

Reuse the backend-authoritative connected-member action reference from current Stage 3.5A-R1 geometry.

For the controlled W/I default:

`r_B = (0,0,4) in`.

Wall common reference:

`r_W = (0,0,0)`.

For other connected profiles, the current backend geometry remains authoritative for `r_B`.

No frontend reference calculation.

## 10. Exact combined wall wrench

For every accepted force vector:

`F_W = F`.

With zero user free moment:

`M_W = (r_B - r_W) × F`.

For the controlled default reference `r_B=(0,0,4)`:

`M_W = (-4 V_major, 4 V_minor, 0)` kip-in when force is in kip and distance in inches.

The axial component `P_axial` produces no wall moment when its line of action passes through the wall-frame normal reference axis.

Any geometry-dependent offset must be retained exactly.

No tolerance-based moment suppression.

## 11. Major-shear regression

Input:

- `V_major = -4 kip`;
- `V_minor = 0`;
- `P_axial = 0`.

Expected:

- combined wall force `(0,-4,0) kip`;
- combined wall moment `(16,0,0) kip-in`;
- exact historical R1 branch split/wrenches.

## 12. Pure axial-force case

Controlled axial benchmark:

- `V_major = 0`;
- `V_minor = 0`;
- `P_axial = +4 kip`;
- default centered geometry.

Expected combined wall:

- `F_W = (0,0,4) kip`;
- `M_W = (0,0,0) kip-in`.

The axial load is tension/pull away from the wall.

Equal branch sharing is eligible under exact pair symmetry:

- `F_+ = F_- = (0,0,2) kip`.

At default branch centroids:

Positive:

- `M_+ = (0,6,0) kip-in`.

Negative:

- `M_- = (0,-6,0) kip-in`.

After shifting both to the wall origin, the branch moments cancel exactly.

## 13. Pure axial compression case

Input:

`P_axial = -4 kip`.

Expected combined wall:

- `F_W = (0,0,-4) kip`;
- `M_W = (0,0,0)` for centered default geometry.

Equal pair force sharing may be retained under exact symmetry, but the physical partition between:

- anchor compression/tension;
- wall contact/bearing;
- clip-angle wall-leg response

is not calculated.

Required:

`WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

## 14. Pure minor-shear case

Controlled benchmark:

- `V_minor = +2 kip`;
- `V_major = 0`;
- `P_axial = 0`;
- default `r_B=(0,0,4)`.

Expected combined wall:

- `F_W = (2,0,0) kip`;
- `M_W = (0,8,0) kip-in`.

This is an exact wall-interface wrench.

No positive/negative branch split for the complete Minor-shear action is authorized.

Required:

`MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION = NOT_EVALUATED`.

The complete anchor layout + combined wall wrench remains in the external handoff.

## 15. Combined three-component case

Controlled benchmark:

- `V_minor = +2 kip`;
- `V_major = -4 kip`;
- `P_axial = +3 kip`;
- default reference.

Expected combined wall:

- `F_W = (2,-4,3) kip`;
- `M_W = (16,8,0) kip-in`.

Because `V_minor != 0`:

- complete branch allocation is `NOT_EVALUATED`;
- combined wall handoff remains exact;
- no fabricated 50/50 Minor-shear branch split.

## 16. Exact pair-symmetry applicability

The existing half-share equation is unchanged.

Stage 3.5A-R2 authorizes its use for exact actions satisfying:

- paired geometry/material symmetry;
- centered connected-member geometry;
- mirrored anchor geometry;
- `V_minor = 0`.

Then:

`F_+ = F_- = 0.5 (0, V_major, P_axial)`.

This is an applicability extension of the existing symmetry proof, not a new distribution equation.

If `V_minor != 0`, complete branch force allocation is not authorized.

## 17. Partial-action trace for nonzero Minor shear

When `V_minor != 0`, the backend may expose for traceability:

- symmetry-eligible in-plane sub-action `(0,V_major,P_axial)`;
- unallocated Minor-shear component `(V_minor,0,0)`.

It shall not present the partial symmetric split as the complete branch action.

The authoritative external-design object remains the full combined wall wrench and full anchor layout.

## 18. Common member-group demand decomposition

The common connected-member bolt axis is the paired-angle transverse axis corresponding to the wall `H_W` direction under the controlled geometry.

Therefore:

### In-plane action

`(V_major, P_axial)` lies in the connected member/clip-leg plane.

Where existing Stage 2.5A applicability holds, calculate the accepted in-plane demand vector using these components and the actual current geometry/reference.

### Bolt-axis / normal action

`V_minor` acts along the common bolt axes.

Retain it explicitly as normal action.

Do not generate:

- bolt tension capacity;
- prying capacity;
- through-thickness connector capacity.

For nonzero Minor shear:

`COMMON_MEMBER_GROUP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

## 19. Connected-profile applicability

All six R1 connected profiles remain available:

- Flat Plate;
- Angle;
- Channel;
- W/I;
- RHS;
- SRS.

The three-component force contract is profile-independent.

Existing profile-specific physical surfaces/paths remain controlling.

No new profile equation.

## 20. Axial FRP-side applicability

Axial `N_W` is in the connected-member/clip connected-leg plane.

Existing:

- bolt shear;
- FRP pin bearing;
- supported net/shear-out/block-shear handoffs

may execute only where their current geometry/direction/applicability contracts hold.

No new axial connector-body method.

## 21. Axial wall-leg limitation

For nonzero `P_axial`, the clip-angle wall legs may experience:

- bending;
- through-thickness action;
- prying;
- local contact;
- anchor tension/compression transfer.

Required:

`CLIP_ANGLE_WALL_LEG_AXIAL_TRANSFER_AND_PRYING = NOT_EVALUATED`.

Do not fabricate wall-leg resistance.

## 22. Minor-shear wall-side limitation

For nonzero `V_minor`:

`MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION = NOT_EVALUATED`.

Because complete branch allocation is not authorized, Stage 3.5A-R2 shall not fabricate positive/negative anchor-group wrenches for the full action.

The handoff still includes:

- positive and negative anchor-group geometry/coordinates;
- complete combined wall wrench;
- wall reference/frame;
- external-design limitations.

## 23. External anchor handoff — combined layout mode

The handoff shall support two modes.

### Branch-resolved mode

Used when `V_minor = 0` and symmetry proof passes.

Include:

- exact positive branch wrench;
- exact negative branch wrench;
- combined wall wrench;
- both group geometries.

### Combined-layout mode

Used when `V_minor != 0`.

Include:

- full combined wall wrench;
- all anchors from positive and negative groups in one complete layout representation while preserving group owner IDs;
- individual group centroids/coordinates;
- branch allocation status `NOT_EVALUATED`;
- explicit instruction for external anchor software to distribute the complete action.

Do not omit the two physical group identities.

## 24. One-anchor default limitation

The R1 default remains one anchor per clip angle.

For `1 × 1` groups:

`WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION = EXTERNAL_DESIGN_REQUIRED`.

This remains true even when branch splitting is otherwise available.

Full group wrenches/combined handoff remain exact.

## 25. Connection qualification for nonmajor force

The original Stage 3.5A source basis remains the pure reaction-shear/simple-connection case.

When either:

- `V_minor != 0`; or
- `P_axial != 0`,

also require:

`NONMAJOR_FORCE_CONNECTION_QUALIFICATION = NOT_EVALUATED`.

Exact force/wrench transfer and existing supported component checks may still execute. This limitation prevents an unsupported whole-connection qualification claim.

## 27. External design limitations

Always preserve:

- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

Conditionally include:

- `WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION`;
- `MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION`;
- `WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION`;
- `CLIP_ANGLE_WALL_LEG_AXIAL_TRANSFER_AND_PRYING`;
- `COMMON_MEMBER_GROUP_BOLT_AXIS_RESPONSE`.

No ordinary whole-connection PASS.

## 27. Status aggregation

Required precedence:

1. invalid geometry/input -> invalid/rejected;
2. supported numerical failure -> `FAIL`;
3. otherwise required internal/external limitations -> `NOT_EVALUATED` / external design required;
4. ordinary whole-connection `PASS` prohibited.

Force-component limitations are not geometry errors.

## 28. Load UI

Replace the single Reaction shear field in the successor UI with:

- `Major shear`;
- `Minor shear`;
- `Axial force`.

Show units.

Add concise sign/direction help:

- Major: wall vertical;
- Minor: wall horizontal;
- Axial +: pull away from wall.

Do not add moment fields.

The wall axis/action legend shall make the directions visible.

## 29. Action display

Display backend-authored:

- user force `(H_W,V_W,N_W)`;
- user moment zero;
- current action reference;
- combined wall wrench;
- branch wrenches when authorized;
- branch-allocation limitation when not authorized.

Label generated moments:

`Eccentricity-induced transfer moment`.

## 30. Material-axis audit requirement

Before changing any material basis, audit the Stage 3.5A-R1 default scene.

For each visible FRP region record:

- component owner;
- physical element;
- material region;
- backend `LW/CW/TT`;
- rendered presentation vectors;
- physical region plane;
- physical through-thickness normal.

At minimum inspect:

### Connected W/I

- web;
- top flange;
- bottom flange.

### Positive clip angle

- connected leg;
- wall/concrete-side leg.

### Negative clip angle

- connected leg;
- wall/concrete-side leg.

Reproduce the owner's observed defects:

- W/I web TT visually collinear with LW;
- concrete-side clip-angle TT visually collinear with CW;
- W/I flange TT indicator absent.

Identify the first loss/corruption boundary before mutation.

## 31. Material-basis invariants

For every FRP physical region:

- `|LW| = |CW| = |TT| = 1`;
- `LW · CW = 0`;
- `LW · TT = 0`;
- `CW · TT = 0`;
- `TT` is parallel to the physical through-thickness normal, up to the exact controlled sign;
- `LW` and `CW` lie in the physical region plane.

Also require:

`|cross(LW,CW) · TT| = 1`

for the exact orthonormal basis orientation.

No tolerance should be used for the existing ±1/0 controlled basis records; transformed vectors shall retain deterministic exactness where the transform is orthogonal.

## 32. Backend R14B preservation

The Stage 3.5A-R2 correction is expected to preserve the accepted R14B material bases.

If backend vectors already satisfy Section 30:

- backend material architecture production code shall not change for this issue;
- correct only transport/scene/presentation transforms/binding.

If a backend basis violates Section 30:

**STOP before mutation** and report that a new engineering-basis authority is required.

Do not silently alter R14B vectors.

## 33. Mirrored/reflected geometry rule

Presentation geometry may involve reflected/mirrored components.

Material vectors shall remain backend-authored global/scene directions and shall not be:

- transformed twice;
- passed through a negative-determinant quaternion conversion;
- collapsed by owner de-duplication;
- replaced by primitive-local axes.

The scene transformation used to render reflected solids shall not corrupt the material basis.

## 34. TT presentation

Every FRP region has one TT presentation marker.

Use the accepted R14C shape convention:

- camera-facing dot/cross where normal points toward/away from camera;
- tangent normal marker where required by current implementation.

The absence of a visible arrow does not permit omission of the TT scene object.

Automated tests shall assert TT presentation object creation independently of camera occlusion.

## 35. W/I material-axis coverage

Require distinct region presentations for:

- web;
- top flange;
- bottom flange.

For each:

- LW present;
- CW present;
- TT present.

The web TT shall be normal to the web plane.

Flange TT shall be normal to the flange planes.

No shared W/I material triad.

## 36. Clip-angle material-axis coverage

For both positive and negative clip angles:

- connected-leg LW/CW/TT;
- wall-leg LW/CW/TT.

The wall-leg TT shall be normal to the wall-leg plate plane and shall not be collinear with CW.

Positive and negative owner identities remain distinct.

## 37. Six-profile material-axis regression

After correction, verify all connected profiles:

- Flat Plate;
- Angle;
- Channel;
- W/I;
- RHS;
- SRS.

RHS:

- axes on physical walls only;
- no cavity axes.

SRS:

- accepted solid-region basis.

Concrete:

- no FRP LW/CW/TT.

## 38. Material-axis toggle semantics

Preserve:

- Off -> no material-axis indicators / legend;
- On -> complete applicable indicators / legend;
- no API call;
- no design staleness;
- no camera reset;
- no engineering fingerprint effect.

## 39. Preview path

Preview shall:

- validate three force inputs;
- retain user moment zero;
- construct geometry;
- compute supported common-group in-plane demand;
- retain Minor-shear normal action;
- compute exact combined wall wrench;
- branch-resolve only where symmetry eligibility passes;
- build correct handoff mode;
- expose material axes;
- execute zero resistance equations.

## 40. Design path

Explicit design check:

- current accepted preview only;
- existing supported member/FRP checks only;
- no bolt-axis tension/prying resistance;
- no wall-leg axial/prying method;
- no anchor/concrete capacity;
- limitations retained.

## 41. API strictness

Successor contract:

`3.5A-R2-RC1`.

Accept exactly:

- Major shear;
- Minor shear;
- Axial force;
- user moments absent or exactly zero under schema convention.

Reject:

- client nonzero moments;
- unsupported extra action fields;
- nonfinite forces;
- invalid units;
- extra fields;
- unknown contract.

Historical `3.5A-RC1` and `3.5A-R1-RC1` remain accepted unchanged.

## 42. U.S./SI

Representative exact conversions:

- `4 kip = 17.792886461042 kN`;
- `3 kip = 13.3446648457815 kN`;
- `2 kip = 8.896443230521 kN`;
- `16 kip-in = 1.807757264441867 kN-m`;
- `8 kip-in = 0.9038786322209335 kN-m`;
- `6 kip-in = 0.6779089741657001 kN-m`.

Equivalent physical force vectors, combined wall wrenches, handoffs, supported demands, and engineering fingerprints shall match.

## 43. Fingerprints

New successor fingerprints include:

- three-component force vector;
- action reference;
- applicability/branch-allocation mode;
- full combined wall wrench;
- anchor-layout handoff mode;
- method/contract version.

Presentation material-axis corrections do not change engineering fingerprints.

Historical Stage 3.5A/R1 fingerprints remain exact.

Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee fingerprints remain exact.

## 44. Required controlled golden cases

At minimum:

G1. Historical `3.5A-RC1` exact.
G2. Historical `3.5A-R1-RC1` exact.
G3. R2 default major `-4`, minor `0`, axial `0` reproduces R1 wrenches.
G4. Pure axial tension `+4 kip`: combined `F=(0,0,4)`, `M=0`.
G5. Pure axial tension exact half-share branch forces.
G6. Pure axial tension branch moments `(0,±6,0)` cancel at wall origin.
G7. Pure axial compression `-4 kip`: combined `F=(0,0,-4)`, `M=0`, external contact/anchor partition limitation.
G8. Pure minor shear `+2 kip`: combined `F=(2,0,0)`, `M=(0,8,0)`.
G9. Pure minor shear branch allocation `NOT_EVALUATED`.
G10. Combined `(minor,major,axial)=(2,-4,3)` -> `F=(2,-4,3)`, `M=(16,8,0)`.
G11. Combined nonzero minor uses combined-layout external handoff.
G12. Major+axial with zero minor remains symmetry eligible.
G13. Minor shear retained as common-group bolt-axis action; no generated tension/prying.
G14. Axial wall-leg/prying limitation.
G15. User-applied moment rejected.
G16. Force sign convention.
G17. 1×1 anchor internal distribution remains external required.
G18. Multi-anchor nominal trace only where equilibrium applies.
G19. W/I web material basis orthonormal and TT normal to web.
G20. W/I top flange TT present/normal.
G21. W/I bottom flange TT present/normal.
G22. Positive clip wall-leg TT present/normal.
G23. Negative clip wall-leg TT present/normal.
G24. No LW/TT or CW/TT collinearity in any Stage 3.5A FRP region.
G25. Six-profile material-axis matrix.
G26. RHS cavity has no material axes.
G27. Concrete has wall frame but no FRP material axes.
G28. Material-axis toggle presentation-only.
G29. Preview zero resistance.
G30. Supported failure precedence / limitations.
G31. Exact U.S./SI major/minor/axial representative cases.
G32. External handoff deterministic in branch-resolved and combined-layout modes.
G33. Historical external handoff unchanged for R1 default.
G34. Frozen Direct/Tee/Clip-Angle/Multi-Member-Tee regressions exact.

## 45. Deliberate exclusions

Not authorized:

- user-applied moment;
- moment-resisting connection;
- bolt-axis tension resistance;
- prying resistance;
- clip-angle wall-leg axial bending/prying resistance;
- internal minor-shear paired branch distribution;
- concrete capacity;
- anchor capacity;
- axial contact/anchor force partition;
- external anchor-software result import;
- new profile/support families;
- Stage 3.5B direct side-lap connection.

## 46. Acceptance boundary

Stage 3.5A-R2 is accepted only if:

- material-axis audit proves correct backend basis or stops for new authority;
- displayed TT is correct/present on W/I web/flanges and both clip-angle legs;
- all Stage 3.5A FRP regions satisfy orthonormal basis rules;
- Major/Minor/Axial inputs are available;
- no user moment input exists;
- default R1 behavior remains exact;
- axial and minor force handoffs remain physically exact;
- no unauthorized 50/50 Minor-shear split;
- no generated bolt-tension/prying method;
- external anchor handoff remains complete;
- historical contracts/fingerprints remain exact;
- frozen families remain exact;
- full local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
