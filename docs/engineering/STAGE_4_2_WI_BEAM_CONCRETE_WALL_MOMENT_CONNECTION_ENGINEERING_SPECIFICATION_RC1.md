# FRP Master Connection — Stage 4.2 W/I Beam-to-Concrete-Wall Major-Axis Moment Connection — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 4.2 creates a physical W/I beam-to-concrete-wall major-axis moment connection using:

- one top flange FRP angle;
- one bottom flange FRP angle;
- two mirrored FRP web clip angles;
- Calculation Slice 5 W/I component resultants;
- Calculation Slice 7 material-neutral angle cores and FRP provider;
- existing local FRP and fastener checks where applicable;
- exact external wall-anchor/concrete handoff.

Concrete and anchor capacity remain external.

## 2. Accepted starting baseline

Expected repository state:

- branch `main`;
- `HEAD == origin/main == remote main`:
  `d940192ea8eecb7e35f9601c38f3ad841f580916`;
- subject:
  `feat: add angle connector core and FRP resistance provider`;
- commit count:
  `104`;
- clean worktree/index.

Calculation Slice 7 RC2 hosted CI:

GitHub Actions run #99, latest attempt #2:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `6m 21s`.

## 3. Immutable freezes

Preserve all existing Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 / 4.1A / 4.1 family freeze tags and historical fingerprints.

No tag operation is authorized.

## 4. Accepted shared authorities

### Calculation Slice 5

Use the accepted W/I region-resultant engine:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`.

Do not duplicate its equations.

### Calculation Slice 7 RC2

Use:

- `ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`;
- `ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`;
- `FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`;
- `ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1`;
- `QUALIFIED_FRP_ANGLE_ASSEMBLY_FULL_WRENCH_ENVELOPE_RC1`;
- `RATIONAL_LINEAR_QUALIFIED_ANGLE_ASSEMBLY_INTERACTION_RC1`.

Do not place FRP-specific resistance assumptions inside Stage 4.2 geometry/wrench allocation.

### Frozen Stage 3.5 wall architecture

Reuse through a successor-specific adapter:

- finite concrete wall prism/frame;
- backend-authoritative wall coordinates;
- external blind-anchor geometry;
- exact group-wrench handoff;
- no concrete FRP material axes;
- current/invalid/last-valid request-state behavior.

Do not modify historical Stage 3.5 contracts or fingerprints.

## 5. Product contract

Product ID:

`WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION`.

Contract:

`4.2-RC1`.

Selector category:

`Moment Connections`.

User label:

`W/I Beam to Concrete Wall Moment Connection`.

No Channel/RHS/SRS/Angle beam option.

## 6. Beam frame

Use right-handed:

`L_B × V_B = T_B`.

- `L_B`: normal away from the wall and into the beam;
- `V_B`: vertical, positive toward top flange;
- `T_B`: beam transverse direction.

Wall front face:

`L_B=0`.

Beam-end section:

`L_B=g`.

Wall common handoff reference:

`r_W=(0,0,0)`.

Beam-end centroidal action reference:

`r_J=(g,0,0)`.

## 7. Normal action scope

Accept:

- signed axial `P_L`;
- signed major shear `V_V`;
- signed major-axis structural moment `M_T`.

Positive `P_L` = tension.

Positive `M_T` = top-flange tension under the Calculation Slice 5 convention.

Reject:

- minor shear;
- minor-axis moment;
- torsion.

No user moment other than major-axis `M_T`.

## 8. Structural-to-right-hand end-wrench map

Implement:

`EXACT_WI_NEGATIVE_END_STRUCTURAL_TO_RIGHT_HAND_WRENCH_MAP_RC1`.

At the negative-`L_B` beam end, the physical beam-on-connection right-hand wrench is:

`F_J^RH=(P_L,V_V,0)`.

`M_J^RH=(0,0,-M_T)`.

For each Calculation Slice 5 component:

- structural longitudinal force `N_i` maps to `+L_B N_i`;
- structural major shear maps to `+V_B`;
- structural local major moment `m_i` maps to right-hand `-T_B m_i`.

The product shall return both:

- right-hand mechanical vectors;
- structural display signs.

No silent sign conversion in the frontend.

## 9. Default beam geometry

Use:

- depth `d=10 in`;
- flange width `b_f=8 in`;
- web thickness `t_w=0.5 in`;
- flange thickness `t_f=0.5 in`;
- display/member length `16 in`;
- beam-end-to-wall gap `g=0.5 in`.

Require:

`g>0`.

No direct beam-end bearing on concrete.

## 10. Default concrete wall

Reuse Stage 3.5 finite wall:

- width `48 in`;
- height `48 in`;
- thickness `8 in`;
- connection origin centered at wall front face;
- concrete extends away from the beam behind `L_B=0`;
- no FRP LW/CW/TT axes assigned to concrete.

All angle support legs and anchor holes shall lie within the finite wall face.

## 11. Physical connector count

Exactly four angle connectors:

1. `TOP_FLANGE_ANGLE`;
2. `BOTTOM_FLANGE_ANGLE`;
3. `POSITIVE_WEB_CLIP_ANGLE`;
4. `NEGATIVE_WEB_CLIP_ANGLE`.

Exactly four external wall-anchor groups, one per connector.

## 12. Default angle geometry

Two locked geometry families.

### Flange-angle family

Top and bottom:

- angle length `L_A,f=8 in`;
- member leg width `b_M,f=4 in`;
- support leg width `b_S,f=4 in`;
- thickness `t_A,f=0.5 in`;
- inside heel radius `r_i,f=0.25 in`.

### Web-angle family

Positive and negative web clip angles:

- angle length `L_A,w=8 in`;
- member leg width `b_M,w=4 in`;
- support leg width `b_S,w=4 in`;
- thickness `t_A,w=0.5 in`;
- inside heel radius `r_i,w=0.25 in`.

Top/bottom share one input set.

Positive/negative web angles share one input set.

## 13. Local connector frames

Every frame satisfies:

`A_A × B_A = C_A`.

### Top flange angle

- `A_A=+T_B`;
- `B_A=+L_B`;
- `C_A=+V_B`.

### Bottom flange angle

- `A_A=-T_B`;
- `B_A=+L_B`;
- `C_A=-V_B`.

### Positive web angle

- `A_A=-V_B`;
- `B_A=+L_B`;
- `C_A=+T_B`.

### Negative web angle

- `A_A=+V_B`;
- `B_A=+L_B`;
- `C_A=-T_B`.

The signs are part of the deterministic engineering contract.

## 14. Heel locations

For angle thickness `t_A=0.5 in`:

### Top

`r_H,top=(0.25,+5.25,0) in`.

### Bottom

`r_H,bottom=(0.25,-5.25,0) in`.

### Positive web

`r_H,+web=(0.25,0,+0.50) in`.

### Negative web

`r_H,-web=(0.25,0,-0.50) in`.

These are angle mid-surface tangent intersections at mid-length.

Derive from actual beam and angle geometry.

## 15. Default local interface references

For every default connector in local `(A_A,B_A,C_A)` coordinates:

Heel:

`r_H=(0,0,0)`.

Member interface:

`r_M=(0,2.0,-0.25) in`.

Support/wall interface:

`r_S=(0,-0.25,2.0) in`.

The `-0.25 in` values place the references on the physical contact/interface planes.

Member and support group centroid distances are user-controlled within geometry limits.

## 16. Default global interface locations

Derived global member-interface references:

- top `(2.25,+5.00,0) in`;
- bottom `(2.25,-5.00,0) in`;
- positive web `(2.25,0,+0.25) in`;
- negative web `(2.25,0,-0.25) in`.

Derived wall-interface group references:

- top `(0,+7.25,0) in`;
- bottom `(0,-7.25,0) in`;
- positive web `(0,0,+2.50) in`;
- negative web `(0,0,-2.50) in`.

No frontend coordinate reconstruction.

## 17. Slice 5 component references

At the beam-end section `L_B=g`:

- top flange:
  `(g,+4.75,0) in`;
- web:
  `(g,0,0) in`;
- bottom flange:
  `(g,-4.75,0) in`.

Use complete component wrenches.

## 18. Default Slice 5 resultants

For:

- `P_L=+20 kip`;
- `V_V=-10 kip`;
- `M_T=+100 kip-in`;

require accepted exact Slice 5 values:

Top:

`N_top=15.402961500493583415597235932872655478775913129318854886475814412635735439289240 kip`.

`m_top=0.039486673247778874629812438302073050345508390918065153010858835143139190523198420 kip-in`.

Web:

`N_web=7.2 kip`.

`V_web=-10 kip`.

`m_web=14.392892398815399802566633761105626850937808489634748272458045409674234945705824 kip-in`.

Bottom:

`N_bottom=-2.6029615004935834155972359328726554787759131293188548864758144126357354392892397 kip`.

`m_bottom=0.039486673247778874629812438302073050345508390918065153010858835143139190523198420 kip-in`.

## 19. Top flange-angle member-interface wrench

Shift the mechanical top component from its Slice 5 reference to the physical member interface and transform to the top angle frame.

Default at `r_M`:

Force `(A,B,C)`:

`(0,15.402961500493583415597235932872655478775913129318854886475814412635735439289240,0) kip`.

Moment `(A,B,C)`:

`(3.811253701875616979269496544916090819348469891411648568608094768015794669299111580,0,0) kip-in`.

## 20. Top heel and support wrenches

Default heel:

Force unchanged.

Moment:

`(7.661994076999012833168805528134254689042448173741362290227048371174728529121421580,0,0) kip-in`.

Default connector-on-wall at `r_S`:

Force unchanged.

Moment:

`(38.467917077986179664363277393879565646594274432379072063178677196446199407699901580,0,0) kip-in`.

## 21. Bottom flange-angle member-interface wrench

Default at `r_M`:

Force:

`(0,-2.6029615004935834155972359328726554787759131293188548864758144126357354392892397,0) kip`.

Moment:

`(-0.611253701875616979269496544916090819348469891411648568608094768015794669299111505,0,0) kip-in`.

## 22. Bottom heel and support wrenches

Default heel moment:

`(-1.261994076999012833168805528134254689042448173741362290227048371174728529121421430,0,0) kip-in`.

Default connector-on-wall support moment:

`(-6.467917077986179664363277393879565646594274432379072063178677196446199407699900830,0,0) kip-in`.

## 23. Paired web-angle allocation

Method:

`RATIONAL_SYMMETRIC_PAIRED_WEB_ANGLE_WRENCH_ALLOCATION_RC1`.

At the exact Slice 5 web reference, allocate one-half of the complete mechanical web wrench to each web angle only after exact proof of:

- mirrored angle geometry;
- identical FRP provider/source identity;
- common symmetric member bolt group;
- mirrored wall-anchor geometry;
- zero minor shear;
- zero minor-axis moment;
- zero torsion.

Then shift each half-wrench to its member interface.

If symmetry fails:

`PAIRED_WEB_ANGLE_FULL_WRENCH_ALLOCATION=NOT_EVALUATED`.

## 24. Positive web-angle default member wrench

At `r_M`, local force:

`(5,3.6,0) kip`.

Local moment:

`(0.9,-1.25,1.553553800592300098716683119447186574531095755182625863770977295162882527147088) kip-in`.

## 25. Positive web-angle heel/support wrenches

Heel moment:

`(1.8,-2.5,-8.446446199407699901283316880552813425468904244817374136229022704837117472852912) kip-in`.

Connector-on-wall support moment:

`(9,-12.5,-9.696446199407699901283316880552813425468904244817374136229022704837117472852912) kip-in`.

## 26. Negative web-angle default member wrench

At `r_M`, local force:

`(-5,3.6,0) kip`.

Local moment:

`(0.9,1.25,-1.553553800592300098716683119447186574531095755182625863770977295162882527147088) kip-in`.

## 27. Negative web-angle heel/support wrenches

Heel moment:

`(1.8,2.5,8.446446199407699901283316880552813425468904244817374136229022704837117472852912) kip-in`.

Connector-on-wall support moment:

`(9,12.5,9.696446199407699901283316880552813425468904244817374136229022704837117472852912) kip-in`.

## 28. Connector core invocation

For every connector invoke:

`ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`.

Return:

- core geometry/frame;
- member-interface wrench;
- heel-reference wrench;
- connector-on-wall support wrench;
- support-on-connector reaction;
- exact connector equilibrium;
- provider-independent core fingerprint.

No duplicate wrench formulas in Stage 4.2 orchestration.

## 29. FRP provider invocation

Provider key:

`FRP`.

Provider:

`FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`.

RC1 shall not expose unsupported provider keys as user choices.

A future 316SS provider remains outside scope.

## 30. Instep shear

For web angles:

`V_instep=|F_A,H|=5 kip` in the default case.

For top/bottom angles:

`F_A,H=0`, so:

`NOT_REQUIRED_ZERO_SHEAR`.

Use Equation 8-15 only inside the FRP provider.

For test-only `F_sh=8 ksi`, `l_sp=8 in`, `t=0.5 in`:

`phi R=22.4 kip`.

Web-angle utilization:

`0.22321428571428571428571428571428571428571428571428571428571428571428571428571429`.

## 31. Qualified FRP angle source

A nonzero connector-body result requires an exact Slice 7 qualified source package bound to:

- connector core geometry;
- connector FRP material;
- member-side fastener layout;
- support-side fixture/anchor layout;
- connector references/frame;
- source version;
- covered limit states;
- interaction authority.

Top/bottom may share one source only if exact mirror applicability is proven.

Positive/negative web angles may share one source only if signed strength and mirrored applicability are proven.

## 32. Qualified member-attachment source

Implement a product-level applicability record:

`QUALIFIED_FRP_MEMBER_ANGLE_ATTACHMENT_SOURCE_RC1`.

It shall bind:

- W/I connected region geometry/material fingerprint;
- angle member-leg geometry/material fingerprint;
- member-side bolt/hole pattern;
- fastener source/condition;
- interface frame/reference;
- demanded full member-interface wrench;
- coverage for member through-thickness/pull-through/delamination;
- bolt-axis force distribution;
- secondary bolt bending;
- local leg/member bending and prying;
- combined interaction;
- source identity/version.

It shall reuse existing qualified signed-wrench source infrastructure rather than inventing an analytical pull-through/prying formula.

If required coverage is absent:

`MEMBER_ANGLE_ATTACHMENT_QUALIFIED_SOURCE_REQUIRED`.

## 33. Member-side flange bolt groups

Top and bottom each use a 2×2 group by default.

Local coordinates:

- `A=±2.5 in`;
- `B=1.25,2.75 in`;
- member-interface centroid `B=2.0 in`.

Inputs include:

- bolts across angle length;
- bolts along member leg;
- extrusion gauge;
- leg-direction pitch;
- bolt diameter;
- hole diameter.

Default:

- 2×2;
- extrusion gauge `5 in`;
- leg pitch `1.5 in`;
- bolt `0.5 in`;
- hole `0.563 in`.

## 34. Member-side web common bolt group

One common physical 2×2 group by default.

Local group coordinates for each web angle:

- `A=±1.5 in`;
- `B=1.25,2.75 in`.

Physical stack:

`NEGATIVE_WEB_CLIP_ANGLE_MEMBER_LEG -> W/I_WEB -> POSITIVE_WEB_CLIP_ANGLE_MEMBER_LEG`.

One shank per bolt.

Two physical shear planes.

## 35. Stage 2.5A in-plane member demand

For each angle member interface, resolve only the in-plane member-leg components:

- force `(F_A,F_B)`;
- in-plane group moment `M_C`.

Use actual bolt coordinates and Stage 2.5A.

Retain separately:

- normal force `F_C`;
- out-of-plane moments `M_A`, `M_B`.

Those components are not discarded and require qualified attachment coverage.

## 36. Default flange in-plane per-bolt direct demand

With four bolts and no in-plane group moment:

Top:

`N_top/4=3.850740375123395853899308983218163869693978282329713721618953603158933859822310 kip`.

Bottom:

`N_bottom/4=-0.650740375123395853899308983218163869693978282329713721618953603158933859822310 kip`.

Signed values retained.

## 37. Default web in-plane Stage 2.5A demand

For the positive web-angle plane:

- `F_A=+5 kip`;
- `F_B=+3.6 kip`;
- `M_C=+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

For the negative plane:

- `F_A=-5 kip`;
- `F_B=+3.6 kip`;
- `M_C=-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

Use actual Stage 2.5A per-bolt vectors.

No blind force/n division.

## 38. Common web-bolt plane method

Use:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

Each physical web bolt receives:

- negative-angle/web plane vector;
- web/positive-angle plane vector.

Check independently where source-authorized.

No blind `2×` capacity.

## 39. Flange member attachment boundary

Each flange angle is a one-sided Angle/Flange attachment.

No backing plate or hidden second angle.

Existing in-plane local checks and bolt shear run where applicable.

The nonzero member-interface `M_A` and any other out-of-plane component require the qualified member-attachment source.

No numerical prying/pull-through demand is invented.

## 40. Web member attachment boundary

The paired common-bolt assembly retains actual in-plane two-plane vectors.

The member-interface `M_A/M_B/F_C` components remain explicit.

Complete web attachment adequacy requires the qualified paired attachment source.

## 41. Support anchor-group geometry

Each connector has a default 2×2 wall group.

### Top/bottom groups

Local:

- `A=±2.5 in`;
- `C=1.25,2.75 in`.

### Web groups

Local:

- `A=±1.5 in`;
- `C=1.25,2.75 in`.

All anchors are backend-authoritative physical blind anchors into concrete.

No fictitious far-side hardware.

## 42. External group handoff

Return the complete connector-on-wall wrench for each group.

Do not distribute to individual anchors unless a separately qualified flexible-fixture source provides that distribution.

Always expose:

`FLEXIBLE_FIXTURE_PRYING_DISTRIBUTION_EXTERNAL_REQUIRED`

when no such source exists.

## 43. Default global support-group wrenches

In right-hand beam `(L_B,V_B,T_B)` components:

### Top group at `(0,7.25,0) in`

Force:

`(15.402961500493583415597235932872655478775913129318854886475814412635735439289240,0,0) kip`.

Moment:

`(0,0,38.467917077986179664363277393879565646594274432379072063178677196446199407699901580) kip-in`.

### Bottom group at `(0,-7.25,0) in`

Force:

`(-2.6029615004935834155972359328726554787759131293188548864758144126357354392892397,0,0) kip`.

Moment:

`(0,0,6.467917077986179664363277393879565646594274432379072063178677196446199407699900830) kip-in`.

### Positive web group at `(0,0,2.5) in`

Force:

`(3.6,-5,0) kip`.

Moment:

`(-12.5,-9,-9.696446199407699901283316880552813425468904244817374136229022704837117472852912) kip-in`.

### Negative web group at `(0,0,-2.5) in`

Force:

`(3.6,-5,0) kip`.

Moment:

`(12.5,9,-9.696446199407699901283316880552813425468904244817374136229022704837117472852912) kip-in`.

## 44. Exact wall common-reference handoff

Shift all four connector-on-wall group wrenches to `r_W`.

Default sum:

Right-hand force:

`(20,-10,0) kip`.

Right-hand moment:

`(0,0,-105) kip-in`.

Equivalent structural wall moment:

`+105 kip-in`.

Require exact identity with the input beam-end wrench shifted from `r_J=(0.5,0,0)` to the wall front-face reference.

## 45. Wall reaction

Wall reaction on the connection is the exact negative of the connector-on-wall combined handoff.

Return both signs explicitly.

## 46. Beam local checks

At member-side bolt groups, reuse existing applicable W/I region checks for:

- bearing;
- net tension;
- shear-out;
- cleavage;
- block shear / accepted local path.

Use actual material axes and loaded-edge direction.

Do not infer out-of-plane capacity from in-plane checks.

## 47. Angle member-leg local checks

Run existing in-plane local checks on the angle member leg where applicable using the FRP provider material trace and Stage 2.5A demand.

The complete connector body/heel result remains controlled by Slice 7 provider.

## 48. Member-side fastener checks

Use source-controlled fastener properties.

In-plane shear checks execute from Stage 2.5A vectors.

Out-of-plane bolt-axis/secondary-bending response is controlled by the qualified member-attachment source.

Do not fabricate bolt tension.

## 49. Support-leg/anchor-hole local response

Support-leg/anchor-hole/prying response is controlled by the qualified angle assembly source and external anchor analysis.

Do not calculate local support-leg capacity from fabricated per-anchor forces.

## 50. Source package UI

RC1 exposes controlled source selectors/references for:

- flange-angle FRP qualified connector source;
- web-angle FRP qualified connector source;
- flange member-attachment qualified source;
- paired web member-attachment qualified source.

Production default:

no qualified source selected.

Test-only source packages are never exposed as production defaults.

## 51. Test-only high-capacity qualified source

For deterministic tests only, use twice the Calculation Slice 7 test strengths:

### Forces

- `R_FA+=50 kip`;
- `R_FA-=40 kip`;
- `R_FB+=60 kip`;
- `R_FB-=80 kip`;
- `R_FC+=30 kip`;
- `R_FC-=30 kip`.

### Moments

- `R_MA+=24 kip-in`;
- `R_MA-=20 kip-in`;
- `R_MB+=40 kip-in`;
- `R_MB-=40 kip-in`;
- `R_MC+=36 kip-in`;
- `R_MC-=48 kip-in`.

Full coverage and interaction authority are test-only.

## 52. Test-only default connector utilizations

Using the test-only high-capacity qualified source at the heel:

- top angle:
  `0.57596577821651859164198749588680487002303389272787101020072392234287594603487989`;
- bottom angle:
  `0.095636722606120434353405725567620927936821322803553800592300098716683119447186575`;
- positive web angle:
  `0.47346762915432708127673576834485027969726883843369529450477130635077328068443567`;
- negative web angle:
  `0.55712350553910277503564769112646703959635845124492705933969507513436437424591423`.

All pass under the test-only qualified source.

## 53. Test-only member-attachment utilizations

At each member-interface wrench using the same doubled signed strengths as a separate qualified attachment fixture:

- top:
  `0.41551826258637709772951628825271470878578479763079960513326752221125370187561698`;
- bottom:
  `0.063099703849950641658440276406712734452122408687068114511352418558736426456071076`;
- positive web:
  `0.27190427223867500274213008665131073818141932653285071843808270264341340353186355`;
- negative web:
  `0.28611570417900625205659756498848305363606449489963803882856202698256005264889766`.

These values test source integration only.

## 54. Pure axial behavior

For:

`P=+20 kip, V=0, M=0`

Slice 5:

- top `6.4 kip`;
- web `7.2 kip`;
- bottom `6.4 kip`;
- local moments zero.

Each web angle receives half web axial force.

Top/bottom angle heel moments arise from physical one-sided offset and remain qualified-source demand.

Combined wall right-hand moment is zero.

## 55. Pure major shear behavior

For:

`P=0, V=-10 kip, M=0`

Top/bottom connector demands are zero.

Web angle member-interface local forces:

- positive `(5,0,0) kip`;
- negative `(-5,0,0) kip`.

Generated wall structural major moment from gap:

`+5 kip-in`.

All web-angle offset moments remain retained.

## 56. Pure major moment behavior

For:

`P=0, V=0, M=+100 kip-in`

Top angle receives the full top flange component.

Bottom angle receives the full bottom flange component.

Web angles receive opposite local `M_C` signs from the half web free moment.

Combined wall right-hand major moment:

`-100 kip-in`.

## 57. Sign reversal

Require exact:

- `P -> -P`: axial component and corresponding connector forces reverse;
- `V -> -V`: web connector extrusion forces, offset moments, support handoffs, and gap moment reverse;
- `M -> -M`: top/bottom tension/compression roles and web local moments reverse;
- physical geometry remains unchanged;
- source signed strengths use the demanded sign.

## 58. Preview behavior

Preview performs zero resistance equations.

Preview returns:

- finite wall/beam/four-angle geometry;
- Slice 5;
- exact component mapping;
- four Slice 7 core records;
- member-side demand plans;
- support-group handoffs;
- wall common-reference equilibrium;
- source/applicability plan;
- external limitations;
- deterministic preview fingerprint.

## 59. Design behavior

Only explicit **Run Design Check** evaluates:

- beam local checks;
- angle member-leg local checks;
- Stage 2.5A group demand;
- source-controlled in-plane fastener checks;
- Slice 7 FRP provider;
- qualified member-attachment source;
- result aggregation.

Engineering changes stale prior results.

## 60. FRP-side status precedence

1. invalid geometry/input;
2. any required evaluated failure -> `FAIL`;
3. required qualified source absent -> `SOURCE_REQUIRED`;
4. required coverage/interaction unavailable -> `NOT_EVALUATED`;
5. all required FRP/member/fastener checks pass ->
   `PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`.

Ordinary FRP-side `PASS` prohibited.

## 61. Whole-connection status

Concrete and anchors remain external.

A successful FRP-side result does not become an ordinary whole-connection PASS.

Always retain:

`EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED`.

Internal failure or source limitation remains visible and governing for the internal scope.

## 62. Required review/classification states

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

`WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`.

`MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION=NOT_EVALUATED`.

`MOMENT_ROTATION_CAPACITY=NOT_EVALUATED`.

`FULL_STRENGTH_CLASSIFICATION=NOT_EVALUATED`.

## 63. API

Add strict stateless endpoints:

- `/api/v1/calculations/wi-beam-concrete-wall-moment/preview`;
- `/api/v1/calculations/wi-beam-concrete-wall-moment/design-check`.

Historical routes remain unchanged.

## 64. Frontend workspace

Add a dedicated Moment Connections workspace.

Inputs:

### Beam/wall
- W/I dimensions;
- beam display length;
- beam-end gap;
- wall width/height/thickness;
- connection origin.

### Loads
- axial;
- major shear;
- major moment.

### Flange angles
- common top/bottom angle geometry;
- member bolt group;
- wall anchor group;
- qualified source references.

### Web angles
- common mirrored angle geometry;
- common member bolt group;
- wall anchor groups;
- qualified source references.

No 316SS selector.

## 65. Result trace

Expose:

- original structural `P/V/M`;
- right-hand end wrench;
- Slice 5 top/web/bottom;
- web pair split proof;
- each member-interface wrench;
- each heel wrench;
- each support-group wrench;
- each instep result;
- connector-provider source/status;
- member-attachment source/status;
- in-plane Stage 2.5A demand;
- combined wall handoff;
- FRP-side status;
- external wall status;
- qualification/disclaimer.

No hidden frontend mechanics.

## 66. Visualization

Show:

- finite concrete wall;
- complete W/I beam;
- positive gap;
- top flange angle;
- bottom flange angle;
- positive web clip angle;
- negative web clip angle;
- all member bolts;
- all wall anchors;
- material axes;
- structural action arrows;
- four support-group references;
- combined wall-handoff trace.

## 67. X-ray / inspection

X-ray/camera must expose:

- both web clip angles;
- top/bottom member legs;
- support legs;
- common web bolts;
- flange bolts;
- all four anchor groups;
- no wall/beam/angle collision.

## 68. Backend authority

Backend owns:

- all physical solids;
- face/contact identities;
- connector frames;
- references;
- bolt/anchor paths;
- material axes;
- action arrows/references;
- source applicability;
- wall handoff.

Frontend renders only.

## 69. Invalid geometry

Reject at minimum:

- nonpositive gap;
- invalid W/I dimensions;
- angle overlap/interference;
- top/bottom angle support-leg overlap with web angles;
- bolt/hole outside any physical layer;
- common web bolt missing either angle;
- flange bolt crossing web;
- angle member/support group outside leg;
- anchor hole outside finite wall;
- wall edge/spacing containment failure;
- asymmetric paired web angles in RC1;
- top/bottom flange angle mismatch in RC1;
- invalid qualified source binding;
- unsupported action.

No auto-repair.

## 70. U.S./SI equivalence

Equivalent physical inputs preserve:

- geometry;
- Slice 5 resultants;
- connector frames/references;
- all member/heel/support wrenches;
- Stage 2.5A demand;
- provider/source results;
- combined wall handoff;
- statuses;
- fingerprints.

## 71. Fingerprints

Include:

- product/contract;
- beam/wall geometry;
- angle geometry;
- member/anchor groups;
- Slice 5 fingerprint;
- structural-to-right-hand map;
- web pair split;
- four Slice 7 core fingerprints;
- provider/source identities;
- qualified attachment identities;
- local/group demand;
- four support handoffs;
- combined wall equilibrium;
- status/review/disclaimer.

Presentation excluded.

## 72. Historical/frozen invariance

Require exact:

- Stage 4.1 family freeze;
- Stage 4.1A freeze;
- Slices 5/6/7;
- Stage 3.7 / 3.6 / 3.5 / 3.4 / 3.3 / 3.2 / 2.3 freeze audits;
- all historical selectors/products/fingerprints.

Stage 4.2 adds one new product only.

## 73. Controlled golden coverage

The Stage 4.2 golden shall contain exactly `G1-G128`.

Coverage includes:

- contract/scope;
- geometry/frames/references;
- Slice 5 handoff;
- sign adapter;
- web pair split;
- four connector core wrenches;
- member groups;
- Stage 2.5A vectors;
- FRP provider/instep;
- qualified attachment sources;
- anchor-group geometry;
- four support handoffs;
- exact wall equilibrium;
- pure/sign cases;
- preview/design/status;
- source/external boundaries;
- invalid geometry;
- U.S./SI;
- fingerprints;
- visualization;
- all freeze regressions.

## 74. Acceptance boundary

Stage 4.2 RC1 is accepted only if:

- Slice 5 remains exact;
- Slice 7 remains exact;
- structural/right-hand signs are explicit;
- top/bottom complete component wrenches are retained;
- paired web half-wrench allocation is exactly proven;
- all four connector core equilibria close;
- qualified FRP connector and member-attachment limitations remain fail-closed;
- no bolt-axis/prying/pull-through force is invented;
- four support-group handoffs sum exactly at the wall reference;
- no individual anchor force is fabricated;
- concrete/anchor capacity remains external;
- complete QA/object isolation/hosted CI pass;
- owner visual/result acceptance passes.

**END OF STAGE 4.2 W/I BEAM CONCRETE WALL MOMENT CONNECTION ENGINEERING SPECIFICATION RC1**
