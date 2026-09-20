# FRP Master Connection
# CME-2 Core C2-R / C2-A / C2-T RC1 Independent Validation

**Status:** PASS - independent validation of the approved isolated C2-core engineering package.  
**Frozen baseline:** `88961da28de3421722290c2bf78af0c6191b81a1`, count 130.  
**Frozen C2-P2 implementation:** `61855bda1f76bbf11a85ae58664ed81bbc8ea419`, tag `cme-2c-c2-p2-freeze`.

## Independence

The benchmark oracle was recomputed without importing any production provider. It validates the approved equations and contract invariants only.

## Recomputed source/method constants

- 316-family project basis: Fy = 25 ksi, Fu = 70 ksi, E = 28,000 ksi, G = 10,800 ksi.
- AISC 370 LRFD factors used by this package: tension yielding 0.90, tension rupture 0.75, compression 0.90, flexure 0.90, shear 0.90.
- AISC 370 Curve A: alpha 0.56, beta0 0.76, beta1 0.41, beta2 0.69.
- AISC 370 F10 austenitic beta_LT = 0.82.
- Frozen project Curve-A cap: Fn_used = min(Fy, Fn_raw).

## Independent benchmark results

Response:
- FRP-steel 2-row distribution of 10 kip -> 6 / 4 kip.
- FRP-steel 3-row distribution of 20 kip -> 10 / 6 / 4 kip.
- Common-shaft layer forces +5 / -3 / -2 kip -> cumulative cuts +5 / +2 / 0 kip.
- Source total tension 12 kip already including 3 kip prying remains 12 kip; no second prying addition.

Angle analytical fixture:
- Ag = 2.859375 in^2.
- D2 gross-yield available tension = 64.335937500000 kip.
- D3 Case 8 net-rupture available tension = 105.000000000000 kip.
- D3 Case 2 U = 0.875000000000.
- G6 zone-1 pure shear available strength = 24.300000000000 kip.
- F10 available flexure: no-LTB 18.000000000000, inelastic-LTB 8.450985630984, elastic-LTB 7.084800000000 kip-in.
- E3/E4 available compression = 23.560378107332 kip, E4 governing in the test-only stability record.
- H2 compression interactions = 0.868885850030 PASS and 1.552586514875 FAIL.
- H2 tension governing interactions = 0.522161505768 PASS and 1.310868245294 FAIL.

Tee analytical fixture:
- D2/D3 available tension = 59.062500000000 kip.
- G6 available pure shear = 18.225000000000 kip.
- F10 inelastic-LTB available flexure = 12.676478446477 kip-in.
- E3/E4 available compression = 18.468510228054 kip, E4 governing in the test-only stability record.

## Counts

- Positive cases: 24.
- Negative/fail-closed cases: 27.
- Invariants: 16.
- Independent validation checks executed: 25.
- Passed: 25.
- Failed: 0.

**Result: PASS.**

The analytical section and stability snapshots in the golden file are test-only trusted fixtures. They are not a product catalogue, not a procurement certificate, and not authority to infer properties for an arbitrary nominal angle or Tee.

This validation does not authorize public family activation. C2-R/C2-A/C2-T remain isolated until a later CME-3 activation stage.
