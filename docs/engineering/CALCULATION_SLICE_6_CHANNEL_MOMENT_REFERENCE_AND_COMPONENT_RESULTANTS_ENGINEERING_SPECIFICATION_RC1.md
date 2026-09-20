# FRP Master Connection — Calculation Slice 6 — Channel Major-Axis Moment Reference and Component Resultants — Engineering Specification RC1

## 1. Status

**Controlled shared calculation authority — RC1**

Calculation Slice 6 is the mandatory engineering prerequisite for Stage 4.1B Channel Beam Moment Splice.

It establishes:

- exact Channel centroid and centroidal section properties;
- a controlled Channel shear-center source contract;
- exact generated torsion associated with the major-shear reference;
- exact top-flange, web, and bottom-flange component wrenches;
- exact major-axis, minor-axis, and torsional equilibrium traces.

It does not add the physical Channel splice product.

## 2. Accepted starting baseline

Expected repository state:

- branch `main`;
- `HEAD == origin/main == remote main`:
  `cc9effad0691d083bb204c44ec3fb6e9dfb3671d`;
- subject:
  `chore: freeze Stage 4.1A W/I moment splice baseline`;
- commit count:
  `99`;
- clean worktree/index.

Stage 4.1A freeze hosted CI:

- GitHub Actions run #94;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `6m 1s`.

Expected Stage 4.1A freeze tag:

`stage-4.1a-wi-major-axis-moment-splice-freeze`

tag object:

`a265ff394413d8fef16e7012c1de910bf3ece1b7`

peeled target:

`cc9effad0691d083bb204c44ec3fb6e9dfb3671d`.

All earlier freeze tags remain immutable.

## 3. Source hierarchy

Controlling sources:

1. ASCE/SEI 74-23 and applicable commentary;
2. Erratum 1;
3. this specification;
4. the companion golden benchmark file;
5. accepted repository geometry, quantity, provenance, and fingerprint contracts.

Source-derived requirements include:

- Channel eccentricity must not be ignored;
- connection forces/deformations must be consistent with structural analysis;
- flexural splices must transfer applicable forces and moments;
- the web/shear part retains shear, bolt-group eccentricity effects, and its moment proportion;
- open-section torsion and unsymmetrical Channel connection behavior require rational analysis and Section 2.3.2 review/qualification.

The exact Channel region integration and shear-center equations in this slice are project-controlled rational methods.

## 4. Method identities

Contract:

`CS6-RC1`.

Component-resultant method:

`RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1`.

Default shear-center method:

`RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1`.

Alternative shear-center method:

`EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1`.

Unknown future versions fail closed.

## 5. Product/UI boundary

Calculation Slice 6 is backend-only.

It shall not add:

- a Moment Connections selector item;
- a Channel moment-splice workspace;
- splice plates;
- bolt groups;
- resistance calculations;
- connection status;
- 3D product geometry.

Expected frontend production changes:

`0`.

## 6. Supported Channel geometry

Support exactly one unlipped equal-flange Channel defined by:

- overall depth `d`;
- flange width `b_f`, measured from the back web face to the flange tip;
- web thickness `t_w`;
- flange thickness `t_f`.

Require:

- finite positive dimensions;
- `d > 2t_f`;
- `b_f > t_w`;
- equal top and bottom flange geometry;
- homogeneous longitudinal material stiffness across web and flanges for RC1;
- the existing sharp-corner geometry idealization.

Reject:

- lipped Channels;
- unequal flanges;
- back-to-back Channels;
- built-up Channels;
- hybrid longitudinal moduli;
- W/I, Angle, RHS, and SRS profiles.

## 7. Channel profile frame

Use local axes:

- `L_CH`: member longitudinal axis;
- `V_CH`: depth axis, positive toward the top flange;
- `T_CH`: opening direction, positive from the back web face toward the flange tips.

Geometry construction origin:

- `L_CH=0` at the evaluated member-end section;
- `V_CH=0` at middepth;
- `T_CH=0` at the back web face.

The exact member centroid is:

`C=(0,0,T_c)`.

All returned component-reference coordinates are relative to `C`.

## 8. Region geometry

Define:

`h_w=d-2t_f`

`A_f=b_f t_f`

`A_w=t_w h_w`

`A=2A_f+A_w`.

Absolute region coordinates:

`V_top=+(d-t_f)/2`

`V_web=0`

`V_bottom=-(d-t_f)/2`

`T_f=b_f/2`

`T_w=t_w/2`.

## 9. Exact centroid

Calculate:

`T_c=(2A_fT_f+A_wT_w)/A`.

The centroid is exact solid-region geometry.

Do not replace it with:

- web mid-plane;
- half flange width by assumption;
- a frontend coordinate;
- the rational shear center.

## 10. Exact centroidal second moments

Major axis:

`I_f,T,c=b_f t_f^3/12`

`I_w,T,c=t_w h_w^3/12`

`I_T=2(I_f,T,c+A_fV_top^2)+I_w,T,c`.

Minor axis:

`I_f,V,c=t_f b_f^3/12`

`I_w,V,c=h_w t_w^3/12`

`I_V=I_w,V,c+A_w(T_w-T_c)^2+2[I_f,V,c+A_f(T_f-T_c)^2]`.

For this singly symmetric geometry:

`I_VT=0`.

Use exact Decimal quantities and existing fourth-power inertia units.

## 11. Homogeneous-section boundary

The stress field in RC1 assumes the web and flanges share the same longitudinal modulus/material architecture.

If longitudinal moduli differ:

`CS6_CHANNEL_REGION_DECOMPOSITION = REQUIRES_SECTION_2_3_2`.

Do not silently use geometric area instead of transformed-section area.

## 12. Shear-center source contract

Exactly one controlling shear-center source is required.

### Mode A — rational geometry

`RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1`.

### Mode B — explicit verified property

`EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1`.

Do not blend or average sources.

Fingerprint the controlling source and provenance.

## 13. Rational median-line geometry

For rational mode:

`h_m=d-t_f`

`b_m=b_f-t_w/2`.

Require:

- `h_m>0`;
- `b_m>0`.

Median-line major-axis inertia:

`I_T,m=t_w h_m^3/12+2t_f b_m(h_m/2)^2`.

## 14. Rational shear-center calculation

Offset magnitude from the web midline toward the side opposite the opening:

`e_w=t_f h_m^2 b_m^2/(4I_T,m)`.

Equivalent controlled closed form:

`e_w=3t_f b_m^2/(t_wh_m+6t_fb_m)`.

Absolute shear-center coordinate:

`T_sc=t_w/2-e_w`.

Centroid-to-shear-center distance:

`e_Csc=T_c-T_sc`.

Require the two `e_w` expressions to agree under the implementation's exact arithmetic/canonicalization.

## 15. Rational shear-center limitations

The method is an open-section thin-wall rational approximation.

Always return:

`CHANNEL_SHEAR_CENTER_SOURCE = RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1`

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED = true`.

Also return:

- `t_w/h_m`;
- `t_f/b_m`;
- median-line dimensions;
- method fingerprint;
- source/provenance.

Do not label the result as experimentally verified.

## 16. Explicit verified shear-center mode

Input:

- exact absolute `T_sc`;
- deterministic nonempty source/provenance record.

Examples of acceptable provenance categories:

- manufacturer property;
- controlled finite-element section analysis;
- controlled physical test;
- approved engineering calculation record.

If provenance is absent:

reject.

The explicit value controls all torsional/reference calculations.

The rational value may be calculated only as a noncontrolling comparison diagnostic.

## 17. Action-reference convention

Input actions:

- axial force `P_L` through the exact centroid `C`;
- major-axis free moment `M_T` at `C`;
- major shear `V_V` acting through the selected shear center `(0,0,T_sc)`.

Require exact zero / reject:

- minor shear `V_T`;
- minor-axis moment `M_V`;
- user torsion `M_L,user`.

The generated torsion caused by the major-shear reference remains authorized.

## 18. Canonical centroid wrench

Equivalent canonical wrench at `C`:

- force:
  `(P_L,V_V,0)` in `(L_CH,V_CH,T_CH)`;
- free moment:
  `(M_L,C,0,M_T)`.

Controlled generated torsion:

`M_L,C=(T_c-T_sc)V_V`.

No tolerance zeroing.

## 19. Longitudinal stress field

Use:

`σ_L(V)=P_L/A+M_TV/I_T`.

No plastic redistribution.

No tension-only contact behavior.

No minor-axis bending.

## 20. Region longitudinal resultants

For each region `i`:

`N_i=P_LA_i/A+M_TA_iV_i/I_T`.

Return signed:

- `N_top`;
- `N_web`;
- `N_bottom`.

Positive = tension.

Negative = compression.

## 21. Region local major moments

For each region:

`m_T,i=M_TI_i,T,c/I_T`.

Do not discard local flange or web moments.

## 22. Region global major moment contribution

For the inherited major-axis sign convention:

`M_T,i=V_iN_i+m_T,i`.

Require:

`ΣM_T,i=M_T`.

## 23. Longitudinal-force transverse eccentricity ledger

Relative coordinates:

`ΔT_f=T_f-T_c`

`ΔT_w=T_w-T_c`.

For each region return:

`M_V,i=ΔT_iN_i`.

Require:

`M_V,top+M_V,web+M_V,bottom=0`

for supported centroidal axial + major-axis bending actions.

The individual nonzero contributions remain visible.

This ledger is mandatory input to later Stage 4.1B physical connection equilibrium.

## 24. Major shear allocation

RC1 assigns:

- top flange major shear = `0`;
- web major shear = `V_V`;
- bottom flange major shear = `0`.

No flange major-shear distribution equation.

## 25. Web force-line torsion

The web shear acts at `T_w`.

Its centroidal torsion contribution is:

`M_L,web-force=(T_c-T_w)V_V`.

## 26. Web free torsion

Assign the web component free torsion:

`m_L,web=(T_w-T_sc)V_V`.

Require:

`M_L,web-force+m_L,web=M_L,C`.

This is a demand decomposition, not torsional resistance.

## 27. Rational shear-flow diagnostic

For rational shear-center mode:

`H_f=V_Vt_fh_mb_m^2/(4I_T,m)`.

Require:

`H_fh_m=m_L,web`.

Return `H_f` as a provenance/communication diagnostic.

Do not use it as a physical flange splice demand in this calculation slice.

## 28. Component references

Relative to centroid `C`:

### Top flange

`r_top=(0,V_top,T_f-T_c)`.

### Web

`r_web=(0,0,T_w-T_c)`.

### Bottom flange

`r_bottom=(0,V_bottom,T_f-T_c)`.

These are physical region centroids.

## 29. Component wrenches

### Top flange

Force:

`(N_top,0,0)`.

Local free moment:

`(0,0,m_T,top)`.

### Web

Force:

`(N_web,V_V,0)`.

Local free moment:

`(m_L,web,0,m_T,web)`.

### Bottom flange

Force:

`(N_bottom,0,0)`.

Local free moment:

`(0,0,m_T,bottom)`.

Use existing immutable vector/wrench contracts where compatible.

## 30. Exact equilibrium proof

Return a deterministic six-component equilibrium trace.

Require exact:

`ΣF_L=P_L`

`ΣF_V=V_V`

`ΣF_T=0`

`ΣM_T=M_T`

`ΣM_V=0`

`ΣM_L=M_L,C`.

No tolerance residual dumping.

## 31. Major-axis couple diagnostics

Return:

`z_f=d-t_f`

`C_f=(N_top-N_bottom)/2`

`M_couple=C_fz_f`

`C_M_over_z=M_T/z_f`

`M_residual=M_T-M_couple`.

Require exact residual identity with web and local flange major-moment contributions.

`C_M_over_z` is:

`REFERENCE_ONLY_NOT_CONTROLLING_COMPONENT_DEMAND`.

## 32. Stress extrema

Return signed stresses at:

### Top flange

- inner depth face `V=d/2-t_f`;
- outer depth face `V=d/2`.

### Web

- bottom edge `V=-h_w/2`;
- top edge `V=+h_w/2`.

### Bottom flange

- outer depth face `V=-d/2`;
- inner depth face `V=-d/2+t_f`.

## 33. Region state

For each resultant:

- `TENSION` if `N_i>0`;
- `COMPRESSION` if `N_i<0`;
- `ZERO_FORCE` if `N_i=0`.

Return stress zero-crossing independently.

## 34. Default geometry benchmark

Use:

- `d=8 in`;
- `b_f=4 in`;
- `t_w=0.5 in`;
- `t_f=0.5 in`.

Expected:

- `h_w=7 in`;
- `A_f=2 in²`;
- `A_w=3.5 in²`;
- `A=7.5 in²`;
- `V_top=+3.75 in`;
- `V_bottom=-3.75 in`;
- `T_f=2 in`;
- `T_w=0.25 in`;
- `T_c=1.18333333333333333333333333333333333333333333333333333333333333333333333333333333333333333 in`;
- `I_T=70.625... in⁴` as controlled by the golden;
- `I_V=11.1229166666666666666666666666666666666666666666666666666666666666666666666666666666666667 in⁴`.

## 35. Default rational shear-center benchmark

Expected:

- `h_m=7.5 in`;
- `b_m=3.75 in`;
- `I_T,m=70.3125 in⁴`;
- `e_w=1.40625 in`;
- `T_sc=-1.15625 in`;
- `e_Csc=2.33958333333333333333333333333333333333333333333333333333333333333333333333333333333333333 in`.

## 36. Default actions

Use:

- `P_L=+20 kip`;
- `V_V=-10 kip`;
- `M_T=+100 kip-in`.

Expected canonical generated torsion:

`M_L,C=-23.3958333333333333333333333333333333333333333333333333333333333333333333333333333333333333 kip-in`.

## 37. Default component-resultant benchmark

Top:

`N_top=15.9528023598820058997050147492625368731563421828908554572271386430678466076696165191740412 kip`.

`m_T,top=0.0589970501474926253687315634218289085545722713864306784660766961651917404129793510324483775 kip-in`.

Web:

`N_web=9.33333333333333333333333333333333333333333333333333333333333333333333333333333333333333333 kip`.

`V_web=-10 kip`.

`m_T,web=20.2359882005899705014749262536873156342182890855457227138643067846607669616519174041297935 kip-in`.

`m_L,web=-14.0625 kip-in`.

Bottom:

`N_bottom=-5.28613569321533923303834808259587020648967551622418879056047197640117994100294985250737457 kip`.

`m_T,bottom=0.0589970501474926253687315634218289085545722713864306784660766961651917404129793510324483775 kip-in`.

## 38. Default transverse eccentricity ledger

Expected:

- top `M_V=+13.0281219272369714847590953785644051130776794493608652900688298918387413962635201573254670 kip-in`;
- web `M_V=-8.71111111111111111111111111111111111111111111111111111111111111111111111111111111111111108 kip-in`;
- bottom `M_V=-4.31701081612586037364798426745329400196656833824975417895771878072763028515240904621435592 kip-in`;
- exact sum = zero.

## 39. Default torsion benchmark

Expected:

- web shear force-line torsion:
  `-9.33333333333333333333333333333333333333333333333333333333333333333333333333333333333333330 kip-in`;
- web free torsion:
  `-14.0625 kip-in`;
- centroidal total:
  `-23.3958333333333333333333333333333333333333333333333333333333333333333333333333333333333333 kip-in`;
- flange shear-flow resultant:
  `-1.875 kip` per flange;
- `H_fh_m=-14.0625 kip-in`.

## 40. Explicit verified shear-center benchmark

Use:

`T_sc=-1.0 in`

with valid test provenance.

Expected:

- `e_Csc=2.18333333333333333333333333333333333333333333333333333333333333333333333333333333333333333 in`;
- centroidal torsion for default `V=-10`:
  `-21.8333333333333333333333333333333333333333333333333333333333333333333333333333333333333333 kip-in`;
- web free torsion:
  `-12.5 kip-in`.

## 41. Pure action cases

### Pure axial

`P=+20`, `V=0`, `M=0`:

- top `5.333333333333... kip`;
- web `9.333333333333... kip`;
- bottom `5.333333333333... kip`;
- all local moments zero;
- minor-moment ledger sums zero;
- generated torsion zero.

### Pure major moment

`P=0`, `V=0`, `M=+100`:

- top `+10.619469026548672566... kip`;
- web axial zero;
- bottom `-10.619469026548672566... kip`;
- local major moments retained;
- minor-moment ledger sums zero;
- generated torsion zero.

### Pure major shear

`P=0`, `V=-10`, `M=0`:

- normal resultants zero;
- web shear `-10 kip`;
- centroidal torsion and web free torsion remain as the default shear-center benchmark.

## 42. Sign reversal

Require exact:

- `P -> -P`: uniform region shares reverse;
- `M -> -M`: bending region forces/local major moments reverse;
- `V -> -V`: web shear, centroidal torsion, web free torsion, and `H_f` reverse;
- geometry/reference coordinates remain unchanged.

## 43. Invalid and unsupported inputs

Reject:

- nonpositive dimensions;
- `d<=2t_f`;
- `b_f<=t_w`;
- missing explicit shear-center provenance;
- simultaneous conflicting shear-center source modes;
- minor shear;
- minor-axis moment;
- user torsion;
- unsupported profile;
- inhomogeneous longitudinal-modulus Channel under RC1.

No absolute-value or epsilon repair.

## 44. U.S./SI equivalence

Equivalent physical inputs preserve:

- geometry;
- centroid;
- section properties;
- shear-center coordinate/source;
- component references/wrenches;
- stress extrema;
- minor-moment ledger;
- generated torsion;
- equilibrium;
- fingerprints.

No unit-specific formula branch.

## 45. Deterministic fingerprints

Include:

- contract/methods;
- geometry and source profile identity;
- centroid/section properties;
- shear-center source/provenance;
- input multi-reference actions;
- canonical centroid wrench;
- component references/wrenches;
- stress extrema/states;
- minor-moment ledger;
- torsional ledger;
- couple diagnostics;
- equilibrium;
- review/disclaimer metadata.

Presentation excluded.

## 46. Review and disclaimer

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

Disclaimer ID:

`CHANNEL_MOMENT_REFERENCE_AND_COMPONENT_RESULTANTS_DISCLAIMER_RC1`.

No frontend-authored substitute.

No report generator required in this slice.

## 47. No strength result

Calculation Slice 6 returns demand/reference authority only.

Do not calculate:

- local FRP capacity;
- Channel splice plate capacity;
- bolt capacity;
- open-section torsional/warping stress;
- connection PASS/FAIL;
- connection stiffness;
- moment-rotation capacity.

## 48. Required controlled golden cases

The companion golden contains exactly `G1-G72`, covering:

- geometry;
- centroid;
- major/minor properties;
- rational and explicit shear-center modes;
- default component wrenches;
- six-component equilibrium;
- transverse eccentricity;
- generated torsion;
- pure actions;
- sign reversals;
- invalid/unsupported states;
- U.S./SI;
- fingerprints;
- review/disclaimer;
- no frontend/product work;
- all freeze regressions.

## 49. Production architecture

Expected backend production changes only.

Suggested conceptual module:

`calculation/channel_moment_resultants.py`.

Exact repository naming may follow architecture.

Reuse existing:

- profile geometry records;
- quantities;
- Decimal helpers;
- vector/wrench types;
- provenance;
- fingerprint;
- applicability/status;
- review/disclaimer metadata.

Do not duplicate current Channel geometry.

## 50. Historical/frozen invariance

Require exact:

- Stage 4.1A freeze;
- Stage 3.7 freeze;
- Stage 3.6 freeze;
- Stage 3.5/3.4/3.3/3.2/2.3 freezes;
- Calculation Slice 5;
- all existing product fingerprints.

Calculation Slice 6 is not wired into historical products.

## 51. Acceptance boundary

Calculation Slice 6 is accepted only if:

- exact Channel centroid and section properties are correct;
- no web-centered/W/I reference assumption remains;
- the controlling shear-center source is explicit and fingerprinted;
- rational shear-center limitations are visible;
- generated centroidal torsion is retained;
- web force-line and free torsion close exactly;
- individual transverse eccentricity moments are retained and cancel exactly;
- top/web/bottom component wrenches close all six supported components;
- unsupported user torsion/minor actions fail closed;
- no strength or physical splice is added;
- frontend production change count is zero;
- complete local/object-isolated QA passes;
- hosted CI 4/4 passes;
- all frozen families remain exact.

**END OF CALCULATION SLICE 6 CHANNEL MOMENT REFERENCE AND COMPONENT RESULTANTS ENGINEERING SPECIFICATION RC1**
