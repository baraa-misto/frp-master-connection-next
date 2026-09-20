# FRP Master Connection — Calculation Slice 7 — Material-Neutral Angle Connector Core + FRP Resistance Provider — Decision RC2

## Status

**RC2 supersedes the unexecuted RC1 Calculation Slice 7 package before implementation.**

The earlier RC1 package shall not be sent to Codex or implemented.

## Decision

Stage 4.2 shall begin with a reusable architecture that separates:

1. **material-neutral angle-connector geometry/reference/wrench transport**, and
2. **material-specific resistance providers**.

RC2 implements:

- generic angle connector core;
- FRP resistance provider only.

It deliberately does **not** implement the future 316 stainless steel provider, but the core/provider boundary shall allow that provider to be added later without rewriting the connection-demand mechanics.

## Core method identities

Material-neutral core:

`ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`

Exact wrench transport:

`EXACT_ANGLE_CONNECTOR_INTERFACE_WRENCH_TRANSPORT_RC1`

Support handoff:

`EXACT_ANGLE_CONNECTOR_SUPPORT_HANDOFF_RC1`

Core responsibilities:

- angle geometry/reference records;
- local connector frame;
- member-interface wrench;
- heel-reference wrench;
- support-interface wrench;
- exact force/moment equilibrium;
- deterministic core fingerprint.

The core shall contain **no FRP strength equation, no stainless strength equation, and no material-specific resistance assumption**.

## Provider architecture

Provider contract:

`ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`

RC2 provider registry:

- `FRP` -> implemented;
- all other material families -> fail closed as provider unavailable.

Future intended provider:

- `316SS` / controlled structural stainless material provider — **not implemented in RC2**.

Adding the future stainless provider shall not require changing:

- angle connector core geometry;
- wrench transport;
- support handoff;
- exact equilibrium;
- connection topology demand allocation.

## FRP provider

FRP provider identity:

`FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`

It contains:

- ASCE/SEI 74-23 Equation 8-15 instep shear where applicable;
- exact qualified FRP assembly source binding;
- signed six-component qualified strengths;
- explicit qualified interaction authority;
- required heel/leg/through-thickness/contact/prying coverage;
- fail-closed source-required behavior.

Qualified envelope:

`QUALIFIED_FRP_ANGLE_ASSEMBLY_FULL_WRENCH_ENVELOPE_RC1`

Interaction:

`RATIONAL_LINEAR_QUALIFIED_ANGLE_ASSEMBLY_INTERACTION_RC1`

The FRP provider shall not leak its assumptions into the generic core.

## 316 stainless future boundary

RC2 does not implement structural stainless capacity.

The core shall be able to dispatch a future provider such as:

`STRUCTURAL_STAINLESS_ANGLE_RESISTANCE_PROVIDER_RC1`

under a separately controlled engineering package using the appropriate structural stainless specification/material records.

Until implemented:

`CONNECTOR_MATERIAL_PROVIDER_316SS = NOT_IMPLEMENTED_FUTURE_SCOPE`.

Do not expose a user-selectable 316SS option in Stage 4.2 from this slice.

## Stage 4.2 implication

The future Stage 4.2 physical product may initially expose FRP connector angles only, while using the material-neutral core internally.

Later connector-material expansion can add 316SS without reworking the W/I beam-to-wall demand decomposition or the exact support handoff.

## Frozen boundary

All Stage 2.3 through Stage 4.1 freezes remain immutable.

**END OF CALCULATION SLICE 7 ANGLE CONNECTOR CORE AND FRP PROVIDER DECISION RC2**
