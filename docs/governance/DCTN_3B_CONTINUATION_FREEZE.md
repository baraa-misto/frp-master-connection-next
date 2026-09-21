# DCTN-3B continuation-repository freeze

## Identity and acceptance

Status: accepted DCTN-3B RC1 scope, subject to the publication gates below.

- Continuation root: `27cb9c908ca648566b3b6d3d2e19dd9be1e1df98`.
- Archived source snapshot: `5a391ce68cb04fba3df20f5bd3b57a01fd05da19` in `https://github.com/baraa-misto/frp-master-connection.git`.
- Accepted continuation implementation: `d556585c1b905532431e4ec9b7be9ab23acabc10`, count 3.
- Annotated tag: `dctn-3b-double-channel-truss-node-freeze`.
- Annotation: `Freeze DCTN-3B Double-Channel Truss Node RC1`.
- Tag object: `cf33dd5b939bbed35cb8bb1b770d9fe929e9152e`; peeled target is the accepted continuation implementation, not this governance successor and not the archived source snapshot.
- Acceptance: `DCTN_3B_CONTINUATION_ACCEPTANCE_PASSED`.
- External acceptance report: `DCTN_3B_CONTINUATION_ACCEPTANCE_REPORT.md`, SHA-256 `752864DD45CF1A74FFD34455F9B0B13D5308D149C395C721F5E16C0627D448A2`.
- Controlling order SHA-256: `1E431F4C1D8817658B2C25E0B876907D20351B01D3C013E4A529A11BE6D5AD9D`; final sentinel verified.
- Implementation CI: run `35548324063`, run number 3, attempt 1, exact accepted SHA; Backend Ubuntu/Windows and Frontend Ubuntu/Windows all passed.

The continuation repository intentionally has fresh Git history and no imported historical tags. Historical authority remains in the archived repository. Its main remains `5a391ce68cb04fba3df20f5bd3b57a01fd05da19`; all 18 archived annotated-tag objects and peeled targets were directly reverified unchanged.

## Frozen DCTN-3B RC1 scope

The single `double-channel-truss-node` route retains five arrangements: vertical only, one inclined, two inclined, vertical plus one inclined, and vertical plus two inclined. Incoming member forms remain RHS, solid rectangle, and W/I. DCTN has no connector body and no CME-3 material selector.

Channel-relative public placement is `Member Horizontal Location` and `Member Vertical Location`; global START coordinates are derived/read-only. The Z-up frame, degree-based inclinations, canonical local `P`, `Qp`, `Qq`, exact global wrench transport, generated moments, physical shaft identities, 0.563-inch/14.3002-mm startup-hole authority, and selected-unit trace are preserved.

Historical P-only response remains exactly `DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1`, including complete-symmetry half sharing and existing one-, two-, and three-row fractions. RHS/SRS retain one common full-through shaft per row. W/I retains two independent centro-symmetric mirrored-side bolts per row.

Any nonzero `Qp` or `Qq` calculates demand and generated moments but remains fail-closed under `DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED`. No automatic transverse Channel sharing, row sharing, contact, bolt tension, prying, or local resistance is frozen. The complete-response production registry remains empty; typed source text is not qualification. Global Channel/member/truss design remains outside the local connection scope.

The accepted UI keeps separate Geometry, Demand, Response, Qualification, and Design statuses; selected-member action labels with optional all-member overlay; native major/minor or equal-axis p/q names without swapping stored `Qp/Qq`; Advanced qualification/source controls; concise selected-unit cards with exact trace; and LAST VALID behavior with stale arrows hidden and automatic recovery.

## Accepted test and runtime authority

- Backend: 6,609 tests, executed exactly once across four deterministic shards; collection digest `C73BD9F22BCE23B389A155BC64CAAB723777D26A1589F7E218833A55780D3903`; combined line and branch coverage 100%.
- Frontend: 62 files / 1,016 tests; statements, branches, functions, and lines each 100%.
- DCTN-3B: 36 positive / 34 negative / 22 invariant cases.
- DCTN-2: 24 positive / 26 negative / 18 invariant cases.
- All 16 old public routes and historical/frozen authorities remain regression-covered.
- Ruff formatting/lint, strict mypy, pip checks, runtime/import smoke, ESLint, strict TypeScript, production build, dependency tree, full audit, and runtime audit passed with zero findings.
- Fresh depth-one, no-tags, no-alternates verification passed at the accepted SHA.
- Browser acceptance covered all five arrangements, RHS/SRS/W-I ownership, nonzero P/Qp/Qq, U.S./S.I. paths, reversed/equal axes, fail-closed response, LAST VALID recovery, qualification controls, action overlays, request completion, and rendered 3D scene. No console error, failed application request, blank root, or scene/runtime defect occurred.

## Change control and publication gates

This record changes no production code, frontend behavior, engineering test, golden, dependency, lockfile, workflow, provider, route, or numerical authority. It does not qualify transverse response or authorize a later DCTN extension.

Governance subject: `chore: record DCTN-3B continuation freeze`; expected continuation count 4. Complete post-governance QA must pass before publication. Push continuation `main` normally, then explicitly push only `dctn-3b-double-channel-truss-node-freeze`. Never copy the 18 archived tags into the continuation repository.

Freeze completion additionally requires synchronized local/remote governance main, one continuation tag peeling exactly to `d556585c1b905532431e4ec9b7be9ab23acabc10`, unchanged archive main/tags, a clean tree/index, and direct exact-governance-SHA hosted CI success for the complete current Ubuntu/Windows backend/frontend logical gate. Final publication evidence is recorded externally without amendment or circular self-hashes.
