# Stage 3.3C2-R2 Connected-RHS Through-Bolt Orientation Correction

## Authority and baseline

The controlling external order was read completely and verified at SHA-256
`AC10A10D186385741BDE0E1ECB4671615DC688E4E71E2556445890669EDF6997`, including its
final sentinel. Work began from clean synchronized `main` commit
`8ead20714ff18cfc383d0bcd8fa422eeaf3c90bf`. The Stage 2.3 and Stage 3.2 immutable
freeze tags remained exact.

## Four-case pre-mutation audit

The accepted C2-R1 backend already produced the correct engineering bolt axis, selected
and opposite rectangular faces, ordered path, containment, hardware semantics, demand,
and fingerprint. The first bolt in each required comparison was:

| Case | Bolt | Engineering axis | Physical start | Physical end | Existing scene growth |
| --- | --- | --- | --- | --- | --- |
| Single connected RHS | `CLIP-A-R1-B1` | `(1,0,0)` | `(0.5,1.25,-1)` | `(-6,1.25,-1)` | Wrong `+X` |
| Tee connected RHS | `A_B_R1_L1` | `(0,-1,0)` | `(3.5,-0.25,-3)` | `(3.5,6.25,-3)` | Wrong `-Y` |
| Single support RHS | `CLIP-B-R1-B1` | `(0,-1,0)` | `(1.25,0.5,-1)` | `(1.25,-6,-1)` | Correct `-Y` |
| Tee support RHS | `B_B_R1_L1` | `(-1,0,0)` | `(0.5,-1,-3)` | `(-6,-1,-3)` | Correct `-X` |

Every case retained the exact connector, near-wall, cavity, and far-wall traversal.
The connected segment plane order is connector `ENTRY -> EXIT`, `Z_POS_FACE ->
Z_POS_FACE:INNER`, `Z_POS_FACE:INNER -> Z_NEG_FACE:INNER`, and `Z_NEG_FACE:INNER ->
Z_NEG_FACE`. Support cases use the same rectangular plane order with their accepted
connector identity. The 6.5-inch span contains 0.5-inch connector, 0.5-inch near wall,
5-inch free cavity, and 0.5-inch far wall. Head and near washer remain on
`EXTERIOR_NEAR_SIDE`; nut and far washer remain on `EXTERIOR_FAR_SIDE`; internal
hardware count remains zero.

## First mismatch and correction

The backend preview trace carried a scalar shank length but no global physical
head-side/nut-side endpoints. The shared frontend `applyFullThroughBoltSpans` adapter
therefore took the historical `stack_end - stack_start` engineering direction and
computed `start + direction * shank_length`. That coincided with ordered physical growth
for the two support controls and reversed it for both connected-RHS cases. Head/nut
presentation then correctly followed the already-wrong shank endpoints.

The shared backend integration trace now carries `physical_start_point` and
`physical_end_point`. They are derived from the actual placed RHS/SRS profile, selected
exterior face, opposite exterior face, bolt UV, section datum, and connector thickness.
The frontend derives shank center, direction, and length only from these transported
decimal-string endpoints and relocates existing authority-provided exterior washers to
the matching ends. No family-specific frontend offset, sign flip, clamping, rounding,
or duplicate geometry authority was added. A missing placed profile or malformed
transport endpoint fails closed.

## Engineering invariance

C2-R1 engineering paths were already correct. R2 changes zero path segment, bolt center,
engineering axis, demand/resistance input, containment result, limitation, or
fingerprint input. Exact current fingerprints remain:

- Tee connected RHS: `a089c44a4652b207ff1145d8a5790154855c1078cf006a6022c8d649f947a6f9`
- Single Brace connected RHS: `16ae7ce854c5b5b4d34da713373bcf5924f5fc411687e5dc0a765928e5db3288`
- Single Beam connected RHS: `1c995ab0e90b76cd405bff1c5f4990bef2fdbba83e12daac47dffd9fbace7c51`
- Tee RHS support: `5eb5ce6e2a9bffe2a94dedd5ac2b18af82197f4b4fbeace35e85519c2275a239`
- Single RHS support: `20d54cebf9ea15decc83cc2d2c91b558eb3bbcd317f2cd26f2f4930a9f3e6586`

Connected SRS uses the same endpoint contract without a behavior transition. Open
sections bypass the full-through adapter and remain exact. Trim continues to use current
backend-authored member geometry; a valid trim does not change the retained
cross-section endpoints at a contained bolt location.

## Verification evidence

- Focused gates: 54 existing C2 plus new R2 backend tests and 80 focused frontend/client
  tests passed during implementation.
- Full backend: 2,297 tests passed with exact 100% coverage over 16,619 statements and
  4,990 branches; Ruff formatting/lint and strict mypy passed.
- Full frontend: 381 tests across 26 files passed with exact 100% coverage over 2,557
  statements, 2,222 branches, 858 functions, and 2,088 lines; ESLint, strict TypeScript,
  and production build passed.
- The integrated clean-index gate passed the same complete backend/frontend suites,
  both zero-vulnerability dependency audits, JSON and whitespace checks, and the
  repository staging guard.
- C1 G1-G12, C2 G1-G18, Direct, frozen non-RHS Tee, Stage 3.3A R1-R4, Stage 3.3B,
  connected SRS, support RHS, open-section, trim, material-axis, current/last-valid,
  navigation, strict-version, controlled-hash, and freeze regressions remain mandatory
  parts of complete and object-isolated QA.
- Dependencies, package/lock, workflows, controlled engineering artifacts, equations,
  and freeze tags changed zero times. Stage 3.3C3 is not started.

Object-isolated, push, hosted-CI, and post-CI visual evidence is recorded only after its
respective gate; none is inferred here.
