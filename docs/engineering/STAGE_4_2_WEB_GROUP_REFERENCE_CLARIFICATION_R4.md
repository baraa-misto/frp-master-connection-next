# FRP Master Connection — Stage 4.2 — Web Group Reference Clarification R4

## Status

**Controlled pre-implementation clarification R4.**

No Stage 4.2 repository mutation has occurred.

R4 resolves the web-group reference conflict identified during the R3 mandatory pre-implementation audit.

All R3 engineering methods and all earlier accepted dependencies remain unchanged.

## Controlling representation

Use the physical heel-local angle coordinate representation.

The Stage 4.2 common web-bolt coordinates remain exactly:

- `A=-1.5 in, B=1.25 in`;
- `A=+1.5 in, B=1.25 in`;
- `A=-1.5 in, B=2.75 in`;
- `A=+1.5 in, B=2.75 in`.

Their exact centroid is:

`(A_c,B_c)=(0,2.0) in`.

The web member-interface wrench reference is also:

`(A_R,B_R)=(0,2.0) in`.

Therefore the independently applied `M_C,R` is already stated at the physical bolt-group centroid.

No additional force-reference eccentricity moment is generated when Slice 8 transports the wrench to the group centroid.

## Why this representation controls

The alternative centroid-relative representation:

- bolt coordinates `A=±1.5`, `B=±0.75`;
- wrench reference `(0,0)`;

is mechanically translation-equivalent.

However, it is **not controlling for Stage 4.2** because Stage 4.2 already defines:

- angle-local geometry from the heel;
- member-interface reference at local `B=2.0 in`;
- physical bolt coordinates in that same heel-local frame;
- reference-bound deterministic fingerprints.

Keeping G60's heel-local physical coordinates and setting G66/G68 to reference `(0,2)` preserves one consistent physical coordinate system and preserves the intended reference-bound provenance.

Do not translate the Stage 4.2 physical bolt coordinates to a centroid-relative frame merely to reuse the accepted Slice 8 fixture fingerprint.

## Positive web input

Use:

- bolt coordinates from G60;
- wrench reference `(0,2) in`;
- `F_A=+5 kip`;
- `F_B=+3.6 kip`;
- `M_C,R=+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

Since reference equals centroid:

`M_C,c=M_C,R`.

## Negative web input

Use:

- bolt coordinates from G60;
- wrench reference `(0,2) in`;
- `F_A=-5 kip`;
- `F_B=+3.6 kip`;
- `M_C,R=-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

Again:

`M_C,c=M_C,R`.

## Slice 8 relation

Stage 4.2 shall compare its web-group result with a **direct accepted Slice 8 invocation using the physical G60 coordinates and reference `(0,2)`**.

The result vectors must be mechanically identical to the accepted centroid-relative Slice 8 Stage 4.2 fixture because the bolt coordinates and reference have been translated together.

The reference-bound fingerprint is expected to differ from a centroid-relative fixture fingerprint and shall not be forced to match it.

Stage 4.2 shall preserve the physical-reference fingerprint generated from its actual coordinates/reference.

## Golden case labels

R4 cleans stale pre-Slice-8 case labels without changing G numbers:

- G66 -> `G66_POSITIVE_WEB_SLICE8_INPUT`;
- G67 -> `G67_POSITIVE_WEB_SLICE8_OUTPUT`;
- G68 -> `G68_NEGATIVE_WEB_SLICE8_INPUT`;
- G69 -> `G69_NEGATIVE_WEB_SLICE8_OUTPUT`;
- G70 -> `G70_SLICE8_EXACT_RECOVERY`.

G71 now references the actual G67/G69 Slice 8 output case IDs.

This is metadata/reference cleanup only; it changes no physical mechanics.

## Numeric authority

All R3 native-engine boundaries remain controlling.

The final Stage 4.2 audit diagnostics remain:

- axial `+3E-79 kip`;
- right-hand wall major moment `+6E-79 kip-in`;
- structural wall major moment `-6E-79 kip-in`.

No tolerance and no redistribution.

## Supersession

The R3 golden is superseded before implementation.

The controlling golden is:

`FRP_MASTER_CONNECTION_STAGE_4_2_WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_GOLDEN_BENCHMARKS_RC1_R4.json`.

It contains exactly G1-G128.

The R3 clarification and implementation order remain controlling except where this R4 explicitly corrects web bolt-group coordinate/reference authority and case labels/references.

**END OF STAGE 4.2 WEB GROUP REFERENCE CLARIFICATION R4**
