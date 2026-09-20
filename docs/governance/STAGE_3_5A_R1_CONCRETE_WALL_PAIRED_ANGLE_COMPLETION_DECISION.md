# FRP Master Connection — Stage 3.5A-R1 Concrete-Wall Paired-Angle Completion Decision

## Decision

Stage 3.5A-R1 completes the Stage 3.5A Beam/Member-to-Concrete-Wall paired clip-angle product before final visual acceptance.

The successor stage has four owner-directed changes:

1. Presentation labels for the common shear families shall use **Brace/beam** rather than Brace-only wording where the same physical connection can serve a zero-degree beam.
2. The concrete-wall paired-angle scene shall render the complete physical topology: connected member, positive clip angle, negative clip angle, common member group, and both wall-anchor groups.
3. The default wall-anchor pattern shall be **one anchor per clip angle (1 × 1 per mirrored group)**. The user may increase rows and anchors-per-row as required.
4. The connected member shall support the full six-profile matrix already accepted by the frozen paired clip-angle family:
   - Flat Plate
   - Angle
   - Channel
   - Wide-Flange / I
   - Rectangular Hollow Section
   - Solid Rectangular Section

## Connection naming

The concrete-wall product remains:

`Beam connection — Paired clip angles to concrete wall`

because the connected member is horizontal in Stage 3.5A.

The connected-member panel shall use the generic label:

`Connected Member`

Existing shared shear-family presentation labels shall be normalized where applicable:

- `Brace connection — Direct` -> `Brace/beam connection — Direct`
- `Brace connection — Tee connector` -> `Brace/beam connection — Tee connector`
- `Brace connection — Symmetric paired clip angles` -> `Brace/beam connection — Symmetric paired clip angles`

Existing labels already using Brace/beam remain unchanged.

The selector group heading shall be:

`Brace/beam connections`

These are presentation-label changes only and shall not alter request identities or engineering fingerprints.

## Connected-member semantics

All six connected profiles are horizontal and frame normal to the concrete wall.

Stage 3.5A-R1 does not add inclination input.

The paired clip angles use the exact frozen Stage 3.3C3 connected-member topology for each profile:

- Flat Plate: one clip angle on each broad face.
- Angle: one clip angle on each broad face of one selected Angle leg.
- Channel: paired connection on the selected accepted physical region.
- W/I: paired connection on opposite selected web/region faces.
- RHS: common physical bolts traverse positive clip angle, near wall, cavity, far wall, negative clip angle.
- SRS: common physical bolts traverse positive clip angle, full solid depth, negative clip angle.

## Default external-anchor pattern

Each mirrored wall-anchor group defaults to:

- rows: `1`;
- anchors per row: `1`;
- positive group centroid: `H_W = +3 in`, `V_W = 0`;
- negative group centroid: `H_W = -3 in`, `V_W = 0`.

Default anchor coordinates:

- positive: `(H,V) = (+3,0) in`;
- negative: `(H,V) = (-3,0) in`.

The branch and combined wall wrenches remain unchanged because the group centroids remain unchanged.

## One-anchor engineering boundary

A one-anchor group cannot, under the existing rigid point-anchor distribution model, independently equilibrate a general branch wrench containing nonzero moment at the anchor centroid.

Therefore the default 1 × 1 group shall **not** fabricate a per-anchor force solution for the branch moments.

For 1 × 1 groups:

- the exact branch wrench is retained;
- the anchor coordinate is retained;
- the complete external anchor-design handoff is retained;
- internal nominal point-anchor force distribution is `EXTERNAL_DESIGN_REQUIRED`.

For multi-anchor groups, a nominal coordination demand trace may be shown only where the accepted Stage 2.5A rigid-group mechanics are applicable and equilibrium is exact.

Specialized anchor software remains authoritative for anchor-force distribution and all anchor/concrete capacities.

## Engineering boundary

No new demand, resistance, concrete, or anchor equation is introduced.

Shear-only input remains controlling.

User-applied moments remain prohibited.

Eccentricity-induced transfer moments remain mandatory in the external handoff.

Concrete and anchor capacities remain external.

## Frozen-family boundary

Stage 2.3, Stage 3.2, Stage 3.3, and Stage 3.4 freeze tags remain immutable.

The frozen Stage 3.3 paired-angle product remains exact.

The existing Stage 3.5A RC1 request/engineering fingerprint remains reproducible under its historical contract.

Stage 3.5A-R1 introduces a successor contract for the expanded profile/default behavior.

**END OF STAGE 3.5A-R1 CONCRETE-WALL PAIRED-ANGLE COMPLETION DECISION**
