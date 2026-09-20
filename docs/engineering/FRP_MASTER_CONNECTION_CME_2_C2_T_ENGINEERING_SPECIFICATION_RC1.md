# FRP Master Connection
# CME-2 C2-T Hot-Rolled/Extruded 316 Stainless Tee Body Engineering Specification - RC1

**Provider identity:** `C2_T_AISC_370_25_A276_A484_HOT_SHAPE_LRFD_RC1`

**Status:** Approved isolated implementation authority. No public family activation.

## 1. Product/material scope

Supported:

- one-piece hot-rolled or extruded Tee;
- ASTM A276/A276M + ASTM A484/A484M;
- condition/finish A or HF;
- unwelded monolithic product;
- approved 316-family identity;
- Fy 25 ksi, Fu 70 ksi, E 28,000 ksi, G 10,800 ksi.

Excluded:

- Tee cut from W/S/I parent shape;
- A479 project route;
- cold-finished/strain-hardened credit;
- laser/welded/built-up Tee;
- formed product;
- CSM/MTR uplift.

## 2. Trusted Tee section snapshot

The trusted product/section record binds:

- source/product/section identity;
- flange width/thickness;
- stem depth/thickness;
- actual geometry/radius authority as applicable;
- gross area;
- centroid/principal axes;
- radii of gyration;
- `Smin` and `Sft` by supported principal axis;
- trusted net area if rupture is checked;
- shear-element records;
- axial/flexural element slenderness;
- product/geometry fingerprint.

No FRP Tee dimensions alone qualify stainless stock.

## 3. Slenderness

For axial compression, Tee flange and stem unstiffened elements use the B4.1a limit:

`lambda_r = 0.41 sqrt(E/Fy)`.

For F10 flexure, every applicable compression element must be non-slender under B4.1b.

If slender:

`STAINLESS_SHAPE_SLENDER_ELEMENT_NOT_SUPPORTED_IN_C2_CORE`.

## 4. Tension

### 4.1 Gross yielding

`Pn = Fy Ag`, `phi=0.90`.

### 4.2 Net rupture

`Pn = Fu An U`, `phi=0.75`.

Net area is trusted/resolved.

Permitted U:

- D3 Case 1 when every cross-sectional element receives direct transfer;
- D3 Case 2, `U=1-x/l`, when applicable.

D3 Case 7 is prohibited in RC1 because the selected product route is not a Tee cut from W/S shapes.

Attempting Case 7 returns:

`STAINLESS_TEE_D3_CASE7_NOT_APPLICABLE_TO_HOT_ROLLED_EXTRUDED_TEE`.

## 5. Pure shear - G6

Use the same four-zone G6/G2.2 `Cv2` method and LRFD factor 0.90 defined in the C2-A RC1 specification.

A rolled/extruded Tee may use full physical depth/width parallel to the shear action where the trusted shear-element record establishes the G6 element.

No tension-field enhancement.

## 6. Compression

For a nonslender Tee:

- evaluate E3 flexural buckling about both principal axes;
- require trusted E4 elastic-buckling stress from qualified analysis;
- use Curve A and frozen project `Fn_used=min(Fy,Fn_raw)` policy;
- `Pc=0.90 Fn_used Ag`;
- lowest E3/E4 available strength governs.

C2-T does not solve the E4 elastic eigenvalue in RC1.

## 7. Flexure - F10

Use the same F10 method as C2-A:

- `My=Fy Smin`;
- austenitic beta_LT=0.82;
- trusted `Lb`, `Ly`, `Lr`, and required `Fcr`;
- no-LTB / inelastic-LTB / elastic-LTB branches;
- `Mn <= My`;
- `Mc=0.90 Mn`.

## 8. Combined axial force + flexure - H2

Use H2 exactly as specified for C2-A.

Supports one or both principal flexural axes.

No simultaneous shear interaction and no torsion.

## 9. Tee stem/flange/junction boundary

C2-T full-section D/E/F/G/H checks do not invent a local flange-prying or stem-flange-junction plate mechanism.

Frozen C2-P1/C2-P2 local-region snapshots may be consumed when independently applicable and correctly bound.

If the requested connection response requires a local Tee junction/flange mechanism not covered by:

- full-section C2-T checks;
- a qualified frozen local-region snapshot; and
- qualified C2-R response,

return:

`STAINLESS_TEE_LOCAL_JUNCTION_METHOD_NOT_AVAILABLE`.

## 10. Historical Tee geometry

C2-T shall not repair or reinterpret the historical default Tee geometry limitation.

`CANONICAL_TEE_MAPPING_INVALID` / `OUTSIDE_SELECTED_LEG_SURFACE` behavior remains frozen outside this provider.

## 11. Torsion / combined shear boundary

Any nonzero required torsion:

`STAINLESS_SHAPE_TORSION_NOT_SUPPORTED`.

Any request requiring H3-style combined shear/torsion/axial/flexure interaction:

`STAINLESS_SHAPE_COMBINED_NORMAL_SHEAR_NOT_SUPPORTED`.

## 12. Result/fingerprint/public isolation

Return independent product/source, response, full-section, local-region, stability, unsupported-action, and family-activation dispositions.

Fingerprint binds every trusted source/section/response/stability/demand field.

No public family/API/frontend activation is authorized in C2-T RC1.
