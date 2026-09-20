# FRP Master Connection — Calculation Slice 4 — ASCE/SEI 74-23 Chapter 7 Pure-Mode FRP Plate Strength Engine — Decision

## Decision

The revised Stage 3.6B rational web-splice body calculation is paused because the repository does not yet contain executable ASCE/SEI 74-23 Chapter 7 pure-mode plate-strength engines.

Before Stage 3.6B resumes, implement one shared backend calculation authority:

**Calculation Slice 4 — Chapter 7 Pure-Mode FRP Plate Strength Engine**

This is a reusable engineering-calculation slice, not a new connection family and not a UI/product stage.

It supplies the code-based pure-mode strengths required by Stage 3.6B and future FRP plate/member calculations.

## Authorized scope

Calculation Slice 4 implements the normative Chapter 7 plate equations required for:

### In-plane tension

- longitudinal plate tension;
- transverse plate tension;
- LRFD resistance factor handling;
- existing time-effect factor input;
- effective net-area-per-unit-width input from geometry/caller.

### In-plane compression

- longitudinal material-rupture strength;
- transverse material-rupture strength reference;
- longitudinal orthotropic plate buckling;
- governing longitudinal compression strength;
- combined longitudinal/transverse compression buckling for the explicit normative `0.3 <= xi_LT <= 1.0` range.

### In-plane shear

- material-rupture strength;
- orthotropic shear-buckling strength;
- governing in-plane shear strength.

## Property-adjustment boundary

Calculation Slice 4 does **not** reimplement Section 2.4 material/environment/end-use adjustments.

The engine consumes already resolved/adjusted characteristic properties and moduli from the existing material/property authority:

- `F_tL`;
- `F_tT`;
- `F_cL`;
- `F_cT`;
- `F_vLT`;
- `E_L`;
- `E_T`;
- `G_LT`;
- `nu_LT`.

It also consumes the already resolved time-effect factor `lambda`.

Every result retains property/source provenance.

## Geometry boundary

The engine consumes explicit plate geometry:

- thickness `t`;
- material-transverse plate span `b`;
- optional material-longitudinal span `a` where required;
- effective tensile net area per unit plate width `Ae`.

It does not infer geometry from a connection scene.

The caller remains responsible for selecting the correct physical panel/section dimensions.

## Normative equations

The controlled implementation identities are:

- `ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION`;
- `ASCE74_EQ_7_13_TRANSVERSE_PLATE_TENSION`;
- `ASCE74_EQ_7_15_LONGITUDINAL_COMPRESSION_RUPTURE`;
- `ASCE74_EQ_7_16_TRANSVERSE_COMPRESSION_RUPTURE`;
- `ASCE74_EQ_7_18_LONGITUDINAL_PLATE_BUCKLING`;
- `ASCE74_EQ_7_21_COMBINED_COMPRESSION_BUCKLING`;
- `ASCE74_EQ_7_24_IN_PLANE_SHEAR_RUPTURE`;
- `ASCE74_EQ_7_26_IN_PLANE_SHEAR_BUCKLING`;
- `ASCE74_EQ_7_27_SHEAR_BUCKLING_ETA`.

Resistance factors remain the source-prescribed values:

- plate tension: `phi = 0.65`;
- plate compression: `phi = 0.70`;
- plate in-plane shear: `phi = 0.70`.

The time-effect factor is not hard-coded to 1.0 in production; it is supplied by the existing caller/factor authority.

## Longitudinal compression buckling boundary

The Section 7.6.3 long-plate equation uses the source-prescribed edge-rotation coefficient:

`k_cr = 1.0`.

No user override is permitted in this slice.

The engine shall return an advisory provenance flag when the plate falls within commentary-described narrow-plate or short-plate caution ranges, but the normative equation itself is not altered.

## Combined compression boundary

The Section 7.6.4 combined longitudinal/transverse compression buckling calculation is authorized only for:

`0.3 <= xi_LT <= 1.0`.

Outside that range:

`SECTION_7_6_4_COMBINED_COMPRESSION = REQUIRES_SECTION_2_3_2`.

No extrapolation.

This combined-compression sub-engine is included for reusable completeness, but Stage 3.6B rational web-splice body RC1 does not require it.

## Shear buckling boundary

Implement the normative Section 7.7.3 piecewise shear-buckling equation and `eta_LT`.

Use the source-prescribed branch:

- `0 < eta_LT <= 1`;
- `eta_LT > 1`.

No smoothing/tolerance branch switch.

For `a < b`, commentary identifies the normative long-plate equation as conservative and discusses a better short-plate estimate. Calculation Slice 4 RC1 retains the normative equation and emits a commentary caution flag rather than introducing the commentary axis-swap method as a second strength equation.

## Transverse compression boundary

Section 7.6.2 provides transverse material-rupture strength.

Calculation Slice 4 may expose that source result, but it shall not claim a complete pure-transverse-compression stability design where the source does not provide a directly applicable pure-transverse buckling equation.

Return:

`TRANSVERSE_COMPRESSION_STABILITY = REQUIRES_SECTION_2_3_2`

when a complete transverse compression design result is requested.

## Stage 3.6B handoff

After Calculation Slice 4 is accepted:

1. do not alter its equations inside Stage 3.6B;
2. Stage 3.6B shall call Slice 4 for its code-based pure tension/compression/shear plate resistances;
3. the controlled rational combined normal/shear interaction remains separate Stage 3.6B authority;
4. Stage 3.6B shall be reissued with the new Slice 4 baseline commit.

## No product/UI work

Calculation Slice 4 adds no normal frontend workspace and no new connection selector.

Frontend production changes expected:

`0`.

Any optional diagnostics belong in backend tests/governance, not a user workspace.

## Frozen-family boundary

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 freeze tags remain immutable.

Stage 3.6A behavior and fingerprints remain exact.

**END OF CALCULATION SLICE 4 CHAPTER 7 PLATE STRENGTH ENGINE DECISION**
