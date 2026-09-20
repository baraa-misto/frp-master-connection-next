# FRP Master Connection — Stage 3.3C2 Tee + Single Clip-Angle Supporting-Member and Rectangular-Section Expansion — Authority Ledger RC1

## New authority

Stage 3.3C2 authorizes product integration of the Stage 3.3C1 shared core into:

- FRP Tee connections;
- Single FRP Clip-Angle connections.

It authorizes these supporting-member targets in both families:

- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

It also authorizes `Solid Rectangular Section` as a connected-member option wherever these two families offer `Rectangular Hollow Section`.

## Rectangular full-through successor authority

For C2-integrated RHS paths, the normal product behavior is one full-through physical bolt:

`external connector layer(s) -> near RHS wall -> cavity free shank span -> far RHS wall -> external hardware`

No internal nut or washer is authorized.

This intentionally supersedes historical single-wall RHS behavior for affected Tee and Single Clip-Angle requests.

## Frozen Tee successor boundary

The Stage 3.2 freeze tag and freeze manifest remain immutable historical evidence.

C2 may intentionally supersede only the Tee RHS request classes whose physical bolt path changes from single-wall to the user-confirmed full-through arrangement.

For each such request class:
- exact before/after fingerprints are mandatory;
- canonical payload differences must be limited to the full-through successor geometry/path/access identity;
- all non-RHS frozen Tee behavior remains exact.

No freeze tag may move.

## Single Clip-Angle successor boundary

The accepted Stage 3.3A historical baseline remains evidence.

Affected RHS request classes intentionally transition from single-wall to full-through behavior.

All non-RHS Stage 3.3A R1-R4 behavior remains exact.

## Supporting-member geometry authority

C2 authorizes integration of the C1 target registry into Tee and Single-Angle physical support interfaces.

Open-section targets:
- W Column Web
- Channel Column Web
- Angle Column Leg

reuse existing exact physical surface/path authority.

Rectangular targets:
- RHS Column Wall uses near-wall/cavity/far-wall full-through paths;
- SRS Column Face uses one full solid-depth path.

## Solid rectangular authority

SRS is a real continuous solid member, not hidden RHS geometry.

Connected and support SRS requests use one full-depth material segment.

## No new resistance authority

C2 does not authorize new resistance equations.

Required unsupported rectangular local checks remain explicit, including:
- `RHS_LOCAL_WALL_RESPONSE`
- `RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT`
- `SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY`

These are design limitations, not geometry-invalid reasons.

The RHS cavity is not a material layer and receives no bearing demand or resistance check.

## Existing methods

Existing accepted bolt shear, FRP bearing, block/shear-out, and group-mode calculations may run only where their current applicability contracts clearly cover the actual physical layers/geometry.

No far-wall RHS demand is inferred merely because a bolt reaches the far wall.

## Product/UI authority

Tee and Single Clip-Angle shall use one shared support-target contract/editor.

The exact seven support options are controlled.

Where RHS is offered as a connected profile, SRS shall also be offered.

## Paired-angle boundary

Stage 3.3B production topology/selectors remain unchanged by C2.

Stage 3.3C3 will integrate:
- new paired support targets;
- Angle connected-member paired topology;
- RHS/SRS connected-member paired full-through topology.

## Acceptance

C2 is accepted only when:
- all C2 G1-G18 pass;
- exact RHS successor transitions are recorded;
- all unaffected legacy fingerprints remain exact;
- frozen non-RHS Tee behavior remains exact;
- single-angle non-RHS behavior remains exact;
- paired-angle behavior remains exact;
- full-through hardware has no internal nut/washer;
- local rectangular mechanics remain fail-closed;
- full QA, hosted CI, and user visual matrix pass.

**END OF AUTHORITY LEDGER RC1**
