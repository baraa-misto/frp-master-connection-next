# Material and Fastener Snapshot Specification

## Source and qualification dimensions

Source classification is independent from qualification. Controlled source classes
are code characteristic, qualified test data, manufacturer characteristic,
manufacturer nominal, engineer-approved development, user-defined, and source pending.
Controlled qualification states are qualified, development only, source pending,
engineering review required, and Section 2.3.2 qualification required.

Every FRP property retains kind, quantity, behavior/direction, source class,
qualification, document/revision, applicability, notes, and whether it is eligible for
the future Chapter 8 equation plan. Snapshots use deterministic immutable tuples,
reject duplicate kinds, and distinguish explicit absence from an undeclared kind.
Lookup is exact and never falls back to another property.

## Locked ICE development snapshot

`ICE_LOCKED_PULTRUDED_FRP` contains the RC2 values for `FT_L`, `FT_T`, `ET_L`,
`ET_T`, `FC_L`, `EC_L`, `EC_T`, `FSH_LT`, `G_LT`, `FSH_INT`, `FBR_L`, `FBR_T`,
the three discrete pull-through values, and `NU_LT`. `FC_T` is explicitly absent.
The complete values are controlled in the Stage 2.1A code factory and golden JSON.

The basis is `ENGINEER_APPROVED_DEVELOPMENT`; qualification is development only with
engineering review required. No label upgrades it to characteristic data. Discrete
pull-through data are retained but excluded from the Chapter 8 8-4a/b plan.

## Fastener snapshot

The locked `ASTM_F593_17_GROUP_2_316_316L` preset records:

- ASTM F593-17, Alloy Group 2, 316/316L, cold-worked basis;
- ASTM F594-15 matching nut;
- compatible 316/316L stainless washer basis;
- snug-tight installation;
- ordinary diameter range 0.375 through 1.0 in.; and
- absent `Fnt` with `SOURCE_PENDING` source/qualification state.

No 30, 75, 85, 100 ksi, or other generic strength is substituted. A synthetic
explicit-`Fnt` snapshot is separate, user-defined or engineer-approved development
data, and expressly not an F593-qualified preset.

Thread status is stored separately by shear-plane ID and bearing-layer ID. Washer
diameter, thickness, and presence under head/nut are explicit physical inputs.

## Stage 2.1B numerical consumption

FRP properties used by a ready check are adjusted exactly once by explicit `C_M`,
`C_T`, and `C_CH`, with qualification retained in the trace. ICE values remain
development-only and keep aggregate engineering review. Bearing consumes the
directional property selected by applicability and the checked layer's thread status.

The locked F593 preset still cannot execute bolt strength checks because `Fnt` remains
absent. B1 uses a separate synthetic explicit `100 ksi` fixture, exactly one shear
plane, and threads excluded. No B1 value is written into or represented as the locked
preset.

## Stage 2.2A assignment boundary

Each FRP penetrated layer is explicitly bound by participant, physical element, and
material region to one immutable snapshot; material is never inferred from topology,
participant kind, label, or an adjacent layer. Exact assignments and selected
directional properties remain in response provenance. Metallic layers receive no FRP
check, while unsupported material kinds fail closed. The fastener snapshot is likewise
explicit and unchanged: locked F593 `Fnt` stays source-pending, while a separate
synthetic explicit-`Fnt` snapshot can execute without claiming F593 qualification.
