# FRP Master Connection
# CME-2 — C2-P2 Source and Method Reconciliation — RC1

**Status:** Approved RC1 engineering authority for the bounded isolated C2-P2 method. This document does not authorize family activation.

**Frozen repository baseline:** `20fabefa90247dd3470d4698edda1b22d017e7c6`  
**Frozen C2-M/C2-P1 implementation:** `7ef49bdbf8b9704af3d314735963069ddf7259f3`  
**Freeze tag:** `cme-2b-c2-m-c2-p1-freeze`  
**Final stainless authority:** ANSI/AISC 370-25, December 8, 2025, SHA-256 `A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`.

## 1. Purpose

C2-P2 extends the already-frozen isolated stainless flat-plate body provider into a narrowly bounded **clear-body compression, in-plane flexure, and combined axial-force plus in-plane-flexure resistance method**.

It does not activate any existing connection family and does not determine connector force distribution.

## 2. Frozen authorities carried forward

C2-P2 shall reuse without modification:

- C2-M material/source contract, SHA-256 `D7364C080B983CA7830177DE278DD30826D17770D196A72664BDD02C02DCB0A0`;
- C2-P1 RC1 R1 engineering specification, SHA-256 `1A40C852DA4AB2A7E9BE434E65CA519B5074B8D5C7433FD1BCF6DC3BE6ACB165`;
- C2-P1 RC1 R1 golden authority, SHA-256 `C0A63BB1DD20CC3985671CCEC2406FD928AC0A1541EC91D4F2E8922937D5C492`;
- generic conservative 316-family basis `Fy = 25 ksi`, `Fu = 70 ksi`;
- austenitic elastic modulus `E = 28,000 ksi`;
- native exact quantity conversion helpers;
- C2-P1 design-thickness rule;
- C2-P1 source/provenance/fingerprint separation;
- independent fastener/hardware authority;
- family isolation.

## 3. Final AISC 370-25 provisions directly inspected

The approved RC1 method uses these final-source locators only:

- **J4.4** — connecting elements in compression use Chapter E; effective length `Lc = KL`; restraint-specific effective-length authority is required.
- **J4.5** — affected/connecting elements in flexure are governed by applicable flexural yielding, local buckling, lateral-torsional buckling, and flexural rupture limit states.
- **E1** — LRFD compression resistance factor `phi_c = 0.90`.
- **E2** — effective length comes from Chapter C / effective-length or buckling analysis authority.
- **E3** — nonslender compression flexural-buckling resistance; Curve A applies to “other sections not specified” in Table E3.1.
- **Table E3.1, Curve A** — `alpha = 0.56`, `beta0 = 0.76`, `beta1 = 0.41`, `beta2 = 0.69`.
- **E4** — torsional/flexural-torsional buckling may control certain doubly symmetric members and requires separate torsional restraint/property authority.
- **F1** — LRFD flexural resistance factor `phi_b = 0.90`; `Cb` is determined from the moment diagram and is capped at 1.67; `Cb = 1.0` is a valid uniform-moment/cantilever value.
- **F9** — solid rectangular shapes: yielding/plastic moment and lateral-torsional buckling.
- **H2** — may be used for any shape in lieu of H1 for axial force plus flexure; gives separate tension and compression interaction equations.
- **Appendix 2** — Continuous Strength Method is optional and provides beneficial strain-hardening/local-buckling treatment; it is excluded from initial C2-P2.
- **H3/G9** — torsion and broader combined-action routes require additional stress/buckling authority and are excluded from initial C2-P2.

No final-source clause was found that authorizes C2-P2 to invent a moment from connector eccentricity, infer brace points from bolts/contact, or resolve material-dependent load sharing.

## 4. Flat-plate clear-body mapping

For a qualified hole-free clear strip through an unwelded A240 flat plate, define:

- local `x`: longitudinal strip/load-path axis;
- local `y`: in-plane transverse plate-width direction;
- local `z`: through-thickness direction.

For clear width `b` and C2-P1 design thickness `t`:

- `A = b t`;
- `Iy = b t^3 / 12`;
- `Iz = t b^3 / 12`;
- `ry = t / sqrt(12)`;
- `rz = b / sqrt(12)`;
- `Sy = b t^2 / 6`;
- `Sz = t b^2 / 6`;
- `Zy = b t^2 / 4`;
- `Zz = t b^2 / 4`.

Initial C2-P2 in-plane flexure is about `z`, so the F9 rectangular-shape depth is mapped to `d = b` and the F9 width parallel to the bending axis is mapped to the plate design thickness `t`.

This is a **project method mapping**, not a change in product provenance: the material remains A240/A480 plate/sheet/strip under C2-M.

## 5. Compression method

For each principal flexural-buckling axis, when E4 has been explicitly qualified as not controlling:

`Fe = pi^2 E / (Lc/r)^2`

and Curve A is applied:

- if `Lc/r <= beta0 sqrt(E/Fy)`: `Fn = Fy`;
- if `beta0 sqrt(E/Fy) < Lc/r <= 5.62 sqrt(E/Fy)`:
  `Fn = 1.2 * beta1^((Fy/Fe)^alpha) * Fy`;
- if `Lc/r > 5.62 sqrt(E/Fy)`:
  `Fn = beta2 Fe`.

Then:

- `Pn = Fn A`;
- `Pc = 0.90 Pn`.

Both principal flexural-buckling axes are checked and the smaller available strength governs.

### Mandatory E4 gate

C2-P2 shall **not** assume torsional/flexural-torsional buckling is irrelevant.

Compression may be numerically evaluated only when trusted stability authority states that Chapter E4 is not controlling for the selected clear strip and restraint condition.

If E4 is required or unresolved, C2-P2 fails closed without a compression capacity.

## 6. Flexure method

For the clear rectangular strip in in-plane major-axis bending:

`Mp = Fy Zz`
`My = Fy Sz`
`q = Lb b / t^2`

with `phi_b = 0.90`.

Using F9:

- if `q <= 0.306 E/Fy`, LTB does not apply and `Mn = Mp`;
- if `0.306 E/Fy < q <= 2.00 E/Fy`,
  `Mn = min[ Cb (1.61 - 0.36 q Fy/E) My, Mp ]`;
- if `q > 2.00 E/Fy`,
  `Fcr = 1.78 E Cb / q`,
  `Mn = min(Fcr Sz, Mp)`.

Then `Mc = 0.90 Mn`.

### Cb policy

A trusted nonuniform moment diagram may supply the source-derived `Cb`, bounded by the final F1 rules.

If favorable moment-gradient authority is absent, C2-P2 uses `Cb = 1.0` and receives no favorable credit. A client-entered arbitrary `Cb > 1.0` is not engineering authority.

## 7. Combined axial force plus in-plane flexure

Initial C2-P2 adopts **H2 in lieu of H1** as the project method because H2 is expressly permitted for any shape and avoids introducing beneficial H1-specific refinements.

Only one in-plane bending axis is supported in RC1.

### Compression + flexure

`IR = Pr/Pc + Mr/Mc`

Numerical PASS requires `IR <= 1.0`.

### Tension + flexure

Both H2 checks are retained:

`IR_tension = Mr/Mct + Pr/Pct`

`IR_compression_side = Mr/Mc - Pr/Pct`

Both must be `<= 1.0`.

For the initial hole-free direct strip:

- `Pct` is the frozen C2-P1-compatible tensile endpoint for the same clear section and full-direct-transfer classification;
- `Mct = 0.90 Fy Sz`;
- `Mc` is the F9 available flexural strength.

No tension-induced `Cb` enhancement is credited in RC1.

## 8. Eccentricity and demand boundary

C2-P2 consumes already-resolved factored resultants.

It does not calculate `M = P e` from a client-entered eccentricity and does not shift a force to a new reference point.

If upstream authority has resolved an eccentric force into signed `P` and `M` with reference/frame provenance, C2-P2 may consume those resultants.

Raw eccentricity without resolved moment authority fails closed.

## 9. Clear-body qualification boundary

C2-P2 is available only for a selected critical section that is:

- hole-free at the evaluated clear-body section;
- away from local hole-bearing/tearout paths;
- away from welds/folds/formed-angle or Tee geometry;
- away from a local prying/contact/concentrated-force zone;
- represented by a physically defined clear rectangular strip;
- supplied with trusted signed factored resultants and reference/frame;
- supplied with trusted restraint/unbraced-length authority.

Hole-bearing/net-section/block-shear behavior remains C2-P1 authority.

## 10. Deliberately excluded initial methods

RC1 excludes:

- family activation;
- force redistribution;
- common-fastener-plane response;
- prying/contact;
- raw eccentricity conversion to moment;
- biaxial flexure;
- out-of-plane/minor-axis plate flexure;
- torsion;
- simultaneous normal-force/flexure plus shear interaction;
- Chapter E4 torsional/flexural-torsional resistance calculation;
- CSM / strain-hardening strength enhancement;
- welding/fabricated shapes;
- angles;
- Tees;
- plate transverse concentrated-force/yield-line/punching methods;
- fastener resistance;
- support/FRP/foundation resistance;
- fatigue/fire/corrosion-life qualification;
- whole-connection stainless PASS.

## 11. Source conclusion

The final AISC 370-25 text is sufficient for the bounded C2-P2 numerical method adopted below.

There is no unresolved final-edition source lock analogous to the earlier C2-P1 final-source lock.

## 12. Project-method lock closure

`SL-C2P2-BOUNDED-METHOD-POLICY = CLOSED_OWNER_EOR_APPROVED_2026_09_12`

Owner/EOR approval on 2026-09-12:

> Approved: C2-P2 bounded clear-plate E3/F9/H2 method policy with Cb=1.0 default and fail-closed E4/shear/torsion boundaries.

The approved bounded policy is:

1. a qualified hole-free A240 plate strip is treated geometrically as a solid rectangular cross-section for the F9 in-plane flexure route while retaining A240/A480 product provenance;
2. E3 Curve A is used for flexural buckling of that rectangular strip only when E4 has been explicitly qualified as not controlling;
3. H2 is used in lieu of H1 for initial axial-force-plus-in-plane-flexure interaction;
4. `Cb = 1.0` is used unless a trusted source moment profile qualifies a larger source-derived value;
5. CSM is excluded;
6. E4-required/unresolved compression, torsion, biaxial/out-of-plane bending, and combined normal/shear actions fail closed.

This closes the final C2-P2 method lock. The package may be used as implementation authority for an **isolated internal C2-P2 provider only**. Existing connection-family stainless activation remains prohibited and requires later C2-R/family-stage authority.
