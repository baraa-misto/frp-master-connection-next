# FRP Master Connection
# Calculation Slice 3 RC1 Independent Verification Ledger

**Status:** Candidate verification ledger pending owner approval  
**Calculation family:** Member-end-force transfer and eccentric in-plane bolt-group demand  
**Companion specification:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_3_ENGINEERING_SPECIFICATION_RC1.md`  
**Companion golden:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_3_GOLDEN_BENCHMARKS_RC1.json`

## Verification basis

The reference calculations were performed independently with Python `Decimal` arithmetic at 80-digit working precision.

The candidate implementation policy is 60-digit internal Decimal precision with no intermediate engineering rounding.

Golden serialization uses 12 decimal places with `ROUND_HALF_EVEN`.

## Source review

The engineering basis was checked against:

- ASCE/SEI 74-23 Section 2.9;
- ASCE/SEI 74-23 Commentary C8.1;
- ASCE/SEI 74-23 Commentary C8.3.2.

The standard requires equilibrium and realistic force/moment distribution and states that moment-induced internal forces are linear with distance from the center of rotation.

The specific superposition of the existing Stage 2.4A direct-demand plan with the residual equal-stiffness elastic moment correction is treated as a project rational extension, not as a quoted ASCE formula.

## Numerical checks

Reference cases independently verify:

- concentric direct force;
- eccentric direct force;
- diagonal force plus eccentricity;
- force reversal;
- three-row FRP/steel direct distribution plus eccentricity;
- pure-moment unsupported status;
- out-of-plane-force warning;
- nonzero-member-moment warning;
- single-bolt eccentric-moment unsupported status;
- U.S./SI physical equivalence.

For every calculated numerical case:

- vector-force equilibrium closes at the stored precision;
- moment equilibrium about the geometric bolt centroid closes at the stored precision;
- direct and moment components are retained separately;
- total per-bolt magnitudes are recomputed from vector components rather than independently prescribed.

## Key independent reference results

### ECCENTRIC_2X2_EQUAL

Input:

- four bolts at `(±1, ±1) in`;
- 10 kip in `+u`;
- force reference point `(0, 2) in`;
- equal direct shares.

Reference values:

- geometric centroid `(0,0) in`;
- `Jb = 8 in²`;
- external moment `-20 kip-in`;
- residual moment `-20 kip-in`;
- per-bolt total magnitudes: `2.5`, `5.590169943749`, `2.5`, `5.590169943749 kip`.

### DIAGONAL_FORCE_ECCENTRIC_2X2

Input:

- same four-bolt geometry;
- force `(6,8) kip`;
- reference point `(1.2,-0.5) in`.

Reference values:

- external moment `12.6 kip-in`;
- per-bolt total magnitudes:
  - `3.104230983674 kip`
  - `0.431566912541 kip`
  - `4.715532843699 kip`
  - `3.575786626744 kip`

### FRP_STEEL_3ROW_ECCENTRIC

Input:

- three bolts at `u = -2, 0, 2 in`;
- prescribed direct shares `0.50, 0.30, 0.20`;
- force `10 kip` in `+u`;
- force-line offset `+1 in` in `v`.

Reference per-bolt total magnitudes:

- `5.590169943749 kip`
- `3.000000000000 kip`
- `3.201562118716 kip`

## Deliberate verification boundary

This ledger does not verify resistance utilization from these eccentric per-bolt vectors.

Resistance handoff is explicitly deferred because the accepted FRP resistance engine has directional and applicability assumptions requiring a separate engineering compatibility review.

## Result

The candidate RC1 specification and golden are internally consistent for the demand-analysis scope described above.

No production implementation is authorized by this ledger alone.
