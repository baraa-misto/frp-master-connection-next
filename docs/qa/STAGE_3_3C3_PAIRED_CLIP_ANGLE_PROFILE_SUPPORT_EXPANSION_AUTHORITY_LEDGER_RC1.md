# FRP Master Connection — Stage 3.3C3 Paired Clip-Angle Connected/Supporting-Member Expansion — Authority Ledger RC1

## New authority

Stage 3.3C3 authorizes product integration of the shared Stage 3.3C1/C2 support-target and rectangular full-through architecture into the Symmetric Paired FRP Clip-Angle family.

### Connected profiles
- Flat Plate
- Wide-Flange / I Web
- Channel Web
- Angle selected leg
- Rectangular Hollow Section
- Solid Rectangular Section

### Supporting targets
- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

## Connected Angle authority

One clip angle is placed on each broad face of one selected member Angle leg.

Common path:
`positive clip leg -> selected member Angle leg -> negative clip leg`

Heel and perpendicular-leg collision remain fail-closed.

Equal sharing is not automatically authorized for Angle members.

## Connected rectangular authority

RHS common path:
`positive clip leg -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall -> negative clip leg`

SRS common path:
`positive clip leg -> full solid depth -> negative clip leg`

One physical bolt per common axis.
No internal RHS hardware.

## Supporting-member authority

The paired family consumes the same shared support-target contract/editor as Tee and Single-Angle.

Two mirrored support groups remain physically separate.

For RHS/SRS supports, each support group independently uses full-through/full-depth bolts.

Normal C3 topology does not infer one common support bolt merely because the target is rectangular.

## Equal-sharing boundary

C3 adds no new sharing equation.

The Stage 3.3B symmetry/action proof remains controlling.

Angle/asymmetric connected/support geometry remains `NOT_EVALUATED` for distribution unless the complete proof passes.

## Endpoint/hardware authority

C3 reuses Stage 3.3C2-R2 endpoint-based hardware placement.

Physical hardware orientation is derived from actual stack start/end points, not arbitrary engineering-axis sign.

Existing engineering axes and numerical sign conventions remain unchanged.

## No new resistance authority

C3 does not authorize:
- paired connector body capacity
- common through-bolt double-shear capacity
- branch compatibility capacity
- RHS local wall response
- RHS sleeve/crush-tube design
- SRS full-depth resistance method

Known supported failures still govern FAIL.
Ordinary whole-connection PASS remains prohibited where required checks are not evaluated.

## Regression boundary

Existing Stage 3.3B requests remain exact.

Tee and Single-Angle product behavior/fingerprints remain unchanged.

Stage 2.3 and Stage 3.2 freeze tags remain immutable.

**END OF AUTHORITY LEDGER RC1**
