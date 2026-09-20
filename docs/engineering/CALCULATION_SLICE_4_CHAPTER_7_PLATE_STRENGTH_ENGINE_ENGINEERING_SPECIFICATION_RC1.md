# FRP Master Connection — Calculation Slice 4 — ASCE/SEI 74-23 Chapter 7 Pure-Mode FRP Plate Strength Engine — Engineering Specification RC1

## 1. Status

**Controlled shared calculation authority — RC1**

Calculation Slice 4 implements reusable backend-only plate strength equations from ASCE/SEI 74-23 Chapter 7.

It is a prerequisite for the revised Stage 3.6B rational web-splice plate-body calculation.

It is not a new connection family.

## 2. Accepted starting baseline

Expected repository state:

- branch `main`;
- `HEAD == origin/main == remote main`:
  `80df7524417c752ab3c0f6194348e72aff40767a`;
- subject:
  `feat: add symmetric double web splice connection`;
- commit count:
  `90`;
- clean worktree/index.

Stage 3.6A is accepted.

Stage 3.5 and all earlier frozen families remain protected.

## 3. Source files

Read-only source:

- `ASCE SEI 74-23 Code.pdf`
- `9780784415771.err.pdf`

Required source hash identities remain the currently controlled values.

The erratum does not alter the Chapter 7 equations implemented by this slice.

## 4. Architecture

Create one shared calculation module under the existing calculation layer, using repository conventions.

Suggested conceptual API:

- `plate_longitudinal_tension_strength(...)`;
- `plate_transverse_tension_strength(...)`;
- `plate_longitudinal_compression_strength(...)`;
- `plate_combined_compression_buckling_strength(...)`;
- `plate_in_plane_shear_strength(...)`.

Exact filenames/symbols may follow repository architecture.

Do not create a parallel material-property system.

Do not create frontend engineering calculations.

## 5. Input quantity policy

Use existing Decimal/quantity conventions.

No binary-float engineering arithmetic.

All geometric and material inputs must be finite and physically positive where applicable.

Inputs are already adjusted under existing Section 2.4/property authority.

At minimum:

- `t` plate thickness;
- `b` plate span in material transverse direction;
- `a` plate span in material longitudinal direction where required;
- `Ae` effective net area per unit plate width for tension;
- `F_tL`;
- `F_tT`;
- `F_cL`;
- `F_cT`;
- `F_vLT`;
- `E_L`;
- `E_T`;
- `G_LT`;
- `nu_LT`;
- `lambda_time`.

## 6. Result provenance

Every result shall include:

- equation/method identity;
- nominal resistance;
- design resistance;
- resistance factor;
- time-effect factor;
- adjusted property values used;
- geometry values used;
- governing limit state;
- warnings/applicability;
- deterministic fingerprint/provenance.

No presentation fields.

## 7. Longitudinal plate tension — Equation 7-12

Nominal tensile strength per unit width:

`N_tL,n = 0.7 F_tL Ae`.

Design strength:

`R_tL,d = lambda * 0.65 * N_tL,n`.

Method:

`ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION`.

For an unperforated one-unit-width body strip:

`Ae = t`.

The engine shall not calculate connection-hole effective area itself.

## 8. Transverse plate tension — Equation 7-13

Nominal tensile strength per unit width:

`N_tT,n = 0.85 F_tT Ae`.

Design strength:

`R_tT,d = lambda * 0.65 * N_tT,n`.

Method:

`ASCE74_EQ_7_13_TRANSVERSE_PLATE_TENSION`.

## 9. Longitudinal compression material rupture — Equation 7-15

Nominal:

`N_cL,rupture = F_cL t`.

Method:

`ASCE74_EQ_7_15_LONGITUDINAL_COMPRESSION_RUPTURE`.

## 10. Transverse compression material rupture — Equation 7-16

Nominal:

`N_cT,rupture = F_cT t`.

Method:

`ASCE74_EQ_7_16_TRANSVERSE_COMPRESSION_RUPTURE`.

This is a source result, not by itself a complete pure-transverse-compression stability design.

## 11. Longitudinal compression buckling — Equations 7-17 through 7-19

Nominal buckling strength per unit width:

`N_cL,buckling = F_crL t`.

Use:

`k_cr = 1.0`.

Buckling stress:

`F_crL = (pi^2/6) (t/b)^2 [ (4 k_cr - 3) sqrt(E_L E_T) + k_cr E_T nu_LT + 2 k_cr G_LT ]`.

Methods:

- `ASCE74_EQ_7_17_LONGITUDINAL_PLATE_BUCKLING_STRENGTH`;
- `ASCE74_EQ_7_18_LONGITUDINAL_PLATE_BUCKLING_STRESS`;
- `ASCE74_EQ_7_19_KCR`.

No user-controlled `k_cr`.

## 12. Governing longitudinal compression strength

Nominal longitudinal compression strength:

`N_cL,n = min(N_cL,rupture, N_cL,buckling)`.

Design strength:

`R_cL,d = lambda * 0.70 * N_cL,n`.

Return governing mode:

- `MATERIAL_RUPTURE`;
- `ORTHOTROPIC_PLATE_BUCKLING`.

## 13. Longitudinal compression commentary advisories

Calculate:

- `b/t`;
- `a/b` when `a` is supplied.

Return non-governing advisory flags:

- `C7_6_3_NARROW_PLATE_VALIDATION_CAUTION` when `b/t < 20`;
- `C7_6_3_SHORT_PLATE_CONSERVATIVE_APPROXIMATION` when `a/b <= 4`.

These are provenance/review advisories, not automatic rejection of the normative equation.

## 14. Combined longitudinal/transverse compression buckling — Equations 7-20 through 7-22

For a simply supported rectangular plate with applied compression ratio:

`xi_LT = transverse compression / longitudinal compression`.

Applicability:

`0.3 <= xi_LT <= 1.0`.

Nominal longitudinal buckling strength per unit width:

`N_cL,biax,buckling = F_crL,biax t`.

Use:

`r = b/a`.

`F_crL,biax = (pi^2/12) (t/b)^2 *
[ E_L r^4 + 2(E_T nu_LT + 2 G_LT) r^2 + E_T ] /
[ r^2 + xi_LT ]`.

Methods:

- `ASCE74_EQ_7_20_COMBINED_COMPRESSION_BUCKLING_STRENGTH`;
- `ASCE74_EQ_7_21_COMBINED_COMPRESSION_BUCKLING_STRESS`;
- `ASCE74_EQ_7_22_COMBINED_COMPRESSION_XI_RANGE`.

Outside the permitted ratio:

`SECTION_7_6_4_COMBINED_COMPRESSION = REQUIRES_SECTION_2_3_2`.

Do not extrapolate.

## 15. In-plane shear material rupture — Equation 7-24

Nominal shear strength per unit width:

`N_vLT,rupture = F_vLT t`.

Method:

`ASCE74_EQ_7_24_IN_PLANE_SHEAR_RUPTURE`.

## 16. In-plane shear eta — Equation 7-27

`eta_LT = (2 G_LT + E_T nu_LT) / sqrt(E_L E_T)`.

Method:

`ASCE74_EQ_7_27_SHEAR_BUCKLING_ETA`.

Require:

`eta_LT > 0`.

No tolerance branch logic.

## 17. In-plane shear buckling — Equations 7-25 and 7-26

Nominal buckling strength per unit width:

`N_vLT,buckling = F_crLT t`.

For:

`0 < eta_LT <= 1`:

`F_crLT =
(2.7 + 1.7 eta_LT)
(t/b)^2
(E_L E_T^3)^(1/4)`.

For:

`eta_LT > 1`:

`F_crLT =
(3.9 + 0.47/eta_LT^2)
(t/b)^2
sqrt[ E_T (E_T nu_LT + 2 G_LT) ]`.

Methods:

- `ASCE74_EQ_7_25_IN_PLANE_SHEAR_BUCKLING_STRENGTH`;
- `ASCE74_EQ_7_26_IN_PLANE_SHEAR_BUCKLING_STRESS`.

## 18. Governing in-plane shear strength

Nominal:

`N_vLT,n = min(N_vLT,rupture, N_vLT,buckling)`.

Design:

`R_vLT,d = lambda * 0.70 * N_vLT,n`.

Return governing mode:

- `MATERIAL_RUPTURE`;
- `ORTHOTROPIC_SHEAR_BUCKLING`.

## 19. Shear commentary advisory

When both `a` and `b` are supplied and:

`a < b`,

return:

`C7_7_3_LONG_PLATE_EQUATION_CONSERVATIVE_FOR_A_LT_B`.

Calculation Slice 4 RC1 still uses the normative Equation 7-26 as written.

Do not introduce the commentary axis-swap alternative as another production strength method.

## 20. Pure transverse compression complete-design boundary

Calculation Slice 4 exposes Equation 7-16 material rupture.

If a caller requests a complete pure-transverse compression design resistance including stability, return:

`TRANSVERSE_COMPRESSION_STABILITY = REQUIRES_SECTION_2_3_2`.

Do not rotate/swap axes and present that as a normative pure-transverse buckling equation.

## 21. Time-effect factor

The caller supplies `lambda_time` from the existing factor authority.

Require:

`lambda_time > 0`.

Calculation Slice 4 applies it exactly once to design strength.

Do not hard-code load-duration categories.

## 22. Resistance factors

Locked:

- tension `0.65`;
- compression `0.70`;
- in-plane shear `0.70`.

No user override.

## 23. Property-adjustment boundary

Do not perform environmental/end-use adjustments inside this slice.

The input values are the adjusted characteristic values used in Chapter 7 equations.

Provenance must identify the caller/property record.

## 24. Test-only controlled property fixture

Use the following test-only adjusted properties for arithmetic benchmarks:

- `t = 0.5 in`;
- `a = 24 in`;
- `b = 12 in`;
- `Ae = 0.5 in^2/in`;
- `F_tL = 30 ksi`;
- `F_tT = 10 ksi`;
- `F_cL = 25 ksi`;
- `F_cT = 12 ksi`;
- `F_vLT = 8 ksi`;
- `E_L = 2500 ksi`;
- `E_T = 1200 ksi`;
- `G_LT = 500 ksi`;
- `nu_LT = 0.3`;
- `lambda = 1.0`.

These are benchmark values only, not production material defaults.

## 25. Controlled benchmark — tension

Expected:

Longitudinal nominal:

`10.50 kip/in`.

Longitudinal design:

`6.8250 kip/in`.

Transverse nominal:

`4.250 kip/in`.

Transverse design:

`2.76250 kip/in`.

## 26. Controlled benchmark — longitudinal compression

Expected longitudinal buckling stress:

`8.83024255172850024200170156575662986972001339994848039924152 ksi`.

Buckling nominal:

`4.41512127586425012100085078287831493486000669997424019962076 kip/in`.

Material-rupture nominal:

`12.5 kip/in`.

Governing:

`ORTHOTROPIC_PLATE_BUCKLING`.

Design:

`3.09058489310497508470059554801482045440200468998196813973453 kip/in`.

## 27. Controlled benchmark — transverse compression rupture reference

Nominal:

`6.0 kip/in`.

Material-rupture design reference:

`4.200 kip/in`.

Complete transverse compression stability:

`REQUIRES_SECTION_2_3_2`.

## 28. Controlled benchmark — combined compression buckling

For:

- `a=24 in`;
- `b=12 in`;
- `xi_LT=0.5`;

Expected buckling stress:

`3.87673263150428365887379095264232499021653557445873069310072 ksi`.

Nominal buckling strength:

`1.93836631575214182943689547632116249510826778722936534655036 kip/in`.

Design buckling reference:

`1.35685642102649928060582683342481374657578745106055574258525 kip/in`.

## 29. Controlled benchmark — shear

Expected:

`eta_LT =
0.785196366097891039732442341482662139680738381727372551385298`.

Buckling stress:

`10.0989007942906052338660699950449888538294409035305580120792 ksi`.

Buckling nominal:

`5.04945039714530261693303499752249442691472045176527900603960 kip/in`.

Rupture nominal:

`4.0 kip/in`.

Governing:

`MATERIAL_RUPTURE`.

Design:

`2.800 kip/in`.

## 30. Eta greater-than-one branch benchmark

Use same fixture except:

`G_LT = 1000 ksi`.

Expected:

`eta_LT =
1.36254663528751680424159112198461959532834013299749942740390`.

Expected shear-buckling stress:

`12.1339668708477341328176138381088695405829988347944168747123 ksi`.

This directly proves the `eta_LT > 1` branch.

## 31. Stage 3.6B representative narrow-plate advisory

For:

- `t=0.5 in`;
- `b=8 in`;

return:

`b/t=16`

and advisory:

`C7_6_3_NARROW_PLATE_VALIDATION_CAUTION`.

The normative longitudinal buckling stress remains calculable:

`19.8680457413891255445038285229524172068700301498840808982934 ksi`.

Do not convert the advisory to a fake capacity increase/decrease.

## 32. Invalid inputs

Reject:

- `t <= 0`;
- `b <= 0`;
- `a <= 0` when required;
- `Ae < 0`;
- nonpositive moduli;
- nonpositive required strength properties;
- invalid/nonfinite Poisson ratio under repository conventions;
- `lambda <= 0`;
- `eta <= 0`;
- combined-compression `xi` outside source range for Equation 7-21.

## 33. U.S./SI equivalence

Equivalent physical inputs shall produce identical:

- nominal strength;
- design strength;
- governing mode;
- buckling stress;
- eta;
- applicability/advisories;
- fingerprints.

No unit-specific formula branching.

## 34. Deterministic fingerprints

Create deterministic method/result fingerprints including:

- equation identity;
- geometry;
- adjusted property provenance;
- lambda;
- resistance factor;
- nominal/design result;
- governing mode;
- applicability/advisories.

Presentation excluded.

## 35. No frontend production

Expected frontend production changes:

`0`.

If frontend production changes are proposed:

**STOP and explain why a backend calculation prerequisite requires them.**

## 36. Historical/frozen invariance

Require exact:

- Stage 3.6A request/result/fingerprint behavior;
- Stage 3.5 frozen family;
- Stage 3.4 frozen family;
- Stage 3.3 frozen family;
- Stage 3.2 frozen family;
- Stage 2.3 frozen interface.

No freeze tag moves.

## 37. Acceptance boundary

Calculation Slice 4 is accepted only if:

- every normative equation listed above is implemented byte-for-byte in engineering meaning;
- Decimal exactness is retained;
- Section 2.4 adjustment is not duplicated;
- resistance/time factors are applied exactly once;
- both shear-buckling branches are tested;
- governing rupture/buckling selection is tested;
- combined-compression xi range fails closed;
- transverse-compression stability is not invented;
- commentary advisories do not alter the normative equation;
- full local/object-isolated QA passes;
- hosted CI 4/4 passes;
- Stage 3.6A and all frozen families remain exact.

**END OF CALCULATION SLICE 4 CHAPTER 7 PLATE STRENGTH ENGINE SPECIFICATION RC1**
