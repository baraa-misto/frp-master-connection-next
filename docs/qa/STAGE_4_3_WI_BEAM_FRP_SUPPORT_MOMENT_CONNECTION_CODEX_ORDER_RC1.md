# FRP Master Connection — Stage 4.3
# W/I Beam to FRP Support Major-Axis Moment Connection
## Controlled implementation order and engineering integration specification — RC1

**Recommended Codex effort: EXTRA HIGH**

**Product:** `WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION`  
**Contract:** `4.3-RC1`  
**Category:** Moment Connections  
**Label:** W/I Beam to FRP Support Moment Connection

This order authorizes the physical Stage 4.3 product, not a separate prerequisite slice. It extends the accepted four-angle beam connection to the five receiving-support configurations below. It includes support-side fastener checks and the affected local FRP support region. It does not authorize inventing missing fastener forces, source properties, or FRP face/prying resistance.

The order has two consecutive parts: a consolidated read-only compatibility audit, then implementation within the authority below. Continue into implementation without another routine approval when the audit passes. Expected missing production qualification data is an explicitly handled result state, not by itself a development stop.

---

## 1. Baseline, evidence, and publication identity

Require clean, synchronized `main` before source mutation:

`HEAD == origin/main == remote main == c8094293e6da49aa830b5801f49aae537cccae2b`

Starting reachable commit count: **109**.

This is the Stage 4.2 governance freeze commit. The owner has supplied direct CI #104, attempt 1, four-job green evidence and Stage 4.2 acceptance. The associated accepted product baseline is:

`1dee177a02bcaec713c1e3f597b053790ff7337e`

Use that corrected identity, not the older mistyped identity in the historical freeze-order attachment. Do not rewrite historical attachments to fix their spelling; record the accepted clarification and verify the actual Git objects.

Latest freeze tag:

`stage-4.2-wi-beam-concrete-wall-moment-connection-freeze`

Reported annotated tag object:

`5ad81fe69c1ea17bc0a76daf34cf27f44963cecf`

Its peeled target must equal the starting governance commit. Verify it and **all ten existing freeze tags** locally/remotely. Resolve earlier tag names and identities from the repository registers, not from guessed names in this order.

Expected one-commit implementation subject:

`feat: add W/I beam-to-FRP-support moment connection`

Expected final count: **110**. No amendment, rebase, force push, or new tag. Stage 4.4, Stage 4.5 and 316SS connector expansion are not authorized here.

## 2. Controlling files and source reuse

Only two new files are required:

1. This self-contained order/specification.
2. `FRP_MASTER_CONNECTION_STAGE_4_3_ACCEPTANCE_MATRIX_RC1.json`.

Approved acceptance-matrix SHA-256:

`3E277AF2388F15BA5C2CA2AA0B52ED9AAE7064F15DCFA354C8C233B174EB5043`

The matrix contains **90 checks T43-001 through T43-090**, **six independent synthetic fixtures**, and a required five-support/eight-load/two-unit-system sweep: **80 profile/load/unit combinations**. Those counts describe this matrix, not a required number of pytest/Vitest test functions.

This order's SHA-256 is supplied in the owner handoff message. Verify it and the final sentinel. The order does not embed its own hash, which would be self-referential. Matching an explicitly supplied approval digest requires no second routine confirmation.

Use accessible, already supplied sources and repository-controlled prior authorities. Do not request duplicate source PDFs or earlier packages when their actual bytes remain accessible. A remembered quotation is not a substitute for an accessible controlled source.

**S1 — ASCE/SEI 74-23**, supplied PDF SHA-256:

`A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`

**S2 — supplied Erratum 1**, SHA-256:

`5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`

S2 changes the Chapter 5 modulus-description text; it is not new Chapter 8 connection authority. If an additional official erratum is discovered, assess its relevance and report any actual conflict before affected implementation. Do not silently replace S1/S2.

**S3 — accepted repository authorities:** Stage 4.2 frozen implementation, manifest and effective R1–R7 clarifications; Slices 5, 7 and 8; Stage 2.5A and the resistance-handoff/local-check engines; accepted profile, full-through-bolt, material-axis and source infrastructure from the earlier families. Resolve exact paths, versions, hashes and executable APIs from the baseline registry.

The old August project handoff is historical background, not the current starting baseline.

## 3. Source-derived requirements versus new integration decisions

Review S1 at these locators, including relevant figures/tables in the actual PDF:

- §2.3.1–2.3.2 and §2.4: design-strength/factor and qualification/property rules (printed p.7 onward; PDF p.22 onward).
- §8.1–8.2: scope, tension/prying, eccentricity, bolt/hole/washer/detail requirements (printed pp.31–32; PDF pp.46–47).
- §8.3.1–8.3.2.2: applicability, bolt shear/tension/interaction and pull-through (printed pp.32–34; PDF pp.47–49).
- §8.3.2.3–8.3.3: directional bearing and applicable local/row failure checks (printed pp.34–36; PDF pp.49–51).
- §8.3.4 and C8.3.4: connection compatibility, FRP angle/prying and support flange–web-junction limitations (printed p.36 and p.96; PDF pp.51 and 111).

S1 provides capacity checks; it does **not** turn a six-component group wrench into a uniquely determined bolt-tension/contact distribution. S1 §8.3.2.1 requires prying-induced tension to be included. C8.3.4 discusses limitations of general FRP prying/through-thickness and flange–web-junction methods. S1 §2.3.2 qualification cannot be replaced by merely naming an analyst or checking static equilibrium.

The topology, API, response-ledger validation, source routing, and scope/status contracts below are project integration authority. They are not represented as new prescriptive ASCE formulas. Do not copy long licensed passages into the repository.

## 4. Support matrix and exclusions

Implement these five receiving-support modes in one new product:

| Logical mode | Receiving region | Physical member retained |
|---|---|---|
| `WI_FLANGE` | Selected exterior W/I flange | Both flanges and web |
| `WI_WEB` | Selected broad web face | Web and both surrounding flanges |
| `HOLLOW_SQUARE` | Selected exterior face | Near wall, cavity, opposite wall and side walls |
| `SOLID_SQUARE` | Selected face | Complete solid square section |
| `CHANNEL_WEB` | Selected broad web face | Web, both flanges and opening direction |

Incoming beam: W/I only. Receiving members are vertical in RC1. The support's own extrusion/longitudinal axis is vertical. Do not add sloped/skewed supports or a Channel incoming beam in this order.

Reuse existing RHS/SRS geometry primitives where appropriate, with equal exterior sides for the square-only options. Do not label a solid square section as a hollow tube. Do not extend the UI to nonsquare rectangles, circular tubes, lipped Channels, built-up supports or arbitrary profiles.

Use existing discrete face/orientation authority. W/I flange mode uses an exterior flange face. A web mode may select either broad face when geometry/hardware access is feasible. Square modes use actual selected faces/opposites. Record the face in all geometry, source and result identities. An infeasible face/size combination returns controlled invalid geometry, not a silent change of face.

## 5. Connection topology and material families

Retain the accepted Stage 4.2 beam-side arrangement:

- top flange angle outside the top beam flange;
- bottom flange angle outside the bottom beam flange;
- positive and negative web clip angles;
- the two flange member-bolt groups;
- the common Angle/Web/Angle beam-web bolt group.

Replace the four concrete anchor groups with **four support-side through-bolt groups** and actual FRP receiving geometry. There is no concrete wall, anchor embedment, adhesive anchorage, or invented blind anchor in Stage 4.3.

Use locked top/bottom angle geometry and a mirrored web-angle pair as in the accepted predecessor. Those locks do not by themselves prove a symmetric support response or authorize 50/50 receiving-wall participation.

RC1 connector material is FRP. Beam, connector and support material records remain separate and region-aware. Metallic/stainless bolts use their own source records. Do not expose 316SS connector material yet; retain the material-neutral geometry/wrench/provider separation.

No hidden backing plates, additional angles, sleeves, spacers, inserts or reinforcement patches. A topology requiring one of these is unavailable under RC1 unless separately authorized later.

## 6. Consolidated pre-mutation audit — one report, not first-error stopping

Before changing repository source, inspect the complete support matrix and native interfaces. Temporary audit scripts/output may be written outside tracked source; they must not mutate accepted engines, fixtures or manifests.

Record a capability table for every support mode, with columns:

`geometry/path | beam-side transfer | support in-plane demand | support normal/contact response | bolt capacity | local FRP checks | local joint-zone coverage | source requirements | existing/new adapter`

For every cell identify the actual callable/contract, input reference and units, native numerical authority, applicability, source coverage, and planned regression. Explicitly verify:

1. Stage 4.2 effective source/specification lineage and freeze baseline.
2. Slice 5 region-resultant calls; Slice 7 core versus provider; Slice 8 independent-moment support.
3. Stage 2.5A's supported domain and its independently applied member-moment warning.
4. Existing bolt tension, shear, interaction, pull-through and local FRP entry points.
5. Existing explicit per-bolt external-demand/source infrastructure: which parts exist and which additive Stage 4.3 adapters are needed.
6. Physical paths and clearances for all five supports, including washers/nuts and common support regions.
7. Actual numeric conversions, object types, serialization and source binding; no assumption that every engine uses Decimal-80.
8. Application/root selector, sidebar fieldsets, frontend DTO/result-flattening, source controls, browser commands and ports.
9. Existing freeze-test historical-object/manifest-only resolution and protected paths.
10. One geometrically feasible preset per support; invalid-geometry counterexamples; absence of forged qualified data.

Continue all technically safe read-only checks after finding an issue; report all real blockers together. A missing production source is an expected fail-closed result and not a reason to invent capacity or interrupt implementation. A missing adapter is authorized work if it is fully defined here and does not change an accepted method.

If there is an unresolved engineering interpretation, an unsupported load path that cannot be represented by these contracts, or a need to alter frozen mechanics, finish unaffected audit work and issue one consolidated report. Do not waive that issue. Otherwise document the audit, seal the resolved authority map, and proceed without another approval.

## 7. Module and dependency reuse policy

Prefer new Stage 4.3 domain/orchestration/geometry/response/result adapters and a dedicated frontend workspace. Actual filenames follow repository conventions; conceptual method names in this order do not require a pre-existing Python symbol of identical spelling.

Use the material-neutral parts of Stage 4.2's transfer architecture; do not create a fake concrete wall or call an anchor-capacity path to emulate an FRP column. Additive route/selector/type/export changes in shared modules are permitted with historical regression coverage. Modifying accepted engine equations, frozen controlled artifacts or changing historical request behavior is not.

The prior restriction that older slices add no frontend applied to their historical implementation; it does not prohibit the new Stage 4.3 frontend authorized here.

## 8. Frames, origins and action signs

Preserve the accepted beam frame `L_B × V_B = T_B` and negative-end structural/right-hand mapping. `L_B` points from the selected support face toward the beam, `V_B` upward, `T_B` transverse. Structural beam inputs remain signed axial P, major shear V and major moment M; other user action components reject explicitly.

The selected physical support face defines the connection interface plane. The beam-end reference is separated from it by the real positive gap. Default gap inherits 0.5 in. RC1 permits `0 < gap <= 0.5 in`; a different qualified-detail gap requires later authority. Do not clamp an invalid request. No direct beam-end bearing is credited.

For support-side attachment records define a common right-handed frame:

`u = +V_B; v = +T_B; n = +L_B; u × v = n`.

The normal points from the receiving member toward the connector/beam. Transform every connector-local support wrench into this frame at its **actual group reference**. Do not reuse a heel-origin wrench at a group centroid without transport.

For each coordinate set record origin ID, axes, ordered components, units and physical bolt IDs. A plane group's coordinates and wrench reference must share the same origin. When using centered coordinates, translate BOTH together and preserve the physical-reference provenance. Do not force translated-geometry fingerprints to be identical.

## 9. Receiving-member reference and support contribution

Backend derives the receiving profile's centroid at the connection elevation and the selected-face-to-centroid offset. Export the complete six-component connection-on-support wrench there, plus the equal-and-opposite support-on-connection action. This is **this connection's contribution**, not the solved total forces at the top/bottom of the column or its foundation.

Transform full moments; normal force, shear, bending and eccentricity-generated torsion may appear in different support-frame components. A Channel centroid is not silently its web center or shear center. If a later evaluation needs a shear-center/warping model not covered by a current source, expose that limitation; do not invent zero torsion.

Sum four connector-on-support groups at one reference once. Do not add the same reactions again as bolt totals, member-check demands or contact forces. The support-response ledger is a decomposition of those actions, not extra loading.

## 10. Beam-side transfer and frozen numerical boundaries

Reuse Slice 5 once and the four Slice 7 cores for the approved beam/angle topology. Preserve complete component forces and local moments; M/z remains a diagnostic only.

Retain the predecessor's component/branch allocation only within its documented symmetry and qualification domain. A new support orientation, offset or flexibility condition that invalidates that domain must be exposed as a source/applicability limitation, not treated as a new proof of equal sharing. Do not change Slice 5 resultants to hide such an incompatibility.

Preserve Stage 2.5A where the flange in-plane demand falls within its accepted scope. Use Slice 8 for independently applied web in-plane moments. Preserve physical web coordinates/reference consistently, including the accepted `(0,2)` heel-local default when inherited unchanged.

Consume each native engine's results verbatim. Integration tests build dependency inputs independently and compare to direct native calls. Those tests verify integration; they do not replace the dependency's independent regression suite or its source applicability. Never use separately calculated N/n, high-precision reruns, or rounded expected values as a substitute oracle for a native output.

New exact sign/permutation/reference-response validators use the existing rational machinery or standard-library exact rationals from finite Decimal inputs. No binary float for engineering values and no ambient-context Decimal negation of long strings.

Retain raw serialized aggregates, algebraic targets and their provenance separately. Compute any serialization residual from the actual pipeline as an audit value. Do not copy the old Stage 4.2 `6E-79` or `2E-78` residuals into new support geometries, redistribute them or replace a failed physical/source proof with an epsilon test.

## 11. Physical support-side bolt paths

Every bolt is an identified continuous physical shank with actual head, washer(s), nut, grip and end extension.

**W/I flange:** angle support leg -> selected flange. Retain the internal web/flange junction; ensure rear hardware/access does not conflict with it. Do not send the bolt through the opposite flange by default.

**W/I web:** angle support leg -> selected web. Retain both flanges for collision/access and local-junction checks. Do not let a hole accidentally enter a flange or heel region.

**Channel web:** angle support leg -> Channel web. Retain opening direction and internal/rear hardware clearance. Do not silently flatten the Channel into a generic plate.

**Hollow square:** angle support leg -> near wall -> cavity/free shank -> far wall, with exterior hardware only. The two FRP walls are separate regions; the cavity is neither material nor a resistance layer. The near/far shear participation, far-wall normal reaction, wall crushing/ovalization and long-shank bending cannot be inferred from the count of penetrations. Two walls do not automatically mean double-shear capacity or equal wall sharing.

**Solid square:** angle support leg -> continuous solid section -> opposite exterior hardware. No artificial cavity. The full grip depth is physical; it is not automatically the effective thickness in every local plate/pull-through equation.

Record actual loaded shear interfaces/shaft sections from the applicable response authority. Do not assert the support groups have the same two-plane mechanism as the beam's Angle/Web/Angle bolts.

## 12. Geometry validity and feasible presets

Validate whole holes, real material intersections, full washer seating where its formula is used, hardware envelopes, angle fillets, perpendicular support elements, opposing groups and installation access. Unknown installation access must be explicit; visibly impossible access is invalid.

All four support groups must fit the finite member face. Reject collisions or insufficient physical overlap rather than moving bolts, shrinking washers, deleting flanges or changing the profile silently.

Choose and record one feasible support-geometry preset per mode through the canonical backend geometry audit. Reuse the accepted W/I beam and angle starting inputs where they physically fit. Support dimensions may differ across these presets; selecting a feasible geometry does not require inventing a passing resistance result. Record dimensions and source/factor identities before committing fixtures.

Display length is not an engineering edge distance, restraint or local-panel boundary. Receiving-member physical ends/connection location, where required by a check, must be distinct from viewer clipping extents. No force-based geometry optimization is authorized.

## 13. Support-side in-plane demand

At each support group's actual `(u,v)` reference decompose its complete wrench into:

- in-plane part: `F_u, F_v, M_n`;
- out-of-plane part: `F_n, M_u, M_v`.

Slice 8 may resolve the in-plane part only where the physical participation/equal-stiffness model is applicable. It does not establish normal bolt forces, contact, prying, member flexibility or near/far-wall sharing.

For thin single-lap receiving regions, an approved in-plane projection may be shown/evaluated as a separately identified scope. It must not claim complete attachment adequacy when normal/contact effects remain unqualified. For hollow/solid long paths, do not invent per-wall reactions by applying a thin-plate solver without an applicable path-response authority.

All missing complete-response items remain visible. No force component disappears merely because a particular solver does not support it.

## 14. New support-attachment response contract

Implement a Stage 4.3 source-bound adapter/validator with logical identity:

`QUALIFIED_FRP_SUPPORT_ATTACHMENT_RESPONSE_RC1`.

It consumes verified response evidence for the actual attachment, rather than generating a universal FRP prying solution. Reuse existing explicit external-demand and qualification/source infrastructure. New immutable DTOs, validation and interface adapters required for this contract are authorized in this stage.

A record shall bind: source ID/version/issuer and qualification evidence; receiving profile/face/material; angle geometry/material; all affected support groups and physical bolt IDs; bolt/hole/washer/grip details and fastener source/condition; interface/frame/reference; load case and input/core fingerprint; participating layers; contact/stiffness/boundary assumptions; covered limit states and source domain.

Demand response includes, as applicable:

- signed in-plane force per actual bolt/interface;
- total nonnegative bolt-axis tensile demand per physical bolt or source-defined bolt segment;
- identified compression-contact resultants and locations;
- actual near/far-wall or solid-region reactions;
- any required additional couple/secondary-bending records and their coverage;
- complete force/moment reconstruction and proof provenance;
- a declaration of whether prying is included in the total demand.

No additive prying factor is applied again if total demand already includes it. A source that gives pure-mode strengths or a scalar utilization but no forces is **not** a per-bolt response source. A generic manufacturer material sheet is not assembly-response qualification. A user-typed source name or `qualified=true` flag cannot grant trust.

One source may cover the coupled four-group support assembly, or individual groups with explicit compatible interaction coverage. Four unrelated angle certificates alone do not establish the combined support-region response.

## 15. Exact response validation — not a stiffness solver

The synthetic fixtures in the companion matrix independently test bookkeeping and admissibility only. They do not establish a real qualified connection or automatic distribution formula.

In `(u,v,n)` with n outward, define actions **on the support**:

- a bolt resultant `(s_u,i, s_v,i, t_i)` at its actual action point, with `t_i >= 0`;
- compression contact `-c_j n` at an actual contact location, with `c_j >= 0`.

The ledger must reconstruct the applied group/support wrench:

`sum f_k = F_target`

`sum [(r_k-r_reference) cross f_k + m_k] = M_target`.

The `m_k` term is permitted only when an explicitly modeled source-authorized couple exists; otherwise it is zero. Do not add a balancing couple to make a response pass. Do not count both sides of an action/reaction pair or duplicate an internal bolt section as an extra external support force.

Check force/moment reconstruction and source-bound applicability separately. A statically balanced response without qualification remains unqualified. Preserve native external-analysis residuals separately when the source has its own declared precision/proof. This order authorizes no new tolerance for accepting an unbalanced record. Do not silently alter imported forces; unavailable compatible proof means NOT_EVALUATED/invalid-response as appropriate.

A negative tensile demand is not repaired with abs() or clipping. A source may explicitly provide opposite contact active sets on load reversal; negating a prior all-tension distribution is not automatically valid.

## 16. Missing-response behavior and implementation completion

For nonzero normal/moment demand, complete support-bolt numerical evaluation needs an applicable per-bolt response. If none exists, return named `SOURCE_REQUIRED` or `NOT_EVALUATED` items and preserve the full group wrench. Do not manufacture zero tension or a rigid plate N/n + M/I distribution.

This is expected RC1 behavior, not a reason to stop development. Implement the five geometries, the response/source controls, the validator, the bolt/local-check integration, complete traces, and the failure/unavailability tests. Demonstrate numeric shear/tension/interaction with isolated test-only verified-response fixtures and applicable test source records. Do not expose synthetic sources as production choices or claim they qualify construction.

An already accepted qualified response generator may be reused within its exact domain if found during audit. Do not introduce a new automatic flexible-angle/contact/stiffness solver under this order. If the owner later requires automatic no-source full response for uncovered details, that requires separate engineering authority, not hidden assumptions here.

## 17. Support-side bolt strength

Use the existing verified bolt-check engines where present, with source-authorized properties and the actual resolved demand:

- shear rupture;
- tensile rupture;
- combined tension/shear;
- source/thread/grip applicability;
- actual loaded plane/shaft section.

S1 §8.3.2.1 gives Eq.8-2 and Eqs.8-3a/b, including prying-induced tension and time-effect factor 1.0 for these bolt checks. Map the accepted native engine's quantities/units/factor assembly exactly; do not duplicate an equation merely for integration convenience.

If a source-specified basic bolt-check entry point is genuinely absent, an additive isolated implementation of that explicitly cited equation is permitted in Stage 4.3 only after source/applicability review, independent tests, and documented no-change to old engines. This is not authority to add a demand distribution method.

Keep F593 strength source-pending when Fnt/Fnv/condition is not authorized. Do not infer bolt strength from the phrase “316 stainless,” the FRP material, or a tensile-to-shear ratio without its controlling source path. A documented nominal shear plane and thread condition do not by themselves qualify prying or secondary bolt bending.

For multi-plane/long-shank cases use only a method whose actual applicability covers the provided response. Otherwise report the missing interaction/bending authority. Never replace it with the sum of plane capacities.

## 18. Local receiving-member and angle support-leg checks

Evaluate each applicable existing check independently using the actual region, material axes, fastener force, hole/edge path and native factors:

- pin bearing;
- net tension and applicable first-row checks;
- shear-out/cleavage and actual junction/end exemptions;
- inter-row and block-shear paths;
- pull-through under resolved normal bolt demand;
- applicable support-leg local response.

Receiving-member LW follows the receiving member, not the beam. The angle support leg has its own CW/TT orientation. Reversing force direction can change the loaded end and candidate paths. A copied beam-side result is not a support-region check.

S1 §8.3.2.2 requires the lesser applicable result from Eqs.8-4a/b. Reuse the accepted implementation with actual washer diameter, resisting FRP thickness and both required strength sources. Missing interlaminar strength does not authorize dropping one branch. Insufficient washer seating, a non-plate solid-depth condition, or an unrepresented load path does not authorize extending the equation.

Maintain factor provenance, end-use/time-effect treatment and native single-lap/thread rules exactly once. Do not apply a factor from one limit state to another solely because both involve the same bolt.

## 19. Local support zone and shared-region interaction

Local support response is in scope; overall column design is not. Track the relevant joint-zone requirements by support mode:

- W/I flange: flange-face bending and flange–web load transfer/junction response.
- W/I web: local web response and transfer to the rest of the section.
- Channel web: local web/flange-junction response and asymmetric section transfer.
- Hollow square: near/far-wall response, side-wall interaction, local bending/crushing and long-bolt effects.
- Solid square: appropriate three-dimensional bearing, washer/bolt load spread and local splitting/through-thickness applicability.

Assess interacting holes/groups, common net/block-shear paths and combined actions in the affected region. Do not check each connector separately and claim the receiving zone is complete without required interaction coverage.

Reuse a numerical local-support method only inside its established domain. Do not import a W/I splice clear-body panel, call a full solid square a thin plate, or invent simply-supported boundaries from the display length. For uncovered face/junction/intergroup/three-dimensional response require an applicable qualified local-support assembly source and display the missing checks otherwise. This local-zone source is separate from a per-bolt demand record.

## 20. Qualification and source applicability

Maintain separate identities for:

1. connector angle body/heel qualification (Slice 7);
2. beam-to-angle member attachment coverage inherited from Stage 4.2;
3. angle-to-FRP-support response/demand evidence;
4. support-side fastener material strength;
5. affected local support-zone capacity/interaction coverage.

Do not reuse a concrete-wall fixture qualification for an FRP support solely because the angle dimensions match. Source applicability must include the receiving-member stiffness/contact/path where relevant. Load changes invalidate single-load response data; scaling or sign reuse requires explicit source-domain authority and valid contact/active-set behavior.

Source-free default examples are permitted and expected. They must honestly report native failures and missing coverage. Do not alter material/factors, choose a favorable source or suppress a failure to manufacture a default pass.

## 21. Results, governing failures, and completeness

Use existing backend status enums where semantically equivalent, with an explicit mapping record for any new status. Do not silently conflate source-missing, invalid geometry and numeric failure.

Required precedence for validly executable records: invalid request/geometry first; then any required evaluated failure; then missing required source/method/coverage; then qualified review-required success only when every in-scope requirement is satisfied. An invalid source record must not produce a PASS or hide independent valid evaluated failures.

Show separate statuses for beam attachment, angle bodies, support fasteners, local support region, connection-scope completeness, and full receiving-member design. Highest completed connection/local-zone state is the existing review-required qualified success or its explicit semantic equivalent. Never ordinary unqualified PASS. Full-member stability/strength under other structural loads, stiffness classification, rotation capacity and full-strength classification remain NOT_EVALUATED/external to this connection-scope check.

Remove Stage 4.2's concrete/anchor-design message from the new FRP-support product; replace it with the correct local-support completeness and overall-member analysis boundary. Preserve that message in frozen Stage 4.2.

Every displayed FAIL must include actual current supporting native records/reasons. Preserve native governing selection, show subordinate failures and missing sources, and do not recompute governance in React. A status-aggregation-only success fixture is not a physically passing default preset.

## 22. API, workspace, scene and input behavior

Add dedicated stateless preview/design endpoints following current repository routing conventions; register the final paths in tests/docs. Historical paths and payload meanings remain unchanged.

Preview: validation, complete physical geometry, action/reference planning and group-wrench/proof/source-availability records; zero resistance calls. Design: explicit Run Design Check, full authorized numerical checks and completeness aggregation.

Workspace inputs include support mode and selected face/orientation, physical profile dimensions, connection location, W/I beam and gap, four connector input families, member bolt groups, **Support bolts** groups, washer/head/nut details needed by checks, materials, fastener sources and response/qualification references. No anchor embedment or 316SS connector option.

Keep geometry grids compact but Member bolts and Support bolts as separate full-width fieldsets with readable labels. Source references are full-width. Verify narrow panes and zoom. Preserve values, units and state on field edits; invalidate incompatible sources when support geometry changes.

Scene is backend-authored: actual complete support, W/I beam, four angles, finite shanks, all exterior hardware and actual layer surfaces. Show selected face, support centroid/reference, material directions, input action signs and generated moments. X-ray/camera must expose hidden support hardware and hollow/solid differences. Do not substitute a wall mesh behind a support label.

## 23. Trace and runtime invariants

Expose the path from beam P/V/M through Slice 5, connector member/heel/support wrenches, support-side plane decomposition, per-bolt demand/response source, contact/participation record, native capacity checks, receiving-layer/local-zone checks, and combined support contribution.

For each check show component/face/layer, bolt/group ID, method, demand, capacity if available, units, status, source/applicability and governing reason. A group wrench is labeled as a group wrench, not an individual bolt result. Unavailable tension shows unavailable, not zero.

Keep current input and design fingerprints visible in expanded diagnostics. Edits stale old design. Superseded requests cannot overwrite current results. Source-required, invalid geometry, initial loading, malformed response, HTTP/network failure and rapid product switching must not blank the root. Preserve last-valid geometry where appropriate, without presenting stale results as current.

## 24. Verification oracles and matrix execution

The companion matrix is an **acceptance contract**, not an imitation numerical golden file generated from an unavailable repository. It deliberately does not prescribe hundreds of decimal digits for inherited engines.

Use three distinct oracle classes:

- Direct pinned-native dependency calls for integration equality, with independently constructed physical inputs and existing dependency regressions still running.
- Independent exact small fixtures for reference transforms, reaction ledger reconstruction and simple equation-interface arithmetic; the six matrix fixtures were calculated independently and are test-only.
- Metamorphic and negative tests for translations, sign/contact transitions, unit equivalence, source invalidation, topology tampering, missing coverage and status completeness.

Resolve test-case/fixture IDs literally and validate all references. Do not make a test pass by comparing the orchestrator with itself or by changing its output into the expected value. If current accepted dependent equations materially conflict with source applicability, consolidate and report rather than silently replacing the native engine.

Generate the new Stage 4.3 native fixture snapshot/catalogue only from documented baseline calls and independently validated representations. Seal its hashes and record which fields are native, algebraic, synthetic or display-only. Such generated fixtures supplement, not override, this order or the matrix. No change to old golden files.

## 25. Required five-support load and geometry sweep

Run every support configuration through the eight matrix load cases in equivalent U.S./SI inputs: combined; pure shear; pure major moment; axial tension; axial compression; reversed major moment; reversed shear; zero. That is at least 80 automated profile/load/unit cases, plus invalid/source/path checks.

For support geometry, include eligible alternate faces, W/I web and Channel hardware-clearance boundaries, every square-face mapping, hollow near/far wall path, solid full-depth path, load reversal, source-mismatch, invalid gap and hole/washer containment cases.

At least one feasible preset for each support must render and produce a complete structured preview. Design may be FAIL or source-limited; it must not be mislabeled complete. Source-limited behavior does not excuse an unimplemented numerical support-bolt path: exercise verified synthetic demand/strength integration for all five topologies and check that invalid/missing sources correctly gate production use.

## 26. Full QA and historical invariance

Require full backend/frontend suites and configured 100% statement/branch coverage plus frontend functions/lines as currently enforced; Ruff format/lint, strict mypy, ESLint, TypeScript, production build, JSON/reference integrity, whitespace, dependency consistency/pip check and security audits.

Run Stage 4.2 G1–G128 and its accepted UI/failure-trace regressions, Slice 5 G1–G52, Slice 7 G1–G72, Slice 8 G1–G80 with its accepted R1 clarification, applicable native bolt/local-check regressions, and all existing freeze audits/manifests. Use the current registry's effective fixture files, not superseded attachments.

Keep the historical per-test Windows timeout correction. No arbitrary timeout, skip, assertion weakening, retry inflation, coverage exclusions or workflow changes.

Historical tree/blob identities resolve the historical object or approved manifest evidence; a successor HEAD tree is not a historical identity. New tests must work in a fresh one-commit tagless checkout without fetching history or using Git alternates. Source immutability and behavior equivalence are both evidenced, not inferred from a test count.

## 27. Permissions and environment handling

Reuse the repository's established locked install/build/test commands. No dependency/lockfile/workflow changes. Scope any network operation to the approved repository, existing dependency registries and checks required by QA.

Standing approved npm audit operations are:

`npm audit --json`

`npm audit --omit=dev --json`

against `https://registry.npmjs.org/` and its advisory endpoints, disclosing dependency metadata only. No publishing, `audit fix`, secret/source upload or credential modification. Do not request duplicate routine consent for these unchanged operations; obey any actual higher-level environment restriction and consolidate unavoidable permission issues.

Existing localhost server startup, browser/CDP inspection and shutdown of only the processes started for this task are authorized. Do not install new browser packages/OS or disable security policy. An already approved Python-module invocation may replace a blocked executable wrapper only when it loads the same tool/configuration and is permitted; do not bypass an application-control prohibition. An existing trusted verification environment may be used with the same locked inputs.

For external integrity checkers, compare canonical committed bytes with `git show <commit>:<path>` where the authority is Git-blob identity. Raw Windows CRLF worktree bytes are not automatically equivalent to canonical Git bytes. Do not weaken a source SHA whose authority is explicitly its raw file bytes. Clean Git status is one check, not proof of every controlled hash.

## 28. Automatic local browser QA

After local implementation/tests, start or safely reuse backend/frontend in persistent Codex terminal sessions using actual repository commands and discovered ports. Wait for readiness, open the local app in the built-in browser or already-approved available browser automation, and inspect runtime/console/network evidence where supported. Do not claim CDP checks if unavailable.

Exercise the real application selector for all five support modes. For each inspect the default, pure shear and pure moment plus load reversal; confirm 3D/X-ray paths and support-side source/status trace. Automate the broader eight-load sweep in tests. Also inspect narrow sidebar/zoom, profile/source changes, invalid geometry, stale state and delayed/failed requests.

Correct implementation/scene/request-state bugs within this order without stopping for routine permission. Stop only when the fix requires new engineering authority or a protected change. Save before/after screenshots, request/response evidence and current fingerprints. A green unit suite alone does not substitute for this browser gate.

Before isolated QA, stop only task-owned processes if file locks would interfere. After publication reopen the verified checkout and leave the app running for owner review; report URL/session/process identities. Do not terminate unrelated servers or leave the owner to open two PowerShell windows manually.

## 29. Governance and efficient progress

Copy the two new controlling files byte-exact under the repository's current documentation/QA conventions and register their hashes. Record this order as the single Stage 4.3 authority; do not import old Stage 4.2 execution baselines/commit counts into this task.

Update only current handoff, roadmap, artifact/decision registers and QA/source/coverage records needed for Stage 4.3. Record the actual dependency map, fixture catalogue, all source-limited scopes, five support presets, new API paths, source types and accepted/no-authority boundaries. No production PDFs, font files, secrets or external browser evidence copied into source.

Do not pause after each normal milestone. Reuse still-valid expensive audit evidence when its checked objects/environment have not changed; rerun directly affected checks and all final QA gates. If blocked, collect all safely discoverable issues, attempted approved remedies and exact needed decisions in one report. Do not silently broaden scope to avoid a stop.

## 30. Staging, commit and isolated verification

Review and stage explicit named paths only. Require cached whitespace checks and no unexplained tracked/untracked residue. Do not use broad `git add .`/`git add -A`.

Create one commit with the exact subject from §1; expected final count 110. Do not amend without separate owner approval. Verify the commit's source/dependency changes match the audited scope; all existing tags remain unchanged.

Before push, run complete prescribed QA on the exact commit in a fresh depth-one, no-tags, no-alternates clone. Record exact commit, one reachable commit, no alternates, clean integrity/status checks, test/static/build/security evidence and no history-dependent fallback. The isolated checkout must actually run the tests, not reuse the main checkout's result files.

If isolated QA fails, do not push. Diagnose and report any required correction to the unpublished commit; do not bypass the gate merely because local QA passed.

## 31. Publication authorization, CI and owner review

After successful local, browser and isolated verification, the owner handoff authorizes normal non-force push of that exact unchanged Stage 4.3 commit to `main` at:

`https://github.com/baraa-misto/frp-master-connection.git`

No tags. Verify HEAD/origin/main/remote main equality. Hosted CI for this commit runs **after** the push that triggers it; it is not a pre-push prerequisite. Do not change credentials or override environmental security controls.

Obtain direct Backend Ubuntu, Backend Windows, Frontend Ubuntu and Frontend Windows results with run/attempt and commit identity. Use already authenticated available CLI/browser access. No inferred success. If a failure is clearly transient infrastructure with no assertion or engineering failure, one failed-job rerun is permitted; otherwise report consolidated evidence without changing workflows/dependencies. Authentication unavailable means CI evidence pending, not accepted.

Owner final visual/result acceptance remains pending even with four green jobs. Leave the app ready for review. Do not freeze Stage 4.3 or start a later family automatically.

## 32. Completion report

Provide one report with:

1. Baseline/order/matrix hashes, initial and final refs/counts, and ten-tag preservation.
2. Full five-support capability audit, exact existing/new module paths and source locators.
3. Physical presets, face frames, centroids, bolt paths/hardware and access checks.
4. Preserved beam/angle transfer and native numerical boundaries.
5. Support-side response contract, normal/contact/prying evidence, equilibrium validation and missing-source behavior.
6. Actual support bolt shear/tension/interaction and local FRP checks exercised; source/factor/applicability provenance.
7. Remaining local-support-zone and whole-member limitations; no qualification claims based solely on synthetic data.
8. Default/native governing outcomes, complete failure/source tables and scope completeness.
9. Matrix check coverage, 80 profile/load/unit sweep, six independent fixtures, negative/metamorphic tests and fixture-catalogue hashes.
10. API/workspace/sidebar/3D/X-ray/browser evidence, runtime checks actually performed and corrected defects.
11. Full local and isolated QA/coverage/static/build/security and historical regressions.
12. Reviewed/staged paths; production/dependency/workflow/tag counts; exact commit and normal push.
13. Direct hosted four-job evidence or clearly pending items.
14. Running application URL and task-owned server sessions for owner review.
15. Deviations, consolidated unresolved limits, owner acceptance pending, and confirmation no 316SS or later family began.

**END OF STAGE 4.3 W/I BEAM FRP SUPPORT MOMENT CONNECTION ORDER RC1 — DO NOT PROCEED IF THIS LINE IS MISSING**
