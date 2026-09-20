# FRP Master Connection
# CME-2 — C2 Source Reconciliation Record — RC1

**Status:** Approved engineering source reconciliation authority for the bounded C2-M/C2-P1 implementation scope. `SL-370-25-FINAL`, the code-basis bridge, and the conservative 316SS property-snapshot gates are closed. This record does **not** authorize existing-family stainless activation, angles, Tees, welding, material-dependent redistribution, or CME-3.

**Date:** 2026-09-12

## 1. Purpose

This record reconciles the currently available controlling FRP source, the project-supplied AISC 360-22 reference, publicly accessible AISC stainless source material, and publicly accessible ASTM metadata for the first bounded 316 stainless connector-body engineering slices C2-M and C2-P1.

The objective is to record the directly verified final-source provisions, the deliberately conservative project policy, and the bounded implementation authority for C2-M/C2-P1.

## 2. Frozen project boundary

CME-1 remains frozen at implementation commit `d62064a7d96ba139841c222f90b62b8e7c4601c8`, with freeze tag `cme-1-connector-material-extension-freeze`. The later CME-1F governance commit is `c4b8552e33a6d20d3f5ec5257fa741ffebc6a176`.

Structural members remain FRP-only. Connector-body material is a separate role. Bolts, nuts, and washers remain the project's existing 316 stainless hardware and remain under their independent fastener authority. Nothing in C2-M or C2-P1 changes native FRP equations, demand resolution, geometry, fastener strength, or frozen fingerprints.

## 3. ASCE/SEI 74-23 bridge issue

ASCE/SEI 74-23 Chapter 8 explicitly permits connecting elements to be steel, stainless steel, or aluminum. In the same scope paragraph it directs design of steel connection components to AISC 360. ASCE/SEI 74-23 Section 1.2 references ANSI/AISC 360-16.

Because AISC 370 did not yet have the current 2025 edition when ASCE/SEI 74-23 was issued, moving a stainless connector-body component to ANSI/AISC 370-25 is a deliberate project design-basis bridge, not something that shall be silently inferred from the words "stainless steel" in ASCE 74.

**Owner-approved RC1 bridge (2026-09-12):** for stainless connector-body resistance only, use ANSI/AISC 370-25 as the stainless-specific component design basis, while retaining ASCE/SEI 74-23 as the FRP member/interface authority and retaining AISC 360 only as the historical/reference bridge. This project engineering decision is now closed for C2-M/C2-P1; project-specific EOR adoption remains a deployment/design responsibility where required.

## 4. Final ANSI/AISC 370-25 direct source lock

The owner supplied the final published **ANSI/AISC 370-25, Specification for Structural Stainless Steel Buildings, December 8, 2025** (`A370-25W.pdf`). The document was directly inspected as the final standard and commentary.

Controlled file SHA-256 for this implementation package:

`A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`

The final text directly verifies the C2-M/C2-P1 source chain used by this package:

- Section A3.1b includes S31600 and S31603 as approved austenitic stainless alloys; S31600 shall not be welded, while the user note identifies S31603/316L and qualifying S31600/S31603 dual-certified material as weldable subject to the applicable welding requirements.
- Table A3.1f requires ASTM A240/A240M for plate/sheet/strip chemical and mechanical properties and ASTM A480/A480M for general requirements. Section A2 references the 2024 editions of both for this AISC 370-25 edition.
- Commentary Table C-A3.2 reports the ordinary minimum flat-product properties S31600: `Fu = 75 ksi`, `Fy = 30 ksi`; S31603: `Fu = 70 ksi`, `Fy = 25 ksi`. The owner-approved project snapshot remains conservatively fixed at 25/70 for all initial 316-family aliases.
- Section B4.2a directly verifies the design-thickness rule: nominal thickness above `3/16 in. (5 mm)` uses nominal; at or below that source boundary use `0.95 t_nom` unless the minimum-thickness tolerance qualifies nominal-thickness use. U.S. and SI source boundaries remain separate source identities.
- Section B4.4b directly verifies the net-area hole deduction of nominal hole dimension plus `1/16 in. (2 mm)` and the zigzag-path rule; C2-P1 intentionally defers automatic staggered-path evaluation.
- Section D3/Table D3.1 directly verifies `Ae = An U` and `U = 1.0` for direct transfer to all cross-sectional elements.
- Section J3.2/Table J3.1 directly verifies the U.S. standard-hole rows used by C2-P1, beginning at a `1/2-in.` bolt; the existing project `3/8-in.` hardware therefore remains outside automatic C2-P1 J3 table scope.
- Sections J3.3-J3.5 directly verify minimum spacing/clear spacing, minimum standard-hole edge distances, and maximum spacing/edge limits used by C2-P1.
- Section J3.10a directly verifies the initial service-deformation-considered standard-hole bearing and tearout branch and LRFD `phi = 0.75`.
- Section J4.1 directly verifies connecting-element tension yielding `Fy Ag`, `phi = 0.90`, and rupture `Fu Ae`, `phi = 0.75`.
- Section J4.2 directly verifies connecting-element shear yielding `0.60 Cv Fy Agv` with `Cv = 1.2`, `phi = 0.90`, and shear rupture `0.60 Fu Anv`, `phi = 0.75`.
- Section J4.3 directly verifies block shear, `phi = 0.75`, and `Ubs = 1.0` for uniform tension stress / `0.5` for nonuniform tension stress.

No final-text discrepancy was found that changes the approved RC1 C2-P1 equations, LRFD factors, U.S.-source standard-hole rows, design-thickness rule, or fail-closed boundary. The source lock is therefore closed without changing the previously validated numerical benchmark values.

## 5. Final-source C2-P1 method reconciliation

The following method structure is present in final ANSI/AISC 370-21 and remains materially the same in the 2025-08-22 final ANSI/AISC 370-25 text:

| Topic | 370-21 | Final 370-25 | RC1 disposition |
|---|---|---|---|
| Gross-section tension yielding | `Rn = Fy Ag`, LRFD `phi = 0.90` | directly verified | final RC1 |
| Effective-net tension rupture | `Rn = Fu Ae`, LRFD `phi = 0.75` | directly verified | final RC1 |
| Connecting-element shear yielding | `Rn = 0.60 Cv Fy Agv`, `Cv = 1.2`, LRFD `phi = 0.90` | directly verified | final RC1 |
| Shear rupture | `Rn = 0.60 Fu Anv`, LRFD `phi = 0.75` | directly verified | final RC1 |
| Block shear | rupture branch limited by the `Cv Fy Agv` branch, LRFD `phi = 0.75`; `Ubs` uniform/nonuniform | directly verified | final RC1 |
| Design thickness for plate/flat bar | nominal above 3/16 in.; 0.95 nominal at/below boundary unless verified tolerance permits nominal | directly verified | final RC1 |
| Net hole deduction | nominal hole plus `1/16 in. (2 mm)` | directly verified | final RC1 |
| Effective net area | `Ae = An U`; direct full-element transfer case gives `U = 1.0` | directly verified | final RC1 |
| Bearing/tearout, service deformation considered | bearing coefficient `1.25`; tearout uses `l1/(2dh)` and same coefficient; LRFD `phi = 0.75` | directly verified | final RC1 |
| Standard-hole spacing/edge table structure | present | directly verified | final RC1 |

Direct final 370-25 verification now supersedes the earlier draft/cross-edition inference.

## 6. AISC 360-22 is not a numerical substitute

The owner supplied AISC 360-22. It is useful as a compatibility and negative-control source, but its connecting-element shear rule is not identical to the stainless rule.

For example, AISC 360-22 J4 shear yielding uses `Rn = 0.60 Fy Agv` with LRFD `phi = 1.00`. The stainless AISC 370 route uses `Rn = 0.60 Cv Fy Agv`, `Cv = 1.2`, with LRFD `phi = 0.90` in the inspected 370-21 and 370-25 public-review provisions.

Therefore, feeding 316 material properties into the AISC 360-22 connecting-element equations is not an acceptable C2-P1 implementation strategy.

## 7. Initial bolt-hole/detailing source domain

For the initial U.S.-source C2-P1 automatic standard-hole scope, the final ANSI/AISC 370-25 tables provide rows for nominal bolt diameters:

- 1/2 in. -> standard hole 9/16 in.; minimum table edge distance 3/4 in.
- 5/8 in. -> standard hole 11/16 in.; minimum table edge distance 7/8 in.
- 3/4 in. -> standard hole 13/16 in.; minimum table edge distance 1 in.
- 7/8 in. -> standard hole 15/16 in.; minimum table edge distance 1-1/8 in.
- 1 in. -> standard hole 1-1/8 in.; minimum table edge distance 1-1/4 in.

The table does not provide an automatic 3/8-in. row. C2-P1 shall not extrapolate one merely because ASCE/SEI 74-23 permits FRP connection bolts down to 3/8 in. A future separately approved source rule may broaden this boundary.

For automatic C2-P1 geometry, center spacing must satisfy the inspected minimum of `(8/3)d` and the clear distance between holes/slots must not be less than `d`. The preferred `3d` spacing is treated as a preference, not the code minimum. The maximum center-to-edge distance is `min(12t, 6 in.)`; longitudinal spacing of elements in continuous contact is `min(24 t_thinner, 12 in.)`.

C2-P1 deliberately supports standard round holes only and does not automatically use the source exceptions for reduced edge distance that require EOR judgment.

## 7A. Design-thickness rule

The inspected final ANSI/AISC 370-25 text and final AISC 370-21 use a stainless-specific **design thickness** for plates/flat bars. For C2-P1 RC1:

- nominal thickness greater than `3/16 in. (5 mm)` uses nominal thickness as design thickness;
- nominal thickness at or below `3/16 in. (5 mm)` uses `0.95` times nominal thickness unless a verified product minimum-thickness tolerance of no more than 5% qualifies nominal-thickness use;
- the initial automatic method conservatively uses the `0.95` rule at or below the boundary unless that tolerance authority is present.

This rule is directly verified in final ANSI/AISC 370-25 and `SL-370-25-FINAL` is closed.

## 8. Flat-product/property source state

Final ANSI/AISC 370-25 Section A2 references **ASTM A240/A240M-24** and **ASTM A480/A480M-24** for this standard edition. Table A3.1f requires A240/A240M for plate/sheet/strip chemical and mechanical properties and A480/A480M for general requirements.

Final AISC 370-25 Commentary Table C-A3.2 independently reports the ordinary flat-product minima used to corroborate the owner-approved conservative snapshot:

- S31603 / 316L: `Fu = 70 ksi`, `Fy = 25 ksi`;
- S31600 / 316: `Fu = 75 ksi`, `Fy = 30 ksi`.

C2-M/C2-P1 nevertheless retain the owner's deliberately conservative **project-controlled U.S.-source snapshot** `Fy = 25 ksi`, `Fu = 70 ksi` for all accepted 316-family aliases. The software shall identify that snapshot as project-controlled and shall not claim MTR overstrength or exact-S31600 credit.

The previous discovery of later ASTM A240 editions is not used to silently advance the edition referenced by AISC 370-25. Future source updates require a separately controlled revision.

## 9. C2-M conservative property snapshot

The proposed initial project material option remains client-facing `316 Stainless Steel` and accepts common client language `316SS`, `316`, `316L`, and `316/316L`.

To avoid making the ordinary user's capacity depend on ambiguous client nomenclature or MTR overstrength, C2-P1 uses one conservative initial design snapshot for all accepted 316-family aliases:

- U.S.-source `Fy = 25 ksi`;
- U.S.-source `Fu = 70 ksi`;
- no cold-work strength enhancement;
- no MTR strength enhancement;
- exact certified grade/dual-certification is retained as provenance when known.

This is intentionally conservative for S31600 material and exactly matches the ordinary S31603/316L minimum snapshot in the corroborating source evidence. A future advanced exact-grade method may separately credit S31600 after direct source locking and approval.

## 10. Source-unit policy

The source property system is part of engineering provenance. The initial project snapshot is U.S.-source.

A UI change to SI converts the stored U.S. value exactly for calculation/display. It does **not** replace 25 ksi with the separately tabulated 170 MPa ASTM value or 70 ksi with 485 MPa. Conversely, a future genuinely SI-source material record would preserve its SI source identity rather than being regenerated from a U.S. table.

The same rule applies to source-defined hole dimensions. A U.S.-source 1/2-in. bolt displayed in SI retains the U.S. standard-hole identity and converts 9/16 in. exactly; it is not remapped to a different metric bolt/hole table.

## 11. Hardware separation

The project hardware policy remains: bolts, nuts, and washers are 316 stainless steel. Their existing ASTM/source/thread/grip/washer authority remains independent.

C2-P1 uses bolt/hole geometry and an already-resolved bearing demand but does not substitute connector-body `Fy`/`Fu` for bolt strength, change bolt material, or cure any existing fastener source gap.

## 12. Mixed FRP/stainless response boundary

An isolated stainless plate limit-state calculation does not prove that an existing FRP connection has the correct stainless branch force distribution. C2-P1 therefore accepts only already-resolved, provenance-bearing plate/bolt demands.

No existing family shall be activated for stainless merely because the isolated plate resistance provider returns a numerical PASS. Material-dependent load sharing, common-fastener-plane forces, contact/prying, receiving-member behavior, and FRP local checks remain separate required authorities.

## 13. Source/adoption locks — CLOSED

**SL-370-25-FINAL — CLOSED 2026-09-12:** final ANSI/AISC 370-25 was directly supplied and reconciled. No C2-P1 numerical or applicability discrepancy requiring a benchmark change was found.

**SL-CONSERVATIVE-316SS-PROPERTY-SNAPSHOT — CLOSED BY OWNER DECISION 2026-09-12:** the owner explicitly adopted the project-controlled conservative U.S.-source snapshot `Fy = 25 ksi`, `Fu = 70 ksi`. Final AISC 370-25 Commentary Table C-A3.2 independently corroborates this as the S31603/316L flat-product minimum and confirms S31600 is stronger in the ordinary table. No higher strength is credited.

**SL-CODE-BASIS-BRIDGE — CLOSED BY OWNER DECISION 2026-09-12:** the owner approved ANSI/AISC 370-25 as the stainless connector-body component design basis, with ASCE/SEI 74-23 authoritative for FRP members/interfaces and AISC 360-22 retained as comparison/reference authority.

All source/adoption gates required for the bounded C2-M/C2-P1 implementation are closed.

## 14. Approved disposition

C2-M RC1 and C2-P1 RC1 are approved engineering implementation authorities for the **isolated bounded stainless flat-plate scope only**. The companion RC1 golden benchmark file remains the implementation oracle.

This approval does **not** authorize any existing shear/moment family to dispatch to stainless, any public/UI stainless capacity result, any change to frozen CME-1 readiness responses, angles, Tees, welding, compression/stability, combined-action interaction, prying/contact, material-dependent branch redistribution, or CME-3 family activation.
