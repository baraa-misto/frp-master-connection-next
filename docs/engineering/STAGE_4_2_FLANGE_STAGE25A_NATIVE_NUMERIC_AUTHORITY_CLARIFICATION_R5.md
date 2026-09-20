# FRP Master Connection — Stage 4.2 — Flange Stage 2.5A Native Numeric Authority Clarification R5

## Status

**Controlled pre-implementation clarification R5.**

No Stage 4.2 repository mutation has occurred.

R5 resolves the flange Stage 2.5A numerical-authority mismatch found during the R4 mandatory pre-implementation audit.

No physical mechanics, topology, or accepted dependency behavior changes.

## Root cause

The R4 golden used separately calculated Decimal-80 `N/4` values as literal controlling expectations for the top and bottom flange member-side bolt demand.

However, Stage 4.2 is required to use the unchanged accepted Stage 2.5A engine for those flange groups.

Stage 2.5A passes through its own accepted canonical force-unit/numeric path before producing its native per-bolt demand records.

Therefore:

- the algebraic direct-share mechanics agree;
- the final native Decimal representations differ in their trailing digits;
- independently computing `N/4` in Stage 4.2 is not a valid exact oracle for the immutable Stage 2.5A output.

## Controlling rule

For top and bottom flange member-side in-plane bolt demand, the controlling numerical authority is:

`STAGE_2_5A_ACCEPTED_ENGINE`

invoked directly with the exact Stage 4.2 physical input/group.

Stage 4.2 shall consume the returned Stage 2.5A demand records verbatim.

It shall not:

- replace them with independently calculated `N/4`;
- project them to Decimal-80 merely to make a golden comparison;
- reimplement Stage 2.5A direct-share mechanics;
- round, quantize, truncate, or otherwise modify the native result;
- use a tolerance.

## Top flange

R5 G64 is now:

`G64_TOP_FLANGE_STAGE25A_NATIVE_DEMAND`.

The Stage 4.2 top-flange integration result must be exactly equal to a direct invocation of the unchanged accepted Stage 2.5A engine for the same top-flange member-side group.

For audit only, the native signed per-bolt B-component observed by Codex is:

`3.850740375123395853899308983218163869693978282329713721618953603158933859822310073801547368672344557 kip`.

The prior independently calculated Decimal-80 `N/4` value:

`3.850740375123395853899308983218163869693978282329713721618953603158933859822310 kip`

is a noncontrolling algebraic diagnostic only.

## Bottom flange

R5 G65 is now:

`G65_BOTTOM_FLANGE_STAGE25A_NATIVE_DEMAND`.

The Stage 4.2 bottom-flange integration result must be exactly equal to a direct invocation of the unchanged accepted Stage 2.5A engine for the same bottom-flange member-side group.

For audit only, the native signed per-bolt B-component observed by Codex is:

`-0.6507403751233958538993089832181638696939782823297137216189536031589338598223098939543928889039582288 kip`.

The prior independently calculated Decimal-80 `N/4` value:

`-0.65074037512339585389930898321816386969397828232971372161895360315893385982230992 kip`

is a noncontrolling algebraic diagnostic only.

## Mechanics compatibility

This clarification does not weaken the physical requirement.

For these RC1 flange groups:

- the accepted Stage 2.5A path is within its supported force/eccentricity scope;
- no independently applied member-end in-plane free moment is sent through Stage 2.5A;
- the direct equal-share mechanics remain the accepted physical model;
- force/moment proof/status remain those of Stage 2.5A.

Stage 4.2 shall test both:

1. exact native dependency integration equality; and
2. the expected algebraic direct-share mechanics as a separate nonserialization proof/diagnostic where useful.

The second test may not replace the first.

## Cross-engine authority consistency

R5 applies the same project rule already established for Slice 7 and Slice 8:

**an immutable accepted calculation engine owns its native numerical output.**

Integration goldens shall test direct dependency equality rather than duplicate the dependency's mechanics through a second numerical path.

No tolerance is introduced.

## Supersession

The Stage 4.2 RC1-R4 golden is superseded before implementation.

The controlling golden is:

`FRP_MASTER_CONNECTION_STAGE_4_2_WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_GOLDEN_BENCHMARKS_RC1_R5.json`.

It contains exactly G1-G128.

R4 and R3 remain controlling in all other respects.

## No scope change

R5 changes no:

- beam/wall/angle geometry;
- Slice 5 allocation;
- Slice 7 connector behavior;
- Slice 8 web demand;
- Stage 2.5A behavior;
- qualified-source requirement;
- wall handoff;
- diagnostic residuals;
- status/qualification;
- 316SS scope;
- later moment-family scope.

**END OF STAGE 4.2 FLANGE STAGE 2.5A NATIVE NUMERIC AUTHORITY CLARIFICATION R5**
