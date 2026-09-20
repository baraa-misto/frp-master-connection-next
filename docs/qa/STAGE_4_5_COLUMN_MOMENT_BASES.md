# Stage 4.5 implementation and phase-aware acceptance evidence

Product: `WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION`, `4.5-RC1`.
Baseline: `99befa9780e7c7abf72c8a33e5eb45b9e368d916`, full-history count 118.
Expected subject: `feat: add W/I RHS SRS column moment bases`; normal count 119.

This catalogue links the 120 controlled requirements to executable tests and
external phase evidence. A link is not itself an engineering PASS. Reference
fixtures are independent arithmetic, never production qualification. Production
source registries remain empty; expected missing response/capacity is explicit.

## Local verification checkpoint

The five presets and three layouts have 360 source-absent and 90 source-present
integration cases, plus 24 exact rational reference fixtures. Native Slice 7/8,
bolt and applicable local FRP comparisons use independent direct calls. Negative
qualification, real hardware collisions, contact and immutable-history tamper
cases are additional. The frontend fixture records are test-only native captures;
no test qualification is registered by production.

Complete local QA passed: 4,814 backend tests and 800 frontend tests, configured
100% line/statement/function/branch coverage, Ruff/strict mypy, ESLint/strict
TypeScript, production build, imports, pip/dependency validation, clean npm ci,
and current full/runtime npm audits with zero findings. Existing dependencies,
workflows and twelve historical tags remain unchanged.

Actual localhost browser review covered all fifteen preset/layout geometries,
all nine mode edit/invalid/recovery sequences, nine U.S.–SI fingerprint-preserving
conversions, orthogonal/X-ray/material-axis views, all five independently clickable
signed action editors, crossing bolts, oversized washers, finite containment,
source invalidation, view-only identity, design staleness and rapid recovery.
Of 224 application requests, 222 completed HTTP 200 and two superseded requests
were intentionally aborted. No console errors or runtime exceptions occurred.
Inherited Three.Clock deprecation and informational view-remount disposal logs
remain unchanged. Browser captures and request/fingerprint evidence are external.

Precommit completion, isolated QA, publication and hosted CI remain PENDING at
this checkpoint. Later outcomes are reported with actual external logs/refs.
Owner final visual/result acceptance remains PENDING; no Stage 4.5 freeze is
authorized.

Twelve historical tags and every nonregistered baseline blob are protected by the
pinned historical tree and exact seven-glue-file allowlist. The two historical
scope test changes distinguish a recorded successor from original counterfactual
probes; original digests and negative tamper tests remain in force.

## Requirement catalogue

| ID | Requirement | Executable / phase evidence | Checkpoint |
| --- | --- | --- | --- |
| T45-001 | Exact starting state | backend/tests/calculation/test_stage_4_5_scope_authority.py | PREFLIGHT VERIFIED |
| T45-002 | Twelve historical tags | backend/tests/calculation/test_stage_4_5_scope_authority.py | PREFLIGHT VERIFIED |
| T45-003 | Two-file integrity | backend/tests/calculation/test_stage_4_5_acceptance.py | PREFLIGHT VERIFIED |
| T45-004 | Applicable source review | docs/engineering/STAGE_4_5_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md | PREFLIGHT VERIFIED |
| T45-005 | No stale stage restart | backend/tests/calculation/test_stage_4_5_scope_authority.py | PREFLIGHT VERIFIED |
| T45-006 | One new physical product | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-007 | Three distinct profile families | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-008 | Nine mode combinations | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-009 | No unsupported expansion | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-010 | No unqualified capacity claim | backend/tests/application/test_column_moment_base_preview.py ; F45-14 | LOCAL QA VERIFIED |
| T45-011 | WI physical footprint | backend/tests/application/test_column_moment_base_preview.py ; F45-01 | LOCAL QA VERIFIED |
| T45-012 | Hollow footprint | backend/tests/application/test_column_moment_base_preview.py ; F45-02, F45-04, F45-17, F45-18 | LOCAL QA VERIFIED |
| T45-013 | Solid footprint | backend/tests/application/test_column_moment_base_preview.py ; F45-03, F45-05 | LOCAL QA VERIFIED |
| T45-014 | WI flange pair | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-015 | WI web pair | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-016 | WI four angles | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-017 | Box two angles | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-018 | Box four angles | backend/tests/application/test_column_moment_base_negative.py ; F45-22 | LOCAL QA VERIFIED |
| T45-019 | Fifteen constructive examples | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-020 | Prepared nominal base | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-021 | Pedestal containment | backend/tests/api/test_column_moment_base_api.py | LOCAL QA VERIFIED |
| T45-022 | Independent dimensions and deliberate locks | backend/tests/api/test_column_moment_base_api.py | LOCAL QA VERIFIED |
| T45-023 | View extents are not engineering dimensions | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-024 | Offset reference and placement | backend/tests/application/test_column_moment_base_preview.py ; F45-08, F45-09, F45-10 | LOCAL QA VERIFIED |
| T45-025 | One physical shank ID | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-026 | Hollow ordered stack | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-027 | Solid ordered stack | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-028 | WI web ordered stack | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-029 | WI flange ordered stack | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-030 | Opposite-grid mapping | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-031 | Crossing shanks rejected | backend/tests/application/test_column_moment_base_negative.py ; F45-22 | LOCAL QA VERIFIED |
| T45-032 | No silent stagger | backend/tests/application/test_column_moment_base_negative.py ; F45-22 | LOCAL QA VERIFIED |
| T45-033 | Hardware containment and access | backend/tests/api/test_column_moment_base_api.py | LOCAL QA VERIFIED |
| T45-034 | Source-bound long grip | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-035 | Unequal wall and shaft reactions | backend/tests/application/test_column_moment_base_qualified.py ; F45-21 | LOCAL QA VERIFIED |
| T45-036 | No hidden reinforcement | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-037 | Opposite connectors share only physical constraints | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-038 | Column material axes | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-039 | Angle material axes | backend/tests/application/test_column_moment_base_qualified.py ; F45-06, F45-24 | LOCAL QA VERIFIED |
| T45-040 | Foundation attachment representation | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-041 | Right-hand input convention | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-042 | Independent torsion boundary | backend/tests/api/test_column_moment_base_api.py ; F45-08, F45-09, F45-24 | LOCAL QA VERIFIED |
| T45-043 | Native centroid identity | backend/tests/application/test_column_moment_base_preview.py ; F45-01, F45-02, F45-03, F45-04, F45-05 | LOCAL QA VERIFIED |
| T45-044 | Exact total transport | backend/tests/application/test_column_moment_base_preview.py ; F45-07, F45-08, F45-09, F45-10 | LOCAL QA VERIFIED |
| T45-045 | Proper frame transforms | backend/tests/calculation/test_stage_4_5_references.py ; F45-06, F45-10, F45-24 | LOCAL QA VERIFIED |
| T45-046 | Native dependency equality | backend/tests/application/test_column_moment_base_qualified.py ; F45-11, F45-19, F45-20 | LOCAL QA VERIFIED |
| T45-047 | Proof versus serialization | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-048 | Member in-plane versus normal | backend/tests/application/test_column_moment_base_qualified.py ; F45-24 | LOCAL QA VERIFIED |
| T45-049 | Wrench reference agrees with grid | backend/tests/calculation/test_stage_4_5_references.py ; F45-19, F45-20 | LOCAL QA VERIFIED |
| T45-050 | Exact dual-unit identity | backend/tests/application/test_column_moment_base_preview.py ; F45-23 | LOCAL QA VERIFIED |
| T45-051 | Complete topology-bound source | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-052 | Missing response is explicit | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-053 | No production synthetic source | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-054 | Static balance is insufficient | backend/tests/application/test_column_moment_base_negative.py ; F45-14 | LOCAL QA VERIFIED |
| T45-055 | All active branches and direct contact | backend/tests/application/test_column_moment_base_qualified.py ; F45-12, F45-13, F45-15 | LOCAL QA VERIFIED |
| T45-056 | No dangling inactive branch | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-057 | Physical contact patches | backend/tests/application/test_column_moment_base_negative.py ; F45-15, F45-17, F45-18 | LOCAL QA VERIFIED |
| T45-058 | Contact signs and zero area | backend/tests/application/test_column_moment_base_negative.py ; F45-17, F45-18 | LOCAL QA VERIFIED |
| T45-059 | No counted-twice contact | backend/tests/application/test_column_moment_base_negative.py ; F45-15, F45-16 | LOCAL QA VERIFIED |
| T45-060 | Common bolts are coupled | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-061 | Normal and secondary bending | backend/tests/application/test_column_moment_base_negative.py ; F45-21, F45-24 | LOCAL QA VERIFIED |
| T45-062 | Source changes invalidate bindings | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-063 | Per-bolt/source ownership | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-064 | Exact ledger recovery | backend/tests/application/test_column_moment_base_qualified.py ; F45-12, F45-13, F45-15, F45-16 | LOCAL QA VERIFIED |
| T45-065 | Zero actions | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-066 | Load reversal uses new admissible state | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-067 | Response is not capacity | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-068 | All three action cases source-present | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-069 | All active Slice 7 cores | backend/tests/application/test_column_moment_base_qualified.py ; F45-11, F45-12, F45-13 | LOCAL QA VERIFIED |
| T45-070 | FRP body/instep coverage | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-071 | Native bolt strengths | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-072 | Shared physical bolt check | backend/tests/application/test_column_moment_base_qualified.py ; F45-21 | LOCAL QA VERIFIED |
| T45-073 | Actual local regions | backend/tests/application/test_column_moment_base_native_local.py | LOCAL QA VERIFIED |
| T45-074 | Local limit states retained | backend/tests/application/test_column_moment_base_native_local.py | LOCAL QA VERIFIED |
| T45-075 | End-zone interaction separate | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-076 | Full foundation remains external | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-077 | Full column remains external | backend/tests/application/test_column_moment_base_preview.py | LOCAL QA VERIFIED |
| T45-078 | Status precedence without canned FAIL | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-079 | Failure trace must explain FAIL | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-080 | Preview resistance count zero | backend/tests/api/test_column_moment_base_api.py | LOCAL QA VERIFIED |
| T45-081 | Additive integration | backend/tests/api/test_column_moment_base_api.py | LOCAL QA VERIFIED |
| T45-082 | One canonical state | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-083 | Topology selectors clear incompatible state | frontend/tests/columnMomentBaseNegative.test.tsx | LOCAL QA VERIFIED |
| T45-084 | Square and nonsquare presets | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-085 | Shared group editors | frontend/tests/columnMomentBaseNegative.test.tsx | LOCAL QA VERIFIED |
| T45-086 | Readable input groups | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-087 | Live valid load edit | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-088 | Live valid hardware edit | backend/tests/api/test_column_moment_base_api.py | LOCAL QA VERIFIED |
| T45-089 | Prominent invalid LAST VALID | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-090 | Automatic recovery | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-091 | Input parsing and intermediate edits | frontend/tests/columnMomentBaseNegative.test.tsx | LOCAL QA VERIFIED |
| T45-092 | Request race protection | frontend/tests/columnMomentBaseNegative.test.tsx | LOCAL QA VERIFIED |
| T45-093 | Presentation-only edits | frontend/tests/columnMomentBaseNegative.test.tsx | LOCAL QA VERIFIED |
| T45-094 | Source absence usable | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-095 | Source-present readable trace | frontend/tests/columnMomentBaseNegative.test.tsx | LOCAL QA VERIFIED |
| T45-096 | Scene color/type identity | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-097 | Hardware X-ray and views | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-098 | Action labels editable and clear | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-099 | No fictitious anchors/contact graphics | frontend/tests/columnMomentBase.test.tsx | LOCAL QA VERIFIED |
| T45-100 | Independent real-browser evidence | External real-browser evidence | LOCAL BROWSER VERIFIED; owner acceptance PENDING |
| T45-101 | Twenty-four independent fixtures | backend/tests/calculation/test_stage_4_5_references.py ; F45-01, F45-02, F45-03, F45-04, F45-05, F45-06, F45-07, F45-08, F45-09, F45-10, F45-11, F45-12, F45-13, F45-14, F45-15, F45-16, F45-17, F45-18, F45-19, F45-20, F45-21, F45-22, F45-23, F45-24 | LOCAL QA VERIFIED |
| T45-102 | 360 source-absent integrations | backend/tests/application/test_column_moment_base_preview.py::test_360_source_absent_sweep | LOCAL QA VERIFIED |
| T45-103 | 90 source-present integrations | backend/tests/application/test_column_moment_base_qualified.py::test_90_source_present_integrations | LOCAL QA VERIFIED |
| T45-104 | Normal source negative tests | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-105 | Real-native integration oracles | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-106 | Native capacity failure visible | backend/tests/application/test_column_moment_base_negative.py | LOCAL QA VERIFIED |
| T45-107 | Zero and degenerate group coverage | backend/tests/application/test_column_moment_base_native_local.py | LOCAL QA VERIFIED |
| T45-108 | Display-unit and permutation invariance | backend/tests/application/test_column_moment_base_qualified.py | LOCAL QA VERIFIED |
| T45-109 | Preflight all legacy patterns | backend/tests/calculation/test_stage_4_5_scope_authority.py | PREFLIGHT VERIFIED |
| T45-110 | No silent coverage loss | External complete QA logs | LOCAL QA VERIFIED |
| T45-111 | Historical/source guard successor safety | backend/tests/calculation/test_stage_4_5_scope_authority.py | LOCAL QA VERIFIED |
| T45-112 | Scope inventory and historical blobs | backend/tests/calculation/test_stage_4_5_scope_authority.py | LOCAL QA VERIFIED |
| T45-113 | No licensed/generated artifacts | backend/tests/calculation/test_stage_4_5_scope_authority.py | LOCAL QA VERIFIED |
| T45-114 | Bounded timing and environment handling | Conditional maintenance log | NOT NEEDED at checkpoint; bounded conditions remain |
| T45-115 | Precommit checkpoint | backend/tests/calculation/test_stage_4_5_scope_authority.py | PENDING — PRECOMMIT |
| T45-116 | Correct commit lineage | Git commit/lineage evidence | PENDING — COMMIT |
| T45-117 | True object-isolated verification | External fresh isolated-clone QA | PENDING — OBJECT_ISOLATED |
| T45-118 | Authorized exact destination push | Git remote/ref evidence | PENDING — PUBLICATION |
| T45-119 | Direct hosted acceptance | Direct four-job hosted CI | PENDING — HOSTED_CI |
| T45-120 | Owner acceptance remains pending | Owner review | PENDING — OWNER_REVIEW |

## Completion boundaries

No concrete/anchor capacity, full-column stability, stiffness, rotation or
full-strength classification is claimed. No equal branch/wall allocation is
inferred. An accepted complete test response is not a production source. Every
shared shank is checked using its source-defined physical layer/section actions,
not two independent or automatically doubled capacities. Unqualified long-shank,
solid-section, coupled normal/prying and end-zone checks remain source-limited.

External evidence must retain the active/isolated paths, process IDs, exact
candidate and refs, audit timestamps, runtime requests/console observations,
all fifteen preset/layout browser captures and all nine mode edit/recovery
checks. Postcommit phases cannot truthfully be embedded as already passed in the
same candidate. The final handoff supplies those direct observations.

## Owner-review successor: UI/defaults/action binding R1

Authority: `FRP_MASTER_CONNECTION_STAGE_4_5_UI_DEFAULTS_AND_ACTION_RENDERING_CORRECTION_ORDER_R1.md`,
SHA-256 `06EEA4B207E55763C522622F148938EA5F006C51124B33CD8A532A06C07B693C`.
Starting implementation: `45d4a13590f4551926cae5762982284dfd6dc591`, count 119.

The earlier named-preset UI description is historical. Production now has separate
U.S. Units/S.I. Units, three generic column-shape choices and the existing three
layout choices. Named engineering fixtures remain unchanged and explicitly
addressable for regression. Generic backend defaults use 3x1 member bolts and 1x1
foundation attachments. W/I flange-angle references start 3 in beside the web
with 1.5 in bolt gauge: a centered odd flange row would intersect the web.
No bolt-path, interference, demand, capacity or sharing rule was relaxed.
Irrelevant pitch/gauge controls are disabled/N/A and reactivate with their counts.

The reported +Vy-to-negative-label defect did not reproduce in the clean
implementation baseline: the owner fixture rendered +4.00 kip. No sign-reversing
operation was found in the shared renderer. R1 binds the five Stage 4.5 action
arrows directly to the returned column-on-base wrench rather than the request
echo. Backend signs and the renderer remain unchanged. This is not a claim that
an unreproduced sign-inversion root cause was established.

Local complete QA: **4,958 backend / 846 frontend tests passed**, configured
coverage 100%, Ruff/strict mypy/ESLint/strict TypeScript/build and full/runtime
security audits passed (zero vulnerabilities). The 120 acceptance requirements,
24 references, 360 source-absent cases, 90 source-present integrations, inherited
engines and twelve freeze audits remain in the suite. Original acceptance JSON
and engineering fixtures have not been re-goldened.

New native API coverage includes nine generic defaults/round-trips and 135
positive/negative/zero action cases. Forty-five real-panel tests cover the five
components in all nine layouts; another verifies the exact control choices and
count-aware spacing. The historical scope inventory registers this exact new
test path without changing the immutable evidence digest or tamper assertions.

Browser review passed all nine layouts: generic hardware, exact unit round-trip
fingerprints, positive/negative Vy, valid geometry/spacing/location edits,
invalid LAST VALID hidden actions and automatic recovery. W/I/RHS/SRS X-ray
hardware views were inspected. The owner N=30, Vx=-10, Vy=4, Mx=-50, My=30 fixture
showed +4.00 kip and the matching backend wrench. Explicit design remained
SOURCE_REQUIRED with no resistance on unresolved branch demand. Runtime capture:
307 responses, no HTTP errors, no runtime exceptions or console errors; three
intentional superseded-request cancellations.

Commit/object-isolated/push/hosted-CI outcomes are recorded externally after this
checkpoint; they are not inferred here. Owner final visual/result acceptance
remains required. No Stage 4.5 freeze or later-family work is authorized.

## R2 centered two-bolt generic defaults

Owner order SHA-256:
`4E9663E11EE3654FC5B46FC1D28BD68D10ACEA4F30418DF41906911C4A024D58`.
R2 supersedes R1's three-bolt and displaced W/I flange-angle generic defaults.
Every generic active angle now initializes with two across / one along member
bolts, a 3 in gauge, zero tangential center offset and one foundation attachment.
Historical named engineering fixtures remain unchanged.

The existing native placement already centers the extrusion at the selected
face's tangential midline, including column X/Y translation; zero is not an edge
or global-origin reference. R1's explicit 3 in W/I flange offset was the cause of
the shifted default. With two bolts the 3 in gauge straddles the web, so this
offset is removed. No compensating scene translation is used. Signed user
offsets move the angle, its bolts and its foundation attachment coherently.

The native selected-face contact bounds now also reject an overlong extrusion.
The R2 invalid-input audit found RHS/SRS could previously pass when the holes fit
but the angle extended beyond its face. The narrow guard rejects this condition
without auto-shifting the angle or changing valid geometry or native mechanics.

Regression coverage includes all nine modes, translated columns, positive/zero/
negative offsets, solid midpoints/extents, two symmetric bolt locations, shared
bindings, one-anchor alignment, perpendicular clearances, exact U.S./SI geometry
identity and API unit round-trips, overlong rejection and recovery. The existing
action-sign and LAST VALID/request-sequencing suites remain controlling.

Unique physical member-shank counts for TWO_X / TWO_Y / FOUR_XY are 2/4/6 for W/I
and 2/2/4 for RHS/SRS. Shared opposite-face bindings give every active angle two
bolts without duplicate shanks. Foundation counts remain 2/2/4. Geometry linking
does not create load-sharing, anchor strength or complete-base-response authority.

No controlled acceptance JSON, historical golden, source, material, factor,
dependency, lockfile, workflow or freeze-tag identity changes are required.
The original 120 requirements, 24 references, 360 source-absent cases and 90
source-present integrations are retained. Final complete QA, browser, isolated,
publication and hosted-CI evidence is recorded in the external R2 completion
report. Owner final visual/result acceptance remains required; no freeze follows
automatically.
