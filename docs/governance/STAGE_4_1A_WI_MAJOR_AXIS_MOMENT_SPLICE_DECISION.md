# FRP Master Connection — Stage 4.1A W/I Major-Axis Moment Splice — Decision

## Decision

Proceed with **Stage 4.1A — W/I Beam Major-Axis Moment Splice** as the first physical Moment Connections product.

The connection uses:

- two identical, collinear pultruded FRP W/I beams;
- a positive physical beam-end gap;
- the frozen Stage 3.6-style symmetric double web-splice system;
- one **outer full-width FRP flange splice plate** on each beam flange;
- two **split inner FRP flange splice plates** on each beam flange, one on each side of the web;
- common through-bolts through each outer plate / beam flange / corresponding inner plate stack.

The top and bottom flange splice geometry is identical in RC1.

No Channel beam is included.

## Accepted prerequisite

Calculation Slice 5 is accepted and controlling:

Commit:

`23813a5c2d015b74591e577fa95715950c34912c`

Subject:

`feat: add W/I moment component resultant engine`

Hosted CI:

GitHub Actions run #92, 4/4 green.

Method:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`.

Stage 4.1A shall consume the complete top-flange, web, and bottom-flange component wrenches from Slice 5.

It shall not replace those complete wrenches with a sole `M/z` force.

## RC1 actions

Normal user actions at the splice joint reference:

- signed axial force `P_L`;
- signed major shear `V_V`;
- signed major-axis bending moment `M_T`.

Require zero / reject:

- minor shear;
- minor-axis moment;
- torsion.

The user-applied moment is now an authorized action.

## Canonical joint action

Joint reference:

`r_J=(0,0,0)`.

The canonical transfer wrench is decomposed once by Calculation Slice 5.

Beam A and Beam B physical interface actions are equal and opposite, but the canonical Slice 5 material stress-state classification is not sign-reversed merely because the two physical cut-face tractions are opposite.

This distinction is mandatory.

## Web system

Reuse Stage 3.6 physical web-splice topology and accepted resistance architecture without changing the frozen Stage 3.6 contract.

For Stage 4.1A only, the web subsystem receives the authoritative Slice 5 web component wrench:

- web longitudinal force;
- 100% major shear;
- web local major-axis moment.

The Stage 3.6 rational splice-plate body method and accepted common-bolt double-shear logic are reused as applicable.

Stage 3.6 frozen requests/results/fingerprints remain unchanged.

## Balanced flange topology

For each top/bottom flange:

- one continuous outer full-width plate spans the joint;
- two identical continuous inner strips span the joint, one on each side of the web;
- inner strips are symmetric about the web;
- each common bolt passes:
  `OUTER_FLANGE_SPLICE_PLATE -> BEAM_FLANGE -> CORRESPONDING_INNER_FLANGE_SPLICE_PLATE`.

The outer plate alone is not an RC1 topology.

Missing either inner strip is invalid.

## Flange force-line decomposition

The accepted Slice 5 flange wrench at the flange-region centroid is:

- signed longitudinal force `N_f`;
- signed local major-axis moment `m_f`.

Let:

- `y_f` = beam flange-region centroid;
- `y_o` = outer splice-plate centroid;
- `y_i` = combined inner splice-plate centroid in the through-flange direction;
- `e_o=y_o-y_f`;
- `e_i=y_i-y_f`.

Solve exactly:

`F_o + F_i = N_f`

`e_o F_o + e_i F_i = m_f`.

Therefore:

`F_o = (m_f - e_i N_f)/(e_o-e_i)`

`F_i = (e_o N_f - m_f)/(e_o-e_i)`.

`F_i` is then split exactly 50/50 between the two symmetric inner strips because RC1 has:

- symmetric W/I geometry;
- symmetric left/right inner-strip geometry;
- zero minor-axis moment;
- zero torsion;
- zero minor shear.

This left/right 50/50 split is not authority for future biaxial/torsional splices.

## Flange branch method identity

Controlled method:

`RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1`.

The decomposition is exact force/moment equilibrium about the authoritative flange reference using the actual outer/inner plate force-line locations.

It is a project-controlled rational connection model, not an ASCE-prescribed moment-splice equation.

## Beam-flange local transfer

The common bolts introduce two physical in-plane shear-transfer faces:

- outer plate / beam flange;
- beam flange / inner plate.

To avoid losing the Slice 5 local flange moment when the two plane demands are unequal or opposite, Stage 4.1A uses a conservative rational face-sublayer model:

`RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1`.

For local Chapter 8-style FRP connection checks only:

- outer-face beam-flange sublayer thickness = `t_f/2`;
- inner-face beam-flange sublayer thickness = `t_f/2`;
- outer sublayer receives `F_o`;
- inner sublayer receives `F_i`;
- both use the actual full flange width, material basis, hole grid, and loaded-edge direction;
- no perpendicular-web exemption is silently used to reduce the rational sublayer checks.

This does not physically split the beam flange into two members.

It is a conservative local connection-verification device requiring engineering review.

## Common flange-bolt shear

The two physical flange-bolt shear planes are not assumed to carry equal force.

Controlled method:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

For each physical bolt:

- outer-plane demand comes from the outer-plate branch;
- inner-plane demand comes from the corresponding inner-strip branch;
- each plane is checked independently against the accepted per-plane bolt shear strength;
- governing bolt utilization is the maximum plane utilization.

Do not use a blind `2 × single-plane capacity` division unless the actual plane demands are equal.

No bolt-axis tension is generated by the RC1 idealized in-plane load path.

## Flange splice-plate body

Each flange splice-plate branch carries longitudinal force only in RC1.

For the clear body between the two beam-side bolt groups:

- tension branch: reuse Calculation Slice 4 longitudinal tension;
- compression branch: reuse Calculation Slice 4 longitudinal compression, including the accepted orthotropic-buckling method;
- clear-body panel mapping uses the inherited rational simply-supported clear-body boundary model.

Outer full-width plate and each inner strip are checked separately.

## Local FRP connection checks

Reuse accepted Chapter 8 / existing local engines where applicable for:

- pin bearing;
- net tension;
- shear-out;
- cleavage;
- block-shear / accepted local failure-path logic.

Apply them independently to:

- outer flange splice plate;
- each inner flange splice plate;
- rational outer beam-flange face sublayer;
- rational inner beam-flange face sublayer;
- inherited web components.

Do not invent a strength merely to eliminate `NOT_EVALUATED`.

## Physical gap

Require:

`beam_end_gap > 0`.

No direct beam-end bearing or flange-end bearing transfer is credited.

Compression and moment transfer remain through the splice systems.

## Bolt tension / pull-through / prying

For the RC1 idealized load set and balanced in-plane topology:

- applied bolt-axis action = zero;
- no bolt tension capacity is invoked;
- pull-through/prying is not generated by the authoritative in-plane demand model.

However, actual out-of-plane deformation, unequal-plane contact, secondary bolt bending, and moment-rotation behavior remain part of the mandatory engineering-review / Section 2.3.2 qualification boundary.

No unqualified claim is made that these deformation effects are experimentally closed.

## Overall result

A supported failure governs:

`FAIL`.

A required unavailable source/method governs:

`NOT_EVALUATED`.

If all required numerical component-strength checks pass, the highest allowed success state is:

`PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Never ordinary unqualified `PASS`.

## Mandatory qualification / stiffness boundary

Always retain:

`WI_MOMENT_SPLICE_CONNECTION_QUALIFICATION = REQUIRED_2_3_2`

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED = true`

`MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION = NOT_EVALUATED`

`MOMENT_ROTATION_CAPACITY = NOT_EVALUATED`

`FULL_STRENGTH_CLASSIFICATION = NOT_EVALUATED`

Stage 4.1A calculates connection component strength, not experimental stiffness or moment-rotation qualification.

## Mandatory disclaimer

Backend ID:

`WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1`.

Controlled meaning:

The Stage 4.1A W/I moment splice uses project-controlled rational methods to decompose the member-end wrench into W/I region resultants, resolve each flange-region wrench into outer and inner cover-plate force lines, verify local beam-flange transfer with a conservative face-sublayer model, and check unequal physical bolt shear-plane demands. Code-based local and pure-mode FRP strengths are used where applicable, and the inherited web-splice rational body method is retained. ASCE/SEI 74-23 does not prescriptively qualify moment-resistant FRP beam splices. The engineer of record shall review the load-path assumptions, relative stiffness/deformation compatibility, actual bolt/contact behavior, plate restraint/buckling conditions, and Section 2.3.2 qualification. Connection rotational stiffness, rotation capacity, and full-strength classification are not established by this calculation.

## Frozen-family boundary

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 freeze tags remain immutable.

No historical shear connection is modified.

## Future scope

Not Stage 4.1A RC1:

- Channel moment splice;
- minor-axis moment;
- torsion;
- minor shear;
- outer-only flange splice;
- unequal W/I beams;
- unequal top/bottom flange splice geometry;
- connection stiffness / moment-rotation design.

**END OF STAGE 4.1A W/I MAJOR-AXIS MOMENT SPLICE DECISION**
