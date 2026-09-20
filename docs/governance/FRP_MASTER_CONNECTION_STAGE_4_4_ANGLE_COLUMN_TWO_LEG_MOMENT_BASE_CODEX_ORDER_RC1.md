# FRP Master Connection - Stage 4.4
# Angle Column Base Moment Connection: One Base Angle on Each Different Leg
## Controlled engineering integration specification and Codex implementation order - RC1

Recommended Codex effort: EXTRA HIGH.

Product: `ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION`
Contract: `4.4-RC1`
Category: `Moment Connections`
Workspace label: `Angle Column Two-Leg Moment Base`

This order authorizes a physical product implementation, not a separate planning-only slice. It includes one vertical FRP angle column, two FRP base-angle connectors attached to different column legs, member bolts, two foundation attachment groups, a finite concrete pedestal, numerical wrench/source validation, the applicable inherited connection checks, and a complete frontend workflow.

It does not authorize an unqualified automatic stiffness/contact/prying/load-sharing model. The complete base-response boundary described below is essential: geometry and equilibrium alone cannot determine how an unsymmetrical column, two perpendicular connectors, and direct column-end bearing share a general load. Missing production qualification is an explicitly implemented result state, not a reason to stop development or to invent a force split.

## 1. Starting identity and accepted evidence

Require the active implementation work area to start from:

`1faa1ff522d0e0a39a42e2dc2d3974b5dba98479`

Starting reachable commit count in the full development repository: **114**.

Latest frozen stage: Stage 4.3. Verify the annotated tag:

`stage-4.3-wi-beam-frp-support-moment-connection-freeze`

Its peeled commit must equal the starting SHA. Resolve its actual annotated tag object from Git; this order does not invent that object's SHA. Verify all **eleven** existing freeze tags against the established local/remote registers. Earlier tags retain their historical objects and targets.

Owner-reported accepted baseline evidence: CI #109, attempt 1, Backend Ubuntu/Windows and Frontend Ubuntu/Windows green; 3,571 backend and 642 frontend tests; configured 100% coverage; no audit findings. The supplied completion evidence is not a substitute for Codex's actual baseline/ref verification.

Expected implementation subject:

`feat: add angle-column two-leg moment base connection`

Normally one new commit, final full-history count **115**. The bounded maintenance-successor provisions in section 30 are the only exception; count must be reported from Git, not fabricated or maintained by rewriting published history.

The underlying Stage 4.3 engineering implementation is `2e4416a4dbd0b99c6a7280f6576264c37c09101a`; its later security/test/governance successors remain accepted. Do not restart an older stage using the August handoff's obsolete baseline.

Repository destination:

`https://github.com/baraa-misto/frp-master-connection.git`

Branch: `main`. Use the existing repository-local author identity. Do not inspect or modify sibling projects.

## 2. Two-file controlling package

The only new owner attachments required are:

1. This order/specification.
2. `FRP_MASTER_CONNECTION_STAGE_4_4_ACCEPTANCE_MATRIX_RC1.json`.

Acceptance-matrix SHA-256:

`A09FB76C07AB12AB9C435CAD1B29806D4B4DB839B12191444BE4507DFE0D9BB8`

The matrix contains **96 requirements T44-001 through T44-096**, **14 independent reference fixtures F44-01 through F44-14**, a **64-case source-absent geometry/load/unit sweep**, and at least **24 source-present test-only integration cases**. These are acceptance obligations, not mandated pytest/Vitest function counts.

The approved SHA-256 of this order is supplied separately in the owner handoff. Verify that digest and the final sentinel; do not embed a self-referential order hash. Matching the explicitly supplied digest needs no additional approval.

Read both files completely. Check unique IDs, contiguous ranges, references, exact signs, units, and branch/reference identities before mutation. New files use UTF-8, LF and no trailing whitespace. Do not normalize historical byte-controlled documents.

## 3. Sources, evidence, and source limits

### S1 - supplied ASCE/SEI 74-23

SHA-256:

`A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`

Review the actual pages, including relevant figures/tables, at these locators:

- Sections 1.4.2 and 1.7.2: analysis compatibility and column-base bearing/detailing (printed pp.4-5; PDF pp.19-20).
- Sections 2.3.2, 2.4, 2.9 and 2.10: qualification, material/factor, eccentricity and net-section requirements (printed pp.7-11; PDF pp.22-26).
- Sections 8.1-8.3: connection applicability, eccentricity, hardware, bolt forces, local FRP checks and prying requirements (printed pp.31-36; PDF pp.46-51).
- Section 8.4: transfer of column forces/moments into footings/foundations, with the cited ACI/AISC design boundary (printed p.37; PDF p.52).
- Commentary C8.3.4 and C8.4: FRP prying/through-thickness limitations, column bases, bearing preparation and external anchorage scope (printed pp.96-97; PDF pp.111-112).

Section 8.4 is not a complete numerical anchor/contact solver in this package. Do not infer one from a reference to ACI/AISC. FRP connector qualification and actual prying/normal response remain required where applicable.

### S2 - supplied Erratum 1

SHA-256:

`5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`

Effective January 13, 2026. The supplied correction concerns the Chapter 5 transverse-modulus description; it does not supply a base-response model. The official book listing consulted for preparation identifies that erratum. If a new official correction is found during implementation, assess actual relevance without silently changing the approved source basis.

Official publication locator: `https://ascelibrary.org/doi/book/10.1061/9780784415771`.

### S3 - baseline repository authorities

Reuse the accepted Stage 3.7 angle-column/base geometry and shear-family infrastructure where applicable, Slice 7 angle core/FRP provider, Slice 8 in-plane wrench demand, native bolt/local-FRP checks, Stage 4.2 external foundation handoffs, and Stage 4.3 response-source/trace infrastructure. Resolve exact versioned paths, source IDs, numerical contexts and callable APIs from the **current baseline**.

Stage 3.7 shear-only allocation is not authority for moment sharing between perpendicular legs. Stage 4.2 paired web angles are not the same physical arrangement. Stage 4.3 normal-response source infrastructure may be reused, but its beam/support source domain cannot silently qualify this different base topology.

The new topology, source contract, integration rules and software controls below are project decisions. They are not additional prescriptive ASCE equations. Reference fixtures are independent mathematical checks, not manufacturer strengths, calibration data, or Section 2.3.2 qualification.

Preparation limitation: ChatGPT checked the supplied source/specification material and reference arithmetic, but did not execute this repository's current production APIs. Codex must complete the actual compatibility audit before implementation. Do not claim otherwise.

Use accessible source copies already supplied to the same project. Do not ask for duplicate PDFs/packages unless their actual required bytes are inaccessible. Do not commit licensed PDFs or long copied standard passages.

## 4. Scope and engineering outcome

Implement one vertical L-section column of accepted pultruded FRP, with two perpendicular legs and constant accepted thickness. Equal-leg and unequal-leg examples are required using the existing profile domain; the new product does not extend overall member-strength applicability.

Exactly one base-angle connector attaches to the exterior broad face of each column leg. Each connector has a vertical member leg and a horizontal foot projecting outward onto the pedestal. There are two member-bolt groups and two distinct foundation attachment groups. No two brackets on the same column leg, no shared bolt through both perpendicular groups, and no hidden base plate/backing plate/sleeve/doubler.

RC1 covers signed axial uplift/compression, two horizontal shears and bending about two leg-parallel horizontal axes. Independently applied torque about the vertical axis is rejected at the column-end input in RC1. Reference-generated vertical-axis moment is retained and exported. Do not call the leg-parallel axes the section's principal axes.

Numerical scope includes exact total reference transport, validation of qualified complete base responses, two connector-core transports, applicable member-bolt/local FRP checks when their demand is resolved, and signed foundation handoff. Concrete/anchor strength, overall angle-column stability/strength, serviceability classification, and complete building/foundation analysis remain external or not evaluated.

A workspace with missing sources is useful and permitted, but it must truthfully show which quantities are unavailable. Passing arithmetic fixtures does not make the unsupported production design adequate.

## 5. Canonical coordinates and signs

Use an orthonormal right-handed base frame `(X,Y,Z)`:

- `Z` is upward, parallel to column extrusion.
- `X` runs along column leg 1 from heel toward its toe.
- `Y` runs along column leg 2 from heel toward its toe.
- `X cross Y = Z`.

For the sharp-corner reference geometry the outer-heel reference `O=(0,0,0)` lies on the foundation top plane. The cross section is the union `[0,bx] x [0,t]` and `[0,t] x [0,by]`, with overlap counted once. The existing profile representation, including any actual fillets, remains production authority. Do not silently remove fillets or change native centroid serialization to match a reference fixture.

The applied load reference is the **native actual column-section centroid at the physical lower end**, `C=(xc,yc,0)` in the default flush-contact configuration. Inputs are actions exerted by the column on the base:

`F_C = (Vx,Vy,N)`

`M_C = (Mx,My,0)`.

Positive `N` is uplift; negative is compression. Moments follow the physical right-hand rule. These signs are not the W/I beam workspace's structural major-moment sign mapping.

The foundation report reference is `O` unless an explicitly named report-only reference is selected. Report column-on-base/base-on-foundation and opposite reaction separately. They are not two loads to add together.

Inputs represent already-resolved factored actions. No load-combination generator, self-weight inference, preloading, bolt pretension or thermal action is added in RC1.

## 6. Nominal contact geometry and constructive presets

RC1 nominal geometry is a prepared, flush column end and connector feet on a planar foundation top. No freely editable positive column gap or floating axial-load path is introduced here. Contact may open under load; nominal touching is not proof that a patch remains compressed.

Represent the real column-end footprint separately from each connector foot. Do not replace the L footprint by its bounding rectangle. A resultant reference may lie outside a nonconvex footprint without implying that pressure acts in empty space; physical pressure/contact records must still use real material patches.

Provide constructive engineering test presets, not claims of adequate designs:

- Equal column: outside legs 8 in / 8 in, thickness 0.5 in.
- Unequal column: outside legs 8 in / 6 in, thickness 0.5 in.
- Column display length: 18 in; presentation only.
- Pedestal: 32 in x 32 in plan, depth 12 in, top at Z=0; centered about the report origin for display, subject to actual geometry checks.
- Each base angle: length 6 in, vertical member leg 6 in, foot width 6 in, thickness 0.5 in, inside radius 0.25 in, with no fictitious end relief.
- Connector extrusion centers: midpoint of the matching column leg; changing either connector is an independent input, not automatic load symmetry.
- Member patterns: 2 across extrusion x 2 vertically, gauge 3 in, vertical pitch 2 in, vertical centroid 3 in above nominal bottom.
- Foundation patterns: 2 across extrusion x 2 outward, gauge 3 in, outward pitch 2 in, outward centroid 3 in from the nominal column exterior-face line.
- Nominal member bolts and anchor shanks: 0.5 in; physical round holes 0.563 in for this U.S.-source preset; geometric embedment 4 in. Existing native hardware/source policies control remaining details.

The reference-fixture support points are independent arithmetic examples; they are not substituted for the preset anchor-group centroids.

Before mutation verify these constructive presets against the actual baseline solid/fillet/hardware implementation. Adapter placement must preserve the intended interfaces, not force a presumed core origin that differs from its contract. Within this order, a **geometry-only preset adjustment** for actual fillet/hardware clearance is permitted if it preserves the two-exterior-leg topology, supported scope and accepted material/factor values. Record exact changes and regenerate only the new Stage 4.4 fixture catalogue; do not change this order's reference arithmetic or older goldens. A preset adjustment is not permission to manipulate material/factors to obtain a desired design status.

## 7. Physical connector frames and bolt paths

Use each connector's existing local `(A,B,C)` core frame. For the canonical orientation:

- Connector 1: `A=+X`, `B=+Z`, `C=-Y`.
- Connector 2: `A=-Y`, `B=+Z`, `C=-X`.

Both frames are proper rotations with determinant +1, not a reflection. The matrix fixture gives their columns/row representation. Actual origins and member/foot reference offsets come from canonical geometry and the accepted core contract.

Member bolts pass through the upright connector leaf and the matching column leg, with washers and accessible head/nut locations on the actual outer faces. Two penetrated leaves normally mean one shear interface, not automatic double shear. Do not let a shank cross the other column leg, heel, unrelated bracket, empty fictitious material, or a forbidden hardware envelope.

Foundation attachments are vertical shanks through the foot into the represented pedestal, using existing approved geometric anchor representation. Do not fabricate a nut under a deep pedestal, a hidden backing plate, or anchor pullout capacity from displayed embedment. An embedment dimension is geometry only.

Use actual round-hole and hardware containment, row/line ordering and free boundaries. The selected connector's LW axis is its horizontal extrusion A, while the column's LW is vertical Z. Their material directions must not be copied from each other.

## 8. Exact transport - available independently of load allocation

For an input wrench in a local proper frame Q at global point r_R, express it at global report point r_O by:

`F_O = Q F_R`

`M_O = Q M_R + (r_R - r_O) cross F_O`.

The opposite reaction is `(-F_O,-M_O)` at the same reference. Use exact rational arithmetic over already-authoritative finite native values for new Stage 4.4 shifts/sums; no binary float engineering decisions. Preserve inherited numeric contexts when invoking accepted engines.

The total connection contribution to the foundation is available from the input wrench even when branch responses are unknown. Label it **required total foundation action**, not calculated individual anchor reactions or foundation capacity.

For example, the general reference fixture `r_R=(2,1,3) in`, `F=(5,-3,-20) kip`, `M_R=(60,40,0) kip-in` gives `M_O=(49,95,-11) kip-in` at O=0. This is an arbitrary reference-arithmetic fixture, not the default angle centroid or a prescribed load allocation.

Do not discard reference-generated Mz just because independently applied input Mz is outside RC1. Do not invent an angle shear-center location or accept shear-center-referenced actions without a separately controlled transform.

## 9. Complete base-response authority: no automatic 50/50 split

A general five-action base load does not uniquely determine two full connector wrenches plus column-end contact. Two equal geometric legs do not prove equal loads under biaxial moments, uplift, different connector stiffness, different bolt details or partial contact.

Use a Stage 4.4-specific **complete two-leg-base response** source/adapter, conceptually:

`QUALIFIED_ANGLE_COLUMN_TWO_LEG_BASE_RESPONSE_RC1`.

The exact symbol/path may follow the repository convention. Reuse Stage 4.3 source infrastructure without assigning its old source domain to this new topology.

Permitted production response authority is either:

1. a server-controlled, applicable qualified response record for this exact base assembly/load domain; or
2. an already accepted analysis provider whose existing verified domain explicitly includes this topology, contact state and action combination.

Do not develop an unapproved automatic spring, rigid-plate, plastic-hinge, stiffness-weighted, N/n+M/I, section-half, or M/z base distribution in this order. An elastic L-section stress diagnostic is not automatically the load allocation to two physical brackets. Stage 3.7's shear allocation cannot simply be extended to moments.

If no applicable response exists, return `SOURCE_REQUIRED` for branch allocation/complete base response while still giving valid geometry and total foundation actions. Do not run attachment resistance on invented branch demands. This is expected production behavior; implement it and the verified-source path without further owner approval.

## 10. Response-record content and validation

The source must bind to actual geometry, section/fillet identity, connector-to-leg assignment, each material record, all bolt/anchor patterns and relevant hardware, nominal contact surfaces, complete load vector/sign/reference, source version/hash, analysis/qualification basis and applicability domain.

Required content:

- full column-on-connector member-interface wrench for connector 1;
- full column-on-connector member-interface wrench for connector 2;
- direct column-on-foundation contact contribution, including explicit inactive/zero certification when applicable;
- coordinates and proper frames for each record;
- physical contact state/footprint and compression-only admissibility evidence;
- proof/validation basis for compatibility, stiffness, load path and demanded prying/normal response;
- scope-specific available/unavailable coverage;
- qualified-source provenance distinct from a user-typed label.

Every nonzero branch needed by the model must be present. A missing field is not zero. If a branch is inactive the record must explicitly identify it and justify that state for this load. No automatic load-domain interpolation/extrapolation unless the already accepted source contract authorizes it.

Mathematical equilibrium is necessary, not sufficient evidence of qualification. The two equilibrated allocations in F44-12 deliberately prove why an arbitrary balanced record cannot self-certify its physical correctness.

Source mismatches, malformed data, wrong leg assignment, nonfinite values, duplicated nodes, incompatible signs or changed geometry must fail closed with explicit reasons. An out-of-domain source is not equivalent to a calculated numerical failure; preserve native availability/status semantics.

## 11. Contact and force accounting

Define source branch actions consistently as forces the column transmits **outward** to each connector and to any direct foundation contact. Then, about a common reference:

`W_column = shift(W_member_1) + shift(W_member_2) + W_column_contact`.

Do not count the column-contact contribution in either connector core a second time.

For contact traction exerted onto the foundation by a compression-only patch, use downward normal traction. With upward surface normal n:

`dF_contact = -p n dA`, with `p >= 0`.

The force/moment contribution must be integrated from actual contact patches or supplied in a qualified record with the corresponding admissibility evidence. No tensile bearing, no pressure over the L-section's empty quadrant, and no frictional shear credit in this RC1 method. Full or partial contact and separation come from the response authority, not from compression sign alone.

Foot-group handoff is a net connector-on-foundation wrench. It may already combine anchor forces and foot contact. Never add those subcomponents again to the net handoff. If a qualified source additionally supplies individual anchors/contact, validate that their sum reproduces the foot-group wrench and label their source/domain. Otherwise report only group wrench; individual anchor demand is unavailable/external.

Do not infer that all compression bypasses bolts, all uplift goes half to each connector, or reversing a load simply negates a previous contact solution.

## 12. Numeric/proof boundary

Inherited engine output records remain verbatim. In particular, do not force Slice 7, Slice 8, Stage 2.5A or native quantity conversion to match independently calculated Decimal-80 strings.

New exact response-ledger checks use the source's declared exact finite-decimal or rational canonical records. Require exact force/moment recovery at that boundary. A response containing only approximate solver outputs with no accepted numerical proof/representation contract is not made valid by an arbitrary tolerance. Reuse an already accepted source/proof contract where its applicability is established; do not silently widen its tolerance.

At a subsequent inherited native serialization/projection boundary, preserve the native values, native proof and the actual transferred input record. Compute any serialized aggregate-minus-proof-target diagnostic separately and label its origin. Do not hard-code tiny residuals copied from a different stage/load case or repair them by dumping force/moment into another branch.

An inherited algebraic proof does not prove a new branch allocation. Display independent statuses for total input transport, response-ledger conservation, connector-core equilibrium and qualification. Do not state branch equilibrium PASS when no branch response is available.

## 13. Two Slice 7 connector cores and FRP providers

For each valid branch, pass the complete member-interface wrench with its actual local reference into the unchanged material-neutral Slice 7 core. Obtain heel wrench and connector-on-foot/foundation reference handoff without discarding local moment.

Run the FRP provider only in explicit design. Its angle-body qualified-source applicability remains separate from the whole-base response source. A correct response is not a capacity source; a capacity envelope is not a force-distribution solver.

The existing instep-shear equation applies only to its defined local extrusion-axis shear and geometry. For these base angles A is horizontal; column axial force is not automatically instep shear. Preserve all other forces/moments for the provider's qualified coverage. Do not call an instep-only result a complete base-angle strength result.

Use actual column/connector LW/CW/TT identities and accepted single-lap, geometric, environment and other native factors. Never choose a different material or factor merely to make a default fixture reach a particular status.

## 14. Column-to-connector member bolt demand

Use the accepted Slice 8 in-plane wrench engine for each resolved member-side group, including independent in-plane free moment. Use the physical bolt coordinates and wrench reference in the same local frame and plane; do not combine heel-based coordinates with an accidentally recentered wrench.

For an `(A,B)` member plane, the in-plane subset is `(F_A,F_B,M_C)`. The complementary `(F_C,M_A,M_B)` remains explicit. Slice 8 is not an automatic normal bolt-tension/contact/prying solver.

The F44-09 reference group has centroid `(0,3)`, J=13 in2, force `(4,-6)` kip and independent moment 3 kip-in; F44-10 shows that using `(0,0)` as the wrench reference changes the centroid moment by +12 kip-in. Those are physical reference differences, not serialization issues.

Do not route independent member moments through Stage 2.5A's unsupported path. Reuse Stage 2.5A only where an existing accepted sub-check explicitly supports the given demand.

## 15. Bolt-axis response and local FRP checks

For numerical member-bolt tension, pull-through and combined shear/tension, require an applicable source/provider for actual per-bolt normal demand, contact/prying and relevant shaft-plane response. Extend the accepted Stage 4.3 validation adapter additively where needed for two perpendicular groups; do not broaden its original source domain.

Use unchanged native bolt strength and local FRP engines for resolved and applicable demands. Keep actual bolt source/condition/grade/diameter/grip and demanded sign. ASTM F593/316 naming alone does not provide an approved Fnt; preserve source-required behavior where the controlled authority is absent.

Evaluate actual connector upright and column leg layers separately. Do not apply double-shear capacity by counting two leaves. Do not mix incompatible per-plane result conventions or suppress signed vectors. Retain each applicable bearing, net-section, shear-out, cleavage, block-path and pull-through check; preserve native governing selection.

Per-leg checks do not establish the complete two-leg column-end region/heel/junction interaction. Represent that coverage separately with applicable source authority. No new whole-column compression/flexure/buckling equation is authorized.

## 16. Foundation handoff and external design

For every available response, transport both native connector foot wrenches and direct column contact to the actual common foundation reference. Preserve opposite reactions separately. If the response is missing, export the required total foundation wrench from section 8 and clearly mark branch/anchor breakdown unavailable.

Do not execute an unprovided ACI anchorage or concrete-bearing engine. Do not reuse metallic through-bolt capacity as concrete-anchor-system capacity. Anchor steel, pullout, breakout, pryout, edge/group effects, concrete bearing and foundation strength/stability remain external unless already supplied under a separately accepted complete design authority; this order does not create that authority.

Show `EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED` or the exact compatible baseline equivalent as a distinct whole-connection boundary. No ordinary whole-base PASS. A fully checked internal FRP/bolt subset is still not the complete foundation design.

## 17. Default behavior and source-present evidence

The default combined case is:

`N=-20 kip, Vx=+5 kip, Vy=-3 kip, Mx=+60 kip-in, My=+40 kip-in, Mz=0`.

No production qualified source is invented or preselected. With no complete base-response source, show required total foundation actions, valid geometry where applicable, branch response `SOURCE_REQUIRED`, and uncalculated connector/member quantities as unavailable. Do not inherit Stage 4.2's default FAIL or governing check.

When exact zero actions are supplied and the problem excludes self-weight/preload/pretension, zero transfer can be proven without inventing a nonzero response. Geometry and external design/qualification still remain separate. Zero demand is not proof of future strength.

Source-limited production behavior must not conceal missing implementation: provide test-only source-present integration for both column presets, exercising nonzero connector transport, member-bolt shear/normal/combined paths, local FRP checks, body-provider coverage and base contact/handoff. Synthetic sources must be isolated to tests and must not appear in the production source registry/UI.

## 18. Status and traceability contract

Keep at least these distinct scopes:

- geometry;
- required total foundation action/transport;
- complete base response / branch allocation;
- column-end contact;
- connector 1 and connector 2 member attachment;
- connector 1 and connector 2 body/provider;
- per-bolt normal/prying response;
- local two-leg column-end zone;
- foundation group handoff;
- external anchor/concrete/full foundation design;
- overall angle-column member design.

Use accepted baseline status semantics. Invalid input/geometry controls; a real evaluated required failure remains visible and governs the applicable internal comparison; otherwise missing required sources or unsupported coverage prevent complete success. Every FAIL must have a native reason or failed-check record. Every unavailable quantity remains unavailable, never a fabricated zero.

The highest permitted internal success state remains qualified-source/engineering-review constrained. A sub-check PASS is not a whole-connection PASS. Stiffness, rotation capacity and full-strength classification remain NOT_EVALUATED. Keep design status, source availability and proof status distinct in payload and UI.

## 19. API and application integration

Add one dedicated Stage 4.4 preview/design product contract using the existing routing/version conventions. Additive selector/type/export/route integration is authorized; actual filenames should fit the repository.

Do not implement by passing fake wall geometry into a W/I beam product. Reuse material-neutral helper layers and existing source adapters instead. Do not modify inherited calculation equations or historical request semantics.

Preview may resolve canonical geometry, load references, total wrench transport and source-binding/applicability plans, but it must execute zero resistance functions. Explicit design performs applicable native calculations and returns a complete scope trace.

Every result binds the exact normalized input, geometry, reference, material, source and method identities. Display-unit changes are presentation-only when they do not change physical input; an equivalent SI input must preserve engineering identity according to inherited source/unit conventions.

## 20. Frontend layout and source controls

Provide readable independent sections for Column, Foundation geometry, Joint actions, Base angle on leg 1 and Base angle on leg 2. Each connector contains full-width Member bolts, Foundation anchors and Qualified sources groups; do not nest these beside a scalar radius/diameter input.

Expose separately the complete base-response reference, angle-body references, member normal/attachment references, and local column-end-zone coverage. Use the existing server-controlled source selection/resolution model. Typed text alone is not qualification.

Explain the difference between a required group wrench, an in-plane projection and actual per-bolt normal/contact response. Show the required total foundation handoff even without branch qualification, but never show fictitious per-anchor arrows or forces.

Load presets and engineering edits use one canonical request state. Presentation controls never write engineering input. No hidden equal-angle load-sharing lock; an optional explicit copy-geometry action must not claim structural symmetry.

## 21. 3D, X-ray and request-state behavior

Render one real L column, both base-angle connectors on different legs, all physical member bolts/anchor shanks/hardware, the finite pedestal, and backend-authoritative local/material axes and signed actions.

Plan and two orthogonal side views must expose the different-leg arrangement. X-ray must make inner nuts and real shanks inspectable without pretending voids are connected material. No floating foot, self-interpenetrating angle heel or bolt crossing an unrelated leg.

Engineering edits stale design, request preview and clear incompatible qualifications. Invalid input retains last-valid scene as explicitly last-valid and blocks design. Superseded/aborted requests cannot overwrite current results. Design/source tables must correspond to the same input/result fingerprint; no previous-case FAIL on new-case empty rows.

## 22. Acceptance tests and independent numerical references

Implement all T44-001 through T44-096. The fourteen F44 fixtures test proper frames, L-section reference geometry, wrench shifts, both connector transports, full/direct-contact conservation, bolt references, compression-only contact, nonunique static allocation, units and rotation.

Reference fixture numbers are exact rational strings and may include mathematical centroids that do not have finite Decimal representations. They are **not** literal replacement oracles for an inherited engine's native serialization. For native integration, build the input independently of the Stage 4.4 adapter and compare to a direct immutable dependency call with exactly the same physical input. Do not test an adapter against itself.

Where a reference fixture includes a rational mathematical geometry target, verify the pure reference computation independently and test the native production integration under its established representation/proof contract. Do not change the native centroid or adopt a new epsilon to force equality to an unrepresentable rational number.

The 64-case source-absent sweep is two column presets x sixteen named loads x two unit systems. Check actual request normalization, geometry/reference invariants, total handoff, source status, and non-invention of branch demand, not just object creation.

The additional source-present suite has at least two presets x six named cases (compression, uplift, pure Mx, pure My, biaxial, combined) x two units = 24 cases. Test sources must bind each actual case; reversing a contact solution is not automatically valid. Include numerical success/failure/source-mismatch cases without redefining production materials. Source-present checks exercise the implementation, not construction qualification.

The matrix assigns verification phases. Local and isolated runs evaluate the requirements applicable to that phase; future push, hosted-CI and owner-review evidence remains PENDING until actually available. Conditional maintenance can be NOT_NEEDED with a reason. Do not require hosted evidence before the push that enables it or claim owner acceptance on behalf of the owner.

Retain negative/metamorphic cases for wrong centroid/reference, omitted contact, swapped legs, reflection frame, duplicate bolt/branch, source-domain mismatch, tensile bearing, hole/edge invalidity, nonexistent source and request races.

## 23. One exhaustive compatibility preflight

Before implementation mutations, inspect the **entire** package and all planned integration boundaries, then emit one capability/change plan. Temporary diagnostics and in-memory candidate projections outside tracked source are permitted.

The plan must identify actual APIs, frames/units, native numerical authorities, applicability, source limitations, planned paths, and independent tests for: angle geometry, base layout, total wrench transport, branch/contact records, both Slice 7 cores/providers, member Slice 8 demand, normal-response validation, native local checks, foundation handoff, statuses, UI and historical guards.

Search repository-wide for old source/register/package/tree digests applied to current HEAD, hard-coded current-file allowlists, source-registry append coupling, tag/history dependencies, current-scope tests that accidentally freeze later development, and the known Windows timing-sensitive tests. Project the **full planned Stage 4.4 change set** through affected scope guards before spending time implementing.

Continue every safe read-only check after discovering a discrepancy. Report all genuine unresolved engineering conflicts together. Expected missing sources, permitted adapter work and the maintenance class in section 24 are not separate owner-approval stops. Do not skip actual engineering ambiguity or invent source properties to continue.

## 24. Standing tests-only successor-safety authority for this order

Owner handoff approving this order authorizes narrow tests-only maintenance of the **known historical-versus-current mutable identity pattern** across whichever repository test files/test-only helpers the consolidated audit actually identifies. There is no repeated one-file-at-a-time approval requirement.

Allowed locations: existing test roots and test-only historical-evidence helpers/fixtures. Record every changed path and the exact brittle assertion before/after. Do not broaden this into arbitrary test refactoring.

Separate two obligations:

1. Historical freeze/security identity is checked against its original immutable object/snapshot/approved manifest and original expected digest, never today's mutable package/source tree.
2. Current candidate scope is checked against this order's explicit new-product/shared-glue/tests/governance authority and preserved behavior, not an old global nine-file allowlist treated as permanent engineering scope.

A current authorized successor edit is not historical tampering. Conversely, recognizing a successor does not grant blanket permission to mutate unrelated current code. Preserve exact historical digests, tag targets, controlled content and behavior fixtures. Prohibit whole-test-tree wildcards, accepting arbitrary hashes, changing old expected hashes to new ones, disabled/xfail/skipped assertions, or editing old manifests/tags.

Require positive and negative proof for historical content change/add/delete/rename, wrong manifest/tag/object, unrelated current mutation, legitimate Stage 4.4 additions and bounded timeout-only maintenance. Preserve assertion bodies/engineering expectations except where this specific historical anchoring mechanism changes.

Add a test-only forward-successor probe: a later governance append or explicitly registered product/maintenance change must not invalidate a historical record merely because current HEAD grows. This probe does not authorize that future production change now. Do not replace one permanent whole-current-tree lock with another.

When tag/history is unavailable in an isolated clone, use the already accepted manifest-only evidence scheme anchored to original published hashes. Label what it verifies. Do not claim a missing historical object was fetched/checked, substitute successor HEAD, or pass by skipping verification. Any new test-only historical evidence must be captured from actual verified original objects before mutation, not reconstructed to match modified current content.

These maintenance changes may be included in the Stage 4.4 implementation commit; no separate maintenance order/CI cycle is required solely for this known pattern. Changes to actual engineering test expectations, historical production semantics or controlled engineering artifacts remain outside this standing authority.

## 25. QA, bounded timing policy and integrity

Require full backend/frontend suites, configured 100% coverage with existing denominators/policies, Ruff, strict mypy, ESLint, strict TypeScript, build, JSON, whitespace, locked dependency consistency, pip check and both full/runtime npm audits. No coverage exclusions or removed assertions.

Run all existing stage/slice suites and eleven registered historical freeze audits, including Stage 3.7, Stage 4.2/4.3, Slice 7, Slice 8 and their native local-check dependencies. Resolve fixture IDs from current accepted registers, not superseded attachment names or guessed old test counts.

New broad multi-input Stage 4.4 browser-like unit tests may use explicit per-test 15,000 ms budgets from the outset. Preserve the accepted historical 15-second budgets. Keep short unit tests short and avoid needless sleeps.

For an additional existing frontend test with a reproducible timing-only 5-second failure, this order pre-authorizes only its individual timeout up to 15 seconds after evidence excludes assertion/runtime/request errors and deadlock. Require 10 consecutive Windows passes of each adjusted test, then full QA. No global timeout, retry inflation, skipped assertion or timing-sensitive semantic change. Record changed path/test/budget and allow the historical guard to recognize only this bounded timeout change under section 24.

Full and runtime audit results must actually be obtained and be zero. An unavailable registry is not zero findings. No dependency/lockfile/framework/workflow upgrade is authorized by this product order; a newly discovered real security issue outside the accepted dependency set is a consolidated genuine blocker, not permission to run audit fix.

## 26. Environment, network and working-area permissions

Use a clean active worktree/clone at the accepted baseline. If the original desktop worktree still contains preserved obsolete Stage 4.3 drafts, leave it untouched and use another clean work area; do not delete/stash/overwrite those drafts or demand that every other worktree be clean.

The owner handoff permits repository reads/fetches and eventual normal non-force branch push only to the specified GitHub repository. It permits existing locked dependency installation and QA operations against the repository's established registries, plus npm full/runtime audit metadata access at `https://registry.npmjs.org/` including its advisory endpoints. Do not publish packages, upload source/secrets, modify credentials, use unrelated services or bypass actual environment approval rules.

Start/reuse existing backend/frontend dev commands in persistent sessions, inspect localhost in available approved browser/CDP tooling, and stop only task-owned processes when necessary. Discover actual ports rather than assuming 5173 is free. Do not expose servers publicly or install a new OS/browser dependency.

Use a permitted Python-module invocation of the same installed mypy package/configuration if a wrapper cannot execute, or an existing trusted verification environment. Do not disable Windows Application Control or evade a security prohibition.

For committed identity, use Git tree/blob bytes and platform-independent relative paths. Checkout CRLF bytes are not automatically canonical Git blob bytes. For explicitly raw source hashes, use the authority's exact representation instead; clean Git status alone does not prove those hashes.

Bounded external timeouts may be retried up to two times with delay and preserved logs. Real vulnerability or assertion failures are not transient endpoint errors.

## 27. Automatic browser review and controlled records

After implementation/local checks, open the real running application automatically. Review equal and unequal columns, both connector groups, plan/front/side/X-ray, default combined, uplift/compression, each pure bending direction, biaxial load, each shear sign and zero. Inspect invalid geometry, stale/source invalidation and superseded requests.

Inspect console/network/runtime evidence using available tools; do not claim CDP execution if unavailable. Fix new Stage 4.4 implementation defects within this specification without routine milestone approval. Preserve before/after evidence outside production source.

Register the two new files byte-exact under existing conventions. Update only current roadmap/handoff/decision/artifact/source/QA records required for Stage 4.4. Include scope, native dependencies, response/capacity gaps, source provenance and an actual test-to-requirement map.

Create a new Stage 4.4 resolved fixture/change catalogue if useful; it must bind chosen physical presets, source domains, actual callable map and the exact approved stage scope. It must not rewrite the matrix, old golden values or historical freeze manifests. Never require a committed document to contain its own SHA or the final future commit/CI identity.

## 28. Commit and object-isolated verification

Review the complete changed-path list and stage explicit paths only; no `git add .` or `git add -A`. Run both worktree and cached whitespace checks. This new package has no hard-break trailing spaces. Historical approved three-line exceptions apply only to their original exact artifact/lines when actually scanned, never as a global waiver.

Create the section-1 implementation commit. Include necessary preflight successor-safe tests-only maintenance in this commit rather than starting another permission cycle. Do not modify dependencies, workflows, existing tags or old engineering authority.

Before push, create a fresh clone with depth one, no tags, no local/shared object optimization and no alternates at the exact new commit. Verify one reachable commit and a clean isolated checkout. Run the **complete** final suite/static/build/security/acceptance gates there; do not reuse output files from the development worktree.

Do not require the absent parent object inside that clone to prove a baseline diff. Capture the canonical parent tree/path/blob evidence and exact diff in the full checkout before isolation, then validate the recorded evidence and current object identities inside the clone. Use existing approved historical evidence modes truthfully.

If the isolated check reveals a tests-only historic scope/timeout or authorized new governance-record error, one unpublished amend is pre-authorized under section 30, with unchanged production trees and full repeat verification. Do not push a known failing commit.

## 29. Push and direct hosted CI

After local/browser/object-isolated gates pass, the owner authorizes normal non-force push of the exact verified commit to `main` at:

`https://github.com/baraa-misto/frp-master-connection.git`

No tags. Verify active worktree HEAD, origin/main and remote main equality. Identify other preserved worktrees separately; do not falsely report them synchronized or clean.

Hosted CI runs **after** the push that triggers it. Require direct Backend Ubuntu, Backend Windows, Frontend Ubuntu and Frontend Windows results with exact SHA/run/attempt. Do not infer hosted success from local QA or from another commit.

For a timeout or external infrastructure episode with no assertion/application error, one failed-job-only hosted rerun is authorized. If the same marginal 5-second test failure recurs, the bounded tests-only correction in section 30 is already authorized. Do not ask the owner again for exactly that maintenance. An assertion/engineering failure, incompatible source authority or real security finding is not covered by a timing exception.

## 30. Bounded corrections and count rules

Normal path: one implementation commit, count 115.

Pre-push: at most **one** amend of the unpublished Stage 4.4 commit is authorized for the section-24 historical test pattern, the section-25 individual timeout field, or an authorized Stage 4.4 bookkeeping/integrity record. Preserve all production/engineering/artifact input bytes, exact subject and count. Compare superseded versus amended objects; record every changed path. Re-run complete object-isolated QA. A new engineering-method decision is not an amendment permission.

After publication: never amend/rebase/squash the published implementation. If a repeated hosted timing-only failure needs the section-25 correction, create at most **one** tests-only maintenance successor with subject:

`test: stabilize Stage 4.4 Windows verification`

That conditional successor may include only the specifically evidenced timeout fields and directly necessary tests-only historical-scope recognition. It must retain assertion bodies and all production/dependency/workflow/controlled-source identities. Run the 10-pass Windows gate, full QA, object isolation, normal push and hosted four-job verification. Final full-history count then becomes 116; this is an authorized reported exception, not a reason to stop merely over count.

No new test-file whitelist approval is needed for the precisely bounded maintenance class already authorized here. No further autonomous commit, timeout beyond 15 seconds, production change to an old frozen method, security bypass or broadened dependency update is authorized.

## 31. Acceptance, remaining limits and completion report

Leave the latest verified local application running/open for owner review; report URL, active checkout SHA, task-owned sessions/processes and any unavailable browser evidence. Do not stop unrelated servers or ask the owner to open two PowerShell windows manually.

Owner final visual/result acceptance remains required. Do not freeze Stage 4.4 automatically. Do not begin Stage 4.5, other column-base families, full concrete-anchor design or 316SS connector expansion.

Provide one completion report with:

1. Initial/final SHA/counts, order/matrix hashes, eleven-tag verification and preserved-draft disposition.
2. Consolidated preflight, actual dependency/authority map and exact reviewed/changed paths.
3. Column/contact/pedestal presets, both proper connector frames and physical bolt/anchor paths.
4. Applied/transported total wrench, reference-generated moments and reaction convention.
5. Complete-base source contract, branch/contact proof, compatibility/qualification evidence and missing-source behavior.
6. Both Slice 7 core/provider results, member Slice 8 paths, native per-bolt/local-FRP coverage actually executed and unmet source boundaries.
7. Foundation total/group/contact handoff and all external anchor/concrete/member-design limitations.
8. Native versus reference numeric/proof authority; no unapproved half-share, M/z replacement, reserialization or residual redistribution.
9. Ninety-six requirements, fourteen fixtures, 64-case sweep, 24 qualified test integrations, negative/metamorphic cases and source segregation.
10. API/sidebar/scene/request-state/browser evidence and corrected new-product defects.
11. All successor-safe historical test repairs with original digests, tamper-positive/negative proof and forward-successor probes.
12. Full local/isolated QA, coverage/static/build/security, individual timing budgets and any 10-pass evidence.
13. Explicit diff/staging, commit/amend or permitted maintenance successor evidence, normal push and direct hosted four-job results.
14. Running application URL/SHA, owner acceptance pending, consolidated limits and confirmation no later family or 316SS work began.

**END OF STAGE 4.4 ANGLE COLUMN TWO-LEG MOMENT BASE ORDER RC1 - DO NOT PROCEED IF THIS LINE IS MISSING**
