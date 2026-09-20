# FRP Master Connection
# Calculation Slice 2 Engineering Specification — RC1

**Document status:** Approved engineering specification for controlled Stage 2.4A contracts/applicability implementation and subsequent Stage 2.4B numerical-engine implementation  
**Not a Codex implementation order**  
**Calculation family:** General bolt-group and multi-row pultruded-FRP bolted-connection checks  
**Primary standard:** ASCE/SEI 74-23  
**Correction set:** Erratum 1, effective January 13, 2026  
**Erratum effect on this slice:** None; Erratum 1 changes Chapter 5, not Chapter 8  
**Approved by:** Baraa Misto  
**Companion benchmark authority:** `FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_GOLDEN_BENCHMARKS_RC1.json`  
**Companion golden SHA-256:** `C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610`

---

## 1. Purpose

This RC1 specification extends the existing verified single-bolt/single-row calculation architecture into a
future-ready bolt-group model and a controlled multi-row calculation family.

It intentionally separates:

1. Physical geometry validity.
2. Numerical calculation availability.
3. Calculation method and ASCE applicability.
4. Qualification disposition.
5. Numerical PASS/FAIL.

The geometry model shall not contain a permanent three-row limit. Connections with more than three rows may
continue through identified numerical methods and display resistance/utilization results, but they shall not receive
an ordinary ASCE prescriptive PASS. They remain subject to Section 2.3.2 qualification.

Stage 2.4A establishes immutable domain contracts, geometry/applicability resolution, calculation-plan contracts,
warnings, and deterministic fixtures. Stage 2.4A shall not execute the new resistance equations.

Stage 2.4B will separately implement the executable numerical engine against these approved contracts and goldens.

---

## 2. Source hierarchy and interpretation policy

### 2.1 Controlling sources

1. ASCE/SEI 74-23, Chapter 8 and Section 2.10.
2. ASCE/SEI 74-23 Commentary, including Appendix CA8.3.3.
3. Erratum 1, effective January 13, 2026.
4. This approved engineering specification.
5. The companion machine-readable golden benchmark file.

### 2.2 Source-derived provisions

The following are source-derived:

- Two- and three-row prescriptive scope.
- Row-load proportions in Commentary Table C8-1.
- Main-body first-row net-tension Equations 8-10 and 8-11.
- Appendix CA8.3.3 first-row net-tension equations.
- Two-row and three-row shear-out Equations 8-12 and 8-13.
- Block-shear Equations 8-14a and 8-14b.
- Section 2.10 hole deduction and 75% net-area requirement.
- Single-lap multiplier.
- Geometry limits in Table 8-1 and Section 8.2.5.

### 2.3 Approved rational extensions

The following are approved rational extensions and must be labeled as such:

- General geometry with any positive row count and bolt count.
- Conservative full-row demand envelope.
- Unknown-first-row-share Appendix endpoint envelope.
- Numerical first-row lower envelope beyond three rows.
- Equation 8-13 row-span extension beyond three rows.
- L/U block-path geometry resolver.
- Half-hole allocation at a shared shear/tension corner.
- Numerical calculation using actual raw net area when the 75% requirement is not satisfied, with ordinary PASS prohibited.
- Conservative `C_T = 0.50` interpretation for the pultruded-plate Appendix source conflict.

No rational extension may be reported as an ordinary prescriptive ASCE result.

---

## 3. Terminology

Use distinct software terms:

- `row_count`, `N_r`: number of bolt rows along the connection-force direction.
- `bolts_per_row`, `N_b`: number of bolts across a row, normal to the force direction.
- `pitch`, `s`: center-to-center spacing between adjacent rows.
- `gauge`, `g`: center-to-center spacing between bolts across a row.
- `Row 1`: row farthest from the unloaded free end.
- `Row N_r`: row nearest the unloaded free end.
- `bolt line`: bolts aligned along the force direction.
- `first-row bearing fraction`, `L_br`: proportion of total in-plane force transferred in bearing at Row 1.
- `bypass fraction`: `1 - L_br`.

Do not use one ambiguous `n` for both row count and bolts per row.

---

## 4. General geometry scope

The canonical geometry model supports:

- `N_r >= 1`.
- `N_b >= 1`.
- Explicit bolt coordinates.
- Explicit row identities.
- Explicit bolt-line identities.
- Explicit pitch values.
- Explicit gauge values.
- Physical free ends and side boundaries.
- Round holes.
- Per-layer material axes.
- Per-bolt penetrated-layer stacks.

The first automatic multi-row calculation family is optimized for:

- Rectangular, nonstaggered arrangements.
- Constant bolt diameter, grade, and hole diameter.
- Constant pitch for direct ASCE methods.
- Constant gauge for direct ASCE methods.
- Equal numbers of bolts in covered rows.
- One planar interface.
- One signed in-plane resultant force.
- `N_b <= 3` for automatic first-row net-tension methods.

Geometry with more rows or more bolts per row is not automatically invalid.

---

## 5. Method/applicability model

### 5.1 `ASCE_STANDARD_SIMPLIFIED`

Uses main-body Equations 8-10 and 8-11.

Ordinary prescriptive applicability requires all source limits, including:

- `N_r = 2 or 3`.
- `N_b = 1 to 3`.
- Nonstaggered arrangement.
- Constant pitch/gauge as required.
- Source geometry-ratio limits.
- Valid material direction.
- Other Chapter 8 geometry requirements.

This is the default issued-design method when applicable.

### 5.2 `ASCE_COMMENTARY_FULL`

Uses Appendix CA8.3.3 and source-prescribed row fractions.

It is optional, explicitly commentary-based, and shall not silently replace the standard simplified result.

### 5.3 `CONSERVATIVE_FULL_ROW_ENVELOPE`

Used when more than three rows are modeled and no engineer-defined distribution is supplied.

Every physical row is separately evaluated as potentially carrying 100% of the total in-plane connection force.
Within a row of identical bolts:

`per_bolt_demand = total_in_plane_demand / bolts_in_that_row`.

No automatic row-sharing credit is taken.

### 5.4 `ENGINEER_DEFINED_ROW_DISTRIBUTION`

Accepts either:

- Row fractions summing exactly to 1.0 within a controlled tolerance; or
- Explicit resolved row forces.

Required provenance:

- Source method.
- Source document/calculation.
- Revision.
- Load combination.
- Reference point.
- Whether clearance/contact was modeled.
- Engineer confirmation.

### 5.5 `RATIONAL_MULTIROW_LOWER_ENVELOPE`

For more than three rows, automatic first-row net tension is the lower of:

- Main-body simplified numerical extrapolation.
- Appendix unknown-`L_br` endpoint envelope.

It remains outside prescriptive scope.

### 5.6 `RATIONAL_EXTENSION_EQ_8_13`

For more than three rows, inter-row shear-out may use the actual Row-1-to-free-end row span in a rational extension
of Equation 8-13. It remains outside prescriptive scope.

---

## 6. Source-prescribed row distributions

For equal bolts per row:

| Connected materials | Rows | Row 1 | Row 2 | Row 3 |
|---|---:|---:|---:|---:|
| FRP/FRP | 2 | 0.50 | 0.50 | — |
| FRP/steel | 2 | 0.60 | 0.40 | — |
| FRP/FRP | 3 | 0.40 | 0.20 | 0.40 |
| FRP/steel | 3 | 0.50 | 0.30 | 0.20 |

Each bolt within one row receives an equal share of that row force only when the row geometry and selected method
support that assumption.

---

## 7. Demand contracts

### 7.1 Total in-plane force

The multi-row family consumes one explicitly resolved signed in-plane connection resultant for each checked load
combination and layer/load path.

It does not yet solve an arbitrary six-component member-end action into a general bolt group.

### 7.2 Bolt-axis tension

Pull-through and bolt tension require explicit per-bolt bolt-axis tension or approved externally resolved values.

The software shall not automatically generate prying demand.

### 7.3 Eccentricity

Block-shear concentric/eccentric classification derives from the canonical force line and physical geometry.

Screen coordinates and rendered arrow offsets have no engineering authority.

---

## 8. Reused per-bolt equations

Existing Stage 2.1B equations remain authoritative for:

- Bolt tensile rupture.
- Bolt shear rupture.
- Combined bolt tension/shear.
- Pull-through.
- Pin bearing.

For row `j` with fraction `p_j` and `N_b,j` identical bolts:

`V_u,bolt,j = p_j V_u,total / N_b,j`.

For the conservative full-row envelope:

`V_u,bolt,j = V_u,total / N_b,j`

for every row scenario.

No friction transfer is credited.

---

## 9. Main-body simplified first-row net tension

### 9.1 Longitudinal

`R_nt,f,L = 0.2 w t F_t,L`

`phi = 0.50`

### 9.2 Transverse

`R_nt,f,T = 0.2 w t F_t,T`

`phi = 0.45`

### 9.3 Effective width

For `N_b = 1`:

`w = e_3 + e_4`

For `N_b = 2 or 3`:

`w = e_3 + e_4 + (N_b - 1) g`

The actual physical side distances and Chapter 8 caps control `e_3` and `e_4`.

The first-row plane is Row 1.

---

## 10. Appendix CA8.3.3 first-row net tension

Define:

`A = K_nt,i (w / (N_b d))`

`B = K_op,i / (1 - N_b d_n / w)`

Then:

`R_nt,f,i = w t F_t,i / [A L_br + B (1 - L_br)]`

with:

- `phi = 0.50` for longitudinal.
- `phi = 0.45` for transverse.

### 10.1 One bolt across each row

`S_pr = w / d`

`K_nt,i = [1 + C_i(S_pr - 1.5((S_pr - 1)/(S_pr + 1))^Theta)] / (w/d - 1)`

`Theta = 1.5 - 0.5(w/e_1)` when `e_1/w <= 1`; otherwise `Theta = 1`.

`K_op,i = 1 + C_op,i[1 + (1 - 1/S_pr)^3]`

### 10.2 Two or three bolts across each row

`S_pr = g / d`

`K_nt,i = [1 + C_i(S_pr - 1.5((S_pr - 1)/(S_pr + 1))^Theta)] / (w/(N_b d) - 1)`

`Theta = 1.5 - 0.5(g/e_1)` when `e_1/g <= 1`; otherwise `Theta = 1`.

`K_op,i = 1 + C_op,i[1 + (1 - 1/S_pr)^3]`

### 10.3 Coefficients

Longitudinal:

- Pultruded shape: `C_L = 0.50`.
- Pultruded plate: `C_L = 0.40`.
- `C_op,L = 0.50`.

Transverse controlled interpretation:

- Pultruded shape: `C_T = 0.50`.
- Pultruded plate: `C_T = 0.50`, with source-conflict warning.
- `C_op,T = 0.50`.

---

## 11. Unknown-`L_br` endpoint envelope

For:

`R(L_br) = w t F_t / [B + (A - B)L_br]`

and:

`0 <= L_br <= 1`

the minimum resistance occurs at an endpoint:

`R_env = w t F_t / max(A, B)`.

The trace shall retain:

- `A`.
- `B`.
- Controlling endpoint `LBR_0` or `LBR_1`.
- Envelope nominal resistance.
- Envelope design resistance.

For more than three rows:

`R_auto = min(R_simplified_extension, R_CA8_envelope)`.

This is a rational extension, not an ASCE-prescriptive result.

---

## 12. Inter-row shear-out

### 12.1 Two rows — Equation 8-12

`R_sh = 1.4(e_1 - d_n/2 + s)tF_sh`

`phi = 0.45`

This is a resistance per bolt line.

### 12.2 Three rows — Equation 8-13

`R_sh = 2[(N_r - 1)s]tF_sh`, with `N_r = 3`

`phi = 0.45`

This is a resistance per bolt line.

### 12.3 More than three rows

Define actual row span:

`L_rows = sum(s_i)` from the row nearest the free end to Row 1.

Use:

`R_sh,ext = 2 L_rows t F_sh`

`phi = 0.45`

The result is labeled `RATIONAL_EXTENSION_EQ_8_13`, outside prescriptive scope, and qualification is required.

Each bolt line is checked separately.

---

## 13. Block shear equations

### 13.1 Concentric longitudinal tension — Equation 8-14a

`R_bs = 0.5(A_ns F_sh + A_nt F_t,L)`

`phi = 0.45`

### 13.2 Eccentric in-plane tension — Equation 8-14b

`R_bs,e = 0.5(A_ns F_sh + 0.5 A_nt F_t,L)`

`phi = 0.45`

The result trace notes the limited eccentric test basis discussed in the commentary.

### 13.3 Applicability

- Tensile force parallel to LW: calculable.
- Compression: `NOT_APPLICABLE`.
- Material angle greater than 5 degrees: `CALCULATION_NOT_SUPPORTED`.
- Staggered and eccentric: Section 2.3.2 qualification required.
- More than three rows: numerical result may be shown but qualification remains required.

---

## 14. Block-shear coordinate and path model

For each FRP layer:

- `u` = signed in-plane force direction.
- `v` = in-plane perpendicular direction.
- Project bolt centers into `(x_i, y_i)`.
- Group rows by `x`.
- Group bolt lines by `y`.
- Row 1 is farthest from the unloaded free end.

A valid candidate must create a complete separable block using rupture planes and real physical free boundaries.

Reject a candidate that:

- Leaves bolts bridging the proposed block.
- Does not close on a physical free boundary.
- Crosses a void or physical boundary.
- Crosses a deferred heel/junction/corner.
- Stops at an intermediate row.
- Self-intersects.
- Produces nonpositive net length.

---

## 15. L- and U-shaped block paths

### 15.1 Net-hole deduction

`d_h* = d_n + 0.063 in` for a U.S.-source hole.

`d_h* = d_n + 1.6 mm` for an SI-source hole.

This affects net-area calculation only; it does not change the physical hole.

### 15.2 Shared-corner rule

A hole shared by perpendicular shear and tension path segments contributes:

- `0.5 d_h*` to the shear segment.
- `0.5 d_h*` to the tension segment.

No physical hole contributes more than one complete deduction across the combined candidate.

### 15.3 U-shaped path

For gross shear length per leg `L_v`:

`A_ns = 2 t [L_v - (N_r - 0.5)d_h*]`

For constant gauge and `N_b` bolts across Row 1:

`A_nt = t(N_b - 1)(g - d_h*)`

### 15.4 L-shaped path

`A_ns = t[L_v - (N_r - 0.5)d_h*]`

For a direct corner-to-free-side tension path without interior full holes:

`A_nt = t(e_side - 0.5d_h*)`

With `q` additional full holes:

`A_nt = t[L_t - (q + 0.5)d_h*]`

All raw lengths, holes, deductions, boundaries, and rejection reasons remain in the trace.

---

## 16. Section 2.10 minimum net area

Calculate raw physical areas.

Do not replace a smaller raw area with `0.75 A_g`.

If:

`A_n / A_g < 0.75`

return:

- Numerical resistance using the raw smaller area.
- `CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED`.
- Ordinary PASS prohibited.

If raw net area is zero or negative:

`INVALID_GEOMETRY`.

Check applicable shear and tension sections separately.

---

## 17. Single-lap and factors

For applicable FRP in-plane multi-row strengths:

`C_lap = 0.60` for single lap.

The single-lap multiplier does not apply to:

- Metallic bolt strength.
- Pull-through.

Retain separately:

- `lambda`.
- `phi`.
- `C_lap`.
- `C_delta`.
- `C_M`.
- `C_T`.
- `C_CH`.

No factor may be silently merged.

---

## 18. Geometry and detailing rules

Retain at minimum:

- Bolt diameter: 3/8 through 1 in.
- FRP thickness: at least 0.188 in for ordinary use.
- Multi-row tension end distance: at least `2d`.
- Compression end distance: at least `2d`.
- Edge distance: at least `1.5d`.
- Pitch: at least `4d`.
- Gauge: at least `4d`.
- Maximum pitch in force direction: `min(24t, 12 in)`.
- Constant bolt size/grade, hole size, and spacing for direct prescriptive methods.
- `C_delta = s/s_min` where the source permits a reduced pitch.
- More than three rows or more than three bolts in the applicable line requires Section 2.3.2 qualification.

A geometry violation is distinct from exceeding prescriptive row count.

---

## 19. Status model

### 19.1 Geometry

- `VALID`
- `INVALID_GEOMETRY`

### 19.2 Availability

- `CALCULATED`
- `NOT_APPLICABLE`
- `INCOMPLETE_INPUT`
- `SOURCE_DATA_PENDING`
- `CALCULATION_NOT_SUPPORTED`
- `ENGINEERING_REVIEW_REQUIRED`
- `SECTION_2_3_2_QUALIFICATION_REQUIRED`
- `CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED`

### 19.3 Method/applicability

- `ASCE_PRESCRIPTIVE`
- `ASCE_COMMENTARY_METHOD`
- `CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE`
- `ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE`
- `ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION`

### 19.4 Numerical comparison

- `PASS`
- `FAIL`
- `NOT_EVALUATED`

### 19.5 Aggregate hierarchy

1. Invalid geometry controls.
2. A known numerical failure remains visible and controls numerical comparison.
3. Unsupported or incomplete required checks prevent ordinary PASS.
4. Code-geometry violations prevent ordinary PASS.
5. Exceeding prescriptive row/bolt count requires Section 2.3.2 qualification.
6. Unqualified development material requires engineering review.
7. Ordinary PASS requires every required check to be covered, calculated, qualified, and not failed.

A numerical PASS outside prescriptive scope is never displayed as an ordinary whole-connection ASCE PASS.

---

## 20. Required warnings

### 20.1 More than three rows

`ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED`

The message shall state that numerical resistance/utilization is shown using the identified method, while Section 2.3.2 qualification remains required.

### 20.2 Conservative row envelope

`CONSERVATIVE_FULL_ROW_ENVELOPE_USED`

The message shall state that every row was evaluated as potentially taking the full in-plane force and no row-sharing benefit was credited.

### 20.3 Rational Equation 8-13 extension

`RATIONAL_EQ_8_13_EXTENSION_USED`

The message shall identify the actual row span and qualification status.

### 20.4 Plate transverse source conflict

`ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION`

The trace shall identify the conflicting `C_T` values and adopted `C_T = 0.50`.

### 20.5 Block-shear corner accounting

`RATIONAL_HALF_HOLE_CORNER_ACCOUNTING`

The trace shall identify shared corner holes and the half/half allocation.

---

## 21. Input validation

- Positive integer row/bolt counts.
- Unique row and bolt IDs.
- Finite physical coordinates.
- Unique physical bolt locations.
- Valid row ordering from canonical force/free-end geometry.
- Positive bolt/hole sizes.
- Row fractions finite, nonnegative, and summing to one within the named tolerance.
- Explicit direct row demands must balance the total within the named force tolerance.
- Mixed methods in one result are prohibited unless each method is separately identified.
- Booleans are not numeric inputs.
- NaN and infinity are rejected.

---

## 22. Determinism and fingerprinting

The future Slice 2 fingerprint shall include:

- Physical geometry and material identities.
- Row/bolt identities and coordinates.
- Demand method.
- Row fractions/direct demands.
- Selected first-row method.
- Rational-extension flags.
- Source-conflict interpretation.
- Block-path identities and raw geometry.
- Factors and source metadata.
- Engine/rule/schema versions.

Exclude:

- Display units.
- Display rounding.
- Camera/view state.
- UI selection.
- Preview timing.
- Request timestamps.
- Random IDs.

Stage 2.4A does not activate a new calculation engine or rule set.

---

## 23. Dual-unit policy

One physical equation path.

Exact conversions:

- `1 in = 25.4 mm`.
- `1 kip = 4.4482216152605 kN`.
- `1 ksi = 6.8947572931683613367 MPa`.

The source representation that created the ordinary hole is retained.

Changing display units does not regenerate the hole.

No intermediate engineering value is rounded.

---

## 24. Golden benchmark authority

The companion JSON is the machine-readable benchmark authority.

Production code must derive all values.

Tests may use the JSON as the oracle.

The JSON includes:

- Prescribed two- and three-row cases.
- Method comparison cases.
- Numerical failure cases.
- More-than-three-row automatic cases.
- Engineer-defined distribution.
- Single-lap behavior.
- Block-shear L/U and concentric/eccentric cases.
- Section 2.10 warning case.
- Plate `C_T` conflict case.
- Applicability-only cases.
- U.S./SI equivalence.

Golden SHA-256:

`C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610`

---

## 25. Mandatory invariants

- Demand increase cannot reduce utilization.
- Thickness increase cannot reduce applicable resistance.
- Hole-size increase cannot increase net-tension, shear-out, or block-shear resistance.
- A row fraction increase cannot reduce that row’s bearing utilization.
- Row fractions must balance.
- Display-unit changes cannot alter results/status/fingerprint.
- Single-lap affects only applicable FRP in-plane strengths.
- Existing RC2 results remain unchanged.
- Known failure remains visible with qualification warnings.
- More than three rows may calculate but cannot receive ordinary ASCE PASS.
- No equal-sharing assumption is silent.
- Every rational extension is explicitly identified.
- All credible block-shear candidates are retained; minimum resistance governs.
- No hole is deducted more than once across one combined block path.

---

## 26. Stage 2.3 freeze compatibility

The frozen tag remains:

`stage-2.3-interface-geometry-freeze`

This specification is a compatible backend engineering extension.

Stage 2.4A shall not modify:

- Frozen frontend production source.
- Frozen viewer behavior.
- Frozen single-bolt workspace interaction.
- Frozen preview/design separation.
- Frozen e1/view-extent semantics.
- Frozen action visualization/editing.

Future UI exposure of multi-row behavior will be separately controlled.

---

## 27. Deliberate exclusions from RC1 automatic execution

- General six-component member-end-to-bolt-group solution.
- Friction/slip transfer.
- Prying generation.
- Variable bolt size/grade/hole within one direct method.
- Staggered automatic block-path execution.
- Slotted holes.
- Skewed bolts.
- Cylindrical-side bolting.
- Automatic first-row net-tension formula for `N_b > 3`.
- Automatic row distribution for unequal row bolt counts.
- Section 2.3.2 qualification calculations.
- Whole-joint qualification for unsymmetrical frame connections.
- Persistence, reporting, auth, billing, or deployment.

Geometry may still represent future configurations without falsely claiming calculation coverage.

---

## 28. Approval

Baraa Misto approved this engineering direction for controlled implementation.

Stage 2.4A may implement contracts, applicability, geometry-to-plan mapping, warnings, fixtures, and documentation.

Stage 2.4A may not execute the new equations.

Stage 2.4B requires a separate controlling order.
