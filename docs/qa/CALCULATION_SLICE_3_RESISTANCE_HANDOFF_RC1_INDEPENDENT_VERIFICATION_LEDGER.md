# FRP Master Connection
# Calculation Slice 3 Resistance Handoff RC1 Independent Verification Ledger

**Status:** Candidate verification ledger pending owner approval  
**Calculation family:** Eccentric bolt-group demand to directional FRP resistance compatibility and handoff  
**Parent demand authority:** Calculation Slice 3 RC1 / Stage 2.5A  
**Parent resistance authority:** Calculation Slice 2 RC2 / Stage 2.4B

## Verification objective

This ledger independently checks the RC1 compatibility decisions and benchmark arithmetic without modifying either parent calculation authority.

## Source review conclusions

The source basis establishes three important constraints.

1. Connection strength is to be evaluated using the actual force distribution.
2. Pin-bearing property selection is based on the orientation of the resultant force at the individual bolt/FRP contact relative to the material pultrusion direction.
3. The accepted multi-row first-row row-distribution/bypass method assumes bolt bearing in the connection-force direction, while the standard separately provides an eccentric block-shear resistance equation with limited FRP test evidence.

These source facts support direct per-bolt bearing/shear handoff but do not provide a verified RC1 rule for converting noncollinear eccentric bolt vectors into first-row net-tension or inter-row shear-out demand.

## Numerical reference policy

Reference arithmetic was independently evaluated with Decimal values at 80-digit working precision.

Golden output is serialized to 12 decimal places with `ROUND_HALF_EVEN`.

No binary floating point is an engineering authority.

## Bearing reference

Using the inherited benchmark values:

- `t = 0.375 in`
- `d = 0.500 in`
- `Fbr,L = 30 ksi`
- `Fbr,T = 18 ksi`
- `phi = 0.60`

Reference design resistances are:

- longitudinal bearing: `3.375000000000 kip`
- transverse bearing: `2.025000000000 kip`

## Key reference cases

### Concentric 2x2 full handoff

For 3 kip in-plane force with equal 2x2 direct sharing and zero residual moment:

- per-bolt demand = `0.750000000000 kip`;
- all bolt vectors remain collinear with the connection force;
- longitudinal bearing utilization = `0.222222222222`;
- simplified first-row utilization = `0.484848484848`;
- inter-row shear-out line utilization = `0.213433049254`.

This reproduces the accepted legacy demand meaning and supports full handoff.

### Small-eccentric 2x2 partial handoff

For 3 kip at `0.1 in` eccentricity:

- residual moment = `-0.300000000000 kip-in`;
- bolt magnitudes are:
  - `0.713486159642`;
  - `0.788392351561`;
  - `0.713486159642`;
  - `0.788392351561` kip;
- bearing angles remain below 5 degrees and select longitudinal bearing;
- all supported bearing checks pass;
- first-row net tension and inter-row shear-out remain unsupported;
- ordinary PASS is therefore prohibited.

### Large-eccentric 2x2 bearing shift

For the accepted Stage 2.5A `ECCENTRIC_2X2_EQUAL` case:

- bolt 1 and 3 act at 90 degrees to a layer whose LW axis is `u`;
- bolt 2 and 4 act at approximately 26.565 degrees;
- all four therefore select transverse bearing;
- bearing utilizations are:
  - `1.234567901235`;
  - `2.760577750000`;
  - `1.234567901235`;
  - `2.760577750000`;
- the supported bearing checks fail;
- the known failure remains controlling even though first-row/shear-out handoff is unsupported.

### Layer-specific directional selection

For physical bolt vector `(0, 2.5) kip`:

- an FRP layer with LW along `u` sees 90-degree bearing and uses transverse bearing;
- an FRP layer with LW along `v` sees 0-degree bearing and uses longitudinal bearing.

The physical demand is identical; only the layer material axis changes.

### Direction boundary

Independent high-precision trigonometric reference values verify:

- exactly 5 degrees -> longitudinal;
- 5.000001 degrees -> transverse;
- exact 90 degrees -> accepted project transverse endpoint.

### Eccentric block shear

The accepted Slice 2 case `BS_U3_ECCENTRIC` remains:

- total connection demand = `6.000000000000 kip`;
- design resistance = `11.644256250000 kip`;
- utilization = `0.515275503320`.

The handoff is authorized only when the existing path/eccentricity context is proven to represent the same canonical physical force line.

## Fail-closed verification

The benchmark set verifies:

- zero-demand bolts do not receive invented bearing direction or utilization;
- supported-check PASS plus unsupported required group modes does not become ordinary PASS;
- supported bearing failure remains FAIL with unsupported group modes still visible;
- member-end moments remain untransferred;
- out-of-plane force does not generate bolt-axis demand or prying;
- explicit axis tension is consumed rather than generated.

## Engineering boundary

RC1 intentionally does not establish eccentric first-row net-tension or inter-row shear-out demand.

Those modes require a separate mechanics/source development step if future automatic eccentric whole-connection PASS is desired.

## Result

The candidate RC1 compatibility specification and golden are internally consistent with the accepted parent demand and resistance authorities.

No production implementation is authorized by this ledger alone.
