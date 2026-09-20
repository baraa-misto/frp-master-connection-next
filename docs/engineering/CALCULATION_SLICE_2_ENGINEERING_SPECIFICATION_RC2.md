# FRP Master Connection
# Calculation Slice 2 Engineering Specification — RC2

**Document status:** Candidate engineering specification pending Baraa Misto approval  
**Implementation status:** Stage 2.4B implementation is not authorized by this document alone  
**Calculation family:** General bolt-group and multi-row pultruded-FRP bolted-connection numerical engine  
**Primary standard:** ASCE/SEI 74-23  
**Correction set:** Erratum 1, effective January 13, 2026  
**Erratum effect on this slice:** None; Erratum 1 changes Chapter 5, not Chapter 8  
**Parent planning authority:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1.md`  
**Parent planning SHA-256:** `44431A8921CF1ADF9C7D0F7F022C9615265308A41BE589B1EE5150A7D7886F99`  
**Parent golden SHA-256:** `C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610`  
**Companion RC2 benchmark candidate:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_GOLDEN_BENCHMARKS_RC2.json`  
**Companion RC2 benchmark SHA-256:** `B3A49FB44089E065F7B4659F52AB856288298247504423970C3D19B8FCEA7B0B`

---

## 1. Purpose and approval boundary

This RC2 candidate defines the engineering and software contract for Stage 2.4B: a framework-independent backend numerical engine that consumes the accepted Stage 2.4A multi-row calculation plans through a complete, typed, deeply immutable execution bundle.

RC2 preserves RC1 as the accepted Stage 2.4A planning and regression authority. RC2 does not alter the RC1 file or the RC1 golden. RC2 adds the executable numerical contract, including:

1. Exact engine inputs and outputs.
2. New Slice 2 version identities.
3. Decimal precision and conversion authority.
4. Correct ASCE `e1` mapping.
5. Typed factor carriage and application order.
6. First-row, inter-row, block-shear, bearing, and reused per-bolt numerical execution.
7. Numerical-domain behavior.
8. Required-check membership and fail-closed aggregate status.
9. Eccentricity classification.
10. Multi-layer evaluation.
11. Deterministic governing and co-governing results.
12. Expanded benchmark and regression requirements.

This document is not a Codex implementation order. It becomes an implementation authority only after Baraa Misto approves this RC2 specification, the companion RC2 golden, and the independent verification ledger.

---

## 2. Controlling source hierarchy

Use the following hierarchy:

1. ASCE/SEI 74-23, including Chapter 2, Section 2.9, Section 2.10, Chapter 8, Commentary Chapter C8, and Appendix CA8.3.3.
2. Erratum 1, effective January 13, 2026.
3. Approved Calculation Slice 2 RC1 planning specification.
4. Approved Calculation Slice 2 RC1 golden.
5. The approved Phase 2 D1–D18 decision docket.
6. This RC2 specification after approval.
7. The companion RC2 golden after approval.
8. Accepted repository behavior where it does not conflict with a higher authority.

Use concise source locators. Do not reproduce licensed standards text in repository documents.

### 2.1 Direct source-derived provisions

The direct source basis includes:

- Design strength and time-effect treatment: Sections 2.3.1 and 2.4.
- Connection-force consistency and eccentricity: Section 2.9.
- Net-area deductions and the 75% requirement: Section 2.10.
- Chapter 8 scope and Section 2.3.2 qualification outside covered configurations: Section 8.1.
- Detailing limits: Sections 8.2.2 through 8.2.5 and Table 8-1.
- Pitch factor `C_delta`: Section 8.3.1.
- Reused bolt, pull-through, and pin-bearing checks: Sections 8.3.2.1 through 8.3.2.3.
- Multi-row single-lap multiplier and source-authorized check exemptions: Section 8.3.3 introduction.
- Simplified first-row net tension: Equations 8-10 and 8-11.
- Inter-row shear-out: Equations 8-12 and 8-13.
- Block shear: Equations 8-14a and 8-14b.
- Prescribed row distributions: Commentary Table C8-1.
- Full first-row method: Appendix CA8.3.3.
- Limited eccentric block-shear test basis: Commentary C8.3.3.3.

### 2.2 Approved project rational extensions

The following remain approved rational extensions and shall be labeled as such:

- General geometry with any positive row and bolt count.
- Conservative full-row demand envelope.
- Unknown-`L_br` endpoint envelope.
- More-than-three-row lower envelope.
- Equation 8-13 actual-row-span extension.
- Automatic L/U block-path resolver.
- Shared-corner half-hole allocation.
- Numerical use of raw net area below 75%, with ordinary PASS prohibited.
- Controlled transverse-plate Appendix coefficient `C_i = 0.50`.
- Execution of fully resolved external staggered or unequal-row plans with provenance and qualification.
- General geometry/result trace and deterministic fingerprint conventions beyond the text of the standard.

A rational extension shall never be reported as an ordinary ASCE-prescriptive method.

### 2.3 Project software conventions

The following are software conventions, not direct standard provisions:

- Exact 90 degrees selects the transverse property family.
- Exact branch-boundary trace selection.
- Decimal precision and serialization policy.
- Co-governing utilization tolerance.
- Block-shear concentric/eccentric classification tolerance.
- Deep immutability and canonical fingerprint representation.
- Deterministic candidate ordering and stable IDs.
- Exact aggregate result encoding.

---

## 3. Accepted repository and freeze baseline

The RC2 package is prepared against:

```text
Repository:
C:\Users\green\Documents\New project\frp-master-connection

Branch:
main

HEAD and origin/main:
41f698dce1c96b11890c4b349cc62b68cc753b7a

Commit subject:
fix: correct Stage 2.4A freeze audit and row distributions

Commit count:
30

Tracked files:
239
```

The immutable Stage 2.3 freeze remains:

```text
Tag:
stage-2.3-interface-geometry-freeze

Target:
5bc545ab8251f9bd49dedc776962937ed5e822a2
```

Stage 2.4B is a compatible backend calculation-layer extension. It shall not modify frozen Stage 2.3 frontend production source or frozen preview/design interaction behavior.

---

## 4. Stage 2.4B software boundary

Stage 2.4B is a framework-independent calculation-layer numerical engine.

It may:

- consume accepted Stage 2.4A geometry, applicability, demand, first-row, shear-out, and block-area plans;
- perform the approved narrow contract hardening needed for complete immutable execution input;
- reuse existing Slice 1 equation, quantity, Decimal, factor, result, comparison, trace, and governing utilities where engineering meaning is unchanged;
- calculate nominal resistance, connection-adjusted nominal resistance, design resistance, demand, utilization, numerical comparison, governing cases, warnings, qualification, and fingerprints;
- return pure calculation-layer contracts.

It shall not include:

- application orchestration for multi-row designs;
- public API exposure;
- frontend controls or results;
- preview changes;
- persistence;
- reporting;
- authentication;
- authorization;
- entitlements;
- billing;
- deployment changes;
- general six-component member-end-action-to-bolt-group analysis;
- friction or slip transfer;
- automatic prying generation;
- dependency or lockfile changes;
- changes to existing Slice 1 equations, results, versions, or golden benchmarks.

No application, API, preview, or frontend production path is required to consume the Stage 2.4B engine during this stage.

---

## 5. Proposed Slice 2 version identities

The following exact identities are proposed for approval:

```text
calculation_contract_version:
2.4B-RC2

calculation_engine_version:
0.2.0.dev1

engineering_rule_set_version:
asce74-23-ch8-multirow-rc2.dev1

execution_input_schema:
frp-master-connection-calculation-slice-2-execution-input
0.1.0-draft

result_schema:
frp-master-connection-calculation-slice-2-result
0.1.0-draft

fingerprint_schema:
frp-master-connection-calculation-slice-2-fingerprint
0.1.0-draft

golden_schema:
frp-master-connection-calculation-slice-2-golden-rc2
```

Before Stage 2.4B implementation is accepted, Slice 2 results and fingerprints shall carry these identities.

Existing Slice 1 results retain:

```text
calculation_engine_version:
0.1.0.dev1

engineering_rule_set_version:
asce74-23-ch8-single-bolt-rc2.dev1
```

Stage 2.4B shall not rewrite or re-fingerprint accepted Slice 1 results merely because Slice 2 is added.

---

## 6. Terminology

Use distinct terms:

- `row_count`, `N_r`: number of rows along the signed in-plane force direction.
- `bolts_per_row`, `N_b`: bolts across a row.
- `pitch`, `s`: spacing between adjacent rows.
- `gauge`, `g`: spacing across a row.
- `Row 1`: row farthest from the unloaded free end.
- `Row N_r`: row nearest the unloaded free end.
- `bolt line`: bolts aligned along the force direction.
- `unloaded_end_e1`: source-authoritative distance from the unloaded free end to the nearest row.
- `row_1_to_unloaded_end_distance`: distance from Row 1 to the unloaded free end.
- `loaded_boundary_to_row_1_distance`: a separate physical distance that is not ASCE `e1`.
- `L_br`: proportion of total in-plane force transferred in bearing at Row 1.
- `bypass fraction`: `1 - L_br`.
- `equation_nominal_resistance`: resistance produced by the equation using adjusted material properties.
- `connection_adjusted_nominal_resistance`: equation nominal resistance after applicable `C_lap` and `C_delta`.
- `design_resistance`: `lambda × phi × connection_adjusted_nominal_resistance`.
- `method_applicability`: source or project method classification.
- `qualification`: independent qualification disposition.
- `numerical_comparison`: `PASS`, `FAIL`, or `NOT_EVALUATED`.
- `overall_disposition`: fail-closed whole-result disposition derived from all independent axes.

Do not use one ambiguous `e1` field for loaded-boundary and unloaded-free-end distances.

---

## 7. Execution-input contract

### 7.1 Execution bundle

The engine shall consume one typed immutable execution bundle containing, at minimum:

1. Execution-input schema identity and version.
2. One `MultiRowCalculationPlanSet` or repository-equivalent planning root.
3. Complete block-shear path and area plans, not only path IDs.
4. Ordered layer execution contexts.
5. Ordered bolt and bolt-line execution contexts.
6. Signed demand context and nonnegative comparison magnitudes.
7. Typed factor context.
8. Required-check contract.
9. Source and method provenance.
10. Version context.
11. Fingerprint metadata.
12. Eccentricity data and tolerance where block shear may apply.

Repository-consistent production names are permitted, but every semantic field above is mandatory.

### 7.2 Deep immutability

The execution bundle and every fingerprinted nested value shall be deeply immutable or converted to a canonical immutable representation before execution and hashing.

Prohibited authoritative payloads include:

- mutable lists;
- mutable dictionaries;
- unconstrained `object` payloads;
- binary floats;
- runtime-dependent iteration order;
- timestamps;
- random IDs;
- display state.

Use frozen/slotted dataclasses, tuples, controlled enums, exact Decimals, immutable mappings, or equivalent mechanisms.

Direct construction shall validate tuple members and nested contract types. A frozen outer dataclass containing mutable nested state does not satisfy this requirement.

### 7.3 Narrow Stage 2.4A contract hardening

Stage 2.4B may add a backward-compatible hardened execution wrapper or strengthen validation of existing planning contracts when needed to satisfy this section.

It shall not redesign:

- physical row meaning;
- approved distributions;
- demand-method meaning;
- block-path geometry meaning;
- applicability classifications;
- source locators.

If a required correction changes approved Stage 2.4A engineering meaning, implementation shall stop for a separately controlled correction.

---

## 8. Result contract

### 8.1 Per-check result

Each numerical check result shall retain, at minimum:

- stable result ID;
- source plan ID;
- layer ID where applicable;
- bolt, row, bolt-line, or block-path ID where applicable;
- limit-state identity;
- equation or method identity;
- source locator;
- method applicability;
- qualification;
- availability;
- geometry status;
- equation nominal resistance;
- connection-adjusted nominal resistance;
- design resistance;
- nonnegative comparison demand;
- utilization, when defined;
- numerical comparison;
- factor trace;
- equation trace;
- warning IDs and structured trace;
- engine, rule-set, contract, and result-schema identities;
- input fingerprint.

### 8.2 Aggregate result

The aggregate Slice 2 result shall retain:

- ordered per-check results;
- complete required-check IDs;
- calculated, not-applicable, incomplete, unsupported, and failed check IDs;
- governing and co-governing result IDs;
- geometry status;
- availability;
- method applicability;
- qualification;
- numerical comparison;
- overall disposition;
- structured warnings;
- result fingerprint;
- source and version metadata.

A known failure, qualification requirement, unsupported check, or code-geometry issue shall not erase any other axis.

---

## 9. Decimal, precision, and unit policy

Use exact `Decimal` values for authoritative calculation inputs and outputs.

Required policy:

```text
Quantity conversion precision:
100 decimal digits

Equation evaluation precision:
60 decimal digits

Benchmark serialization:
12 decimal places

Benchmark serialization rounding:
ROUND_HALF_EVEN

Intermediate engineering rounding:
prohibited
```

Binary floats shall not be authoritative calculation inputs. Booleans are not numeric inputs. NaN and infinity are rejected.

### 9.1 Authoritative conversions

Use:

```text
1 in = 25.4 mm

1 kip = 4.4482216152605 kN

1 ksi =
6.89475729316836133672267344534689069378138756277512555025110 MPa

1 in² = 645.16 mm²
```

The long production Decimal is the authoritative software calculation representation.

The unchanged RC1 specification value `6.8947572931683613367` and RC1 golden value `6.8947572931683613` remain controlled documentary and serialized representations. Neither RC1 artifact shall be edited.

The source representation that created an ordinary hole remains authoritative. A U.S.-source hole uses `+0.063 in`; an SI-source hole uses `+1.6 mm`. Display-unit switching converts stored physical values and shall not recreate the hole.

---

## 10. Physical geometry and ASCE `e1`

Commentary C8.2.5 defines source `e1` from the unloaded free end to the row nearest that end.

Therefore:

```text
unloaded_end_e1 =
distance from unloaded free end
to Row N_r
```

For a group with pitches `s_i`:

```text
row_1_to_unloaded_end_distance =
unloaded_end_e1 + sum(s_i)
```

The following are distinct:

- `unloaded_end_e1`;
- `row_1_to_unloaded_end_distance`;
- `loaded_boundary_to_row_1_distance`.

Appendix CA8.3.3 and Equation 8-12 shall use `unloaded_end_e1`.

A field derived from the loaded boundary and Row 1 shall not be passed into those equations unless its semantic identity has independently been proven to be the same source quantity.

The planning layer shall provide explicit source geometry IDs for the unloaded free end, nearest row, Row 1, pitches, and side boundaries.

An asymmetric benchmark shall prove that loaded-end and unloaded-end distances cannot be interchanged.

---

## 11. Geometry scope and source applicability

The canonical geometry model continues to support:

- `N_r >= 1`;
- `N_b >= 1`;
- explicit bolt coordinates;
- explicit rows and bolt lines;
- arbitrary positive future row/bolt counts;
- physical free ends and side boundaries;
- round holes;
- per-layer material axes;
- per-bolt penetrated-layer stacks.

Direct automatic source methods require their individual prerequisites.

### 11.1 Simplified first-row source limits

Equations 8-10 and 8-11 require:

- two or three rows;
- one to three bolts across the effective width;
- nonstaggered geometry;
- constant pitch and gauge where required;
- `g/d <= 5`;
- `e2_max <= 2 e2_min`;
- `e1 <= 2 e1_min`;
- valid material direction;
- applicable Chapter 8 detailing;
- constant bolt, hole, and relevant FRP thickness properties.

Use the actual source-authoritative `e1`.

### 11.2 General geometry outside source scope

More than three rows or more than three bolts in the applicable line does not make physical geometry invalid.

Such configurations may proceed only under the approved availability, method, and qualification rules. They shall not receive ordinary prescriptive PASS.

---

## 12. Signed demand and row distribution

The engine consumes an explicitly resolved signed in-plane resultant for each checked load combination and layer/load path.

The signed vector controls:

- loaded and unloaded ends;
- physical row order;
- path orientation;
- result trace;
- fingerprint.

A nonnegative magnitude controls resistance comparison and utilization.

Force reversal shall rebuild physical row ordering and change the fingerprint, but shall not create negative demand or utilization.

### 12.1 Prescribed distributions

For equal bolts per row:

| Material pair | Rows | Fractions from Row 1 toward the unloaded free end |
|---|---:|---|
| FRP/FRP | 2 | `0.50, 0.50` |
| FRP/steel | 2 | `0.60, 0.40` |
| FRP/FRP | 3 | `0.40, 0.20, 0.40` |
| FRP/steel | 3 | `0.50, 0.30, 0.20` |

These exact Decimal values shall sum exactly to one.

For row `j` with `N_b,j` identical bolts:

```text
V_u,bolt,j = p_j V_u,total / N_b,j
```

### 12.2 Conservative full-row envelope

For each physical row, evaluate one scenario with:

```text
row demand = V_u,total

per-bolt demand =
V_u,total / bolts in that row
```

No row-sharing or friction credit is permitted.

### 12.3 Engineer-defined demand

Engineer-defined fractions or direct row forces require complete provenance and engineer confirmation.

They remain:

```text
ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE
```

even if geometry is otherwise prescriptive and all numerical checks pass.

### 12.4 Bolt-line demand

Equal division among physical bolt lines is permitted only for equivalent parallel lines in the approved rectangular benchmark family or when an explicit selected method establishes it.

Do not equal-share nonuniform, staggered, eccentric, or unresolved lines silently.

---

## 13. Directional FRP properties and penetrated layers

Each penetrated FRP layer shall be evaluated independently.

Each layer retains:

- layer ID;
- component ID;
- material ID;
- thickness;
- LW/CW/TT axes;
- material angle;
- shape/plate identity;
- directional strengths;
- end-use factors;
- source and qualification;
- geometry and path IDs;
- warnings and results.

Use:

- `F_t,L` for longitudinal first-row net tension and block-shear tension;
- `F_t,T` for transverse first-row net tension;
- `F_sh` for inter-row shear-out and block-shear shear planes;
- `F_br,L` or `F_br,T` for bearing;
- accepted through-thickness properties for pull-through under the existing Slice 1 authority.

The engine consumes the Stage 2.4A resolved material direction. It shall not independently reclassify display orientation.

Approved direction boundaries:

```text
0° <= angle <= 5°:
LONGITUDINAL

5° < angle <= 90°:
TRANSVERSE
```

Exactly 90 degrees is an accepted project endpoint interpretation and remains in the trace.

Block shear is supported automatically only for the longitudinal family.

Bolt-body checks are evaluated once per bolt, not once per FRP layer. FRP checks remain layer-specific. Governing and co-governing results may occur in different layers and shall remain visible.

---

## 14. Factor model and trace

### 14.1 Typed factor identities

Use distinct software identities equivalent to:

- `time_effect_factor_lambda`;
- `resistance_factor_phi`;
- `lap_factor_c_lap`;
- `pitch_factor_c_delta`;
- `moisture_factor_c_m`;
- `temperature_factor_c_temperature`;
- `chemical_factor_c_ch`;
- `appendix_coefficient_c_i`;
- `appendix_open_hole_coefficient_c_op_i`.

Do not use one ambiguous `C_T` software field for both temperature adjustment and the Appendix transverse coefficient.

### 14.2 Calculation sequence

For each applicable FRP property:

```text
F_adjusted =
F_reference
× C_M
× C_temperature
× C_CH
```

Use `F_adjusted` in the governing equation:

```text
R_n,equation =
equation(geometry, F_adjusted)
```

Then:

```text
R_n,connection =
R_n,equation
× C_lap
× C_delta
```

Finally:

```text
R_d =
lambda
× phi
× R_n,connection
```

Every factor shall be applied exactly once.

The trace shall retain:

- reference property;
- every end-use factor;
- adjusted property;
- equation nominal resistance;
- `C_lap`;
- `C_delta`;
- connection-adjusted nominal resistance;
- `phi`;
- `lambda`;
- final design resistance.

For block shear, adjust `F_sh` and `F_t,L` independently, combine them in Equation 8-14a or 8-14b, then apply `C_lap` and `C_delta` once to the combined equation result.

### 14.3 Reused Slice 1 behavior

Existing Slice 1 factor behavior remains authoritative for:

- metallic bolt strength;
- pull-through;
- pin bearing;
- bolt interaction.

`C_lap` and `C_delta` do not apply to metallic bolt strength or pull-through.

---

## 15. Reused per-bolt checks

Reuse the accepted Stage 2.1B equation authority without changing existing results for:

- bolt tensile rupture;
- bolt shear rupture;
- combined bolt tension/shear;
- pull-through;
- pin bearing.

The multi-row engine supplies resolved per-bolt demands and layer contexts.

No friction transfer is credited.

Pull-through and bolt-axis tension require explicit per-bolt bolt-axis demand. The engine shall not generate prying demand.

If bolt-axis demand is required but missing:

- bolt tension is `INCOMPLETE_INPUT`;
- pull-through is `INCOMPLETE_INPUT`;
- automatic prying remains absent;
- ordinary PASS is prohibited unless another source-authorized rule makes those checks not required.

---

## 16. Simplified first-row net tension

### 16.1 Longitudinal

```text
R_nt,f,L =
0.2 w t F_t,L

phi = 0.50
```

### 16.2 Transverse

```text
R_nt,f,T =
0.2 w t F_t,T

phi = 0.45
```

### 16.3 Effective width

For one bolt across the row:

```text
w = e3 + e4
```

For two or three bolts:

```text
w =
e3 + e4 + (N_b - 1)g
```

Use resolved raw and effective side distances from the accepted geometry mapping. The numerical engine shall not recalculate or silently clamp `e3`, `e4`, or `w`.

---

## 17. Appendix CA8.3.3 full first-row method

Define:

```text
A =
K_nt,i [w / (N_b d)]

B =
K_op,i /
[1 - N_b d_n / w]
```

Then:

```text
R_nt,f,i =
w t F_t,i /
[A L_br + B(1 - L_br)]
```

Use:

```text
phi = 0.50 for longitudinal

phi = 0.45 for transverse
```

### 17.1 One bolt across each row

```text
S_pr = w/d
```

```text
K_nt,i =
{
1 + C_i[
S_pr
- 1.5((S_pr - 1)/(S_pr + 1))^Theta
]
}
/
(w/d - 1)
```

```text
Theta =
1.5 - 0.5(w/e1)
when e1/w <= 1

Theta = 1
when e1/w > 1
```

### 17.2 Two or three bolts across each row

```text
S_pr = g/d
```

```text
K_nt,i =
{
1 + C_i[
S_pr
- 1.5((S_pr - 1)/(S_pr + 1))^Theta
]
}
/
[w/(N_b d) - 1]
```

```text
Theta =
1.5 - 0.5(g/e1)
when e1/g <= 1

Theta = 1
when e1/g > 1
```

For both:

```text
K_op,i =
1 + C_op,i[
1 + (1 - 1/S_pr)^3
]
```

### 17.3 Coefficients

| Direction | Element | `C_i` | `C_op,i` |
|---|---|---:|---:|
| Longitudinal | Shape | `0.50` | `0.50` |
| Longitudinal | Plate | `0.40` | `0.50` |
| Transverse | Shape | `0.50` | `0.50` |
| Transverse | Plate | controlled `0.50` | `0.50` |

The transverse plate result retains:

```text
ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION
```

and both source locators.

The printed `0.40` alternative is retained only as source-conflict trace and benchmark comparison. It is not an ordinary selectable production value.

---

## 18. Full-method numerical domains

Before execution, require all applicable values to be finite and:

```text
w > 0
d > 0
d_n > 0
t > 0
e1 > 0
S_pr > 1
w > N_b d
w > N_b d_n
0 <= L_br <= 1
```

Require:

```text
w/(N_b d) - 1 > 0

1 - N_b d_n/w > 0

A > 0

B > 0

A L_br + B(1 - L_br) > 0
```

No intermediate value may be NaN or infinite.

Disposition:

- nonphysical geometry or nonpositive clear/net width: `INVALID_GEOMETRY`;
- missing required value: `INCOMPLETE_INPUT`;
- unsupported method: `CALCULATION_NOT_SUPPORTED`;
- invalid engineer-defined value: invalid input; do not build an executable plan;
- unexpected arithmetic failure after validated inputs: `CALCULATION_NOT_SUPPORTED`, numerical `NOT_EVALUATED`, warning `NUMERICAL_DOMAIN_ERROR`.

Do not clamp, take absolute values, inject epsilons, or fall back to another equation.

At exact `e1/w = 1` or `e1/g = 1`, use the `<= 1` trace branch. Both mathematical branches produce `Theta = 1`.

---

## 19. Unknown-`L_br` and more-than-three-row envelopes

For:

```text
R(L_br) =
w t F_t /
[B + (A - B)L_br]
```

with:

```text
0 <= L_br <= 1
```

the minimum resistance occurs at an endpoint:

```text
R_env =
w t F_t /
max(A, B)
```

Retain:

- `A`;
- `B`;
- `LBR_0` result;
- `LBR_1` result;
- controlling endpoint IDs;
- nominal and design envelope resistance.

If `A = B` exactly, retain both endpoints as co-governing.

For more than three rows:

```text
R_auto =
min(
R_simplified_extension,
R_CA8_endpoint_envelope
)
```

Use exact Decimal resistance for selection.

If both branches are exactly equal, retain both method IDs as co-governing.

This is:

```text
RATIONAL_MULTIROW_LOWER_ENVELOPE
```

and requires Section 2.3.2 qualification.

---

## 20. Inter-row shear-out

### 20.1 Two rows — Equation 8-12

```text
R_sh =
1.4(
e1 - d_n/2 + s
)t F_sh

phi = 0.45
```

This is resistance per bolt line.

`e1` is `unloaded_end_e1`.

### 20.2 Three rows — Equation 8-13

```text
R_sh =
2[(N_r - 1)s]tF_sh

N_r = 3

phi = 0.45
```

This is resistance per bolt line.

### 20.3 More than three rows

Define:

```text
L_rows =
sum of physical pitches
from Row 1 to Row N_r
```

Use:

```text
R_sh,ext =
2 L_rows t F_sh

phi = 0.45
```

This is:

```text
RATIONAL_EXTENSION_EQ_8_13
```

and requires Section 2.3.2 qualification.

### 20.4 Bolt-line demand

Check each physical bolt line separately.

For equivalent rectangular lines, equal line demand may be used when the selected demand method authorizes it.

For nonuniform lines, use explicit resolved line demands or return incomplete/unsupported. Do not use an average or silent equal share.

### 20.5 Source-authorized exemption

Inter-row shear-out need not be a required check when the accepted source condition for a perpendicular FRP end element is satisfied and traced.

---

## 21. Pitch factor `C_delta`

For constant pitch:

```text
s_min = 4d
```

```text
C_delta =
min(1, s/s_min)
```

Apply `C_delta` exactly once to:

- pin bearing;
- simplified first-row net tension;
- full first-row net tension;
- inter-row shear-out;
- concentric block shear;
- eccentric block shear.

Do not apply `C_delta` to:

- metallic bolt strength;
- combined metallic bolt strength;
- pull-through.

When `s < s_min` and all other source requirements are satisfied:

- the numerical method may remain `ASCE_PRESCRIPTIVE`;
- apply the reduced resistance;
- retain warning `REDUCED_PITCH_FACTOR_APPLIED`;
- retain `s`, `s_min`, and `C_delta` in trace.

For nonuniform pitch:

- do not compute an average, minimum, or blended automatic `C_delta`;
- direct prescriptive execution is unavailable;
- an engineer-defined factor may execute only with provenance and confirmation;
- the method remains outside prescriptive scope.

---

## 22. Block-shear resistance

### 22.1 Concentric longitudinal tension — Equation 8-14a

```text
R_bs =
0.5(
A_ns F_sh
+
A_nt F_t,L
)

phi = 0.45
```

### 22.2 Eccentric in-plane tension — Equation 8-14b

```text
R_bs,e =
0.5(
A_ns F_sh
+
0.5 A_nt F_t,L
)

phi = 0.45
```

Retain warning:

```text
LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS
```

### 22.3 Applicability

- longitudinal tension: calculable;
- compression: `NOT_APPLICABLE`;
- material angle greater than 5 degrees: `CALCULATION_NOT_SUPPORTED`;
- eccentric: Equation 8-14b with qualification and warning;
- staggered: automatic RC1 path planning unsupported; fully resolved external execution may proceed under Section 2.3.2 qualification;
- more than three rows: numerical calculation may proceed with qualification.

---

## 23. Block-shear eccentricity classification

The planning layer provides:

- signed physical eccentricity;
- geometric reference;
- tolerance;
- source geometry IDs;
- classification.

Use the proposed default:

```text
block_shear_eccentricity_tolerance =
0.000001 in
=
0.0000254 mm
```

This is a numerical geometry-classification tolerance, not a fabrication allowance.

The planning layer shall copy the exact canonical geometry distance tolerance into the separately named eccentricity field. The value is fingerprinted.

Classification:

```text
abs(eccentricity) <= tolerance:
CONCENTRIC

abs(eccentricity) > tolerance:
ECCENTRIC
```

Consequences:

- `CONCENTRIC` selects Equation 8-14a;
- `ECCENTRIC` selects Equation 8-14b;
- missing eccentricity, reference, or tolerance is `INCOMPLETE_INPUT`;
- no silent assumption of concentricity;
- no rendered arrow or screen coordinate has engineering authority.

---

## 24. Block-path and net-area contract

The accepted L/U path resolver remains a project rational extension.

Each candidate retains:

- candidate ID;
- path family;
- row ID;
- physical segments;
- boundaries;
- holes;
- gross and net lengths;
- gross and net areas;
- full deductions;
- shared half deductions;
- rejection reasons;
- path status;
- source and method classification.

A valid path shall create complete separation against real physical free boundaries.

Reject candidates with:

- bridging bolts;
- no closure;
- void crossing;
- boundary crossing;
- deferred heel/junction/corner;
- intermediate-row termination;
- self-intersection;
- nonpositive raw net length or area.

### 24.1 Net-hole deduction

Use:

```text
d_h* =
d_n + 0.063 in
for a U.S.-source hole
```

or:

```text
d_h* =
d_n + 1.6 mm
for an SI-source hole
```

This affects net area only.

### 24.2 Shared corner

A shared corner hole contributes:

```text
0.5 d_h*
to the shear segment
```

and:

```text
0.5 d_h*
to the tension segment
```

No physical hole contributes more than one complete deduction across a combined candidate.

### 24.3 U path

```text
A_ns =
2t[
L_v - (N_r - 0.5)d_h*
]
```

```text
A_nt =
t(N_b - 1)(g - d_h*)
```

### 24.4 L path

```text
A_ns =
t[
L_v - (N_r - 0.5)d_h*
]
```

Without additional full tension-path holes:

```text
A_nt =
t(
e_side - 0.5d_h*
)
```

With `q` additional full holes:

```text
A_nt =
t[
L_t - (q + 0.5)d_h*
]
```

### 24.5 Method trace

Retain two independent method bases:

- equation basis: `ASCE_EQ_8_14A` or `ASCE_EQ_8_14B`;
- path basis: project rational L/U and half-hole resolver, or explicit external path provenance.

When the automatic project resolver supplies the path:

```text
method_applicability =
CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
```

and Section 2.3.2 qualification remains required.

All credible candidates are calculated. Exact minimum design resistance controls. Equal candidates remain co-governing.

---

## 25. Section 2.10 net-area disposition

Use raw physical areas.

Do not replace a raw area with `0.75A_g`.

If:

```text
A_n/A_g < 0.75
```

then:

- calculate with the raw smaller area;
- return `CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED`;
- prohibit ordinary PASS.

If raw net area is zero or negative:

```text
INVALID_GEOMETRY
```

Check applicable shear and tension planes separately.

---

## 26. Single-lap multiplier

For multi-row single-lap connections:

```text
C_lap = 0.60
```

Apply it exactly once to:

- pin bearing;
- simplified first-row net tension;
- full first-row net tension;
- inter-row shear-out;
- concentric block shear;
- eccentric block shear.

Do not apply it to:

- metallic bolt strength;
- combined metallic bolt resistance;
- pull-through.

The RC2 golden includes an explicit single-lap block-shear case.

---

## 27. Required-check contract

The execution bundle shall contain a deterministic nonempty required-check set unless no check is physically applicable.

Required checks are determined per load combination, bolt, bolt line, path, layer, geometry, and selected method.

| Check family | Required when |
|---|---|
| Bolt shear | Every bolt carrying resolved in-plane demand |
| Bolt tension and combined interaction | Explicit bolt-axis tension is present or required |
| Pull-through | Explicit bolt-axis demand and an applicable FRP face/layer exist |
| Pin bearing | Every applicable FRP layer and bolt under every governing row-demand scenario |
| First-row net tension | Applicable in-plane tension and no source-authorized exemption |
| Inter-row shear-out | Two or more rows and no source-authorized exemption |
| Block shear | Applicable longitudinal tension and at least one credible complete path or approved external plan |
| Code geometry | Every applicable layer and connection detail |
| Qualification | Every rational, commentary, engineer-defined, external, or otherwise nonprescriptive method |
| Material/source review | Every unqualified or source-pending material input |

### 27.1 First-row method membership

- Simplified is the default direct-standard method when eligible.
- Commentary full is optional and separately identified.
- Commentary full shall not silently replace simplified.
- For more than three rows, the automatic lower-envelope result requires both simplified extension and unknown-`L_br` endpoint envelope.

### 27.2 Block candidates

All credible block candidates are required within the selected block-path plan. The minimum design resistance controls.

### 27.3 Zero required checks

If the required-check set is empty:

```text
numerical_comparison =
NOT_EVALUATED

overall_disposition =
NOT_EVALUATED
```

Never return PASS from an empty required-check set.

---

## 28. Numerical comparison

For positive design resistance:

```text
utilization =
demand / design_resistance
```

Use nonnegative demand magnitude.

```text
demand <= design_resistance:
PASS

demand > design_resistance:
FAIL
```

Exact equality passes.

For zero or negative design resistance:

- numerical comparison is `FAIL`;
- utilization is absent;
- retain `NONPOSITIVE_DESIGN_RESISTANCE`;
- do not clamp.

If a required check is not evaluated:

- numerical comparison is `NOT_EVALUATED` unless another known required-check failure already establishes `FAIL`;
- the incomplete or unsupported condition remains visible.

---

## 29. Governing, co-governing, and deterministic ordering

Use exact Decimal values to determine the actual minimum resistance or maximum utilization.

The existing co-governing utilization tolerance is:

```text
1E-12
```

It is used only to retain co-governing IDs for reporting. It shall not change:

- resistance;
- utilization;
- PASS/FAIL;
- exact controlling minimum.

Rules:

1. Exact `A = B`: retain `LBR_0` and `LBR_1`.
2. Equal simplified and full-envelope resistance: retain both method IDs.
3. Equal block candidates: retain all equal candidate IDs in stable candidate order.
4. Results within `1E-12` of maximum utilization: retain all co-governing IDs in existing deterministic result order.
5. Do not select an arbitrary single winner solely to simplify output.
6. Candidate and result ordering shall not depend on filesystem, hash-map, set, or operating-system order.

---

## 30. Applicability, qualification, and aggregate status

Maintain separate axes:

### Geometry

- `VALID`
- `INVALID_GEOMETRY`

### Availability

- `CALCULATED`
- `NOT_APPLICABLE`
- `INCOMPLETE_INPUT`
- `SOURCE_DATA_PENDING`
- `CALCULATION_NOT_SUPPORTED`
- `ENGINEERING_REVIEW_REQUIRED`
- `SECTION_2_3_2_QUALIFICATION_REQUIRED`
- `CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED`

### Method applicability

- `ASCE_PRESCRIPTIVE`
- `ASCE_COMMENTARY_METHOD`
- `CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE`
- `ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE`
- `ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION`

### Numerical comparison

- `PASS`
- `FAIL`
- `NOT_EVALUATED`

### Qualification

Use the accepted repository qualification enum or repository-consistent equivalent, including:

- ordinary ASCE-prescriptive qualification;
- Section 2.3.2 qualification required;
- engineering review required;
- source data pending.

### 30.1 Aggregate hierarchy

1. Invalid geometry controls overall disposition.
2. A known numerical failure remains `FAIL`.
3. Unsupported or incomplete required checks prevent ordinary PASS.
4. Code-geometry violations prevent ordinary PASS.
5. Method applicability outside prescriptive scope independently prevents ordinary PASS.
6. Section 2.3.2 qualification prevents ordinary PASS.
7. Unqualified development material requires engineering review.
8. Ordinary PASS requires:
   - valid geometry;
   - a nonempty required-check set;
   - every required check calculated or source-authorized as not required;
   - no numerical failure;
   - prescriptive method applicability;
   - ordinary qualification;
   - no code-geometry violation;
   - no source or engineering-review limitation.
9. If no required check exists, return `NOT_EVALUATED`.

### 30.2 Combined conditions

- Known failure plus qualification: overall numerical result remains `FAIL`; qualification remains visible.
- Known failure plus unsupported/incomplete check: failure remains visible and controls numerical comparison; unsupported/incomplete state remains visible.
- Numerical PASS plus engineer-defined method: numerical comparison may be `PASS`; overall disposition is qualification required, not ordinary PASS.
- Numerical PASS plus rational block-path method: overall disposition is qualification required.
- Code geometry below 75% plus numerical PASS: ordinary PASS prohibited.

---

## 31. Fully resolved external plans

### 31.1 Unequal rows

When row bolt counts are unequal:

- automatic prescribed distribution is unavailable;
- engineer-defined row or per-bolt demand may execute with provenance;
- per-bolt checks may execute when fully resolved;
- other limit-state plans may execute only when their geometry and demand inputs are complete;
- qualification remains required.

### 31.2 Staggered geometry

For staggered groups:

- automatic RC1 distribution and automatic RC1 block-path execution remain unsupported;
- do not fabricate a path or distribution;
- a complete external demand/area/path plan may execute only when:
  - every value is explicit;
  - physical validation succeeds;
  - provenance and engineer confirmation are present;
  - method applicability remains outside prescriptive scope;
  - Section 2.3.2 qualification remains required.

Missing or partial external plans return incomplete/unsupported.

---

## 32. Required warning identities

Retain existing warnings and add the following exact or repository-consistent identities:

- `ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED`
- `CONSERVATIVE_FULL_ROW_ENVELOPE_USED`
- `RATIONAL_EQ_8_13_EXTENSION_USED`
- `ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION`
- `RATIONAL_HALF_HOLE_CORNER_ACCOUNTING`
- `CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED`
- `REDUCED_PITCH_FACTOR_APPLIED`
- `LIMITED_ECCENTRIC_BLOCK_SHEAR_TEST_BASIS`
- `NUMERICAL_DOMAIN_ERROR`
- `NONPOSITIVE_DESIGN_RESISTANCE`
- `ENGINEER_DEFINED_METHOD_USED`
- `EXTERNAL_RESOLVED_PLAN_USED`
- `MISSING_REQUIRED_BOLT_AXIS_TENSION`
- `RATIONAL_BLOCK_PATH_RESOLVER_USED`

Warnings shall include safe structured trace fields. User-facing prose may be finalized later.

---

## 33. Fingerprinting

The Slice 2 fingerprint shall include:

- physical geometry and material identities;
- ordered rows, lines, bolts, layers, and paths;
- signed force vector and nonnegative magnitude;
- demand method and provenance;
- row fractions or direct demands;
- selected first-row and shear-out methods;
- source/rational/engineer-defined classifications;
- block-path and raw area plans;
- eccentricity, reference, classification, and tolerance;
- factors;
- required-check contract;
- source metadata;
- execution-input schema;
- contract, engine, rule-set, result, and fingerprint versions.

Exclude:

- display units;
- display rounding;
- camera/view state;
- UI selection;
- preview timing;
- request timestamps;
- random IDs;
- filesystem ordering.

Force reversal changes physical row order and therefore changes the fingerprint.

Display-unit changes do not change the fingerprint.

The result fingerprint shall be deterministic across operating systems and process runs.

---

## 34. Input validation and failure behavior

Validate:

- positive integer row and bolt counts;
- unique row, line, bolt, layer, and path IDs;
- finite coordinates and quantities;
- unique physical bolt locations;
- positive bolt, hole, thickness, and relevant geometric dimensions;
- physical hole diameter not less than bolt diameter;
- exact Decimal row fractions;
- complete row coverage;
- row-fraction balance within the named Decimal tolerance;
- direct-force balance within the named force tolerance;
- valid method provenance;
- valid source and factor identities;
- deeply immutable nested execution state;
- complete block-shear payload;
- complete required-check set;
- complete version context.

Do not repair invalid input silently.

Unexpected arithmetic exceptions shall not escape the pure engine entry point. Convert them into structured fail-closed results with trace, without reporting PASS.

---

## 35. Companion RC2 golden authority

The companion golden is:

```text
FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_GOLDEN_BENCHMARKS_RC2.json
```

SHA-256:

```text
B3A49FB44089E065F7B4659F52AB856288298247504423970C3D19B8FCEA7B0B
```

The golden:

- carries every RC1 numerical and applicability case unchanged;
- registers the unchanged RC1 hashes;
- adds `e1` mapping cases;
- adds Appendix branch-boundary cases;
- adds coefficient matrix cases;
- adds reduced-pitch scope;
- adds complete factor-stack cases;
- adds exact endpoint ties;
- adds single-lap block shear;
- adds native-SI hole handling;
- adds eccentricity classification;
- adds invalid-domain behavior;
- adds zero-check and nonpositive-resistance behavior;
- adds source-authorized exemptions;
- adds external staggered/unequal-plan behavior;
- adds engineer-defined PASS-with-qualification;
- adds known failure plus qualification;
- adds independent multi-layer evaluation;
- adds force reversal;
- adds deterministic tie behavior;
- adds demand, thickness, hole-size, and row-fraction monotonic pairs.

Production code shall derive every value. Production code shall not read the golden.

Tests may use RC1 and RC2 goldens as independent oracles.

---

## 36. Mandatory invariants

1. Increasing demand cannot reduce utilization.
2. Increasing valid thickness cannot reduce applicable resistance.
3. Increasing hole diameter cannot increase full-method or block-shear resistance.
4. Increasing a row fraction cannot reduce that row’s bearing utilization.
5. Row fractions balance exactly in their authoritative Decimal representation.
6. Display-unit changes cannot alter result, status, method, or fingerprint.
7. Force reversal changes physical row order and fingerprint but not demand magnitude sign.
8. Single-lap affects only approved FRP in-plane modes.
9. `C_delta` affects only approved FRP in-plane modes and is applied once.
10. Existing Slice 1 results, versions, and golden hash remain unchanged.
11. Every RC1 benchmark remains unchanged in RC2 regression.
12. Known failure remains visible with qualification or unsupported conditions.
13. More than three rows may calculate but cannot receive ordinary ASCE PASS.
14. Engineer-defined methods cannot receive ordinary ASCE PASS.
15. Rational block-path results cannot receive ordinary ASCE PASS.
16. No equal-sharing assumption is silent.
17. Every rational extension is explicitly identified.
18. All credible block candidates are retained; exact minimum resistance governs.
19. No hole is deducted more than once across one combined block path.
20. Source `e1` is measured from the unloaded free end to the nearest row.
21. An empty required-check set is `NOT_EVALUATED`.
22. Every factor is typed, separately traced, and applied exactly once.
23. Every fingerprinted execution input is deeply immutable or canonically frozen.
24. Eccentricity uses physical geometry and a fingerprinted tolerance.
25. Equal endpoints and candidates retain all co-governing IDs deterministically.
26. No automatic prying demand is generated.

---

## 37. Stage 2.3 and Slice 1 compatibility

Stage 2.4B shall not modify:

- frozen frontend production source;
- frozen viewport behavior;
- frozen single-bolt workspace interaction;
- preview/design separation;
- frozen engineering-end/view-extent semantics;
- frozen action visualization/editing;
- existing Slice 1 equations;
- existing Slice 1 results;
- existing Slice 1 golden;
- existing Slice 1 API behavior;
- the Stage 2.3 freeze tag.

The Stage 2.3 freeze tag remains immutable.

---

## 38. Deliberate exclusions

Stage 2.4B shall not implement:

- general member-end-action-to-bolt-group analysis;
- general equilibrium distribution;
- friction or slip transfer;
- automatic prying generation;
- slotted holes;
- skewed bolts;
- cylindrical-side bolting;
- variable bolt size/grade/hole within one direct method;
- automatic first-row method for `N_b > 3`;
- automatic ASCE distribution for unequal rows;
- automatic staggered block-path planning;
- Section 2.3.2 qualification calculations;
- whole-joint qualification for unsymmetrical frame connections;
- application orchestration;
- API exposure;
- frontend presentation;
- persistence;
- reporting;
- authentication;
- authorization;
- entitlements;
- billing;
- deployment changes.

Geometry and external plans may represent future configurations without falsely claiming direct source coverage.

---

## 39. Required implementation verification after approval

A future Codex implementation order shall require, at minimum:

- exact repository preflight;
- unchanged RC1 and Slice 1 hashes;
- implementation only in calculation-layer production paths and tests;
- no API/frontend/dependency change;
- direct golden-driven tests for every RC1 and RC2 case;
- 100% backend line and branch coverage;
- configured frontend regression coverage unchanged;
- Ruff, strict mypy, ESLint, TypeScript, build, and dependency audits;
- deterministic cross-platform behavior;
- unit-equivalence tests;
- monotonicity tests;
- exact status-precedence tests;
- mutation tests for immutability and fingerprints;
- regression of Stage 2.1B, Stage 2.2A, Stage 2.2B, and Stage 2.3 freeze;
- explicit diff, commit, push, and hosted CI evidence.

No implementation order shall be issued until this specification, its golden, and the independent verification ledger are approved.

---

## 40. RC1-to-RC2 change summary

RC2 preserves RC1 and adds or clarifies:

1. Final engine-only Stage 2.4B boundary.
2. Proposed Slice 2 version identities.
3. Complete immutable execution bundle.
4. Complete result schema semantics.
5. Authoritative production conversion constant.
6. Correct unloaded-end `e1`.
7. Typed factor context and factor sequence.
8. Complete numerical domains.
9. Reduced-pitch mode scope.
10. Explicit single-lap block-shear scope.
11. Eccentricity tolerance and classification.
12. Independent multi-layer execution.
13. Fully resolved external staggered/unequal-plan execution.
14. Nonempty required-check requirement.
15. Method-applicability gating independent of qualification.
16. Deterministic endpoint, method, path, and utilization ties.
17. Expanded RC2 golden and verification requirements.

---

## 41. Approval

This document is a candidate.

Approval of this RC2 package authorizes preparation of the Stage 2.4B Codex implementation order. It does not itself modify the repository or authorize any unreviewed implementation.

**END OF RC2 ENGINEERING SPECIFICATION CANDIDATE**
