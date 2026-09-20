# Stage 4.2 post-implementation sidebar and result-traceability correction

## Authority and baseline

The owner's pasted correction order (SHA-256 B3B9B434A455C88CC9B002AB46F82A77149DB4395E9698246A6D584D74AFC6BD) and four owner screenshots control this narrow successor. The initial worktree was clean on main; HEAD, origin/main and remote main were 2886daab9d736926ba78fc9c6c44c652321756d1, count 107. The accepted implementation is not amended. Hosted run 102 attempt 1 was accepted 4/4; owner visual/result acceptance remains open.

## Reproduction before mutation

The existing localhost application was inspected in the Codex built-in browser with CDP Network capture. A fresh U.S. loader followed by P=0 kip, V=-10 kip, M=0 kip-in and explicit Run Design Check reproduced FAIL, no selected native group and an empty displayed failure table. A second run of combined default followed by the same edits and explicit design returned a byte-for-byte identical parsed response. The combined result became stale and its design table disappeared immediately after the edits. No stale-result mixing was found.

The exact pure-shear request and complete raw response are retained in the local correction evidence artifact. All default geometry, locked ICE material, factors, F593 source boundary and empty source references were unchanged. Native checks report eight actual bearing failures:

- BEARING:POSITIVE_WEB_ANGLE:B_R1_L1 and B_R1_L2: utilization 1.07311973748191748388197062673731430724742284426503135126756.
- BEARING:NEGATIVE_WEB_ANGLE:B_R1_L1 and B_R1_L2: the same utilization.
- BEARING:WI_WEB:COMMON_WEB:B_R1_L1 and B_R1_L2: utilization 2.14623947496383496776394125347462861449484568853006270253511.
- BEARING:WI_WEB:COMMON_WEB:B_R2_L1 and B_R2_L2: utilization 1.32712061700387648598627378276605286109208169639647298566857.

Each native design resistance is 9007.6487709025125 N (2.025 kip). First-row beam-web demand is 19332.571368720441796010153188557050696087821695066901829982748353838959275209499 N. The two web instep checks pass (native utilization 0.22321428571428571428571428571428571428571428571428571428571428571428571428571429); web qualified connector/attachment sources remain SOURCE_REQUIRED. Zero-demand flange sources are NOT_REQUIRED_ZERO_DEMAND. Common-bolt F593 strength remains NOT_EVALUATED / SOURCE_AUTHORIZED_FNV_REQUIRED.

## First inconsistent boundary and correction

The native design aggregator already includes web/flange bearing, provider, attachment, common-bolt and local-group statuses. Its `native_failed_checks` and `native_governing_check_ids` are specifically the group-mode subset. The complete response also contains `web_bearing` and the other native categories. The first inconsistent boundary was the frontend treating the group-mode subset as the entire required-failure display. It ignored eight genuine failures that supported the backend aggregate FAIL, while joining an empty group-selection array into blank text.

The frontend now projects all returned failure categories into the display, retains native identifiers/component/reasons and available demand/design resistance, and offers each exact native record. Qualified full-wrench terms and common-bolt vectors remain in their native records; the display does not invent scalar demand, select a new governing check, calculate a resistance or compare utilization. A native aggregate failure without an individual record has an explicit native-reason row rather than an empty numerical table. No-failure responses show an explicit empty state. Missing sources remain visible and do not override a genuine evaluated failure. Strict transport guards reject missing/malformed failure categories.

The native governing group is unchanged. In pure shear it is explicitly described as not selected by the native group-mode engine; it is not replaced by a frontend maximum-utilization selection. Combined default retains FIRST_ROW:TOP_FLANGE_ANGLE and the original ordered 15 group-mode failure records; other actual failed categories are additionally visible.

The sidebar defect was intrinsic-width fieldsets placed alongside individual geometry cells in one compact grid. Geometry now occupies its own grid. Member bolts and wall anchors are separate full-width sibling fieldsets with their respective dimensions/counts/hardware fields; thread condition belongs to member bolts. Qualified references are full-width sibling controls. Exposed labels use Member bolts / Wall anchors gauge, pitch and centroid distance rather than implementation keys. State keys, exact quantities, units, validation and locked partner copies are unchanged. CSS is scoped to `.wi-wall-moment-workspace`; shared CSS is untouched.

## Exact identities and protected scope

Pure-shear backend status before/after is FAIL, reason EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE. No result-fingerprint transition is authorized or necessary:

| Case | Engineering fingerprint | Result fingerprint |
| --- | --- | --- |
| Combined | 4629228f806f8ec9e80c24eca9ee3c33b22dab5f3195eea75490772c94fd0624 | d2d041e7a76fababe8b6eef72ee3e7675d2c045e55d608bcd3dd415f3a87a9a9 |
| Pure shear | 76ad0f326eacec1c7ae7ddce981e94b235d3ff24fadf548e4f83e84f41be6968 | dc758641c2f59866c9ccc3f92d1d7bf13dba8fac6a7199b581105ca72534e4f1 |

All backend production source is byte-identical to the accepted implementation, including API serialization and product aggregation. CS5/7/8, Stage 2.5A, all native demand/resistance/governing selection, material/factors/geometry/wrenches/qualification/external-anchor boundaries remain unchanged. No controlled artifact, golden, dependency, lockfile, workflow, freeze manifest or tag is changed. The targeted Windows timeout and all prior test assertions are preserved. Both frontend response fixtures are verified as exact subsets of independent native backend responses, not new engineering goldens.

## Local verification and browser evidence

Complete local backend QA passed: locked installation and dependency check, Ruff formatting/lint, strict mypy, 3,253 tests, 100% statement/branch coverage, runtime imports and command smoke checks. This includes Stage 4.2 G1–G128, CS5/7/8, Stage 2.5A, historical and successor-safe freeze regressions. Complete frontend QA passed: npm ci/ls, ESLint, strict TypeScript, 623 tests in 44 files, configured 100% coverage, production build and full/production npm audits with zero vulnerabilities. The same complete frontend suite passed again after the final responsive CSS corrections.

The Codex built-in browser/CDP matrix confirmed:

- Combined U.S. and SI defaults: identical engineering/result fingerprints; FAIL and FIRST_ROW:TOP_FLANGE_ANGLE preserved.
- Fresh pure shear and combined-to-pure-shear: exact current raw-response equality with the pre-correction response, eight visible bearing failures and explicit no-native-group explanation. Prior design results become stale after edits; no automatic design request occurs.
- Pure moment: FAIL, top/bottom first-row groups and 32 visible failure records. Sign reversal: FAIL with 21 visible records. Small source-only shear: SOURCE_REQUIRED, explicit no-evaluated-failures message and remaining sources visible.
- Invalid zero beam-wall gap: native POSITIVE_BEAM_WALL_GAP_REQUIRED, retained last valid canvas, no current design trace and disabled design action.
- Deliberately CDP-blocked preview and design requests: visible service error, no fabricated/current replacement result, recovery after unblocking and explicit retry. Both blocks were removed.
- 1280-pixel and 1024-pixel desktop viewports, including the 290-pixel sidebar, and temporary 125% page zoom: full-width member/anchor groups, readable decimal inputs, full-width references, no sidebar/page horizontal overflow. Both Flange angles and Web clip angles were inspected. Scoped unit padding and long-fingerprint wrapping corrected issues found during this check. Zoom and viewport overrides were restored.
- Front/Top/Side 1/Side 2/3D/Fit/Reset navigation: no application requests and no stale design. One live canvas, no blank root or Runtime.exceptionThrown. Captured failed requests were one expected abort of a superseded request and the two intentional inspector blocks; no unexplained application-request failure occurred.

Local evidence includes full pre-correction raw request/response capture and verified screenshots of both narrow input sections and the complete pure-shear failure table. Existing Three.Clock deprecation and bundle-size warnings are unchanged.

## Publication gates

Focused coverage includes input grouping and exact mirrored payloads, real pure-shear native failures, source-only status, explicit aggregate reasons, malformed transport, stale results and an old design response arriving after the current pure-shear response. Full local QA, responsive/zoom browser matrix, object-isolated QA and hosted evidence are recorded at completion. Configured 100% coverage remains mandatory; it is not weakened. Publication requires one successor commit named `fix: correct wall moment sidebar and result traceability`, final count 108, normal non-force main push, no tags. The final report supplies the committed hash, isolated checkout and direct four-job CI evidence without amending the commit.

Stage 4.2 remains open for owner visual/result acceptance. No freeze, 316SS or later family is begun.
