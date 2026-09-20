# FRP Master Connection — Stage 4.1A W/I Major-Axis Moment Splice — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 4.1A is the first physical Moment Connections product.

It creates a W/I beam moment splice with:

- double web splice plates;
- one outer full-width cover plate on each flange;
- two split inner cover plates on each flange;
- common through-bolts;
- complete component-strength design with mandatory rational-method engineering review.

## 2. Accepted starting baseline

Expected repository state:

- branch `main`;
- `HEAD == origin/main == remote main`:
  `23813a5c2d015b74591e577fa95715950c34912c`;
- subject:
  `feat: add W/I moment component resultant engine`;
- commit count:
  `97`;
- clean worktree/index.

Calculation Slice 5 hosted CI:

GitHub Actions run #92:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `5m 26s`.

## 3. Immutable freeze tags

Preserve exactly:

- Stage 2.3 `stage-2.3-interface-geometry-freeze`;
- Stage 3.2 `stage-3.2-tee-connection-freeze`;
- Stage 3.3 `stage-3.3-clip-angle-family-freeze`;
- Stage 3.4 `stage-3.4-multi-member-tee-family-freeze`;
- Stage 3.5 `stage-3.5-concrete-support-shear-family-freeze`;
- Stage 3.6 `stage-3.6-wi-web-splice-family-freeze`;
- Stage 3.7 `stage-3.7-column-base-shear-family-freeze`.

No tag creation, move, deletion, or push in Stage 4.1A.

## 4. Accepted Calculation Slice 5 authority

Require exact accepted commit:

`23813a5c2d015b74591e577fa95715950c34912c`.

Controlled Calculation Slice 5 artifacts:

- Decision:
  `1E3DFA8727953087C883F5E8627778960CBD6AFECCDC357A35C89D99A6139DC9`
- Engineering Specification RC1:
  `33C88001777BD11CAF1EE724B5F2EFFCB84D9C0232578091755FA9751BEB49B1`
- Golden Benchmarks RC1:
  `8854FE7CB56B7D7CEE1FF30A5EA554B83D400386FAE4B1AFDCABC8DF7A1E3D82`
- Authority Ledger RC1:
  `246EC10341A1E4011069231C296B6CCA1346DACC74455F42EFAD3C0C98937DA9`
- Implementation Order:
  `27E3B713F358CFBB1B27A15F3745A7FF6D263FEF0F87AC4534062723F9B60755`.

Stage 4.1A shall call Slice 5 and shall not duplicate its section-integration equations in product orchestration.

## 5. Inherited Stage 3.6 authority

Stage 3.6 W/I web-splice family remains frozen.

Stage 4.1A may reuse its implementation architecture and accepted methods through a new successor-specific adapter but shall not alter the historical Stage 3.6 public contract or historical fingerprints.

Inherited concepts include:

- symmetric double web splice plates;
- positive beam-end gap;
- Plate/Web/Plate common bolts;
- Stage 2.5A exact group demand;
- existing local FRP connection checks;
- clear splice-body geometry;
- `RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`;
- `RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`;
- physical two-plane web-bolt shear logic;
- source-pending fastener behavior;
- rational-review / Section 2.3.2 qualification behavior.

Stage 4.1A differs by supplying the Slice 5 web component free moment to the web subsystem.

## 6. Source/provenance basis

Review and record relevant ASCE/SEI 74-23 provisions including:

- Section 2.3.2;
- Section 2.9;
- Section 8.1;
- Section 8.1.2;
- Section 8.2.2 through 8.2.5;
- Section 8.3.1;
- Section 8.3.2;
- Section 8.3.4.2;
- Commentary C8.1.3 and C8.3.4.

Controlled interpretation:

- connection actions/deformations must match structural-analysis assumptions;
- eccentricity is retained;
- flexural splices transmit applicable force and moment;
- flange tension/compression states matter;
- web/shear part retains shear, bolt-group eccentricity effects, and its moment proportion;
- Chapter 8 gives local component provisions once connection load effects are known;
- moment-resistant FRP connections are outside normal prescriptive coverage and require Section 2.3.2 qualification.

The balanced flange force-line model, rational beam-flange face-sublayer model, and unequal two-plane bolt model are project rational methods.

## 7. Product contract

Product ID:

`WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE`.

Contract:

`4.1A-RC1`.

Selector category:

`Moment Connections`.

User-facing connection label may be:

`W/I Beam Moment Splice`.

No Channel selector.

## 8. Splice frame

Define right-handed:

- `L_S`: Beam A -> Beam B longitudinal;
- `V_S`: vertical / beam depth axis, positive toward top flange;
- `T_S`: beam transverse axis.

Require:

`L_S × V_S = T_S`.

Joint reference:

`r_J=(0,0,0)`.

Joint plane:

`L_S=0`.

## 9. Beam identities

Exactly:

- `BEAM_A`;
- `BEAM_B`.

Beam A occupies negative `L_S`.

Beam B occupies positive `L_S`.

Both are identical W/I profiles in RC1.

Reject unequal section dimensions/materials.

## 10. W/I geometry

Reuse the existing authoritative W/I geometry.

Default:

- depth `d=10 in`;
- flange width `b_f=8 in`;
- web thickness `t_w=0.5 in`;
- flange thickness `t_f=0.5 in`;
- displayed length away from joint `18 in`.

No Channel/asymmetric profile.

## 11. Beam-end gap

Input:

`beam_end_gap`.

Require:

`beam_end_gap > 0`.

Default:

`0.5 in`.

Beam A end:

`L_S=-beam_end_gap/2`.

Beam B end:

`L_S=+beam_end_gap/2`.

No direct beam-end bearing transfer is credited.

## 12. Normal user actions

At `r_J`:

### Axial

`P_L`, signed.

Positive = tension across splice.

Negative = compression across splice.

### Major shear

`V_V`, signed along `V_S`.

### Major-axis moment

`M_T`, signed about `T_S`.

Positive uses the Slice 5 sign convention: longitudinal tension at positive `V_S`.

Require zero / reject:

- `V_T`;
- `M_V`;
- `M_L`.

## 13. Default actions

Default:

- `P_L=+20 kip`;
- `V_V=-10 kip`;
- `M_T=+100 kip-in`.

These defaults exercise top-flange tension, web combined action, and bottom-flange compression.

## 14. Canonical component decomposition

Call Calculation Slice 5 exactly once on the canonical joint section demand.

Receive:

### Top flange
- `N_top`;
- `m_top`;
- zero major shear;
- top stress extrema/state.

### Web
- `N_web`;
- `V_web=V_V`;
- `m_web`;
- web stress extrema/state.

### Bottom flange
- `N_bottom`;
- `m_bottom`;
- zero major shear;
- bottom stress extrema/state.

Require exact Slice 5 equilibrium before proceeding.

## 15. Interface-action versus material-state signs

The canonical Slice 5 component state represents the physical W/I section stress state.

At the common joint reference:

Beam A physical interface action:

`W_A=+W_component`.

Beam B physical interface action:

`W_B=-W_component`.

Do not rerun Slice 5 with sign-reversed Beam B actions to classify the Beam B material state.

The opposite Beam B traction is caused by the opposite cut-face normal.

## 16. Web splice geometry

Reuse Stage 3.6 web splice geometry and defaults:

- two symmetric web splice plates;
- default plate length `16 in`;
- default plate height `8 in`;
- default plate thickness `0.5 in`;
- mirrored Beam A / Beam B web bolt groups;
- default 2 × 2 group per beam side;
- default group centroids at `L_S=±4 in`;
- default web bolt diameter `0.5 in`;
- default web hole diameter `0.563 in`.

The web plates bridge the positive gap.

## 17. Web component demand

Stage 4.1A web subsystem receives at `r_J`:

- `N_web`;
- `V_web`;
- `m_web`.

Beam A and Beam B local web group wrenches include:

- the signed interface force;
- the signed Slice 5 free component moment;
- exact generated moment from reference translation.

The existing Stage 3.6 frozen no-user-moment contract is not modified.

## 18. Web body / web bolt design

Reuse Stage 3.6B RC2 logic as applicable:

- local FRP checks;
- pair-body resultants;
- rational plate-body interaction;
- Calculation Slice 4 pure-mode strengths;
- Plate/Web/Plate common bolt checks;
- source-pending behavior;
- review/disclaimer provenance.

No minor shear exists in RC1, so the historical minor-shear bolt-axis limitation is not activated by normal Stage 4.1A inputs.

## 19. Flange splice system count

For each of the top and bottom beam flanges create exactly:

- one outer full-width splice plate;
- one negative-`T_S` inner strip;
- one positive-`T_S` inner strip.

Total flange splice plates:

`6`.

Together with the two web splice plates:

total FRP splice plates:

`8`.

## 20. Flange splice plate material basis

All flange splice plates:

- `LW || L_S`;
- `CW || T_S`;
- `TT || ±V_S`.

Top/bottom and outer/inner material axes are backend-authored.

The two inner strips and the outer plate use one common RC1 flange-splice material definition.

## 21. Flange plate geometry

RC1 top/bottom flange splice geometry is identical.

Inputs:

- flange splice plate length `L_fp`;
- flange splice plate thickness `t_fp`;
- inner strip width `b_i`.

Default:

- `L_fp=16 in`;
- `t_fp=0.5 in`;
- `b_i=3 in`.

Outer plate width is not separately input:

`b_outer=b_f`.

Require:

- `L_fp>0`;
- `t_fp>0`;
- `b_i>0`;
- both inner strips fit outside the web;
- no positive-volume overlap with web;
- no flange/plate overlap other than intended face contact.

## 22. Flange plate through-depth positions

Top flange-region centroid:

`y_top=+(d-t_f)/2`.

Bottom:

`y_bottom=-(d-t_f)/2`.

### Top outer plate centroid

`y_top,o=+d/2+t_fp/2`.

### Top inner combined centroid

`y_top,i=+d/2-t_f-t_fp/2`.

### Bottom outer plate centroid

`y_bottom,o=-d/2-t_fp/2`.

### Bottom inner combined centroid

`y_bottom,i=-d/2+t_f+t_fp/2`.

For equal outer/inner thickness:

the force lines are symmetric around the associated beam-flange centroid.

## 23. Inner-strip transverse placement

Each inner strip outer edge aligns with the applicable beam flange free edge.

Positive strip:

`T_S in [b_f/2-b_i, b_f/2]`.

Negative strip:

`T_S in [-b_f/2, -b_f/2+b_i]`.

Inner strip center magnitude:

`t_i,c=b_f/2-b_i/2`.

Default:

`t_i,c=2.5 in`.

Clearance from each strip inner edge to the nearest web face:

`c_i=(b_f/2-b_i)-t_w/2`.

Default:

`c_i=0.75 in`.

Require:

`c_i>=0`.

## 24. Flange bolt topology

Each physical beam-side flange group has:

- exactly two transverse bolt lines, one centered on each inner strip;
- `n_L` bolts per line along `L_S`;
- identical left/right line geometry;
- identical Beam A/Beam B mirror geometry;
- identical top/bottom geometry.

Input:

`flange_bolts_per_line = n_L`.

RC1 require:

`1 <= n_L <= 3`.

Default:

`n_L=2`.

## 25. Flange bolt longitudinal geometry

Inputs:

- longitudinal pitch `s_L`;
- beam-side group centroid distance from joint `x_g`.

Default:

- `s_L=3 in`;
- `x_g=4 in`.

Beam A flange-group centroid:

`L_S=-x_g`.

Beam B:

`L_S=+x_g`.

For `n_L=2`, default longitudinal bolt coordinates are:

Beam A:

`L=-5.5, -2.5 in`.

Beam B:

`L=+2.5, +5.5 in`.

## 26. Flange bolt transverse geometry

Each bolt line is centered on the corresponding inner strip.

Default line coordinates:

`T_S=±2.5 in`.

Default transverse gauge:

`g_T=5 in`.

No flange bolt is placed through the web.

## 27. Flange bolt size / holes

Inputs:

- nominal bolt diameter `d_b,f`;
- nominal hole diameter `d_h,f`;
- controlled bolt grade/thread condition.

Default:

- `d_b,f=0.5 in`;
- `d_h,f=0.563 in`.

Reuse existing bolt/hole validation and source authority.

## 28. Physical flange bolt paths

Top flange:

`TOP_OUTER_FLANGE_SPLICE_PLATE -> TOP_BEAM_FLANGE -> TOP_INNER_FLANGE_SPLICE_PLATE`.

Bottom:

`BOTTOM_OUTER_FLANGE_SPLICE_PLATE -> BOTTOM_BEAM_FLANGE -> BOTTOM_INNER_FLANGE_SPLICE_PLATE`.

The corresponding positive/negative inner strip is selected by bolt `T_S` coordinate.

One shank per physical bolt axis.

No duplicate bolts.

## 29. Flange bolt axis / hardware

Top common bolts are normal to the flange plane.

Bottom common bolts are normal to the flange plane.

Backend returns authoritative physical endpoints/layer order.

Default hardware convention:

- head/washer exterior to outer flange splice plate;
- nut/washer exterior to inner flange splice plate.

No hardware inside the beam flange.

No web interference.

## 30. Complete-hole containment

Validate every flange hole independently in:

- outer splice plate;
- beam flange;
- corresponding inner strip.

Also validate:

- beam-end hole containment;
- plate outer longitudinal ends;
- plate joint-side ligament;
- flange free edges;
- inner strip free edges;
- web clearance;
- pitch/gauge requirements;
- bolt-line count limits.

No automatic bolt relocation.

## 31. Flange clear-body region

For the flange splice plates define the unperforated central body between the joint-side boundaries of the nearest Beam A / Beam B flange bolt holes.

Derive from actual geometry.

For default:

nearest centers:

`L=±2.5 in`.

Hole radius:

`0.2815 in`.

Clear boundaries:

`L=±2.2185 in`.

Clear-body length:

`a_body,f=4.437 in`.

No hard-coded production value.

## 32. Flange force-line equilibrium method

Method:

`RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1`.

For each flange component:

- `N_f` = Slice 5 flange longitudinal force;
- `m_f` = Slice 5 local component moment;
- `e_o=y_o-y_f`;
- `e_i=y_i-y_f`.

Require:

`e_o*e_i<0`.

Solve:

`F_o = (m_f-e_i N_f)/(e_o-e_i)`.

`F_i = (e_o N_f-m_f)/(e_o-e_i)`.

Exact proof:

`F_o+F_i=N_f`.

`e_oF_o+e_iF_i=m_f`.

## 33. Inner-strip allocation

Because RC1 is transversely symmetric:

`F_i,positive=F_i/2`.

`F_i,negative=F_i/2`.

Require exact equality.

If left/right geometry/material/bolt pattern symmetry fails:

`FLANGE_INNER_STRIP_EQUAL_ALLOCATION = NOT_EVALUATED`

and the full flange system is not allowed to pass.

## 34. Outer plate group demand

The continuous outer plate receives total `F_o`.

At each beam side, apply signed equal/opposite interface force to the complete two-line flange bolt group.

Reference force line:

outer plate centroid with `T_S=0`.

Because the group is symmetric in `T_S`, zero minor/torsional action is generated.

Use Stage 2.5A for actual per-bolt in-plane demand.

## 35. Inner strip group demand

Each inner strip receives `F_i/2`.

At each beam side, apply its signed interface force through the strip/bolt-line centroid.

Use Stage 2.5A for actual per-bolt in-plane demand.

Do not infer from outer-plane demand.

## 36. Beam-flange face-sublayer method

Method:

`RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1`.

For local FRP connection failure-path evaluation only, create two rational sublayers of the connected beam flange:

### Outer face sublayer

- width = actual flange width `b_f`;
- effective thickness = `t_f/2`;
- material axes = actual beam flange axes;
- holes = complete two-line flange group;
- signed interface action = `F_o`.

### Inner face sublayer

- width = actual flange width `b_f`;
- effective thickness = `t_f/2`;
- material axes = actual beam flange axes;
- holes = complete two-line flange group;
- signed interface action = `F_i`.

No perpendicular-web exemption is used to reduce these rational sublayer local checks.

The sublayers are calculation constructs only.

## 37. Face-sublayer local checks

Reuse accepted local FRP connection formulas/applicability on the rational sublayers, including where applicable:

- pin bearing;
- net tension;
- shear-out;
- cleavage;
- block shear / accepted equivalent local failure path.

Use actual signed loaded-edge direction.

Do not merge opposite face demands before local checks.

This prevents the flange local moment from disappearing when `F_o` and `F_i` differ or oppose one another.

## 38. Outer flange splice plate local checks

Evaluate the outer plate at each beam-side group using:

- full width `b_f`;
- thickness `t_fp`;
- actual two-line bolt grid;
- signed `F_o`;
- flange splice plate material basis.

Reuse accepted local FRP checks.

## 39. Inner flange splice plate local checks

Evaluate each inner strip separately using:

- width `b_i`;
- thickness `t_fp`;
- one bolt line;
- signed `F_i/2`;
- flange splice plate material basis.

Return distinct positive/negative strip result IDs.

## 40. Flange splice plate clear-body tension

If branch force is tensile:

Use Calculation Slice 4 longitudinal tension for the clear unperforated plate body.

Outer:

- width `b_f`;
- thickness `t_fp`;
- demand `|F_o|`.

Inner each:

- width `b_i`;
- thickness `t_fp`;
- demand `|F_i|/2`.

Retain Slice 4 provenance.

## 41. Flange splice plate clear-body compression

If branch force is compressive:

Use Calculation Slice 4 longitudinal compression.

Rational panel mapping:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

Use:

- `a=a_body,f`;
- `b=actual plate width`;
- `t=t_fp`;
- accepted adjusted material properties/factors.

Outer and each inner strip are evaluated separately.

Retain all Slice 4 advisories.

## 42. Zero branch force

If a flange branch force is exactly zero:

- body resistance = `NOT_REQUIRED_ZERO_FORCE`;
- local bolt/plate demand = exact zero;
- no artificial epsilon demand.

The other branch remains fully evaluated if nonzero.

## 43. Flange common-bolt physical shear planes

Every flange common bolt has exactly two physical shear planes:

1. outer splice plate / beam flange;
2. beam flange / inner splice plate.

Derive from physical layer path.

## 44. Unequal two-plane bolt method

Method:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

For each physical bolt:

- obtain actual signed outer-plane vector `Q_o,i`;
- obtain actual signed inner-plane vector `Q_i,i`.

No equal-plane assumption.

For each plane independently:

`V_plane=|Q_plane|`.

Reuse accepted Section 8.3.2.1 shear-rupture strength:

`phi R_plane=0.75 F_nv A_b`

when the bolt grade/thread/source authority permits.

Plane utilization:

`U_plane=V_plane/(phi R_plane)`.

Bolt utilization:

`U_bolt=max(U_outer,U_inner)`.

Both planes must pass.

## 45. No blind double-shear sum

Do not calculate flange bolt utilization from:

`(|Q_outer|+|Q_inner|)/(2 phi F_nv A_b)`

and do not assume:

`Q_outer=Q_inner`.

An equal-plane special case may be displayed only when exact.

## 46. Fastener source pending

Preserve current source behavior.

For ASTM F593 if controlled `F_nt/F_nv` is unavailable:

- no invented numerical capacity;
- explicit source-required / `NOT_EVALUATED` state.

Existing verified/custom strength authority may be used.

## 47. Bolt tension / pull-through / prying

RC1 normal actions create no authoritative bolt-axis force in flange or web bolts.

Therefore:

- bolt tension demand = zero;
- combined Eq. 8-3 tension/shear is not invoked for zero tension;
- pull-through from applied bolt-axis force = `NOT_REQUIRED`.

The product shall still carry engineering-review metadata that actual out-of-plane deformation/prying/contact and unequal-plane bolt bending are not experimentally qualified by this strength model.

Do not create a numerical prying force.

## 48. Whole flange-system equilibrium

For each top/bottom flange prove exact:

`F_o+F_i=N_f`.

`y_oF_o+y_iF_i = y_fN_f+m_f`.

At the joint, prove exact:

sum of:

- top outer/inner branch global contributions;
- web component global wrench;
- bottom outer/inner branch global contributions

recovers the original:

- `P_L`;
- `V_V`;
- `M_T`.

No force/moment loss.

## 49. Beam A / Beam B equilibrium

Beam A component interface actions sum to the canonical transfer wrench.

Beam B component interface actions sum to the exact negative canonical transfer wrench.

Each plate subsystem returns equal/opposite side actions.

No foundation/support handoff exists in a splice.

## 50. Default flange geometry benchmark

Default W/I:

- `d=10 in`;
- `b_f=8 in`;
- `t_w=0.5 in`;
- `t_f=0.5 in`.

Flange plates:

- `L_fp=16 in`;
- `t_fp=0.5 in`;
- `b_i=3 in`.

Derived:

- top flange centroid `+4.75 in`;
- top outer centroid `+5.25 in`;
- top inner centroid `+4.25 in`;
- bottom flange centroid `-4.75 in`;
- bottom outer centroid `-5.25 in`;
- bottom inner centroid `-4.25 in`;
- inner strip centers `T_S=±2.5 in`;
- inner strip/web clearance `0.75 in`.

## 51. Default flange bolt benchmark

- `n_L=2`;
- `s_L=3 in`;
- `x_g=4 in`;
- `d_b=0.5 in`;
- `d_h=0.563 in`.

Beam A flange bolt coordinates:

`(L,T)=(-5.5,-2.5), (-2.5,-2.5), (-5.5,+2.5), (-2.5,+2.5)`.

Beam B is exact mirror.

Top/bottom share the same plan coordinates.

## 52. Default Slice 5 component benchmark

For:

- `P_L=+20 kip`;
- `V_V=-10 kip`;
- `M_T=+100 kip-in`;

require exact accepted Slice 5 values:

Top:

`N_top=15.402961500493583415597235932872655478775913129318854886475814412635735439289240 kip`

`m_top=0.039486673247778874629812438302073050345508390918065153010858835143139190523198420 kip-in`

Web:

`N_web=7.2 kip`

`V_web=-10 kip`

`m_web=14.392892398815399802566633761105626850937808489634748272458045409674234945705824 kip-in`

Bottom:

`N_bottom=-2.6029615004935834155972359328726554787759131293188548864758144126357354392892397 kip`

`m_bottom=0.039486673247778874629812438302073050345508390918065153010858835143139190523198420 kip-in`.

## 53. Default top flange branch benchmark

With `e_o=+0.5 in`, `e_i=-0.5 in`:

`F_top,o=7.7409674234945705824284304047384007897334649555774925962487660414610069101678184 kip`.

`F_top,i=7.6619940769990128331688055281342546890424481737413622902270483711747285291214216 kip`.

Each inner strip:

`3.8309970384995064165844027640671273445212240868706811451135241855873642645607108 kip`.

## 54. Default bottom flange branch benchmark

With `e_o=-0.5 in`, `e_i=+0.5 in`:

`F_bottom,o=-1.3409674234945705824284304047384007897334649555774925962487660414610069101678182 kip`.

`F_bottom,i=-1.2619940769990128331688055281342546890424481737413622902270483711747285291214214 kip`.

Each inner strip:

`-0.6309970384995064165844027640671273445212240868706811451135241855873642645607107 kip`.

## 55. Default per-bolt flange plane demands

For 2 transverse lines and `n_L=2`:

Top outer plane per bolt:

`1.9352418558736426456071076011846001974333662388943731490621915103652517275419546 kip`.

Top inner plane per bolt:

`1.9154985192497532082922013820335636722606120434353405725567620927936821322803554 kip`.

Bottom outer plane per bolt:

`-0.33524185587364264560710760118460019743336623889437314906219151036525172754195455 kip`.

Bottom inner plane per bolt:

`-0.31549851924975320829220138203356367226061204343534057255676209279368213228035535 kip`.

Signed vectors remain available; capacity uses magnitude.

## 56. Analytical bolt benchmark

Test-only F3125 benchmark:

- `d=0.5 in`;
- `F_nv=68 ksi`;
- `phi=0.75`;
- threads excluded.

Use accepted bolt area authority.

Per-plane design shear strength:

`10.013826583317465947599675784203415443378477460508149804357635887981164795036625 kip`.

Expected top outer-plane utilization:

`0.19325697721764612430021933203443990807028918305764098693451146780825660582291138`.

Expected top inner-plane utilization:

`0.19128536961493600264851336047726341441521583901502069529061724756944558148274701`.

Do not use these test-only bolt values to override production source selection.

## 57. Test-only flange-body arithmetic benchmark

For arithmetic tests only use:

- longitudinal tension design stress `12 ksi`;
- longitudinal compression design stress `10 ksi`.

These do not replace Calculation Slice 4 in production.

Default branch body utilizations:

Top outer tension:

`0.16127015465613688713392563343205001645278051990786442908851595919710431062849622`.

Top inner strip tension:

`0.21283316880552813425468904244817374136229022704837117472852912142152023692003949`.

Bottom outer compression arithmetic:

`0.033524185587364264560710760118460019743336623889437314906219151036525172754195455`.

Bottom inner strip compression arithmetic:

`0.042066469233300427772293517604475156301414939124712076340901612372490950970714047`.

Production compression still uses governing Slice 4 rupture/buckling resistance.

## 58. Test-only beam-flange face-sublayer arithmetic

For arithmetic only use design bearing stress:

`20 ksi`.

Effective sublayer thickness:

`t_f/2=0.25 in`.

For `d_b=0.5 in`, test-only bearing design strength per bolt:

`2.5 kip`.

Top outer-face benchmark utilization:

`0.77409674234945705824284304047384007897334649555774925962487660414610069101678184`.

Top inner-face benchmark utilization:

`0.76619940769990128331688055281342546890424481737413622902270483711747285291214216`.

Production uses existing source-controlled local FRP strengths/factors.

## 59. Default web body arithmetic extension

For regression of the added Slice 5 web free moment, use the inherited Stage 3.6 test-only web plate values:

- plate `h=8 in`;
- `t=0.5 in`;
- test-only `f_t,d=12 ksi`;
- `f_c,d=10 ksi`;
- `f_v,d=5 ksi`;
- clear boundaries `L=±2.2185 in`.

Pair internal moment function shall retain both:

- Slice 5 web component free moment;
- shear-generated linear moment variation.

At `L=+2.2185 in` for the default signs:

pair moment magnitude/sign result:

`36.577892398815399802566633761105626850937808489634748272458045409674234945705824 kip-in`.

Per plate:

`18.288946199407699901283316880552813425468904244817374136229022704837117472852912 kip-in`.

With pair `N=7.2 kip` and `V=-10 kip`, expected governing test-only rational utilization:

`0.610764784365745310957551826258637709772951628825271470878578`.

Production uses inherited Stage 3.6B / Slice 4 authority.

## 60. Pure axial behavior

For `P_L=+20 kip`, `V_V=0`, `M_T=0`:

Slice 5:

- top `N=6.4 kip`;
- web `N=7.2 kip`;
- bottom `N=6.4 kip`;
- all local component moments zero.

Each top/bottom flange:

`F_o=F_i=3.2 kip`.

Each inner strip:

`1.6 kip`.

No flange through-depth couple.

## 61. Pure moment behavior

For `P_L=0`, `V_V=0`, `M_T=+100 kip-in`:

Top:

`N=+9.002961500493583415597235932872655478775913129318854886475814412635735439289240 kip`.

Bottom:

`N=-9.0029615004935834155972359328726554787759131293188548864758144126357354392892397 kip`.

Top branches:

- outer `+4.5409674234945705824284304047384007897334649555774925962487660414610069101678184 kip`;
- inner total `+4.4619940769990128331688055281342546890424481737413622902270483711747285291214216 kip`.

Bottom branches are exact sign reversals with bottom geometry.

## 62. Zero flange resultant with nonzero local moment

A valid combined `P/M` state may produce `N_f=0` while `m_f!=0`.

For the top flange with the default `M_T=100 kip-in`, the exact axial force causing `N_top=0` is:

`P_L=-28.134254689042448173741362290227048371174728529121421520236920039486673247778875 kip`.

Then:

`F_top,o=+0.03948667324777887462981243830207305034550839091806515301085883514313919052319842 kip`.

`F_top,i=-0.03948667324777887462981243830207305034550839091806515301085883514313919052319842 kip`.

This case proves the local flange moment is not discarded.

## 63. Moment sign reversal

For identical geometry/actions except `M_T -> -M_T`:

- Slice 5 bending terms reverse;
- top/bottom tension/compression roles interchange as dictated by combined axial force;
- flange branch couple terms reverse;
- web free moment reverses;
- exact global equilibrium remains.

No geometry changes.

## 64. Axial sign reversal

For `P_L -> -P_L` with same `M_T`:

- uniform Slice 5 axial shares reverse;
- bending terms remain;
- branch forces recompute exactly;
- no absolute-value load redistribution.

## 65. Shear sign reversal

For `V_V -> -V_V`:

- Slice 5 flange branch forces remain unchanged;
- web shear reverses;
- web shear-generated group/body moments reverse appropriately;
- web free component moment from `M_T` remains unchanged.

## 66. Flange outer-only topology

Not permitted in RC1.

If outer flange plate exists without both inner strips:

`INVALID_GEOMETRY`.

Do not silently fall back to single-lap design.

## 67. Unsupported profile/actions

Reject:

- Channel;
- Angle;
- RHS/SRS beam;
- unequal W/I beams;
- minor shear;
- minor-axis moment;
- torsion.

No partial product design under unsupported global actions.

## 68. Preview behavior

Preview performs:

- strict validation;
- full authoritative geometry;
- Slice 5 demand decomposition;
- flange branch decomposition;
- web/flange group demand planning;
- physical bolt paths/endpoints;
- material axes;
- applicability/source plan;
- review/qualification/disclaimer metadata;
- exact equilibrium trace.

Preview resistance calls:

`0`.

No capacity/utilization in preview.

## 69. Explicit Run Design Check

Only explicit design action performs:

- existing web local checks;
- web rational body interaction;
- web common-bolt shear;
- flange outer/inner local checks;
- beam-flange rational face-sublayer local checks;
- flange plate clear-body Slice 4 tension/compression;
- flange common-bolt unequal-plane shear checks;
- whole-result aggregation.

Engineering edits make design stale.

## 70. Overall aggregation precedence

1. invalid/rejected input -> invalid/rejected;
2. any supported required failure -> `FAIL`;
3. required source/method unavailable -> `NOT_EVALUATED`;
4. all required numerical strength checks pass -> `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Never ordinary `PASS`.

## 71. Required review/qualification metadata

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

`WI_MOMENT_SPLICE_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`.

Also retain inherited FRP splice-plate qualification metadata.

## 72. Stiffness / classification states

Always:

`MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION=NOT_EVALUATED`.

`MOMENT_ROTATION_CAPACITY=NOT_EVALUATED`.

`FULL_STRENGTH_CLASSIFICATION=NOT_EVALUATED`.

No stiffness or member-capacity comparison is invented.

## 73. Mandatory disclaimer

Backend ID:

`WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1`.

Backend owns the full controlled meaning from the decision/ledger.

If report generation exists, include it in the final disclaimer section.

Otherwise transport deterministic metadata for future report generation.

## 74. Visualization

Required 3D geometry:

- two W/I beams;
- positive physical gap;
- two web splice plates;
- top outer full-width plate;
- top two inner split plates;
- bottom outer full-width plate;
- bottom two inner split plates;
- all web and flange physical bolts;
- exterior hardware;
- holes;
- material-axis visualization;
- action arrows including major moment.

Inner plates must be inspectable via camera/X-ray.

## 75. Backend-authoritative visualization

Backend owns:

- plate solids;
- contact surfaces;
- physical layer order;
- bolt endpoints;
- bolt axes;
- hole positions;
- material axes;
- action references;
- component references;
- branch-force references.

Frontend only renders/mapps scene primitives.

No frontend geometry engineering.

## 76. Viewer/request-state invariance

Preserve existing:

- persistent viewer;
- camera/navigation;
- Solid/X-ray;
- material-axis toggle;
- current/invalid/last-valid behavior;
- request-failure behavior;
- stale design behavior;
- no blank workspace.

## 77. UI traceability

Results shall expose, at minimum:

- original `P/V/M`;
- Slice 5 top/web/bottom component wrenches;
- `M/z` reference diagnostic from Slice 5;
- top outer/inner branch forces;
- bottom outer/inner branch forces;
- web component wrench;
- each physical bolt plane demand;
- governing local/component result;
- rational method/review/qualification/disclaimer status.

No hidden redistribution.

## 78. Deterministic fingerprints

Stage 4.1A engineering fingerprints include:

- contract/product;
- W/I geometry;
- gap;
- web splice geometry;
- flange plate geometry/positions;
- bolt grids/layer paths;
- material bases;
- input actions/reference;
- Slice 5 result fingerprint;
- flange branch decomposition;
- face-sublayer records;
- group wrenches;
- per-plane bolt demand;
- all local/body resistance provenance;
- equilibrium;
- result/status;
- review/qualification/disclaimer.

Presentation excluded.

## 79. U.S./SI equivalence

Equivalent physical inputs shall preserve:

- geometry;
- actions;
- component wrenches;
- branch forces;
- physical bolt paths;
- local demand;
- resistance;
- equilibrium;
- status;
- fingerprints.

No unit-specific engineering branch.

## 80. Historical invariance

Require exact Stage 3.6 historical requests/results/fingerprints.

Require all Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 freeze audits.

Stage 4.1A shall not alter historical selector behavior except by adding the new Moment Connections product option.

## 81. Required controlled golden coverage

The Stage 4.1A golden fixture shall contain at least G1-G96 covering:

- product/contract;
- topology;
- exact geometry;
- bolt paths;
- Slice 5 handoff;
- branch-force arithmetic;
- exact joint equilibrium;
- web moment handoff;
- flange plate body;
- rational flange face sublayers;
- unequal bolt shear planes;
- sign reversal;
- pure axial;
- pure moment;
- zero-resultant/nonzero-local-moment case;
- source pending;
- unsupported action/profile rejection;
- geometry invalidity;
- preview/design separation;
- result aggregation;
- review/qualification/disclaimer;
- U.S./SI;
- fingerprints;
- frontend visual contract;
- all freeze regressions.

## 82. Acceptance boundary

Stage 4.1A RC1 is accepted only if:

- Calculation Slice 5 remains exact;
- no component moment is discarded;
- flange outer/inner forces exactly recover each flange wrench;
- inner strip split is proven by exact transverse symmetry;
- web subsystem receives the Slice 5 web free moment;
- beam-flange local face transfer is checked with the controlled rational sublayer method;
- flange common bolts use actual unequal per-plane demands;
- flange plate clear bodies are checked for tension/compression;
- all local FRP checks use accepted authority;
- exact global equilibrium closes;
- overall success remains review-required;
- stiffness/rotation/full-strength classification remains unevaluated;
- complete local/object-isolated QA passes;
- hosted CI 4/4 passes;
- owner visual acceptance passes.

**END OF STAGE 4.1A W/I MAJOR-AXIS MOMENT SPLICE ENGINEERING SPECIFICATION RC1**
