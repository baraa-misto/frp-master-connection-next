# FRP Master Connection
# CME-2 — C2-P2 RC1 Independent Validation

**Status:** Independent validation of the approved RC1 engineering package; not production code.

**Frozen baseline:** `20fabefa90247dd3470d4698edda1b22d017e7c6`  
**Approved golden:** `FRP_MASTER_CONNECTION_CME_2_C2_P2_GOLDEN_BENCHMARKS_RC1.json`

## 1. Independence

The benchmark calculations were recomputed independently from the proposed implementation architecture.

No repository production provider was imported or used.

The validation separately recomputed:

- design-thickness boundary behavior;
- rectangular section properties;
- E3 Curve A compression branches;
- F9 flexural/LTB branches;
- plastic-moment cap;
- trusted-Cb example;
- H2 compression-plus-flexure interaction;
- H2 tension-plus-flexure dual interaction;
- exact native force/length derived moment conversion;
- benchmark structure/count/identity checks.

## 2. Numerical basis

Independent recomputation used:

- `Fy = 25 ksi`;
- `Fu = 70 ksi`;
- `E = 28,000 ksi`;
- `phi_c = phi_b = 0.90`;
- primary section `b = 4 in`, `t = 0.375 in`;
- AISC 370 E3 Curve A coefficients `0.56 / 0.76 / 0.41 / 0.69`;
- F9 branch constants `0.306`, `2.00`, `1.61`, `0.36`, `1.78`;
- H2 interaction algebra;
- native project `1 kip = 4.4482216152605 kN`;
- native project `1 in = 25.4 mm`.

## 3. Key independently recomputed values

Primary section:

- `A = 1.5 in^2`;
- `Iy = 0.017578125 in^4`;
- `Iz = 2.0 in^4`;
- `ry = 0.108253175473... in`;
- `rz = 1.154700538379... in`;
- `Sz = 1.0 in^3`;
- `Zz = 1.5 in^3`.

Compression, weak-axis controlling for the primary examples:

- `Lc = 2 in` -> yield plateau -> `phi Pn = 33.75 kip`;
- `Lc = 12 in` -> inelastic E3 branch -> `phi Pn = 15.725188458451 kip`;
- `Lc = 21 in` -> elastic E3 branch -> `phi Pn = 6.840428943166 kip`.

Flexure:

- `Lb = 10 in`, `Cb=1.0` -> no-LTB branch -> `phi Mn = 33.75 kip-in`;
- `Lb = 30 in`, `Cb=1.0` -> inelastic-LTB branch -> `phi Mn = 30.053571428571 kip-in`;
- `Lb = 100 in`, `Cb=1.0` -> elastic-LTB branch -> `phi Mn = 15.7696875 kip-in`;
- `Lb = 50 in`, trusted `Cb=1.1` -> `phi Mn = 28.533214285714 kip-in`.

H2:

- compression `Pr=10 kip`, `Mr=15 kip-in` with 33.75/33.75 endpoints -> `IR = 0.740740740741`;
- compression `Pr=15 kip`, `Mr=20 kip-in` -> `IR = 1.037037037037`;
- tension `Pr=5 kip`, `Mr=15 kip-in` -> governing `IR = 0.814814814815`;
- tension `Pr=10 kip`, `Mr=20 kip-in` -> governing `IR = 1.185185185185`.

Exact derived moment conversion:

`1 kip-in = 112.98482902761670 kN-mm`.

## 4. Validation result

Independent checks executed: **64**  
Passed: **64**  
Failed: **0**

Result: **PASS**.

The approved RC1 numerical package is internally consistent with the bounded source/method reconciliation.

## 5. Method-lock disposition

`SL-C2P2-BOUNDED-METHOD-POLICY = CLOSED_OWNER_EOR_APPROVED_2026_09_12`

Owner/EOR approval:

> Approved: C2-P2 bounded clear-plate E3/F9/H2 method policy with Cb=1.0 default and fail-closed E4/shear/torsion boundaries.

The numerical benchmark values are unchanged from the independently validated candidate. The approved RC1 package contains 14 positive cases, 17 negative/fail-closed cases, and 13 invariants, with the prior independent recomputation remaining **64/64 PASS**.

This validation does not authorize public family activation or whole-connection stainless approval.
