# FRP Master Connection
# CME-2 Core C2-R / C2-A / C2-T Source and Method Reconciliation - RC1

**Status:** Approved RC1 engineering authority for isolated C2-R, C2-A, and C2-T implementation. No public family activation authority.

## 1. Frozen baseline

- Governance baseline: `88961da28de3421722290c2bf78af0c6191b81a1`.
- Commit count: `130`.
- Frozen C2-P2 implementation: `61855bda1f76bbf11a85ae58664ed81bbc8ea419`.
- Freeze tag: `cme-2c-c2-p2-freeze`.
- Freeze tag object: `7861f351e88fdfa7a65e6166dc941b2476c8e0b8`.
- Final ANSI/AISC 370-25 SHA-256: `A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`.
- ASCE/SEI 74-23 SHA-256: `A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`.
- Erratum 1 SHA-256: `5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`.
- Combined C2-R/A/T readiness audit SHA-256: `B664C1FCE58C53575952A44EE2A11C474801821DF7A8C49C45890225DE42925C`.
- C2-P2 freeze/core-audit completion report SHA-256: `225DBD9C5A8A29507A0628029CABA8CDED83AA04E20A375DAF5969E6D2896A02`.

Frozen C2-M, C2-P1, C2-P2, FRP, hardware, foundation, route, and historical behavior remain immutable dependencies.

## 2. Owner/EOR decision

Owner/EOR approved on 2026-09-12:

> Approved: use unwelded hot-rolled/extruded ASTM A276/A276M + A484/A484M 316-family shapes as the initial C2-A/C2-T fabrication domain; retain conservative Fy=25 ksi/Fu=70 ksi; exclude formed, laser-fused, welded/built-up and other fabrication routes; adopt the bounded C2-R trusted-response-envelope policy with reuse only of proven material-neutral transport/conservation mechanics; keep angle/Tee torsion and unqualified contact/prying/sharing fail-closed.

This closes the product/fabrication and bounded-response project-method decisions required by the read-only core audit.

## 3. Initial product domain

The only supported stainless Angle/Tee product route in RC1 is:

`A276_A484_HOT_ROLLED_EXTRUDED_UNWELDED_316_FAMILY_RC1`

Required identity:

- product form: structural angle or Tee;
- production route: hot-rolled or extruded;
- chemistry/mechanical standard: ASTM A276/A276M;
- general requirements: ASTM A484/A484M;
- alloy family: approved 316-family identity under the existing C2-M alias/provenance policy;
- permitted condition/finish for RC1: annealed / hot-finished (`A` or `HF`);
- fabrication: unwelded monolithic shape.

Explicitly excluded:

- ASTM A479/A479M as a project-selected route in RC1, even though AISC 370 permits it as an alternative;
- cold-finished/strain-hardened shape credit;
- formed/bent flat-product angles;
- laser or laser-hybrid A1069 shapes;
- welded or otherwise built-up shapes;
- cut Tees from W/S/I parent shapes;
- any route requiring welding authority;
- MTR overstrength;
- cold-work strength uplift;
- CSM strength enhancement.

No built-in dimensional catalogue or A484 tolerance table is authorized in RC1. Production must consume a trusted section/product snapshot with actual source identity and section properties. Test fixtures may use synthetic trusted section records, but those fixtures are not production qualification.

## 4. Material properties

Initial numerical project basis for every accepted 316-family alias:

- `Fy = 25 ksi`;
- `Fu = 70 ksi`;
- `E = 28,000 ksi`;
- `G = 10,800 ksi`.

These values are deliberately conservative relative to the AISC 370 commentary minimum-property table for ASTM A276/A276M hot-finished/annealed 316 and 316L. Exact known S31600, S31603, or dual certification does not increase RC1 strength.

The existing C2-M commercial-label and provenance separation remains authoritative.

## 5. Final AISC 370-25 provisions used

The approved package uses these final-source locators:

### Product/source

- A3.1a and Table A3.1a: hot-rolled/extruded structural shapes; A276/A276M or A479/A479M chemistry/mechanical properties and A484/A484M general requirements.
- Commentary Table C-A3.3: A276/A276M bars/shapes mechanical-property minima and condition dependence.
- Table User Note A3.1: austenitic `E = 28,000 ksi`, `G = 10,800 ksi`.

The project selects only A276/A276M + A484/A484M for RC1.

### Section classification

- B4.1a: axial-compression nonslender limit for angle legs and Tee flange/stem unstiffened elements:
  `lambda_r = 0.41 sqrt(E/Fy)`.
- B4.1b: flexural slender limit for Tee flanges/stems and other unstiffened elements:
  `lambda_r = 0.41 sqrt(E/Fy)`.
- B4.1a element widths: full angle leg, half Tee flange width, full Tee stem depth.

F10 applies only when the applicable section has no slender compression element.

### Tension

- D2: gross yielding `Pn = Fy Ag`, LRFD factor 0.90.
- D2: net rupture `Pn = Fu Ae`, LRFD factor 0.75.
- D3: `Ae = An U`.
- D3 Case 1: `U = 1.0` only when load is transmitted directly to every cross-sectional element.
- D3 Case 2: `U = 1 - x/l` for applicable open-section partial connection.
- D3 Case 8: single/double angles with four or more fasteners per line may use `U = 0.80`; with three fasteners per line `U = 0.60`; fewer use Case 2. If Case 2 is also applicable, the larger permitted value may be used.
- D3 Case 7 is not authorized for RC1 Tees because it specifically addresses Tees cut from W/S shapes, which are excluded by the selected product route.

Net area is a trusted resolved geometry input. RC1 does not perform staggered-path search.

### Compression

- E2: trusted effective lengths.
- E3: nonslender flexural buckling.
- Table E3.1 Curve A for "other sections not specified".
- E4: torsional/flexural-torsional buckling applies to Tees and single equal-leg angles without slender elements.
- E5: the simplified single-equal-leg-angle eccentricity-neglect procedure is not automatically invoked for connector angles.

C2-A/C2-T RC1 evaluate E3 internally but require a trusted E4 elastic-buckling stress record from an approved analysis/source. The provider applies Curve A to that trusted E4 `Fe` and takes the lowest available compression strength.

For every Curve A evaluation, the already-frozen C2-P2 conservative project policy is retained:

`Fn_used = min(Fy, Fn_raw)`.

Unequal-leg angle compression is fail-closed in RC1 because the final E4 scope does not establish the required complete compression method for that shape.

### Flexure

- F1: LRFD flexural factor 0.90.
- F10: other shapes without slender elements, including Tees and single angles.
- F10 yielding: `Mn = Fy Smin`.
- F10 lateral-torsional buckling:
  - no LTB when `Lb <= Ly`;
  - inelastic interpolation for `Ly < Lb <= Lr`;
  - elastic branch `Mn = beta_LT Fcr Smin` for `Lb > Lr`;
  - cap `Mn <= Fy Smin`.
- F2-6 supplies `alpha_LT = 0.60 - 0.40[(Lb-Ly)/(Lr-Ly)]`.
- Table F2.1 supplies austenitic `beta_LT = 0.82`.

Because F10 states that `Fcr` is determined by analysis, RC1 consumes trusted `Ly`, `Lr`, and, where needed, `Fcr` stability authority rather than inventing a universal Angle/Tee LTB formula.

### Shear

- G1 LRFD shear factor 0.90.
- G6 applies to other singly/doubly symmetric shapes and, per final commentary, to single-angle sections.
- `Vn = 0.6 Cv2 Fy Aw`.
- Rolled Angle/Tee dimensions parallel to the shear force may use the full depth/width in the G6 shear-area definition.
- G2.2 supplies the four `Cv2` branches.
- For unstiffened elements RC1 uses `kv = 1.2`; `kv = 5` is permitted only when a trusted supported shear-element record establishes a stiffened element.

No tension-field post-buckling enhancement is introduced by C2-A/C2-T.

### Combined axial force and flexure

- H2 may be used for any shape in lieu of H1.
- Tension uses both H2-1 and H2-2.
- Compression uses H2-3.
- All interaction terms are positive magnitudes.

RC1 supports combined axial force plus flexure about one or both principal axes when no simultaneous shear or torsion interaction is required.

### Torsion and prying/contact

- Chapter G states that angles and Tees subjected to torsion are outside its scope.
- Therefore any nonzero required torsion fails closed in C2-A/C2-T RC1.
- J3 requires bolt tensile demand to include deformation-induced prying where applicable, but it does not create a universal Angle/Tee prying/contact solver.

Prying/contact/sharing is response authority under C2-R, not a body-strength multiplier.

## 6. ASCE/SEI 74-23 response authority retained

The frozen Calculation Slice 2 engineering authority identifies ASCE/SEI 74-23 Commentary Table C8-1 row-load proportions.

For a qualified FRP-to-steel bolted interface:

- 2 rows: `[0.60, 0.40]`;
- 3 rows: `[0.50, 0.30, 0.20]`.

The existing row definitions/order remain authoritative.

RC1 does not extrapolate these prescriptive fractions beyond two or three rows.

## 7. C2-R bounded response policy

C2-R is a trusted-response-envelope validator and provenance authority. It is not a new nonlinear connection solver.

Accepted response modes are:

1. `MATERIAL_NEUTRAL_TRANSPORT`
   - reference shifting/summation/conservation only;
   - no redistribution created.

2. `ASCE74_FRP_STEEL_PRESCRIBED_ROWS`
   - only within the frozen two-/three-row ASCE scope and geometry/applicability rules;
   - stainless connector stock is treated as the steel side of the FRP-steel material pair.

3. `NATIVE_EQUAL_BOLT_STIFFNESS_ECCENTRIC`
   - consumes an existing native resolved-demand snapshot;
   - only where the accepted native equal-bolt-stiffness rigid-group assumptions remain applicable;
   - no slip/contact/prying/material-stiffness redistribution may be hidden behind this mode.

4. `NATIVE_LOCKED_SYMMETRY`
   - only for a route that already contains an explicit native symmetry gate;
   - branches must remain identical in material, geometry, thickness, fasteners, fixture, and action symmetry.

5. `QUALIFIED_EXTERNAL_MATERIAL_SPECIFIC_RESPONSE`
   - complete trusted EOR/test/analysis response with source/model/domain provenance.

Anything else that requires material-dependent stiffness, contact, prying, slip, unequal sharing, active-set changes, or unqualified receiver behavior fails closed.

## 8. Common-fastener conservation

A trusted response envelope shall preserve one physical shaft identity.

For every shared shaft:

- ordered material/body/member layers are unique;
- interface force vectors are retained by physical plane;
- cumulative shaft cuts are derived from the actual ordered layer forces;
- final vector closure is exact within the source numerical authority;
- one shaft capacity is not duplicated per displayed layer/body alias.

The validator proves conservation only. It does not decide an unknown load allocation.

## 9. Contact/prying contract

When contact or prying is physically relevant, C2-R requires a trusted source record.

The record shall distinguish:

- direct bolt tension;
- source prying contribution, if separately reported;
- total bolt tension;
- whether prying is already included in the source total;
- active/inactive contact domains;
- nonnegative compression-only contact resultants;
- physical footprint/reference;
- response/model provenance.

If a trusted source total already includes prying, no additional prying factor or increment is permitted.

If contact/prying is required but unqualified, response fails closed.

## 10. C2-A and C2-T local/full-body separation

C2-A/C2-T can consume trusted frozen local-region snapshots from C2-P1/C2-P2 without importing or modifying those frozen production modules.

Such snapshots are optional independent checks and remain bound to:

- exact body/region identity;
- material/source fingerprint;
- geometry and thickness;
- demand/reference/frame;
- P1/P2 provider fingerprint;
- applicability status.

A local P1/P2 PASS is not a full Angle/Tee PASS.

Full shape tension/compression/shear/flexure/H2 checks use C2-A/C2-T authority.

## 11. Deliberate RC1 exclusions

RC1 excludes:

- public family activation;
- frontend stainless editor changes;
- public C2-R/C2-A/C2-T API routes;
- arbitrary client-created trusted response/source records;
- welded/formed/laser/cut-Tee product routes;
- A479 project route;
- cold-finished/strain-hardened strength credit;
- unequal-leg angle compression;
- slender Angle/Tee section design;
- Angle/Tee torsion;
- H3 combined torsion/shear/axial/flexure;
- simultaneous axial/flexure plus shear interaction;
- unqualified contact/prying/sharing;
- automatic F10 LTB analysis;
- automatic E4 elastic-buckling analysis;
- automatic shape catalogue/tolerance generation;
- Tee flange/junction local plate mechanisms when not separately covered by an approved local-region method;
- Angle heel/local prying mechanisms when not separately covered by a qualified response/local method;
- CSM;
- fatigue/fire/corrosion-life qualification;
- fastener/foundation/FRP-member authority changes;
- whole-connection stainless PASS.

## 12. Engineering conclusion

The owner/EOR decision plus final AISC 370-25 and retained ASCE/SEI 74-23 authority are sufficient for one bounded isolated C2-R/C2-A/C2-T implementation package.

No additional owner decision is required before isolated implementation.

Family activation remains a later CME-3 stage and may only enable configurations whose response, product, body, local-region, fastener, FRP-member, support, and foundation authorities are all satisfied.
