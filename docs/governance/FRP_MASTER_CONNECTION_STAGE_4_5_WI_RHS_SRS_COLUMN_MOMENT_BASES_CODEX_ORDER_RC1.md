# FRP Master Connection - Stage 4.5
# W/I, RHS and SRS Column Moment Bases with Two or Four Base Angles
## Controlled engineering integration specification and Codex implementation order - RC1

Recommended Codex effort: EXTRA HIGH.

Product: `WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION`
Contract: `4.5-RC1`
Category: `Moment Connections`
Workspace label: `W/I / RHS / SRS Column Moment Base`

This is the physical-product implementation order, including source/response validation, applicable native calculations, APIs, the complete engineering workspace, browser verification and publication. It is not a planning-only calculation slice. It adds symmetric W/I, rectangular hollow (including square), and rectangular solid (including square) column bases with two opposite or four base-angle connectors.

Biaxial input capability is not proof of biaxial connection adequacy. This RC1 preserves the Stage 4.4 distinction between a known required total foundation wrench and a source-qualified complete base/contact/connector response. No automatic half/quarter sharing, rigid-base assumption or invented long-bolt/wall participation is authorized. A useful source-limited production result and fully exercised source-present numerical integration are both required.

## 1. Starting baseline and publication identity

Start the clean active implementation work area at the full commit:

`99befa9780e7c7abf72c8a33e5eb45b9e368d916`

Full-development-history count: **118**. Verify active HEAD, origin/main and remote main, actual commit subject, clean index/worktree, and repository-local author identity. The twelve existing freeze tags must retain their actual local/remote objects and peeled targets. Specifically:

`stage-4.4-angle-column-two-leg-moment-base-freeze`

must peel to the starting SHA. Derive tag-object identities from actual Git evidence, not from abbreviated screenshots. Owner-reported baseline evidence: CI #113 attempt 1, four jobs green; 3,963 backend / 710 frontend tests, configured 100% coverage, zero audit findings. Do not represent that report as a new test run.

Accepted Stage 4.4 implementation: `e8bc2355bcecaabd70d31332cf1af3ee6eb17712`.
Accepted Stage 4.4 preview correction: `d11012e771556f0ed5cac46f39ab40cb0a53273e`.
The later count-118 freeze is the starting repository authority; do not restart from either earlier product commit or the August handoff's obsolete Stage 2.4 stopping point.

Repository destination: `https://github.com/baraa-misto/frp-master-connection.git`.
Branch to publish: `main`.
Normal implementation subject: `feat: add W/I RHS SRS column moment bases`.
Normal final count: **119**. Counts are measured in the full development history, not asserted to be 119 in a depth-one clone. No tag is created by this order. Bounded postpublication timing maintenance is the only automatic extra-commit exception described below.

A separate clean worktree/clone is permitted if the original checkout contains preserved owner drafts or unrelated work. Do not reset, clean, stash-pop, delete or overwrite those drafts. Record the active work area and refs separately from inactive draft worktrees. Do not inspect sibling projects.

## 2. Two controlling attachments

1. This combined order/specification.
2. `FRP_MASTER_CONNECTION_STAGE_4_5_ACCEPTANCE_MATRIX_RC1.json`.

Acceptance-matrix SHA-256:

`68695DFC75C51E85982ED07E76ED7A4D0B344F1CCE7AE4425A9842260967074D`

The matrix has **120 requirements T45-001 through T45-120**, **24 independent reference fixtures F45-01 through F45-24**, five section presets and three layouts, a **360-case source-absent sweep**, and **90 source-present test-only integrations**. These are engineering acceptance cases, not mandated counts of individual test functions.

The order's approved SHA-256 is supplied separately in the owner handoff. Read both files completely, verify hashes/sentinel, contiguous unique IDs and reference links. No second approval is needed after matching the explicit digest. Use UTF-8/LF and no trailing whitespace for new controlled artifacts; do not normalize historical byte-controlled documents.

## 3. Source basis and limits

### S1 - supplied ASCE/SEI 74-23

SHA-256: `A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`.

Review relevant actual source pages and figures/tables, not only extracted text:

- Sections 1.4.2 and 1.7.2, printed pp.4-5 / PDF pp.19-20: analysis assumptions, compatibility, bearing preparation and assembly detailing.
- Sections 2.3.2, 2.4, 2.9 and 2.10, printed pp.7-11 / PDF pp.22-26: qualification, material/factor authority, eccentricity and actual net areas.
- Sections 7.1-7.2, printed p.27 / PDF p.42: limits of plate provisions; do not treat a solid column's complete grip depth as an arbitrary plate thickness.
- Sections 8.1-8.3, printed pp.31-36 / PDF pp.46-51: connection applicability, hardware, geometry, forces, applicable local limit states and prying.
- Figure 8-2 and Table 8-2, printed p.33 / PDF p.48: in-plane versus axial bolt demand and source/condition-specific metallic bolt strength. Penetrated-layer count is not a substitute for actual shaft/plane demand.
- Section 8.4, printed p.37 / PDF p.52: base force/moment transfer and the referenced ACI/AISC design boundary.
- Commentary C8.3.4 and C8.4, printed pp.96-97 / PDF pp.111-112: FRP normal/prying response limitations, base detailing and anchorage-system scope.

The standard does not prescribe the specific nine topology modes, common-bolt response schema, or an automatic quarter-share rule in this package. Those topology and integration choices are project decisions. A reference to ACI/AISC is not a supplied executable anchor-design method. Do not copy long licensed passages into repository files.

### S2 - supplied Erratum 1

SHA-256: `5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`.
Effective January 13, 2026. The supplied correction changes the Chapter 5 transverse-modulus description; it does not provide a base-sharing or long-bolt response solver. The official publication listing checked for preparation still identifies that effective erratum date. Official locator: `https://ascelibrary.org/doi/book/10.1061/9780784415771`.

A newly found official correction must be assessed for relevance without silently changing the pinned basis. Do not update the standard edition or copy a guessed material value.

### S3 - accepted project authorities

Read the current Stage 3.7 geometry/base-family authorities, Stage 4.3 common/long-shank support-response infrastructure, frozen Stage 4.4 complete-base/contact and preview contracts, Slice 7 angle core/FRP provider, Slice 8 in-plane demand, and applicable native bolt/local-FRP consumers. Resolve actual paths, method versions, input frames, numeric contexts, callable APIs and hashes from the current repository.

Stage 4.4 original order/spec SHA-256: `71C62369A68ED8CB61BB04539FF9F2C13D2B9B237C6B10449C3CBE5340487009`.
Stage 4.4 original acceptance matrix SHA-256: `A09FB76C07AB12AB9C435CAD1B29806D4B4DB839B12191444BE4507DFE0D9BB8`.

Current frozen production is the authority for accepted behavior, including subsequent preview fixes. Earlier simple-shear sharing, section stress distributions, and source qualifications for a different topology must not be silently reused as complete multi-angle moment-base response.

Preparation limitation: ChatGPT reviewed accessible controlled source/specification material and independently checked reference arithmetic; it did not execute the current repository's production APIs or inspect its private Git objects. Codex must complete the actual native compatibility audit. Reuse existing readable source copies; do not ask for duplicate attachments unless genuinely inaccessible.

## 4. Supported profiles and layouts

Use three explicit receiving-column families:

- `WI`: uniform doubly symmetric W/I section, two flanges and web.
- `RHS`: rectangular hollow section including square, with explicit wall thickness and cavity.
- `SRS`: solid rectangular section including square, with continuous solid material rather than a fictitious wall/cavity model.

RHS/SRS rectangular coverage in this new product is an explicit project addition; it does not expand the frozen square-only Stage 4.3 product. Use existing accepted rectangular profile primitives where present. Do not add hybrid/asymmetric material layouts, tapered/rounded arbitrary profiles, sloped columns, Channel/Angle columns or circular members in this RC1.

For every family implement three layouts:

| Layout | Active connector faces | W/I interpretation | RHS/SRS interpretation |
| --- | --- | --- | --- |
| `TWO_X` | `X_POS`, `X_NEG` | One angle on each broad web face | One angle on each opposite X exterior face |
| `TWO_Y` | `Y_POS`, `Y_NEG` | One angle on each exterior flange | One angle on each opposite Y exterior face |
| `FOUR_XY` | All four | Exterior flange pair plus opposite web-face pair | One angle on each exterior face |

This gives nine logical family/layout combinations. Do not attach a W/I X-face bracket to an imaginary face at the flange-width bounding box: its receiving surface is the actual web. Two-angle configurations accept the same biaxial inputs but remain conditional on an applicable complete response. Do not claim a two-angle pair always resists, or never resists, an orthogonal moment from connector count alone.

All connector feet point outward from their receiving faces onto a finite concrete pedestal. No hidden base plate, stiffener, backing plate, sleeve, internal nut, cavity fill or access opening is introduced. Such details would change the load path and require separate authority.

## 5. Global frame, physical end and signs

Use a right-handed orthonormal base frame `(X,Y,Z)`, with column extrusion along `+Z`. For W/I, X runs across flange width B and Y across overall depth D. For RHS/SRS, X spans B and Y spans D. Show actual axes rather than asserting X is always the stronger axis of a nonsquare section.

For uniform reference sections centered in plan, the native centroid is at `(0,0)` before placement. The nominal physical lower end is at Z=0. Allow named column-placement offsets relative to foundation report origin O; the actual applied centroid C includes those offsets. Defaults are zero. O is on the foundation top plane, initially the pedestal plan center.

Inputs are column-on-base actions at the actual native centroid of the lower end:

`F_C = (Vx,Vy,N)`

`M_C = (Mx,My,0)`.

Positive N is uplift; negative N is compression. Moments use physical right-hand signs. No W/I beam structural-sign conversion is applied to these column inputs. Independently applied input Mz is outside RC1 and rejected if nonzero; reference-generated Mz and all connector local free moments are retained.

Inputs are already resolved factored actions. Do not add self-weight, pretension, preload, thermal action or load combinations. Column view length is presentation-only, not a moment lever arm, column end, failure-plane location, restraint or unbraced length.

## 6. Required total foundation action

For a local input frame Q at physical reference r_R and report reference r_O:

`F_O = Q F_R`

`M_O = Q M_R + (r_R-r_O) cross F_O`.

The opposite reaction is `(-F_O,-M_O)` at the same reference and must not be added as a second applied load.

This total is available independently of connector sharing. For centered, flush default geometry, C=O and the input moments pass through unchanged. Nonzero placement offsets can generate additional bending and Mz; changing display length cannot. For the independent offset fixture, C=(2,-1,0) in with F=(5,-3,-20) kip and M_C=(60,40,0) kip-in gives M_O=(80,80,-1) kip-in. The fixture is not a stiffness/contact solution.

Use native quantities and exact rational transforms over authoritative finite/rational input values. Keep proof targets, native outputs and any native-serialization diagnostic separate. Do not force residuals to zero by rounding or assigning them to another bracket.

## 7. Constructive presets and controlled feasibility tuning

Provide five section presets, each with all three layouts, in US and equivalent SI units:

- W/I: B=12 in, D=12 in, tf=tw=0.5 in.
- Hollow square: B=D=8 in, wall t=0.5 in.
- Hollow rectangle: B=10 in, D=8 in, wall t=0.5 in.
- Solid square: B=D=8 in.
- Solid rectangle: B=10 in, D=8 in.

Common starting connector geometry: extrusion length 6 in; vertical member leg 8 in; outward foot 6 in; thickness 0.5 in; inside radius 0.25 in. Tangential extrusion centers are at the selected face midpoint. Each foot has a 2-by-2 anchor pattern with 3-in tangential gauge, 2-in outward pitch, and outward centroid 3 in from its nominal receiving-face line. Member bolts use two tangential lines at +/-1.5 in and two vertical rows at 2-in pitch.

Explicit member elevations:

- X-pair: Z=2 and 4 in, vertical centroid 3 in.
- Y-pair: Z=5 and 7 in, vertical centroid 6 in.

Use these pair elevations in both two- and four-angle presets for transparent topology switching. For RHS/SRS four-angle layouts this vertical separation prevents the perpendicular through-shanks from crossing. These are deliberate preset coordinates, not hidden automatic staggering. A user edit that creates a collision must be rejected with a useful field-level reason, not silently repaired.

Nominal member bolts and foundation shanks: 0.5 in. Physical US-source round holes: 0.563 in. Foundation geometric embedment: 4 in. Pedestal starting plan: 40 by 40 in; depth 12 in; top at Z=0. Column display length: 18 in. Use the current accepted hardware geometry policy; preserve its actual source/properties, nominal washer/head/nut dimensions and installation clearances. Do not silently enlarge material strengths or reduce safety factors to obtain a passing example.

These are constructive examples, not certified designs. Before mutation audit all fifteen geometry/layout combinations against the real baseline profile, fillet, solid, washer and path resolvers. A recorded geometry-only preset adjustment to achieve actual clearance is authorized within the same topology/material/factor scope. Adjust only the new product's fixture catalogue, not the independent reference fixtures or old goldens. Do not respond to a bad starting clearance by inventing reinforcement or changing a load path.

## 8. Local connector frames and physical grid mapping

For every connector use the unchanged Slice 7 core frame `(A,B,C)`, where A is horizontal extrusion, B points up the upright, and C points outward along the foot. Q has columns A,B,C, all in the global frame:

| Face | A | B | C |
| --- | --- | --- | --- |
| X_POS | +Y | +Z | +X |
| X_NEG | -Y | +Z | -X |
| Y_POS | -X | +Z | +Y |
| Y_NEG | +X | +Z | -Y |

Each is a proper rotation, determinant +1. Opposite faces are not represented by an improper reflection. Exact origins, fillet positions and member/foot reference offsets come from actual geometry and the native core contract; do not presume the core heel is on Z=0 if its physical origin differs.

For a separate upward-normal foot response frame use a declared proper basis such as `(u,v,n)=(A,-C,B)`; do not silently use `(A,C,B)`, which has the wrong handedness. The connector core's own frame remains unchanged.

Opposite connector member grids align by global physical shank coordinates. Their local A directions reverse, so copying a local index/sign is not sufficient. Give shared physical bolt patterns one canonical owner and derived per-face coordinates. Independent connector dimensions remain editable where the common holes still physically fit. Such geometric linking proves neither equal stiffness nor equal force.

Column LW is Z. Connector LW is A. Per-face CW/TT are backend derived; the frontend cannot choose a resistance direction from camera orientation.

## 9. W/I physical bolts and connected regions

### Exterior flange pair

Each Y-face bolt is a short independent bolt through one angle upright and the selected flange, with real head/washer/nut on its outer terminal surfaces. Retain the internal web and fillets for washer/access validation. Do not extend it through the entire column depth or opposite flange by default.

### Opposite web-face pair

Each aligned X-pair bolt is one continuous physical shank through ANGLE / WEB / ANGLE, with two actual interfaces and exterior terminal hardware. Both connectors refer to the same physical bolt ID. Do not render or count two coincident shanks. The actual source/accepted method controls the two plane demands; do not use blind 2x capacity or halve the force solely because the stack has two interfaces.

### Four angles

Combine those actual two arrangements. Check web-angle ends against the flanges, upright/foot/anchor interference, rear flange-bolt hardware, shared web bolts, and all holes. Web bolts must not enter the flanges or heel region. Preserve all region identities for local and column-end-zone checks.

## 10. Hollow/solid common through-bolts

RHS/SRS use exterior-to-exterior common shanks for each active opposite pair. The production topology is not a set of independent blind bolts.

RHS ordered path:

`ANGLE_POS / NEAR_WALL / CAVITY_FREE_SHANK / FAR_WALL / ANGLE_NEG`.

SRS ordered path:

`ANGLE_POS / CONTINUOUS_SOLID_SECTION / ANGLE_NEG`.

One head and terminal washer at one exterior bracket, one nut and terminal washer at the opposite bracket. No invisible cavity hardware, artificial center bearing layer or automatic sleeve. All actual material/void intersections and shaft lengths are retained.

In FOUR_XY the perpendicular physical shaft sets must have nonintersecting finite envelopes. Validate both nominal shanks and drilled hole envelopes, not only points or a rendered X-ray. The reference heights provide minimum axis separation 1 in for 0.5-in shanks, but the full native hardware/solid checks remain necessary. Do not automatically move another group's rows after an edit.

Two walls or two brackets do not by themselves define the load carried by each wall, a double-shear capacity, or a normal-pressure distribution. Long-shank bending, wall crushing/local deformation, contact and physical shaft-section forces must be covered by the accepted response authority. Solid grip depth is not automatically an effective thickness in every plate or pull-through formula.

## 11. Physical identity versus analytical branch identity

Retain separately:

- connector branch IDs and complete local wrenches;
- physical bolt/shank IDs;
- real contact/layer/interface IDs;
- actual shaft sections and their signed demands;
- per-region hole reactions and material axes.

A bolt shared by two connectors is one physical bolt with coupled response, not two independent capacities. Do not add a bolt section force and its equal/opposite internal action to the total external foundation load. Source-provided ordered section-equilibrium ledgers may be checked, but they are not a new stiffness/bending solver.

## 12. Complete two-/four-angle base-response source

Implement a product-specific adapter/validator, logical identity:

`QUALIFIED_WI_RHS_SRS_MULTI_ANGLE_BASE_RESPONSE_RC1`.

Reuse frozen Stage 4.4 and Stage 4.3 material-neutral source infrastructure additively. Do not attach their older topology/source domain to these new assemblies without an explicit matching authority.

A permitted production response is either a trusted server-controlled applicable record for the current physical assembly/load, or a previously accepted analysis provider whose verified domain explicitly includes that assembly, shared-shank topology and contact state. No new universal spring, rigid plate, N/n+M/I, stiffness-weighted, elastic-section-to-bracket, contact active-set or prying solver is authorized here.

The record binds exact profile/fillets, active face set and pair orientations, connector geometries/materials, every physical bolt and real penetrated region, holes/grip/hardware, pedestal/contact boundaries, lower-end reference, signed load, source revision/hash and compatibility/qualification basis. Profile/face/layout, load reversal, hardware and placement changes invalidate incompatible records. A typed name or self-declared qualified=true is not evidence of trust.

The complete response must supply all active column-on-connector member wrenches, separate direct column-on-foundation contact (or certified inactive zero), relevant coupled shared-shank/local-region response, exact references/proper frames and coverage/availability metadata. Missing demanded data is not zero. A source containing only strengths or an aggregate utilization is not a load-distribution source.

## 13. Equilibrium, compatibility and admissibility remain distinct

At one physical reference, with outward column transfer signs:

`W_column = sum(shift(W_column_to_member_i)) + W_direct_column_contact`.

There are two or four terms as dictated by the active topology, not by array length alone. Reject omitted, duplicate or inactive-extra branches. Preserve local free moments. An equilibrated arbitrary allocation is not self-qualifying; F45-14 deliberately supplies two different equilibrated allocations for the same total.

Complete response validation must verify trusted source/domain, declared compatibility/contact basis, physical admissibility and exact conservation as separate requirements. Do not infer stiffness/full-strength classification from equilibrium PASS.

When no applicable response exists for a nonzero load, expose required total foundation action and SOURCE_REQUIRED branch/shaft/contact scopes. Do not invent N/2, N/4, M/z or a plane-stress distribution to populate tables. This source-limited mode is expected and is not a development stop; the source-present integration still must be implemented and exercised.

## 14. Contact accounting and source proof

Nominal flush geometry represents prepared bearing surfaces, not their active pressure under load. For direct column-on-foundation compression contact with upward n:

`dF = -p n dA`, `p >= 0`.

Pressure patches must lie on the real W/I, hollow-ring or solid footprint. A net resultant located at a hollow-section centroid can legitimately represent several wall patches; it is not permission to place pressure in the cavity. Compression sign alone does not establish full contact. No tensile bearing, arbitrary abs/clipping, friction transfer or pressure over removed material is permitted in this RC1.

A net connector-on-foundation foot wrench may already include its anchors and foot contact. Sum net feet plus direct column contact once. If a qualified detailed anchor/foot-contact breakdown exists, check that it exactly recovers that net foot wrench; do not add both into the total.

Input sign reversal negates the required wrench transport, but it does not automatically negate a previous tensile-bolt/compression-contact solution. Use a newly applicable response/active state.

Use the existing accepted exact finite-value/rational source proof contract. No added tolerance for an arbitrary approximate solver record. Reuse an existing source numerical-proof contract only within its declared domain. Do not alter supplied demand to make closure pass or introduce a balancing free couple absent from the actual source.

## 15. Native connector and member demand integration

For each source-resolved active branch, pass its complete member-interface wrench at its actual local reference to the unchanged Slice 7 core. Retain member, heel and foot wrenches and native core equilibrium. Two-/four-branch routing is new integration, not permission to change the core.

For an actual member plane `(A,B)`, the Slice 8 in-plane subset is `(FA,FB,MC)`. The complementary `(FC,MA,MB)` is explicit and requires suitable normal/contact response. A shared-shank response may constrain per-interface reactions differently from an isolated equal-stiffness in-plane projection; use an accepted applicable model or record, not an automatic overlay of incompatible distributions.

Slice 8 handles independent in-plane free moments. Do not pass those moments into Stage 2.5A's known unsupported end-moment path. Use Stage 2.5A only for subcases already within its accepted applicability. Keep actual grid coordinates and wrench reference together; physically translating only one changes demand.

The numerical interface oracle is a direct native call with independently assembled physical inputs. Reference rational fixture strings do not replace native Decimal output. Keep native proof and later serialization diagnostic separate; no hard-coded tiny residual from Stage 4.2/4.3/4.4.

## 16. Native FRP and metallic-bolt checking

Run resistance only on explicit design and only with resolved applicable demands. Use unchanged native engines/providers for metallic bolt shear, tension and interaction, actual shaft/plane demands, source/thread/grip applicability and local FRP modes. Preserve known long-grip source adjustments and source-required coverage where applicable; do not infer an F593 strength from the text 316/316L alone.

Check actual angle uprights, W/I web/flanges, RHS walls and source-defined SRS receiving regions independently, with actual material LW/CW/TT and native factors. Do not replace the solid section's unresolved local response with an invented thin plate. Evaluate bearing, net tension, shear-out, cleavage, block shear and pull-through only within actual source/geometric applicability. Do not discard a legitimate failure because another source is missing.

The FRP angle instep shear path applies only to its native local extrusion-axis shear, not automatically to vertical column force. Full-wrench body/heel/normal response and capacity remain separately source-qualified. Per-angle or per-wall PASS does not qualify combined column-end-zone, flange-web junction or box-wall interaction.

Metallic fasteners may retain already available stainless-steel bolt metadata/strength sources. This does not implement the deferred 316SS material provider for angle connectors.

## 17. Scope/status contract

Keep distinct status/proof records for geometry, required total foundation transport, complete base response/branch allocation, direct contact, each connector core/body/member attachment, coupled physical bolts/shaft sections, actual local FRP regions, common column-end zone, net foundation handoff, external anchor/concrete design and overall column analysis.

Use accepted status precedence: invalid geometry/input; actual evaluated required failure; missing/unavailable required source or coverage; qualified-source/engineering-review-constrained internal success. No ordinary whole-base PASS. Every FAIL needs an identifiable native reason or failed-check record. Missing source is not numerical failure and is not zero demand.

With all actions exactly zero and no self-weight/preload/pretension, zero transfer may be shown as separately proven; zero demand does not certify strength or future load adequacy. Do not import Stage 4.2's default FAIL or any fixed native governing check into this new product.

Always retain `EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED` or native compatible wording, whole-column `NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY`, and stiffness/rotation/full-strength NOT_EVALUATED. ASCE 74 Chapter 6 member interaction is not a bolt-group distribution or base-sharing equation and is not newly implemented here.

## 18. API and architecture

Add one distinct product and repository-conventional preview/preset/design routes. Reuse material-neutral geometry, quantities, frames, source contracts, response validators, snapshots and result types where compatible. Additive exports/route/selector registries, exact route inventories and domain DTO bindings are authorized; do not substitute fake L-column dimensions into the Stage 4.4 product.

Prefer new Stage 4.5 adapters and workspace files. Do not refactor inherited equations, source semantics or shared viewer behavior merely for convenience. Preserve all accepted historical product outputs and frozen fixtures. An internal helper may be reused without extending its original public domain; otherwise use an additive new wrapper/provider key.

Preview may resolve geometry, total demand and source-binding/demand validation within the accepted preview contract; it must call zero resistance functions. Design is explicit. All current records bind the exact normalized physical request, geometry/material/source/reference identities and stable physical IDs.

## 19. Frontend controls and source clarity

Provide Column profile/dimensions, Layout TWO_X/TWO_Y/FOUR_XY, Placement/reference, Foundation geometry, Actions, active Connector sections, Physical member-bolt pair sections and Qualification sections. Use full-width nested groups, readable engineering labels and no fieldsets squeezed next to a radius or diameter.

Make the W/I distinction explicit: X pair is on web faces; Y pair is on exterior flanges. For common-bolt pairs provide one editable canonical grid/bolt identity with clearly marked derived opposite-face fields. Independent connector dimensions may differ when physical alignment remains valid. Do not duplicate editable contradictory grids or label geometric mirroring as load symmetry.

Topology switching removes inactive geometry/results and clears incompatible qualified sources. Preserve signed N/Vx/Vy/Mx/My. Show actual normal-response and capacity sources separately from required total action and per-bolt demand. Default sources remain genuinely absent when no production record exists; no synthetic production option.

## 20. Current preview, invalid inputs and request races

Carry forward the corrected Stage 4.4 behavior rather than its original weak stale-state labeling. Every valid geometry/load/hardware edit must drive a current backend preview and corresponding scene/action labels. Validate this end to end, not by checking only that a request was queued.

During an invalid request or invalid current input, keep editor values, show a prominent viewer-level LAST VALID state and field-relevant validation reasons, hide stale force/moment labels, retain only the explicitly prior scene, and block stale design. Do not create a partial current scene from invalid hardware. Correcting back to valid must automatically replace the scene/actions and mark old design stale.

Test empty/sign-only numeric intermediate edits without zero coercion; valid-valid, valid-invalid, invalid-valid, rapid edits, delayed responses, aborts, network/HTTP failures and switching profile/layout while requests are pending. Current result tables, status and geometry/action snapshot must identify the same current normalized input. Older responses cannot overwrite newer state.

Presentation-only orbit/fit/X-ray/selection and view length do not change engineering identity or rerun design. Unit switching converts physical values through native quantities; it does not regenerate a different hole or silently grant qualification.

## 21. 3D and real-browser review

Render the actual W/I/hollow/solid section, two or four connectors, unique common/independent shanks, genuine terminal hardware, separate feet/anchors and concrete pedestal. Use proper object-kind appearance: do not color a concrete pedestal as FRP or fill a hollow section with an opaque bounding box. X-ray shows real voids and inside shaft paths.

Inspect top and orthogonal sides: W/I web brackets between flanges, separate flange bolts, common opposite web bolts, RHS/SRS orthogonal sets at distinct elevations, no hidden cavity nuts, no feet intersecting a column or each other. Signed action arrows/editors must be visible and independently clickable, not occluded by overlapping labels.

Run a real-browser matrix covering all nine family/layout modes, both nonsquare section variants, US/SI presentation, valid independent load/dimension/member-bolt/foundation edits, invalid crossing/washer/containment cases, recovery and source invalidation. One view is not proof of all topologies. Capture at least one geometric view per fifteen preset/layout cases plus targeted before/after request-state screenshots, using the actual app root and backend APIs. No new browser dependency is authorized; use existing approved browser/CDP infrastructure.

## 22. Acceptance and test-oracle design

Implement all T45-001..T45-120 and F45-01..F45-24. The independent fixture algebra includes section footprints, proper frames, full wrench transport, nonunique static allocations, contact accounting, source rejection, real bolt reference shifts, supplied long-shank force ledgers, crossing-clearance and units. They are not manufacturer/source qualification or substitutes for production native outputs.

The source-absent sweep is **5 section presets x 3 layouts x 12 loads x 2 units = 360**. Assert normalization, actual geometry/path/reference, exact total demand, statuses and absence of invented branch quantities, not just constructor success.

The source-present suite is **15 preset/layout cases x 3 loads x 2 units = 90**; loads are combined compression, combined uplift reversal and pure biaxial. Bind each synthetic record to its actual geometry/load. Exercise two/four cores, coupled common-shank/normal demands, native capacities, local regions, contact accounted once and foundation handoff. Include applicable success/failure/missing-capacity cases without changing production material properties. Do not make these tests pass by mocking away the very integration under test or showing source absence in every case.

Add negative/mutation tests for wrong profiles, active faces, source revision/load sign, mirrored versus proper frame, changed reference, missing branch, duplicate shaft, inconsistent wall reaction, tensile contact, contact in void, double-counted net feet, intersecting shanks, incompatible sources and stale UI responses. A reference fixture's rational Ixx/Iyy does not authorize a new section-stress-to-bracket allocation.

Future-phase evidence is PENDING until reached: local/isolated gates do not require a future hosted-CI run or owner approval. The matrix phase policy prevents circular pre-push/CI requirements.

## 23. One consolidated preflight and candidate-scope projection

Before implementation mutation, perform the complete package/source/geometry/API/scope audit. Temporary read-only diagnostics, in-memory change projections and external scratch files are authorized.

Identify actual baseline callable APIs, frames/references, material/source requirements, precision/proof contracts, common-shank representation, presets, planned additive paths and required tests. Inspect all nine modes and fifteen geometric candidates before implementing only the first one. Source-limited production is expected; a missing manufacturer qualification record is not itself an implementation stop.

Search repository-wide for historical hashes compared to current source/package trees, old allowed-path lists treated as permanent future scope, source-prefix insertion coupling, test inventories/routes, shallow/tag dependencies, and known long interactive-test timing. Project the full planned change set through those guards. Append new source-register entries without disturbing frozen prefixes.

Consolidate all safely discoverable genuine conflicts. Continue other read-only checks after the first discrepancy. Resolve authorized adapter/preset/test-maintenance issues within this order, without a new owner request for each filename. Do not change an actual physical or engineering authority to avoid a legitimate stop.

## 24. Bounded historical-test and inventory maintenance

Narrow tests-only successor-safety maintenance is authorized across whichever existing test roots/test-only evidence helpers the preflight identifies. No filename-by-filename reapproval is needed for this known class. Additive exact route/selector inventories may be updated for the new endpoints; retain old entries and assertions.

Separate historical identity from current task scope:

1. Historical hashes/objects are checked against their original immutable snapshot, manifest or Git object. Never replace old expected digests with current hashes or substitute successor HEAD for a missing historical object.
2. Current Stage 4.5 changed paths are compared to a recorded explicit candidate inventory for this order: new product, narrowly additive shared glue, tests/fixtures and governance. An old nine-file security allowlist must not govern all later development.

Maintain historical tamper tests and current unauthorized-change tests. Detect historical changes/add/delete/rename, tag/manifest/object substitution and unrelated current source changes. No wildcard acceptance of all tests/source, skips/xfails, removed coverage or old-manifest/tag edits. A tagless depth-one run may use a controlled manifest/snapshot mode, but must report that mode honestly and must not claim absent historical bytes were fetched or compared.

Include forward-successor probes that show a later separately declared governance append/maintenance change does not invalidate an earlier historical digest. These test fixtures do not authorize unknown future production changes now. Never freeze the new whole current tree as an accidental permanent substitute for the historical record.

Keep the maintenance in the one planned implementation commit when discovered before commit. One explicitly bounded unpublished tests-only correction/amend is permitted under section 29 if a missed same-class guard appears only after commit. Do not rewrite a published commit.

## 25. Verification and network permissions

Upon owner handoff approval, necessary existing QA activity is authorized for this repository: npm metadata/advisory queries to `https://registry.npmjs.org/`, full and runtime audits, and locked package retrieval/clean npm ci using the existing lockfile's integrity-checked registry records. No package publication, credential changes, audit-fix, new dependency, lockfile update, unrelated endpoint or secret/source upload is authorized.

Use existing trusted Python tooling and locked requirements according to repository policy. An approved module invocation such as `python -m mypy` may replace a blocked wrapper only when it is permitted by the environment/security policy and loads the same package/configuration/targets. Existing trusted Linux/WSL verification is permitted; do not disable Application Control or install a new operating system. Git-aware blob/EOL comparison must distinguish checked-out CRLF from controlled canonical bytes without weakening artifact hashes.

Automatically start or reuse compatible local backend/frontend servers and inspect localhost in the approved browser. Report actual URLs/ports, process/session ownership and health checks. Use new free ports rather than kill unrelated owner sessions. Stop only processes you started. Do not introduce startup scripts/dependencies just to avoid opening terminals.

If a registry call fails transiently, retry with bounded attempts and record the distinction between service failure and actual vulnerability. No cached audit PASS substituted for a required current successful audit; no --force or suppressed findings. A new dependency vulnerability requiring a version change is outside this implementation order and must be consolidated/reported.

## 26. Full QA and browser acceptance gates

Run complete configured backend/frontend suites, Ruff, strict mypy, ESLint, strict TypeScript, production build, runtime/import/API checks, dependency-tree validation, pip check, JSON/whitespace checks and both npm audits. Require configured 100% coverage and zero current audit findings. Baseline counts 3963/710 are reference counts; new tests increase them. Do not lower test discovery or coverage to match a count.

Run all existing independent engine goldens and available freeze audits, the twelve-tag manifest identity checks, the new acceptance map/reference fixtures/sweeps, and actual browser review. Verify every unapproved baseline blob remains unchanged. Append-only governance/source-register constraints remain exact.

Cache and reuse successful untouched read-only evidence only where its inputs/tooling did not change; rerun directly affected checks. Complete final local QA and complete exact-commit isolated QA remain mandatory. No repeated owner visual acceptance is requested before publication; the final new-product owner acceptance is genuinely pending afterward.

## 27. Bounded Windows interactive-test timing maintenance

No global timeout or arbitrary sleeps. For a long new Stage 4.5 integration test, an explicit per-test ceiling up to 15000 ms may be selected after measuring its actual UI work; this is not an application performance benchmark. Retain all assertions/interactions and time-budget evidence.

For a pre-existing test or a hosted-only 5000-ms timeout: retry the affected Windows job once when the only failure is timing with no assertion/application/request/runtime defect. If the same test repeats and diagnosis supports runner timing rather than product failure, at most **three** tests in this order may receive only a local per-test timeout up to 15000 ms. Require 10 consecutive local Windows passes for each under the comparable coverage command where available. Do not alter global config, test logic, expected results, dependency versions or workflows.

If found before commit, include the narrow test maintenance in the implementation commit. If found after publication, create one normal successor with subject `test: stabilize Windows column moment base coverage`; preserve the published implementation, rerun full local/isolated QA and obtain hosted four-job evidence. Report actual count rather than forcing 119. A real assertion/product failure or repeated failure at the approved ceiling requires a consolidated report, not another automatic timeout increase.

## 28. Staging, commit and isolated verification

Review all new/modified/deleted paths, native numerical authority, protected records and source-prefix preservation. Use explicit-path staging only, never git add . or git add -A. Commit no licensed PDFs, screenshots, logs, application credentials, environments, build/coverage output or temporary checkers. Store browser reports/logs externally; controlled QA summaries and new acceptance fixtures may be committed.

Create the normally single implementation commit:

`feat: add W/I RHS SRS column moment bases`.

Expected full-history count:119 when no later timing successor is needed. Do not embed this commit's unknown self-hash or future hosted run in precommit bytes; use accepted baseline and external postcommit evidence. Verify staged and final commit scope, expected parent, no old tags changed and clean active worktree.

Before push, create a genuinely fresh clone of the exact candidate using depth one, --no-local and no tags, with one reachable commit, no alternates/object borrowing and no global/shallow workaround that secretly fetches historical objects. Copy/retrieve only existing locked runtime/test dependencies as allowed, never unstaged working files. Run complete QA against that exact commit and verify the checkout stays clean.

Do not demand full-history commit count or remote-equals-unpublished-HEAD inside the isolated clone. Report active candidate, remote baseline and isolated resolution modes truthfully. No QA bypass or amendment to a published object.

## 29. Bounded unpublished successor-test repair

If exact-commit isolated verification reveals only a missed historical-versus-current guard in the already-authorized tests-only class, one unpublished amend is preauthorized for this order. First prove no push occurred, preserve the pre-amend object, and change only that identified test/evidence mechanism with historical/current tamper tests. Production, engineering fixtures, dependencies and workflows must remain object-identical between the two candidate commits. Preserve subject and reachable count; report old/new full hashes.

Then repeat complete local and fresh object-isolated QA. No repeated amend cycle, other protected-scope repair, hidden production change or force-push is authorized. Other genuine postcommit verification failures require one consolidated report. This narrow rule prevents a routine missed historical test from forcing a separate approval round while preserving the engineering gate.

## 30. Publish, hosted evidence and stop after owner-review handoff

After successful local, browser and object-isolated verification, owner handoff approving this order authorizes a normal non-force push of the exact unchanged verified commit to `main` at:

`https://github.com/baraa-misto/frp-master-connection.git`.

No tags. Check remote advancement; do not overwrite unrelated work or merge/rebase blindly. Verify active HEAD/origin-main/remote-main equality after push. Hosted QA is then required for Backend Ubuntu/Windows and Frontend Ubuntu/Windows on the actual published SHA. Do not require future CI before the push which triggers it. Use section 27 only for its bounded timing case.

Do not claim live authenticated GitHub evidence when authentication is unavailable. Report PENDING and preserve the verified commit; the environment's permission/security restrictions still apply despite owner task authorization.

Leave the verified local application running/open for owner review, with URL, process/session identifiers and current code/commit identity. Retain source-limited behavior and all qualification notices. Do not mark Stage 4.5 frozen, tag it, claim all moment families fully adequate, begin 316SS, or start another stage.

## 31. Completion evidence

Provide a compact numbered report and an external detailed ledger containing: full starting/final SHA and count; actual tag objects/targets; source/package hashes; actual native APIs/numeric boundaries; full changed-path inventory; fifteen preset/layout feasibility records; shared bolt ownership and orthogonal elevations; total and source-qualified branch/contact proofs; actual local/shaft/source coverage; all 120 requirement dispositions with test/evidence links; 24 fixture results; 360 and 90 sweep results; all test/coverage/static/build/audit results; browser valid/invalid/recovery screenshots and network/fingerprint evidence; all bounded maintenance and any old/new unpublished hashes; isolated clone facts; normal push and hosted run/attempt/jobs; running URL/processes; remaining qualification/external boundaries; owner acceptance PENDING.

Engineering conflicts, frozen-behavior changes, unapproved load paths, manufactured qualification, dependency/workflow changes or failures outside bounded maintenance require a consolidated stop. Expected missing sources, authorized new adapters, exact route-inventory updates, allowed preset-clearance tuning and known historical-test maintenance do not require recurring owner approval.

**END OF STAGE 4.5 W/I RHS SRS COLUMN MOMENT BASES ORDER RC1 - DO NOT PROCEED IF THIS LINE IS MISSING**
