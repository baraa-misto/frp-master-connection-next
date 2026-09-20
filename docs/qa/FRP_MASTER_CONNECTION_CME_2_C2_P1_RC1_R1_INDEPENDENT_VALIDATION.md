# FRP Master Connection
# CME-2 C2-P1 RC1 R1 — Independent Benchmark, Native-Conversion, and Final-Source Validation

**Status:** PASS. Independent numerical/contract validation of the approved RC1 R1 benchmark, direct reconciliation against final ANSI/AISC 370-25, and reconciliation to the frozen repository native exact Decimal stress-conversion helper. This is engineering validation evidence for isolated C2-M/C2-P1 implementation, not family activation.

- Benchmark: `FRP_MASTER_CONNECTION_CME_2_C2_P1_GOLDEN_BENCHMARKS_RC1_R1.json`
- Original engineering/contract checks preserved: **61**
- Added exact native stress-conversion checks: **3**
- Total validated checks: **64**
- Result: **PASS**

## Recomputed engineering branches

- Design-thickness boundary (>3/16 in. nominal vs. 0.95 nominal at/below the boundary).
- Gross/net tension and LRFD factors.
- Stainless connecting-element shear yielding with `Cv = 1.2` and shear rupture.
- Uniform and nonuniform block shear.
- Standard-hole bearing/tearout for the service-deformation-considered branch.
- U.S.-source to SI exact force conversions.
- All initial U.S. standard-hole rows: hole-to-net-deduction, `(8/3)d` center spacing, and clear-spacing identity.

## Representative recomputed values

| Check | Recomputed value |
|---|---:|
| 3/16-in nominal conservative design thickness | 0.178125 in |
| 4-in x 3/16-in nominal gross-area tension design resistance | 16.03125 kip |
| 4-in x 3/8-in plate, one 1/2-in standard-hole gross-yield design resistance | 33.75 kip |
| Same section effective-net rupture design resistance | 66.4453125 kip |
| 2-in shear length x 3/8-in plate shear-yield design resistance | 12.15 kip |
| Uniform block-shear design resistance | 43.875 kip |
| Nonuniform block-shear design resistance | 32.0625 kip |
| 1/2-in bolt / 9/16-in hole / l1=1 in connected-material tearout design resistance | 10.9375 kip |
| Same at 3/4-in table minimum edge | 8.203125 kip |
| 33.75 kip exact project conversion | 150.127479515041875 kN |

No expected numerical value was generated from FRP Master Connection production code.


## RC1 R1 numerical-authority correction

The repository native exact Decimal conversion helper is authoritative for stress conversion. No C2-specific conversion is permitted. The earlier RC1 benchmark/specification shortened the exact ksi-to-MPa decimal and is superseded.

Directly recomputed from the repository-native exact helper:

- `1 ksi = 6.89475729316836133672267344534689069378138756277512555025110 MPa`
- `25 ksi = 172.36893232920903341806683613367226734453468906937813875627750 MPa`
- `70 ksi = 482.63301052178529357058714117428234856469712939425878851757700 MPa`

The AISC 360-22 SHA-256 metadata was also corrected from the earlier one-character omission to:

`6B1322440EEDAA0B82D617811DC4B2A2657E7492CF9067CBB3DEBDF9E610ABB7`

A structural comparison of the RC1 and RC1 R1 benchmark JSONs confirms that only these three stress-conversion fields and the AISC 360-22 source-hash metadata changed. All 11 positive cases, 14 negative cases, 11 invariants, strength factors, geometry tables, resistance expected values, and force/length conversions are unchanged.

## Limitation

This PASS validates the approved benchmark arithmetic and internal benchmark consistency. Final ANSI/AISC 370-25 is now directly supplied and reconciled. The final source confirms the RC1 equations, factors, design-thickness rule, U.S. standard-hole/detailing rows, net-hole deduction, effective-net-area basis, bearing/tearout branch, and block-shear classifications used in the benchmark. No benchmark numerical value required revision. C2-M/C2-P1 are ready for controlled isolated-provider implementation.

## Owner-decision and final-source reconciliation

RC1 R1 preserves every engineering case and resistance expected value from RC1. It corrects only exact stress-conversion display/source values to the repository-native helper and one AISC 360-22 source-hash metadata typo. The original 61 independent arithmetic/contract checks remain applicable to the unchanged engineering cases; three additional exact stress-conversion checks were independently recomputed. Final-source reconciliation additionally confirmed the AISC 370-25 provisions used by those checks.

## Final AISC 370-25 source lock

Directly verified against `A370-25W.pdf`, SHA-256:

`A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`

Relevant final provisions verified: A3.1b/Table A3.1f; B4.2a/B4.4b; D3/Table D3.1; J3.2-J3.5; J3.10a; J4.1-J4.3; Commentary Table C-A3.2.

Final disposition: `SL-370-25-FINAL = CLOSED`.
