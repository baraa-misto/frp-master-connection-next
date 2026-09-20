# FRP Master Connection
# CME-2 C2-A Hot-Rolled/Extruded 316 Stainless Angle Body Engineering Specification - RC1

**Provider identity:** `C2_A_AISC_370_25_A276_A484_HOT_SHAPE_LRFD_RC1`

**Status:** Approved isolated implementation authority. No public family activation.

## 1. Product/material scope

Supported:

- one-piece structural angle;
- ASTM A276/A276M chemistry/mechanical-property authority;
- ASTM A484/A484M general requirements;
- hot-rolled or extruded;
- condition/finish A or HF;
- unwelded;
- approved 316-family identity;
- Fy 25 ksi, Fu 70 ksi, E 28,000 ksi, G 10,800 ksi.

Excluded:

- A479 project route;
- cold-finished/strain-hardened credit;
- formed/bent flat product;
- laser-fused;
- welded/built-up;
- MTR uplift;
- CSM.

## 2. Trusted section snapshot

Production shall consume a trusted section/product record. It shall not infer a stainless section from an FRP nominal angle name.

The record binds at minimum:

- source/product identity;
- section identity;
- equal- or unequal-leg classification;
- actual leg dimensions and design thickness;
- radius/geometry authority where relevant;
- gross area;
- centroid/principal-axis identity;
- radii of gyration;
- elastic section moduli `Smin` and tension-fiber moduli by supported principal axis;
- resolved net area where rupture is evaluated;
- shear-element records;
- axial/flexural element slenderness classification;
- geometry/source fingerprint.

Test-only analytical fixtures are not production qualification.

## 3. Section slenderness

For axial compression, each unstiffened angle leg must satisfy:

`b/t <= 0.41 sqrt(E/Fy)`.

For F10 flexure, every compression element relevant to the evaluated bending axis must be non-slender under the B4.1b `lambda_r` limit.

If any required element is slender:

`STAINLESS_SHAPE_SLENDER_ELEMENT_NOT_SUPPORTED_IN_C2_CORE`.

## 4. Tension

### 4.1 Gross yielding

`Pn = Fy Ag`, `phi = 0.90`.

### 4.2 Net rupture

`Pn = Fu Ae`, `phi = 0.75`.

`Ae = An U`.

`An` must be a trusted resolved net area. RC1 performs no staggered path search.

### 4.3 Shear lag U

Permitted classifications:

- D3 Case 1: `U=1.0` only for direct transfer to every cross-sectional element.
- D3 Case 2: `U=1-x/l` with trusted `x` and `l`.
- D3 Case 8:
  - four or more fasteners per line: `U=0.80`;
  - three fasteners per line: `U=0.60`;
  - fewer: use Case 2.

Where Case 2 and Case 8 are both applicable, the larger permitted U may be used.

Arbitrary client U is prohibited.

## 5. Pure shear - G6

LRFD:

`Vc = 0.90 Vn`

`Vn = 0.6 Cv2 Fy Aw`.

A trusted shear-element record supplies `d`, `t`, and whether the element is unstiffened/stiffened.

For RC1:

- unstiffened `kv=1.2`;
- stiffened `kv=5.0` only with trusted boundary authority.

Define:

`lambda = d/t`

`q = sqrt(kv E/Fy)`.

Then:

- Zone 1, `lambda <= 0.33 q`: `Cv2 = 1.2`.
- Zone 2, `0.33 q < lambda <= 0.97 q`:
  `Cv2 = 1.2 - 0.62(lambda/q - 0.33)`.
- Zone 3, `0.97 q < lambda <= 2.68 q`:
  `Cv2 = (5.02q-lambda)/(1.62q+3.55lambda)`.
- Zone 4, `lambda > 2.68 q`:
  `Cv2 = 1.51 kv E/(lambda^2 Fy)`.

For a rolled/extruded angle, a supported shear record may use the full physical section depth/width parallel to the shear action, consistent with G6 commentary.

No tension-field enhancement.

## 6. Compression

Compression RC1 is available only for:

- equal-leg angles;
- nonslender elements;
- trusted effective lengths for both principal flexural axes;
- trusted E4 elastic-buckling stress `Fe_E4` from qualified stability analysis.

Unequal-leg angle compression returns:

`STAINLESS_ANGLE_COMPRESSION_UNEQUAL_LEG_NOT_SUPPORTED`.

### 6.1 E3 flexural buckling

Use Curve A:

- alpha 0.56;
- beta0 0.76;
- beta1 0.41;
- beta2 0.69.

For each principal flexural axis:

`Fe = pi^2 E/(Lc/r)^2`.

Use E3 branches and retain raw `Fn_raw`.

Project policy:

`Fn_used = min(Fy, Fn_raw)`.

`Pc_axis = 0.90 Fn_used Ag`.

### 6.2 E4 flexural-torsional buckling

The trusted stability record supplies `Fe_E4`.

C2-A applies E3 Curve A to that elastic buckling stress, retains raw/capped Fn, and computes:

`Pc_E4 = 0.90 Fn_used Ag`.

The lower of both E3 axes and E4 governs.

C2-A does not itself solve E4 geometry/eigenvalue equations in RC1.

## 7. Flexure - F10

Applicable only to a nonslender section.

For each supported principal bending axis:

`My = Fy Smin`.

LRFD factor 0.90.

Trusted stability record supplies `Lb`, `Ly`, `Lr`, and, when `Lb>Lr`, `Fcr`.

- `Lb <= Ly`: `Mn = My`.
- `Ly < Lb <= Lr`:
  `x=(Lb-Ly)/(Lr-Ly)`;
  `alpha_LT=0.60-0.40x`;
  `Mn = My - (My-0.30My) x^alpha_LT`.
- `Lb > Lr`:
  `Mn = beta_LT Fcr Smin`, with austenitic `beta_LT=0.82`.

Always:

`Mn <= My`

`Mc = 0.90 Mn`.

A missing required stability record fails closed.

## 8. Combined axial force + flexure - H2

Only when required torsion is zero and no simultaneous normal-plus-shear interaction is required.

All demand terms are positive magnitudes.

### 8.1 Compression

`IR = Pr/Pc + Mrw/Mcw + Mrz/Mcz`.

PASS only if `IR <= 1.0`.

### 8.2 Tension

Both:

`IR1 = Mrw/Mctw + Mrz/Mctz + Pr/Pct`

`IR2 = Mrw/Mcw + Mrz/Mcz - Pr/Pct`.

`Pct` is the C2-A available tensile strength.

`Mct = 0.90 Fy Sft` for the relevant extreme tension fiber.

Both equations shall be retained; the larger governs.

## 9. Unsupported combined actions

Any nonzero required torsion:

`STAINLESS_SHAPE_TORSION_NOT_SUPPORTED`.

Any request requiring combined axial/flexure plus shear interaction:

`STAINLESS_SHAPE_COMBINED_NORMAL_SHEAR_NOT_SUPPORTED`.

Pure shear may be checked independently under G6.

## 10. Local Angle regions

C2-A may consume bound frozen C2-P1/C2-P2 local-region snapshots.

It must not import or modify those frozen modules.

Local snapshots cannot establish:

- full-angle shear lag;
- full-angle stability;
- heel bending/prying;
- material-dependent response.

If heel/contact/prying local resistance is required without approved local authority:

`STAINLESS_ANGLE_LOCAL_HEEL_PRYING_METHOD_NOT_AVAILABLE`.

## 11. Result/fingerprint/public isolation

Provider results retain product/source, section, response, tension, shear, compression, flexure, H2, local-region, unsupported-action, and family-activation states separately.

Canonical fingerprint binds every result-affecting trusted field.

No public family dispatcher/API/frontend integration is authorized in C2-A RC1.
