# FRP Master Connection
# Calculation Slice 2 RC2 Independent Verification Ledger

**Document status:** Candidate verification record pending Baraa Misto approval  
**Engineering specification:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC2.md`  
**Engineering specification SHA-256:** `C296E5FB3B304985A62D49B3F486EF6DB8E5D212EDFE2B83AACB6D68E09B71FD`  
**Golden benchmark:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_GOLDEN_BENCHMARKS_RC2.json`  
**Golden benchmark SHA-256:** `B3A49FB44089E065F7B4659F52AB856288298247504423970C3D19B8FCEA7B0B`  
**Parent RC1 specification SHA-256:** `44431A8921CF1ADF9C7D0F7F022C9615265308A41BE589B1EE5150A7D7886F99`  
**Parent RC1 golden SHA-256:** `C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610`  
**Slice 1 RC2 golden SHA-256:** `39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392`

---

## 1. Verification disposition

The RC2 candidate package was developed from:

- the approved Slice 2 RC1 specification;
- the unchanged Slice 2 RC1 golden;
- the accepted Stage 2.4A contracts and Stage 2.4A-R1 correction history;
- the complete Stage 2.4B Phase 1 read-only architecture report;
- the approved Phase 2 D1–D18 docket;
- ASCE/SEI 74-23 Chapter 2, Section 2.9, Section 2.10, Chapter 8, Commentary C8, and Appendix CA8.3.3;
- Erratum 1.

Disposition:

```text
RC2 SPECIFICATION CANDIDATE:
INTERNALLY CONSISTENT

RC2 GOLDEN CANDIDATE:
VALID JSON AND NUMERICALLY VERIFIED

RC1 REGRESSION:
136 CHECKS, 0 DISCREPANCIES

STAGE 2.4B IMPLEMENTATION:
NOT AUTHORIZED UNTIL OWNER APPROVAL
```

No repository implementation, API change, frontend change, dependency change, commit, push, or tag action was performed.

---

## 2. Source and artifact review

Erratum 1 changes Chapter 5, Section 5.2.3.5 only. It does not change the Chapter 8 basis used by this package.

The source review confirmed:

- Commentary C8.2.5 defines `e1` from the unloaded free end to the nearest row.
- Commentary Table C8-1 gives the four approved distributions.
- Section 8.3.3 applies the `0.60` single-lap multiplier to `Rbr`, `Rnt,f`, `Rsh`, `Rbs`, and `Rbs,e`.
- Equations 8-10 through 8-14b and Appendix CA8.3.3 are the numerical source basis.
- Section 2.10 supplies the source-specific net-hole addition and 75% net-area requirement.
- Section 8.3.1 and Table 8-1 supply `C_delta`.

The RC1 specification and golden were not edited. Their identities are registered as immutable parent authorities.

---

## 3. Reference-calculation method

The reference calculation used:

```text
Authoritative type:
Decimal

Working precision:
100 decimal digits

Equation-policy target:
60 decimal digits

Benchmark serialization:
12 decimal places, ROUND_HALF_EVEN

Intermediate rounding:
none
```

For Appendix cases with fractional powers, a second 100-decimal-place `mpmath` implementation was used independently from the Decimal implementation.

The maximum observed Decimal-versus-`mpmath` difference among the selected Appendix cross-checks was:

```text
3.3E-99 kip
```

This is far below the 12-decimal benchmark serialization precision.

---

## 4. RC1 regression verification

The independent calculator re-evaluated:

- all five prescriptive cases;
- both more-than-three-row automatic cases;
- the engineer-defined case;
- the single-lap case;
- all five block-shear cases;
- the below-75%-net-area case;
- the U.S./SI block-shear conversions.

Verified quantities included:

- bearing nominal and design resistance;
- simplified first-row nominal and design resistance;
- Appendix `S_pr`, `Theta`, `K_nt`, `K_op`, `A`, `B`, denominator, nominal resistance, and design resistance;
- Equation 8-12/8-13 and rational row-span shear-out;
- block-shear nominal and design resistance;
- converted areas and design resistance.

Result:

```text
Assertions:
136

Discrepancies at 12 decimals:
0
```

---

## 5. New RC2 numerical cases

| Case | Principal expected result |
|---|---|
| `RC2_E1_MAPPING_ASYMMETRIC` | Full-method design `5.998406376749 kip`; Eq. 8-12 design `5.610465000000 kip`; both use unloaded-end `e1 = 1.25 in` |
| `RC2_APPENDIX_BRANCH_BOUNDARY_NB1` | Exact `e1/w = 1` uses the `<= 1` trace branch; `Theta = 1.000000000000` |
| `RC2_APPENDIX_COEFFICIENT_MATRIX_NB1_LBR_050` | L-shape `5.889623934957 kip`; L-plate `6.486627586212 kip`; T-shape/T-plate controlled `1.204695804878 kip` |
| `RC2_CDELTA_REDUCED_PITCH_SCOPE` | Bearing `2.531250000000 kip`; simplified `2.784375000000 kip`; shear-out `5.270973750000 kip`; block shear `10.950946875000 kip` |
| `RC2_FIRST_ROW_SIMPLIFIED_FULL_FACTOR_STACK` | Adjusted `Ft,L = 17.820000000000 ksi`; design `0.721710000000 kip`; utilization `0.831358856050` |
| `RC2_UNKNOWN_LBR_A_EQUALS_B_TIE` | Both endpoints govern; nominal `4.000000000000 kip`; design `2.000000000000 kip` |
| `RC2_BLOCK_SHEAR_SINGLE_LAP_CONCENTRIC` | Design `8.760757500000 kip`; utilization `0.684872284160` |
| `RC2_BLOCK_SHEAR_FULL_FACTOR_STACK` | Adjusted `Fsh = 4.320000000000 ksi`; adjusted `Ft,L = 17.820000000000 ksi`; design `2.838485430000 kip` |
| `RC2_BLOCK_SHEAR_NATIVE_SI_SOURCE` | `A_ns = 1220 mm²`; `A_nt = 344 mm²`; design `32.512500000000 kN`; utilization `0.615148019992` |
| `RC2_BLOCK_SHEAR_ECCENTRICITY_TOLERANCE` | `|e| <= 0.000001 in` concentric; a value just above selects Equation 8-14b |

---

## 6. Representative independent hand checks

### 6.1 Asymmetric Equation 8-12 `e1`

Inputs:

```text
e1 = 1.25 in
dn = 0.563 in
s = 2.00 in
t = 0.375 in
Fsh = 8.00 ksi
phi = 0.45
```

Nominal resistance:

```text
Rsh
= 1.4(1.25 - 0.563/2 + 2.00)(0.375)(8.00)
= 12.467700000000 kip
```

Design resistance:

```text
Rd
= 0.45(12.467700000000)
= 5.610465000000 kip
```

The separate loaded-boundary-to-Row-1 distance is not used.

### 6.2 Full factor stack

```text
Ft,L,adjusted
= 33(0.75)(0.80)(0.90)
= 17.82 ksi
```

```text
Rn,equation
= 0.2(3)(0.375)(17.82)
= 4.0095 kip
```

```text
Rn,connection
= 4.0095(0.60)(0.75)
= 1.804275 kip
```

```text
Rd
= 1.804275(0.50)(0.80)
= 0.721710 kip
```

```text
utilization
= 0.60/0.721710
= 0.831358856050
```

### 6.3 Single-lap block shear

```text
Rn
= 0.5[
(4.82625)(8)
+
(0.7965)(33)
]
= 32.44725 kip
```

```text
Rn,connection
= 32.44725(0.60)
= 19.46835 kip
```

```text
Rd
= 19.46835(0.45)
= 8.7607575 kip
```

### 6.4 Native-SI source hole

```text
d_h*
= 14.0 + 1.6
= 15.6 mm
```

```text
A_ns
= 2(10)[100 - (3 - 0.5)(15.6)]
= 1220 mm²
```

```text
A_nt
= 10(50 - 15.6)
= 344 mm²
```

```text
Rn
= 0.5[
(1220)(55)
+
(344)(225)
]/1000
= 72.25 kN
```

```text
Rd
= 0.45(72.25)
= 32.5125 kN
```

### 6.5 Exact endpoint tie

For `A = B = 2.5`:

```text
R(Lbr)
= 10/[2.5 + (2.5 - 2.5)Lbr]
= 4.0 kip
```

Both `LBR_0` and `LBR_1` are therefore exact co-governing endpoints.

---

## 7. Independent Appendix cross-checks

| Case | Decimal-versus-mpmath absolute difference in design resistance |
|---|---:|
| RC1 longitudinal shape | `3.3E-99 kip` |
| RC2 asymmetric `e1` | `3.3E-99 kip` |
| RC2 branch just below `e1/w = 1` | `2E-99 kip` |
| RC2 exact `e1/w = 1` | `1E-99 kip` |
| RC2 longitudinal plate | `1E-99 kip` |

---

## 8. Status and aggregate verification

The RC2 golden explicitly locks:

- `S_pr <= 1` as invalid geometry;
- zero Appendix denominators as invalid geometry;
- out-of-range `L_br` as invalid input;
- unexpected arithmetic failure as fail-closed `NOT_EVALUATED`;
- zero required checks as `NOT_EVALUATED`, never PASS;
- zero demand against positive resistance as utilization zero and numerical PASS;
- zero or negative design resistance as structured FAIL with no utilization;
- missing required bolt-axis tension as incomplete input with no automatic prying;
- nonuniform pitch as unavailable for automatic `C_delta`;
- source-authorized first-row and shear-out exemptions;
- fully resolved staggered and unequal-row external plans as numerically executable only outside prescriptive scope and with qualification.

The integration cases verify:

1. All numerical checks may pass while an engineer-defined method still returns qualification required.
2. A known numerical failure remains FAIL when Section 2.3.2 qualification is also required.
3. Two FRP layers are evaluated independently and the transverse layer can govern.
4. Force reversal reverses physical row order and changes the fingerprint while retaining nonnegative demand.

---

## 9. Deterministic tie verification

The golden requires:

- exact `A = B` preserves both `LBR_0` and `LBR_1`;
- equal simplified/full lower-envelope branches preserve both method IDs;
- equal block candidates preserve all candidate IDs in stable order;
- results within `1E-12` utilization remain co-governing;
- the co-governing tolerance does not affect PASS/FAIL or exact resistance selection.

---

## 10. Monotonicity verification

| Invariant | Lower result | Higher result | Verified relation |
|---|---:|---:|---|
| Demand versus utilization | `0.296296296296` | `0.592592592593` | higher demand increases utilization |
| Thickness versus resistance | `3.712500000000 kip` | `4.950000000000 kip` | higher thickness increases resistance |
| Hole size versus full-method resistance | `5.889623934957 kip` | `5.836381935644 kip` | larger hole reduces resistance |
| Row fraction versus bearing utilization | `0.740740740741` | `0.888888888889` | higher row fraction increases utilization |

---

## 11. Unit and source-origin verification

The following were independently confirmed:

- RC1 U.S.-source physical values convert to the stored SI values without regenerating the hole.
- The RC2 native-SI case uses `+1.6 mm`, not the converted `+0.063 in` addition.
- The authoritative software `ksi_to_MPa` Decimal is recorded separately from RC1 documentary and serialized representations.
- Display-unit changes remain excluded from engineering fingerprints.

---

## 12. Proposed decisions embedded in RC2

The candidate package proposes the following exact deferred values for owner approval:

```text
Calculation engine:
0.2.0.dev1

Engineering rule set:
asce74-23-ch8-multirow-rc2.dev1

Calculation contract:
2.4B-RC2

Execution-input schema:
frp-master-connection-calculation-slice-2-execution-input
0.1.0-draft

Result schema:
frp-master-connection-calculation-slice-2-result
0.1.0-draft

Fingerprint schema:
frp-master-connection-calculation-slice-2-fingerprint
0.1.0-draft

Block-shear eccentricity tolerance:
0.000001 in
0.0000254 mm
```

These values are not active repository identities until the complete package is approved and implemented.

---

## 13. Limitations of this verification

This ledger verifies the engineering specification and machine-readable benchmark candidate. It does not verify a repository implementation because Stage 2.4B code does not yet exist.

The current block-shear RC1 cases primarily validate resolved path areas and numerical resistance. RC2 adds execution-contract and status coverage, but the future implementation must still prove that accepted Stage 2.4A physical path plans are consumed without reinterpretation.

No claim is made that hosted CI, repository tests, a commit, or a push exists for Stage 2.4B.

---

## 14. Final package integrity audit

A final independent artifact audit was performed after the three candidate files were written.

Results:

```text
RC2 JSON syntax validation:
PASS

Inherited RC1 benchmark sections compared exactly:
12 of 12 unchanged

Machine calculation and consistency assertions:
350

Discrepancies:
0
```

The 350 assertions comprise 267 parent-inheritance, RC1 numerical, factor, utilization, and U.S./SI conversion checks plus 83 RC2 numerical, factor-stack, boundary, tie, and metamorphic checks. This expanded audit supplements the 136 focused RC1 reference-calculation assertions recorded in Section 4.

---

## 15. Approval gate

Owner approval of all three RC2 candidate artifacts will authorize preparation of the Stage 2.4B Codex implementation order.

It will not authorize API, frontend, orchestration, persistence, reporting, authentication, entitlement, billing, deployment, or dependency work.

**END OF RC2 INDEPENDENT VERIFICATION LEDGER**
