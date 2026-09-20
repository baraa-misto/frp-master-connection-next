# FRP Master Connection — Calculation Slice 5 — W/I Major-Axis Moment-to-Component Resultants — Authority Ledger RC1

## Authority purpose

Calculation Slice 5 supplies the shared demand-decomposition authority required before Stage 4.1A can design a W/I beam major-axis moment splice.

It returns exact top-flange, web, and bottom-flange component wrenches.

It is not a connection-capacity engine.

## Source-derived boundary

ASCE/SEI 74-23 requires:

- connection demand to be consistent with structural analysis;
- flexural splices to transfer all applicable forces and moments;
- tension and compression flanges to be treated according to their force state;
- shear-carrying parts to transfer splice shear, bolt-group eccentricity effects, and the proportion of moment carried by the part.

ASCE/SEI 74-23 does not prescribe the exact top-flange/web/bottom-flange elastic integration implemented here and does not prescriptively cover moment-resistant FRP connections.

## Rational method authority

Controlled method:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`.

The method assumes the accepted idealized symmetric W/I section remains linear elastic and plane sections remain plane.

Longitudinal stress:

`σ_L(y)=P_L/A + M_T y/I_T`.

The field is integrated exactly over the physical top flange, web, and bottom flange.

## Region-resultant authority

For region `i`:

`N_i=P_L A_i/A + M_T A_i y_i/I_T`.

`m_i=M_T I_i,c/I_T`.

`M_i=y_i N_i+m_i`.

The complete component wrench is reported at the physical region centroid.

No region-local moment is discarded.

## Shear-allocation authority

For Calculation Slice 5 RC1:

- web receives 100% of major shear;
- top and bottom flanges receive zero major shear;
- unsupported minor shear/torsion are rejected.

This allocation is specific to the first W/I major-axis moment-connection program.

## Couple authority

The dominant flange couple is exposed as:

`C_f=(N_top-N_bottom)/2`.

Lever arm:

`z_f=d-t_f`.

Flange-couple moment:

`M_couple=C_f z_f`.

The familiar full-moment reference:

`C_M_over_z=M_T/z_f`

is diagnostic only.

The complete component wrenches remain controlling because the web and local flange stress gradients carry the residual moment.

## Equilibrium authority

Require exact:

- `ΣN=P_L`;
- `ΣV=V_V`;
- `Σ(y_iN_i+m_i)=M_T`.

No tolerance suppression or residual dumping.

## Axial-force authority

Uniform axial force is distributed by actual region area and superimposed with bending-induced resultants.

This allows combined axial force and moment to place either flange in tension or compression.

## Review / qualification boundary

Whenever the method executes:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

Mandatory disclaimer ID:

`WI_MOMENT_COMPONENT_RESULTANT_DECOMPOSITION_DISCLAIMER_RC1`.

Calculation Slice 5 does not establish:

- moment-connection strength;
- stiffness or moment-rotation classification;
- full-strength/partial-strength classification;
- rotation capacity;
- Section 2.3.2 qualification.

## Stage 4.1A handoff

Stage 4.1A shall consume:

- top-flange component wrench;
- web component wrench;
- bottom-flange component wrench;
- exact reference points;
- stress extrema;
- flange-couple diagnostics;
- equilibrium proof;
- provenance/fingerprints.

Stage 4.1A shall not recompute or simplify these resultants in frontend or connection orchestration.

## Frozen-family boundary

Stage 3.7 and all earlier freeze tags/fingerprints remain immutable.

No existing shear product is wired to Calculation Slice 5.

**END OF CALCULATION SLICE 5 W/I MOMENT COMPONENT RESULTANTS AUTHORITY LEDGER RC1**
