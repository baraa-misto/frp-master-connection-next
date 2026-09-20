# FRP Master Connection
# CME-2 — C2-M 316 Stainless Steel Material / Source Engineering Specification — RC1

**Status:** Approved controlled engineering implementation authority for the bounded C2-M material/source contract. Final ANSI/AISC 370-25 has been directly reconciled. This document does **not** activate stainless in any existing connection family.

**Companion source record:** `FRP_MASTER_CONNECTION_CME_2_C2_SOURCE_RECONCILIATION_RC1.md`

**Implementation state:** CME-2 production code has not begun. Repository baseline remains the frozen CME-1F state.

## 1. Purpose

C2-M establishes the first controlled material identity, provenance, product-form boundary, design-property policy, unit-source behavior, and fail-closed rules for future 316 stainless connector-body calculations.

It does not calculate connector resistance and does not authorize stainless material in any existing family.

## 2. Frozen project boundary

CME-1 remains frozen. The following are non-negotiable:

- primary beams, columns, braces, and receiving structural members remain FRP-only;
- connector-body material is a separate role from structural-member material;
- bolts, nuts, and washers remain the project's existing 316 stainless hardware under independent fastener authority;
- anchors/foundations remain separate;
- current FRP connector bodies continue to use their frozen native FRP providers;
- changing future connector-body material must not silently alter native FRP geometry, demand, capacities, source status, governing selection, or historical fingerprints;
- historical Tee invalid-default behavior remains independent from material readiness.

## 3. Approved stainless code-basis bridge

ASCE/SEI 74-23 Chapter 8 permits stainless-steel connecting elements but directs steel connection-component design to AISC 360; its listed AISC reference is ANSI/AISC 360-16.

For future 316 stainless connector-body resistance, this project adopts the following explicit bridge:

`ASCE/SEI 74-23 FRP member/interface authority + ANSI/AISC 370-25 stainless connector-body authority`

AISC 360-22 is retained as a compatibility/reference source but is not the numerical stainless body provider authority.

The owner explicitly approved this project engineering bridge on 2026-09-12. The software shall record the adopted basis explicitly and shall never infer or substitute it silently. Project-specific EOR adoption remains a responsibility of issued engineering work where required.

## 4. Source hierarchy

For the bounded initial C2-M/P1 scope:

1. Explicit owner/EOR-approved code-basis bridge in Section 3.
2. Final ANSI/AISC 370-25 for stainless connector-body structural resistance and stainless connection detailing.
3. ASTM A240/A240M-24 for the final AISC 370-25 referenced 316-family flat-product chemical/mechanical property chain.
4. ASTM A480/A480M-24 for the final AISC 370-25 referenced general requirements applicable to flat-rolled stainless product.
5. AISC 313-25 for fabrication/standard-practice requirements when its scope becomes relevant to product activation.
6. ASCE/SEI 74-23 + accepted errata for FRP member, FRP interface, connection scope, hardware compatibility, and frozen product boundaries.
7. AISC 360-22 as comparison/historical bridge only.
8. Approved project specifications, goldens, freeze records, and source signatures.

The final ANSI/AISC 370-25 text dated December 8, 2025 was directly supplied and reconciled. Controlled source SHA-256: `A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`. The relevant A3, B4, D3, J3, J4 and commentary provisions are directly locked for C2-M/C2-P1.

## 5. Client-facing material option

The normal user-facing connector-body material option is:

`316 Stainless Steel`

Accepted client/project wording may map to this family:

- `316SS`
- `316 SS`
- `316`
- `316L`
- `316L SS`
- `316/316L`

These aliases do not erase the certified material identity when certification is available.

## 6. Internal material identities

Retain at minimum:

- `S31600_316`
- `S31603_316L`
- `S31600_S31603_DUAL_CERTIFIED`
- `GENERIC_316SS_CONSERVATIVE_BASIS`

The user does not need to choose among these identities for ordinary design. The backend preserves them for provenance and future qualification.

## 7. Initial design-property policy

For **all** initial C2-P1 uses of the user-facing `316 Stainless Steel` option, use one conservative U.S.-source project property snapshot:

- `Fy = 25 ksi`
- `Fu = 70 ksi`

This is the lower ordinary strength envelope of the 316/316L pair in the currently corroborated material sources and corresponds to the 316L/S31603 minimum basis.

Therefore:

- a generic client specification `316SS` uses 25/70;
- explicit `316L` uses 25/70;
- qualifying `316/316L` dual-certified stock uses 25/70 in C2-P1;
- explicit `316` may retain S31600 identity in provenance, but **C2-P1 does not credit the higher S31600 minimum strength**;
- a higher MTR yield/tensile result does not increase C2-P1 resistance;
- cold-worked or strain-hardened strength is not credited.

A later separately approved advanced material method may credit exact S31600 or condition-specific strength. That is not part of C2-M/P1.

## 8. Property snapshot source description

The 25/70 U.S. snapshot is an **owner-approved project-controlled conservative property snapshot**. Final AISC 370-25 Commentary Table C-A3.2 directly corroborates S31603/316L `Fu = 70 ksi`, `Fy = 25 ksi`, while S31600/316 is listed at higher ordinary minima; C2-M intentionally credits only 25/70.

Final-source reconciliation is:

- final AISC 370-25 Section A2 references ASTM A240/A240M-24 and A480/A480M-24 for this edition;
- final Table A3.1f defines A240/A240M + A480/A480M as the flat plate/sheet/strip product chain;
- final Commentary Table C-A3.2 reports S31603/316L 70/25 and S31600/316 75/30 in U.S. customary units;
- the owner-approved 25/70 project snapshot remains deliberately conservative and is not increased by exact S31600 identity, MTR results, or cold-worked strength.

No later ASTM edition is silently substituted for the edition referenced by final AISC 370-25.

## 9. Initial product form

C2-M/P1 is limited to:

- austenitic 316-family stainless;
- flat plate, sheet, or strip;
- ASTM A240/A240M product basis;
- ASTM A480/A480M general-requirements basis;
- cut, drilled, or machined flat connector bodies;
- no intentional strength enhancement from cold working;
- no welded or built-up connector-body strength;
- no formed/bent angle provider;
- no rolled/extruded angle provider;
- no Tee provider;
- no laser-welded structural-shape provider.

Geometry may represent future bodies without falsely claiming numerical coverage.

## 9A. Design thickness for the initial flat-plate provider

C2-M distinguishes nominal stock thickness from the design thickness consumed by C2-P1. Based on the inspected stainless design provisions:

- for nominal thickness greater than `3/16 in. (5 mm)`, the initial design thickness equals nominal thickness;
- for nominal thickness at or below `3/16 in. (5 mm)`, the initial automatic design thickness is `0.95` times nominal thickness unless a separately verified product minimum-thickness tolerance of no more than 5% authorizes nominal-thickness use;
- a user/MTR nominal thickness does not itself authorize bypass of this rule;
- this design-thickness decision and its source/tolerance provenance belong in the engineering fingerprint.

This design-thickness rule is directly verified in final ANSI/AISC 370-25 and is approved for implementation.

## 10. Welding and 316/316L identity

For the initial unwelded flat-plate scope, certified S31600, S31603, or dual-certified stock may be recorded, but the C2-P1 property snapshot remains 25/70.

For future welded bodies:

- generic `316SS` does not establish welding eligibility;
- the adopted stainless specification's low-carbon/dual-certified welding requirements must be satisfied;
- welding procedure, filler, inspection, heat-affected material applicability, and fabricated-junction strength require separate controlled authority;
- C2-M/P1 does not activate welding or Tee/angle fabrication methods.

## 11. Source-unit policy

ASTM A240/A240M states U.S. customary and SI systems independently as standard and warns that they need not be exact equivalents.

Therefore source units are engineering provenance.

Initial project snapshot:

`source_property_system = US_CUSTOMARY`

Rules:

- store `Fy = 25 ksi`, `Fu = 70 ksi` as the source values;
- SI calculations/display use exact unit conversion of those stored physical values;
- switching display units must never swap the stored values for separately tabulated ASTM SI values;
- a future genuinely SI-source record must retain the SI table values as its own source identity;
- source value, display value, and printed alternate-standard value are distinct concepts;
- no intermediate engineering rounding.

## 12. Physical properties for later methods

Final ANSI/AISC 370-25 Table User Note A3.1 lists ordinary austenitic stainless physical values including:

- `E = 28,000 ksi`;
- `G = 10,800 ksi`;
- density `500 lb/ft^3`;
- common Poisson-ratio treatment consistent with the stainless specification's analysis provisions.

C2-P1 does not require these for its initial pure strength methods. They remain outside the current numerical provider and may only be used in a later separately approved stiffness/stability/response method.

## 13. Material certificate / MTR policy

A material certificate may establish:

- UNS identity;
- dual certification;
- product specification;
- heat/lot traceability;
- product form and thickness;
- condition;
- measured chemistry and mechanical tests.

For C2-P1 it shall **not** increase the ordinary 25/70 design snapshot.

Missing required identity/provenance shall return a source/provenance status. It shall never become a zero property and shall never trigger a fallback to a different grade.

## 14. Independent 316SS hardware policy

Project bolts, nuts, and washers remain 316 stainless steel regardless of connector-body material.

C2-M/P1 shall not:

- reuse ASTM F593/F594 fastener strengths as connector-body properties;
- use connector-body `Fy`/`Fu` for bolt capacity;
- alter thread/grip/washer rules;
- change the bolt/nut/washer material when a connector switches between FRP and stainless;
- resolve any existing source-pending hardware check by borrowing body properties.

The connector-body result may consume trusted bolt/hole geometry and already-resolved demand, but fastener resistance remains a different provider responsibility.

## 15. Corrosion and environmental boundary

A structural-strength calculation using 316 stainless does not by itself establish service-environment suitability.

Where applicable, project design must separately address:

- chloride exposure and crevice conditions;
- galvanic/bimetallic interfaces;
- electrical isolation;
- finish/cleaning/passivation;
- moisture trapping;
- dissimilar metal contact;
- chemical exposure.

A C2-P1 numerical PASS is not a corrosion-suitability PASS.

## 16. Required material/source contract fields

A future trusted material snapshot shall retain at minimum:

- client-facing family label;
- exact internal material identity;
- generic/conservative-basis flag;
- UNS identity when known;
- dual-certification identity when applicable;
- product specification and edition;
- general-requirements specification and edition;
- property source identity/content digest or controlled snapshot ID;
- source unit system;
- `Fy` and `Fu` source values;
- product form;
- thickness/domain applicability;
- condition/fabrication state;
- cold-work-credit flag, fixed false in C2-P1;
- MTR-overstrength-credit flag, fixed false in C2-P1;
- final-source-lock status;
- provider/rule-set version.

Client-minted strings do not become trusted source descriptors.

## 17. Fail-closed status vocabulary

At minimum support repository-consistent equivalents of:

- `STAINLESS_SOURCE_AUTHORITY_NOT_LOCKED`
- `STAINLESS_MATERIAL_SOURCE_NOT_VERIFIED`
- `STAINLESS_GRADE_IDENTITY_INCOMPLETE`
- `STAINLESS_PRODUCT_FORM_NOT_SUPPORTED`
- `STAINLESS_PROPERTY_DOMAIN_NOT_APPLICABLE`
- `STAINLESS_FABRICATION_METHOD_NOT_SUPPORTED`
- `STAINLESS_WELDING_AUTHORITY_NOT_AVAILABLE`
- `STAINLESS_MATERIAL_DEPENDENT_RESPONSE_NOT_QUALIFIED`
- `STAINLESS_ENGINEERING_REVIEW_REQUIRED`

A missing property/source is unavailable, not zero.

## 18. Fingerprinting and reproducibility

A future C2-M/P1 engineering identity shall include:

- commercial material family;
- internal material identity;
- conservative-property-snapshot ID;
- property/source edition and source-unit system;
- actual body geometry;
- demand identity/provenance;
- provider/rule version;
- code-basis bridge version;
- final-source-lock/adoption state.

Exclude display units, display rounding, camera/view state, timestamps, UI selections, and nonengineering readiness prose.

Existing FRP fingerprints remain frozen and unchanged.

## 19. Source/adoption locks — CLOSED

### SL-370-25-FINAL — CLOSED 2026-09-12

Final ANSI/AISC 370-25 was directly supplied and reconciled for C2-M/C2-P1. Relevant A3 material/product provisions, B4 design thickness/net area, D3 effective net area, J3 detailing/bearing/tearout, J4 connecting-element strength, and final commentary were verified.

### SL-CONSERVATIVE-316SS-PROPERTY-SNAPSHOT — CLOSED BY OWNER DECISION 2026-09-12

The owner adopted the project-controlled conservative U.S.-source snapshot `Fy = 25 ksi`, `Fu = 70 ksi`. Final AISC 370-25 Commentary Table C-A3.2 independently corroborates those minima for S31603/316L. C2-M does not credit the higher S31600 table minima.

### SL-CODE-BASIS-BRIDGE — CLOSED BY OWNER DECISION 2026-09-12

The owner approved ANSI/AISC 370-25 as the stainless connector-body design basis, with ASCE/SEI 74-23 preserved for FRP member/interface authority and AISC 360-22 retained as comparison/reference authority.

## 20. Mandatory invariants

- Generic `316SS` does not receive a stronger value than 316L in C2-P1.
- Exact 316 or dual certification does not increase C2-P1 strength without a later approved method.
- An MTR cannot silently increase design resistance.
- Cold work cannot silently increase design resistance.
- Display-unit changes cannot change source values or fingerprints.
- Missing source data cannot become zero or a guessed value.
- Connector material cannot alter structural-member FRP-only policy.
- Connector material cannot alter the project's independent 316SS hardware policy.
- Native FRP results remain exactly preserved.
- No material record alone creates a connection-response qualification.

## 21. Approval state

**C2-M RC1 is approved as controlled implementation authority for the bounded material/source contract.**

It does not itself execute resistance and does not authorize family activation. Implement only together with the companion C2-P1 RC1 specification and RC1 goldens under the controlled Codex order.
