# Validation and QA Plan

## Stage 4.4 RC1 current successor

`ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION` / `4.4-RC1` starts from
`1faa1ff522d0e0a39a42e2dc2d3974b5dba98479` (114 commits). Equal and unequal
FRP Angle columns each have exactly two independent FRP base angles, one on each
different leg, with actual member bolts and separate foundation attachment groups.

One new product uses the accepted Angle geometry, material-neutral Slice 7 core/FRP provider and Slice 8 native in-plane demand. Source-limited branch allocation remains explicit; total required foundation actions are available without invented connector or anchor response. Historical frozen families are unchanged.

See [native integration/source boundaries](../engineering/STAGE_4_4_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md)
and [96-requirement QA catalogue](../qa/STAGE_4_4_ANGLE_COLUMN_MOMENT_BASE.md).
The exact implementation subject is `feat: add angle-column two-leg moment base connection`;
normal expected count 115. Local, browser and fresh object-isolated QA precede the
normal non-force main push; direct four-job CI follows it. Future CI is not inferred.
All eleven existing freeze tags remain immutable. Owner final visual/result acceptance
is PENDING; no Stage 4.4 freeze, Stage 4.5 or 316SS expansion is authorized.

| Control | Value |
|---|---|
| Document ID | FMC-QA-PLAN-001 |
| Stage | 2.2B |
| Plan status | Draft; bounded numerical, orchestration, and stateless API gates implemented; broader gates pending |
| Application calculations | Limited Stage 2.1B single-bolt/single-row engine with Stage 2.2A orchestration and Stage 2.2B transport |
| Commercially validated calculation families | None |

## Purpose

This plan defines the evidence and approvals required before a calculation family can be described as verified, validated, released, or commercially usable. Stage 0.1 created the control framework; Stages 2.1A, 2.1B, 2.2A, and 2.2B now add the explicitly bounded contract, numerical, fixture, canonical-orchestration, and stateless-transport software evidence recorded below. That evidence does not validate a general connection family or authorize commercial use.

**No calculation family is commercially validated until its qualified engineering review gate is Approved and the applicable release freeze is complete.**

## Governing principles

- Validation is scoped to a named capability, topology, input range, engineering basis, edition, errata set, material-data versions, and rule-set version.
- Geometry support is not evidence of calculation support.
- Source verification, applicability approval, implementation verification, independent calculation verification, integration testing, security testing, and engineering approval are distinct gates.
- Expected results come from controlled independent evidence, not from copying the implementation under test.
- Unsupported, incomplete, invalid, stale, not-applicable, not-covered, and review-required outcomes are tested as first-class results.
- Warnings may supplement but never replace a required fail-closed state.
- A changed source, errata set, rule, material dataset, manufacturer dataset, schema, or calculation dependency triggers a documented impact review and revalidation scope.

## Validation gates

| Gate | Required outcome | Minimum evidence | Approval owner |
|---|---|---|---|
| G0 — Controlled definition | Capability and intended user-facing scope are unambiguous. | Capability ID; topology; canonical inputs; intended result levels; exclusions; risk links; version identifiers. | Product and Engineering Leads |
| G1 — Source verification | Every engineering basis is authorized, edition-aware, correction-aware, and traceable. | Source-register entry; controlled-copy verification; verified errata/correction set; mapping reviewer; no unlicensed repository content. | Engineering Source Custodian |
| G2 — Applicability verification | Supported and unsupported conditions are explicit and fail closed. | Coverage-matrix row; mapped references; input requirements; applicability constraints; unsupported triggers; result-state rules; qualified engineering approval of scope. | Qualified Engineering Reviewer |
| G3 — Implementation verification | Deterministic implementation matches the approved mapping within scope. | Traceable unit tests; independent expected values; branch and invalid-input tests; unit controls; review record; no placeholder PASS/FAIL path. | Engineering Development Lead and QA Lead |
| G4 — Independent engineering validation | Results agree with calculations prepared independently of production code. | Controlled hand calculations; known PASS and FAIL cases; boundary cases; sign and direction cases; combined-action cases; discrepancies resolved; reviewer independence recorded. | Independent Qualified Engineer |
| G5 — Model and reproducibility integration | Persistence, fingerprints, views, and reports remain consistent with canonical engineering data. | Save/reopen tests; fingerprint tests; stale-result tests; 3D/2D/calculation consistency; visual regression; immutable report-snapshot tests. | QA Lead |
| G6 — Security and project isolation | Engineering inputs, projects, results, and reports are protected by server-side identity and entitlement boundaries. | Authorization and isolation tests; cross-user and cross-organization negative tests; report/object access tests; audit evidence. | Security Owner |
| G7 — Qualified engineering review | The complete evidence package supports release for the bounded scope. | Signed review checklist; open-risk disposition; limitation text; coverage approval; validation summary; approval authority and date. | Qualified Engineering Approval Authority |
| G8 — Release freeze | Exact approved artifacts and versions are immutable and reproducible. | Frozen source, rule set, schema, datasets, fixtures, snapshots, fingerprints, release notes, artifact hashes, and rollback/recalculation policy. | Release Authority with Engineering concurrence |

Failure or missing evidence at any gate leaves the capability unapproved. A later gate cannot waive an earlier gate without a controlled decision by the appropriate authority.

## Required future verification coverage

| Verification area | Required future evidence |
|---|---|
| Source verification | Bibliographic record, authorized controlled-copy review, edition confirmation, errata/correction verification, mapper/reviewer identities, and traceable references without reproducing licensed content |
| Applicability verification | In-scope examples, out-of-scope examples, boundary classifications, required inputs, unsupported-condition triggers, and expected fail-closed statuses |
| Unit tests | Deterministic tests for each approved rule, input normalization, branch, error state, metadata field, and result provenance item |
| Independent hand calculations | Independently prepared and reviewed cases whose expected outcomes and intermediate values do not originate from production code |
| Known PASS and FAIL cases | At least one controlled case on each side of every implemented governing check, created only after the engineering method is approved |
| Boundary and invalid geometry | Cases at, immediately within, immediately outside, and structurally invalid relative to each approved applicability boundary, without embedding licensed source text |
| Positive and negative force cases | Signed cases for every supported action component, plus explicit fail-closed expectations for unsupported components |
| Reversed member directions | Physically equivalent and intentionally non-equivalent cases that exercise approved frame and sign transformations |
| Combined actions | Cases for actions sharing an interface, component, bolt group, supporting region, or whole joint; independent interface checks alone are insufficient |
| English/SI equivalence | Equivalent physical inputs through both unit interfaces, compared after approved canonical normalization with controlled tolerances |
| Property-based tests | Invariants for units, serialization, ordering, identifier stability, direction reversal where valid, and geometry/data relationships; generated cases remain within declared domains |
| Save/reopen reproducibility | Canonical engineering input, version references, and immutable prior snapshots remain unchanged through persistence round trips |
| Fingerprint reproducibility | Equivalent canonical inputs and versions yield the same fingerprint; every fingerprint-relevant engineering change changes it; ownership metadata does not |
| Visual regression | Controlled 3D and vector-view snapshots for supported geometry, selections, force-arrow modes, dimension layers, and failure highlighting |
| 3D/2D/calculation consistency | Bolt centers, holes, member/component positions, material orientations, reference points, and result identifiers agree across canonical input, calculations, 3D, 2D, dimensions, and reports |
| Report snapshot tests | Summary and Detailed reports use the same immutable calculation snapshot and preserve basis, versions, status, warnings, assumptions, and stale state |
| Security and project-isolation tests | Server-side ownership, role, entitlement, project, report, object-storage, and audit enforcement, including hostile client-supplied owner identifiers |
| Qualified engineering review | Review of source mapping, applicability, independent evidence, discrepancy disposition, limitations, open risks, user communication, and commercial scope |
| Release freeze | Versioned and hashed evidence package tied to the released code, schema, rule set, source edition/errata, and datasets |

## Test-case and evidence controls

Each controlled engineering case must identify:

- case ID, capability ID, author, independent reviewer, revision, and approval state;
- source IDs and locator references, edition, verified errata set, and engineering-rule-set version;
- canonical input and unit declarations, including member directions, coordinate frames, force reference points, and signed actions;
- applicability expectation and the reason the case is in scope, out of scope, invalid, incomplete, or review-required;
- independently established expected status, intermediate evidence, and comparison tolerance where appropriate;
- expected warnings, assumptions, and result-level identifiers;
- fixture and artifact provenance, including whether any manufacturer or qualification data is restricted; and
- discrepancy history and final disposition.

Licensed source text, figures, tables, or equations are not copied into ordinary fixtures. Access-restricted evidence is referenced through controlled metadata and handled under its license and repository policy.

## Result-state testing

Future suites must demonstrate that PASS and FAIL are emitted only by approved, complete checks. They must also exercise INVALID GEOMETRY, NOT APPLICABLE, NOT COVERED BY SELECTED CODE, ENGINEERING REVIEW REQUIRED, CALCULATION NOT SUPPORTED, INCOMPLETE INPUT, and STALE RESULTS. Missing resistance data for an unsupported or incomplete check must remain absent and cannot be converted to zero or PASS.

## Discrepancy and regression handling

1. Quarantine the affected capability from approval or release.
2. Record the discrepancy against the exact case, source/rule-set version, input fingerprint, and implementation version.
3. Determine whether the source mapping, applicability definition, independent calculation, implementation, units, data, or expected result is at fault.
4. Correct through controlled review; never alter expected evidence merely to match production output.
5. Rerun the affected case, related boundary/property cases, integration snapshots, and an impact-based regression set.
6. Obtain renewed approvals for every invalidated gate and retain the audit history.

## Stage 0.2.4 integrated software-foundation gate

Stage 0.2.4 adds a software QA gate around the existing nonengineering backend and
frontend foundations. From the repository root, the controlling local command is:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-all.ps1
```

The local gate validates the handoff JSON, performs the complete backend and frontend
bootstrap/check sequences, runs both npm audits, checks repository whitespace, and
requires an empty Git index. The initial GitHub Actions workflow repeats backend and
frontend validation independently on Linux and Windows for pushes to `main`, pull
requests targeting `main`, and manual dispatch.

The workflow has read-only repository-content permission and uses no repository secret,
artifact upload, publication, release, or deployment. A platform or lock failure is
reported visibly; hash, binary-only, exact-runtime, and `npm ci` controls are not
weakened to make a job pass.

This gate validates only the existing executable software shells and their dependency,
format, lint, type, test, coverage, build, audit, and repository controls. It does not
complete G0 through G8 for any calculation family, does not validate engineering
mathematics, and does not authorize a calculation result or commercial use.

## Stage 1.1 domain-contract gate

Stage 1.1 extends the software gate to the framework-independent joint-assembly data
contracts. Automated tests cover exact controlled vocabularies, immutable tuple and
vector behavior, finite numeric values, unit-system identity, frame and reference-point
ownership, pultruded-FRP material-axis declarations, direct and shared-connector
interfaces, bolt-group references, complete manual actions, duplicate and unresolved
IDs, design-category rules, stable issue ordering, and `require_valid()` failure.

The recursive architecture test also prohibits HTTPX in the engineering-core boundary
in addition to the existing web, validation, persistence, migration, and outer-layer
imports. The backend gate retains 100% statement and branch coverage for executable
source.

This is G0/G3-oriented software contract evidence only. Expected outcomes are contract
validity issues, never calculated PASS/FAIL results. It supplies no independent
engineering expected value, source-derived rule, applicability decision, geometry,
transformation, resistance, force distribution, equilibrium method, or qualified
engineering approval and therefore completes no calculation-family gate.

## Current Stage 0.1 status

- G0 is being established by controlled product, architecture, engineering, risk, and QA documents.
- G1 through G8 have not been completed for any calculation family.
- The four roadmap slices are Not currently supported, Not started, and Pending engineer approval.
- Automated software-shell and Stage 1.1 domain-contract tests are present; no
  calculation test or calculated engineering result is claimed.
- Documentation review, repository validation, and JSON parsing performed for Stage 0.1 are repository checks, not engineering validation.
- Stage 0.2.4 integrated software-foundation QA is implemented and its first hosted
  four-job run succeeded; Stage 1.1 local domain-contract QA is implemented, its new
  hosted run remains pending, and no calculation family is validated.

## Stage 2.1A contract and fixture validation

Stage 2.1A adds software tests for all 150 required contract/applicability categories:
dual-unit quantities and exact conversion, published-source and authoritative physical
holes, immutable source/material/fastener snapshots, demand contracts, C3
geometry-to-code mapping, geometry prerequisites, applicability/readiness, separate
availability/comparison dimensions, aggregate precedence, fingerprint determinism and
exclusions, RC2 golden-fixture integrity, and architecture/scope exclusions.

The golden JSON is test-only, duplicate-key checked, recursively frozen, and parsed from
decimal strings without mutation. Future numerical expected values are preserved but
not evaluated. Synthetic supplied `PASS`/`FAIL` states exercise schema/precedence only;
no physical input is converted into a numerical comparison.

Required release evidence remains: complete backend and integrated gates; 100% backend
statement and branch coverage; unchanged frontend gate and coverage; JSON validation;
diff/hygiene/source-concordance review; no PDF or private source payload; and no
dependency or lock change. Passing these software gates does not validate a calculation
family, ICE material qualification, the locked F593 preset, or the J1 whole connection.

## Stage 2.1B numerical-engine validation

Stage 2.1B adds direct equation and branch tests for bolt area, thread multipliers,
pure/combined bolt checks, pull-through branch A/B/ties, directional bearing and layer
threads, every net-tension coefficient and theta branch, shear-out, and cleavage
boundary/design-level selection. Factor tests prove end-use, time, geometry, and lap
factors are applied exactly once and do not leak into excluded checks.

Numerical tests independently calculate and compare every RC2 recorded value for P1,
PT1, P2A, P2B, J1-T, J1-C, and B1 using 12-decimal `ROUND_HALF_EVEN` oracles without
production access to expected data. The exact 90-degree case verifies transverse
property consumption. Every golden case is independently recalculated after exact
physical conversion to SI and compared unrounded. Boundary, fail-closed, aggregate,
immutability, monotonicity, layer-order, bolt-axis provenance, framework-independence,
and prohibited-scope tests complete the matrix. Golden discrepancies stop staging;
expected values are never edited merely to make implementation pass.

## Stage 2.2A orchestration validation

The application suite covers immutable request/response records; deterministic repeat
execution; exact assembly/context and target identity; interface, group, location,
path, and layer order; explicit material/fastener assignment; ICE, locked F593, and
synthetic `Fnt`; load combination and time/end-use traces; explicit demand execution;
undistributed actions and conflict rejection; no equal sharing, automatic moment
shift, prying, or return-element credit; geometry mapping; P1/PT1/P2A/P2B/J1-T/J1-C/
B1; 90-degree direction; US/SI equivalence; thread-bearing versus thread-shear-plane
independence; invalid/curved/multi-plane fail-closed paths; status, governing,
fingerprint, ordering, and no-mutation behavior; Stage 2.1B numerical regression; and
framework/API/persistence/report/equation-duplication boundaries. Complete backend and
integrated gates remain mandatory with 100% statement and branch coverage.

## Stage 2.2B API validation

The API suite covers the strict request DTO graph; forbidden extra fields; decimal-
string and explicit-unit transport; rejection of floats, Boolean values, NaN, and
infinity; trusted server identity and spoof-field absence; canonical domain, geometry,
material, fastener, action, and demand reconstruction; exactly one orchestration call;
deterministic response projection; HTTP 200 engineering outcomes versus HTTP 422
transport/mapping errors; P1, P2B, J1-T, J1-C, B1, locked F593, no-distribution,
U.S./SI, and exact 90-degree cases; immutable requests; safe error detail; and
OpenAPI, route-count, security, and direct-equation-call audits.

Stage 2.1B regression and Stage 2.2A orchestration equivalence remain mandatory.
Golden data are not imported by production or altered, and complete backend and
integrated gates must retain 100% statement and branch coverage. API verification
does not establish frontend behavior, persistence, report output, automatic demand
distribution, broader equation coverage, or commercial engineering validation.

## Stage 2.3 workspace and visualization validation

Backend validation covers immutable deterministic visualization snapshots; exact
rectangular and annular physical primitives; bounded support and planar zone geometry;
global/local/interface/bolt frames and inspection; planar material axes and explicit
not-applicable cases; connection zones; bolt/round-hole stacks; START/END/action
reference points; positive, negative, zero, tension, and compression action display;
member-end no-distribution behavior; U.S./SI equivalence; deterministic API transport;
and preservation of existing status, result, and fingerprint authority.

Frontend validation covers the typed same-origin client; input-only J1 profiles;
case-level units; every supported input and demand mode; loading, stale, transport,
known-failure, review, qualification, unsupported, and source-pending presentation;
summary/table/trace; pure scene-model mapping; 3D/Front/Top/Side views; camera reset;
axes/reference/action toggles and inspectors; accessibility; responsive/reduced-motion
structure; no expected result, engineering formula, browser persistence, production
host, or unsupported category. WebGL is mocked at the test boundary; the adapter is
separately linted, type-checked, and production-built.

Complete backend and frontend suites must retain 100% statement/line and branch
coverage (and 100% frontend function coverage), strict mypy, Ruff, ESLint, TypeScript,
build, dependency/lock consistency, zero npm audit vulnerabilities, golden integrity,
scope audits, hygiene review, and a real-browser loopback smoke when available.

## Stage 2.3R refinement validation

Stage 2.3R adds regression checks for a proper rotation determinant, vertical W
column with START below END, diagonal brace placement, preserved 45-degree material
relationship, U.S./SI Q12 result equivalence, unchanged governing W-flange net
tension and qualification, role-based solids, clean default overlays, solid/X-ray
and camera controls, unit-independent fit, connection-first/sidebar/results layout,
friendly labels with stable IDs, presentation-only number formatting, demand-mode
clarity, and absence of copied competitor assets or unsupported scope.

The backend suite passes 1,052 tests with 100% statement and branch coverage over
6,243 statements and 2,076 branches. The frontend passes 55 tests at 100% statement,
branch, function, and line coverage over 417 statements, 271 branches, 183 functions,
and 310 lines. Desktop and narrow-width browser acceptance passed for the U.S./SI
benchmarks, all four views, fit/reset, solid/X-ray, opt-in overlays, inspectors,
member-end fail-closed behavior, exact-on-focus input precision, and local-only table
overflow. The final browser session had no application error.

## Stage 2.3R2 geometry and portability validation

The Stage 2.3R hosted run failed only Backend / Ubuntu 24.04 because a proper rigid
rotation serialized a mathematically zero W-axis component as approximately
`-1.839226599442302E-17`; the test required the exact string `0`. Backend / Windows
2025 and both frontend jobs passed. The correction compares that derived float using
the established `1E-12` dimensionless mathematical tolerance. Tests prove exact zero
and small positive/negative residue pass, while values outside tolerance fail, and
retain norm, orthogonality, right-handedness, and determinant checks. Production
geometry and serialization are not rounded, normalized, or clamped.

Backend tests cover strict template DTOs; exclusive explicit/template input; 45, 90,
and 5-degree placements; proper frames; fixed connection/bolt/path station; editable
local extents; exact U.S./SI physical equivalence; unchanged J1 Q12 values/statuses;
and washer present/absent branches. Frontend tests cover server-only geometry
authority, angle/extent/length validation and stale behavior, friendly labels, ICE
properties, demand wording, exact-known hardware, and full-extent camera fit. The
cross-platform audit rejects exact assertions for derived binary-float residue while
retaining exact Decimal engineering assertions, portable paths/case, deterministic
ordering, and controlled line endings.

Browser acceptance must exercise J1 U.S. at 45 degrees, edits to 60 and 90 degrees,
changed extents/brace length, the equivalent SI case, all four views plus Fit
Connection, and member-end distribution-unavailable behavior. No ordinary J1 PASS,
ICE qualification, F593 `Fnt`, or frontend engineering formula may appear.

The completed local Stage 2.3R2 suites pass 1,069 backend tests at 100% statement and
branch coverage over 6,333 statements and 2,094 branches, and 58 frontend tests at
100% statement, branch, function, and line coverage over 451 statements, 296
branches, 196 functions, and 337 lines. Real-browser acceptance passes all required
U.S., SI, 60-degree, 90-degree, changed-extent, view/fit, material-inspector, and
member-end fail-closed cases. The required governing/qualification/source/review
boundaries remain visible.

Hosted Stage 2.3R2 commit `a28f83c2f124c3dcd994de250a1de962ef8ff72f`
failed only Backend / Ubuntu 24.04 after 1 minute 58 seconds. Exactly one of 1,069
backend tests failed: the default J1 template test required exact strings for a
derived dimensional bolt-center point. Backend / Windows 2025 and both frontend jobs
passed; no artifacts were shown. This is a test portability defect, not an engineering
geometry change.

The correction adds one platform-neutral test for the supplied Windows-style and
Ubuntu-style coordinate strings and a materially shifted failure case. It requires
exact `x`/`y`/`z`/`unit` structure and exact units, parses finite coordinate strings,
and bounds differences by `16 * sys.float_info.epsilon` times the point scale. The
bound is test-only IEEE-754 serialization roundoff, not a dimensional engineering or
fabrication tolerance. Derived directions retain the existing `1E-12` dimensionless
comparison. The corrected backend suite has 1,070 passing tests with unchanged 100%
statement/branch coverage over 6,333 statements and 2,094 branches; production
geometry, serialization, equations, goldens, qualification, extents, angle behavior,
and UI remain unchanged. The user verified correction commit
`c2114fbb2b4c3c99568669407b97aa1b944cd75b` with all four hosted jobs green in
1 minute 54 seconds and no artifacts.

## Stage 2.3R3 orientation, interference, and visualization matrix

The complete backend gate covers exact exterior and web-side flange-strip mapping,
Leg 1/Leg 2 material identity, both outstanding-side clockings, proper frames at 45,
60, and 90 degrees, valid exterior and web-side paths through exactly angle leg plus
W flange, and invalid positive-volume angle/W interference. Invalid cases must return
`INVALID_GEOMETRY` before resistance and contain no plan, result, governing check, or
fingerprint. U.S./SI cases must preserve the same semantics and physical result set.

Frontend tests cover strict orientation controls, stale-result behavior for all three
engineering geometry changes, no stale transition for presentation-only selection or
overlay changes, stable ID display, contact highlighting, model/sidebar selection,
corner versus full global axes, selected-member local axes, material labels, legend,
and clean defaults. Browser acceptance covers default exterior, valid web-side,
invalid interference, Leg 2, axes/legend/orbit/views/fit, 60/90 degrees, SI, narrow
viewport, and solid/X-ray behavior. These tests are bounded software and engineering
regression evidence; they do not constitute general connection validation.

Local R3 evidence passes 1,081 backend tests at configured 100% statement and branch
coverage and 62 frontend tests at 100% statement, branch, function, and line coverage
over 487 statements, 326 branches, 213 functions, and 362 lines. Real-browser
acceptance passed the listed default exterior, web-side, invalid interference, Leg 2,
45/60/90-degree, SI, view/fit, solid/X-ray, axis/legend/default-overlay,
model/sidebar-selection, contact-picking, and 800-pixel responsive cases.

## Stage 2.3R4 viewport-interaction validation

The pre-correction browser reproduction must cover Fit Connection and left-drag over
both empty and selectable canvas areas. The confirmed failure mode was a controls
change listener writing projected camera orientation into React state on every camera
change, combined with selectable geometry stopping the pointer at pointer-down. The
first behavior rerendered the visualization/Canvas during navigation and could freeze
the tab; the second prevented navigation starting over model geometry. Static overlay
pointer interception is audited independently.

Automated R4 tests require exactly one controls construction site, explicit left-
rotate/right-pan/wheel mappings, one listener with idempotent cleanup, direct triad SVG
updates without a React camera-orientation state or frame loop, four-pixel click/drag
classification, retained W/angle/bolt/contact picking, and twenty repeated cycles of
3D/Front/Top/Side, Fit, Reset, overlay changes, and selection. Those cycles must leave
the initial calculation request count unchanged and the current result non-stale.

Real-browser acceptance requires at least 60 continuous seconds of rotate/pan/zoom
interaction, including rapid reversal, dragging over selectable geometry, repeated
view/Fit/Reset operations, overlay toggling, post-navigation picking, and console/tab
responsiveness. Automated browser evidence completed 60.471 seconds of left-drag and
wheel interaction without a freeze, retained the current qualified result, updated
the fixed-corner triad orientation, selected every R3 target type after navigation,
and emitted no warning/error console records. The in-app browser automation exposes
only left-button dragging, so right-drag pan remains an explicit user acceptance step.
No browser acceptance result broadens the controlled engineering scope.

The completed R4 local gates pass 1,081 backend tests at configured 100% statement and
branch coverage over 6,467 statements and 2,116 branches. They pass 67 frontend tests
at 100% statement, branch, function, and line coverage over 539 statements, 336
branches, 225 functions, and 412 lines. Ruff format/lint, strict mypy, ESLint, strict
TypeScript, production build, dependency resolution, both zero-vulnerability audits,
manifest/whitespace checks, and the integrated gate pass. The RC2 fixture hash remains
`39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392`.

## Stage 2.3R5 preview/workflow validation

Backend tests prove that preview uses the canonical geometry/action resolver, returns
valid, invalid, incomplete, and unsupported engineering states over HTTP 200, keeps
transport failures at HTTP 422, reports design readiness independently, and exposes
no resistance plan, equation result, utilization, governing check, fingerprint, or
design PASS/FAIL. Default J1, web-side, 60-degree, 90-degree, 5-degree, member extent,
bolt geometry, signed load, material direction, contact/path, and interference cases
are required. Static source audits prohibit the Stage 2.1B evaluator/equations from
the preview service.

Frontend tests cover initial/live preview, 200 ms numeric debounce, immediate discrete
edits, abort, latest-response-wins, model revision, silent abort handling, retryable
network failure, invalid local fields, invalid design blocking, stale retained design
results, design-response obsolescence, and all three input classifications. They also
prove orbit, pan, zoom, views, Fit/Reset, overlays, selection, and case-label edits do
not request preview, and only `Run Design Check` requests design results.

Real-browser acceptance must cover default preview before design, invalid and valid
orientation/interference, 60/90-degree and load-arrow updates, a rapid-edit race, and
the R4 navigation stress without unexpected preview/design calls, stale-state loss,
console errors, or a freeze. The unchanged RC2 golden hash, J1 outcomes, dependencies,
and 100% backend/frontend configured coverage remain release gates. Hosted R5 CI is
pending until direct post-push evidence exists.

Automated browser evidence passed the U.S. and SI initial previews, valid web-side,
45-degree invalid interference, 5/60/90-degree updates, signed `FX = -1.2 kip`
action inspection, old-result staleness/retention, invalid design blocking, rapid-edit
latest-wins, and explicit design-only submission. A controlled discrete orientation
edit produced one preview, a typed angle produced one preview after debounce, and an
explicit design action produced one design call. During 62.711 seconds of active
left-drag orbit/wheel zoom plus thirty view/Fit/Reset operations and presentation
changes, server counts remained `preview=16, design=2`, the tab stayed responsive,
and the current result did not become stale. No console error was observed; Three.js
emitted its existing development-only `THREE.Clock` deprecation warning. The browser
automation cannot synthesize right-button drag, so right-pan remains an explicit user
acceptance item while the automated R4 mapping/gesture tests remain green.

## Stage 2.3R6 validation plan

Backend regression covers J1 brace views 4/5/8/12 inches and exact SI equivalents,
proving invariant connected end, bolt center, contact, path, mapped `e1`, capacities,
governing identity, and fingerprint. Separate 2.0/2.5-inch `e1` cases prove canonical
end movement, mapper re-derivation, permitted result changes, and fingerprint change.
Directed 5/45/60/90/120/135/150/175-degree cases prove proper frames, preserved
topology/interference, and server material relationships. Applied force/moment tests
cover sign reversal, zero, U.S./SI units, and zero resistance output from preview.

Frontend regression covers input classification, 120/150/175 display, view-only
preview without staleness/design calls, shared sidebar/label load state, signed and
zero formatting, Enter/Escape/blur/invalid behavior, pointer isolation, camera fit,
latest-response-wins, and explicit design. The formerly timed-out stress test caches
DOM controls and uses four semantic cycles rather than twenty redundant cycles while
retaining every view/Fit/Reset/overlay/selection and no-request/no-stale assertion;
no timeout was increased. Real-browser acceptance remains required for the complete
A-K matrix, including manual right-button pan where automation cannot synthesize it.

Execution evidence: the complete A-K automated portion passed. View lengths
4/5/8/12 inches remained valid with `e1 = 2`, the current 0.972 default result, and no
staleness; changing `e1` to 2.5 staled design and changed the intended server-derived
angle-member results only after `Run Design Check`. Directed 120/150/175-degree
previews reported 60/30/5-degree material relationships. Force `+0.700` to `-1.200`,
moment sign change, zero action, sidebar synchronization, U.S./SI units, and explicit
design refresh passed. A 73.909-second navigation pass performed 48 orbit, zoom,
view, Fit, and Reset actions without a freeze, API call, or stale result. Automated
right-drag remains unavailable and is the only manual browser acceptance item.

## Stage 2.3R7 action-label validation plan

Frontend regression must prove projected labels for all six applied components,
positive and negative signed formatting, U.S./SI force and moment units, force versus
moment identity, applied/value/zero visibility coupling, and separate nonnumeric,
noneditable positive-convention symbols. Pure projection tests cover points along the
rendered shaft/arc, deterministic component offsets, screen projection, camera-change
coordinates, and off-camera visibility. DOM tests prohibit the former detached corner
list and verify that each label retains its component and source identity.

Interaction regression covers force and moment label editing, shared sidebar state,
Enter/Escape/blur/invalid behavior, preview scheduling, latest-response-wins, stale
design, and the absence of automatic design calls. R4 view/Fit/Reset, orbit/pan/zoom,
selection, pointer isolation, listener cleanup, and no-request/no-stale tests remain
required, as do R5 preview/design separation, R6 `e1`/view-extent/directed-angle
behavior, R3 orientation/interference, full backend regression, the unchanged RC2
golden hash, dependency/lock validation, production build, and configured 100%
frontend coverage. Browser acceptance covers J1 U.S./SI labels, camera tracking,
force/moment edits, visibility, and positive conventions; right-button pan remains a
manual item only if the available automation cannot synthesize it.

Execution evidence: the complete backend, frontend, and integrated gates passed with
1,162 backend and 119 frontend tests at configured 100% coverage. Dependency-tree,
lint, strict typing, production build, JSON, whitespace, and both npm audit scopes
passed. U.S. and SI browser cases showed force and moment values beside their own
primitives; 3D/Front/Top/Side, Fit, Reset, orbit, and zoom changed their projected
coordinates while navigation issued no design request. Editing Fx and Mz updated the
same sidebar state, scheduled preview, staled the retained result, and did not run
design. Applied values hid with their overlay, positive conventions stayed
nonnumeric/noneditable, and the detached primary card list was absent. Unit-scaled
camera clipping corrected SI presentation without changing production geometry.
Automated right-button pan remains unavailable and therefore pending manual review.

## Stage 2.3F frozen-baseline regression plan

The accepted Stage 2.3 interface and geometry baseline is implementation commit
`5bc545ab8251f9bd49dedc776962937ed5e822a2`, preserved by annotated tag
`stage-2.3-interface-geometry-freeze`. Its hosted R8 run passed 4/4 backend/frontend
Ubuntu 24.04 and Windows 2025 jobs in 2 minutes 23 seconds, with 123 frontend tests on
both hosted platforms and no artifacts. The backend suite baseline remains 1,162 tests
at configured 100% statement and branch coverage, and the RC2 golden SHA-256 remains
`39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392`.

Every future change touching a frozen invariant must identify the affected invariant,
compare old and proposed behavior, analyze compatibility, and define focused plus
full regression against this tag. Required regression continues to include backend,
frontend, integrated, dependency/lock, audit, JSON, whitespace, U.S./SI, preview-zero-
resistance, explicit-design, geometry/view-extent, directed-angle/material,
orientation/interference/bolt-path, axes, action-label/editing, viewport navigation,
qualification, fingerprint, and golden checks as applicable. Compatible extensions
must prove the frozen behavior remains available and unchanged. The tag is never
moved to a later implementation or documentation commit.

## Stage 2.4A multi-row planning validation

Stage 2.4A validation covers arbitrary positive bolt/row counts; deterministic
force-relative row and line resolution under input permutation; rectangular and
nonrectangular classifications; exact two-/three-row prescribed fractions;
conservative full-row and attributed engineer-defined scenarios; first-row and
inter-row mappings; L/U accepted and rejected physical paths; half-hole accounting;
U.S./SI hole additions; raw net-area invalid/warning behavior; source conflict;
more-than-three-row qualification; unsupported branches; status precedence; and
deterministic fingerprints.

Scope audits require zero new numerical resistance execution, zero fixture use in
production, zero framework/file/network/time/random dependencies in pure mapping,
unchanged RC2 fixture/hash and Stage 2.1B/2.2A/2.2B regression, no API-route change,
no frozen frontend production change, and no freeze-tag mutation. New production
modules require 100 percent statement and branch coverage. Complete backend,
frontend, integrated, JSON, whitespace, dependency/lock, production-build, and npm
audit gates are required before commit; hosted status remains pending until direct
evidence exists.

## Stage 2.4A-R1 correction validation

Reconcile feature commit `b7411ef8da08bb7134bd7f83e729cfc3a90f77d8` as a hosted
failure: both backend jobs failed the raw-byte Stage 2.3 frontend freeze audit with 1
failed/1,239 passed and 100 percent coverage; both 123-test frontend jobs passed; no
artifacts were shown. The correction must compare the frozen source tree and package
blobs as Git objects and separately prove failure for a changed, added, deleted, or
renamed source and either package-file change. Separator/order variants must compare
equal, and any checkout-byte read must make the focused test fail.

The four production prescribed sequences must be obtained by canonical material-pair
identity and compared directly with the unchanged Slice 2 golden. A nonsymmetric
FRP/steel three-row plan must prove Row 1 receives 0.50, Row 2 receives 0.30, and Row
3 receives 0.20 in order from farthest to nearest the unloaded free end. Repository
search must find no inaccurate generic prescribed distribution.

Acceptance requires the complete backend/frontend/integrated gates, 100 percent
configured coverage, strict typing/lint/build, clean locked install, both zero-
vulnerability audits, all three controlled hashes, unchanged frontend/API/dependency
trees and freeze tag, clean explicit staging, and no resistance execution. Hosted R1
remains pending until directly verified.

## Stage 2.4B multi-row numerical validation

Stage 2.4B validation treats RC1 as the preserved planning/regression authority and
the exact approved RC2 specification, golden benchmark, and independent ledger as the
numerical authority. Production code must not import, open, parse, or otherwise use a
golden fixture. Tests compare production results to independent expected values and
never change an approved value to match implementation.

Golden-driven coverage includes inherited RC1 cases; every RC2 equation, domain/status,
integration, tie/ordering, and metamorphic case; asymmetric `e1`; Appendix branch and
coefficient matrices; reduced/nonuniform pitch; exact endpoint and lower-envelope ties;
Equations 8-12, 8-13, 8-14a, and 8-14b; eccentricity tolerance; raw net-area warnings;
multi-layer independence; unequal/staggered external plans; source exemptions;
missing demand; zero/negative resistance; qualification/failure precedence; and
deterministic result order.

Direct architecture tests require one calculation-layer entry point, frozen/slotted
contracts, deep immutable nested payloads, finite Decimal-only physical authority,
complete block-plan carriage, exact version identities, and canonical fingerprints.
Cross-platform evidence covers path syntax, line endings, mapping/set enumeration,
display units, stable source-unit hole origin, repeated execution, and approved force-
reversal differences. Scope audits require zero application/API/frontend/dependency/
lock/freeze-tag changes and preserve every Slice 1 result and version.

Acceptance requires all focused and complete backend gates with 100 percent statement
and branch coverage; Ruff; strict mypy; frontend lint/type/test/build with configured
100 percent coverage; clean locked install and dependency tree; full/runtime npm audits
with zero vulnerabilities; integrated QA; exact controlled hashes; JSON/whitespace
checks; and explicit staged-diff review. Local success never implies hosted success.

Stage 2.4B implementation commit pushed; local verification passed; hosted CI pending
user verification.

## Stage 2.4C end-to-end multi-row validation

Application tests cover prescribed FRP/FRP and FRP/steel two/three-row cases,
more-than-three-row qualification, conservative and both engineer-defined methods,
one/two/three and more-than-three bolts per row, distinct end distances, signed-force
row reversal, longitudinal/transverse mapping, independent layers, lap and reduced
pitch factors, concentric/eccentric block shear, explicit/missing tension, zero demand,
invalid geometry and identities, below-75-percent raw net area, known failure with
qualification, nonempty required checks, deterministic fingerprints, display-unit
equivalence, and zero production golden access.

Preview tests patch the engine boundary and prove no resistance call or result fields,
deterministic snapshot/fingerprint behavior, invalid-geometry failure, and qualification
visibility. Design tests prove one engine call and unchanged complete result meaning.
API tests cover strict Decimal/unit DTOs, Boolean/extra/internal field rejection, trusted
identity, exact routes/OpenAPI, deterministic serialization, engineering HTTP 200 versus
transport 422, and the API-to-application dependency boundary.

Frontend tests retain every Stage 2.3 regression and cover the unified default/arrangement routing,
debounce, abort/latest-response-wins, explicit design, stale results, local/server
invalid state, row methods/provenance, optional tension, presentation-only units,
backend-authoritative same-scene physical bolts/holes/axes/paths, bolt selection,
detailed trace, accessibility, and transport errors. They assert that no separate
multi-row workspace or primary replacement viewer remains. Configured statement,
branch, function, and line coverage remains 100 percent.

Freeze tests compare the authoritative staged source tree before commit and
`HEAD:frontend/src` after commit against the registered R3 active successor. The
hosted-green but visually rejected interim tree and historical R1/R2 predecessors are
explicitly rejected as current active identities. Mutation
coverage includes change/add/delete/rename/arbitrary trees plus package/lock mutation;
separator, line-ending, enumeration, checkout-location, and depth-1 safety are retained.

Acceptance requires complete backend/frontend/integrated gates, exact controlled
hashes, zero vulnerabilities, isolated depth-1 committed-state verification, normal
push, hosted four-job success, and user visual review. Local success does not establish
hosted or formal Stage 2.4C acceptance.

Stage 2.4C-R1 local validation passes 1,374 backend tests at 100 percent statement and
branch coverage over 9,712 statements and 3,116 branches, plus 167 frontend tests at
100 percent configured statement, branch, function, and line coverage. Required
clean-`HEAD` and object-isolated depth-one clone verification remain post-commit gates;
hosted CI and user post-push visual acceptance remain external gates.

The exact R1 commit subsequently passed all four hosted Ubuntu/Windows
backend/frontend jobs in 2 minutes 54 seconds with 167 frontend tests. R2 adds focused
checks that bolt and hole radii independently equal half
their canonical backend diameters, that every multi-row fastener uses the same rule,
and that no perspective/orthographic camera preset scales engineering geometry. Side 1
and Side 2 must be exact opposing orthographic directions with the same target and up
vector. Navigation tests must prove view switching performs no API request and does not
stale a completed design result.

Real-browser R2 review must cover 1-by-1 and 2-by-2 diameter changes in all five views,
the physical 2D diagnostic, independent hole diameter, opposite-side appearance,
selection, Fit, Reset, and fresh-console behavior. Complete local gates, staged-tree
identity, exact controlled hashes, object-isolated depth-one verification, hosted CI,
and user post-push visual acceptance remain separate evidence points.

R3 adds semantic tests for capped/non-wireframe shanks, the exact frontend-only
head/nut ratios, authoritative washer faces/dimensions, absent-washer stack-end
fallbacks, zero-length-axis fail-closed behavior, and common 1 × 1/2 × 1/2 × 2/larger
assembly mapping. Scope audits prohibit those presentation ratios from backend/API
engineering contracts. Browser review covers solid hardware, selection, all five views,
0.500-to-0.750 diameter scaling, opposing sides, U.S./SI preview, explicit design-result
persistence, and repeated View/Fit/Reset with zero navigation-triggered API calls.
Freeze tests register active tree `deb93d01646580ae62c9f90a507446d84019bd87`
and reject the R2 predecessor as current while preserving all earlier provenance.

The final staged-tree component gates pass 1,378 backend tests at 100 percent statement
and branch coverage over 9,715 statements and 3,116 branches, plus 178 frontend tests
at 100 percent configured coverage over 1,162 statements, 917 branches, 391 functions,
and 972 lines. Ruff, strict mypy, ESLint, strict TypeScript, production build, clean
install, dependency tree, and both zero-vulnerability audits pass. Exact
RC1/RC2/Slice 1 hashes, package/lock identities, and the original freeze tag remain
unchanged. The clean-index integrated gate and object-isolated clone are verified only
against the committed state.

## Stage 2.5A eccentric demand-engine validation

Validation loads every owner-approved Slice 3 RC1 golden case and independently
compares centroid, geometric polar coordinate sum, force-line moment,
direct-distribution moment, residual moment, every per-bolt direct/moment/total vector,
magnitude, and both equilibrium totals at 12-decimal `ROUND_HALF_EVEN` serialization.
The U.S./SI case must produce the same canonical physical results and fingerprints.

Focused engineering tests cover global-to-interface projection, physical reference
transfer, translated and rotated frames, concentric and eccentric force, nonzero direct
distribution moment, force reversal, increasing eccentricity, linear moment response,
single-bolt degeneracy, pure moment, retained member-end moments, interface-normal
force, all three inherited direct-demand bases, multiple conservative scenarios, and
engineer-defined provenance. Deliberate force and moment tampering must fail the named
equilibrium tolerance without clamping, normalization, rounding, or redistribution.

Architecture tests enforce a pure calculation-layer entry point, zero production
golden access, zero resistance call/handoff, and zero API/application/frontend
integration. Source scans prohibit resistance equations, file/network/time/random
authority, friction, prying, and implicit bolt-axis tension. Complete backend statement
and branch coverage remains 100 percent; the unchanged frontend must retain configured
100 percent coverage, strict lint/type/build, dependency-tree integrity, and both
zero-vulnerability audits. Exact Slice 1/Slice 2 hashes, the Stage 2.3 freeze identity,
frontend tree, package blob, and secure lock identities must remain unchanged.

## Stage 2.5B resistance-handoff validation

Validation verifies the byte-exact RC1 specification, golden, and independent ledger;
all eight handoff cases and four status cases; exact concentric legacy equivalence;
actual Stage 2.5A total-vector authority; zero-demand behavior; per-bolt/per-layer
direction selection at 0, 5, just-over-5, and 90 degrees; supported shear, bearing,
combined, and pull-through reuse; and conditional block-shear compatibility.

Fail-closed tests retain eccentric first-row and inter-row required checks, prohibit
ordinary PASS for incomplete action transfer, preserve known supported FAIL, and prove
that axis tension is explicit and consumed rather than derived. Metamorphic checks
cover deterministic repeatability, parent immutability, display-unit exclusion,
fingerprint sensitivity to parent/compatibility changes, multilayer direction changes,
and scoped monotonic demand behavior.

Architecture gates require zero production golden/file/network/database/time/random
access and zero API/application/frontend/dependency/workflow change. Full backend and
unchanged frontend gates, both npm audits, exact parent hashes, frozen source identities,
clean-index integration, isolated committed-state verification, normal push, and
hosted Ubuntu/Windows results remain separate mandatory evidence.

Measured final local evidence is 26 focused handoff tests and 1,433 complete backend
tests over 10,618 statements and 3,374 branches at 100 percent coverage. The unchanged
frontend regression remains 178 tests with 1,162 statements, 917 branches, 391
functions, and 972 lines at 100 percent coverage; lint, strict typing, build, and both
npm audits passed. This local evidence does not imply isolated-clone or hosted success.

## Stage 2.5C automatic-demand integration validation

Application tests cover explicit/default and automatic sources, canonical action and
reference resolution, one Stage 2.5A invocation per scenario, exact Stage 2.5A result
handoff into Stage 2.5B, zero direct eccentric Stage 2.4B orchestration, zero preview
resistance, full-legacy equivalence, partial-eccentric fail-closed behavior, supported
FAIL precedence, retained member moments, and explicit-only axis demand. API tests
cover strict enums and mutually exclusive source fields, missing/invalid actions,
decimal transport, extra/internal-field rejection, deterministic U.S./SI output, and
distinct failure/unsupported/incomplete serialization.

Frontend tests protect the backward-compatible explicit default, one shared member
action state, preview/debounce/abort/latest-response behavior, stale results after
engineering edits, explicit **Run Design Check**, automatic status presentation, and
the optional backend-authored per-bolt overlay. Source-boundary tests prohibit frontend
vector mechanics and permit Stage 2.5A/2.5B calls only from the application integration
module. The final local component suites pass 1,448 backend tests over 10,842 statements
and 3,452 branches and 181 frontend tests over 1,182 statements, 972 branches, 402
functions, and 990 lines, all at 100 percent configured coverage.

Freeze validation registers active tree
`035af7c9c44c49914c63c68edf6ec4eea5521bcf`, preserves every historical identity,
and retains strict mutation and cross-platform checks. Full scripts, build, locked
dependency install/tree, both audits, controlled hashes, isolated committed-state
verification, hosted CI, and user post-push visual acceptance remain separate gates.

## Stage 2.5C-R1 collinear determinism validation

The exact automatic group-local collinear fixture must produce zero external moment,
zero direct-distribution moment, zero residual moment, and
`FULL_LEGACY_COLLINEAR` through both application and API paths. The same physical case
must retain identical demand fingerprints under U.S. and SI transport, force reversal,
repeated execution, selected connection-side/basis variants, and deliberately perturbed
platform-float geometry views. The repaired authoritative input path must use Decimal or
exact repository quantity types and must not depend on OS math stringification, locale,
filesystem order, or native paths.

Positive and negative member-reference eccentricities and a deliberately real
`1E-12 in` reference offset must remain nonzero and `PARTIAL_ECCENTRIC`; no residual
tolerance, clamp, rounding, or Stage 2.5B label relaxation is permitted. All Stage 2.4B,
Stage 2.5A, and Stage 2.5B authority hashes and numerical regressions, the explicit-demand
path, complete backend/frontend gates, audits, active frontend/package/lock identities,
and immutable Stage 2.3 tag remain mandatory. Local, isolated committed-state, pushed,
and hosted Ubuntu/Windows evidence are recorded independently.

## Stage 2.6A eccentric group-mode compatibility validation

Validation loads every owner-approved Eccentric Group Modes RC1 golden case and checks
byte-exact specification, golden, and ledger identities. Tests derive every line from
canonical physical membership and accepted Stage 2.5A total bolt vectors, verify exact
vector sums and parallel/transverse decomposition, and cover zero, positive-parallel,
nonparallel, reversed, and deliberately tiny nonzero transverse components without a
tolerance.

Delegation tests prove unchanged Stage 2.4B Equation 8-12, Equation 8-13, and qualified
more-than-three-row paths, fixed resistance under positive demand scaling, zero-line
not-required behavior, legacy equality at zero residual moment, first-row fail-closed
behavior otherwise, exemption preservation, and supported FAIL precedence. Contract,
immutability, deterministic fingerprint, physical U.S./SI equivalence, invalid parent,
membership, and architecture-isolation tests are mandatory. Full backend/frontend,
static, build, audit, hash, freeze, staged-tree, isolated-clone, pushed, and hosted
outcomes remain separate evidence.

The final local Stage 2.6A gate passes 1,481 backend tests over 11,357 statements and
3,634 branches at 100 percent coverage. The unchanged frontend passes 183 tests at
100 percent configured statement, branch, function, and line coverage. Ruff, strict
mypy, ESLint, strict TypeScript, production build, clean locked install, dependency
tree, both zero-vulnerability audits, JSON, whitespace, hash/freeze, and integrated
gates pass; isolated committed-state and hosted evidence remain separate.

## Stage 2.6B end-to-end integration validation

Application tests must prove exactly one Stage 2.6A call per automatic scenario, exact
Stage 2.5A/2.5B parent identity, no application line reduction or Stage 2.4B bypass,
preview resistance isolation, explicit-path separation, deterministic/unit-invariant
fingerprints, >3-row qualification, zero/parallel/nonparallel/reversed line states,
first-row limitation, legacy equality, and FAIL precedence.

API tests must prove strict request rejection of client-authored internal fields, exact
serialization of line quantities and Stage 2.6A identities, U.S./SI physical identity,
and application-only invocation. Frontend tests must prove the unified workflow and
every required presentation state without frontend line-resultant math, hidden failure,
new stale state, or regression to views, per-bolt overlays, solid fasteners, loaded
boundary, explicit demand, or session-only behavior.

The full local and integrated gates pass 1,501 backend tests over 11,433 statements and 3,664
branches at 100 percent coverage and 185 frontend tests over 1,205 statements, 1,031
branches, 410 functions, and 1,012 lines at 100 percent coverage. Static analysis and
frontend build pass. Clean install/tree, both audits, JSON, whitespace, and the exact
freeze audit pass. Isolated committed, pushed, hosted, and direct visual outcomes
remain separately recorded.

## Stage 3.1 connector and fastener material architecture validation

Focused domain tests in `backend/tests/domain/test_material_architecture.py` must cover
every exact connector/fastener material family, material-behavior family, property
source kind and confirmation state, P/Q/X/R coverage class, resistance-authority kind,
component role, deeply immutable record, strict stable identifier, optional controlled
artifact hash, deterministic canonical representation/fingerprint, and invalid or
mutable nested input. They must prove topology/material separation and that display
labels or ordering accidents cannot become engineering identity.

The no-default-property matrix must prove that choosing `STAINLESS_STEEL_316` or
`CARBON_STEEL` populates no grade, Fnt, shear strength, yield/tensile strength,
resistance factor, coating, toughness, or corrosion classification. Property values
and accepted Stage 2 snapshots remain explicit source-bound engineering data. A
`CUSTOM_FRP` fastener remains physically representable but cannot enter the existing
metallic-bolt path under any authority. It carries
`NO_AUTOMATIC_RESISTANCE_AUTHORITY` for bolt-body strength until a separate custom
method and authority are approved.

Focused calculation tests in
`backend/tests/calculation/test_material_compatibility.py` must prove exactly:

- FRP/FRP resolves to unchanged `FRP_FRP`;
- FRP/316 stainless resolves to unchanged `FRP_STEEL` while retaining
  `STAINLESS_STEEL_316`;
- FRP/carbon steel resolves to unchanged `FRP_STEEL` while retaining
  `CARBON_STEEL`;
- participant order does not erase the exact supported metal subtype;
- steel/steel, unknown/custom, and every unsupported pair reject without fallback; and
- existing metallic-bolt eligibility requires a supported metallic family,
  authoritative geometry, existing metallic authority, exact matching accepted
  snapshot identity, and positive explicit Fnt.

The custom-FRP, missing-authority, missing-geometry, missing/mismatched-snapshot,
missing-Fnt, and nonpositive-Fnt branches must produce named blocked statuses and expose
no eligible snapshot. The adapter must call no resistance equation and production must
read no test fixture.

Regression must preserve every Stage 2.1B, 2.4B, 2.5A, 2.5B, 2.6A, and 2.6B numerical
result, controlled golden/hash, and fingerprint. Architecture tests must enforce the
allowed dependency direction and zero production changes in API, application,
frontend, dependencies/lock, workflows, persistence, reporting, authentication, or
billing. The exact Stage 2.3 freeze tag/tree, active frontend tree, package blob, and
secure-lock identities remain mandatory.

Environmental exposure, coating/protection, galvanic/isolation detail, and corrosion
review are deferred provenance scope. Validation must not treat an absent or future
metadata value as a Stage 3.1 corrosion rule, structural resistance, durability credit,
or automatic compatibility decision.

Measured local evidence is 66 domain plus 21 compatibility tests (87 focused), 1,588
complete backend tests at 100-percent statement/line and branch coverage over 11,914
statements and 3,856 branches, and 185 frontend tests at configured 100-percent coverage
over 1,205 statements, 1,031 branches, 410 functions, and 1,012 lines. Static analysis,
build, clean dependency tree, both zero-vulnerability audits, controlled hashes, JSON,
whitespace, freeze, and integrated QA pass. Clean committed-state isolation, push, and
hosted Ubuntu/Windows outcomes remain separate pending evidence.

## Stage 3.2 reusable Tee vertical-slice validation

Backend tests must prove one shared Tee topology supports column- and beam-flange
placement and both selected physical flanges with exact perpendicular flange/stem
geometry. They must independently vary Interface A and Interface B row/bolt layout and
prove unchanged identity, position, path order, and result for the untouched interface.
Every selected contact surface, bolt center/axis, ordered layer stack, W support solid,
brace solid, and Tee solid must come from the canonical backend assembly.

Application and golden tests must prove exact global-to-interface action/reference
resolution, locally equivalent column/beam demand, unchanged Stage 2.5A demand,
Stage 2.5B handoff, Stage 2.6A compatibility states, and unchanged parent numerical
fingerprints. Nonzero interface-normal action must remain explicit and must create no
automatic bolt-axis tension or prying. Tee-body `NOT_EVALUATED` and other unsupported
required checks prohibit ordinary PASS; supported failure retains whole-assembly FAIL
precedence. The exact material/source trace must show the PULTRUDED_FRP Tee and
existing controlled FRP brace/support path plus STAINLESS_STEEL_316 F593 fasteners
without inferred Fnt; custom FRP must remain outside the metallic path.

API tests must enforce the two strict stateless Tee POST routes, trusted identity,
decimal-string/unit transport, deterministic responses, preview resistance isolation,
and explicit-only design execution. Frontend tests must cover the unified template
switcher, U.S./SI loaders, every required geometry/layout/action input, automatic
debounced/aborted/latest-wins preview, stale-result behavior, explicit design, two
interface result groups, Tee-body/normal warnings, both bolt groups, column/beam views,
selected contact, camera controls, and the unchanged direct-connection template. Scene
tests must prohibit hollow/cage bolts and frontend engineering placement or resistance.

The owner artifacts must remain byte-exact at SHA-256
`802C74CD6FCC76872E3E63DE34C52392111A5C44D495B80919C06616B65E48C2`,
`77FD574FC0EE55F565480E131FCDC3D334B8E7047D75FADC00C96979B31F1313`, and
`2D9324690886BBE39F09827AB5F9BEA465443C47F2905AA3AB5C252333BCF11A`.
Package/lock identities, the immutable Stage 2.3 tag, all Stage 2 controlled hashes,
and new frontend tree `241dc569cb17aef5bd05eba604962607b730411f` are mandatory.

Focused Stage 3.2 backend validation passes 61 tests with 100-percent statement/branch
coverage over the new backend files. Full local and integrated gates pass 1,650 backend
tests at 100-percent coverage over 12,563 statements and 3,974 branches plus 227
frontend tests at configured 100-percent coverage over 1,464 statements, 1,262
branches, 500 functions, and 1,223 lines. Ruff, strict mypy, ESLint, strict TypeScript,
build, clean locked installation/tree, both zero-vulnerability audits, controlled
hashes, JSON, whitespace, and freeze gates pass. Isolated committed verification,
push, and Stage 3.2-R1 hosted Ubuntu/Windows evidence passed; owner V1 review required
the R2 correction and renewed V1-R2 through V5-R2 visual evidence.

## Stage 3.2-R2 unified-workspace and member-profile validation

Domain tests must cover exact immutable member-role, profile-family, family-specific
dimension, material, orientation, selected-surface, and geometry-fingerprint identity.
They must verify every controlled surface ID for angle, channel, wide-flange/I,
rectangular hollow, and flat plate; strict dimension and family/surface validation;
round-hollow direct-contact rejection; deterministic Decimal canonicalization; and no
catalog or strength inference. The byte-exact R2 golden fixture must drive G1 through
G10 and must never be imported by production code.

Application/API tests must prove that explicit `3.2-R2` profile requests resolve real
backend section solids, bounded connection surfaces, actual penetrated elements and
through-thickness layers for Brace to Tee Stem while Tee Flange to Support remains
independent. Tests must retain column/beam local invariance, both support flanges,
independent layouts, global action/reference transformation, interface-normal
fail-closed behavior, Tee-body `NOT_EVALUATED`, parent Stage 2 result/fingerprint
identity, exact material/source trace, and preview zero-resistance behavior. Strict
transport tests must accept either the exact legacy `3.2-RC1` flat-plate shape or the
explicit R2 profile shape, reject mixed/ambiguous inputs and invalid dimensions or
surfaces, preserve route/trusted-identity behavior, and serialize deterministic profile
and resolved-surface trace.

Frontend tests must prove the grouped connection dropdown and absence of the old
button strip; unchanged default direct workflow; Tee use of the shared shell/sidebar,
persistent majority-width desktop viewer, independently scrollable sidebar, and
accessible results; all profile-specific controls and surface filtering; real angle,
channel, W/I, RHS, and explicit plate solids; round-hollow unavailability; shared W
column/beam geometry; dynamic physical title/interface names; independent interface
layouts; solid fastener scaling; one-way result/sidebar highlighting; and unchanged
five-view camera/navigation behavior. Engineering profile edits must abort/stale and
schedule latest preview without automatic design, while camera, highlight, accordion,
scroll, and formatting state must not stale or call an API.

Regression includes all Stage 3.2 G1-G6, every Stage 2 numerical result/golden/
fingerprint, Stage 3.1 architecture/compatibility, direct-workspace behavior, the six
targeted Windows `App.test.tsx` timeouts, package/lock identity, the cross-platform
frontend-tree audit, and the immutable Stage 2.3 tag. Full backend and frontend gates,
configured 100-percent coverage, Ruff, strict mypy, ESLint, TypeScript, production
build, clean dependency tree, both zero-vulnerability audits, exact controlled hashes,
JSON, whitespace, integrated QA, explicit staged diff, and object-isolated depth-one
committed verification are mandatory before normal push. Hosted four-job success and
V1-R2 through V5-R2 remain direct post-push evidence; neither is inferred locally.

Current local execution passes 1,849 backend tests with 13,264/13,264 statements and
4,160/4,160 branches covered, and 247 frontend tests with 1,539/1,539 statements,
1,330/1,330 branches, 530/530 functions, and 1,282/1,282 lines covered. Three
consecutive isolated Windows `App.test.tsx` coverage runs pass all 31 tests while
retaining the six targeted timeouts. Clean committed-state isolation, push, hosted
Ubuntu/Windows results, and V1-R2 through V5-R2 remain pending evidence at this point.

## Stage 3.2-R4 exact-unit geometry and benchmark validation

R4 tests must prove exact Decimal source conversion and coordinate arithmetic before
end-distance comparison/fingerprinting, including `1 + 2 = 3 in` and
`25.4 + 50.8 = 76.2 mm`. They must reject partial exact-source input, retain the exact
validator, prohibit tolerance/epsilon/rounding/clamping, assert execution transition
`7c6d…8bf57` to `40ba…1a69`, assert derived preview transition `673b…68d8d` to
`94de…e9d2`, and freeze the corresponding U.S. execution/preview identities.

Backend/application/API tests must consume the byte-exact R4 golden and prove both
U.S. and SI benchmark loaders resolve a `FLAT_PLATE` brace with `FACE_POS`, exact
equivalent Tee/support/profile/layout/bolt/action data, valid A/B interface geometry,
finite opposing physical faces, ordered penetrated layers, positive containment, and
no exact-geometry warning. Stage 3.2 G1-G6, R2 G1-G10, every Stage 2 golden and
fingerprint, profile-family applicability, direct workflow, Tee mechanics, normal
fail-closed behavior, and Tee-body limitation remain mandatory regressions.

Frontend tests must prove one canonical fixture feeds both buttons with exact decimal
strings and a fresh request, while the initial/manual workspace remains Angle-capable.
Full backend/frontend configured 100-percent coverage, static/type/build checks, clean
dependency reproduction/tree, both zero-vulnerability audits, exact old/new hashes,
JSON, whitespace, Stage 2.3 freeze, staged-tree identity, and object-isolated
committed-state QA are mandatory before normal push. Hosted four-job CI and V1-R2
through V6-R4 visual acceptance remain post-push evidence and cannot be inferred.

Measured local R4 evidence is 1,859 backend tests at 100-percent coverage over
13,285 statements and 4,168 branches, plus 250 frontend tests at 100-percent
configured coverage over 1,555 statements, 1,304 branches, 533 functions, and 1,299
lines. Static/type/build and clean dependency/audit gates pass with zero
vulnerabilities. The integrated repository gate also passes. Isolated committed-state,
push, hosted, and visual evidence are recorded separately.

## Stage 3.2-R5 cross-platform preview fingerprint validation

The accepted R4 hosted run passed Backend Windows and both 250-test frontend jobs.
Backend Ubuntu completed the suite and failed only the two exact U.S./SI preview-hash
assertions. R5 validation must reproduce that divergence at canonical pre-hash payload
level, identify the first structurally different fields, and prove a single production
root cause rather than rewriting expected hashes or applying post-hash normalization.

Focused tests must cover the controlled diagonal semantic angle and non-diagonal
conversion paths, and must expose the exact canonical preview JSON for
test inspection. Parameterized U.S./SI regressions must assert representative canonical
payload fields, hash the complete canonical payload to the unchanged controlled preview
fingerprints, exclude display-unit/camera-only state, and prove byte identity after
simulating Ubuntu's one-ULP-lower `sin(pi/4)` result. No platform branch, tolerance,
epsilon, rounding, quantization, clamp, or fixture-specific fingerprint rewrite is
allowed.

All R4 exact-unit and benchmark cases, Stage 3.2 G1-G6, R2 G1-G10, every Stage 2
golden/fingerprint, geometry and action invariants, frontend behavior, dependency and
workflow identities, controlled hashes, active frontend tree, and immutable Stage 2.3
tag remain mandatory. The four exact identities are U.S. execution
`c61a4d73946a014e218fdf02896ea08de90c1d9f94c6a2ca23495e72ca006a27`,
U.S. preview `f21cd78fc1c332c52268295c4fb273c1dc4ae841e6d94f7edeb5cbd984558961`,
SI execution `40ba8cb419f56f5b5c59e2b102c9842850bc925a600088b62185d96cc0314a69`,
and SI preview `94dee19bc2b27a9a726c94eed9e66ddcfd637d5a80a8d74230d8716b9294e9d2`.

Measured local R5 component evidence is 1,863 backend tests at 100-percent coverage
over 13,317 statements and 4,174 branches, plus the unchanged 250 frontend tests at
100-percent configured coverage over 1,555 statements, 1,304 branches, 533 functions,
and 1,299 lines. Ruff, strict mypy, ESLint, strict TypeScript, and production build
pass, as do the clean dependency tree, both zero-vulnerability audits, controlled
hashes, JSON, whitespace, freeze checks, and the integrated repository gate.
Object-isolated committed-state results are recorded after commit. Direct user
evidence accepts all four hosted R5 Ubuntu/Windows backend/frontend jobs.

## Stage 3.2-R6 live-preview state validation

R6 frontend tests must prove that a valid flat-plate-to-Angle change replaces backend
scene primitives, valid Interface A row and line growth changes only Interface A bolt
geometry, and an Interface B edit leaves Interface A unchanged. They must also prove
that an invalid current request preserves the last valid scene with an explicit
invalid/stale label, exposes safe backend detail, disables design, recovers after
correction, rejects late obsolete responses, and renders no guessed model when the
first preview is rejected.

Selection tests must retain stable entities and clear bolts or contacts absent from a
newly accepted model. Preview tests must bind acceptance to the current revision,
preserve AbortController/sequence latest-response-wins behavior, and distinguish
network failure from invalid geometry. Backend regression remains complete because no
backend production source or validation rule changes.

Measured local evidence is 1,864 backend tests at 100-percent coverage over 13,317
statements and 4,174 branches plus 259 frontend tests at 100-percent coverage over
1,613 statements, 1,416 branches, 544 functions, and 1,349 lines. Static, type, build,
dependency-tree, both zero-vulnerability audits, controlled hashes, R4 fingerprints,
JSON, whitespace, and freeze/tree identity remain mandatory. Object-isolated
committed-state QA, hosted four-job CI, and renewed V1-R2 through V6-R4 visual evidence
are recorded separately.

## Stage 3.2-R7 exact Angle bolt-path validation

R7 tests must load the byte-exact controlled golden and prove both selected Angle legs
resolve one finite exposed opposing broad boundary exactly `0.5 in` from the selected
outer surface. Heel-overlap, outside-leg, wrong-patch, ambiguous-candidate, and
thickness-mismatch paths must reject without epsilon, tolerance, or fallback. A
90-degree orientation must retain the same local physical surface pair and thickness
while the existing owner-frame transform changes its global mapping.

Application regression uses the exact `6 x 6 x 0.5 in`, `8 in`, zero-degree,
`LEG_Y_OUTER` fixture with 2-by-2 Interface A, `2 in` pitch/gauge, and `1.2815 in`
unloaded-end distance. All four finite paths must retain physical `LEG_1`, FRP material
region `LEG_1`, `LEG_1:EXTERIOR_TT_BROAD` and
`LEG_1:OPEN_AREA_TT_BROAD`, and exact `0.5 in` thickness with no heel layer. The
`1.2814 in` boundary and original `1 in` visual case remain invalid; Interface B and
all R4 fingerprints remain unchanged.

The full local backend gate passes 1,880 tests at 100-percent coverage over 13,367
statements and 4,192 branches. The frontend remains production-identical and passes
259 tests over 20 files at configured 100-percent coverage over 1,613 statements,
1,416 branches, 544 functions, and 1,349 lines. Ruff, strict mypy, ESLint, strict
TypeScript, and production build pass. Controlled hashes, locked dependencies, both
zero-vulnerability audits, JSON, whitespace, freeze/tree identity, integrated QA, and
object-isolated committed verification remain mandatory before normal push. Hosted R7
CI and renewed V1 visual acceptance remain direct post-push evidence.

## Stage 3.2-R8 exact profile-wall bolt-path validation

R8 tests must load the byte-exact controlled golden and prove exact finite same-wall
opposing boundaries for Channel web/flanges, W/I web/flanges, and every RHS wall.
Complete-hole containment must reject Channel and W/I junction overlap, flange/web
overlap, RHS corner overlap, outside-wall points, wrong patches, ambiguous candidates,
and exact thickness mismatches without epsilon, tolerance, rounding, quantization, or
float reconstruction of authoritative profile-wall coordinates. Angle remains governed
by the unchanged R7 resolver.

Application and HTTP regressions use the exact controlled Channel and RHS 2-by-2
fixtures. `1.3 in` and `1.7814 in` unloaded-end distances must remain invalid;
`1.7815 in` must resolve all four Interface A paths with exact profile element,
material region, outer/inner surface IDs, and wall thickness. RHS must expose
`INTERNAL_FASTENER_ACCESS_REQUIRED` without inferring hardware, installation, access
feasibility, or local-wall resistance. Interface B, W/I placement, R7 Angle cases, R4
U.S./SI fingerprints, Stage 2 calculation goldens, and frontend behavior remain exact.

Measured local backend evidence is 1,904 tests at 100-percent coverage over 13,431
statements and 4,214 branches. The unchanged frontend gate must retain 259 tests over
20 files at configured 100-percent coverage over 1,613 statements, 1,416 branches,
544 functions, and 1,349 lines. Ruff, strict mypy, ESLint, strict TypeScript,
production build, clean dependency tree, both zero-vulnerability audits, controlled
hashes, JSON, whitespace, freeze/tree identity, integrated QA, explicit staged review,
and object-isolated committed-state verification remain mandatory before normal push.
Hosted R8 CI and renewed V1 Channel/RHS visual acceptance remain direct post-push
evidence.

## Stage 3.2-R9 independent-interface, inclination, and hardware validation

R9 tests must load the byte-exact controlled golden and prove Interface A 2-by-1 with
Interface B 2-by-2, independent A/B mutations and fingerprints, and a physically valid
one-row group whose calculation remains fail-closed. No test may convert unsupported
single-row calculation into ordinary PASS.

Inclination coverage must include omitted/explicit zero identity, `+30°`, `-30°`,
arbitrary `27.5°`, both `±90°` boundaries, out-of-range/nonfinite/type rejection,
column/beam sign equivalence, profile-roll distinction, Interface B invariance, global
action/reference invariance, and rotated Angle/Channel/RHS geometry. Exact prior R5
trigonometric outputs and all legacy controlled fingerprints remain regression gates.

Fastener presentation tests must prove shared direct/Tee rendering, actual bolt axes,
opposite stack sides for head and nut, accepted schematic ratios, both interface IDs,
and washer count driven only by existing authority. Full local evidence is 1,929 backend
tests at 100-percent coverage over 13,504 statements and 4,242 branches, plus 263
frontend tests over 20 files at configured 100-percent coverage over 1,619 statements,
1,424 branches, 546 functions, and 1,353 lines. Static, build, dependency, audit,
controlled-hash, freeze/tree, JSON, whitespace, integrated, explicit staged, and
object-isolated committed-state gates remain mandatory before push. Hosted R9 CI and
V1-R9 through V5-R9 visual acceptance remain pending direct evidence.

## Stage 3.2-R10 fixed-grid positioning validation

R10 tests load the byte-exact controlled golden and prove the zero-angle legacy
fingerprints, fixed Interface A centers/axes at `+30°`, `-30°`, and `27.5°`, independent
A/B group offsets, exact edge/offset equivalence, independent counts, and persistence of
R9 hardware on canonical bolt axes. The controlled Angle complete-hole cases require
exact clearances `-0.2815`, `-0.0001`, `0`, and `0.0185 in` at entered distances `1.0`,
`1.2814`, `1.2815`, and `1.3 in` respectively.

Validation must separately prove physical geometry and calculation applicability. A
fixed-grid force/layout relationship outside the accepted method frame remains visible
as valid geometry but returns `ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN`, no
automatic demand, and no ordinary design result. Strict DTO/domain tests reject mixed
placement contracts, wrong-dimensional/nonfinite offsets, and every normal-offset key.

Measured local evidence is 1,951 backend tests at 100-percent coverage over 13,664
statements and 4,286 branches, plus 268 frontend tests over 20 files at configured
100-percent coverage over 1,668 statements, 1,487 branches, 557 functions, and 1,396
lines. Ruff, strict mypy, ESLint, strict TypeScript, and production build pass. The
integrated dependency/audit, controlled-hash, freeze/tree, and whitespace gate also
passes. Explicit staged review and object-isolated committed-state QA remain mandatory
before push. Hosted R10/R10A CI is accepted four of four green; V1-R10 through V6-R10
visual acceptance remains pending direct evidence.

## Stage 3.2-R11 simplified placement UX validation

R11 frontend tests prove that new Tee sessions retain the accepted physical default while
using exact signed vertical/horizontal offsets as the normal controls. Each interface
shows its independent pattern, Center action, server-authored directional and governing
clearances, containment-versus-code explanation, and collapsed Advanced placement. The
controlled U.S./SI loaders remain edge-distance controlled and their request semantics
remain unchanged.

Mode-switch tests require a current accepted backend placement trace, preserve the exact
alternate representation, pattern, other interface, and persistent viewer, and refuse an
unavailable conversion without changing request state. Positive, exact-zero-boundary,
and backend-rejected negative clearance states are distinguished by text and units; the
negative recovery instruction consumes the backend deficit and boundary direction and
does not call containment a code minimum.

Local evidence is 1,955 backend tests at 100-percent coverage over 13,664 statements and
4,286 branches, plus 270 frontend tests over 20 files at configured 100-percent coverage
over 1,719 statements, 1,514 branches, 564 functions, and 1,441 lines. Static, type,
build, dependency-tree, zero-vulnerability audit, controlled-hash, R4/R10 fingerprint,
freeze/tree, JSON, whitespace, explicit staged, integrated, and object-isolated gates
remain mandatory before push. Hosted R11 CI and V1-R11 through V5-R11 remain pending
direct post-push evidence.

## Stage 3.2-R12 member-end trim validation

R12 tests load the byte-exact controlled golden and prove T1-T7: exact trim-off
backward compatibility, the 25-degree Angle at 0, 0.25, and 0.5-inch clearance,
negative-input rejection, physical center/hole-edge trim distances with governing bolt,
and generic Channel/RHS cutting. Domain/application coverage additionally proves the
same backend cut engine for Angle, Channel, W/I, RHS, and Flat Plate; positive-volume
interference status; deterministic faces/meshes; R10/R11 offset interaction; exact
U.S./SI behavior; incomplete-hole and remaining-interference rejection; and the
trim-enabled resistance handoff failing closed.

Frontend coverage proves the explicit disabled default, unit-aware nonnegative input,
backend-reported trim/interference state, canonical trimmed mesh consumption, last-valid
recovery, stale-design semantics, and unchanged direct/reference and R4/R11 behavior.
Local evidence is 1,982 backend tests at 100-percent coverage over 13,932 statements
and 4,374 branches, plus 274 frontend tests across 20 files at configured 100-percent
coverage over 1,740 statements, 1,554 branches, 574 functions, and 1,457 lines. Static,
build, dependency, both zero-vulnerability audits, controlled-hash, fingerprint,
freeze/tree, JSON, whitespace, integrated, explicit staged, and object-isolated gates
remain mandatory before push. Hosted four-job CI and V1-R12 through V6-R12 remain
pending direct evidence.

## Stage 3.2-R13 Tee length-anchor validation

R13 tests load the byte-exact controlled golden and prove A1-A8: the legacy centered
6-inch body, centered 8-inch growth, positive-end-fixed and negative-end-fixed growth,
equivalent physical anchor representations, translated-body identity, unchanged
Interface A/B master bolt centers and axes, and exact U.S./SI equivalence. Tests also
prove the stable `D_T`/`L_T` trace, decimal half-length equations, strict enum/unit/
finite validation, actual finite-end complete-hole clearances and governing identities,
unchanged connected/supporting members, R7/R8 path behavior, and unchanged inclined R12
trim clearance.

Frontend coverage proves role-aware anchor labels, unit-aware body position, current-
preview-only mode conversion without a scene jump, centered and one-sided 6-to-8 growth,
body-only translation, fixed bolt groups, R6 last-valid invalid-containment behavior,
R11 placement independence, R12 control continuity, persistent viewer behavior, and
direct/reference isolation. Local evidence is 2,000 backend tests at 100-percent
coverage over 13,998 statements and 4,392 branches, plus 279 frontend tests across 20
files at configured 100-percent coverage over 1,751 statements, 1,576 branches, 579
functions, and 1,467 lines. Static, build, dependency, both zero-vulnerability audits,
controlled-hash, fingerprint, freeze/tree, JSON, whitespace, integrated, explicit
staged, and object-isolated gates remain mandatory before push. Hosted four-job CI and
V1-R13 through V7-R13 remain pending direct evidence.

## Stage 3.2-R14B region-material-basis validation

R14B tests load the byte-exact controlled golden and prove the exact W/I web, Tee stem,
Angle Leg 2, Channel web, and RHS side-wall bases. They independently prove physical-
plane membership, exact thickness direction, orthogonality, unit length, right-handedness,
Column/Beam and brace/profile global transforms, and exact preservation of Tee flange,
W/I flanges, Angle Leg 1, Channel flanges, RHS top/bottom, and Flat Plate.

Matched legacy/current fixture tests compare complete geometry projections and numerical
design objects exactly, including demand, handoff, group modes, capacity, utilization,
status, and applicability. They reconstruct complete canonical payloads and assert every
authorized preview/platform transition plus unchanged engineering/interface/result
identities. Frontend tests cover every physical region occurrence, direct vector mapping,
friendly region labels, stable IDs, view modes, overlay behavior, and direct/reference
regression. Full static, coverage, build, dependency, audit, hash, freeze/tree, JSON,
whitespace, integrated, staged, and object-isolated gates remain mandatory. Hosted four-
job CI and V1-R14B through V7-R14B require direct post-push evidence.

Recorded local/integrated component evidence is 2,027 backend tests at 100-percent
coverage over 14,014 statements and 4,400 branches, plus 280 frontend tests across 20
files at configured 100-percent coverage over 1,758 statements, 1,588 branches, 581
functions, and 1,474 lines. Both npm audits report zero vulnerabilities.

## Stage 3.2-R14C region-embedded material-axis visualization validation

R14C frontend tests prove the material overlay defaults off, shows one accessible
color-and-shape legend only when enabled, retains the same camera/reset state, and
contains no normal-mode per-arrow LW/CW/TT sprites. Scene-model tests associate exact
backend component/element/material-region IDs with physical box or trimmed-mesh
primitives and prove separate bounded surface anchors for W/I flanges and webs, Channel
flanges and web, both Angle legs, Tee flange and stem, four RHS walls, and Flat Plate.

Pure presentation tests prove positive-TT surface offset, dimension-bounded scale,
camera-relative TT dot/cross/tangent classification, Solid depth occlusion, X-ray
readability, missing/degenerate-region failure, and zero canonical snapshot mutation.
Source audits require one renderer shared by direct, multi-row, and Tee workspaces, no
profile-specific direction logic, no render-loop React state, and no engineering,
fingerprint, dependency, or workflow behavior. Exact R14B basis/fingerprint, geometry,
calculation, package/lock, freeze, full static/coverage/build/audit, integrated, staged,
and object-isolated gates remain mandatory. Hosted four-job CI and V1-R14C through
V8-R14C require direct post-push evidence.

Recorded local/integrated component evidence is 2,027 backend tests at 100-percent
coverage over 14,014 statements and 4,400 branches, plus 288 frontend tests across 21
files at configured 100-percent coverage over 1,820 statements, 1,610 branches, 601
functions, and 1,528 lines. Both npm audits report zero vulnerabilities. The active
frontend source tree is `fbbf52fa5ad719a6f3e434a19df74c236cd25dfb`; the R14B backend basis and every
engineering fingerprint remain exact.

## Stage 3.2 Tee-connection freeze validation

The Stage 3.2 freeze manifest is a governance/reproducibility artifact, not a new
engineering authority. Its audit runs through the existing backend and integrated QA
paths and verifies the exact frontend/backend source trees, package and secure-lock
Git objects, lock SHA-256, all 30 accepted Stage 3.2 controlled-artifact hashes, all
15 inherited registered Stage 2 hashes, the R14B transition-register hash, and
manifest internal consistency. It also verifies the immutable Stage 2.3 target when
the annotated tag is present and always verifies the byte-exact Stage 2.3 freeze
record in shallow/no-tag environments.

The audit distinguishes product baseline commit
`9aa5706e89639e990a701de965b04fa448d09c26` from the non-recursive governance commit
containing the manifest. The complete local and object-isolated gates, configured
100-percent coverage, dependency tree, both zero-vulnerability npm audits, JSON,
whitespace, changed-path review, branch identity, and both tag targets are mandatory
before the new freeze can be reported complete. Hosted CI for the governance-only
push remains pending until direct evidence is supplied.

## Stage 3.3A single clip-angle validation

Stage 3.3A tests load and hash the byte-exact RC1 specification, golden benchmarks,
and authority ledger. Backend coverage proves G1-G10, exact U.S./SI equivalence,
semantic-hand mirroring, independent A/B layouts, complete-hole containment, physical
two-layer paths, member-end trim/interference, region material bases, exact resolved-
demand handoff, zero resistance during preview, failure precedence, strict DTOs, both
stateless routes, deterministic fingerprints, and fail-closed normal/body boundaries.

Frontend coverage proves the third connection-type workflow, U.S./SI benchmark loads,
all connector/member/support/fastener/action controls, independent group editing,
backend-authored geometry and solid hardware, result cards, explicit Run Design Check,
last-valid preview state, stale/race/abort behavior, accessibility, and Direct/Tee
isolation. Full static, configured 100-percent coverage, build, dependency/audit,
controlled-hash, JSON, whitespace, immutable-tag/freeze, explicit staging, and
object-isolated gates remain mandatory. Hosted four-job CI and V1-V10 require direct
post-push evidence.

## Stage 3.3A-R1 connected-profile preview binding validation

Backend tests cover the complete 5-family by 2-role preview matrix, exact family and
role identity, physical-element replacement after profile edits, backend-authored
material-region axes, and exact U.S./SI physical equivalence. Frontend tests prove that
the scene replaces accepted primitives from the latest response, retains stable
selection identifiers, and does not reconstruct profile solids or display an older
accepted family after a newer request wins.

The full Stage 3.3A golden and engineering-fingerprint suite, the complete Tee suite,
both freeze audits, package/lock identity, static analysis, configured coverage, build,
dependency audits, JSON, whitespace, real-browser inspection, explicit staging, and a
depth-one object-isolated committed-state run are required. Hosted CI remains pending
until direct post-push evidence is available.

## Stage 3.3A-R2 surface-side placement validation

Backend tests prove exact face-to-face contact and zero positive-volume overlap for Flat
Plate, Angle, Channel, finite-clear-web W/I, and RHS profiles. They cover both W/I web
faces and a supported flange face, positive/negative hand, inclination and roll, trim,
the unchanged sharp connector heel and support contact, exact Interface A/B bolt axes,
layer order, stack sides and clearances, plus fail-closed finite-profile interference.
The default W/I case whose clear web is shorter than the finite connector is required to
remain invalid without moving the connector or either grid.

Frontend coverage proves the scene consumes backend profile primitives directly and
does not add a profile-specific offset. Real-browser checks cover the five-profile valid
matrix, invalid-current/last-valid state, negative hand, and persistent camera view.
The full gates must retain all ten Stage 3.3A engineering fingerprints, G1-G10 numerical
results, Direct and frozen Tee regressions, both freeze audits/tags, controlled artifact
hashes, package/lock/workflow identity, JSON, whitespace, clean dependency tree, and
both zero-vulnerability audits. Hosted CI and final visual acceptance remain pending
until direct post-push evidence is available.

## Stage 3.3B symmetric paired clip-angle validation

Stage 3.3B tests load and hash the byte-exact RC1 specification, golden benchmarks,
and authority ledger. Backend coverage proves G1-G14, exact U.S./SI equivalence, the
fixed pair frame, positive/negative body mirroring, three qualified connected profiles,
one common three-layer path, two mirrored support paths, exact hardware counts, trim,
four material regions, pair/action symmetry, half-wrench split/recovery, common and
support demand exact-once behavior, parent-demand identity, controlled layer allocation,
failure precedence, four visible limitations, strict DTOs, deterministic fingerprints,
and zero resistance execution during preview.

Frontend coverage proves one unified paired-angle workflow, strict profile options,
backend-authored mirrored bodies/contact zones/material axes/hardware, three physical
result cards, live preview, explicit Run Design Check, stale/race/abort behavior,
selection and camera persistence, action editing, accessibility, and Direct/Tee/Single
Angle isolation. Full static, configured 100-percent coverage, build, dependency/audit,
controlled-hash, JSON, whitespace, immutable-tag/freeze, explicit staging, and depth-one
object-isolated gates are mandatory. Hosted four-job CI and V1-V11 remain direct
post-push evidence and cannot be inferred from local QA.

## Stage 3.3C1 shared rectangular/full-through architecture validation

Tests load and hash the byte-exact C1 RC1 specification, golden C1_G1-C1_G12 fixture,
and authority ledger; production never reads the golden. Backend coverage proves SRS is
one solid prism rather than an RHS representation, all four exact opposing-face pairs,
the fixed SRS volume basis, and the exact seven-entry support-target registry with no
W Beam Web target.

Physical-path coverage proves immutable material/free-span segments, exact RHS
`t/(D-2t)/t` and SRS `D` cores, external connector composition, one bolt/axis/shank,
exact opposing-hole UV identity, independent two-face containment and governing
deficit, external-only hardware, shank length including cavity, and cavity exclusion
from material/demand/resistance handoff. It also proves exact U.S./SI equivalence and
the three fail-closed future local-mechanics limitations without executing a new
equation or creating ordinary PASS.

Complete Direct, frozen Tee, Stage 3.3A R1-R4, Stage 3.3B, Stage 2.3/3.2 freeze,
controlled-hash, package/lock/workflow, static, configured 100-percent coverage, build,
dependency/audit, JSON, whitespace, explicit-staging, and depth-one object-isolated
gates are mandatory. Frontend production/UI exposure count is zero, so no new C1
product-scene acceptance is claimed. Hosted four-job CI remains pending direct evidence.

## Stage 3.3C2 Tee and Single Clip-Angle integration validation

Backend coverage loads and hashes the byte-exact C2 specification, C2_G1-C2_G18 golden,
and authority ledger; proves the exact seven targets and strict target/profile DTOs; and
exercises complete Tee/Single support matrices plus connected RHS/SRS. Open supports
must resolve the actual selected web or angle leg. Rectangular paths require one
bolt/axis/shank, correct material/free segments, two independently contained hole disks,
external-only hardware, and no cavity bearing or resistance layer.

Frontend coverage proves both families consume the same editor/target list, expose
target-specific dimensions/faces, keep SRS paired with RHS, and extend the shank/far
washer only from backend-authored path traces. Preview validity and design limitations
remain separate; preview executes zero resistance and design remains explicit.

Regression gates require exact permitted RHS successors; exact non-RHS Tee, Single,
Paired, and Direct behavior; C1 and both freeze audits; configured 100-percent coverage;
build; JSON/whitespace; clean npm tree; zero full/runtime audit vulnerabilities; explicit
staging; and a depth-one no-alternates clone. Hosted four-job CI remains pending direct
evidence.

The completed local and integrated gates contain 2,268 passing backend tests with exact
100-percent coverage over 16,595 statements and 4,984 branches, and 376 passing frontend
tests across 26 files with exact 100-percent coverage over 2,541 statements, 2,201
branches, 854 functions, and 2,074 lines. All static, build, dependency, audit, JSON,
whitespace, freeze, and repository-index checks passed.

### Stage 3.3C2-R1 correction validation

The exact workspace Tee RHS request must reach four full-through paths without calling
the historical single-wall resolver. Tests assert Y-positive/Y-negative opposing faces,
Tee-stem/near-wall/cavity/far-wall segment order, independent two-face containment, one
shank with zero internal hardware, and trim preservation. Legacy non-C2 Tee RHS tests
must continue through their accepted same-wall route.

Single Clip-Angle API coverage must serialize `3.3C2-RC1` at both response levels for
all seven support targets, all six authorized connected profiles, preview, and design.
Frontend parsing must accept that identity and reject an unknown future `3.3C3-RC1`
identity without weakening DTO validation. Current C2 fingerprints, C1 G1-G12, C2
G1-G18, Direct, non-RHS frozen Tee, Stage 3.3A, Stage 3.3B, and both freeze audits are
mandatory regressions.

The corrected local component gates contain 2,285 passing backend tests at exact
100-percent coverage over 16,598 statements and 4,986 branches, and 376 passing
frontend tests across 26 files at exact 100-percent coverage over 2,541 statements,
2,201 branches, 854 functions, and 2,074 lines. Integrated and committed-state isolated
evidence are recorded separately; hosted CI and visual acceptance require direct
post-push evidence.

## Stage 3.3 Clip-Angle family freeze validation

Validate the machine-readable freeze manifest byte-for-byte and prove its internal
counts, accepted product baseline, acceptance chain, CI and direct visual evidence,
accepted contracts, deliberate limitations, and future-stage policy. Hash every Stage
3.3 controlled artifact and inherited authority. Verify current production source,
workflow, package/lock, benchmark IDs, current Single/Paired profile and support
fingerprints, accepted Stage 3.3A/3.3B fingerprints, C2 RHS successor provenance, and
C3-R1 zero-transition records.

Verify the annotated Stage 2.3 and Stage 3.2 tag objects and peeled targets without
moving either tag. The new Stage 3.3 audit must pass before its tag exists and must prove
the tag resolves to the committed governance freeze after creation. Complete backend,
frontend, integrated, JSON, whitespace, exact-dependency-tree, full/runtime npm audit,
clean-index, and depth-one no-alternates committed-state gates are mandatory. Production
source, controlled engineering artifacts, dependencies, and workflow YAML must have
zero changes.

## Stage 3.4A Multi-Member Tee node validation

Authenticate the byte-exact family decision, RC1 specification, G1-G20 golden, authority
ledger, and controlling order hashes. Production must never read the golden. Backend
coverage proves immutable ordered slots, right-handed H/V/N frame, one/two/three-slot
activation, zero-slot rejection, exact profile/placement/path topology, same-face and
interference validation, independent groups/trims, cross-group overlap, exact support
wrench and contribution trace, U.S./SI equivalence, deterministic fingerprints, and
exact-once reuse of accepted demand/handoff seams. Preview executes zero resistance;
Tee-body/intergroup limitations prohibit ordinary PASS while supported FAIL retains
precedence.

Frontend coverage proves the separate selector and unchanged historical default,
slot omission and controls, four independent group editors, backend-authored one/two/
three-member scenes, axes/selection, equilibrium trace, resistance-free live preview,
invalid/last-valid/race behavior, explicit design, stale results, and U.S./SI loaders.
Full Direct, frozen single-member Tee, Clip-Angle, G1-G20, package/lock/workflow,
controlled-hash, JSON, whitespace, immutable-tag/freeze, configured 100-percent
coverage, build, dependency/audit, explicit staging, and depth-one no-alternates gates
are mandatory. Hosted four-job CI and visual acceptance require direct post-push
evidence.

## Stage 3.4B Multi-Member Tee profile/support validation

Authenticate the byte-exact Stage 3.4B decision, RC1 specification, G1-G28 golden,
authority ledger, and controlling order hashes. Production must never read the golden.
Backend coverage must exercise all 18 slot/profile cases, horizontal Middle Flat Plate
and Angle, slot inclination domains, all seven shared support targets, open-profile
selected-surface paths, RHS/SRS through paths and external-only hardware, same-face
placement, interference, independent groups, cross-group complete-hole overlap, the
six-profile trim matrix, complete material axes, every slot combination, and U.S./SI
equivalence.

Frontend coverage must prove all three slots use one shared strict profile editor, the
existing shared support editor exposes exactly seven targets, stale fields are removed,
disabled slots retain no state, backend scene primitives drive all profile/support and
hardware rendering, and the resistance-free preview/explicit design/last-valid/race
boundaries remain exact. The `3.4A-RC1` default geometry, support wrench, and fingerprints
must remain exact.

Full Direct, frozen Tee, frozen Single/Paired Clip-Angle, package/lock/workflow,
controlled-hash, JSON, whitespace, immutable-tag/freeze, configured 100-percent coverage,
build, dependency/audit, explicit-staging, and depth-one no-alternates gates are mandatory.
Four hosted jobs and the complete 18-profile/seven-support visual matrix require direct
post-push evidence. No freeze tag is created by Stage 3.4B.

The complete local and integrated gates pass 2,420 backend tests at exact 100-percent
coverage over 17,650 statements and 5,314 branches, plus 442 frontend tests across 28
files at exact 100-percent coverage over 2,925 statements, 2,469 branches, 1,019
functions, and 2,351 lines. Static checks, production build, clean dependency tree,
both zero-vulnerability audits, JSON, whitespace, controlled hashes, and freeze audits
pass. Object-isolated, push, hosted, and direct visual evidence are recorded separately.

## Stage 3.4 Multi-Member Tee family freeze validation

Validate the byte-exact Stage 3.4 freeze manifest and its independently pinned product
baseline, source trees, package/lock, workflow tree, 11 repository artifact records,
27 inherited authority records, five external order hashes, acceptance chain, CI runs,
owner visual acceptance, G1-G20/G1-G28 identities, historical and representative
fingerprints, U.S./SI equivalence, frozen contracts, limitations, and future-stage
policy. Tamper-negative coverage must reject altered manifest bytes, tree/package,
artifact, fingerprint, and externally supplied freeze-target identities.

The audit supports tag-aware historical verification, exact current freeze-commit
verification before tag creation, and `manifest_only` verification for future depth-one
no-tags successors. The last mode must not inspect successor `HEAD` as the frozen source
tree and must never fetch from the network. Existing Stage 2.3 and Stage 3.2 audits and
the Stage 3.3 successor-safe audit remain mandatory.

Full backend, frontend, and integrated scripts; JSON and whitespace checks; clean npm
tree; full and runtime zero-vulnerability audits; controlled hashes; configured
100-percent coverage; explicit staging; a tagless no-alternates committed clone; normal
branch push; single annotated tag push; and final tag-aware verification are required.
No production-source, engineering-artifact, dependency, workflow, existing-manifest,
equation, result, status, applicability, or fingerprint change is permitted.

## Stage 3.5A Beam-to-Concrete Wall validation

Validate G1-G24 from the byte-exact test-only golden without permitting production to
read that fixture. Required evidence covers the finite wall and exact wall frame, W/I
beam and gap, symmetric paired angles, one common beam group, two mirrored exterior
anchor groups, blind embedment with no far-side hardware, complete containment and
invalid geometry, U.S./SI physical equivalence, and deterministic fingerprints.

The action surface must accept exactly one signed vertical reaction shear and reject
all user-applied moments. Tests must independently recover the common-group demand,
positive and negative branch forces/moments, and combined wall-interface wrench using
the backend Decimal `M + r × F` authority. The deterministic external anchor-design
handoff must retain wall frame, branch/group/combined wrenches, anchor coordinates,
edge distances, diameter, hole, embedment, and explicit unevaluated concrete/anchor
limitations. No concrete/anchor resistance, utilization, or ordinary whole-connection
PASS may appear.

Preview must execute zero resistance equations; design is explicit and calls eligible
existing paired/beam checks exactly once. Frontend gates cover selector mounting,
strict contracts, all editors, shear-only controls, last-valid/error/race behavior,
handoff copy/download, wall/beam/angle/anchor presentation, no far-side anchor nut,
material axes/wall frame, camera stability, and no navigation API calls.

Full Direct, frozen Tee, frozen Single/Paired Clip-Angle, frozen Multi-Member Tee,
package/lock/workflow, exact source/errata/artifact hashes, JSON, whitespace,
immutable-tag/freeze, configured 100-percent coverage, static/build, clean npm tree,
both zero-vulnerability audits, explicit staging, and depth-one no-alternates gates
are mandatory. Direct acceptance evidence is now recorded: Stage 3.5A run #76 rerun
attempt 2 passed all four Ubuntu/Windows backend/frontend jobs, and the owner accepted
the final Stage 3.5A-R2 successor visually on 2026-08-29.

The complete local component gates pass 2,453 backend tests at exact 100-percent
coverage over 18,274 statements and 5,416 branches, plus 465 frontend tests across 31
files at exact 100-percent coverage over 3,222 statements, 2,673 branches, 1,125
functions, and 2,546 lines. Integrated, object-isolated, push, hosted, and direct visual
evidence are recorded separately.

## Stage 3.5A-R1 completion validation

Validate the byte-exact R1 decision/specification/ledger and G1-G30 golden independently
of production. Required tests preserve every historical `3.5A-RC1` fingerprint and cover
the successor 1×1 default, exact branch/combined wrenches, explicit external-distribution
limitation, applicable 2×1/2×2 nominal traces, all six connected profiles, selected
surfaces/roll/gap, RHS cavity and SRS full depth, owner-qualified common/anchor hardware,
complete material axes, strict API fields, U.S./SI equality, zero-resistance preview,
and failure precedence.

Frontend regressions require the connected member and both clip angles in every valid
scene, right-handed render bases for reflected solids, one anchor bound to each angle by
default, six-profile field reset without stale fields, Brace/beam labels, preserved
preview/design state, camera behavior, handoff export, and no blank workspace or floating
anchor. Full Direct/Tee/Single/Paired/Multi-Member-Tee fingerprints and all four freeze
audits remain release-blocking. Complete configured 100-percent backend/frontend
coverage, static/build, JSON/whitespace, clean npm tree, zero full/runtime vulnerabilities,
explicit staging, and a depth-one no-alternates clone are required before normal push.
Run #77 passed all four hosted jobs; owner visual acceptance is closed through the final
Stage 3.5A-R2 successor on 2026-08-29.

## Stage 3.5A-R2 material-axis and three-component force validation

Validate byte-exact decision/specification/ledger hashes and all G1-G34 golden cases
without production fixture access. Required backend tests independently verify the
wall-frame force signs, exact force translation and generated moments, pure Major,
pure axial tension/compression, pure Minor, and combined cases; exact symmetry
eligibility; branch-resolved and combined-layout handoffs; Minor common-group normal
action; axial/prying/contact and nonmajor qualification limitations; one-anchor
external-distribution boundary; zero-resistance preview; explicit design; deterministic
U.S./SI identities; and exact historical Stage 3.5A/R1/frozen-family regressions.

The pre-mutation axis audit must prove every R14B FRP basis is unit/orthogonal and TT is
normal to its physical region. Frontend tests must create TT presentation independently
of camera occlusion, preserve exact transported vectors, cover W/I web and both flanges,
both clip-angle wall legs, all six connected profiles, RHS cavity exclusion, and concrete
FRP-axis exclusion. Major/Minor/Axial controls and arrow editing share one state; no moment
control exists. Combined-layout results show one complete wrench and no fabricated branch
cards.

Full backend/frontend/integrated QA, configured 100-percent coverage, static/build,
JSON/whitespace, clean npm tree, zero full/runtime vulnerabilities, controlled hashes,
historical fingerprints, all four freeze audits, explicit staging, and a depth-one
no-alternates clone are mandatory. Run #78 passed all four hosted jobs, and owner final
Stage 3.5A visual acceptance completed 2026-08-29.

## Stage 3.5B direct side-lap validation

Validate byte-exact decision/specification/golden/ledger hashes and all G1-G37 boundaries
without production fixture access. Backend tests cover the finite wall free end, member
continuation, independent lap/anchor placement, explicit center action, Channel web-only
and both Angle-leg selections, free-leg/heel interference, direct penetrated-layer order,
blind hardware, complete hole/face/overlap containment, exact action reference and wrench,
Minor and out-of-plane limitations, preview-zero-resistance, applicable local-FRP failure
precedence, deterministic handoff, and exact U.S./SI identities.

Frontend tests cover the separate selector option, Channel/Angle field reset, one shared
request state, nonmoving anchors on lap edits, explicit centering, live invalid geometry,
three editable force arrows with no moment control, stale explicit design behavior,
copy/download handoff, material axes, persistent navigation, accessibility, and absence of
frontend geometry or wrench authority. Stage 3.5A/R1/R2 identities and every frozen family
audit remain release-blocking. Complete configured 100-percent backend/frontend coverage,
static/build, JSON/whitespace, clean npm tree, zero full/runtime vulnerabilities, explicit
staging, and a depth-one no-alternates clone are mandatory. Run #79 passed all four
hosted jobs; owner visual acceptance is closed through Stage 3.5B-R1 on 2026-08-29.

## Stage 3.5C column-base web-angle validation

Validate the byte-exact Stage 3.5C decision/specification/golden/ledger hashes and
all G1-G43 boundaries without production fixture access. Backend tests cover the
exact base frame and finite solids; Single positive/negative and symmetric Double
topologies; web, anchor, bearing-footprint, and material-direction matrices;
compression and shear actions; component-demand provenance; group resolution;
layer classification; exact component and foundation equilibrium; limitations;
preview zero resistance; explicit design; strict API behavior; deterministic
handoff; U.S./SI equivalence; and engineering fingerprints.

The release-blocking philosophy assertions are: web local transfer equals 100% of
`Pu` in web `LW`; the angle system independently equals 100% in vertical-leg `CW`;
Double branches equal `Pu/2` only after exact symmetry proof; and the physical
foundation reaction equals `Pu` once. Web-normal force receives no invented branch
split, bolt tension, or prying method. Angle-body/heel, concrete-bearing, and anchor
capacity remain explicit external or `NOT_EVALUATED` limits and ordinary unsupported
PASS is prohibited.

Frontend tests cover the separate Column selector group, one shared request state,
complete Single/Double scene and hardware, exact backend material axes, component
demand/foundation cards, three controlled force inputs with no uplift or moment,
live invalid/current/last-valid state, stale explicit-design behavior, deterministic
copy/download handoff, persistent navigation, accessibility, and absence of frontend
geometry, demand, or wrench authority.

Stage 3.5A/R1/R2/B/R1 identities and every Stage 2.3/3.2/3.3/3.4 frozen-family
audit remain release-blocking. Complete configured 100-percent backend/frontend
coverage, Ruff, strict mypy, ESLint, strict TypeScript, production build,
JSON/whitespace, exact controlled hashes, clean npm tree, zero full/runtime
vulnerabilities, explicit staging, and a depth-one no-tags/no-alternates clone are
mandatory. Run #81 passed all four hosted jobs; Stage 3.5C-R1 closed the presentation
comments and owner visual acceptance is complete through Stage 3.5C-R2 on 2026-08-29.
The beam web-splice family is not started.

## Stage 3.5C-R2 signed axial compression/uplift validation

Validate the four prescribed R2 hashes and all G1-G48 cases without production golden
access. Backend gates cover strict historical/successor field exclusion, all finite signed
axial values, exact compression/uplift/zero base and branch wrenches, full signed web LW
and angle-system CW traces, proof-gated signed half branches, one foundation reaction,
signed local vectors, reverse-path fail-closed behavior, contact/angle/prying/anchor/
concrete limitations, web-normal combined layout, zero-resistance preview, explicit
design, deterministic handoff, U.S./SI, and historical/frozen fingerprints.

Frontend gates cover the signed field/default/help, positive/negative/zero arrow matrix
from the backend action reference, shared sidebar/arrow state, compression/uplift
component cards with distinct signed action and magnitude, Single/Double branches, one
foundation action, visible limitations, no moment fields, current/invalid/last-valid
workflow, camera persistence, and Stage 3.5/frozen scene regressions. Full QA, exact
coverage, static/build/security/freeze gates, and object-isolated verification remain
release-blocking. GitHub Actions run #83 passed 4/4 and owner visual acceptance completed
2026-08-29; no beam web-splice work is authorized.

## Stage 3.5 family-freeze validation

Validate the deterministic Stage 3.5 manifest byte hash, accepted baseline and ordered
chain, CI runs #76–#83, owner acceptance, all 28 controlled artifacts and 47 inherited
authorities, exact source/package/lock/workflow identities, historical/current contracts,
benchmark ranges, fingerprints, limitations, external-design boundaries, and all four
existing freeze tags.

Negative tests must reject changed manifest bytes, backend/frontend source identities,
package/lock/workflow identities, artifact hashes, accepted baseline, current contract,
fingerprint, limitation, wrong explicit historical object, wrong tag target, and successor
`HEAD` substitution. Verify `manifest_only` in a depth-one tagless clone, explicit-object
resolution against the committed historical object, and `tag` resolution after annotated
tag creation. Full configured QA, zero vulnerabilities, clean explicit staging, and exact
zero production/engineering/dependency/workflow drift are release-blocking.

## Stage 3.6A symmetric double web-splice validation

Validate the prescribed decision, specification, G1-G43 golden, ledger, and order hashes;
production must never access the golden. Backend gates cover strict DTOs, exactly two
identical W/I beams, positive gap/end planes, two identical opposing plates, two distinct
mirrored 2x2 groups, unique bolts, Plate/Web/Plate stacks, complete-hole containment,
flange/plate interference, equal-and-opposite actions, exact centroid moments, independent
Stage 2.5A calls, full web and proof-gated half-plate traces, actual material directions,
independent Beam B reversal, U.S./SI identity, zero-resistance preview, explicit design,
FAIL precedence, deterministic fingerprints, and all deliberate limitations.

Frontend gates cover Beam-connection selector placement, locked Beam B/second-plate
presentation, explicit web/flange solids, both groups and all holes/hardware, material
axes, signed action arrows, shared sidebar/arrow request state, stale design, invalid
geometry retention, camera persistence, and absence of moment/flange/single-plate controls.
Full configured backend/frontend 100-percent coverage, static analysis, production build,
JSON/whitespace checks, zero vulnerabilities, exact Stage 3.5 and earlier freeze audits,
and fresh depth-one no-tags/no-alternates object-isolated verification are release-blocking.

## Calculation Slice 4 Chapter 7 plate-strength validation

Verify the byte-exact decision, engineering specification, G1-G40 golden, authority
ledger, and controlling-order hashes; production must never read the golden. Cover exact
tension, compression rupture/buckling, permitted combined-compression buckling, both
piecewise shear branches including exact `eta=1`, governing minima, locked factors,
single time-factor application, advisory-only commentary, invalid inputs, source
provenance, deterministic fingerprints, and U.S./SI physical identity.

Pure transverse compression stability and out-of-range combined compression must fail
closed without invented equations. Full backend/frontend/integrated QA, configured
100-percent coverage, static analysis, JSON/whitespace/dependency/security gates,
Stage 3.6A fingerprint regression, all freeze audits, zero frontend-production change,
and fresh depth-one no-tags/no-alternates verification are release-blocking. Revised
Stage 3.6B remains paused.

## Stage 3.6B RC2 web-splice resistance validation

Verify the byte-exact RC2 decision, engineering specification, G1-G50 golden, authority
ledger, and controlling-order hashes; all earlier Stage 3.6B packages are superseded and
must remain unregistered and unimplemented. Production must never read the golden.
Backend gates cover exact clear-body derivation, left/joint/right critical sections,
pair/full and plate-half action provenance, exact eccentric body moments, `A`, `I`,
extreme-fiber normal stresses, `V/A` shear stress, unchanged Slice 4 pure-mode calls,
normal/shear/rational utilization, governing section and fiber, review-qualified success,
FAIL precedence, Section 2.3.2 provenance, and exact disclaimer metadata.

Prove exactly two physical shear planes before dividing each actual Stage 2.5A per-bolt
vector. Cover source-authorized nominal metallic shear strength, exact analytical
capacity/utilization, separate Beam A/B records, source-pending F593, thread authority,
invalid topology, Minor-shear and user-moment exclusions, U.S./SI identity, preview zero
resistance, and explicit design. Frontend gates cover body and double-shear panels,
critical values, advisories/provenance, review/qualification/disclaimer visibility,
source-pending behavior, historical scene/navigation/stale-state behavior, and no
frontend equation. Full configured backend/frontend 100-percent coverage, static/build,
JSON/whitespace/dependency/security audits, G1-G50, Slice 4 and Stage 3.6A regression,
every freeze audit, and fresh depth-one no-tags/no-alternates verification are release
blocking. GitHub Actions run #87 passed all four jobs in approximately 4m30s, and owner
acceptance completed 2026-08-30.

## Stage 3.6 W/I Web-Splice Family freeze validation

Authenticate manifest SHA-256
`58AA05F545984EAAC0EDED666B4BA086BA05ADE40E59C39D3B7821BFFEB60658`, all 12
controlled artifacts, all 38 inherited authorities, baseline `5f77abd0...`, acceptance
chain, CI #85–#87, owner evidence, exact W/I-only contracts/fingerprints, rational method
and panel, disclaimer identity/meaning, physical two-plane bolt contract, F593 boundary,
Minor/moment limitations, result precedence, source/package/lock/workflow identities,
and all five historical tag objects/targets.

Negative tests reject every controlled tamper category, including Channel inclusion and
successor-HEAD substitution. Validate `manifest_only` before the tag, a fresh depth-one
no-tags/no-alternates checkout, the explicit historical object with raw-header parent
verification, and `tag` after annotated tag creation. Run full backend/frontend tests at
configured 100-percent coverage, Ruff, strict mypy, ESLint, strict TypeScript, production
build, JSON and whitespace gates, dependency tree, full/runtime audits at zero
vulnerabilities, Stage 3.6A G1-G43, Slice 4 G1-G40, Stage 3.6B RC2 G1-G50, all earlier
family regressions, and all freeze audits.

Release-block if production source, controlled engineering artifacts, dependencies,
workflows, fingerprints, existing tags, or W/I authority changes. The only new tag is
`stage-3.6-wi-web-splice-family-freeze`, created after object-isolated success. Hosted CI
for the governance commit remains pending direct 4/4 evidence. Channel support and every
later stage remain unstarted.

## Stage 3.7A column-base profile-matrix validation

Authenticate the byte-exact decision, engineering specification, G1-G60 golden,
authority ledger, and controlling-order hashes; production must never read the golden.
Cover strict W/I/RHS/SRS/Angle requests, exact Single/Double selectors, backend profile
frames/member references, every rectangular face/opposite face, exterior-only RHS/SRS
full-through hardware, cavity non-material status, Angle Leg Y/Leg Z, same-selected-leg
Double topology, other-leg interference, and different-leg rejection.

Verify exact shifted moments, column-full `LW` and angle-system-full vertical-leg `CW`
component demands, proof-gated W/I/RHS/SRS branch halves, Angle 0.5/1.0/0.5 local
provenance without fabricated complete branch wrenches, one foundation reaction,
normal/uplift limitations, external handoff, material-region axes, preview zero
resistance, explicit design, U.S./SI identity, and deterministic fingerprints.

Run configured 100-percent backend/frontend coverage, Ruff, strict mypy, ESLint, strict
TypeScript, production build, JSON/whitespace/dependency/security gates, historical
Stage 3.5C regression, all six freeze audits, and Direct/Tee/Clip/Multi-Member-Tee/
Web-Splice regression. A fresh depth-one no-tags/no-alternates clone must repeat the
complete committed-state gates before normal branch publication. No tag is created.

## Stage 3.7A-R1 Angle Single bolt-path orientation validation

Reproduce the exact Leg Y / negative-face / Single case before correction and locate the
first loss across backend layers, axis/endpoints, selected-face frame, scene shank, and
exterior hardware. Exercise all four Angle Single selected-leg/face combinations and
both same-selected-leg Double combinations. Assert connector and selected-leg
intersection, normal axis, ordered path, one shank, endpoint-owned exterior head/nut and
washer provenance, no internal hardware, retained other-leg geometry, and fail-closed
heel/perpendicular-leg interference.

Prove the frontend calculates its displayed shank and schematic end hardware only from
backend endpoints. Lock the two authorized negative-face Single geometry-fingerprint
transitions and exact invariance of positive Single, Double/uplift, Angle
centroid/reference, generated/foundation moments, demand/resistance behavior, material
axes, W/I/RHS/SRS, G1-G60, historical Stage 3.5C, and all frozen-family fingerprints.
Run complete configured 100-percent backend/frontend coverage, strict static/build,
JSON/whitespace/dependency/security, all six freeze audits, explicit staging, and a fresh
depth-one no-tags/no-alternates committed clone before one normal push. No tag or future
Angle-column moment topology is authorized.

Measured local evidence is 2,721 backend tests at configured 100-percent coverage over
21,542 statements and 5,986 branches, plus 571 frontend tests across 39 files at
configured 100-percent coverage over 4,178 statements, 3,531 branches, 1,465 functions,
and 3,129 lines. Static/build, dependency, JSON/whitespace, runtime smoke, freeze, and
both zero-vulnerability audit gates pass.

## Stage 3.7 Column-Base Shear Family freeze validation

Authenticate manifest SHA-256
`8C7CD0238C7A95E54E4B6DC987E4A558AE2910DA80342137C7772B7FCF6EC9AE`, all 4
controlled Stage 3.7 artifacts, all 34 inherited authorities, accepted baseline
`0403bc8a...`, the Stage 3.7A/R1 chain, CI #89/#90, owner evidence, exact eight-case
profile/assembly matrix, six-case Angle orientation matrix, source/package/lock/workflow
identities, fingerprints, member references, paths, demand/foundation rules, material
directions, limitations, and all six historical tags.

Negative tests must reject changed manifest bytes, backend/frontend source trees,
packages/locks/workflows, controlled artifact hashes, baseline, matrix/topology,
different-leg moment inclusion, Angle centroid/reference or R1 negative-face rules,
component/foundation rules, material axes, connection-normal and external-design
boundaries, fingerprints, wrong explicit targets, wrong tag targets, and successor-HEAD
substitution.

Validate `manifest_only` before tag creation, an exact explicit freeze object using raw
commit-header parent proof, a fresh depth-one no-tags/no-alternates complete QA clone,
and `tag` after annotation. Run complete configured 100-percent backend/frontend
coverage, strict static/build gates, JSON/whitespace/dependency/security checks, G1-G60,
Stage 3.7A-R1 orientations, all historical family regressions, and all freeze audits.
Release-block any production, controlled-artifact, dependency, workflow, existing-tag,
or fingerprint change. The future Angle moment topology must remain absent.

## Calculation Slice 5 W/I moment-component validation

Authenticate the byte-exact decision, specification, G1-G52 golden, authority ledger,
and controlling-order hashes. Verify accepted W/I geometry reuse; strict supported and
unsupported action behavior; exact Decimal section properties, stress integration,
top-flange/web/bottom-flange forces, region-local moments, web shear, reference shifts,
and exact force and moment equilibrium. Verify stress extrema/state, flange lever arm,
exact flange couple, residual web moment, review/disclaimer metadata, and reference-only
`M/z` without any capacity or physical-connection output.

Require exact equivalent U.S./SI canonical results and fingerprints, presentation-field
fingerprint exclusion, all G1-G52 categories, full configured 100-percent backend and
unchanged frontend coverage, strict static/build/JSON/whitespace/dependency/security
gates, all historical freeze audits and fingerprints, and a fresh depth-one no-tags/
no-alternates complete-QA clone. Release-block any frontend production, dependency,
workflow, tag, frozen-family, or Stage 4.1A physical-product change.

## Stage 4.1A W/I major-axis moment-splice validation

Stage 4.1A verification executes controlled G1-G96 and all inherited Slice 5 G1-G52.
It proves the strict selector/request contract; exact two-beam/gap, web-plate, six-flange-
plate, 12-group, and 24-bolt geometry; complete Slice 5 wrench handoff; Beam A/B sign
handling; web free-moment retention; exact top/bottom outer-inner branch equilibrium;
rational face-sublayer checks; Calculation Slice 4 body reuse; actual unequal bolt-plane
demands; source-pending F593 behavior; exact whole-joint equilibrium; deterministic
U.S./SI fingerprints; resistance-free preview; explicit design; invalid/unsupported
fail-closed paths; and the qualification/disclaimer/result precedence.

Frontend validation covers the Moment selector, all authorized fields, six flange plates,
inner-strip and X-ray-compatible scene data, 24 bolt/hole paths, signed force/moment
arrows, region material axes, live preview debounce/abort/latest-response behavior,
last-valid and stale states, explicit design trace, no duplicate keys, and historical
product routing. Full backend statement/branch and frontend statement/branch/function/
line coverage remain 100 percent. Every Stage 2.3 through Stage 3.7 freeze audit and all
historical fingerprints remain mandatory. GitHub Actions run #93 and owner acceptance
provide the accepted Stage 4.1A product evidence recorded by the freeze order.

## Stage 4.1A freeze validation

Authenticate freeze-order SHA-256
`0646F456A035C0A2C09492AFF4A59B4A4A8D8E665B346F1DC7B16443D79A3290`, manifest
SHA-256 `A77FACD1A05F60E947F3F394FCFB3FC5D28120922BF6EA9841E4EC9C80D4061F`, baseline
`59713e53...`, the Slice 5 parent, controlled and inherited authorities, exact source and
dependency identities, engineering fingerprints, accepted CI #92/#93, owner visual
matrix, all limitations, and every historical freeze tag.

Run the successor-safe audit in `manifest_only`, explicit-object, and annotated-tag
modes. Parent proof must come from the raw commit header. A fresh depth-one, tagless,
no-alternates checkout must pass the complete backend/frontend configured-coverage,
static/build, JSON/whitespace, dependency/security, engineering/golden, and historical
freeze suite. Release-block any production, controlled-artifact, dependency, workflow,
tag, fingerprint, rational-method, or qualification change. Stage 4.1B must remain absent.

## Calculation Slice 6 Channel moment-reference and resultant validation

Calculation Slice 6 verification executes controlled G1-G72. It proves exact reuse of
the accepted Channel dimensions; exact centroid, web-plane, and shear-center references;
mutually exclusive rational/explicit shear-center sources and explicit-source provenance;
all six signed action components; complete top-flange/web/bottom-flange wrenches; retained
reference-shift moments and generated torsion; exact force and moment equilibrium; stress,
couple, residual, free-torsion, and rational shear-flow diagnostics; pure/sign-reversal and
combined cases; strict invalid-input and Section 2.3.2 homogeneity gates; deterministic
equivalent U.S./SI fingerprints; and the controlled review disclaimer.

The Slice 6 production module requires 100-percent statement and branch coverage. Full
backend and unchanged frontend configured coverage, static/build, JSON/whitespace,
dependency/security, Slice 5/Stage 4.1A, historical engineering/golden, and every
successor-safe freeze audit remain mandatory. A fresh depth-one, no-tags, no-alternates
clone must pass the same gates. Release-block resistance, physical Stage 4.1B geometry,
API/frontend production, dependency, workflow, tag, or frozen-family changes.

## Stage 4.1B Channel major-axis moment-splice validation

Execute controlled G1-G112 and unchanged Slice 6 G1-G72. Prove exact Slice 6 handoff,
centroid/shear-center authority, retained generated torsion and transverse moment ledger,
six physical plates, exact back/opening web-force recovery, independently signed default
web shear, complete paths/endpoints, actual Stage 2.5A plane vectors, rational face
sublayers and plate bodies, source-pending F593 behavior, and exact six-component and
Beam-A/Beam-B equilibrium. Cover pure modes, sign reversals, explicit shear-center
provenance, invalid geometry, U.S./SI identities, preview/design separation, status
precedence, disclaimer, classification, API/UI state, X-ray access, and material axes.

Require configured 100-percent backend and frontend coverage, full static/build/security/
whitespace gates, historical fingerprints, every successor-safe freeze audit, and a
fresh depth-one no-tags/no-alternates committed-object run. Release-block Slice 6 or
frozen-family reinterpretation, blind web-face sharing, hidden moment/torsion, invented
capacity, dependency/workflow/tag change, or later-stage work.

## Stage 4.1 family freeze validation

Freeze accepted R1-inclusive baseline `6d953dbef648bd35ab21b5208432579cdeb59902` with
zero production or engineering changes. Validate all 16 controlled artifacts and 53
inherited authorities; exact backend/frontend/package/lock/workflow identities; W/I
and Channel fingerprints; all eight historical tags; and the new manifest hash.
Execute the complete G1–G52 / G1–G96 / G1–G72 / G1–G112 matrices and existing R1
nonblank-root, selector/direct-load, U.S./SI, explicit-design, and unit-switch regression.

The family audit must reject the 32 tamper categories in order section 34. Test Git
tree identity independent of enumeration, path separators, and checkout line endings.
Read raw commit headers for parent proof at shallow boundaries. Validate historical
objects by tag or explicit full SHA; missing history resolves to authenticated
manifest-only inventory, never successor source. Verify a real tagless successor with
changed source and unavailable historical commit. All existing freeze audits must pass
unchanged. Require complete local and object-isolated coverage/static/security QA,
clean worktree, normal branch push, exact annotated-tag audit/push, then direct hosted
Backend/Frontend Ubuntu/Windows evidence. No next family begins under this order.

## Stage 4.2 RC1-R7 validation

Require G1–G128 and independent native comparisons: Slice 5 complete resultants, four Slice 7 calls, Stage 2.5A flange outputs and governing order, direct Slice 8 positive/negative web calls at (0,2), retained attachment out-of-plane demand, exact native wall diagnostics, pure/sign cases, source-qualified arithmetic and invalid/source matrices. Production must not read golden JSON. The real frontend wire fixture must be a subset of native backend serialization. Test zero resistance in preview, explicit design, stale/invalid/last-valid/network/abort handling, scene handedness, signed/zero arrows and all historical regressions. No epsilon or diagnostic redistribution.

## Stage 4.2 freeze validation

The accepted corrected product `1dee177a02bcaec713c1e3f597b053790ff7337e` has owner visual/result acceptance and direct CI #103 attempt 1 4/4 SUCCESS. Freeze manifest SHA-256 `71A73CF5599B9A2540FC3DD22D024D99565E3D5A9FCF07FACC027D523257F997` pins unchanged RC1-R7 and cumulative original/R3–R7 authority, native component/core/group/result and material/factor identities. Require G1–G128, Slice 5/7/8 regressions, Stage 2.5A compatibility, pure-shear failure visibility, sidebar grouping and every unchanged historical freeze audit. Full local and fresh depth-one/no-tags/no-alternates QA must remain 3253 backend / 623 frontend with configured 100% coverage, complete static/build/integrity/dependency/security gates and zero findings. No repeated visual review is needed for zero-production governance work. FROZEN activates only after normal governance main push, direct new four-job CI and verified exact annotated tag; see `STAGE_4_2_FREEZE.md`. External anchor/concrete and future 316SS/Stage 4.3 remain outside scope.

## Stage 4.3 freeze acceptance and reproducibility gates

Accepted engineering implementation `2e4416a4dbd0b99c6a7280f6576264c37c09101a`; security successor `513e1c9150e63206e432a8d2f971617b6ed9c203`; current tests-only successor/baseline `36f6049c09b3df29ea899af826fbba19f26496b3` (112 commits). Engineering CI #105 attempt 2, security CI #106 attempt 2, and baseline CI #107 attempt 1 are accepted four-job SUCCESS. Owner final visual/result acceptance is ACCEPTED.

Manifest: `docs/governance/STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_FREEZE_MANIFEST.json`, SHA-256 `F120A681C4F85B36EA7519F46E16567F4913C5A181D1BDD6AF07F6CA1E6CC7F0`. See `docs/qa/STAGE_4_3_FREEZE.md`. Status FROZEN activates only after complete governance QA, fresh object-isolated verification, normal main push, direct governance CI 4/4, and verified annotated tag `stage-4.3-wi-beam-frp-support-moment-connection-freeze`. Post-commit evidence is external; SELF is the governance commit with parent `c59ead41acf7e2507842de86fca2a578ee8cb8e3` and expected count 114.

Retain T43-001–T43-090, F43-R01–R04/T01/B01, all five supports by eight loads by U.S./SI (80 cases), Slice 5 G1–G52, Slice 7 G1–G72, Slice 8 G1–G80, Stage 2.5A and Stage 4.2 G1–G128 plus all historical freezes. Native direct-engine equality and historical tamper detection remain mandatory.

All five receiving configurations (W/I flange, W/I web, hollow square, solid square, Channel web) remain exact. Complete native dependency wrenches, material directions, actual through-bolt paths, native failure/source traces and qualified support-response boundaries are unchanged. In-plane projection does not establish normal tension/contact/prying response; unavailable is not zero. Hollow walls do not automatically share load or confer double-shear capacity; full solid depth is not a thin plate. Whole receiving-member design remains `NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY`. No ordinary PASS, new qualified source, Stage 4.4/4.5, or 316SS authority is created.

Recheck JSON, staged whitespace, exact controlled hashes, original ten draft hashes, ten local/remote historical tags, governance-register consistency and zero non-governance diff. Repeat full backend/frontend QA and 100% configured coverage, all static/build/security gates, then exact-commit depth-one/no-tags/no-alternates QA. No new browser review is required for unchanged accepted production. Tag only after governance push and direct hosted 4/4 green.

## Windows CI stabilization and final freeze target

Finalization supersedes only the prior freeze publication target: first governance commit `c59ead41acf7e2507842de86fca2a578ee8cb8e3` (count 113) had CI #108 attempt 2 with three green jobs and two Windows 5000 ms frontend timeouts. Final SELF has parent `c59ead41acf7e2507842de86fca2a578ee8cb8e3`, exact subject `test: stabilize Windows Stage 4.3 freeze timeouts`, and count 114. Only the two named tests receive local 15000 ms limits; `backend/tests/calculation/test_scope_boundaries.py` authenticates their exact timeout-only successors while preserving the original historical digest and tamper detection. Both tests passed 10 consecutive Windows runs. Production, engineering, controlled artifacts, dependencies, workflows and all ten existing tags remain unchanged. The final annotated freeze tag targets SELF only after complete local/object-isolated QA and direct hosted four-job SUCCESS; final run/tag evidence is recorded externally without amendment.

Finalization Order R1 SHA-256: `1397BC0FC17BD4C67D79FE3DFFB20A94818621FB091D309BD167DF81ADDF27F9`. Final manifest SHA-256: `F120A681C4F85B36EA7519F46E16567F4913C5A181D1BDD6AF07F6CA1E6CC7F0`.

## Stage 4.4 freeze regression obligations

Engineering implementation `e8bc2355bcecaabd70d31332cf1af3ee6eb17712` (115); accepted preview/state correction `d11012e771556f0ed5cac46f39ab40cb0a53273e` (116). Owner acceptance: **Stage 4.4 visual accepted**. Product CI #111 attempt 1 is four-job SUCCESS. The bounded tests-only scope-guard successor `388083ba0ae26be5de6bea986c668252db56adbb` (117) passed complete local/object-isolated QA and CI #112 attempt 1, four-job SUCCESS.

Manifest: `docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json`, SHA-256 `2035E881712086643440D67A4F78D142886F749F90BCEA285B01A2E7E37C9443`. Freeze order SHA-256: `21FA8D17DCBBDE6ED6BA2C93892D5343347E5FE521EB2ACB98578E89F86A8836`. See `docs/qa/STAGE_4_4_FREEZE.md`.

Preserve and execute the 96-requirement matrix, 14 references, 64-case sweep and 24 complete source-present test integrations. Synthetic qualified sources remain test-only, never production selection. Verify equal/unequal-leg U.S./SI geometry and exact native action/result fingerprints; exactly two different-leg connectors; total foundation wrench and generated Mz; no 50/50 shortcut; separate direct contact; unresolved-source states; external anchor/concrete boundary; explicit design and LAST VALID recovery/race protection.

Retain Slice 5/7/8, Stage 2.5A and all eleven historical freeze regressions. Authenticate manifest/register hashes, reconstruct historical Git trees, reject tampering and unauthorized production/dependency/workflow/test changes, and verify eleven tag objects and peeled targets unchanged. Full local and isolated QA, 100% configured coverage and zero full/runtime audits are mandatory; no skipped check or tolerance is introduced.

Freeze publication is gated: SELF is the governance commit with parent `388083ba0ae26be5de6bea986c668252db56adbb`, exact subject `chore: freeze Stage 4.4 angle-column two-leg moment base baseline`, and expected count 118. Stage 4.4 becomes FROZEN only after complete governance local/object-isolated QA, normal main push, direct governance four-job CI SUCCESS and verified annotated tag `stage-4.4-angle-column-two-leg-moment-base-freeze` (annotation: `Stage 4.4 angle-column two-leg moment base freeze`). Post-commit evidence records actual objects and run/job URLs externally without amendment or circular self-hashes.
