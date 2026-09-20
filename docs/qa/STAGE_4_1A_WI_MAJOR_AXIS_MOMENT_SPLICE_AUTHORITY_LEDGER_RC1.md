# FRP Master Connection — Stage 4.1A W/I Major-Axis Moment Splice — Authority Ledger RC1

## Purpose

Stage 4.1A creates the first physical Moment Connections product:

`WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE`.

It designs a W/I beam splice for signed axial force, major shear, and major-axis moment using:

- accepted Calculation Slice 5 component resultants;
- balanced outer + split-inner flange cover plates;
- inherited Stage 3.6 web splice mechanics;
- accepted local FRP connection strengths;
- accepted Chapter 7 plate strengths;
- controlled rational methods where ASCE/SEI 74-23 does not prescribe the complete moment-connection load path.

## Source authority

ASCE/SEI 74-23 provides the following controlling boundaries:

- Section 2.9: connected members, connecting elements, and fasteners are proportioned for structural-analysis demands; forces/deformations must match intended connection behavior; eccentricity effects are analyzed by mechanics.
- Section 8.1 / 8.1.2: Chapter 8 covers bolted connection component design and requires eccentricities to be retained.
- Section 8.2: bolt, hole, washer, and geometry requirements.
- Section 8.3: strength is based on basic connection components and critical failure paths.
- Section 8.3.2: bolt shear/tension and local FRP bolted-connection limit states.
- Section 8.3.4.2: flexural splices transmit applicable force/moment; compression/tension flanges are treated by force state; shear-carrying parts retain shear, bolt-group eccentricity effects, and their moment proportion.
- Commentary C8.1.3: moment-resistant FRP framing connections are excluded from ordinary prescriptive coverage because available knowledge/test data are insufficient; Section 2.3.2 qualification is required.

The standard does not prescribe the complete Stage 4.1A balanced flange load distribution, rational beam-flange face-sublayer transfer, or unequal-plane common-bolt model.

## Accepted prerequisite authority

Calculation Slice 5:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`

is accepted at:

`23813a5c2d015b74591e577fa95715950c34912c`.

Stage 4.1A consumes its complete:

- top-flange wrench;
- web wrench;
- bottom-flange wrench;
- stress extrema;
- exact equilibrium;
- diagnostics/provenance.

`M/z` remains reference-only.

## Inherited web authority

Stage 3.6 remains frozen.

Stage 4.1A reuses, through a successor-specific adapter:

- symmetric web Plate/Web/Plate topology;
- Stage 2.5A bolt-group demand;
- local FRP connection checks;
- Calculation Slice 4;
- `RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`;
- `RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`;
- physical web-bolt two-plane shear checks;
- source-pending fastener behavior.

The new Stage 4.1A web demand includes the accepted Slice 5 web free moment.

No Stage 3.6 historical contract/fingerprint changes.

## Flange topology authority

Each top/bottom flange uses exactly:

- one continuous outer full-width FRP cover plate;
- two continuous split inner FRP cover plates;
- two symmetric bolt lines across the flange;
- one line centered on each inner strip;
- common through-bolts:
  `Outer Plate -> Beam Flange -> Corresponding Inner Plate`.

The outer-only single-lap topology is not Stage 4.1A RC1.

## Rational flange branch authority

Method:

`RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1`.

The Slice 5 flange wrench at the flange-region centroid is represented by two longitudinal force resultants at the actual outer and inner cover-plate centroidal force lines.

For:

- flange force `N_f`;
- local flange moment `m_f`;
- force-line offsets `e_o`, `e_i`;

solve:

`F_o+F_i=N_f`

`e_oF_o+e_iF_i=m_f`.

This is exact statics for the selected two-force-line idealization.

The two inner strips receive `F_i/2` only after exact transverse geometry/action symmetry is proven.

## Rational beam-flange local transfer authority

Method:

`RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1`.

The connected beam flange is not physically separated.

For local bolt-hole failure-path verification only, it is conservatively represented by:

- an outer-face sublayer, `t_f/2`, carrying `F_o`;
- an inner-face sublayer, `t_f/2`, carrying `F_i`.

Both use:

- the full actual flange width;
- actual material axes;
- actual full two-line bolt grid;
- signed loaded-edge direction.

The rational sublayer checks do not invoke a perpendicular-web exemption to reduce local resistance.

Purpose:

preserve and locally verify the through-flange force/moment transfer even when outer and inner interface forces are unequal or opposite.

This method requires engineering review.

## Rational flange bolt authority

Method:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

Each common flange bolt has two physical shear planes:

1. outer plate / beam flange;
2. beam flange / inner plate.

Actual plane demand comes from the corresponding Stage 2.5A branch group.

Each physical shear plane is checked independently against the accepted per-plane steel/stainless bolt shear strength when source authority exists.

Bolt utilization:

`max(U_outer,U_inner)`.

No equal-plane assumption.

No blind `2 × capacity` aggregation.

The method retains engineering-review metadata for unequal-plane bearing/contact and secondary bolt-bending behavior not experimentally qualified by the strength model.

## Flange splice plate body authority

Flange cover-plate branches are longitudinal-force-only in RC1.

For each clear unperforated body:

### Tension
Reuse Calculation Slice 4 longitudinal tension.

### Compression
Reuse Calculation Slice 4 longitudinal compression including accepted orthotropic buckling.

Panel mapping:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

Outer plate and each inner strip are separate physical components.

## Local FRP connection authority

Reuse accepted local bolted FRP engines where applicable for:

- pin bearing;
- net tension;
- shear-out;
- cleavage;
- block shear / accepted local path.

Apply independently to:

- outer cover plates;
- each inner cover plate;
- rational outer beam-flange face sublayer;
- rational inner beam-flange face sublayer;
- inherited web components.

No new local resistance formula is invented.

## Bolt-axis / prying boundary

RC1 supported global actions produce zero authoritative bolt-axis force.

Therefore:

- bolt tension demand = zero;
- pull-through from applied bolt-axis force = not required;
- Eq. 8-3 combined tension/shear is not invoked when tension demand is zero.

Actual out-of-plane deformation, prying, unequal-plane contact, and secondary bolt bending remain mandatory review/qualification subjects.

No numerical prying force is invented.

## Exact equilibrium authority

Stage 4.1A must prove, exactly:

1. Slice 5 top + web + bottom wrenches recover the user `P/V/M`;
2. each flange outer + inner branch recovers its Slice 5 flange force and local moment;
3. the two inner strips recover the inner total branch;
4. Beam A interface actions recover the canonical joint wrench;
5. Beam B interface actions recover the exact opposite;
6. plate/bolt group actions are equal/opposite across the splice.

No tolerance dumping.

## Design-result authority

Precedence:

1. invalid/rejected;
2. any required evaluated failure -> `FAIL`;
3. required source/method unavailable -> `NOT_EVALUATED`;
4. all required numerical checks pass -> `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Ordinary unqualified `PASS` is prohibited.

## Qualification / classification authority

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

`WI_MOMENT_SPLICE_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`.

Always unevaluated without external qualification/test authority:

- rotational stiffness classification;
- moment-rotation capacity;
- full-strength / partial-strength classification.

## Disclaimer authority

Backend ID:

`WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1`.

Controlled meaning:

Stage 4.1A performs a complete component-strength calculation using accepted code-based local/pure-mode strengths plus project rational load-distribution/interface methods. The rational methods preserve exact equilibrium but do not constitute experimental qualification of a moment-resistant FRP beam splice. The engineer of record must review load-path assumptions, stiffness/deformation compatibility, actual bolt/contact behavior, plate restraint/buckling conditions, and Section 2.3.2 qualification. Rotational stiffness, rotation capacity, and full-strength classification are not established.

## Preview/design authority

Preview:

- geometry/demand/applicability only;
- resistance calls = 0.

Explicit Run Design Check:

- executes resistance;
- returns full trace/status.

Engineering changes stale the previous design.

## Frozen boundary

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 freeze tags and historical engineering fingerprints remain exact.

## Explicitly excluded from RC1

- Channel moment splice;
- outer-only flange splice;
- minor-axis moment;
- torsion;
- minor shear;
- unequal beams;
- unequal top/bottom flange topology;
- connection stiffness / moment-rotation design.

**END OF STAGE 4.1A W/I MAJOR-AXIS MOMENT SPLICE AUTHORITY LEDGER RC1**
