# SSMC-2 stair stringer miter geometry/demand freeze

## Identity and acceptance

Status: accepted SSMC-2 RC1 geometry/demand engineering-review scope, subject to the publication gates below.

- Engineering implementation parent: `07444a4c88899bab2dc75de3cdea63c657cbfd43`.
- Accepted green candidate: `dfc735f29887edbcdfc6a389c270230d414445ab`, continuation count 6.
- Annotated tag: `ssmc-2-stair-stringer-miter-demand-freeze`.
- Annotation: `Freeze SSMC-2 stair stringer miter geometry and demand RC1`.
- Tag object: `d496fb5dd5c887adce65c96481425aa023e5a11d`; peeled target is the accepted green candidate, not the engineering parent and not this governance successor.
- Acceptance: `SSMC_2_ACCEPTANCE_PASSED`.
- External acceptance report: `SSMC_2_ACCEPTANCE_REPORT.md`, SHA-256 `9B2E068DD2DA92A342BD0FA5326165B9FCFC71449241FAC8D8CC171B0AD35896`.
- Controlling acceptance/freeze order SHA-256: `4BB0C96CA76D18776780EF5AFFA0C0FB5E87F87497D944085A627A07ABB0A431`; final sentinel verified.
- Implementation/stabilization CI: run `35659065255`, attempt 1, exact candidate SHA; Backend Ubuntu/Windows and Frontend Ubuntu/Windows all passed.

The only stabilization delta from `07444a4c88899bab2dc75de3cdea63c657cbfd43` to the accepted candidate is `frontend/tests/ssmcWorkspace.test.tsx`. It preserves and strengthens the original field-edit, group-independence, no-linking and no-repair assertions through deterministic sequencing. No production or engineering behavior changed.

## Frozen SSMC-2 RC1 scope

This is an **SSMC-2 geometry/demand engineering-review freeze**. It is **NOT complete moment-capacity qualification**.

The single `stair-stringer-miter` route retains one continuous FRP web-following polygon plate on one side of ordered Channel/W-I stringers. The public domain remains `+/-30`, `+/-35`, and `+/-45` degrees. Global X remains horizontal, Y remains out of the stair plane, and Z remains vertical. The plate is FRP only; SSMC has no SS316 connector-body selector.

Equal and unequal profiles use the same clarified construction: the web-middepth datum-line work point, outward-retained-member-axis miter normal, parallel `+/-g/2` cut planes, two actual branch polygons, exact transition quadrilateral, transition-derived gross neck, and explicit boundary ownership. Convex hulls, bounding rectangles, hidden translations and automatic geometry repair are excluded.

Signed local N/V/M is transported exactly. The horizontal and inclined 2x2/3x2 web groups are serial and each receives its complete appropriate transported wrench at its own reference. No action halving, axial-row mixing, discarded secondary moment or hidden balancing mechanism is frozen. Native Slice-8 bounded planar group demand is used only within its eligibility boundary.

The complete trusted response registry remains empty. Public source text cannot activate authority. Connector-plate policy remains `MITER_PLATE_CW_BASIS_UNKNOWN_CUT`, isolated to the plate and without LW fallback or rewritten member material axes. Hardware remains independent and receives no automatic double-shear multiplier.

Separate Geometry, Demand, Planar group response, Complete response, Plate resistance, Member local transfer, Hardware, Qualification and Design statuses remain authoritative. Evaluated numerical failure outranks missing qualification; otherwise any unresolved required check retains `ENGINEERING_REVIEW_REQUIRED`. LAST VALID presentation hides stale arrows and recovers automatically when valid input is restored.

## Explicit unresolved and fail-closed boundaries

The following are not qualified by this freeze and remain visibly fail-closed:

- complete single-sided response, `SSMC_SINGLE_SIDE_RESPONSE_NOT_QUALIFIED`;
- arbitrary-polygon combined resistance and stability, `SSMC_POLYGON_RESISTANCE_NOT_QUALIFIED`;
- local member flange-to-web transfer/resistance, `SSMC_MEMBER_FLANGE_WEB_TRANSFER_NOT_QUALIFIED`;
- combined hardware response, `SSMC_HARDWARE_COMBINED_RESPONSE_NOT_QUALIFIED`;
- qualified connector-plate CW/TT/flexural/stiffness material data.

No ordinary complete moment-capacity PASS, new resistance method or additional source qualification is granted.

## Accepted test and runtime authority

- Backend: 7,267 tests executed exactly once across four deterministic shards; canonical node-ID SHA-256 `EB21B4B287DFC4E59AA6BC20151DEFCC0179A995BE4C301DBC966F7EFB48DE08`; configured statement/branch coverage 100%.
- Frontend: 65 files / 1,052 tests; statement, branch, function and line coverage each 100%.
- SSMC-2: 32 positive / 40 negative-fail-closed / 22 invariant cases.
- Independent geometry: 2,304 fixtures, 92,160 disk checks, 576 native trims and 5 rejection fixtures; evidence SHA-256 `11130F347427ADD4EB7456C614EE4DB3BD7BE2C197987BAC61CE6AD198EED32C`.
- Parent regression: 17 predecessor routes / 102 exact comparisons / zero differences; evidence SHA-256 `4B09854D5D02D3AB9B91146E067D71F894F608440F57A045424CD2D371883EE2`.
- Ruff formatting/lint, strict mypy, pip/runtime checks, ESLint, strict TypeScript, production build, full/runtime audits and fresh depth-one no-tags/no-alternates verification passed.
- Browser acceptance covered all four ordered member-form pairs, both plate sides, all signed domain angles, both row topologies, N/V/M signs and combinations, native U.S./S.I. presentation, fail-closed trace, LAST VALID recovery, action hiding and no-SS316 experience, with zero console errors.

## Preserved repositories and prior freeze

The existing continuation tag `dctn-3b-double-channel-truss-node-freeze` remains object `cf33dd5b939bbed35cb8bb1b770d9fe929e9152e`, peeled implementation `d556585c1b905532431e4ec9b7be9ab23acabc10`. No historical archive tag is imported.

The archived repository remains clean at `5a391ce68cb04fba3df20f5bd3b57a01fd05da19`, commit count 139, with all 18 historical annotated-tag objects and peeled targets unchanged.

## Change control and publication gates

This governance record changes no production code, frontend code, engineering test, golden, dependency, lockfile, workflow, provider, route, calculation, default, source authority or existing tag.

Governance subject: `chore: record SSMC-2 miter demand freeze`; expected continuation count 7. Complete post-governance QA must pass before publication. Push continuation `main` normally, then explicitly push only `ssmc-2-stair-stringer-miter-demand-freeze`.

Freeze completion additionally requires synchronized local/remote governance main, two continuation tags, the SSMC tag peeling exactly to `dfc735f29887edbcdfc6a389c270230d414445ab`, unchanged DCTN and archive identities, a clean tree/index, and direct exact-governance-SHA hosted success for the complete Ubuntu/Windows backend/frontend logical gate. Post-publication evidence is recorded externally without amendment or circular self-hashes.
