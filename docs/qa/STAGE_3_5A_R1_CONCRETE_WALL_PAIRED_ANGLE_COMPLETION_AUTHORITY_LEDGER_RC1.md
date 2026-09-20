# FRP Master Connection — Stage 3.5A-R1 Concrete-Wall Paired-Angle Completion — Authority Ledger RC1

## Successor authority

Stage 3.5A-R1 is an additive controlled successor to Stage 3.5A.

It authorizes:

- presentation-only Brace/beam label normalization;
- completion of the missing connected-member / mirrored-angle scene binding;
- default 1 × 1 wall-anchor group per clip angle;
- connected-member expansion to Flat Plate, Angle, Channel, W/I, RHS, and SRS.

## Historical contract boundary

Historical `3.5A-RC1` remains accepted and reproducible.

Its W/I-only scope and historical 2 × 2 wall-anchor default shall not be silently rewritten.

Stage 3.5A-R1 uses successor contract:

`3.5A-R1-RC1`

## Profile authority

The connected member is horizontal for every profile.

No inclination input is authorized.

The six-profile paired topology reuses the frozen Stage 3.3C3 connected-member authority.

No new profile geometry or bearing/path equation is introduced.

## Default anchor authority

The normal successor default is one anchor per clip angle:

- positive group: 1 × 1 at `(H,V)=(+3,0) in`;
- negative group: 1 × 1 at `(H,V)=(-3,0) in`.

The user may increase the mirrored pattern.

The branch-group centroids remain unchanged; therefore branch and combined wall wrenches remain unchanged.

## One-anchor limitation

A single anchor point at the group centroid cannot, under the existing rigid point-anchor model, equilibrate a branch wrench containing nonzero moment.

Therefore Stage 3.5A-R1 explicitly authorizes:

`WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION = EXTERNAL_DESIGN_REQUIRED`

for 1 × 1 groups.

The exact group wrench and anchor coordinate remain in the external anchor-design handoff.

No fabricated single-anchor force solution is permitted.

## Multi-anchor nominal trace

For larger anchor patterns, accepted Stage 2.5A rigid-group mechanics may provide nominal coordination demand only when the actual anchor coordinates permit exact force/moment equilibrium under existing applicability.

Anchor software remains authoritative.

## Scene authority

The authoritative current scene must include:

- connected member;
- positive clip angle;
- negative clip angle;
- common member group;
- positive wall-anchor group;
- negative wall-anchor group;
- concrete wall.

Mirrored connector owners remain distinct.

No anchor group may appear without its owning clip-angle geometry.

## Shear-only boundary

No change:

- one signed vertical reaction shear;
- no user-applied moments;
- no axial/horizontal/out-of-plane force input;
- exact eccentricity-induced transfer moments retained.

This is not a moment connection.

## External design boundary

No concrete or anchor capacity is introduced.

Existing external-design-required limitations remain.

No whole-connection PASS.

## Frozen-family boundary

No Direct, Stage 3.2 Tee, Stage 3.3 Clip-Angle, or Stage 3.4 Multi-Member Tee engineering fingerprint may change.

All existing freeze tags remain immutable.

**END OF AUTHORITY LEDGER RC1**
