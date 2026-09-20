# FRP Master Connection — Calculation Slice 5 — W/I Major-Axis Moment-to-Component Resultants — Decision

## Decision

Stage 4.1A shall begin with one shared prerequisite:

**Calculation Slice 5 — W/I Major-Axis Member-End Wrench to Top-Flange / Web / Bottom-Flange Component Resultants**

This is a reusable backend calculation authority for the Moment Connections program.

It is not yet the physical beam-splice product and adds no selector or normal frontend workspace.

After Calculation Slice 5 is accepted, Stage 4.1A will use its exact component wrenches to design the physical top-flange, web, and bottom-flange splice systems.

## Why a shared calculation slice is required

A major-axis beam moment is physically transferred by a dominant tension-compression flange couple, but the web and the local stress gradients within the flange regions also carry a proportion of the member moment.

ASCE/SEI 74-23 Section 8.3.4.2 requires flexural splices to transmit all applicable forces and moments, treats compression and tension flanges according to their force state, and requires the shear-carrying part to transmit shear, bolt-group eccentricity effects, and the proportion of moment carried by that part.

Therefore Calculation Slice 5 shall not replace the entire member moment with an unqualified `M/z` flange couple.

It shall:

1. calculate the exact linear-elastic longitudinal stress field over the accepted idealized W/I section;
2. integrate that field over the top flange, web, and bottom flange;
3. return a complete force plus local-moment wrench for each physical region;
4. expose the dominant flange-couple force and effective lever arm as a derived diagnostic;
5. retain the exact residual web and local-region moment so global force and moment equilibrium are exact.

## Method classification

Controlled method:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`.

This is a project-controlled rational engineering method based on linear elastic section mechanics.

It is not presented as a standalone ASCE-prescribed component-distribution equation.

The method is consistent with the source requirement that connection forces/deformations match structural-analysis assumptions and that web moment participation and eccentricities be retained.

## RC1 section scope

RC1 supports only:

- geometrically symmetric W/I sections;
- the existing sharp-corner W/I geometry model;
- axial force along beam longitudinal axis;
- major shear in the web plane;
- major-axis bending moment;
- zero minor shear;
- zero minor-axis bending moment;
- zero torsion.

No Channel section is included.

No moment-connection geometry or resistance is included.

## Local frame and signs

Use a right-handed beam frame:

- `L_B`: beam longitudinal axis;
- `V_B`: beam depth/vertical axis, positive toward the top flange;
- `T_B`: transverse axis such that `L_B × V_B = T_B`.

Member-end actions:

- `P_L` positive in longitudinal tension;
- `V_V` signed major shear along `V_B`;
- `M_T` signed major-axis moment about `T_B`.

Positive `M_T` produces longitudinal tension at positive `V_B` and compression at negative `V_B`.

## Idealized W/I geometry

For:

- depth `d`;
- flange width `b_f`;
- web thickness `t_w`;
- flange thickness `t_f`;

define:

`h_w = d - 2 t_f`

`A_f = b_f t_f`

`A_w = t_w h_w`

`A = 2 A_f + A_w`

Top-flange centroid:

`y_t = +(d - t_f)/2`

Web centroid:

`y_w = 0`

Bottom-flange centroid:

`y_b = -(d - t_f)/2`

Region centroidal second moments about `T_B`:

`I_f,c = b_f t_f^3 / 12`

`I_w,c = t_w h_w^3 / 12`

Total:

`I_T = 2 (I_f,c + A_f y_t^2) + I_w,c`.

Use exact Decimal arithmetic.

## Elastic stress field

Longitudinal normal stress:

`σ_L(y) = P_L/A + M_T y/I_T`.

The stress field is integrated exactly over each rectangular physical region.

## Region component resultants

For region `i` with area `A_i`, centroid coordinate `y_i`, and centroidal second moment `I_i,c`:

Longitudinal force:

`N_i = P_L A_i/A + M_T A_i y_i/I_T`.

Local residual moment about the region centroid:

`m_i = M_T I_i,c/I_T`.

Global moment contribution about the member centroid:

`M_i = y_i N_i + m_i`.

The returned component wrench is defined at the region centroid and contains:

- longitudinal force `N_i`;
- local moment `m_i` about `T_B`;
- major shear only where authorized below.

## Major shear allocation

For RC1:

- top-flange major shear = `0`;
- web major shear = `V_V`;
- bottom-flange major shear = `0`.

This represents the web as the physical shear-carrying component while preserving its calculated axial and moment participation.

No flange shear distribution equation is introduced.

## Exact equilibrium

Require exact:

`N_top + N_web + N_bottom = P_L`

and:

`(y_top N_top + m_top) + (y_web N_web + m_web) + (y_bottom N_bottom + m_bottom) = M_T`.

Also:

`V_top + V_web + V_bottom = V_V`.

No tolerance-based zeroing.

## Flange-couple diagnostic

Define the flange force-line lever arm:

`z_f = y_top - y_bottom = d - t_f`.

Define the antisymmetric flange-couple force:

`C_f = (N_top - N_bottom)/2`.

The flange force-couple moment is:

`M_couple = C_f z_f`.

Also expose the familiar full-moment reference couple:

`C_M_over_z = M_T/z_f`.

`C_M_over_z` is the force that would be required if the entire member moment were assigned only to the two flange force lines. It is a comparison/communication value, not the controlling component demand.

The exact residual moment is:

`M_residual = M_T - M_couple`.

The residual equals the sum of the top-flange local moment, web moment contribution, and bottom-flange local moment.

The exact component resultants shall therefore show how the simple `M/z` concept is modified by web participation and local flange stress gradients.

Neither couple diagnostic is a substitute for the complete component wrenches.

Stage 4.1A shall design from the complete component wrenches.

## Axial-force participation

Uniform axial force is distributed according to region area:

- top flange axial share = `P_L A_f/A`;
- web axial share = `P_L A_w/A`;
- bottom flange axial share = `P_L A_f/A`.

The bending-induced antisymmetric flange forces superimpose on those axial shares.

This allows either flange to be in tension or compression depending on combined `P_L` and `M_T`.

## Component state classification

For each region return:

- `TENSION` if `N_i > 0`;
- `COMPRESSION` if `N_i < 0`;
- `ZERO_FORCE` if exactly zero.

Also retain signed stress extrema for later physical connection design.

Do not infer connection PASS/FAIL in this slice.

## Required disclaimer metadata

Whenever this method is used, backend results shall carry:

`WI_MOMENT_COMPONENT_RESULTANT_DECOMPOSITION_DISCLAIMER_RC1`.

Required meaning:

The top-flange, web, and bottom-flange forces and local moments are derived from a project-controlled linear-elastic integration of the accepted idealized W/I section. The decomposition is a rational engineering method used to preserve exact member-end force and moment equilibrium, including web moment participation; it is not a direct ASCE/SEI 74-23 connection-detail equation. The engineer of record shall review the section idealization, structural-analysis assumptions, component stiffness compatibility, and Section 2.3.2 qualification requirements for the final moment connection.

If report generation is not available, preserve deterministic disclaimer metadata for future reporting.

## Moment-connection qualification boundary

Calculation Slice 5 does not establish:

- moment-connection strength;
- rotational stiffness;
- rigid/semi-rigid classification;
- full-strength/partial-strength classification;
- rotation capacity;
- Section 2.3.2 qualification.

Those remain future Stage 4.1A product/reporting responsibilities.

## Frozen-family boundary

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 freeze tags remain immutable.

No existing shear product behavior or fingerprint changes.

**END OF CALCULATION SLICE 5 W/I MOMENT COMPONENT RESULTANTS DECISION**
