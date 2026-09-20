# FRP Master Connection

## Current milestone: CME-3 conditional public connector-body activation

Accepted implementation `d790aacf643a265a839f8ae39051e70915fe5d54` (133) exposes FRP / 316 Stainless Steel on thirteen body-bearing routes; the three no-body routes remain unchanged. [Freeze record](docs/governance/CME_3_316SS_PUBLIC_ACTIVATION_FREEZE.md) pins all sixteen routes/thirty-nine bodies, exact native FRP compatibility, frozen C2 providers and implementation-targeted tag `cme-3-316ss-connector-body-activation-freeze`. Selection is conditional, not universal numerical coverage: unqualified response, product, section, stability and local mechanisms remain fail closed. Primary members remain FRP-only; hardware and foundation remain independent. Earlier milestone descriptions below are historical. Governance publication and exact-SHA CI remain separate required gates.

## Current milestone: CME-2 core isolated provider freeze

Accepted implementation `1d730c70bc446901452f2eacecd9df3f9f36ff4b` (131) is the target of annotated tag `cme-2-core-r-a-t-freeze`, not the governance successor. [Freeze record](docs/governance/CME_2_CORE_R_A_T_FREEZE.md) pins the accepted 24/27/16 authority, owner-corrected I11, response/product boundaries and publication gates. Public stainless family activation and CME-3 remain excluded; primary members remain FRP-only. Earlier milestone/pending descriptions below are historical.

## Current work: isolated CME-2 core

Internal C2-R response envelopes and C2-A/C2-T hot-shape providers are additive only. [Scope, sources and owner I11 clarification](docs/architecture/CME_2_CORE_ISOLATED_RESPONSE_ANGLE_TEE.md) preserve frozen FRP/C2-M/P1/P2 behavior. Public stainless families remain unavailable; no CME-3 activation is included. Implementation publication, read-only acceptance and conditional freeze have separate mandatory QA/CI gates.

## Current milestone: CME-2C isolated C2-P2 freeze

Accepted implementation `61855bda1f76bbf11a85ae58664ed81bbc8ea419` (129) is the target of annotated tag `cme-2c-c2-p2-freeze`, not the later governance commit. [Freeze record](docs/governance/CME_2C_C2_P2_FREEZE.md) pins acceptance, numerical authority, immutable artifacts and publication gates.

Only the isolated C2-P2 clear-body provider is frozen. Public SS316 family dispatch remains unavailable; primary members remain FRP-only. C2-R/A/T and CME-3 implementation are excluded. The combined order permits only a read-only core-readiness audit after exact-governance-SHA hosted CI passes. Earlier milestone descriptions below are historical.

## Current milestone: CME-2B isolated provider freeze

CME-2B C2-M/C2-P1 is owner accepted at `7ef49bdbf8b9704af3d314735963069ddf7259f3` (127), with annotated tag `cme-2b-c2-m-c2-p1-freeze` targeting that implementation, not this documentation successor. [Freeze record](docs/governance/CME_2B_C2_M_C2_P1_FREEZE.md) records the exact authority and publication gates.

This freezes only the conservative material contract and isolated RC1 R1 flat-plate provider. Structural members remain FRP-only; public SS316 family dispatch remains unavailable. Hardware/foundation authority is independent. C2-P2/R/A/T, CME-3 and family activation are excluded. Earlier implementation/pending descriptions below are historical; this milestone does not claim governance CI before direct verification.


## Current milestone: isolated CME-2B C2-M/C2-P1 implementation

The internal conservative 316 stainless material catalogue and bounded flat-plate LRFD provider are implemented under RC1 R1. [Architecture and limits](docs/architecture/CME_2B_ISOLATED_STAINLESS_PLATE_PROVIDER.md) and [validation requirements](docs/qa/CME_2B_VALIDATION.md) define this development/draft scope. No existing family is stainless-enabled; public CME-1 readiness, all FRP behavior and fourteen historical freeze tags remain unchanged. C2-R/P2/A/T and CME-3 are not implemented. Final local/hosted publication evidence is recorded externally for the exact implementation commit.

## Historical milestone: CME-1 foundation frozen

CME-1 is owner accepted and frozen at `d62064a7d96ba139841c222f90b62b8e7c4601c8` (125 commits), tagged `cme-1-connector-material-extension-freeze`. See [the controlled freeze record](docs/governance/CME_1_CONNECTOR_MATERIAL_EXTENSION_FREEZE.md) for scope, acceptance closure and immutable authority.

This freezes the shared connector-material foundation, not the whole product. Native FRP behavior remains exact; structural members are FRP-only and SS316 numerical resistance is not implemented. CME-2 is the next engineering stage, subject to separate approval after owner verification of this governance commit's hosted CI. Earlier dated stage/pending descriptions below are historical and do not override this current milestone.


## Stage 4.4 RC1 current successor

`ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION` / `4.4-RC1` starts from
`1faa1ff522d0e0a39a42e2dc2d3974b5dba98479` (114 commits). Equal and unequal
FRP Angle columns each have exactly two independent FRP base angles, one on each
different leg, with actual member bolts and separate foundation attachment groups.

One new product uses the accepted Angle geometry, material-neutral Slice 7 core/FRP provider and Slice 8 native in-plane demand. Source-limited branch allocation remains explicit; total required foundation actions are available without invented connector or anchor response. Historical frozen families are unchanged.

See [native integration/source boundaries](docs/engineering/STAGE_4_4_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md)
and [96-requirement QA catalogue](docs/qa/STAGE_4_4_ANGLE_COLUMN_MOMENT_BASE.md).
The exact implementation subject is `feat: add angle-column two-leg moment base connection`;
normal expected count 115. Local, browser and fresh object-isolated QA precede the
normal non-force main push; direct four-job CI follows it. Future CI is not inferred.
All eleven existing freeze tags remain immutable. Owner final visual/result acceptance
is PENDING; no Stage 4.4 freeze, Stage 4.5 or 316SS expansion is authorized.

Stage 4.2 adds the W/I Beam to Concrete Wall Moment Connection under Moment
Connections. Four FRP angles retain complete Slice 5 component wrenches and use
the accepted material-neutral Slice 7 core. Flanges consume native Stage 2.5A
demand; both web groups consume Slice 8's independent-moment demand verbatim.
Preview never runs resistance. Run Design Check is explicit. The locked default
is **FAIL**, governed natively by `FIRST_ROW:TOP_FLANGE_ANGLE`; bearing and
inter-row failures and missing qualified sources remain visible. Concrete/anchor
design always remains external. No 316SS provider or later family is implemented.
See the [Stage 4.2 implementation and verification record](docs/qa/STAGE_4_2_IMPLEMENTATION_AND_VERIFICATION_RC1_R7.md)
for the historical implementation gates. The corrected product baseline
`1dee177a02bcaec713c1e3f597b053790ff7337e` is owner accepted with hosted CI #103,
attempt 1, four jobs green. The [Stage 4.2 freeze record](docs/qa/STAGE_4_2_FREEZE.md)
registers the governance-only freeze and its publication/tag gates. Stage 4.3 and
316SS remain future, separately authorized scope.

> **Current safety notice**
>
> - This repository is separate from FRP Master Pro.
> - The Stage 0.1 foundation, Stage 0.2.1 compatibility evidence, and Stage 0.2.2 backend foundation are committed.
> - Stage 0.2.3 implementation is complete and reviewed, validation passed, and the
>   noncalculating frontend shell is provisionally accepted as the frontend application
>   foundation.
> - Stage 0.2.4 integrated repository QA/CI is implemented, pushed, and confirmed by
>   one successful four-job hosted GitHub Actions run.
> - Stage 1.1 hosted CI succeeded for commit
>   `95f469907139a6bc1a365dd42675300384623347`: four of four jobs passed in
>   1 minute 32 seconds with no artifacts.
> - Stage 1.2 is committed at `9de91c81681ebd14e136dfd8ec3470b3a0c20d18`;
>   the user verified all four hosted backend/frontend Ubuntu/Windows jobs green. The
>   run duration and artifact status were not supplied.
> - Stage 1.3A framework-independent spatial mathematics, resolved Cartesian frames,
>   force/moment transformations, explicit reference-point shifting, connected-end
>   axial interpretation, and renderer-neutral direction/inspection contracts are
>   implemented and locally validated. The user verified all four hosted
>   backend/frontend Ubuntu 24.04/Windows 2025 jobs green; exact duration and artifact
>   status were not supplied.
> - Stage 1.3B exact nominal two-dimensional standard cross-section geometry,
>   physical-element geometry, outside-bounds datum, deferred non-targetable
>   heel/corner/junction features, and analytic round-tube annuli are implemented.
>   Focused and full local validation passed. The user verified all four hosted
>   backend/frontend Ubuntu 24.04/Windows 2025 jobs green; exact duration and
>   artifact status were not supplied.
> - Stage 1.3C1 framework-independent member/connector placement, explicit section
>   offsets and longitudinal extents, exact analytic extrusion, physical longitudinal
>   boundary planes, and connected-member-end plane identification are implemented.
>   Hosted commit `080632786f963173f7c3ebeaf7981e9e09575709` passed all four
>   backend/frontend Ubuntu 24.04/Windows 2025 jobs in 1 minute 25 seconds with no
>   artifacts.
> - Stage 1.3C2A exact physical surface patches, element-level end cuts, analytic
>   round-tube surfaces, derived geometric targetability, stable participant-scoped
>   references, and explicit bounded planar support surfaces are implemented in the
>   framework-independent backend core. The complete integrated repository and
>   independent backend gates passed; hosted commit
>   `5e33db84e9efaf98fb5269b6df047be609c24506` passed all four jobs in
>   1 minute 25 seconds with no artifacts.
> - Stage 1.3C2B geometry-only planar interface targeting, bounded whole-patch and
>   rectangular-subzone connection zones, multi-patch target sides, explicit
>   comparison tolerance and interface origin, interface-local frames, raw signed
>   plane separation, and bounded support-surface targeting are implemented. The
>   backend suite passes 744 tests with 100% statement and branch coverage; integrated
>   and independent backend gates pass.
> - Stage 1.3C2B hosted commit
>   `2808348f44d308a4ddb30db0b2f89dc01e706da1` passed backend and frontend on
>   Ubuntu 24.04 and Windows 2025 in 1 minute 53 seconds with no artifacts.
> - Stage 1.3C3 exact surface roles, staged joint geometry context, bolt-group frames,
>   master centers and axes, round-hole cylinders, intended penetrated layers, ordered
>   path stacks, physical reference-point resolution, manual-action spatial resolution,
>   and explicit eccentricity transforms are implemented. The backend suite passed
>   804 tests with 100% statement and branch coverage. Hosted commit
>   6ce3f5f06f14d8e4f29410d7ef7ba9b61e557b75 passed all four backend/frontend
>   Ubuntu 24.04/Windows 2025 jobs in 1 minute 21 seconds with no artifacts.
> - Stage 2.1A calculation contracts now provide exact dual-unit quantities,
>   source/material/fastener snapshots, resolved demand, C3 geometry-to-code mapping,
>   applicability/readiness and aggregate statuses, canonical fingerprints, the RC2
>   golden fixture, and an original non-executable equation catalog. Its hosted commit
>   `1804a6ff1a963966357b975c7d2d975a5e731a35` passed all four Ubuntu/Windows jobs
>   in 1 minute 22 seconds with no artifacts.
> - Stage 2.1B implements the authorized framework-independent single-bolt resistance
>   equations, immutable equation traces and final results, exact comparison and
>   aggregation, RC2 golden numerical verification, and exact U.S./SI equivalence.
>   Engine `0.1.0.dev1` and rule set `asce74-23-ch8-single-bolt-rc2.dev1` remain draft;
>   hosted commit `4931c201222816119fc1871fb4dce70d2f5d7afe` passed all four
>   backend/frontend Ubuntu 24.04 and Windows 2025 jobs in 1 minute 48 seconds with no
>   artifacts.
> - Stage 2.2A implements a framework-independent canonical orchestration service for
>   one explicitly selected bolt. It resolves exact assembly/context, interface,
>   bolt-path, material, fastener, combination, geometry, and explicit-demand inputs
>   into the unchanged Stage 2.1A/2.1B engine and fails closed when distribution is
>   unavailable.
>   Hosted commit `31b4785c88bb0b3564b7db9cc00b7206e3d2daa2` passed all four
>   backend/frontend Ubuntu 24.04 and Windows 2025 jobs in 1 minute 33 seconds with no
>   artifacts.
> - Stage 2.2B exposes that exact service through one trusted, strict, stateless
>   `POST /api/v1/calculations/single-bolt/evaluate` endpoint. It reconstructs the
>   canonical object graph, calls orchestration once, returns engineering FAIL,
>   unsupported, review, qualification, and source-pending outcomes as HTTP 200, and
>   stores nothing. Local gates passed 1,027 backend tests with 100% statement/branch
>   coverage and retained the unchanged 35-test, 100%-covered frontend gate. The user
>   verified all four hosted backend/frontend Ubuntu/Windows jobs successful in
>   1 minute 27 seconds with no artifacts.
> - Stage 2.3 implements the first session-only interactive Shear workspace and
>   canonical Three.js visualization for that same verified single-bolt/single-row
>   slice. The backend response now includes a renderer-neutral geometry/frame/axis/
>   reference/action snapshot. J1 U.S. and SI loaders, editable supported inputs,
>   explicit/member-end demand modes, result summary/table/trace, four camera views,
>   and accessible inspectors are implemented and locally validated.
> - Stage 2.3R refines that same workspace with a properly rotated vertical J1 W
>   column and diagonal brace, solid role colors, a large connection-first viewer,
>   grouped sidebar inputs, compact results, clean overlay defaults, unit-independent
>   fit, presentation-only number formatting, and engineer-friendly labels with
>   stable IDs retained in diagnostics. Desktop and narrow-width browser acceptance
>   passed. It changes no equation or golden value.
> - Stage 2.3R2 makes the narrow brace-to-column-flange template geometry
>   backend-authoritative and exposes an acute, sign-independent brace-to-column
>   angle (default 45 degrees), local W-column extents above and below the fixed
>   connection station, and brace segment length. The default W segment is roughly
>   four times longer than Stage 2.3R, the plan angle remains fixed at 0 degrees, and
>   exact-known shank/washer geometry is shown without fabricating bolt hardware.
>   Stage 2.3R's Ubuntu failure was a test-only exact-zero assertion on harmless
>   floating-point rotation residue; Stage 2.3R2 uses the approved dimensionless
>   mathematical tolerance in that assertion and does not clamp production geometry.
>   Hosted Stage 2.3R2 commit `a28f83c2f124c3dcd994de250a1de962ef8ff72f`
>   then failed only Backend / Ubuntu 24.04 because a derived dimensional bolt-center
>   point was compared as exact serialized strings; the other three jobs passed in the
>   1 minute 58 second run. The narrow correction uses a test-only machine-roundoff
>   point comparator and makes no production geometry change. The user verified
>   correction commit `c2114fbb2b4c3c99568669407b97aa1b944cd75b` with all four jobs
>   green in 1 minute 54 seconds and no artifacts.
> - Stage 2.3R3 commit `e3011ec3919a8c0fce25d49a9938c0fda2fcbd3d` passed all four
>   hosted backend/frontend Ubuntu 24.04/Windows 2025 jobs in 1 minute 49 seconds with
>   no artifacts. Stage 2.3R4 corrects the viewport orbit/pan freeze with one controls
>   lifecycle, direct corner-triad updates, pointer-transparent static overlays, and
>   click-versus-drag gesture isolation. Navigation is presentation-only; physical
>   geometry remains editable through controlled inputs, never direct member dragging,
>   and calculations are unchanged.
> - The Stage 2.3 interface and geometry foundation is scope-frozen at hosted-CI-green
>   Stage 2.3R8 commit `5bc545ab8251f9bd49dedc776962937ed5e822a2` by annotated tag
>   `stage-2.3-interface-geometry-freeze`. All four hosted backend/frontend jobs passed
>   in 2 minutes 23 seconds, with 123 frontend tests on both platforms and no artifacts.
>   This is not a product-wide freeze or a production release; future controlled
>   engineering development continues.
> - Stage 2.4C-R2 retains the verified Slice 2 multi-row engine through pure
>   application orchestration, exactly two strict stateless API operations, and the
>   existing session-only Shear connection workspace. Preview executes zero resistance equations;
>   only explicit **Run Design Check** calls the Stage 2.4B engine. Connection demand
>   is externally resolved: no member-end transformation, automatic bolt-demand
>   distribution, friction credit, or generated prying is provided. The prior separate
>   multi-row workspace was visually rejected; row/bolt controls and every physical
>   bolt now use the same canonical 3D connection view. The exact R1 commit passed all
>   four hosted jobs in 2 minutes 54 seconds with 167 frontend tests. R2 makes
>   canonical bolt/hole scaling visible and adds exact opposing
>   Side 1/Side 2 views; R2 hosted CI and user post-push visual acceptance remain pending.
> - Stage 3.1 establishes the backend-only connection-platform material architecture:
>   exact connector and fastener material families, material-behavior identity,
>   immutable engineering-property provenance, resistance-authority capability,
>   connector/fastener assignments, minimal connection-assembly scaffolding, and a
>   strict adapter into the unchanged Stage 2 `FRP_FRP` and `FRP_STEEL` pair meanings.
>   A stainless- or carbon-steel identity supplies no default grade or strength, and a
>   custom FRP fastener is always prohibited from the existing metallic-bolt path; any
>   future custom-FRP resistance requires its own approved method and authority. Full
>   local QA passes; isolated committed-state verification, push, and hosted CI remain
>   pending, and no hosted success is claimed.
> - No project storage, whole-connection calculation, Moment workflow, report,
>   automatic bolt-demand distribution, friction credit, or generated prying exists.
> - This repository remains unusable as an engineering design tool.
> - No output may be represented as a validated engineering design result.
> - Only authorized calculated `READY` checks may return `PASS` or `FAIL`;
>   placeholder and unavailable work remains `NOT_EVALUATED`.

FRP Master Connection is the controlled foundation for an original web-based engineering calculation, visualization, documentation, and reporting product for pultruded FRP structural connections. The intended final delivery is an authenticated, paid service reached through the Masters Engineering Solutions website and Client Login.

## Current stage

Stage 0.1 through Stage 1.3C1 established the controlled repository, software
foundation, domain/spatial/section/placement contracts, and exact extrusion. Stage
1.3C2A added exact renderer-neutral physical surface patches for all supported placed
standard shapes, stable participant-scoped references, source/exposure/disposition,
derived targetability, element-level end cuts, analytic round-tube cylinders/annular
ends, and explicit bounded planar support surfaces; hosted commit
`5e33db84e9efaf98fb5269b6df047be609c24506` passed all four jobs in 1 minute
25 seconds with no artifacts. Stage 1.3C2B now adds planar interface targeting while
preserving the logical `ConnectionInterface`: bounded whole-patch and rectangular
subzones, participant-safe multi-patch target sides, explicit origin and in-plane
reference, a proper interface-local frame, explicit distance/angular comparison
tolerance, raw signed plane separation, and support-surface targeting. Its hosted
commit `2808348f44d308a4ddb30db0b2f89dc01e706da1` passed all four jobs in
1 minute 53 seconds with no artifacts. Stage 1.3C3 completes the Stage 1.3 geometry
foundation with explicit surface roles, a complete staged in-memory joint geometry
context, bolt paths/holes/layers, physical reference-point resolution, and fully
explicit action/eccentricity transforms.

The production toolchain and deployment are not approved or frozen. Stage 2.1A
calculation contracts/applicability and the narrow Stage 2.1B single-bolt numerical
engine and Stage 2.2A orchestration are implemented and hosted-CI verified. Stage 2.2B
adds the stateless backend transport for that same single-bolt/single-row scope and its
hosted four-job run was user-verified successful. Stage 2.3 adds a session-only
interactive Shear workspace, a same-origin typed API client, and canonical 3D/Front/
Top/Side visualization from a backend renderer-neutral snapshot; hosted commit
`afa0add74f9315c62c1223e55ebf4febfda95bfa` passed all four jobs in 1 minute
43 seconds with no artifacts. Stage 2.3R refines the same workspace and corrects the
J1 visual orientation without changing the verified engineering result. Its Ubuntu
hosted job exposed a test-only exact-zero comparison while both Windows backend and
both frontend jobs passed; Stage 2.3R2 corrects that assertion without production
clamping. Stage 2.3R2 also adds backend-resolved template angle and local extent
controls while preserving the 45-degree J1 Q12 results, qualification, governing
check, and engineering limitations. Hosted Stage 2.3R2 commit
`a28f83c2f124c3dcd994de250a1de962ef8ff72f` failed only Backend / Ubuntu 24.04 on
an exact serialized derived-position assertion; Backend / Windows 2025 and both
frontend jobs passed. The test-only machine-roundoff correction is locally validated;
the user verified correction commit `c2114fbb2b4c3c99568669407b97aa1b944cd75b`
with all four hosted jobs green in 1 minute 54 seconds and no artifacts. Stage 2.3R3
commit `e3011ec3919a8c0fce25d49a9938c0fda2fcbd3d` then passed all four hosted
jobs in 1 minute 49 seconds with no artifacts. Stage 2.3R4 stabilizes that viewer's
left-orbit, right-pan, and wheel-zoom lifecycle while retaining click selection and
presentation-only camera/axis behavior. It changes no engineering input or result.
Stage 2.3R8 completed the approved applied-action label styling and moment-arc
attachment refinement. Baraa Misto approved the resulting Stage 2.3 interface and
geometry foundation for a scope-specific freeze at commit
`5bc545ab8251f9bd49dedc776962937ed5e822a2`, recorded by annotated tag
`stage-2.3-interface-geometry-freeze`. The freeze protects the accepted Stage 2.3
workspace, geometry, preview/design, visualization, navigation, and action-display
contracts; it does not freeze the overall product or prevent future controlled
engineering-method development. See
[the Stage 2.3 freeze record](docs/governance/STAGE_2_3_INTERFACE_GEOMETRY_FREEZE.md).
No project storage, custom or solid-round
geometry, section properties, cylindrical-side targeting, contact/fit, bolt hardware,
automatic force-reference selection or eccentricity discovery, broader
whole-connection equations, demand distribution, optimization, persistence, or report
generation exists. The application remains a development workspace, not a validated
whole-connection design tool.

The J1 canonical angle-to-W fixture remains ASCE/SEI 74-23 Section 2.3.2
qualification-required; constituent single-bolt calculations are not a general
connection-design claim. The user-facing workflow exposes this limitation and does not
create an ordinary J1 whole-joint PASS.

The calculation roadmap is recorded for planning only. A capability remains unsupported until its source mapping, applicability limits, independent verification, and qualified engineering approval are complete.

Stage 3.1 begins controlled connection-platform generalization without changing a
calculation method. Connector topology is independent from material assignment;
fastener geometry/system identity is independent from fastener material and property
source. The initial connector families are `PULTRUDED_FRP`,
`STAINLESS_STEEL_316`, and `CARBON_STEEL`; the initial fastener families are
`STAINLESS_STEEL_316`, `CARBON_STEEL`, and `CUSTOM_FRP`. These identities do not
create material properties. Exact source/provenance and resistance authority remain
explicit and fail closed. Stage 2 engines, results, controlled goldens, fingerprints,
API/application behavior, frontend production source, dependencies, workflows, and the
Stage 2.3 freeze remain unchanged.

## Product boundaries

The future product will check user-defined connection assemblies using manually entered member-end actions as its first force workflow. It is not a structural-analysis or frame finite-element program, a replacement for SAP2000, a nonlinear connection FEA program, a general serviceability program, or a decorative stress-contour tool. It must never invent load paths, equations, capacities, or code requirements.

The future canonical engineering model must drive calculations, 3D and 2D views, dimensions, persistence, and reports. Rendered geometry is not a source of structural resistance. Geometry support and calculation support are distinct states, and unsupported work must fail closed.

## Repository map

- `backend/`: provisional package and service/API shell; Stage 1.1/1.2 domain
  contracts; Stage 1.3A spatial/action contracts; and Stage 1.3B
  standard-library-only exact nominal 2D standard-section geometry with explicit
  deferred features; Stage 1.3C1 renderer-neutral component placement and exact
  longitudinal extrusion; Stage 1.3C2A exact physical surfaces; and Stage 1.3C2B
  bounded planar interface targets, zones, and local frames; and Stage 1.3C3 joint
  context, bolt paths/holes/layers, reference points, and eccentricity traces; and
  Stage 2.1A framework-independent calculation contracts, snapshots, mapping,
  applicability/status, and fingerprints; plus the Stage 2.1B single-bolt numerical
  engine and golden verification; the Stage 2.2A application orchestration that
  resolves one canonical selected bolt with explicit material, fastener, and demand
  inputs; the Stage 2.2B strict stateless API adapter; the later verified multi-row and
  eccentric-demand calculation boundaries; and Stage 3.1 immutable connector,
  fastener, property-source, resistance-authority, compatibility, and assembly
  architecture. No general whole-connection engine, new Stage 3 resistance method,
  frontend integration,
  persistence, or reporting exists.
- `frontend/`: Stage 0.2.3 private React/TypeScript toolchain, tested noncalculating application shell, and project-local ignored dependencies.
- `contracts/`: future versioned cross-boundary contracts.
- `docs/`: controlled product, governance, architecture, engineering, QA, security, and baseline artifacts.
- `validation/`: future approved fixtures and independent benchmarks.
- `reference-private/`: untracked local area for licensed sources; only its README is tracked.
- `generated/`: untracked generated report and snapshot outputs; explanatory READMEs are tracked.
- `scripts/`: controlled backend/frontend bootstrap and QA entry points plus the
  integrated `check-all.ps1` software-foundation gate.
- `infra/`: reserved deployment boundary; no deployment implementation exists.
- `.github/workflows/ci.yml`: read-only Windows/Linux software-foundation CI; the
  Stage 0.2.4, Stage 1.1, Stage 1.2, Stage 1.3A, Stage 1.3B, and Stage 1.3C1 runs
  succeeded. Stage 1.3C2A commit `5e33db84e9efaf98fb5269b6df047be609c24506`
  passed four of four jobs; Stage 1.3C2B commit
  `2808348f44d308a4ddb30db0b2f89dc01e706da1` also passed four of four jobs in
  1 minute 53 seconds with no artifacts. Stage 1.3C3 commit
  6ce3f5f06f14d8e4f29410d7ef7ba9b61e557b75 passed four of four jobs in
  1 minute 21 seconds with no artifacts. Stage 2.1A commit
  `1804a6ff1a963966357b975c7d2d975a5e731a35` passed all four jobs in 1 minute
  22 seconds with no artifacts. Stage 2.1B commit
  `4931c201222816119fc1871fb4dce70d2f5d7afe` passed all four jobs in 1 minute
  48 seconds with no artifacts. Stage 2.2A commit
  `31b4785c88bb0b3564b7db9cc00b7206e3d2daa2` passed all four jobs in 1 minute
  33 seconds with no artifacts. Stage 2.2B passed all four jobs in 1 minute 27
  seconds with no artifacts; Stage 2.3 passed all four jobs in 1 minute 43 seconds
  with no artifacts. Stage 2.3R did not pass overall: only Backend / Ubuntu 24.04
  failed, on an exact floating-point serialization assertion; Backend / Windows 2025
  and both frontend jobs passed. Stage 2.3R2 commit
  `a28f83c2f124c3dcd994de250a1de962ef8ff72f` also did not pass overall: only
  Backend / Ubuntu 24.04 failed, while the other three jobs passed in 1 minute 58
  seconds and no artifacts were shown. The user later verified correction commit
  `c2114fbb2b4c3c99568669407b97aa1b944cd75b` with all four hosted jobs green in
  1 minute 54 seconds and no artifacts. Stage 2.3R3 commit
  `e3011ec3919a8c0fce25d49a9938c0fda2fcbd3d` passed all four jobs in 1 minute
  49 seconds with no artifacts. Stage 2.3R4 hosted CI is pending direct evidence.
- `HANDOFF_MANIFEST.json`: machine-readable Stage 2.3R4 handoff state and bounded
  workspace/API/orchestration/numerical-engine boundary.

## Source control and licensed material

ASCE/SEI 74-23 is registered by bibliographic, source-control, applicability, and
equation-reference metadata. No licensed PDF, table, figure, commentary, or
substantial source-language reproduction belongs in Git. The original user-authorized
Stage 2.1A equation catalog is non-executable and does not reproduce a PDF, table,
figure, or commentary. Local controlled source copies remain outside the tracked
repository or under the ignored `reference-private/` area.

## Governance

Approved requirements are captured as `APR-001` through `APR-131`; the original
`APR-001` through `APR-038` baseline remains historical, Stage 1.3A resolves
`PEN-ENG-001` through `PEN-ENG-003` without changing their IDs or history, and
Stage 1.3B records 19 one-to-one geometry approvals as `APR-040` through `APR-058`.
They are not reopened without a genuine engineering, safety, security, or
architectural conflict. Stage 1.3C1 reuses those compatible geometry approvals and
records its placement controls as `APR-059` through `APR-064`; Stage 1.3C2A records
its physical-surface and support-surface controls as `APR-065` through `APR-077`.
Stage 1.3C2B records planar targeting controls as `APR-078` through `APR-085`, while
Stage 1.3C3 records joint-context, bolt-path, hole/layer, reference-point, and explicit
eccentricity controls as `APR-086` through `APR-097`; Stage 2.1B records executable
equation, factor, comparison, branch-selection, and unit-equivalence controls as
`APR-109` through `APR-115`. APR-022 continues to separate
geometry from calculation support. Stage 2.3R through Stage 2.3R7 product/UI controls are recorded as
`APR-116` through `APR-131`. Provisional choices through `PRV-081`, including
exact implementation names and representations, are not
engineering approvals. Pending engineering,
architecture, commercial, security, and deployment choices remain explicitly
unresolved.

## Stage 2.3R3 connection orientation and axis refinement

The current workspace adds backend-authoritative exterior versus interior/web-side
W-flange contact, connected Angle Leg 1/Leg 2, and discrete outstanding-leg side.
Exact surface identities and bolt paths are returned by the server. Positive-volume
angle/W interference fails closed as `INVALID_GEOMETRY` before resistance, with no
calculation result or fingerprint and no silent orientation correction.

The solid viewer highlights the selected contact face, synchronizes canonical
member/bolt/surface selection with the sidebar, and keeps a labeled corner X/Y/Z triad
visible while optional full model axes, selected-member local x/y/z axes, material
LW/CW/TT axes, and action overlays remain separately controlled. These presentation
features do not enter engineering requests or fingerprints. Stage 2.1B equations,
RC2 goldens, Stage 2.2A/2.2B engineering meaning, and unsupported-method boundaries
remain unchanged.

## Stage 2.3R4 viewport navigation correction

The 3D viewer now owns one OrbitControls instance and one change listener per mounted
camera/canvas lifecycle. Camera changes update the fixed-corner global triad directly
without per-change React workspace state, while pointer-down remains available for
navigation and a four-pixel click threshold preserves W, angle, bolt, and contact-face
selection. Left-drag rotates, right-drag pans, and the wheel zooms. Static overlays are
pointer-transparent, resources are disposed on lifecycle replacement, and repeated
view/Fit/Reset navigation cannot call the calculation API or stale a current result.

Members are not drag-editable. Physical geometry is changed only by the existing
controlled inputs. The Stage 2.1B equations and RC2 goldens, Stage 2.2A orchestration,
Stage 2.2B result/status behavior, R3 geometry/orientation/material mapping,
fingerprints, and qualification behavior remain unchanged.

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change and [SECURITY.md](SECURITY.md) before handling secrets, licensed sources, identity, entitlement, or project data.

## Stage 2.3R5 live canonical preview workflow

Engineering edits now request a debounced, stateless backend preview that rebuilds the
same authoritative geometry, resolved action, material relationship, contact face,
bolt path, and interference state used by the verified design workflow. Preview never
executes a resistance equation and returns no capacity, utilization, governing check,
calculation fingerprint, or design PASS/FAIL result.

`Run Design Check` is the sole action that requests the unchanged Stage 2.2B design
endpoint. Model/Geometry Status and Design Results are distinct: geometry updates
immediately, invalid geometry blocks design, and a previous design result remains
visible but clearly stale until the engineer runs a new check. The scheduler uses a
200 ms numeric-input debounce, aborts superseded requests, and applies only the latest
revision. Camera navigation, overlays, model selection, and other presentation state
neither request preview nor stale design results. The Stage 2.1B equations, RC2
goldens, and Stage 2.2A/2.2B engineering meaning remain unchanged.

### Stage 2.3R6 engineering geometry and interactive preview inputs

The brace connected end and `Bolt-to-brace-end distance e1` are authoritative
engineering geometry. J1 defaults to exactly `2.000 in` / `50.8 mm`; the backend
uses that input to place the canonical end/bolt relationship, then the existing
geometry mapper re-derives the code distance consumed by the unchanged equations.

`Brace view length` and the column view extents are separate preview-only context.
They produce backend-authored, non-targetable `view_extension_primitives` and cannot
change engineering end planes, bolt/hole containment, code distances, capacities,
fingerprints, or design staleness. The directed brace geometry angle now accepts
`0 < theta < 180` in the current vertical plane; the backend separately reports the
sign-independent acute FRP material relationship. Applied force and moment labels
show signed server-returned values and units and can edit the same sidebar load
state. Edits preview automatically and stale design where appropriate, but only
`Run Design Check` requests resistance or utilization.

The prior R5 hosted run at `9a6714a934ac96bd90c136349b5b29fb3bb45c5d`
failed both frontend jobs only because the presentation stress test exceeded its
15-second limit (about 16.7 seconds on Ubuntu and 17.8 seconds on Windows); both
backend jobs passed and no artifacts were shown. R6 removes redundant DOM queries
and wall-clock repetition while preserving view/Fit/Reset/overlay/selection and
no-request/no-staleness assertions. Hosted verification of the correction commit is
still required. All local software gates and automated browser cases pass; the former
timeout case now completes in 623 ms test time / 1.945 seconds wall time without a
timeout increase. Manual right-button pan remains the only browser gesture not
synthesizable by the available automation.

### Stage 2.3R7 projected applied-action values

The primary signed values for `Fx`, `Fy`, `Fz`, `Mx`, `My`, and `Mz` now sit directly
beside their own rendered force arrows or moment arcs. Their presentation points are
projected through the active camera, so labels follow orbit, pan, zoom, all four views,
Fit Connection, and Reset View. The former detached upper-left action-card list is
removed. Applied/value/zero visibility stays coupled to the corresponding primitive,
while optional `+Fx` through `+Mz` convention labels remain nonnumeric and noneditable.

Clicking an applied value opens the same accessible editor and updates the same action
state used by the sidebar. A valid edit schedules canonical preview and marks an old
design stale, but only `Run Design Check` requests resistance or utilization. No
frontend sign, geometry, demand distribution, material direction, resistance, or
fingerprint logic was added. Fit-derived presentation clipping scales with the scene's
physical-unit profile so equivalent U.S. and SI models remain visible without
changing canonical geometry. Complete local QA passes 1,162 backend and 119 frontend
tests at configured 100% coverage; automated U.S./SI browser acceptance also passes,
with manual right-button pan and hosted R7 CI still pending. Stage 2.3R6 commit
`0344bc5eb91d4cc08a9418255ceaffbb3ff5ea84` was user-verified with all four
Ubuntu/Windows backend/frontend hosted jobs passing in 2 minutes 31 seconds and no
artifacts.

### Stage 2.3F scope-specific interface and geometry freeze

The verified Stage 2.3 foundation is frozen at R8 implementation commit
`5bc545ab8251f9bd49dedc776962937ed5e822a2` by annotated tag
`stage-2.3-interface-geometry-freeze`. The user-verified hosted run passed all four
backend/frontend Ubuntu 24.04 and Windows 2025 jobs in 2 minutes 23 seconds, with 123
frontend tests on each hosted platform and no artifacts.

This records the accepted interface, canonical geometry/visualization authority,
preview-versus-design workflow, viewport navigation, and applied-action interaction
foundation. It is not a production release and does not globally freeze FRP Master
Connection. Future engineering-method derivation and verification may continue;
changes to a frozen invariant require the controlled freeze-change procedure in the
[freeze record](docs/governance/STAGE_2_3_INTERFACE_GEOMETRY_FREEZE.md).

### Stage 2.4A multi-row contracts and calculation planning

Stage 2.4A adds general multi-row physical geometry, applicability, demand-scenario,
first-row/inter-row calculation-plan, block-path/raw-area, and deterministic planning
fingerprint contracts. It accepts arbitrary positive physical row and bolt counts,
preserves conservative and engineer-defined plans beyond three rows with explicit
qualification, and does not issue an ordinary ASCE PASS outside prescriptive scope.
No new resistance equation is executed. The active engine/rule set, RC2 equations and
goldens, API, frozen frontend, and freeze tag remain unchanged. See the
[planning specification](docs/engineering/MULTI_ROW_BOLT_GROUP_PLANNING_SPECIFICATION.md)
and [Slice 2 golden controls](docs/qa/CALCULATION_SLICE_2_GOLDEN_BENCHMARKS.md).

Stage 2.4A feature commit `b7411ef8da08bb7134bd7f83e729cfc3a90f77d8`
failed both hosted backend jobs only in the checkout-dependent Stage 2.3 frontend
freeze digest; each backend otherwise passed 1,239 tests at 100% coverage. Both
hosted frontend jobs passed 123 tests. Stage 2.4A-R1 replaces raw working-tree hashing
with exact frozen Git tree/blob identities, retaining strict source-change,
addition/deletion/rename, and package-file detection without path, line-ending, or
enumeration-order sensitivity. It also confirms production already held the four
approved material-pair-specific row distributions; the prior completion wording was
incorrect, and production is now tested directly against the unchanged Slice 2
golden. Full R1 local validation passed 1,254 backend and 123 frontend tests at
configured 100% coverage, all integrated/lint/type/build gates, a clean locked
install, and both zero-vulnerability audits. Correction hosted CI remains pending.

### Stage 2.4B multi-row numerical engine

Stage 2.4B implements the approved RC2 multi-row numerical slice behind one pure,
framework-independent calculation entry point. The immutable execution bundle carries
physical geometry, three distinct end-distance meanings, signed demand plus
nonnegative check demands, complete bolt/layer/line/block-path payloads, factor and
eccentricity contexts, required-check declarations, approved source identities, and
Slice 2 versions. Production derives results from these inputs and never reads the
test-only golden fixture.

The implemented source-derived branches cover the approved reusable per-bolt checks,
simplified and Appendix first-row net tension, inter-row Equations 8-12 and 8-13, and
block-shear Equations 8-14a/8-14b. Explicit RC2 rational/project branches cover the
unknown-`L_br` endpoint envelope, the more-than-three-row lower envelope, actual-row-
span shear-out, engineer-defined distributions, resolved unequal/staggered plans, and
physical L/U block paths. They retain qualification or review status and cannot become
an ordinary prescriptive PASS.

`unloaded_end_e1` is the distance from the unloaded free end to the nearest physical
row; row-to-free-end and loaded-boundary-to-Row-1 distances remain separate. Property
adjustments apply `CM`, temperature, and `C_CH` before the equation; connection factors
`C_lap` and `C_delta` follow the equation; `phi` and `lambda` apply last, each exactly
once. Multiple FRP layers are evaluated independently. Required checks, numerical
comparison, applicability, qualification, and overall disposition remain separate and
aggregate fail closed.

Slice 2 uses calculation contract `2.4B-RC2`, engine `0.2.0.dev1`, rule set
`asce74-23-ch8-multirow-rc2.dev1`, and draft input/result/fingerprint schemas
`0.1.0-draft`. RC1 remains the planning/regression authority; the exact RC2
specification, benchmark, and independent ledger are the numerical implementation
authority. Slice 1 versions, equations, results, and golden data remain unchanged.
Stage 2.4B changes no application orchestration, API route/schema, preview behavior,
frontend production source, dependency, lockfile, or Stage 2.3 freeze identity.

Stage 2.4B implementation commit pushed; local verification passed; hosted CI pending
user verification. The overall product remains draft.

### Stage 2.4C-R3 solid fastener hardware

Stage 2.4C adds orchestration contract `2.4C-RC1`, multi-row API/preview/visualization
schemas `0.1.0-draft`, and exactly these stateless operations:

- `POST /api/v1/calculations/multi-row/preview`
- `POST /api/v1/calculations/multi-row/design-check`

The backend constructs physical coordinates and boundaries, resolves signed-force row
and bolt-line order, re-derives source `unloaded_end_e1` separately from the loaded
boundary distance, classifies material direction, invokes the existing Stage 2.4A
planners, and creates the complete immutable Stage 2.4B bundle. Preview never invokes
the resistance engine. Design invokes it exactly once and preserves every calculation
status, trace, version, governing identity, and fingerprint.

The Shear workspace retains single bolt / single row as its default and adds row and
bolt-count controls in that same sidebar. Supported multi-row groups use automatic
debounced/cancelable preview, explicit design, stale-result protection, strict public
controls, and the same canonical Three.js connection scene and result region. The
backend returns every physical bolt, hole, washer, penetrated layer identity, and the
external connection-demand resultant; the frontend derives no engineering coordinates.
The supported public family is rectangular and nonstaggered;
unsupported row/bolt counts remain physically representable but fail closed or retain
qualification. There is no persistence, authentication, reporting, billing, automatic
demand distribution, friction credit, generated prying, or new equation method.

The original Stage 2.3 freeze tag and target remain immutable. The historical
`frontend/src` tree and visually rejected interim Stage 2.4C tree are retained as
provenance, and the unified R1 tree remains the accepted historical predecessor. R2
registers `f95396ff7ce5604f08f40b04b7b5e216271672c6` as the active reviewed
`frontend/src` Git-tree successor under the controlled freeze-change record.
Package declarations and the accepted secure lock remain exact. Hosted CI and formal
user visual acceptance remain pending until directly verified for the pushed commit.

R2 uses the independent canonical bolt and physical-hole diameters for both the solid
geometry and an exact-radius, non-pickable visibility outline. The backend multi-row
physical scene now uses the same standard hole already derived for its engineering
snapshot, so every bolt/hole pair remains consistent without frontend engineering
math. The former orthographic `+X` Side view is Side 1; Side 2 uses exact opposing
`-X`, with the same target and `+Z` up vector. View/Fit/Reset, picking, stale-result
behavior, calculations, fingerprints, dependencies, and the frozen Stage 2.3 baseline
are unchanged.

R3 removes the open-ended shank wireframe that made solid fasteners appear hollow.
Every 1 × 1, 2 × 1, 2 × 2, or larger supported rectangular group now uses one common
closed-shank/washer/head/nut renderer in all five views. Authoritative washer dimensions
and `UNDER_HEAD`/`UNDER_NUT` placement remain unchanged. Because exact head/nut
dimensions are not modeled, the controller-approved hex primitives are explicitly
schematic: head across-flats/height are `1.50d`/`0.625d`, and nut across-flats/thickness
are `1.50d`/`0.875d`. Those ratios exist only in frontend visualization code and affect
no geometry contract, fingerprint, interference, resistance, utilization, or report.

The active reviewed `frontend/src` tree is
`deb93d01646580ae62c9f90a507446d84019bd87`; R2 tree
`f95396ff7ce5604f08f40b04b7b5e216271672c6` is retained as historical provenance.
Local browser review covered solid 1 × 1/2 × 2 hardware, diameter scaling, all five
views, opposing sides, selection, explicit design persistence, and navigation without
API calls. Hosted R3 CI and user post-push visual acceptance remain pending.

### Stage 2.5A eccentric bolt-group demand engine

Stage 2.5A adds the pure calculation-layer entry point
`calculate_eccentric_bolt_group_demand`. For each accepted Stage 2.4A direct-demand
scenario, it projects the canonical global force into the exact interface basis,
transfers the physical force line to the geometric bolt centroid, retains the direct
distribution moment, and applies the equal-stiffness linear elastic correction needed
to close the residual in-plane moment. Every calculated scenario independently verifies
both vector-force and centroidal-moment equilibrium.

The new authority is Calculation Slice 3 RC1: contract `2.5A-RC1`, demand engine
`0.1.0.dev1`, rule set
`asce74-23-s2.9-eccentric-bolt-group-demand-rc1.dev1`, and demand result/fingerprint
schemas `0.1.0-draft`. The rational correction is explicitly identified as
`RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY`; it is not represented as an ASCE
prescriptive row-distribution equation. Production derives results and never reads the
test-only Slice 3 golden fixture.

RC1 is demand analysis only. Member-end and independent connection moments remain
trace-only, out-of-plane force creates no bolt-axis tension, and no prying, friction,
slip, nonlinear instantaneous-center demand, or heterogeneous-stiffness method is
generated. Every result states `resistance_handoff = NOT_AUTHORIZED_IN_RC1`; Stage
2.4B resistance equations and results are not called or changed. There are zero API,
application-orchestration, frontend, dependency, workflow, persistence, report, or
freeze-tag changes.

### Stage 2.5B eccentric resistance handoff

Stage 2.5B adds the pure calculation entry point
`calculate_eccentric_resistance_handoff`. It consumes one accepted Stage 2.5A result
without reconstructing or mutating its demand vectors and reuses the accepted Stage
2.4B engine without changing a resistance equation. A zero-residual-moment case
retains the complete legacy result exactly. For eccentric cases, metallic bolt shear
and FRP pin bearing use each bolt's actual total vector magnitude; bearing direction
is resolved independently for every penetrated layer against that layer's exact
backend LW axis. Explicit bolt-axis demand may be consumed for tension interaction
and pull-through but is never generated.

The RC1 compatibility matrix is deliberately partial. Eccentric first-row net tension
and inter-row shear-out remain required and `CALCULATION_NOT_SUPPORTED`; block shear
is reused only when stable canonical identities prove the existing path/eccentricity
context represents the same physical force line. Member-end moment transfer and
missing required axis demand prohibit ordinary PASS, while a known supported failure
remains FAIL. Demand analysis, compatibility handoff, and resistance calculation stay
separately traceable.

The handoff uses contract `2.5B-RC1`, engine `0.1.0.dev1`, rule set
`asce74-23-ch8-eccentric-demand-resistance-handoff-rc1.dev1`, and draft result and
fingerprint schemas `0.1.0-draft`. It adds no API, application orchestration,
frontend, dependency, persistence, report, or new resistance method. The Stage 2.3
freeze and both parent calculation identity families remain unchanged.

### Stage 2.5C automatic member-end force integration

Stage 2.5C connects the verified calculation slices through the existing application,
stateless API, and unified Shear workspace. Explicit resolved connection demand remains
the backward-compatible default. Automatic mode resolves the canonical member-end
force and physical reference point, runs Stage 2.5A once for each accepted scenario,
and exposes backend-authored per-bolt demand during preview without running resistance.
Only **Run Design Check** continues into Stage 2.5B, which is the sole compatibility
boundary permitted to reach unchanged Stage 2.4B resistance behavior.

The automatic result keeps the Stage 2.5A demand trace and Stage 2.5B handoff trace
separate. Member-end moments remain untransferred; interface-normal force creates no
axis demand or prying; eccentric first-row net tension and inter-row shear-out remain
unsupported; and block shear is shown only under the existing canonical compatibility
test. Supported numerical failure remains FAIL, while unsupported or incomplete
required checks prevent ordinary whole-connection PASS.

The multi-row application contract is `2.5C-RC1`; its API transport, preview, and
visualization schemas are `0.2.0-draft`. Calculation contracts, rules, equations,
goldens, and fingerprints remain unchanged. Frontend source successor
`035af7c9c44c49914c63c68edf6ec4eea5521bcf` adds the demand-source workflow and an
optional backend-vector overlay while retaining solid hardware, all five views,
session-only state, and explicit design execution. Package and secure-lock identities
and the original Stage 2.3 freeze tag remain unchanged.

Stage 2.5C-R2 corrects loaded-boundary placement without changing engineering-method
meaning. The backend now holds the accepted loaded boundary fixed and places Row 1,
every other row, and every bolt from the independent
`loaded_boundary_to_row_1_distance`; the physical snapshot no longer re-anchors Row 1
and erases whole-group translation. A 2 in to 4 in change therefore moves the complete
group exactly 2 in along the loaded-to-row placement direction while retaining pitch,
gauge, hardware dimensions, identities, and connected-member presentation geometry.
The same corrected coordinates feed explicit preview/design and Stage 2.5A automatic
centroid/eccentricity resolution. The frontend remains coordinate-passive, shares one
scene across all five views, and labels the backend loaded boundary in the optional 2D
diagnostic. Active `frontend/src` tree
`cd25332af05c101aa008934a7b900d8c220938f3` succeeds the R1 tree under the controlled
freeze-change record; package, lock, and immutable Stage 2.3 tag identities remain
unchanged. Hosted CI and direct user visual acceptance are pending.

### Stage 2.6A eccentric group-mode compatibility

Stage 2.6A adds the pure calculation-layer entry point
`calculate_eccentric_group_mode_compatibility`. It consumes the accepted immutable
Stage 2.5A demand result and Stage 2.5B handoff result, derives each physical bolt-line
resultant by summing the actual per-bolt vectors assigned by the canonical Stage 2.4A
geometry, and compares that resultant with the exact connection-force direction.

An exactly zero line is not required. A positive parallel line reuses the unchanged
Stage 2.4B inter-row shear-out calculation through the explicitly identified project
rational extension `RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF`. Nonparallel and
reversed resultants fail closed without projection or magnitude substitution. The
existing Equation 8-12, Equation 8-13, and more-than-three-row extension paths are
reused; no resistance equation is added or changed.

Zero residual moment preserves the complete legacy Stage 2.4B result. With nonzero
residual moment, the general eccentric first-row net-tension method remains
`CALCULATION_NOT_SUPPORTED`, so supported line PASS results do not create an ordinary
whole-result PASS. The contract is `2.6A-RC1`; engine `0.1.0.dev1`; rule set
`asce74-23-ch8-eccentric-group-modes-rc1.dev1`; and result/fingerprint schemas
`0.1.0-draft`. This backend-only stage changes no frontend, API, application
orchestration, dependency, workflow, persistence, report, parent golden, or parent
calculation identity.

### Stage 2.6B eccentric group-mode integration

Stage 2.6B integrates the accepted Stage 2.6A compatibility result into automatic
multi-row design. After **Run Design Check**, the application passes each exact Stage
2.5A demand result and its exact Stage 2.5B handoff context to Stage 2.6A exactly once.
The API and unified workspace expose actual bolt-line resultants, supported inter-row
shear-out resistance/utilization, zero-line and unsupported orientation states, and a
separate eccentric first-row limitation. A supported line failure governs the whole
result; supported line PASS cannot create ordinary PASS while required eccentric
first-row net tension remains unsupported.

Preview remains resistance-free, explicit resolved demand is unchanged, and the
frontend performs no line aggregation or resistance calculation. No engineering
equation, controlled golden, dependency, workflow, persistence, or report changes.
The multi-row API transport advances to `0.3.0-draft`; orchestration remains
`2.5C-RC1`, and the application merge is identified by `2.6B-RC1`. Active controlled
`frontend/src` tree `b73469788561bebf61262f2211b6e39c3e3a699c` succeeds the Stage
2.5C-R2 tree while the package, secure lock, and immutable Stage 2.3 tag remain exact.
Hosted CI and direct user visual acceptance remain pending.

### Stage 3.1 connector and fastener material architecture

Stage 3.1 adds framework-independent contracts in
`domain.material_architecture` for four high-level engineering coverage classes,
connector and fastener material families, material behavior, property-source
provenance, connector engineering assignments, fastener systems, resistance authority,
and the minimum immutable connection-assembly scaffold needed by a later controlled
Tee vertical slice. Topology and material remain independent: a Tee, angle, plate, or
bracket topology is not copied into separate geometry types merely to carry FRP,
stainless-steel, or carbon-steel identity.

Coverage classes are `PRESCRIPTIVE`, `QUALIFICATION_REQUIRED`, `CROSS_CODE`, and
`RESEARCH_OR_PROPRIETARY`. They organize roadmap/architecture scope and never replace
the more precise calculation applicability, availability, qualification, or comparison
statuses. Property sources identify controlled project, manufacturer, standard/grade,
test-qualified, or custom engineering provenance without embedding licensed text or
inventing a value. `STAINLESS_STEEL_316` and `CARBON_STEEL` imply no grade, yield,
tensile, shear, resistance factor, coating, or corrosion classification.

The narrow `calculation.material_compatibility` adapter maps only FRP/FRP to the
unchanged legacy `FRP_FRP` identity and FRP/316-stainless or FRP/carbon-steel to the
unchanged legacy `FRP_STEEL` identity while retaining the exact metal subtype in
higher-level evidence. Steel/steel, custom, unknown, and every other unsupported pair
reject without fallback. Existing metallic-bolt eligibility requires an explicitly
compatible metallic fastener system, authoritative geometry, the existing metallic
authority, and an accepted explicit property snapshot. A `CUSTOM_FRP` fastener cannot
enter the metallic equations under any authority; a future custom-FRP resistance path
would require its own separately approved method and authority.

Exposure environment, coating/protection, galvanic/isolation detail, and corrosion
review remain deferred future provenance. Stage 3.1 adds no corrosion or durability
rule and grants no structural resistance or compatibility credit from such metadata.

The connection-platform contract is `3.1-RC1`; connector-material,
fastener-system, and connection-assembly schemas are each `0.1.0-draft`. Stage 3.1
adds no resistance equation, strength catalog, Tee/clip-angle/gusset/anchor geometry,
steel connector capacity, API route, application orchestration, frontend production
source, dependency, workflow, persistence, report, authentication, or billing. Full
local QA passes 1,588 backend tests and 185 frontend tests at configured 100-percent
coverage, with all static, build, dependency, audit, freeze, and integrated gates green.
Object-isolated committed-state verification, push, and hosted Ubuntu/Windows CI remain
pending and are separate evidence.

### Stage 3.2 reusable Tee connector vertical slice

Stage 3.2 adds one backend-authoritative Tee topology to the existing unified,
session-only connection workspace. The same Tee implementation supports brace-to-
column-flange and brace-to-beam-flange placement and either selected physical support
flange. Its perpendicular flange/stem solids create two distinct physical interfaces:
Interface A joins the brace to the stem, and Interface B joins the Tee flange to the
support. Each interface has an independent bolt layout, group, path/layer stack,
demand, result, and fingerprint.

The application resolves one explicit global action/reference into both local
interfaces and delegates only authorized in-plane work to the unchanged Stage 2.5A,
2.5B, and 2.6A chain. A nonzero interface-normal component is displayed and fails
closed; it is never converted into automatic bolt-axis tension or prying. Tee-body
resistance remains `NOT_EVALUATED`, preventing ordinary whole-assembly PASS, while a
known supported interface failure still yields FAIL. Exact 316 stainless and locked
F593 identities infer no missing strength.

The Tee template provides backend preview, explicit **Run Design Check**, U.S./SI
benchmark loaders, two grouped result panels, both physical bolt groups, and stale-
result handling. Preview runs zero resistance calculations. Stage 3.2 adds no new
resistance equation, dependency, persistence, report, workflow, or tag and does not
begin Stage 3.3. Local automated QA is recorded in the QA plan. Stage 3.2-R1 hosted CI
was accepted four of four green with 227 frontend tests on both platforms; owner V1
review required the R2 workspace/profile correction before Stage 3.2 can close.

### Stage 3.2-R2 unified workspace and member profiles

Stage 3.2-R2 replaces the two connection-template buttons with one grouped
**Connection type** selector and places both the direct and Tee workflows in the same
connection-first shell. On desktop, the engineering sidebar scrolls independently
while the canonical viewer remains visible and retains its camera and presentation
state. The result area remains part of that shared workspace. Physical names replace
internal shorthand: **Brace to Tee Stem** and **Tee Flange to Support** identify the
two Tee interfaces, and the viewer title identifies the selected brace profile, FRP
Tee, and W-column or W-beam support.

The backend now owns an immutable member-profile assignment that keeps member role,
profile family, exact dimensions, material identity, orientation, selected physical
surface, and stable geometry identity separate. Production Tee-brace profiles cover
angle, channel, wide-flange/I, rectangular hollow section, and an explicitly selected
flat plate. Round hollow section remains an identity-only family for this slice: its
curved wall is not silently treated as a flat Tee-stem contact. The supporting W shape
uses one profile geometry for both column and beam roles; role changes placement, not
the section definition.

Interface A is resolved from the chosen real brace surface and its physical penetrated
element. Interface B retains its independent layout, bolt group, path, layer stack,
demand, result, and fingerprint. Profile or surface edits are engineering changes and
stale an existing design result; camera, highlight, accordion, and other display-only
changes do not. The frontend renders backend-authored solids and never reconstructs
profile placement or resistance. Stage 3.2-R2 adds no strength catalog, member-body
resistance, Tee-body resistance, new demand or resistance equation, dependency,
persistence, report, workflow, or Stage 3.3 work. Hosted CI and user V1-R2 through
V5-R2 visual acceptance remain separate closure evidence.

### Stage 3.2-R4 exact SI geometry and valid Tee benchmark

Stage 3.2-R4 keeps exact input quantities authoritative through unit conversion,
coordinate arithmetic, end-distance validation, and fingerprinting. Geometry-kernel
floats remain available for intersections and rendering but are no longer subtracted
and then promoted back into engineering authority when exact source distances exist.
This removes the SI-only `50.800000000000004` artifact without adding a tolerance,
rounding rule, SI branch, or resistance-method change.

Both Tee benchmark buttons now load one controlled physically valid flat-plate brace
connection. The SI request is derived exactly from the U.S. fixture, including the
action and printed-hole identity. Angle, Channel, W/I, RHS, and manual flat-plate
editing remain unchanged. Hosted CI and renewed V1-R2 through V6-R4 user visual
acceptance remain separate closure evidence; Stage 3.3 has not begun.

### Stage 3.2-R5 cross-platform preview fingerprint determinism

Stage 3.2-R5 corrects the only failed R4 hosted job. Backend Ubuntu completed the
engineering suite but produced different U.S. and SI preview hashes because its
platform math library returned the semantic 45-degree sine one binary64 ULP below
the Windows value. That value propagated through normalized brace geometry into the
canonical preview payload; Backend Windows and both unchanged frontend jobs passed.

Semantic degree angles are now converted to deterministic binary64 sine/cosine values
without platform-libm trigonometry. The correction adds no OS branch, tolerance,
epsilon, rounding, quantization, geometry clamp, or fingerprint rewrite. Tests expose
and compare the exact canonical pre-hash payload and simulate the Ubuntu one-ULP
input. All four R4 U.S./SI execution and preview fingerprints remain unchanged, as do
geometry meaning, demand, resistance, frontend production source, dependencies,
workflow, and the Stage 2.3 freeze. Direct user evidence accepts all four hosted R5
Ubuntu/Windows backend/frontend jobs. The existing V1-R2 through V6-R4 visual
acceptance remains pending direct evidence; Stage 3.3 has not begun.

### Stage 3.2-R6 live-preview state correction

R6 makes the Tee viewer explicit about which backend response it displays. A current
accepted preview replaces the scene; while a new request is pending, or when current
inputs are rejected, the prior valid scene remains visibly labeled as the last valid
preview. With no accepted preview, the workspace displays no guessed geometry.

Backend validation detail is surfaced when safely available, design remains disabled
until the current request revision has an accepted design-ready preview, and obsolete
responses cannot replace newer form state. Selected bolts or contacts that disappear
from accepted geometry are cleared deterministically. No backend production source,
engineering rule, geometry validation, equation, fingerprint, dependency, workflow,
or freeze tag changes. Hosted R6 CI and renewed V1-R2 through V6-R4 visual acceptance
remain separate evidence; Stage 3.3 has not begun.

### Stage 3.2-R7 exact Angle bolt paths

R7 derives each selected Angle-leg bolt path from the existing exact member-profile
surface registry. A valid bolt crosses the selected finite exterior face, exactly one
leg thickness, and exactly one finite exposed opposing broad boundary of the same leg.
The internal heel overlap, a free-edge exit, an outside-leg point, a wrong or ambiguous
patch, and a thickness mismatch remain invalid without epsilon or fallback.

The backend-confirmed acceptance fixture is a `6 x 6 x 0.5 in` Angle of `8 in` length,
zero-degree orientation, `LEG_Y_OUTER`, a 2-by-2 Interface A layout, `2 in` pitch and
gauge, and `1.2815 in` unloaded-end distance. No frontend production source changes;
the active R6 tree remains exact. R7 changes no resistance method, accepted
fingerprint, dependency, workflow, or freeze tag. R6 hosted CI is accepted four of
four green. R7 hosted CI and renewed V1 visual acceptance remain pending separate
evidence; Stage 3.3 has not begun.

### Stage 3.2-R9 independent Tee controls and brace direction

The Tee workspace now treats Brace ↔ Tee Stem and Tee Flange ↔ Support as independent
physical bolt groups with positive row/line counts. Unsupported one-row calculation
cases remain explicitly fail-closed. A backend-authoritative signed planar brace
inclination rotates only the brace and Interface A; profile roll remains separate and
the global action is unchanged. Tee bolts reuse the shared solid shank/head/nut/washer
presentation path without creating calculation inputs from schematic hardware.

R9 preserves all earlier controlled fingerprints at zero inclination and changes no
equation, demand distribution, dependency, workflow, persistence, report, or freeze
tag. Hosted R9 CI and V1-R9 through V5-R9 visual acceptance remain pending after the
controlled commit and authorized push; Stage 3.3 has not begun.

### Stage 3.2-R10 Tee-fixed bolt-grid positioning

R10 separates the inclined brace/member frame from the physical Interface A bolt-layout
frame. Brace inclination still rotates the connected member about the established
backend anchor, while both Tee interface grids remain fixed to their physical Tee-stem
and Tee-flange datums. Each interface supports legacy edge-distance placement or signed
vertical/horizontal group offsets; no through-thickness offset is exposed.

The backend reports exact complete-hole clearances to finite interface boundaries. A
geometry-valid fixed grid outside the proven row-distribution frame contract fails
closed as `ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN`; it does not rotate the grid
or execute a new equation. Zero-inclination legacy fingerprints remain exact, and only
controlled nonzero R9 geometry fingerprints transition. Hosted R10 CI and V1-R10
through V6-R10 visual acceptance remain pending after an authorized push.

### Stage 3.2-R12 connected-member end trim

The Tee workspace now provides an explicit optional fabrication end trim. The backend
derives the Tee flange inner clearance plane from the real connector, constructs the
parallel cut plane at the exact nonnegative entered clearance, clips the actual
connected profile solids, and returns the canonical trimmed meshes and physical
free-edge clearances. Trim disabled retains the legacy R11 geometry and fingerprints.

Angle, Channel, W/I, RHS, and Flat Plate use the same geometry engine. Interference,
remaining material, and hole-edge clearance are resolved from the trimmed solids;
negative clearance and unevaluated trimmed resistance mapping fail closed. This stage
adds no resistance equation, automatic bolt relocation, frontend engineering clipping,
dependency, persistence, report, or Stage 3.3 work. Hosted CI and V1-R12 through
V6-R12 visual acceptance remain pending direct evidence.

### Stage 3.2-R13 Tee length anchoring and position

The Tee workspace can now position the entire finite connector along its existing
backend longitudinal axis by the connector center, positive/upper end, or negative/
lower end. Changing length grows symmetrically in centered mode and one-sided in an
end-fixed mode; changing the signed position translates the whole flange-and-stem body.
Anchor switches use the current accepted backend end coordinates, so equivalent modes
do not make the viewer jump.

Connector-body placement remains separate from R10/R11 bolt-group positioning. Both
physical interface bolt groups stay fixed while the server recomputes complete-hole
clearance to the connector's actual finite ends. Connected/supporting members and R12
trim clearance remain unchanged. R13 adds no resistance equation or authority,
automatic relocation, dependency, workflow, persistence, report, or Stage 3.3 work.
Hosted CI and V1-R13 through V7-R13 visual acceptance remain pending direct evidence.

### Stage 3.2-R14B region-specific material-axis correction

The backend now assigns the exact right-handed FRP `LW/CW/TT` basis per physical
section region. This corrects W/I webs, Tee stems, Angle Leg 2, Channel webs, and RHS
side walls while preserving already-correct flanges, Angle Leg 1, RHS top/bottom, and
Flat Plate. The viewer consumes these backend vectors unchanged and identifies the
physical region with engineer-friendly labels while retaining stable internal IDs in
diagnostics.

R14B changes coordinate orientation and basis-derived preview/platform fingerprints
only. Member/Tee/bolt/contact/trim geometry, material properties, equations, demands,
capacities, utilization, statuses, applicability, and unrelated engineering/result
fingerprints remain exact. R14 and R14A were diagnosis-only stops. Hosted CI and
V1-R14B through V7-R14B visual acceptance require direct evidence; Stage 3.3 is not
started.

### Stage 3.2-R14C region-embedded material axes

The shared direct, multi-row, and Tee viewer now places one compact material-direction
indicator on each backend-identified physical FRP plate, flange, web, leg, stem, or
wall. Purple LW and amber CW are bidirectional in-plane axes; teal TT is a camera-aware
through-thickness dot, cross, or tangent ring. The scene contains no repeated floating
LW/CW/TT text. One accessible color-and-shape legend appears only with the existing
`Material axes (LW / CW / TT)` overlay.

Anchors, display scale, surface offset, colors, and marker facing are frontend-only
presentation. Exact R14B backend vectors and stable region IDs remain authoritative;
engineering geometry, material properties, calculations, statuses, fingerprints,
dependencies, workflows, and the Stage 2.3 freeze are unchanged. Hosted R14C CI and
V1-R14C through V8-R14C remain post-push evidence; Stage 3.3 is not started.

### Stage 3.2 Tee-connection freeze

The accepted Stage 3.2 Tee baseline is preserved by the machine-readable
`docs/governance/STAGE_3_2_TEE_CONNECTION_FREEZE_MANIFEST.json`. It records the exact
product commit, source/dependency identities, accepted CI and visual evidence, 30
Stage 3.2 controlled artifacts, 15 inherited Stage 2 hashes, fingerprint provenance,
behavioral contracts, and deliberate limitations. The integrated test-only freeze
audit rejects drift in those identities while retaining the immutable Stage 2.3 tag.

This is a scope-specific governance/reproducibility freeze. The overall product and
schemas remain draft; no production source, engineering method, dependency, workflow,
persistence, or report behavior changes, and Stage 3.3 has not begun.

### Stage 3.3A single FRP clip angle

Stage 3.3A adds the first single clip-angle vertical slice by reusing the frozen Stage
3.2 section, surface, placement, bolt-path, material, fastener, demand, resistance-
handoff, viewport, and live-preview foundations. One physical pultruded-FRP angle has
independent Connected Member-to-Connected Leg and Support Leg-to-Support bolt groups,
backend-authoritative placement and visualization, exact U.S./SI identity, and a
stateless preview/design API. Preview executes zero resistance calculations; design
uses the existing verified multi-row engine through an explicit resolved-demand seam.

Nonzero interface-normal action and the required clip-angle body resistance remain
visible and fail closed. Supported interface failure still governs overall `FAIL`,
while no ordinary `PASS` is possible with the connector-body check unevaluated. The
Stage 2.3 and Stage 3.2 freeze tags/manifests remain immutable. Future Stage 3.3B
paired/double clip angles and Stage 3.3C W-web/beam-to-beam expansion are planned but
not begun.

### Stage 3.3A-R1 connected-profile preview binding

Stage 3.3A-R1 corrects the backend preview adapter that previously represented every
selected connected-member family as one generic plate. Clip-angle preview now carries
the actual backend-authored Flat Plate, Angle, Channel, W/I, or RHS physical elements,
orientation, and material-region axes for either Brace or Beam. The frontend remains a
consumer of the accepted latest response and does not reconstruct profile geometry.

The correction changes no calculation equation, demand, resistance, status,
applicability, engineering fingerprint, dependency, workflow, or frozen Tee behavior.
Preview remains resistance-free, Run Design Check remains explicit, and Stage 3.3B is
not started.

### Stage 3.3A-R2 connected-member surface-side placement

Stage 3.3A-R2 corrects the backend placement of the selected connected-member profile
relative to the fixed clip angle. The selected physical surface and the connected-leg
contact face are now exactly coincident, the profile material occupies the interior
half-space, and the connector occupies the exterior half-space. Exact oriented-box
separation distinguishes permitted zero-volume contact from positive-volume overlap;
finite Angle heels, Channel flanges, W/I flanges, RHS walls, and the support leg can
therefore fail closed instead of being hidden by a visual offset.

The connector body, sharp heel, support interface, both bolt groups and stacks,
controlled numerical results, and all ten Stage 3.3A engineering fingerprints remain
exact. The frontend still renders accepted backend primitives without reconstructing or
offsetting geometry. The Stage 2.3 and Stage 3.2 freezes remain unchanged, and Stage
3.3B is not started.

### Stage 3.3B symmetric paired FRP clip angles

Stage 3.3B adds one symmetric pure-reaction-shear paired-angle vertical slice. Two
mirrored physical FRP angles share one common through-bolt group across the positive
angle, centered connected member, and negative angle; two independent support groups
remain mirrored about the pair plane. The backend proves geometry and action symmetry,
splits the parent reaction into exact half-wrenches, resolves each physical group once,
and assigns controlled half/full/half FRP layer demands without duplicating the common
bolts or changing an accepted resistance equation.

The single unified workspace supports Flat Plate, W Web, and Channel Web profiles with
live resistance-free preview and explicit Run Design Check. Pair-body resistance,
individual angle-body resistance, common-bolt double-shear resistance, and nonzero
interface-normal action remain visible `NOT_EVALUATED` limitations, so no ordinary PASS
is fabricated. Asymmetric pairs, independent left/right support layouts, support-web or
beam-to-beam expansion, and those future resistance methods are not implemented.

### Stage 3.3C1 shared rectangular-section and full-through-bolt core

Stage 3.3C1 adds backend-only reusable architecture for a real Solid Rectangular
Section and full-through rectangular bolts. RHS paths now have an explicit physical
near-wall/material, cavity/free-shank, far-wall/material sequence; SRS paths have one
continuous solid material layer. One bolt owns one exact opposing-face axis, one shank,
external head/nut/washers, and independent complete-hole containment on both exterior
faces. Free cavity spans are excluded from resistance material layers.

The shared support registry contains exactly W Column Flange, W Beam Flange, W Column
Web, Channel Column Web, Angle Column Leg, Rectangular Hollow Column Wall, and Solid
Rectangular Column Face. These are dormant contracts: current production selectors,
API routes, frontend source, equations, and accepted engineering fingerprints are
unchanged. Stage 3.3C2 and Stage 3.3C3 now own the separately controlled product
integrations described below.

### Stage 3.3C2 Tee and Single Clip-Angle support/profile expansion

Stage 3.3C2 integrates the shared C1 section and full-through-bolt core into the
existing Tee and Single Clip-Angle families. Both workspaces use one strict seven-target
support contract and one shared editor for W column/beam flanges, W column web, Channel
column web, Angle column leg, RHS column wall, and SRS column face. There is no W Beam
Web target. Connected-member selectors expose SRS wherever these workflows expose RHS.

RHS paths use one physical bolt across connector, near wall, cavity, and far wall; SRS
paths cross connector plus one solid layer. Hardware is external-only, both exterior
hole disks must be contained, and the RHS cavity is never a material or bearing layer.
Missing RHS local-wall/sleeve and SRS full-depth resistance authority remains visible as
`NOT_EVALUATED` design limitations without converting sound preview geometry to invalid
geometry. No new equation is executed. Unaffected frozen Tee, accepted Single-Angle,
Direct, and then-current Paired-Angle behavior remains exact; Stage 3.3C3 completes the
separately controlled Paired-Angle expansion below.

Stage 3.3C2-R1 corrects two integration defects without changing C2 engineering
identity. Current C2 Tee RHS requests now bypass the historical same-wall resolver and
reach the existing full-through builder; legacy Tee contracts retain their accepted
same-wall behavior. Single Clip-Angle preview and design responses now echo the strict
request contract, so `3.3C2-RC1` responses pass the existing frontend guard while
unknown future versions still fail closed. The current Tee and Single-Angle C2
fingerprints, all controlled artifacts, dependencies, workflows, and both freeze tags
remain exact.

### Stage 3.3C3 Paired Clip-Angle profile/support expansion

Stage 3.3C3 completes the C1/C2 profile and support expansion for the accepted symmetric
Paired Clip-Angle family. The connected selector now contains exactly Flat Plate, W/I,
Channel, Angle, RHS, and SRS, while the shared supporting-member editor exposes the same
seven targets used by Tee and Single Clip-Angle, with no W Beam Web target.

Open-profile common/support groups retain physical selected-surface containment and
stable layer identities. Connected RHS/SRS common bolts and rectangular supporting
groups reuse the shared backend full-through composer: one physical bolt, external
hardware, material/free-span separation, and independent complete-hole containment on
both faces. Angle or open-support cases receive equal sharing only when the existing
pair proof establishes symmetry; no distribution is invented otherwise. Unsupported
rectangular local mechanics remain visible `NOT_EVALUATED` design limitations and do
not turn sound geometry into invalid geometry. The legacy `3.3B-RC1` contract and all
accepted Tee/Single/Stage 3.3A fingerprints remain exact. The Clip-Angle family is not
frozen by this stage.

### Stage 3.3 Clip-Angle family freeze

The accepted Single and Symmetric Paired FRP Clip-Angle family is frozen for governance
and reproducibility at product baseline `a15f6f9bc820bc7e2d466db8519bcb9582b96e55`.
The byte-exact manifest records the 12-commit acceptance chain, 15 Stage 3.3 controlled
artifacts, 22 inherited authorities, source/dependency identities, both prior immutable
freeze tags, GitHub Actions run 69, direct final user visual acceptance, current
fingerprints, accepted contracts, and deliberate fail-closed limitations.

The freeze adds no production source, dependency, workflow, equation, engineering
artifact, result, status, or fingerprint change. Future work may reuse shared
infrastructure only with explicit supersession, controlled authority where engineering
meaning changes, exact fingerprint transitions, unaffected Stage 3.3 regression
evidence, and retained historical freeze/tag evidence.

### Stage 3.4A Multi-Member Tee node

Stage 3.4A adds the owner-selected Multi-Member Tee as a separate connection type; the
superseded Gusset-Plate draft remains unapproved and unused. Optional Upper Angle
Brace, horizontal W/I Beam, and Lower Angle Brace slots share one finite Tee and W
column-flange support while retaining independent placement, trim, bolt group, complete
member-end wrench, result, and fingerprint identities. Disabled slots are omitted.

The backend remains the sole geometry and equilibrium authority. It assembles the exact
support transfer wrench, including every shifted moment, and reuses the verified demand
and eligible resistance handoffs without adding an equation. Preview is resistance-free
and Run Design Check remains explicit. Required Tee-body and intergroup load-path/
stability checks remain `NOT_EVALUATED`, so ordinary PASS is prohibited. Frozen
single-member Tee, Clip-Angle, and Direct behavior and fingerprints remain unchanged;
dependencies, workflows, package/lock identities, and all three immutable freeze tags
also remain unchanged. Hosted four-job CI and the controlled visual matrix require
direct post-push evidence.

### Stage 3.4B Multi-Member Tee profile/support expansion

Stage 3.4B keeps `3.4A-RC1` byte-for-byte compatible and adds the strict additive
`3.4B-RC1` contract. Upper, Middle Member (horizontal), and Lower slots each expose
Flat Plate, Angle, Channel, W/I, RHS, and SRS through one shared profile contract and
editor. Middle Flat Plate and Middle Angle are explicit supported owner requirements;
their inclination remains exactly zero. Disabled slots retain no hidden profile state.

The same shared supporting-member registry/editor now exposes exactly W Column Flange,
W Beam Flange, W Column Web, Channel Column Web, Angle Column Leg, RHS Column Wall, and
SRS Column Face. Backend-authored physical profiles, selected surfaces, trims,
material-region axes, support transforms, and full-through hardware remain authoritative.
RHS bolts cross connector, near wall, cavity, and far wall with external hardware only;
SRS bolts cross connector plus the full solid depth. The cavity is never material.

Slot actions and the exact shifted-moment support wrench remain independent of profile
or support labels. No demand or resistance equation is added. Existing Tee-body and
intergroup limitations remain, and RHS/SRS local-mechanics limitations are explicit
design limitations rather than geometry errors. The Stage 3.4A default fingerprint
`2594c3e28cd47fac2b5235710733ab0bd94d0c61bb82bb174e21b9979c252717`
and support-wrench fingerprint
`1a045a3fdd132d18249c2cc27a9208ffad18a7dd6e857cf85215aaf5090a2e34`
remain exact. After hosted CI and visual acceptance, a separate Multi-Member Tee family
freeze is recommended. No Stage 3.4C engineering-method stage is selected.

### Stage 3.4 Multi-Member Tee family freeze

The accepted Multi-Member Tee family is frozen at product baseline
`b2da06ea04276e2113906d4e7c2b4295496f685f`. GitHub Actions runs 72, 73, and 74
establish the accepted R1, R2, and Stage 3.4B four-job evidence, and the owner accepted
the complete Stage 3.4 visual matrix on 2026-08-28. The machine-readable freeze manifest
records the Stage 3.4A/R1/R2/B chain, exact authorities, production-source and dependency
identities, representative fingerprints, frozen contracts, and deliberate limitations.

The freeze audit is successor-safe in tag-aware, current-freeze-commit, and future
tagless shallow-successor environments. It never treats successor `HEAD` as the frozen
Stage 3.4 source tree when the historical tag/object is unavailable. This freeze changes
no production source, engineering equation, result, status, fingerprint, dependency, or
workflow. The Stage 2.3, Stage 3.2, and Stage 3.3 freezes remain immutable. No Stage 3.4C
or next connection family is selected.

### Stage 3.5A Beam-to-Concrete Wall — Paired FRP Clip Angles

Stage 3.5A adds a separate shear-only connection type for one horizontal W/I beam,
two symmetric FRP clip angles, and a finite concrete wall. One common physical beam
bolt group and two mirrored external wall-anchor groups are backend-authored. The
only applied action is signed vertical reaction shear; user moments are prohibited.

The backend resolves the positive and negative branch forces and exact eccentricity
moments, then retains both branch wrenches and their combined wall-interface wrench in
a deterministic external anchor-design handoff. Concrete and anchor capacities are not
calculated, and external design remains explicitly required. Preview executes zero
resistance equations; Run Design Check remains explicit and may evaluate only the
existing eligible beam/FRP checks. The established Direct, Tee, Clip-Angle, and
Multi-Member Tee products and all four immutable freeze tags remain unchanged.

### Stage 3.5A-R1 Concrete-Wall Paired-Angle completion

The `3.5A-R1-RC1` successor completes the concrete-wall workspace while retaining the
historical `3.5A-RC1` contract byte-for-byte. The shared selector now uses Brace/beam
presentation labels where one physical shear connection serves either role, and the
connected-member editor exposes Flat Plate, Angle, Channel, W/I, RHS, and SRS through
the accepted paired-angle profile registry.

The default has one wall anchor per clip angle. Exact positive/negative branch wrenches
and the combined wall-interface wrench are still exported, but no nominal per-anchor
force is fabricated for a 1×1 group that cannot equilibrate the retained branch moment;
the handoff reports `WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION` as
`EXTERNAL_DESIGN_REQUIRED`. Users may expand the mirrored groups to 2×1 or 2×2, where
the existing equilibrium solver supplies a nominal trace only when applicable.

The backend remains authoritative for every profile, full-through path, gap, material
region, angle body, anchor, and wrench. The scene adapter preserves both reflected clip
angles and the connected member by converting left-handed reflected box bases to an
equivalent right-handed render basis without changing physical volume. Concrete and
anchor capacities remain external. Stage 3.5B was subsequently implemented under its
own controlled contract and is included in the family freeze below.

### Stage 3.5A-R2 Material axes and three-component force

The strict `3.5A-R2-RC1` successor retains the accepted six-profile/1×1 geometry and
adds three signed wall-frame force inputs: Minor shear on `H_W`, Major shear on `V_W`,
and Axial force on `N_W`. User-applied moments remain prohibited. The backend shifts
the complete force from the connected-member reference to the wall origin using exact
`M + r × F` equilibrium and retains every generated moment in the external anchor
handoff.

Major plus Axial action may use the existing in-plane demand path only where its current
geometry/direction applicability holds. Nonzero Minor shear is retained as a common-group
bolt-axis action without invented tension or prying resistance and switches the external
handoff to combined-layout mode; no 50/50 Minor branch split is fabricated. Axial wall-leg
prying/contact partition and every nonmajor-force whole-connection qualification remain
explicitly `NOT_EVALUATED` or external-design-required.

The owner-reported material-axis defect was isolated to presentation: reflected
backend-authored `LW/CW/TT` bases cannot be represented by a rotation quaternion. TT
markers now use a proper render frame whose local normal is exactly the transported TT
vector. R14B material bases, properties, geometry, equations, results, and engineering
fingerprints are unchanged. Historical Stage 3.5A/R1 and all four frozen families remain
exact; Stage 3.5B was subsequently implemented under its own controlled contract.

### Stage 3.5B Direct side-lap Angle/Channel to concrete wall

The separate `3.5B-RC1` product places one finite horizontal FRP Angle or Channel
directly against the exterior face of a finite concrete wall. The wall stops at the
controlled free-end plane while the connected member continues beyond it. The Channel
web or one selected Angle leg owns the physical overlap; Channel flange contact and an
Angle orientation that embeds its free leg or heel fail closed.

Side-lap length changes only the physical overlap and member start. Anchor coordinates
remain fixed behind the wall free end unless the engineer explicitly chooses **Center
anchor group in overlap**. The backend owns profile placement, complete-hole containment,
the direct FRP-to-concrete anchor path, exterior-only blind-anchor hardware, material axes,
and the exact `M + r x F` anchor-group wrench for signed Axial, Major shear, and Minor
shear. User moments are prohibited.

Preview executes no resistance. Run Design Check may reuse only accepted applicable
FRP-local methods; a supported failure governs `FAIL`, but no ordinary whole-connection
`PASS` is issued. Minor/through-thickness action, pull-through, prying, out-of-plane
response, concrete resistance, anchor resistance, and final connection qualification
remain explicit `NOT_EVALUATED` or `EXTERNAL_DESIGN_REQUIRED` limitations in the
deterministic copy/download handoff.

### Stage 3.5C Column base using single/double web angles to concrete

Stage 3.5C adds a separate Column connection for one vertical W/I column, a
finite concrete base, and either one web angle or an exactly symmetric pair.
The backend owns the column-base frame, angle placement, bearing footprints,
web bolts, blind base anchors, material axes, action reference, component-demand
provenance, and deterministic external foundation/anchor handoff.

The owner-controlled component philosophy assigns 100% of compression `Pu` to
the column-web local transfer in web `LW` and independently assigns 100% to the
base-angle system in vertical-leg `CW`. Only a proven symmetric Double pair may
split that angle-system demand to `Pu/2` per branch. Those serial/conservative
component checks never sum into a doubled foundation reaction: the physical
foundation reaction contains `Pu` exactly once.

Only compression plus the two controlled shear components are accepted; uplift
and user moments are unavailable. Angle-body/heel compression, concrete bearing,
anchor resistance, web-normal bolt tension/prying, and unsupported whole-connection
qualification remain explicit limitations. Preview executes zero resistance and
Run Design Check remains explicit. Historical Stage 3.5 products and all four
frozen families remain exact; the beam web-splice family has not begun.

### Stage 3.5C-R2 Signed axial compression/uplift

The additive `3.5C-R2-RC1` contract replaces the current workspace's compression-
magnitude field with one signed axial force: positive is uplift along `+L_C`, negative
is compression along `-L_C`, and zero has no axial action. Historical `3.5C-RC1`
requests, results, handoffs, and fingerprints remain exact.

For either sign, the column web receives 100% of the signed axial action on web `LW`
and the base-angle system independently receives 100% on vertical-leg `CW`. An exactly
symmetric Double pair receives signed half actions only after symmetry proof. These are
serial component-design demands and never sum into a doubled foundation reaction; the
exact base wrench contains the signed column action once.

Uplift does not use column-end bearing. Angle-body/heel uplift transfer and horizontal-
leg prying remain `NOT_EVALUATED`; anchor tension and concrete uplift anchorage remain
`EXTERNAL_DESIGN_REQUIRED`. Preview executes no resistance and Run Design Check remains
explicit. No new reverse-load, prying, concrete, anchor, or moment method is introduced.
GitHub Actions run #83 passed all four Ubuntu/Windows backend/frontend jobs in
approximately 5m43s, and the owner completed final visual acceptance on 2026-08-29.
The beam web-splice family has not begun.

### Stage 3.5 Concrete-Support Shear Family freeze

The accepted Stage 3.5 product baseline is commit
`4c154b9d31e2a0100fd9f8c5cc90243e838a19c7`. The deterministic freeze manifest at
`docs/governance/STAGE_3_5_CONCRETE_SUPPORT_SHEAR_FAMILY_FREEZE_MANIFEST.json`
records the accepted 3.5A/R1/R2, 3.5B/R1, and 3.5C/R1/R2 chain, CI runs #76–#83,
owner visual acceptance, 28 controlled artifacts, 47 inherited authorities, exact
source/package/workflow identities, fingerprints, limitations, and successor policy.

The freeze is governance-only: production source, equations, controlled engineering
artifacts, dependencies, and workflows are unchanged. Its audit resolves the historical
freeze by annotated tag, explicitly supplied historical object, or `manifest_only`; it
never substitutes a successor `HEAD`. Beam-to-beam web splice is planned only and has
not begun.

### Stage 3.6A Symmetric Double Web Splice Plates

Stage 3.6A begins the Beam Splice family under strict contract `3.6A-RC1`. It models
two locked-identical collinear W/I beams separated by a positive physical end gap,
two locked-identical web splice plates on opposite web faces, and two distinct mirrored
Plate/Web/Plate through-bolt groups. Beam A and Beam B retain equal-and-opposite transfer
forces and separately shifted group-centroid moments. Each beam web receives 100% of its
interface demand, the plate pair receives 100% system demand, and each plate receives
50% only after exact symmetry proof.

The backend owns geometry, ordered layer paths, demands, material directions, statuses,
fingerprints, and visualization. Preview executes zero resistance and design remains
explicit. Splice-plate inter-group body capacity, common-bolt double-shear capacity,
minor-shear bolt-axis/prying response, flange splice, a single-plate mode, and user-applied
moment transfer are not authorized and prohibit ordinary unsupported PASS. The immutable
Stage 3.5 family freeze and every earlier freeze tag remain exact.

### Calculation Slice 4 — Chapter 7 Pure-Mode FRP Plate Strength Engine

Calculation Slice 4 adds a backend-only, reusable ASCE/SEI 74-23 Chapter 7 engine for
plate longitudinal/transverse tension, longitudinal compression rupture and buckling,
source-bounded combined-compression buckling, and in-plane shear rupture and buckling.
It consumes the existing adjusted-property and time-effect-factor traces, applies no
Section 2.4 adjustment internally, and retains exact Decimal U.S./SI identity and source
provenance. Commentary narrow/short-plate cautions remain advisories and never replace
the normative equations.

Pure transverse compression stability and combined compression outside
`0.3 <= xi_LT <= 1.0` fail closed to Section 2.3.2 authority. The revised Stage 3.6B
rational web-splice work remains paused; this slice is not wired into the historical
Stage 3.6A product, changes no frontend production source, and leaves every frozen family
and tag exact.

### Stage 3.6B RC2 — Web-Splice Resistance Completion

Stage 3.6B RC2 adds strict successor contract `3.6B-RC2` while retaining historical
`3.6A-RC1` requests, results, and fingerprints exactly. The successor derives each
unperforated clear plate body from the physical inner hole boundaries, evaluates the
left, joint, and right sections under the exact force and eccentric body moment, and
reuses the accepted Calculation Slice 4 Chapter 7 tension, compression/buckling, and
shear strengths without duplicating those equations. Combined normal/shear utilization
uses the controlled project-specific linear rational interaction and therefore requires
Section 2.3.2 qualification plus an engineer-of-record review; a complete supported
success is `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`, never an unqualified PASS.

Each Plate/Web/Plate bolt is proved as two physical shear planes and uses its actual
Stage 2.5A per-bolt demand. Source-authorized metallic `F_nv` may be evaluated through
the existing bolt-strength assembly; the default ASTM F593 case remains
`SOURCE_DATA_PENDING` with no invented strength. Preview remains resistance-free and
only Run Design Check executes resistance. Minor-shear bolt-axis response and user
flexural moment remain outside scope. Stage 3.5 and every earlier frozen family, plus
Calculation Slice 4 and Stage 3.6A historical identities, remain exact. GitHub Actions
run #87 passed all four hosted jobs in approximately 4m30s, and the owner directly
accepted the final W/I web-splice behavior on 2026-08-30.

### Stage 3.6 W/I Web-Splice Family freeze

The accepted Stage 3.6 product baseline is commit
`5f77abd0eeaf61718756e9962ae3a5a67d6db528`. The deterministic freeze manifest at
`docs/governance/STAGE_3_6_WI_WEB_SPLICE_FAMILY_FREEZE_MANIFEST.json`, SHA-256
`58AA05F545984EAAC0EDED666B4BA086BA05ADE40E59C39D3B7821BFFEB60658`, records the
Stage 3.6A / Calculation Slice 4 / Stage 3.6B RC2 chain, CI runs #85–#87, direct owner
acceptance, 12 controlled artifacts, 38 inherited authorities, exact source/package/
workflow identities and fingerprints, rational-method qualification/disclaimer, F593
source boundary, limitations, and successor policy.

This is a governance/reproducibility freeze only. It changes no production source,
calculation method, controlled engineering artifact, dependency, workflow, result, or
fingerprint. The successor-safe audit resolves the historical freeze by annotated tag,
explicitly supplied historical object, or `manifest_only`, reads raw commit headers for
shallow-safe parent verification, and never substitutes successor `HEAD`.

The frozen family is W/I-only. `CHANNEL_WEB_SPLICE` is explicitly outside the frozen
scope because a Channel centroid/reference axis is generally offset from its web plane;
Channel support requires a separate controlled successor with explicit eccentricity and
transfer-moment authority. No Channel work or later stage has begun.

### Stage 3.7A — Column-Base Profile Matrix Expansion

Stage 3.7A adds strict successor contract `3.7A-RC1` to the existing Column connection.
The normal workspace now supports W/I, RHS, SRS, and Angle columns with Single or Double
FRP base-angle assemblies. Historical `3.5C-RC1` and `3.5C-R2-RC1` W/I requests,
results, geometry, material bases, and fingerprints remain exact.

RHS and SRS reuse the accepted rectangular full-through architecture: one physical
bolt spans exterior to exterior, RHS cavity is a non-material free-shank interval, and
no internal hardware is rendered or credited. Angle columns use the exact backend
member centroid/reference; Single connects one selected-leg broad face and Double uses
opposite broad faces of that same selected leg. The other physical leg remains present,
and a different-leg moment topology is not exposed.

The column receives 100 percent of signed axial component demand in `LW`; the
base-angle system independently receives 100 percent in vertical-leg `CW`. Exact
pair sharing is proof-gated, complete Angle branch wrenches are not fabricated without
action symmetry, and the physical foundation reaction is counted once. Preview remains
resistance-free. Concrete/anchor capacity, angle-body/heel transfer, horizontal-leg
prying, unsupported normal response, and new resistance methods remain excluded.

### Stage 3.7 Column-Base Shear Family freeze

The accepted Stage 3.7 product baseline is
`0403bc8a4ace0df95b45a84a55832c17b18d6008`. Deterministic manifest
`docs/governance/STAGE_3_7_COLUMN_BASE_SHEAR_FAMILY_FREEZE_MANIFEST.json`, SHA-256
`8C7CD0238C7A95E54E4B6DC987E4A558AE2910DA80342137C7772B7FCF6EC9AE`, freezes the
W/I, RHS, SRS, and Angle by Single/Double shear-base matrix, including the accepted
Stage 3.7A-R1 negative-face Angle path, exact member references/eccentricity moments,
component-demand/foundation-once rules, material directions, external-design boundaries,
CI runs #89/#90, and owner acceptance.

This governance/reproducibility freeze changes no production source, engineering method,
controlled engineering artifact, dependency, workflow, result, or fingerprint. Its
successor-safe audit resolves an annotated tag, explicitly supplied historical object,
or `manifest_only`, reads the raw commit header for shallow-safe parent verification,
and never substitutes successor `HEAD`.

`ANGLE_COLUMN_TWO_DIFFERENT_LEGS_MOMENT_BASE` is explicitly outside the frozen scope.
That topology belongs to a future Moment Connections stage under separate authority and
has not begun.

### Calculation Slice 5 — W/I Moment Component Resultants

Calculation Slice 5 begins the Moment Connections program with a backend prerequisite
only. Strict method `RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1` reuses the
accepted exact W/I section geometry and Decimal quantity infrastructure to integrate a
linear-elastic major-axis normal-stress field over the top flange, web, and bottom
flange. Each region retains its complete reference, force, local moment, and global
moment contribution; major shear is assigned to the web; and exact force and moment
equilibrium are proved without a tolerance closure.

The result also reports stress extrema and state, the exact flange couple, residual web
moment participation, and full-moment `M/z` as a diagnostic reference only. The method
is a rational component-demand decomposition requiring qualified engineering review; it
is not a connection resistance, stiffness, qualification, or physical splice model.
Calculation Slice 5 is accepted and is frozen with Stage 4.1A. Frontend production is
unchanged, and no earlier frozen family, fingerprint, dependency, or workflow changed
under this slice.

### Stage 4.1A — W/I Major-Axis Moment Splice

Stage 4.1A accepts Calculation Slice 5 and adds the first physical Moment Connections
product under strict contract `4.1A-RC1`: `WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE`. Two
identical collinear W/I beams retain a positive end gap, two frozen-architecture web
splice plates, one full-width outer plate and two symmetric inner strips at each flange,
and independent physical web and flange bolt groups. The backend consumes the complete
Slice 5 top-flange, web, and bottom-flange wrenches; local flange and web moments are
retained, and full-moment `M/z` remains diagnostic only.

The flange system uses controlled methods
`RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1`,
`RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1`, and
`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`. Outer and inner plate force
lines recover each Slice 5 flange force and local moment exactly. Beam-flange face
sublayers receive rational local checks, plate bodies reuse Calculation Slice 4, and
each common bolt uses its actual unequal Stage 2.5A plane demands. ASTM F593 numerical
shear strength remains source-pending; bolt-axis tension and prying are not invented.

Preview remains resistance-free and design execution remains explicit. A supported
complete result can only be `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`; Section 2.3.2
qualification and the controlled report disclaimer remain mandatory. Rotational
stiffness, rotation capacity, and full-strength classification are `NOT_EVALUATED`.
Stage 4.1A changes no dependency, workflow, or frozen historical contract. GitHub
Actions run #93 passed all four Ubuntu/Windows backend/frontend jobs, and owner visual
acceptance is complete. Channel moment-splice support remains future Stage 4.1B under
separate authority.

### Stage 4.1A freeze — W/I Major-Axis Moment Splice

The accepted Stage 4.1A product baseline is
`59713e53c522a6a301e19e458559986fb114d735`. The deterministic freeze manifest at
`docs/governance/STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_FREEZE_MANIFEST.json`, SHA-256
`A77FACD1A05F60E947F3F394FCFB3FC5D28120922BF6EA9841E4EC9C80D4061F`, freezes both
Calculation Slice 5 and the physical W/I moment-splice architecture. It records the
balanced outer-plus-two-split-inner flange topology, retained web free moment, actual
unequal two-plane bolt demand, rational-review/Section 2.3.2 boundary, source-pending
F593 behavior, exact fingerprints, accepted visual cases, and immutable predecessors.

The successor-safe audit resolves only the annotated tag, an explicitly supplied exact
historical object, or `manifest_only`; it reads the raw commit header for shallow-safe
parent proof and never substitutes successor `HEAD`. The freeze changes zero production
source, engineering method, controlled engineering artifact, dependency, or workflow.
Stiffness, rotation, full-strength classification, and prying remain unevaluated.
Stage 4.1B Channel Moment Splice was not begun.

### Calculation Slice 6 — Channel Moment References and Component Resultants

Calculation Slice 6 begins the backend prerequisite for the future Stage 4.1B Channel
Moment Splice under strict contract `CS6-RC1` and method
`RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1`. It reuses the accepted
Channel profile geometry and exact Decimal quantity architecture, derives the exact
member centroid and web-plane eccentricity, and requires either the controlled rational
median shear-center method or an explicit qualified shear-center value with provenance.

Axial force, major shear, minor shear, major-axis moment, minor-axis moment, and torsion
are decomposed into complete top-flange, web, and bottom-flange wrenches. All reference
shifts and generated torsion are retained, and exact equilibrium is proved at the
canonical member-centroid reference. Stress extrema, flange-couple, residual, rational
shear-flow, and full-section stress references are diagnostic only. The result contains
no resistance or physical connection geometry. The Stage 4.1A freeze remains exact;
physical Stage 4.1B remains pending separate authority.

### Stage 4.1B — Channel Major-Axis Moment Splice

Stage 4.1B accepts Calculation Slice 6 and adds the separately versioned
`CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE` product under strict contract `4.1B-RC1`.
Two identical collinear Channels open in `+T_CH` across a positive gap. The physical
connection has one back and one opening-side web plate plus one outer and one inner
plate at each flange; every bolt retains its backend-authored three-layer path.

The backend consumes the complete Slice 6 top-flange, web, and bottom-flange wrenches.
It retains the member centroid, selected shear center, every transverse eccentricity,
and generated centroidal torsion. Flange force lines reuse the frozen Stage 4.1A
decomposition. The two web faces use the controlled rational shear-center couple, so
their major-shear branches are independently solved and may be opposite in sign; no
blind 50/50 split is used.

Local FRP checks reuse the established multi-row engine, plate bodies reuse Calculation
Slice 4 and the Stage 3.6B rational interaction, and common bolts reuse actual Stage
2.5A per-plane demand. Source-pending ASTM F593 strength remains source-pending.
Preview is resistance-free, design execution is explicit, and supported completion is
review-qualified only. Open-section warping/torsional resistance, prying, bolt tension,
stiffness, rotation capacity, and full-strength classification remain unevaluated.

### Stage 4.1 Beam Moment Splice Family freeze

The accepted family baseline is `6d953dbef648bd35ab21b5208432579cdeb59902`, including
Calculation Slices 5/6, the W/I and Channel physical moment-splice products, and the
Channel R1 workspace bootstrap correction. Owner visual acceptance is complete and
the controlling freeze order records four green jobs for CI #93–#97 (Slice 6 #95,
attempt 6); Slice 5 #92 acceptance is retained from the existing W/I freeze evidence.

The [family manifest](docs/governance/STAGE_4_1_BEAM_MOMENT_SPLICE_FAMILY_FREEZE_MANIFEST.json)
is SHA-256 `2C79F811EECFD89C04862359E583A240284872C10A0603E3D6CA276D657CED77`.
It freezes exact source/artifact/fingerprint identities, complete component wrenches,
W/I split-inner flange plates, Channel shear-center/torsion and unequal web branches,
actual unequal bolt-plane demands, review-qualified results, and all limitations.
The R1 nonblank-root and explicit preview/design separation are frozen behavior.

This governance-only freeze changes no production, engineering, controlled artifact,
dependency, lockfile, workflow, or existing tag. The historical Stage 4.1A tag and all
seven earlier tags remain immutable. The new annotated family tag is
`stage-4.1-beam-moment-splice-family-freeze`; publication follows full local and
object-isolated QA. Its own hosted CI remains pending direct four-job evidence.
See the [freeze QA record](docs/qa/STAGE_4_1_BEAM_MOMENT_SPLICE_FAMILY_FREEZE.md).
No next moment-connection family is selected or begun by this order.

### Calculation Slice 8 — backend in-plane wrench demand

The additive `calculation.in_plane_wrench_demand` module accepts ordered physical
bolts, an explicit reference and the complete signed `(F_A,F_B,M_C,R)` wrench.
It supports independent/pure moment using exact rational equal-stiffness mechanics
and four exact recovery proofs. Decimal-80 / `ROUND_HALF_EVEN` output is a
downstream projection only. The RC1-R1 golden replaces the unimplemented original
golden; Stage 2.5A retains its accepted warning, pure-moment boundary, numerical
path and fingerprints. All historical production and freeze tags remain unchanged.
There is no frontend/API product or resistance addition, and physical Stage 4.2
has not begun. See the [Slice 8 QA and API record](docs/qa/CALCULATION_SLICE_8_IN_PLANE_WRENCH_DEMAND_RC1_R1.md)
for controlled hashes, mechanics compatibility and publication gates.

## Stage 4.3 accepted freeze registration

Accepted engineering implementation `2e4416a4dbd0b99c6a7280f6576264c37c09101a`; security successor `513e1c9150e63206e432a8d2f971617b6ed9c203`; current tests-only successor/baseline `36f6049c09b3df29ea899af826fbba19f26496b3` (112 commits). Engineering CI #105 attempt 2, security CI #106 attempt 2, and baseline CI #107 attempt 1 are accepted four-job SUCCESS. Owner final visual/result acceptance is ACCEPTED.

Manifest: `docs/governance/STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_FREEZE_MANIFEST.json`, SHA-256 `F120A681C4F85B36EA7519F46E16567F4913C5A181D1BDD6AF07F6CA1E6CC7F0`. See `docs/qa/STAGE_4_3_FREEZE.md`. Status FROZEN activates only after complete governance QA, fresh object-isolated verification, normal main push, direct governance CI 4/4, and verified annotated tag `stage-4.3-wi-beam-frp-support-moment-connection-freeze`. Post-commit evidence is external; SELF is the governance commit with parent `c59ead41acf7e2507842de86fca2a578ee8cb8e3` and expected count 114.

All five receiving configurations (W/I flange, W/I web, hollow square, solid square, Channel web) remain exact. Complete native dependency wrenches, material directions, actual through-bolt paths, native failure/source traces and qualified support-response boundaries are unchanged. In-plane projection does not establish normal tension/contact/prying response; unavailable is not zero. Hollow walls do not automatically share load or confer double-shear capacity; full solid depth is not a thin plate. Whole receiving-member design remains `NOT_EVALUATED_CONNECTION_CONTRIBUTION_ONLY`. No ordinary PASS, new qualified source, Stage 4.4/4.5, or 316SS authority is created.

The original governance successor changed no production, engineering, dependency, workflow, test, controlled artifact or existing tag. Prior implementation records are historical; this separate acceptance entry is current.

## Windows CI stabilization and final freeze target

Finalization supersedes only the prior freeze publication target: first governance commit `c59ead41acf7e2507842de86fca2a578ee8cb8e3` (count 113) had CI #108 attempt 2 with three green jobs and two Windows 5000 ms frontend timeouts. Final SELF has parent `c59ead41acf7e2507842de86fca2a578ee8cb8e3`, exact subject `test: stabilize Windows Stage 4.3 freeze timeouts`, and count 114. Only the two named tests receive local 15000 ms limits; `backend/tests/calculation/test_scope_boundaries.py` authenticates their exact timeout-only successors while preserving the original historical digest and tamper detection. Both tests passed 10 consecutive Windows runs. Production, engineering, controlled artifacts, dependencies, workflows and all ten existing tags remain unchanged. The final annotated freeze tag targets SELF only after complete local/object-isolated QA and direct hosted four-job SUCCESS; final run/tag evidence is recorded externally without amendment.

Finalization Order R1 SHA-256: `1397BC0FC17BD4C67D79FE3DFFB20A94818621FB091D309BD167DF81ADDF27F9`. Final manifest SHA-256: `F120A681C4F85B36EA7519F46E16567F4913C5A181D1BDD6AF07F6CA1E6CC7F0`.

## Stage 4.4 angle-column two-leg moment base freeze

Engineering implementation `e8bc2355bcecaabd70d31332cf1af3ee6eb17712` (115); accepted preview/state correction `d11012e771556f0ed5cac46f39ab40cb0a53273e` (116). Owner acceptance: **Stage 4.4 visual accepted**. Product CI #111 attempt 1 is four-job SUCCESS. The bounded tests-only scope-guard successor `388083ba0ae26be5de6bea986c668252db56adbb` (117) passed complete local/object-isolated QA and CI #112 attempt 1, four-job SUCCESS.

The frozen contract is `ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION` / `4.4-RC1`: one equal- or unequal-leg FRP angle column and two exterior base angles on different legs. Total required foundation actions, including reference-generated Mz, remain exact; no 50/50 branch allocation or doubled direct-contact reaction is introduced. Unknown branch/contact response remains source-required, foundation/anchor capacity remains external, and the corrected current/LAST VALID preview behavior is preserved.

Manifest: `docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json`, SHA-256 `2035E881712086643440D67A4F78D142886F749F90BCEA285B01A2E7E37C9443`. Freeze order SHA-256: `21FA8D17DCBBDE6ED6BA2C93892D5343347E5FE521EB2ACB98578E89F86A8836`. See `docs/qa/STAGE_4_4_FREEZE.md`.

Freeze publication is gated: SELF is the governance commit with parent `388083ba0ae26be5de6bea986c668252db56adbb`, exact subject `chore: freeze Stage 4.4 angle-column two-leg moment base baseline`, and expected count 118. Stage 4.4 becomes FROZEN only after complete governance local/object-isolated QA, normal main push, direct governance four-job CI SUCCESS and verified annotated tag `stage-4.4-angle-column-two-leg-moment-base-freeze` (annotation: `Stage 4.4 angle-column two-leg moment base freeze`). Post-commit evidence records actual objects and run/job URLs externally without amendment or circular self-hashes.

This governance commit changes no production, engineering, tests, dependencies, workflows, controlled engineering artifacts or existing tags. Stage 4.5 and 316SS remain unstarted.

## CME-2C C2-P2 isolated implementation

Additive internal clear-plate E3/F9/H2 provider from baseline `20fabefa90247dd3470d4698edda1b22d017e7c6` (128). See `docs/architecture/CME_2C_ISOLATED_CLEAR_PLATE_PROVIDER.md` for trusted pre-resolved frozen C2-M/P1 snapshots, the owner-approved raw-traced E3 Fy cap, native numerical authority, fail-closed boundaries and publication gates. Frozen production/tests and all fifteen tags remain unchanged; no public API, frontend, hardware or family material activation. One implementation commit is expected at count 129; exact-SHA hosted four-job verification is recorded externally after normal push. No new freeze tag or later-stage work.
