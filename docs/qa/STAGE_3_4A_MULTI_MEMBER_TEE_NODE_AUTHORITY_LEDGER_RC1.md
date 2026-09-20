# FRP Master Connection — Stage 3.4A Multi-Member Tee Node — Authority Ledger RC1

## New authority

Stage 3.4A authorizes one new product connection type:

`Brace/beam node — Multi-member Tee connector`

It authorizes up to three optional connected-member slots on the same exposed face of one Tee stem:

- Upper Brace — FRP Angle;
- Middle Beam — FRP Wide-Flange / I;
- Lower Brace — FRP Angle.

It authorizes one W Column Flange support and one Tee flange/support bolt group.

At least one slot must be active.

Any valid one-slot, two-slot, or three-slot combination is permitted.

## Frozen single-member Tee boundary

The existing single-member Tee product remains separately available and unchanged.

Stage 3.4A does not replace the Stage 3.2 Tee routes, request contracts, defaults, fingerprints, or freeze evidence.

The Stage 3.2 freeze tag and manifest remain immutable.

## Slot geometry authority

All active connected members attach to the same Tee-stem face.

Each active slot owns:

- one real connected-member profile;
- one independent connection anchor;
- one independent trim state;
- one independent bolt group;
- one independent action/reference;
- one independent result/fingerprint.

Disabled slots are absent from engineering geometry and canonical action/result payloads.

## Profile authority

Initial Stage 3.4A profile scope:

- Upper Brace: Angle;
- Middle Beam: Wide-Flange / I;
- Lower Brace: Angle;
- Support: W Column Flange.

No other profile/support target is authorized in RC1.

## Slot orientation authority

- Upper Brace: `0°` through `+90°`.
- Middle Beam: exactly `0°`.
- Lower Brace: `-90°` through `0°`.

Profile roll remains separate from member inclination.

Bolt groups remain fixed in the Tee-stem frame and do not rotate with member inclination.

## Independent group authority

Stable physical groups:

- Upper Brace ↔ Tee Stem;
- Middle Beam ↔ Tee Stem;
- Lower Brace ↔ Tee Stem;
- Tee Flange ↔ Support.

Each group has independent count, pitch, gauge, and position.

No shared/coupled member bolt group is authorized.

No automatic group repositioning is authorized.

## Joint-wrench assembly authority

Every active slot owns one complete global wrench:

- force `F_i`;
- free moment `M_i`;
- reference point `r_i`.

At support reference `r_S`, the transferred connection wrench is:

`F_S = Σ F_i`

`M_S = Σ [ M_i + (r_i - r_S) × F_i ]`

This is exact wrench translation and summation, not a new connection resistance or load-sharing equation.

The external support reaction on the isolated joint is equal and opposite.

The application shall preserve every slot contribution and provenance identity.

## Demand authority

Each active member group independently uses the accepted Stage 2.5A demand engine with that slot's own action/reference and actual bolt coordinates.

The support group uses Stage 2.5A exactly once with the assembled support-transfer wrench.

The application shall not sum per-bolt support demands from separate slot runs.

## Resistance boundary

Stage 3.4A introduces no new demand or resistance equation.

Existing Stage 2.5B / Stage 2.6 / Stage 2.4B methods may execute only under their accepted applicability contracts.

No automatic prying, bolt-axis tension, moment redistribution, or connector-body stress-field method is authorized.

## Required unsupported checks

The following remain:

`TEE_CONNECTOR_BODY_RESISTANCE = NOT_EVALUATED`

`MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY = NOT_EVALUATED`

The second limitation includes connector-level interaction/stability between separated member groups and the support group.

Ordinary whole-connection PASS is prohibited.

Known supported numerical failure retains overall FAIL precedence.

## Trim authority

Every active slot may independently reuse the accepted member-end trim architecture.

Trim acts on actual member solids, does not move bolt groups, and recomputes fabricated-edge/interference geometry.

No new trim meaning is introduced.

## Visualization authority

Stage 3.4A reuses the shared persistent viewer, real profile geometry, full fasteners, endpoint-based hardware, material axes, and current/last-valid state model.

No frontend engineering geometry or wrench calculation is authorized.

## Fingerprint authority

Stage 3.4A creates new deterministic identities for:

- active slot inputs;
- active member geometries/interfaces/actions;
- Tee connector geometry;
- support transfer wrench;
- support interface;
- preview/design/application results.

All frozen Direct, Tee, and Clip-Angle fingerprints remain exact.

Equivalent U.S./SI requests shall match.

## Explicitly not authorized

Stage 3.4A does not authorize:

- members on opposite Tee-stem faces;
- more than three connected slots;
- profile/support expansion beyond the controlled initial matrix;
- two middle beams;
- common bolts shared by different connected members;
- automatic load redistribution;
- Tee-body global resistance;
- multi-member connector stress-field mechanics;
- moment connection;
- prying/tension generation;
- welds;
- adhesives/epoxy;
- persistence/reporting/authentication.

## Acceptance rule

Stage 3.4A is accepted only after:

- G1–G20 pass;
- all frozen-family regressions/fingerprints pass;
- complete local and object-isolated QA passes;
- hosted Backend/Frontend Ubuntu/Windows CI passes;
- user visual acceptance passes;
- the required Tee-body/intergroup limitations remain explicit.

**END OF AUTHORITY LEDGER RC1**
