# FRP Master Connection — Calculation Slice 5 — W/I Major-Axis Moment-to-Component Resultants — Engineering Specification RC1

## 1. Status

**Controlled shared calculation authority — RC1**

Calculation Slice 5 is the first prerequisite for Stage 4.1A W/I Beam Moment Splice.

It converts a W/I member-end axial force, major shear, and major-axis bending moment into exact top-flange, web, and bottom-flange component wrenches using a controlled linear-elastic region integration.

It adds no normal product selector or frontend workspace.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `b0a6ecdf03c88768ff6ab29e584a992231812bda`;
- subject:
  `chore: freeze Stage 3.7 column-base shear family baseline`;
- commit count:
  `96`;
- clean worktree/index.

Stage 3.7 freeze hosted CI:

- GitHub Actions run #91;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `5m 8s`.

Expected Stage 3.7 freeze tag:

`stage-3.7-column-base-shear-family-freeze`

tag object:

`cbce5bc3e6ab61b550b3848982d6493a32a56bdb`

peeled target:

`b0a6ecdf03c88768ff6ab29e584a992231812bda`.

All earlier freeze tags remain immutable.

## 3. Source basis

Calculation Slice 5 shall be supported by a source/provenance record that confirms:

- Section 2.9 requires connection forces/deformations to be consistent with structural-analysis assumptions;
- Section 8.3.4.2 requires flexural splices to transfer all applicable forces/moments;
- compression flanges are treated as compression members;
- tension flanges are treated as tension members;
- shear-carrying parts transmit splice shear, bolt-group eccentricity effects, and their proportion of moment;
- moment-resistant connections are not prescriptively covered and require Section 2.3.2 qualification/review.

The actual regional elastic integration is a controlled rational engineering method.

## 4. Method and contract

Method identity:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`.

Internal calculation contract:

`CS5-RC1`.

Unknown future versions fail closed.

No public product API route is required in this slice.

## 5. Supported actions

Input member-end actions in local W/I frame:

- axial force `P_L`;
- major shear `V_V`;
- major-axis bending moment `M_T`.

Require exactly zero:

- minor shear `V_T`;
- minor-axis bending moment `M_V`;
- torsion `M_L`.

Those unsupported components shall be rejected or excluded from the strict contract rather than silently discarded.

## 6. Beam frame

Right-handed:

`L_B × V_B = T_B`.

- `L_B`: beam longitudinal;
- `V_B`: depth axis, positive toward top flange;
- `T_B`: major-moment axis.

Positive `P_L` = longitudinal tension.

Positive `M_T` = tension at positive `V_B`.

## 7. W/I geometry inputs

Strictly accept:

- depth `d`;
- flange width `b_f`;
- web thickness `t_w`;
- flange thickness `t_f`.

Require:

- all finite and positive;
- `d > 2 t_f`;
- `b_f > t_w`;
- resulting web height positive;
- symmetric top/bottom flanges;
- no extra Channel/asymmetric-section fields.

Use existing W/I dimension and quantity types where possible.

## 8. Current geometry idealization

RC1 uses the accepted sharp-corner rectangular W/I idealization.

No fillet area is introduced.

No manufacturer-specific region correction.

If the existing backend W/I profile geometry provides exact region primitives/properties, reuse those authoritative values so the calculation and visualization share one geometry definition.

Do not maintain two contradictory W/I geometry formulas.

## 9. Derived geometry

`h_w = d - 2 t_f`

`A_f = b_f t_f`

`A_w = t_w h_w`

`A = 2 A_f + A_w`

`y_t = +(d - t_f)/2`

`y_w = 0`

`y_b = -(d - t_f)/2`

`I_f,c = b_f t_f^3/12`

`I_w,c = t_w h_w^3/12`

`I_T = 2(I_f,c + A_f y_t^2) + I_w,c`.

All values are exact Decimal quantities.

## 10. Longitudinal elastic stress field

At any section coordinate `y`:

`σ_L(y) = P_L/A + M_T y/I_T`.

No material modulus appears because the section is homogeneous in the longitudinal direction under the accepted W/I idealization.

Do not apply nonlinear redistribution, plasticity, or tension-only behavior.

## 11. Region longitudinal force

For each region `i`:

`N_i = P_L A_i/A + M_T A_i y_i/I_T`.

Return signed result.

Positive = tension.

Negative = compression.

## 12. Region local moment

For each region `i`:

`m_i = M_T I_i,c/I_T`.

This is the residual moment about the region centroid caused by the longitudinal stress gradient within that physical region.

It must not be dropped.

## 13. Region global moment contribution

At the member centroid:

`M_i = y_i N_i + m_i`.

Return both:

- local component wrench at region centroid;
- global-equilibrium contribution.

## 14. Major shear allocation

RC1 assigns:

- top flange: `V_V,top = 0`;
- web: `V_V,web = V_V`;
- bottom flange: `V_V,bottom = 0`.

This is a controlled component allocation for the Stage 4.1A major-axis moment-splice program.

No minor shear/torsion allocation.

## 15. Component reference points

At the member-end section:

- top flange component reference:
  `(L=0, V=y_t, T=0)`;
- web component reference:
  `(0,0,0)`;
- bottom flange component reference:
  `(0,y_b,0)`.

The complete component wrench at each reference contains:

- longitudinal force;
- major shear where assigned;
- local moment about `T_B`.

## 16. Exact equilibrium proof

Return deterministic equilibrium trace.

Require exact:

`ΣN_i = P_L`

`ΣV_i = V_V`

`Σ(y_i N_i + m_i) = M_T`.

Also require zero generated unsupported components.

No tolerances.

## 17. Region stress extrema

Return signed longitudinal stress at each physical region boundary.

### Top flange
- inner face `y = d/2 - t_f`;
- outer face `y = d/2`.

### Web
- bottom web edge `y = -h_w/2`;
- top web edge `y = +h_w/2`.

### Bottom flange
- outer face `y = -d/2`;
- inner face `y = -d/2 + t_f`.

These values support later tension/compression classification and local connection checks.

## 18. Region force state

For each region longitudinal resultant:

- `TENSION` if `N_i > 0`;
- `COMPRESSION` if `N_i < 0`;
- `ZERO_FORCE` if `N_i == 0`.

Also return whether the region stress range crosses zero.

A region resultant classification does not replace stress-extrema reporting.

## 19. Equivalent flange couple diagnostics

Flange force-line lever arm:

`z_f = y_t - y_b = d - t_f`.

Exact antisymmetric flange-couple force:

`C_f = (N_top - N_bottom)/2`.

Exact flange-couple moment:

`M_couple = C_f z_f`.

Full-moment reference couple:

`C_M_over_z = M_T/z_f`.

Residual:

`M_residual = M_T - M_couple`.

Require exact proof:

`M_residual = m_top + M_web + m_bottom`

where `M_web = y_w N_web + m_web = m_web`.

The `M/z` reference is presentation/communication only.

The controlling design handoff is the complete component-wrench set.

## 20. Axial/moment superposition

For symmetric W/I:

- top and bottom uniform axial shares are equal;
- web uniform axial share follows area;
- bending adds equal/opposite antisymmetric flange force components;
- web receives its exact bending-induced local moment;
- top/bottom flanges retain their local moments.

No force is counted twice.

## 21. Zero and sign behavior

Require exact:

- all-zero actions -> all-zero resultants;
- pure axial -> region forces proportional to area, zero local moments;
- pure moment -> zero net axial force and opposite flange resultants;
- moment sign reversal -> every bending-induced force/moment/stress reverses;
- axial sign reversal -> uniform axial shares reverse;
- shear sign reversal -> web shear reverses only.

## 22. Method review flag

Whenever Calculation Slice 5 executes:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED = true`.

This flag does not mean the arithmetic is optional; it records the non-prescriptive component-distribution model.

## 23. Disclaimer metadata

Backend-controlled ID:

`WI_MOMENT_COMPONENT_RESULTANT_DECOMPOSITION_DISCLAIMER_RC1`.

Controlled meaning:

The top-flange, web, and bottom-flange forces and local moments are derived from a project-controlled linear-elastic integration of the accepted idealized W/I section. The decomposition preserves exact member-end axial-force, shear, and major-moment equilibrium, including web moment participation, but is not a direct ASCE/SEI 74-23 connection-detail equation. The engineer of record shall review the section idealization, structural-analysis assumptions, component stiffness compatibility, and Section 2.3.2 qualification requirements for the final moment connection.

No frontend paraphrase may replace the backend engineering meaning.

## 24. No connection strength result

Calculation Slice 5 returns demand only.

It shall not return:

- connection PASS/FAIL;
- flange splice capacity;
- web splice capacity;
- bolt demand distribution;
- prying;
- connection stiffness;
- moment-rotation classification.

## 25. Default benchmark geometry

Use:

- `d = 10 in`;
- `b_f = 8 in`;
- `t_w = 0.5 in`;
- `t_f = 0.5 in`.

Expected:

- `h_w = 9 in`;
- `A_f = 4 in²`;
- `A_w = 4.5 in²`;
- `A = 12.5 in²`;
- `y_t = +4.75 in`;
- `y_b = -4.75 in`;
- `I_f,c = 0.0833333333333333333333333333333333333333333333333333333333333 in⁴`;
- `I_w,c = 30.375 in⁴`;
- `I_T = 211.041666666666666666666666666666666666666666666666666666667 in⁴`;
- `z_f = 9.5 in`.

## 26. Default benchmark actions

Use:

- `P_L = +20 kip`;
- `V_V = -10 kip`;
- `M_T = +100 kip-in`.

Expected component resultants are supplied in the golden fixture.

## 27. Required controlled golden cases

At minimum:

G1. Geometry web height.
G2. Region areas.
G3. Region centroids.
G4. Region centroidal inertias.
G5. Total major-axis inertia.
G6. Pure axial area distribution.
G7. Pure axial zero moments.
G8. Pure moment top-flange force.
G9. Pure moment web force zero.
G10. Pure moment bottom-flange force.
G11. Pure moment top local moment.
G12. Pure moment web local moment.
G13. Pure moment bottom local moment.
G14. Pure moment exact axial equilibrium.
G15. Pure moment exact moment equilibrium.
G16. Default top-flange force.
G17. Default web force.
G18. Default bottom-flange force.
G19. Default top local moment.
G20. Default web local moment.
G21. Default bottom local moment.
G22. Default major-shear allocation.
G23. Default axial equilibrium.
G24. Default shear equilibrium.
G25. Default moment equilibrium.
G26. Flange lever arm.
G27. Exact flange-couple force.
G28. Exact flange-couple moment.
G29. Full-moment `M/z` reference force.
G30. Residual moment.
G31. Residual identity proof.
G32. Top stress extrema.
G33. Web stress extrema.
G34. Bottom stress extrema.
G35. Region force-state classification.
G36. Stress zero-crossing classification.
G37. All-zero action.
G38. Axial sign reversal.
G39. Moment sign reversal.
G40. Shear sign reversal.
G41. Unsupported minor shear rejected.
G42. Unsupported minor moment rejected.
G43. Unsupported torsion rejected.
G44. Invalid depth/flange geometry rejected.
G45. Invalid flange-width/web-thickness geometry rejected.
G46. U.S./SI equivalence.
G47. Deterministic fingerprints.
G48. Disclaimer/review metadata.
G49. Stage 3.7 freeze regression.
G50. Stage 3.6 freeze regression.
G51. Stage 3.5 and earlier freeze regressions.
G52. No frontend production change.

## 28. U.S./SI equivalence

Equivalent physical inputs shall preserve:

- section geometry/properties;
- stress field;
- component resultants;
- couple diagnostics;
- equilibrium;
- classifications;
- fingerprints.

No unit-specific engineering branch.

## 29. Fingerprints

Deterministic fingerprints include:

- method/contract;
- W/I geometry;
- section properties;
- input actions;
- component reference points;
- component wrenches;
- stress extrema;
- couple diagnostics;
- equilibrium proof;
- review/disclaimer IDs;
- source/provenance.

Presentation excluded.

## 30. Production architecture

Expected backend-only production changes.

Frontend production changes:

`0`.

No selector/workspace/scene change.

If frontend production becomes necessary:

**STOP and explain.**

## 31. Historical/frozen invariance

Require exact:

- Stage 3.7 frozen family;
- Stage 3.6 frozen family;
- Stage 3.5 frozen family;
- Stage 3.4/3.3/3.2/2.3 freezes;
- all current shear-product fingerprints.

Calculation Slice 5 is not wired into historical shear contracts.

## 32. Acceptance boundary

Calculation Slice 5 is accepted only if:

- exact W/I geometry is reused/consistent;
- linear stress integration is exact;
- web moment participation is retained;
- local region moments are retained;
- component/global equilibrium is exact;
- `M/z` is reference-only;
- unsupported actions fail closed;
- disclaimer/review metadata is deterministic;
- full local/object-isolated QA passes;
- hosted CI 4/4 passes;
- all frozen families remain exact.

**END OF CALCULATION SLICE 5 W/I MOMENT COMPONENT RESULTANTS ENGINEERING SPECIFICATION RC1**
