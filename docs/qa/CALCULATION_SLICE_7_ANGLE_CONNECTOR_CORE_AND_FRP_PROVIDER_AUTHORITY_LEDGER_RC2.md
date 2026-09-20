# FRP Master Connection — Calculation Slice 7 — Material-Neutral Angle Connector Core + FRP Resistance Provider — Authority Ledger RC2

## Supersession

RC2 supersedes the unexecuted RC1 Calculation Slice 7 package before implementation.

The RC1 package is historical draft authority only and shall not be implemented.

## Core authority

Material-neutral core:

`ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`.

It owns only:

- connector geometry/reference contract;
- connector local frame;
- exact member-to-heel wrench transport;
- exact support handoff;
- exact connector equilibrium;
- material-neutral core fingerprint.

It owns no material resistance.

## Provider authority

Provider interface:

`ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`.

RC2 implements only:

`FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`.

Unsupported future providers fail closed and may not inherit FRP resistance behavior.

## FRP provider authority

The FRP provider owns:

- ASCE/SEI 74-23 Equation 8-15 instep shear within applicability;
- qualified FRP assembly source binding;
- signed qualified strengths;
- required full-wrench coverage;
- source-authorized rational interaction;
- FRP review/disclaimer/status behavior.

## Future 316SS authority boundary

Structural stainless resistance is not part of RC2.

A future 316SS provider shall be implemented under a separate controlled engineering package and shall reuse the same core.

It must not require changes to core wrench transport or support handoff.

## Fingerprint boundary

The core fingerprint excludes provider/material resistance identity.

Provider fingerprints are separate.

This is intentional and required for later material-provider expansion without invalidating demand mechanics.

## Frozen boundary

Stage 4.1 family and all prior freezes remain exact.

**END OF CALCULATION SLICE 7 ANGLE CONNECTOR CORE AND FRP PROVIDER AUTHORITY LEDGER RC2**
