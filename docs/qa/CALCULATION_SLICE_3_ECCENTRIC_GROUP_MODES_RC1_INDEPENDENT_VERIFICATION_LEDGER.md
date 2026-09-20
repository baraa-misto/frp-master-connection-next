# FRP Master Connection
# Calculation Slice 3 Eccentric Group-Mode RC1 Independent Verification Ledger

**Status:** Candidate verification ledger pending owner approval  
**Calculation family:** Eccentric inter-row shear-out compatibility and first-row net-tension limitation

## Source review

The source review confirms:

- Section 2.9 requires eccentric fastener effects to be analyzed using established mechanics.
- Section 8.3.3.2 defines shear-out resistance per line of bolts, consistent with a line parallel to the connection-force direction.
- Commentary C8.3.3.1 and Appendix CA8.3.3 base first-row net tension on bearing and bypass loads acting in the connection-force direction, with equal bolt sharing within a row.
- The source does not provide a general noncollinear eccentric first-row net-tension interaction model.

## Independent numerical policy

Reference calculations use Decimal arithmetic with 80-digit working precision.

Golden serialization uses 12 decimal places with `ROUND_HALF_EVEN`.

## Equation 8-12 reference resistance

Reference inputs:

- unloaded-end `e1 = 1.250000000000 in`;
- hole diameter `dn = 0.563000000000 in`;
- pitch `s = 2.000000000000 in`;
- thickness `t = 0.375000000000 in`;
- `Fsh = 8.000000000000 ksi`;
- `phi = 0.450000000000`.

Independent result:

- nominal resistance per bolt line = `12.467700000000 kip`;
- design resistance per bolt line = `5.610465000000 kip`.

## Small eccentric 2x2 case

Using the accepted Stage 2.5A equal-stiffness mechanics for 3 kip and `M_res = -0.3 kip-in`, summing actual bolt vectors by complete physical bolt line gives:

- line A: `1.425000000000 kip` parallel to the connection force;
- line B: `1.575000000000 kip` parallel to the connection force.

Independent utilizations are:

- line A: `0.253989642570`;
- line B: `0.280725394419`.

Both shear-out lines pass.

The first-row resultant is `(1.500000000000, 0.075000000000) kip`, magnitude `1.501873829588 kip`, which is not collinear with the connection force. The source first-row bearing/bypass model therefore does not apply automatically.

## Large eccentric 2x2 case

For the accepted Stage 2.5A `ECCENTRIC_2X2_EQUAL` case:

- one complete bolt line has zero resultant and requires no shear-out comparison;
- the opposite line carries `10.000000000000 kip` parallel to the connection force.

Against the reference design resistance:

- line utilization = `1.782383456630`;
- numerical result = `FAIL`.

This failure remains visible even though eccentric first-row net tension remains unsupported.

## Nonparallel line result

A synthetic line resultant `(2.0, 0.1) kip` is deliberately not reduced to either its magnitude or its parallel projection.

The required result is `CALCULATION_NOT_SUPPORTED`.

## Reversed line result

A line resultant `(-0.5, 0) kip` relative to a `+u` connection-force direction is not automatically reassigned to an opposite-end failure path.

The required result is `CALCULATION_NOT_SUPPORTED`.

## First-row compatibility conclusion

A general nonzero-residual first-row extension is not approved.

The Appendix scalar `L_br` cannot by itself represent unequal and noncollinear first-row bolt forces.

RC1 therefore preserves the zero-residual legacy path and fails closed for general nonzero residual moment.

## Result

The candidate specification and golden are internally consistent.

The new supported engineering capability is limited to actual-line-resultant eccentric shear-out where the physical line resultant remains parallel and nonnegative in the connection-force direction.

No production implementation is authorized by this ledger alone.
