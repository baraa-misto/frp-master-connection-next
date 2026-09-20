# FRP Master Connection — Calculation Slice 6 — Channel Major-Axis Moment Reference and Component Resultants — Decision

## Decision

Stage 4.1B — Channel Beam Moment Splice shall begin with a separate shared prerequisite:

**Calculation Slice 6 — Channel Major-Axis Member-End Reference, Shear-Center Eccentricity, and Top-Flange / Web / Bottom-Flange Component Resultants**

This is a backend calculation authority.

It is not yet the physical Channel moment-splice product.

No normal frontend selector, workspace, splice plate, bolt group, resistance check, or connection PASS/FAIL result is added by this slice.

## Why this prerequisite is separate from Calculation Slice 5

Calculation Slice 5 is frozen with Stage 4.1A and applies to symmetric W/I sections.

A Channel section is singly symmetric and has:

- a centroid offset from the web plane;
- flange and web longitudinal-force resultants at different transverse coordinates;
- a shear center that is generally outside the web on the side opposite the opening;
- a real torsional wrench whenever major shear is represented through the shear center and the equivalent wrench is reported at the centroid;
- connection eccentricities that cannot be removed by copying the W/I reference or by moving the member action line to the web.

Therefore Stage 4.1B shall not reuse W/I assumptions such as a web-centered member reference or zero shear-center eccentricity.

## Source and rational-authority distinction

ASCE/SEI 74-23 recognizes singly symmetric Channels in member design, requires eccentricities of Channels and their connections to be accounted for, and requires moment/splice actions to be transferred consistently with structural analysis.

The standard does not supply the complete Channel region-resultant decomposition or a geometric shear-center formula for this connection implementation.

Calculation Slice 6 therefore separates:

### Exact solid-region geometry

- Channel area;
- exact centroid of the accepted sharp-corner union-of-rectangles profile;
- exact major/minor centroidal section properties;
- exact top-flange, web, and bottom-flange reference locations;
- exact integration of axial force and major-axis moment over the three physical regions.

### Rational shear-center authority

Default method:

`RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1`.

Alternative method:

`EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1`.

The rational thin-wall method is a project engineering approximation and always requires engineering review.

An explicit verified shear-center coordinate may be supplied only with deterministic provenance identifying the manufacturer, test, analysis, or other controlled source.

## RC1 Channel scope

Support only:

- an unlipped pultruded Channel;
- equal top and bottom flange geometry;
- the existing sharp-corner Channel model;
- one web and two flanges made from the accepted common material architecture;
- major-axis bending about the depth-symmetry axis;
- axial force;
- major shear;
- zero user torsion;
- zero minor shear;
- zero minor-axis moment.

No W/I, Angle, RHS, SRS, lipped Channel, back-to-back Channel, or unequal-flange Channel is included.

## Channel frame

Use a right-handed Channel member frame:

- `L_CH`: member longitudinal axis;
- `V_CH`: depth axis, positive toward the top flange;
- `T_CH`: opening direction, positive from the back web face toward the flange tips.

Profile construction coordinates:

- web back face: `T_CH=0`;
- flange tips: `T_CH=b_f`;
- middepth: `V_CH=0`.

The member centroid is:

`C=(0,0,T_c)`.

All component references returned to consumers are expressed relative to `C`.

## Accepted sharp-corner region geometry

For:

- overall depth `d`;
- flange width `b_f`, measured from the web back face to the flange tip;
- web thickness `t_w`;
- flange thickness `t_f`;

define:

`h_w=d-2t_f`

`A_f=b_f t_f`

`A_w=t_w h_w`

`A=2A_f+A_w`.

Absolute transverse region coordinates:

`T_f=b_f/2`

`T_w=t_w/2`.

Exact centroid:

`T_c=(2A_fT_f+A_wT_w)/A`.

Vertical flange centroids:

`V_top=+(d-t_f)/2`

`V_bottom=-(d-t_f)/2`.

## Exact centroidal section properties

Major-axis second moment:

`I_T=2[I_f,T,c+A_f V_top^2]+I_w,T,c`

where:

`I_f,T,c=b_f t_f^3/12`

`I_w,T,c=t_w h_w^3/12`.

Minor-axis second moment:

`I_V=I_w,V,c+A_w(T_w-T_c)^2+2[I_f,V,c+A_f(T_f-T_c)^2]`

where:

`I_w,V,c=h_w t_w^3/12`

`I_f,V,c=t_f b_f^3/12`.

For the accepted singly symmetric geometry:

`I_VT=0`.

No fillet area or manufacturer correction is invented.

## Rational thin-wall shear-center model

Median-line dimensions:

`h_m=d-t_f`

`b_m=b_f-t_w/2`.

Median-line major-axis second moment:

`I_T,m=t_w h_m^3/12+2t_f b_m(h_m/2)^2`.

Magnitude of the shear-center offset from the web midline, toward the side opposite the Channel opening:

`e_w=t_f h_m^2 b_m^2/(4I_T,m)`.

Equivalent closed form:

`e_w=3t_f b_m^2/(t_w h_m+6t_f b_m)`.

Absolute shear-center coordinate:

`T_sc=t_w/2-e_w`.

Centroid-to-shear-center distance:

`e_Csc=T_c-T_sc`.

The rational method returns its median-line geometry, ratios, equation identity, and mandatory review flag.

It does not claim experimentally verified Channel torsional behavior.

## Explicit verified shear-center mode

If the caller supplies an explicit verified shear-center coordinate:

- use the exact supplied `T_sc`;
- require a nonempty deterministic source/provenance record;
- do not also execute the rational thin-wall formula as the controlling source;
- the rational value may be reported only as a noncontrolling comparison diagnostic if requested.

No unproven numeric override.

## RC1 action-reference convention

The user/member analysis actions are interpreted as:

- axial force `P_L` through the exact Channel centroid;
- major-axis free moment `M_T` about the centroidal major axis;
- major shear `V_V` acting through the selected shear-center coordinate.

This multi-reference interpretation is converted to one exact canonical wrench at the Channel centroid.

No user torsion is accepted in RC1.

## Generated torsion at the centroid

The equivalent torsional moment at the centroid due to major shear acting through the shear center is:

`M_L,C=(T_c-T_sc)V_V`.

Sign follows the controlled `L_CH/V_CH/T_CH` convention.

This generated torsion is mandatory and is not zeroed merely because the user did not enter torsion.

## Exact longitudinal stress field

Use:

`σ_L(V)=P_L/A+M_T V/I_T`.

Integrate over:

- top flange;
- web;
- bottom flange.

For region `i`:

`N_i=P_L A_i/A+M_T A_i V_i/I_T`.

Local major-axis moment about the region centroid:

`m_T,i=M_T I_i,T,c/I_T`.

Global major-axis contribution:

`M_T,i=V_iN_i+m_T,i`.

## Transverse eccentricity ledger

Every longitudinal region force acts at its actual transverse region centroid.

Relative transverse coordinates:

`ΔT_f=T_f-T_c`

`ΔT_w=T_w-T_c`.

Return each region's minor-axis moment contribution:

`M_V,i=ΔT_i N_i`.

Require exact:

`ΣM_V,i=0`

for the supported centroidal axial + major-axis bending action set.

Do not suppress individual nonzero contributions merely because they cancel globally.

These records are required for the later physical Stage 4.1B splice load path.

## Major shear and web torsion decomposition

For RC1:

- top-flange major shear = `0`;
- web major shear = `V_V`;
- bottom-flange major shear = `0`.

The web shear force acts at the web centroid `T_w`.

Its force-line contribution to centroidal torsion is:

`M_L,web-force=(T_c-T_w)V_V`.

The web component also receives a free torsional moment:

`m_L,web=(T_w-T_sc)V_V`.

Require exact:

`M_L,web-force+m_L,web=M_L,C`.

The free torsion is the retained Channel shear-center/web-plane effect.

It is not a torsional-resistance calculation.

## Optional shear-flow diagnostic

For rational thin-wall mode, return the resultant longitudinal flange shear-flow force associated with the shear-center derivation:

`H_f=V_V t_f h_m b_m^2/(4I_T,m)`.

Require:

`H_f h_m=m_L,web`.

This is a demand/provenance diagnostic only.

## Complete component wrenches

Return component wrenches at:

### Top flange

Reference:

`(L=0,V=V_top,T=T_f-T_c)`.

Components:

- longitudinal force `N_top`;
- local major-axis moment `m_T,top`;
- no assigned major shear;
- no assigned free torsion.

### Web

Reference:

`(0,0,T_w-T_c)`.

Components:

- longitudinal force `N_web`;
- major shear `V_V`;
- local major-axis moment `m_T,web`;
- free torsion `m_L,web`.

### Bottom flange

Reference:

`(0,V_bottom,T_f-T_c)`.

Components:

- longitudinal force `N_bottom`;
- local major-axis moment `m_T,bottom`;
- no assigned major shear;
- no assigned free torsion.

## Exact six-component equilibrium

At the Channel centroid, require exact recovery of:

- axial force `P_L`;
- major shear `V_V`;
- major-axis moment `M_T`;
- generated torsion `M_L,C`;
- zero minor-axis moment;
- zero minor shear.

No tolerance-based residual dumping.

## Flange-couple diagnostics

Retain Slice 5-style major-axis diagnostics:

`z_f=d-t_f`

`C_f=(N_top-N_bottom)/2`

`M_couple=C_f z_f`

`C_M_over_z=M_T/z_f`.

`C_M_over_z` remains reference-only.

The complete Channel component wrenches, transverse coordinates, and torsional records are controlling.

## Region stress extrema and states

Return exact signed longitudinal stress at:

- top flange inner and outer depth faces;
- web top and bottom edges;
- bottom flange inner and outer depth faces.

Return:

- region resultant state;
- region stress zero-crossing state.

Do not return connection strength.

## Mandatory review / disclaimer

Whenever Calculation Slice 6 executes:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

Backend disclaimer ID:

`CHANNEL_MOMENT_REFERENCE_AND_COMPONENT_RESULTANTS_DISCLAIMER_RC1`.

Controlled meaning:

The Channel centroid and solid-region section properties are calculated from the accepted sharp-corner profile geometry. Top-flange, web, and bottom-flange resultants are obtained by project-controlled linear-elastic region integration. Major shear is referenced to either a controlled explicit shear center or a project-controlled rational thin-wall shear-center estimate, and the resulting centroidal torsion and web free torsion are retained exactly. The rational shear-center model and component decomposition are not direct ASCE/SEI 74-23 connection-detail equations. The engineer of record shall review the profile idealization, shear-center source, structural-analysis reference convention, open-section torsion/warping implications, connection stiffness compatibility, and Section 2.3.2 qualification requirements for the final Channel moment splice.

## No strength / physical connection yet

Calculation Slice 6 shall not provide:

- Channel moment-splice geometry;
- flange/web splice plate forces;
- bolt-group distribution;
- torsional resistance;
- warping stress;
- connection stiffness;
- connection PASS/FAIL;
- moment-rotation classification.

Those belong to a later Stage 4.1B physical product order.

## Frozen-family boundary

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 / 4.1A freeze tags remain immutable.

Calculation Slice 5 and Stage 4.1A remain exact.

**END OF CALCULATION SLICE 6 CHANNEL MOMENT REFERENCE AND COMPONENT RESULTANTS DECISION**
