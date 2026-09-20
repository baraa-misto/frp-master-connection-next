# FRP Master Connection — Stage 4.1B Channel Major-Axis Moment Splice — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 4.1B is the first physical open-section Channel moment-splice product.

It consumes accepted Calculation Slice 6 Channel centroid/shear-center/component resultants and designs a physical splice using:

- two web-face splice plates;
- one outer and one inner plate on the top flange;
- one outer and one inner plate on the bottom flange;
- common through-bolts;
- accepted local FRP connection checks;
- Calculation Slice 4 plate strengths;
- controlled rational Channel-specific branch methods;
- mandatory engineering review and Section 2.3.2 qualification.

## 2. Accepted starting baseline

Expected repository state:

- branch `main`;
- `HEAD == origin/main == remote main`:
  `b275a647bbbc1786d169302f060402fbfb062aab`;
- subject:
  `feat: add Channel moment reference and resultant engine`;
- commit count:
  `100`;
- clean worktree/index.

Calculation Slice 6 hosted CI:

GitHub Actions run #95, latest attempt #6:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `5m 56s`.

## 3. Immutable freeze tags

Preserve exactly all existing freeze tags:

- Stage 2.3;
- Stage 3.2;
- Stage 3.3;
- Stage 3.4;
- Stage 3.5;
- Stage 3.6;
- Stage 3.7;
- Stage 4.1A.

Stage 4.1A freeze tag:

`stage-4.1a-wi-major-axis-moment-splice-freeze`

annotated tag object:

`a265ff394413d8fef16e7012c1de910bf3ece1b7`

peeled target:

`cc9effad0691d083bb204c44ec3fb6e9dfb3671d`.

No tag operation in Stage 4.1B.

## 4. Accepted Calculation Slice 6 authority

Accepted commit:

`b275a647bbbc1786d169302f060402fbfb062aab`.

Stage 4.1B shall call Calculation Slice 6 exactly once for the canonical Channel member-end action.

Do not copy/recompute Slice 6 formulas in product orchestration.

Required Slice 6 records include:

- exact Channel centroid;
- `I_T`, `I_V`, `I_VT`;
- shear-center source/method/provenance;
- canonical centroid wrench;
- top flange component wrench;
- web component wrench;
- bottom flange component wrench;
- transverse eccentricity ledger;
- generated centroidal torsion;
- web free torsion;
- stress extrema/states;
- six-component equilibrium proof;
- deterministic fingerprint;
- review/disclaimer metadata.

## 5. Source/provenance basis

Review and register relevant ASCE/SEI 74-23 provisions and Erratum 1.

Controlled interpretation:

- open-section Channel eccentricities are real and shall not be ignored;
- connection demand must remain consistent with structural analysis;
- flexural splices transmit applicable force and moment;
- shear-carrying connection components retain shear, eccentricity, and their moment contribution;
- rational analysis is required where prescriptive coverage is incomplete;
- Section 2.3.2 qualification/review remains required for the final moment-resistant Channel splice.

The Channel web-face branch decomposition, web face-sublayer transfer, flange face-sublayer transfer, and unequal common-bolt plane methods are project-controlled rational methods.

## 6. Product contract

Product ID:

`CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE`.

Contract:

`4.1B-RC1`.

Selector category:

`Moment Connections`.

User-facing label:

`Channel Beam Moment Splice`.

No W/I fallback.

## 7. Channel profile scope

Exactly:

- unlipped;
- equal top/bottom flanges;
- sharp-corner profile;
- homogeneous longitudinal-modulus Channel;
- two identical beams;
- identical orientation.

Reject:

- lipped Channel;
- unequal flange Channel;
- built-up/back-to-back Channel;
- unequal Channel beams;
- mirrored open directions between Beam A and Beam B;
- W/I, RHS, SRS, Angle, or other profile.

## 8. Channel frame

Reuse Calculation Slice 6:

- `L_CH`: Beam A -> Beam B;
- `V_CH`: depth axis, positive toward top flange;
- `T_CH`: opening direction, positive from back web face toward flange tips.

Require:

`L_CH × V_CH = T_CH`.

Joint plane:

`L_CH=0`.

Canonical joint reference for displayed global action:

the exact Channel centroid at the splice section.

## 9. Beam identities

Exactly:

- `BEAM_A`, negative `L_CH`;
- `BEAM_B`, positive `L_CH`.

Identical Channel orientation.

No mirror transformation across the opening axis.

## 10. Beam-end gap

Input:

`beam_end_gap`.

Require:

`beam_end_gap > 0`.

Default:

`0.5 in`.

Beam A end plane:

`L=-0.25 in`.

Beam B end plane:

`L=+0.25 in`.

No direct beam-end bearing is credited.

## 11. Normal user actions

At the controlled Slice 6 action references:

- axial force `P_L`;
- major shear `V_V`;
- major-axis moment `M_T`.

Require zero / reject:

- minor shear;
- minor-axis moment;
- user torsion.

Default:

- `P_L=+20 kip`;
- `V_V=-10 kip`;
- `M_T=+100 kip-in`.

## 12. Shear-center source UI/contract

Expose exactly one controlling source mode.

### Rational geometry mode

`RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1`.

### Explicit verified mode

`EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1`.

If explicit verified mode is selected, require:

- exact shear-center coordinate;
- deterministic provenance/source fields.

Frontend does not calculate the shear center.

## 13. Slice 6 canonical handoff

Calculation Slice 6 returns:

### Top flange
- longitudinal force `N_top`;
- local major-axis moment `m_T,top`;
- reference `(V_top,T_f-T_c)`.

### Web
- longitudinal force `N_web`;
- major shear `V_web`;
- local major-axis moment `m_T,web`;
- free torsion `m_L,web`;
- reference `(0,T_w-T_c)`.

### Bottom flange
- longitudinal force `N_bottom`;
- local major-axis moment `m_T,bottom`;
- reference `(V_bottom,T_f-T_c)`.

Require exact Slice 6 six-component equilibrium before physical connection planning.

## 14. Interface action versus material-state sign

The Slice 6 component states represent the Channel section stress state.

Beam A and Beam B physical interface actions are equal and opposite.

Do not sign-reverse Beam B material tension/compression classification merely because its cut-face traction is opposite.

Preserve the distinction between section material state and physical interface traction.

## 15. Physical plate count

Create exactly:

### Web
- one back web splice plate;
- one opening web splice plate.

### Top flange
- one outer full-width plate;
- one inner centered plate.

### Bottom flange
- one outer full-width plate;
- one inner centered plate.

Total FRP splice plates:

`6`.

## 16. Default Channel geometry

Default:

- overall depth `d=8 in`;
- flange width `b_f=4 in`;
- web thickness `t_w=0.5 in`;
- flange thickness `t_f=0.5 in`;
- displayed beam length each side `18 in`.

Reuse backend authoritative Channel solids.

## 17. Web splice plate geometry

Inputs:

- web splice plate length `L_wp`;
- web splice plate height `h_wp`;
- web splice plate thickness `t_wp`.

Default:

- `L_wp=16 in`;
- `h_wp=5.5 in`;
- `t_wp=0.5 in`.

Both back/opening web plates are identical.

They are centered at `V_CH=0`.

Back plate occupies:

`T in [-t_wp,0]`.

Opening plate occupies:

`T in [t_w,t_w+t_wp]`.

Require:

`h_wp <= h_w-2t_fp`

where `t_fp` is the common flange splice plate thickness.

This protects the inside corner region occupied by the flange inner plates.

## 18. Web plate force-line coordinates

Web centroid:

`T_w=t_w/2`.

Back web plate centroid:

`T_back=-t_wp/2`.

Opening web plate centroid:

`T_open=t_w+t_wp/2`.

Offsets:

`e_back=T_back-T_w`.

`e_open=T_open-T_w`.

Require:

`e_back<0<e_open`.

For equal web-plate thickness:

`e_open=-e_back=(t_w+t_wp)/2`.

## 19. Web branch method

Method:

`RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1`.

Given Slice 6 web:

- `N_w`;
- `V_w`;
- `m_T,w`;
- `m_L,w`;

assign:

`N_back=N_open=N_w/2`.

`m_T,back=m_T,open=m_T,w/2`.

Solve:

`Q_back+Q_open=V_w`.

`-e_backQ_back-e_openQ_open=m_L,w`.

Therefore:

`Q_back=(m_L,w+e_openV_w)/(e_open-e_back)`.

`Q_open=V_w-Q_back`.

No equal-shear assumption.

## 20. Web branch exact recovery

At the Channel web centroid require exact:

`N_back+N_open=N_w`.

`Q_back+Q_open=V_w`.

`m_T,back+m_T,open=m_T,w`.

`-e_backQ_back-e_openQ_open=m_L,w`.

Equal longitudinal-force split shall also produce zero additional local minor-axis moment about the web centroid.

## 21. Meaning of web shear-center couple

The branch force couple is the physical connection representation of the Slice 6 web free-torsion/reference effect.

It does not create authorization for:

- user torsion;
- Saint-Venant torsional resistance;
- warping stress design;
- connection torsional stiffness.

Those remain outside RC1.

## 22. Web bolt topology

Each beam-side web group uses:

- two vertical rows;
- two longitudinal bolts per row by default;
- one common physical bolt through the three-layer stack.

Inputs:

- web rows `n_V`;
- web bolts per row `n_L,w`;
- vertical pitch `s_V`;
- longitudinal gauge `s_L,w`;
- group centroid distance `x_g,w`;
- web bolt diameter;
- web hole diameter.

Default:

- `n_V=2`;
- `n_L,w=2`;
- `s_V=3 in`;
- `s_L,w=3 in`;
- `x_g,w=4 in`;
- `d_b,w=0.5 in`;
- `d_h,w=0.563 in`.

Default group-relative coordinates:

`L=±1.5 in`

`V=±1.5 in`.

## 23. Physical web bolt path

Every web bolt:

`BACK_WEB_SPLICE_PLATE -> CHANNEL_WEB -> OPENING_WEB_SPLICE_PLATE`.

One physical shank.

Two physical shear planes.

Backend-authoritative endpoints.

Hardware:

- head/washer exterior to back web plate;
- nut/washer exterior to opening web plate;
- no hardware between layers.

## 24. Web group demands

For each back/opening plate branch:

- use its actual signed longitudinal force;
- use its actual signed vertical shear;
- use its allocated local major-axis moment;
- translate exactly from beam-end component reference to actual beam-side group reference;
- use Stage 2.5A to resolve per-bolt in-plane vectors.

Do not infer web per-bolt forces from simple `branch force / bolt count` when an eccentric group moment exists.

Beam A and Beam B group demands shall use exact mirrored geometry and equal/opposite interface traction.

## 25. Rational Channel web face sublayers

Method:

`RATIONAL_CHANNEL_WEB_FACE_SUBLAYER_TRANSFER_RC1`.

For local Channel-web FRP checks only:

### Back face
- width/height domain = actual connected web region;
- effective thickness `t_w/2`;
- full actual web bolt grid;
- actual material axes;
- actual back-branch group demand.

### Opening face
- same connected web region;
- effective thickness `t_w/2`;
- full actual web bolt grid;
- actual material axes;
- actual opening-branch group demand.

Do not physically split the Channel web in visualization.

## 26. Web face local checks

Reuse accepted local FRP connection engines where applicable for:

- pin bearing;
- net tension;
- shear-out;
- cleavage;
- block shear / accepted local path.

Evaluate back and opening face sublayers independently.

Do not merge unequal face demands before local checking.

## 27. Web splice plate local checks

Evaluate each physical web plate independently using:

- full plate thickness;
- actual plate height;
- actual group geometry;
- branch-specific Stage 2.5A demand;
- actual material basis.

Back/opening results are distinct.

## 28. Web clear-body region

Derive from the actual nearest beam-side web hole boundaries.

For default:

nearest group centers at `L=±2.5 in`.

Hole radius:

`0.2815 in`.

Clear boundaries:

`L=±2.2185 in`.

Clear body length:

`4.437 in`.

No hard-coded production value.

## 29. Web plate body method

Evaluate each web plate independently.

Reuse:

`RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`

with:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

Use branch:

- longitudinal force;
- vertical shear;
- internal major-axis moment field derived from branch free moment plus exact shear/reference effects.

Use Calculation Slice 4 pure-mode normal/shear strengths.

Back and opening web plate utilizations may differ substantially.

## 30. Flange splice plate geometry

Top and bottom flange systems are identical in RC1.

Inputs:

- flange splice plate length `L_fp`;
- flange splice plate thickness `t_fp`;
- inner flange plate width `b_i`;
- transverse bolt gauge `g_T,f`.

Default:

- `L_fp=16 in`;
- `t_fp=0.5 in`;
- `b_i=3 in`;
- `g_T,f=1.5 in`.

Outer plate width:

`b_outer=b_f`.

Inner plate centroid:

`T=b_f/2`.

Inner plate edges:

`T=(b_f-b_i)/2` to `(b_f+b_i)/2`.

Require:

`b_i <= b_f-2t_w`.

Default inner plate:

`T=0.5 to 3.5 in`.

No positive-volume web overlap.

## 31. Flange through-depth positions

Top flange centroid:

`V_top=+(d-t_f)/2`.

Top outer plate centroid:

`V_top,o=+d/2+t_fp/2`.

Top inner plate centroid:

`V_top,i=+d/2-t_f-t_fp/2`.

Bottom flange centroid:

`V_bottom=-(d-t_f)/2`.

Bottom outer:

`V_bottom,o=-d/2-t_fp/2`.

Bottom inner:

`V_bottom,i=-d/2+t_f+t_fp/2`.

All flange branch force lines retain:

`T=b_f/2`.

## 32. Flange branch decomposition

Reuse:

`RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1`.

For each flange:

`F_o+F_i=N_f`.

`e_oF_o+e_iF_i=m_T,f`.

Solve exact accepted equations.

Because:

`T_o=T_i=T_f`

require exact transverse eccentricity recovery:

`(T_f-T_c)(F_o+F_i)=M_V,f`.

No artificial flange minor-axis moment.

## 33. Default flange bolt grid

Each beam-side top/bottom flange group has:

- two transverse bolt lines;
- `n_L,f` bolts per line along `L`.

Default:

- `n_L,f=2`;
- longitudinal pitch `s_L,f=3 in`;
- group centroid distance `x_g,f=4 in`;
- transverse gauge `g_T,f=1.5 in`;
- bolt diameter `0.5 in`;
- hole diameter `0.563 in`.

Default transverse coordinates:

`T=1.25 in` and `T=2.75 in`.

Default Beam A longitudinal coordinates:

`L=-5.5,-2.5 in`.

Beam B:

`L=+2.5,+5.5 in`.

No flange bolt crosses the web.

## 34. Flange physical bolt paths

Top:

`TOP_OUTER_FLANGE_SPLICE_PLATE -> TOP_CHANNEL_FLANGE -> TOP_INNER_FLANGE_SPLICE_PLATE`.

Bottom:

`BOTTOM_OUTER_FLANGE_SPLICE_PLATE -> BOTTOM_CHANNEL_FLANGE -> BOTTOM_INNER_FLANGE_SPLICE_PLATE`.

One continuous shank per axis.

Two physical shear planes.

Exterior hardware only.

## 35. Flange face sublayers

Reuse:

`RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1`.

For local Channel flange connection checks:

- outer face effective thickness `t_f/2`, action `F_o`;
- inner face effective thickness `t_f/2`, action `F_i`;
- actual full flange width;
- actual full flange bolt grid;
- actual material axes;
- signed loaded-edge direction.

The Channel flange remains one physical member.

## 36. Flange local checks

Evaluate independently:

- outer physical splice plate;
- inner physical splice plate;
- rational outer Channel-flange face sublayer;
- rational inner Channel-flange face sublayer.

Reuse accepted local FRP connection checks.

## 37. Flange clear-body region

Derive from actual joint-side hole boundaries.

Default:

`a_body,f=4.437 in`.

Outer and inner flange plates share the same longitudinal clear-body length.

## 38. Flange plate body tension

If branch force is tensile:

use Calculation Slice 4 longitudinal tension.

Outer:

- width `b_f`;
- thickness `t_fp`;
- demand `|F_o|`.

Inner:

- width `b_i`;
- thickness `t_fp`;
- demand `|F_i|`.

## 39. Flange plate body compression

If branch force is compressive:

use Calculation Slice 4 longitudinal compression/buckling.

Panel mapping:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

Outer and inner evaluated independently.

## 40. Common-bolt physical planes

### Flange bolt

1. outer flange plate / Channel flange;
2. Channel flange / inner flange plate.

### Web bolt

1. back web plate / Channel web;
2. Channel web / opening web plate.

No other physical shear plane.

## 41. Unequal common-bolt method

Reuse:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

For each physical bolt:

- actual plane vector from the corresponding branch Stage 2.5A result;
- independent plane capacity/utilization;
- governing bolt utilization = maximum plane utilization.

Never use blind equal-plane demand.

Never use blind `2 ×` plane-capacity aggregation.

## 42. Bolt resistance source

Reuse accepted fastener source authority.

When controlled `F_nv` is available:

`phi R_plane=0.75F_nvA_b`

subject to the current thread/source contract.

If F593 remains source-pending:

- no invented strength;
- deterministic `NOT_EVALUATED` / source-required state.

## 43. Bolt-axis action

Supported RC1 branch actions remain in plate planes.

Authoritative bolt-axis force:

`0`.

Do not invoke:

- bolt tension;
- combined tension/shear for zero tension;
- numerical prying;
- pull-through from applied axis force.

## 44. Local deformation/warping limitation

Always report that:

- open-section warping response;
- Channel distortion;
- unequal web-face contact;
- secondary bolt bending;
- out-of-plane prying;
- rotational stiffness

are not established by this component-strength calculation.

These are qualification/review issues.

## 45. Whole physical equilibrium

At the exact Channel centroid require exact recovery of the Slice 6 canonical centroid wrench from:

- top outer/inner flange branches;
- back/opening web branches;
- bottom outer/inner flange branches.

Require exact:

- axial `P_L`;
- major shear `V_V`;
- transverse force zero;
- major moment `M_T`;
- minor-axis moment zero;
- generated torsion `M_L,C`.

No residual dumping.

## 46. Transverse eccentricity trace

The UI/result shall preserve the Slice 6 individual:

- top flange `M_V`;
- web `M_V`;
- bottom flange `M_V`.

The physical branch system shall recover those contributions at the exact component transverse coordinates.

Do not hide them merely because total `M_V=0`.

## 47. Beam A / Beam B equilibrium

Beam A complete interface wrench:

canonical transfer.

Beam B:

exact negative.

Each splice plate has equal/opposite beam-side actions according to exact plate equilibrium.

No external support/foundation handoff exists.

## 48. Default Slice 6 benchmark

For default Channel/actions require accepted Slice 6 values.

### Centroid/shear center

`T_c=1.18333333333333333333333333333333333333333333333333333333333333333333333333333333333333333 in`.

Rational:

`T_sc=-1.15625 in`.

### Top flange

`N_top=15.9528023598820058997050147492625368731563421828908554572271386430678466076696165191740412 kip`.

`m_T,top=0.0589970501474926253687315634218289085545722713864306784660766961651917404129793510324483775 kip-in`.

### Web

`N_web=9.33333333333333333333333333333333333333333333333333333333333333333333333333333333333333333 kip`.

`V_web=-10 kip`.

`m_T,web=20.2359882005899705014749262536873156342182890855457227138643067846607669616519174041297935 kip-in`.

`m_L,web=-14.0625 kip-in`.

### Bottom flange

`N_bottom=-5.28613569321533923303834808259587020648967551622418879056047197640117994100294985250737457 kip`.

`m_T,bottom=0.0589970501474926253687315634218289085545722713864306784660766961651917404129793510324483775 kip-in`.

Generated centroidal torsion:

`-23.3958333333333333333333333333333333333333333333333333333333333333333333333333333333333333 kip-in`.

## 49. Default flange branch benchmark

For default `t_fp=0.5 in`:

Top:

`F_top,o=8.03539823008849557522123893805309734513274336283185840707964601769911504424778761061946898 kip`.

`F_top,i=7.91740412979351032448377581120943952802359882005899705014749262536873156342182890855457222 kip`.

Bottom:

`F_bottom,o=-2.70206489675516224188790560471976401179941002949852507374631268436578171091445427728613566 kip`.

`F_bottom,i=-2.5840707964601769911504424778761061946902654867256637168141592920353982300884955752212389 kip`.

Require exact force/local-moment/global-transverse-moment recovery.

## 50. Default web branch benchmark

For:

- `t_w=0.5 in`;
- `t_wp=0.5 in`;

web plate centroid offsets are:

`e_back=-0.5 in`.

`e_open=+0.5 in`.

Then:

`N_back=N_open=4.66666666666666666666666666666666666666666666666666666666666666666666666666666666666666666 kip`.

`m_T,back=m_T,open=10.1179941002949852507374631268436578171091445427728613569321533923303834808259587020648968 kip-in`.

`Q_back=-19.0625 kip`.

`Q_open=+9.0625 kip`.

Require exact:

`Q_back+Q_open=-10 kip`.

`-e_backQ_back-e_openQ_open=-14.0625 kip-in`.

## 51. Default flange direct per-plane benchmark

For the symmetric 4-bolt flange group, before any additional Stage 2.5A correction (none exists for the default branch line through its group centroid):

Top outer per bolt:

`2.00884955752212389380530973451327433628318584070796460176991150442477876106194690265486724 kip`.

Top inner:

`1.97935103244837758112094395280235988200589970501474926253687315634218289085545722713864306 kip`.

Bottom outer:

`-0.675516224188790560471976401179941002949852507374631268436578171091445427728613569321533915 kip`.

Bottom inner:

`-0.646017699115044247787610619469026548672566371681415929203539823008849557522123893805309725 kip`.

Signed provenance retained.

## 52. Analytical F3125 plane benchmark

Test-only:

- bolt diameter `0.5 in`;
- `F_nv=68 ksi`;
- `phi=0.75`;
- threads excluded.

Per-plane design shear strength:

`10.013826583317465947599675784203415443378477460508149804357635887981164795036625 kip`.

Expected flange utilizations:

- top outer:
  `0.200607584004776630058159232541722076317597582276362249471291963776475158427051615839728296`;
- top inner:
  `0.197661804503972274257011519875911179455371479746606562988600451826747182532381254373652991`;
- bottom outer:
  `0.0674583505684197478462826200470695381449777479314052204536356236487706479879512775731244927`;
- bottom inner:
  `0.0645125710676153920451349073812586412827516454016495339709441116990426720932809161070491872`.

Test-only values do not override production source selection.

## 53. Web body arithmetic benchmark

For arithmetic tests only:

- web plate height `5.5 in`;
- plate thickness `0.5 in`;
- clear section `L=+2.2185 in`;
- test design normal tension `12 ksi`;
- compression `10 ksi`;
- shear `5 ksi`.

Back plate internal major moment at `+2.2185 in`:

`52.4081503502949852507374631268436578171091445427728613569321533923303834808259587020648968 kip-in`.

Opening plate internal major moment:

`-9.9871621497050147492625368731563421828908554572271386430678466076696165191740412979351032 kip-in`.

Expected test-only rational body utilization:

Back:

`3.29566767229820327165459908822740681147760793778492893537141324751944220970769643336015017`.

Opening:

`1.13065917115645595130711783970030148630309531355388153457340907059330229080832459754422747`.

These are arithmetic regression values only.

A default benchmark may legitimately fail a component check; do not alter demand to create a passing example.

## 54. Pure axial case

For:

`P=+20 kip, V=0, M=0`

Slice 6:

- top `N=5.333333333333333... kip`;
- web `N=9.333333333333333... kip`;
- bottom `N=5.333333333333333... kip`;
- all local major moments zero;
- generated torsion zero.

Flange branches:

- top outer `2.666666666666... kip`;
- top inner `2.666666666666... kip`;
- bottom outer `2.666666666666... kip`;
- bottom inner `2.666666666666... kip`.

Web:

- `N_back=N_open=4.666666666666... kip`;
- `Q_back=Q_open=0`;
- no web torsional couple.

## 55. Pure major moment case

For:

`P=0, V=0, M=+100 kip-in`

require:

- top tension;
- bottom compression;
- web longitudinal force zero;
- web local major moment retained;
- generated torsion zero;
- back/opening web shear zero;
- flange branch local-moment recovery exact.

## 56. Pure major shear case

For:

`P=0, V=-10 kip, M=0`

require:

- top/bottom longitudinal flange branch forces zero;
- web longitudinal force zero;
- web local major moment zero;
- `Q_back=-19.0625 kip`;
- `Q_open=+9.0625 kip`;
- generated centroidal torsion retained;
- web free torsion retained.

This case is mandatory visual/result evidence that the Channel shear-center effect is not lost.

## 57. Major shear sign reversal

For `V -> -V`:

- `Q_back`, `Q_open` reverse;
- generated centroidal torsion reverses;
- web free torsion reverses;
- flange longitudinal branch forces remain unchanged for unchanged `P/M`;
- geometry unchanged.

## 58. Major moment sign reversal

For `M -> -M`:

- flange tension/compression roles reverse as dictated by combined `P/M`;
- local major moments reverse;
- web free torsion remains unchanged for same `V`;
- transverse eccentricity ledger recomputes exactly;
- whole six-component equilibrium remains exact.

## 59. Explicit verified shear-center case

The physical splice shall use the explicit Slice 6 shear-center coordinate when that mode is selected.

Web branch forces shall recompute from the resulting `m_L,web`.

No rational value may silently control.

## 60. Preview behavior

Preview executes:

- strict validation;
- complete Channel geometry;
- Slice 6;
- flange branch decomposition;
- web face branch decomposition;
- physical plate geometry;
- bolt paths/endpoints;
- Stage 2.5A demand planning;
- material axes;
- exact equilibrium;
- source/applicability plan;
- review/qualification/disclaimer.

Preview resistance calls:

`0`.

## 61. Explicit Run Design Check

Only explicit design action evaluates:

- Channel web face rational local checks;
- physical web plate local/body checks;
- web common-bolt unequal planes;
- Channel flange rational face local checks;
- physical flange plate local/body checks;
- flange common-bolt unequal planes;
- all source/applicability limits;
- whole result aggregation.

Engineering edits stale the design.

## 62. Overall result precedence

1. invalid/rejected -> invalid/rejected;
2. any required evaluated failure -> `FAIL`;
3. required source/method unavailable -> `NOT_EVALUATED`;
4. all required numerical strength checks pass ->
   `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Ordinary `PASS` prohibited.

## 63. Mandatory review metadata

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

`CHANNEL_MOMENT_SPLICE_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`.

## 64. Mandatory unevaluated classifications

Always:

`MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION=NOT_EVALUATED`.

`MOMENT_ROTATION_CAPACITY=NOT_EVALUATED`.

`FULL_STRENGTH_CLASSIFICATION=NOT_EVALUATED`.

`OPEN_SECTION_WARPING_CONNECTION_RESPONSE=NOT_EVALUATED`.

## 65. Mandatory disclaimer

Backend ID:

`CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1`.

Backend owns the full controlled meaning from the Decision/Authority Ledger.

Frontend displays but does not rewrite engineering meaning.

## 66. Visualization

Required 3D geometry:

- two Channel beams open toward the same `+T_CH`;
- positive gap;
- back web plate;
- opening web plate;
- top outer plate;
- top inner plate;
- bottom outer plate;
- bottom inner plate;
- all web/flange bolts and holes;
- exterior hardware;
- material axes;
- action arrows;
- centroid reference;
- shear-center reference;
- generated torsion indication/trace.

## 67. X-ray / inspection

X-ray/camera shall allow inspection of:

- opening-side web plate;
- top inner plate;
- bottom inner plate;
- internal nuts/washers exterior to inner plates;
- no flange/web plate positive-volume overlap.

## 68. Backend-authoritative visualization

Backend owns:

- Channel solids;
- plate solids;
- contact surfaces;
- bolt physical endpoints;
- layer order;
- material axes;
- centroid;
- shear center;
- action references;
- branch references.

Frontend maps scene primitives only.

## 69. Result trace

Expose at minimum:

- original `P/V/M`;
- Channel centroid;
- shear center/source;
- generated centroidal torsion;
- Slice 6 top/web/bottom component wrenches;
- transverse eccentricity ledger;
- top outer/inner branch forces;
- bottom outer/inner branch forces;
- back/opening web branch forces/wrenches;
- exact torsional recovery;
- physical bolt-plane demands;
- governing strength result;
- rational methods/review/qualification/disclaimer;
- stiffness/warping limitations.

No hidden redistribution.

## 70. Invalid geometry

At minimum reject:

- nonpositive gap;
- invalid Channel dimensions;
- unsupported Channel type;
- unequal/mirrored beams;
- missing plate;
- inner flange plate/web overlap;
- web plate/flange-inner-plate overlap;
- flange/web hole outside any physical layer;
- flange bolt through web;
- web bolt into flange;
- invalid plate dimensions;
- invalid edge/end/pitch/gauge;
- hardware collision;
- asymmetric web plate geometry in RC1;
- flange inner plate centroid shifted away from `T_f`;
- unsupported action;
- invalid shear-center source/provenance.

No auto-repair.

## 71. Deterministic fingerprints

Include:

- product/contract;
- Channel geometry/orientation;
- gap;
- Slice 6 fingerprint;
- centroid/shear-center source;
- generated torsion;
- plate geometry;
- bolt grids/physical paths;
- material bases;
- flange branch decomposition;
- web branch decomposition;
- rational face sublayers;
- group wrenches;
- per-plane bolt vectors;
- local/body resistance provenance;
- exact equilibrium;
- result/status;
- review/qualification/disclaimer.

Presentation excluded.

## 72. U.S./SI equivalence

Equivalent physical inputs preserve:

- Channel geometry;
- centroid/shear center;
- generated torsion;
- component wrenches;
- flange/web branch forces;
- physical bolt paths;
- local/group demand;
- resistance;
- exact equilibrium;
- status;
- fingerprints.

No unit-specific engineering branch.

## 73. Historical/frozen invariance

Require exact:

- Stage 4.1A freeze;
- Calculation Slice 5;
- Calculation Slice 6;
- Stage 3.7 / 3.6 / 3.5 / 3.4 / 3.3 / 3.2 / 2.3 freeze audits;
- historical W/I Moment Splice;
- all historical shear products;
- all historical fingerprints.

Stage 4.1B adds a new Channel product only.

## 74. Controlled golden coverage

The Stage 4.1B golden fixture shall contain exactly `G1-G112`.

It shall cover:

- product/scope;
- Channel orientation;
- centroid/shear-center handoff;
- generated torsion;
- physical topology;
- web/flange plate geometry;
- bolt paths;
- flange branch equations;
- web shear-center branch equations;
- exact six-component equilibrium;
- transverse eccentricity recovery;
- Stage 2.5A integration;
- rational web/flange face sublayers;
- independent web plate body behavior;
- unequal two-plane bolts;
- source pending;
- pure axial/moment/shear;
- sign reversal;
- explicit shear-center mode;
- invalid/unsupported behavior;
- preview/design separation;
- result precedence;
- review/qualification/warping limitations;
- U.S./SI;
- fingerprints;
- visualization contract;
- all freeze/historical regressions.

## 75. Acceptance boundary

Stage 4.1B RC1 is accepted only if:

- Calculation Slice 6 remains exact;
- Channel centroid/shear center are retained;
- generated torsion is retained;
- flange branches recover complete flange wrenches without shifting transverse force lines;
- web back/opening branches recover the complete web wrench including free torsion;
- no equal web-shear assumption is introduced;
- web and flange face local transfer uses controlled rational sublayers;
- common bolts use actual unequal plane vectors;
- web plate bodies are checked independently;
- exact six-component centroidal equilibrium closes;
- user torsion/warping strength is not invented;
- successful design remains review-required;
- complete local/object-isolated QA passes;
- hosted CI 4/4 passes;
- owner visual/result acceptance passes.

**END OF STAGE 4.1B CHANNEL MAJOR-AXIS MOMENT SPLICE ENGINEERING SPECIFICATION RC1**
