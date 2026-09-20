# FRP Master Connection — Stage 3.2-R12 Connected-Member End Trim + User Clearance — Authority Ledger RC1

## New authority
R12 authorizes:
1. explicit user-controlled fabrication end trim for the connected brace/beam in a Tee connection;
2. On/Off trim state;
3. exact user-entered clearance from the Tee flange/root reference plane;
4. a connector-frame fabrication cut plane;
5. exact trimming of existing connected-member profile solids;
6. connector interference reporting;
7. exact bolt-center and hole-edge geometry relative to the fabricated cut edge.

## Recommended terminology
Normal UI:
- `Apply end trim clearance`
- `End clearance to Tee flange`

Generic domain/help:
- `Connected-member end trim`
- `Connected-member end clearance`

The longer phrase `clear distance between beam/brace and the connector` is not used in the normal UI because it is less precise about the measurement plane.

## Measurement authority
The clearance is the perpendicular gap between:
- `TEE_FLANGE_INNER_CLEARANCE_PLANE`; and
- the fabricated connected-member cut plane.

It is not a bolt edge distance and is not measured along the brace axis.

## Inherited authority
Unchanged:
- all Stage 2 calculation authorities;
- Stage 3.1 material authority;
- Stage 3.2 Tee topology;
- R2 member/profile geometry;
- R4 exact units;
- R5 deterministic geometry/fingerprints;
- R6 preview-state behavior;
- R7/R8 profile wall paths;
- R9 hardware;
- R10 fixed Tee-frame bolt grid and placement geometry;
- R11 simplified placement UX.

## Resistance boundary
R12 introduces no new resistance equation.

Existing checks may consume a trimmed free edge only when their current accepted geometry contract unambiguously maps to the same physical edge without new interpretation.

Otherwise return unsupported/not evaluated.

## Interference rule
Trim disabled does not hide or auto-remove connector/member interference.

Trim enabled removes only the portion cut away by the exact fabrication plane.

Remaining interference remains invalid.

## Fingerprint rule
Trim disabled/omitted preserves legacy controlled fingerprints.

Trim-enabled geometry creates deterministic identity from:
- enabled state;
- exact clearance;
- resulting trimmed geometry.

No previous controlled fingerprint transition is authorized.

## Not authorized
R12 does not authorize:
- automatic trim without user selection;
- automatic clearance value;
- negative clearance;
- bolt auto-relocation;
- member auto-resizing;
- frontend-only engineering clipping;
- new edge-distance equations;
- new shear-out/net/block interpretation;
- access holes;
- blind fasteners;
- prying;
- connector-body strength.

**END OF AUTHORITY LEDGER RC1**
