# FRP Master Connection
# CME-2 — C2-P1 Flat 316 Stainless Steel Connector-Plate Resistance Engineering Specification — RC1 R1

**Status:** Approved controlled engineering implementation authority, RC1 R1. R1 corrects only the stress-conversion precision to the frozen repository native exact Decimal helper; engineering equations, factors, cases, scope, and applicability are unchanged. Existing connection-family stainless activation remains prohibited.

**Companion material specification:** `FRP_MASTER_CONNECTION_CME_2_C2_M_ENGINEERING_SPECIFICATION_RC1.md`

**Companion source record:** `FRP_MASTER_CONNECTION_CME_2_C2_SOURCE_RECONCILIATION_RC1.md`

**Companion benchmark authority:** `FRP_MASTER_CONNECTION_CME_2_C2_P1_GOLDEN_BENCHMARKS_RC1_R1.json`

**Implementation state:** CME-2 production code has not begun. Existing CME-1 native FRP behavior remains frozen.

## 1. Purpose

C2-P1 defines the first bounded numerical resistance family for a **flat 316-family stainless connector plate under already-resolved demand**.

It deliberately separates:

1. stainless body resistance;
2. connector/bolt demand resolution;
3. FRP member and receiving-member checks;
4. independent 316SS fastener checks;
5. whole-connection qualification and PASS/FAIL.

A C2-P1 body result shall never be treated as proof that an existing FRP/stainless connection has a valid material-dependent force distribution.

## 2. Approved design-basis bridge

For this bounded implementation scope, the approved authority chain is:

`ASCE/SEI 74-23 FRP member/interface authority + ANSI/AISC 370-25 stainless connector-body authority`

AISC 360-22 is a comparison/reference source only. Its connecting-element shear-yielding rule is not numerically identical to the stainless AISC 370 rule, so C2-P1 shall not be implemented by substituting stainless material properties into an AISC 360 or existing FRP provider.

The owner approved this bridge on 2026-09-12; project-specific EOR adoption remains a deployment/design responsibility where applicable.

## 3. Material scope

C2-P1 consumes only the controlled C2-M material record:

- client-facing family: `316 Stainless Steel`;
- initial numerical property basis: `GENERIC_316SS_CONSERVATIVE_BASIS_US_SOURCE`;
- `Fy = 25 ksi`;
- `Fu = 70 ksi`;
- no cold-work strength credit;
- no MTR overstrength credit;
- exact S31600/S31603/dual-certified identity retained as provenance but not used to increase C2-P1 resistance.

The initial body is an unwelded flat connector plate cut/drilled/machined from an approved A240/A240M flat-product source. Angles, Tees, formed products, welded built-up products, and laser-welded shapes are excluded.

## 4. Included numerical scope

C2-P1 may calculate, when all source/applicability/demand gates are satisfied:

- gross-section tensile yielding;
- effective-net-section tensile rupture;
- pure connecting-element shear yielding;
- pure connecting-element shear rupture;
- block shear on an already-resolved canonical path;
- standard-round-hole bearing of the stainless connected material;
- standard-round-hole tearout of the stainless connected material;
- deterministic governing selection within a common demand family;
- utilization for already-resolved factored demand.

Initial software design basis is LRFD only.

## 5. Explicit exclusions

C2-P1 does **not** provide:

- any existing-family stainless activation;
- any UI stainless capacity result;
- material-dependent branch sharing;
- bolt-group demand distribution;
- equal-share assumptions;
- common-fastener-plane response generation;
- prying/contact or secondary bolt-force generation;
- bolt/nut/washer resistance;
- FRP member/interface resistance;
- receiving-member or support-zone strength;
- anchor/foundation strength;
- compression/buckling resistance;
- general plate bending/flexure/local-buckling resistance;
- combined axial/shear/flexural interaction;
- weld strength;
- formed-angle or Tee strength;
- slip-critical transfer or friction credit;
- oversized/slotted-hole automatic methods;
- staggered automatic net-section paths;
- fatigue;
- elevated-temperature resistance;
- corrosion-life qualification;
- whole-connection ordinary PASS.

Those are separate later scopes.

## 6. Required immutable calculation-plan inputs

A future C2-P1 plan shall retain, at minimum:

- material identity and conservative-property-snapshot identity;
- adopted source/specification editions and source-lock state;
- source property unit system;
- nominal plate thickness;
- **design plate thickness**;
- plate boundaries and reference frame;
- physical hole identities and coordinates;
- nominal bolt diameter and its source system;
- nominal hole diameter and its source system;
- net-area deduction width and its source system;
- signed local force direction(s);
- gross/net tension-section identity;
- gross/net shear-section identity;
- block-shear candidate/path identity and areas;
- per-hole bearing/tearout geometry including `l1`;
- demand identity/provenance;
- per-hole resolved demand where a local-hole check is requested;
- response/qualification disposition;
- provider/rule/source versions.

Client-entered arbitrary areas or capacities are not engineering authority.

## 7. Design thickness

The plate resistance equations use **design thickness**, not blindly the nominal thickness.

RC1 rule from the inspected AISC 370 source:

- if nominal thickness `t_nom > 3/16 in`, use `t = t_nom`;
- if `t_nom <= 3/16 in`, use `t = 0.95 t_nom` unless a separately verified product tolerance permits nominal-thickness credit;
- C2-P1 automatic behavior shall conservatively use `0.95 t_nom` at or below `3/16 in` unless that tolerance authority is present;
- no user-entered override may silently restore nominal thickness.

A future SI-source material record shall apply the adopted final-source metric boundary directly rather than regenerating it from a U.S.-source record.

## 8. Standard-hole automatic geometry domain

The initial automatic U.S.-source C2-P1 standard-hole table is limited to the directly identified AISC stainless table rows:

| Nominal bolt `d` | Standard hole `d_h` | Minimum standard-hole edge distance |
|---:|---:|---:|
| 1/2 in | 9/16 in | 3/4 in |
| 5/8 in | 11/16 in | 7/8 in |
| 3/4 in | 13/16 in | 1 in |
| 7/8 in | 15/16 in | 1-1/8 in |
| 1 in | 1-1/8 in | 1-1/4 in |

The initial provider does **not** extrapolate a 3/8-in row.

A physical 3/8-in project bolt remains permitted under its existing hardware/FRP authority, but an automatic stainless-plate C2-P1 geometry plan using that bolt shall return:

`STAINLESS_BOLT_DIAMETER_OUTSIDE_AUTOMATIC_J3_TABLE_SCOPE`

until a separately approved stainless detailing rule covers it.

## 9. Minimum and maximum detailing checks

For initial automatic standard-hole geometry:

- center-to-center spacing shall satisfy `s >= (8/3)d`;
- clear distance between holes/slots shall not be less than `d`;
- `3d` is a preferred spacing, not the automatic minimum;
- standard-hole edge distance shall satisfy the applicable table minimum;
- C2-P1 does not automatically use the source provision permitting a smaller edge distance through EOR judgment;
- maximum center-to-nearest-edge distance for elements in contact is `min(12t, 6 in)`;
- longitudinal bolt-hole spacing for a plate and shape, or two plates, in continuous contact is `min(24 t_thinner, 12 in)`.

The last rule is applied only to geometry for which the source's continuous-contact condition is actually satisfied.

Geometry/detailing status is independent from numerical resistance status.

## 10. Net-area deduction

For tension and shear net-area calculations, the physical hole is not enlarged. A separate source-derived deduction width is used.

For a U.S.-source ordinary hole:

`d_net = d_h + 1/16 in`

For a genuinely SI-source geometry record, use the adopted final-source SI deduction, retaining that source identity.

A U.S.-source record displayed in SI converts its stored U.S. physical/source values exactly; it does not regenerate a new metric table identity.

Automatic staggered zigzag/net-width arithmetic is deferred. Staggered geometry returns a dedicated unsupported status rather than silently using a straight-line path.

## 11. Effective net area / shear lag

Tensile rupture uses:

`A_e = A_n U`

C2-P1 may automatically use:

`U = 1.0`

only where the canonical load-path resolver proves the adopted source case in which load is transmitted directly to all cross-sectional elements of the plate.

If that condition is not established, the automatic provider shall return:

`STAINLESS_SHEAR_LAG_METHOD_NOT_AVAILABLE`

A free user-entered `U` is not accepted as ordinary numerical authority.

## 12. Gross-section tensile yielding

For a covered tension section:

`R_n = F_y A_g`

LRFD:

`phi = 0.90`

`R_d = phi R_n`

## 13. Effective-net-section tensile rupture

For a covered tension section:

`R_n = F_u A_e`

LRFD:

`phi = 0.75`

`R_d = phi R_n`

The covered pure-tension body result is the lower applicable design resistance from Sections 12 and 13.

## 14. Connecting-element shear yielding

For a covered pure shear section:

`R_n = 0.60 C_v F_y A_gv`

Final-source connecting-element value:

`C_v = 1.2`

LRFD:

`phi = 0.90`

This stainless coefficient/factor combination is deliberately different from the AISC 360-22 J4 connecting-element shear-yielding rule and shall remain a stainless-provider method identity.

## 15. Connecting-element shear rupture

For a covered pure shear section:

`R_n = 0.60 F_u A_nv`

LRFD:

`phi = 0.75`

The covered pure-shear body result is the lower applicable design resistance from Sections 14 and 15.

## 16. Block shear

For each already-resolved, physically credible canonical block path:

`R_n,rupture = 0.60 F_u A_nv + U_bs F_u A_nt`

`R_n,yield_cap = 0.60 C_v F_y A_gv + U_bs F_u A_nt`

`R_n = min(R_n,rupture, R_n,yield_cap)`

LRFD:

`phi = 0.75`

Initial automatic `U_bs` classifications are:

- verified uniform tension distribution -> `U_bs = 1.0`;
- verified nonuniform tension distribution -> `U_bs = 0.5`.

`U_bs` is not a free ordinary-design scalar. An unclassified distribution fails closed.

C2-P1 does not invent the block path. It consumes canonical path geometry from an approved resolver, retains all credible candidates, and reports the minimum design resistance among the applicable candidate paths.

## 17. Standard-hole bearing and tearout — initial service-deformation branch

C2-P1 initially implements only the standard-hole bearing-type branch where deformation at the bolt hole at service load **is** treated as a design consideration.

Per-hole nominal bearing resistance of the stainless connected material:

`R_n,bearing = 1.25 d t F_u`

Per-hole nominal tearout resistance:

`R_n,tearout = 1.25 [l1 / (2 d_h)] d t F_u`

LRFD for both:

`phi = 0.75`

Per-hole connected-material resistance:

`R_d,hole = phi * min(R_n,bearing, R_n,tearout)`

`l1` shall be resolved from the canonical physical hole/edge/adjacent-hole geometry in the signed bearing-force direction using the adopted source definition.

The higher bearing/tearout branch permitted when service-load deformation is not a design consideration is deliberately deferred from C2-P1.

## 18. Per-hole demand boundary

C2-P1 does **not** distribute a connection force among bolts.

For bearing/tearout, each evaluated hole requires a separately resolved signed/magnitude demand with provenance.

If such demand is absent:

`STAINLESS_PER_HOLE_DEMAND_NOT_RESOLVED`

A sum of per-hole resistances may be reported as trace information only; it shall not manufacture equal-share or proportional-share demand.

## 19. Demand contracts

C2-P1 consumes already-resolved demands only, including as applicable:

- section axial tension;
- section in-plane shear;
- demand associated with a specific block-shear path;
- per-hole in-plane bearing demand.

Demand provenance shall identify the load combination, reference point, local frame/force direction, source response method, and whether any material-dependent response assumption is present.

If an existing connection-family demand depends on connector stiffness, branch sharing, common fastener response, contact, prying, support response, or receiving-member behavior that is not qualified for stainless, isolated body resistance may be calculated for development/engineering review but family activation remains prohibited.

## 20. Material/response/whole-connection separation

A future result shall distinguish at least:

- `body_geometry_status`;
- `material_source_status`;
- `resistance_method_status`;
- `demand_status`;
- `response_qualification_status`;
- `numerical_comparison`.

A numerical C2-P1 PASS means only that the isolated covered stainless-body check satisfies its supplied resolved demand.

It does **not** resolve:

- FRP member checks;
- bolt/nut/washer checks;
- source-pending hardware checks;
- receiving-member checks;
- anchor/foundation checks;
- contact/prying checks;
- material-dependent response/redistribution;
- whole-connection qualification.

A known numerical FAIL remains visible even if another required scope is unavailable.

## 21. Governing selection

Within one common demand family, retain every applicable check and select governing deterministically by utilization / available resistance using unrounded engineering values.

Do not compare unrelated scalar capacities tied to different demand components as though they form one interaction equation.

Combined action awaits a separately approved interaction method.

## 22. Unit and numerical policy

**Native stress-conversion reconciliation:** C2-P1 uses the repository native exact Decimal conversion helper. No C2-specific stress conversion, quantization, or shortened constant is permitted. The earlier shortened decimal was a drafting truncation and is superseded by the native helper value below.

One physical calculation path is used for a given source record.

Exact project conversions remain:

- `1 in = 25.4 mm`;
- `1 kip = 4.4482216152605 kN`;
- `1 ksi = 6.89475729316836133672267344534689069378138756277512555025110 MPa`.

For the initial U.S.-source property/geometry records:

- source `Fy`/`Fu`, bolt diameter, hole table identity, and net deduction remain U.S.-source identities;
- SI display/calculation values are exact conversions of those stored physical values;
- display-unit changes do not select the separately tabulated ASTM/AISC metric source values;
- no intermediate engineering rounding is permitted.

A future genuinely SI-source record is a distinct source identity and shall use the final adopted SI tables directly.

## 23. Fingerprint/reproducibility contract

A future C2-P1 numerical fingerprint shall include, at minimum:

- code-basis bridge identity;
- final source/adoption lock state;
- provider/rule version;
- material family/internal identity/property snapshot;
- source property system;
- nominal and design thickness;
- physical plate/hole geometry;
- source hole/detailing table identity;
- net deduction identity;
- resolved demand and provenance;
- section/path/hole IDs;
- `U`/`U_bs` classification and authority;
- response qualification disposition.

Exclude display units, display rounding, camera/view state, UI selection, timestamps, and readiness prose.

Existing native FRP fingerprints remain unchanged.

## 24. Fail-closed statuses

Use repository-consistent equivalents of, at minimum:

- `STAINLESS_SOURCE_AUTHORITY_NOT_LOCKED`
- `STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED`
- `STAINLESS_PRODUCT_FORM_NOT_SUPPORTED`
- `STAINLESS_PROPERTY_DOMAIN_NOT_APPLICABLE`
- `STAINLESS_BOLT_DIAMETER_OUTSIDE_AUTOMATIC_J3_TABLE_SCOPE`
- `STAINLESS_HOLE_TYPE_NOT_SUPPORTED_IN_C2_P1`
- `STAINLESS_CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED`
- `STAINLESS_ENGINEERING_REVIEW_REQUIRED`
- `STAINLESS_STAGGERED_NET_PATH_NOT_SUPPORTED_IN_C2_P1`
- `STAINLESS_SHEAR_LAG_METHOD_NOT_AVAILABLE`
- `STAINLESS_BLOCK_PATH_NOT_RESOLVED`
- `STAINLESS_PER_HOLE_DEMAND_NOT_RESOLVED`
- `STAINLESS_MATERIAL_DEPENDENT_RESPONSE_NOT_QUALIFIED`
- `STAINLESS_NOMINAL_THICKNESS_CREDIT_NOT_QUALIFIED`

Missing data is unavailable, never zero and never guessed.

## 25. Source/adoption locks — CLOSED

### SL-370-25-FINAL — CLOSED 2026-09-12

Final ANSI/AISC 370-25 was directly supplied and reconciled. C2-P1 directly locks the relevant final A3, B4.2/B4.4b, D3/Table D3.1, J3.2-J3.5, J3.10a, J4.1-J4.3, and related commentary provisions. No source discrepancy required changing the already validated benchmark numerics.

### SL-CONSERVATIVE-316SS-PROPERTY-SNAPSHOT — CLOSED BY OWNER DECISION 2026-09-12

The owner adopted the controlled U.S.-source `Fy = 25 ksi`, `Fu = 70 ksi` snapshot for all initial 316-family aliases. Final AISC 370-25 Commentary Table C-A3.2 independently corroborates those values for S31603/316L; no higher S31600 or MTR/cold-work strength is credited.

### SL-CODE-BASIS-BRIDGE — CLOSED BY OWNER DECISION 2026-09-12

ANSI/AISC 370-25 is the stainless connector-body design basis for C2-P1; ASCE/SEI 74-23 remains the FRP member/interface authority; AISC 360-22 remains comparison/reference authority.

## 26. Companion golden benchmark requirements

The companion RC1 JSON shall independently cover, at minimum:

- material alias/property policy;
- design-thickness rule above/below the 3/16-in boundary;
- every initial standard-hole table row;
- U.S.-source geometry displayed in SI without regeneration;
- tension yielding/rupture;
- shear yielding/rupture;
- uniform/nonuniform block shear;
- bearing/tearout;
- minimum-edge tearout;
- source-unit conversion;
- 3/8-in fail-closed behavior;
- detailing violations;
- unsupported hole/stagger/shear-lag conditions;
- unresolved per-hole demand;
- source-lock failure;
- family activation without response authority.

Expected numerical values shall be independently derived and shall not be generated from production code.

## 27. Mandatory invariants

- Demand increase cannot reduce utilization.
- Increasing covered design thickness cannot reduce a covered pure-mode resistance.
- Increasing `Fy` cannot reduce a covered yielding resistance.
- Increasing `Fu` cannot reduce a covered rupture/bearing/tearout/block resistance.
- Increasing a valid net-hole deduction cannot increase net-section/block resistance.
- Reducing valid `l1` cannot increase tearout resistance.
- A display-unit change cannot alter source identity, method, result, status, or fingerprint.
- A U.S.-source standard-hole record is converted, not regenerated from a metric table.
- A 3/8-in project bolt does not receive an invented stainless standard-hole/detailing row.
- Bolts, nuts, and washers remain independent 316SS hardware authority.
- No unresolved bolt-group demand receives automatic equal-share allocation.
- No isolated stainless-body PASS becomes a whole-connection PASS while response, FRP, fastener, support, or foundation checks remain unresolved.
- All frozen native FRP results remain unchanged.

## 28. Approval state

**C2-P1 RC1 is approved as controlled implementation authority for the isolated flat-plate provider only.**

The provider may be implemented and tested internally under the controlling Codex order, but it shall not be wired into any existing family, public design endpoint, UI selector, or frozen CME-1 readiness response until later response/family activation authority is separately approved.
