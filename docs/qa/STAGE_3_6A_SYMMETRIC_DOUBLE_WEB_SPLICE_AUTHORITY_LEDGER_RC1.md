# FRP Master Connection — Stage 3.6A Symmetric Double Web Splice Plates — Authority Ledger RC1

## New product authority

Stage 3.6A authorizes one new Beam Connections product:

`Beam connection — Symmetric double web splice plates`

Exactly:

- two collinear identical FRP W/I beams;
- two symmetric FRP flat web-splice plates;
- one physical bolt group on each side of the beam-end joint;
- positive beam-end gap;
- signed axial, major-shear, and minor-shear actions;
- zero user-applied moment.

## Source boundary

ASCE/SEI 74-23 Chapter 8 recognizes splice plates and requires splice actions to include applicable forces and bolt-group-centroid eccentricity.

Stage 3.6A therefore retains exact group eccentricity moments.

RC1 does not authorize a user-applied flexural splice moment.

Required:

`WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER = NOT_AUTHORIZED_IN_RC1`.

## Beam-end gap authority

RC1 requires a positive beam-end gap.

No direct beam-end bearing is used for axial compression.

Compression transfers through the splice-plate system.

No end-bearing partition method is introduced.

## Interface-action authority

Canonical transfer force:

`F_tr=(P_L,V_V,V_T)`.

Beam A interface:

`F_A=F_tr`.

Beam B interface:

`F_B=-F_tr`.

Group moments are exact translations from the joint reference to each physical group centroid.

Generated moments are equilibrium/transfer moments, not user-applied moment-connection actions.

## Component-demand authority

At each interface:

### Beam web

Demand fraction:

`1.0`.

### Splice-plate pair

System demand fraction:

`1.0`.

Under exact plate-pair symmetry:

- positive splice plate layer = `0.5`;
- negative splice plate layer = `0.5`.

The two plates are branches of one symmetric system; they are not each assigned full system demand.

## Material-direction authority

Default bases:

- beam web LW = beam longitudinal `L_S`;
- splice-plate LW = `L_S`;
- beam web / plate CW = vertical `V_S`;
- TT = web/plate normal `T_S`.

Thus:

- axial force is LW-direction;
- major shear is CW-direction;
- minor shear is TT/bolt-axis action.

Each layer's actual backend basis governs.

## Reversed Beam B action

Beam A and Beam B interface forces are equal/opposite.

Loaded-edge, bypass, net/shear-out/block-shear applicability must be derived independently for each physical side.

Beam B may not inherit Beam A's failure-path status after stripping the sign.

## Existing calculation authority

Existing Stage 2.5A / 2.5B / 2.6 mechanics may be used only under their accepted applicability for local web/plate bolt-hole checks.

No new group-demand or resistance equation.

## Plate-body boundary

The continuous splice plates transfer action between the two physical bolt groups.

Stage 3.6A does not authorize a complete inter-group splice-plate body capacity.

Required:

`WEB_SPLICE_PLATE_INTERGROUP_BODY_TRANSFER = NOT_EVALUATED`.

## Metallic common-bolt boundary

Each Plate/Web/Plate bolt is a physical double-shear configuration.

No new metallic double-shear resistance authority is introduced.

Required:

`WEB_SPLICE_COMMON_BOLT_DOUBLE_SHEAR = NOT_EVALUATED`.

Do not double an existing single-shear capacity.

## Minor-shear boundary

Minor shear acts along bolt axes / TT.

Required:

`WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

No bolt-tension, pull-through, or prying capacity is introduced.

## Status boundary

Supported local FRP numerical failure governs `FAIL`.

Otherwise required plate-body / double-shear / minor-shear / member-moment limitations keep the whole splice `NOT_EVALUATED`.

No ordinary whole-splice PASS.

## Frozen-family boundary

Stage 3.5 concrete-support shear family is frozen at:

`stage-3.5-concrete-support-shear-family-freeze`

targeting:

`7bb83e5c8814781419c0789b7428bd46572d514c`.

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 freeze tags remain immutable.

**END OF AUTHORITY LEDGER RC1**
