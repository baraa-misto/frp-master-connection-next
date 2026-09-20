# FRP Master Connection — Stage 4.5 Windows Frontend Timing Correction — Order R3

**RECOMMENDED CODEX EFFORT:** MEDIUM

## Purpose

Resolve the repeated hosted Windows frontend 5-second timing failures blocking acceptance of the already-pushed Stage 4.5 R2 correction.

This is a **tests-only CI stabilization successor**.

Do not change Stage 4.5 production code, engineering behavior, defaults, geometry, acceptance authority, dependencies, workflows, or existing freeze tags.

Do not freeze Stage 4.5 in this order.

## 1. Starting baseline

Require exactly:

`HEAD == origin/main == remote main == 36f4979e2a4e1ef4cf144c9640974614e18bce03`

Expected subject:

`fix: center Stage 4.5 base angles and use two member bolts`

Expected commit count:

`121`

Require clean worktree/index.

Accepted local/object-isolated verification already passed:

- backend: `5,021` tests;
- frontend: `848` tests;
- configured coverage: `100%`;
- static/build checks passed;
- full/runtime audits: zero findings;
- browser review passed;
- all twelve existing freeze tags unchanged.

## 2. Hosted CI evidence

GitHub Actions run:

`#116`

attempt:

`2`

Three jobs remain green:

- Backend Ubuntu PASS
- Backend Windows PASS
- Frontend Ubuntu PASS

Frontend Windows failed only because five parameterized cases in:

`tests/columnMomentBaseR1.test.tsx:19`

exceeded the default `5000 ms` timeout.

Observed cases:

- RHS `MY`: approximately `5290 ms`
- SRS `FX`: approximately `5057 ms`
- SRS `FY`: approximately `5306 ms`
- SRS `FZ`: approximately `5232 ms`
- SRS `MX`: approximately `5356 ms`

Hosted frontend result:

`843/848 passed`

No assertion failure was reported.

The single ordinary retry is exhausted.

## 3. Mandatory diagnosis before mutation

Inspect the complete parameterized test at `tests/columnMomentBaseR1.test.tsx:19`.

Confirm read-only that:

- no assertion failed before timeout;
- no application, request, network, runtime, or console defect explains the failures;
- no deadlock or infinite wait exists;
- the test legitimately performs enough DOM/user-event work that the hosted Windows 5-second budget is marginal;
- the same cases pass under unchanged production code with additional time;
- all five failing parameter sets exercise the same valid test body rather than five different product defects.

If any real product/application/engineering defect is found:

**STOP before mutation and report one consolidated diagnosis.**

If timing-only, proceed without further owner approval.

## 4. Authorized timing correction

Because all five failures belong to the same parameterized test body, the preferred correction is:

- apply a **single per-test timeout of `15000 ms`** to the parameterized Stage 4.5 test at `columnMomentBaseR1.test.tsx:19`.

This authorization intentionally exceeds the previous three-case timing-maintenance limit for this one known parameterized test.

Do not create five separate sleeps or five independent timing hacks.

Do not:

- change global Vitest timeout;
- add arbitrary sleeps;
- remove/weaken assertions;
- skip/disable/xfail tests;
- alter test inputs/expected values;
- change production code;
- change engineering code;
- change Stage 4.5 acceptance matrix merely to satisfy timing;
- change dependencies/lockfiles/workflows;
- change existing freeze tags.

## 5. Stability gate

After the local per-test timeout correction, on Windows require:

- `10/10` consecutive passes of the complete targeted parameterized test;
- all parameter sets in that test pass on every run;
- no assertion failures;
- no console/runtime/application failures.

Also record elapsed times for the five previously failing cases.

If any case still times out within 15 seconds:

**STOP rather than increasing the timeout again.**

## 6. Full regression QA

Require:

### Backend
- full suite;
- 100% configured coverage;
- Ruff;
- strict mypy.

### Frontend
- full suite;
- 100% configured coverage;
- ESLint;
- strict TypeScript;
- production build.

### Security / engineering
- `pip check`;
- full npm audit zero;
- runtime npm audit zero;
- Stage 4.5 acceptance matrix;
- all 24 reference fixtures;
- prescribed source-absent/source-present sweeps;
- Slice 7 / Slice 8 / Stage 2.5A regressions;
- Stage 4.4 freeze regression;
- all twelve historical freeze audits;
- all accepted Stage 4.5 R1/R2 UI/default/centering/action-sign regressions.

No new browser owner review is required for this tests-only timing successor, but a local Stage 4.5 smoke check may be run if useful.

## 7. Scope gate

Before commit prove:

- frontend production changed paths: `0`;
- backend production changed paths: `0`;
- engineering artifacts changed paths: `0`;
- acceptance-matrix changed paths: `0`;
- dependency changes: `0`;
- workflow changes: `0`;
- tag changes: `0`.

Expected changed production-repository path:

`tests/columnMomentBaseR1.test.tsx`

plus only narrowly required tests-only successor-safety maintenance if an already-known historical scope guard blocks this exact authorized timeout change.

Standing repository-wide successor-safety authority for that known tests-only pattern remains valid.

## 8. Commit

Create a new successor commit exactly:

`test: stabilize Windows Stage 4.5 parameterized timing`

Do not amend:

`36f4979e2a4e1ef4cf144c9640974614e18bce03`

Expected final commit count:

`122`

No tag.

## 9. Object-isolated verification

After commit:

- fresh depth-one / no-tags / no-alternates clone;
- complete QA;
- targeted parameterized timing test;
- clean tree;
- authorized diff scope only.

Failure:

**STOP before push.**

## 10. Push and hosted CI

After successful object-isolated verification, owner authorizes a normal non-force push of the exact successor to `main`.

No tags.

Verify:

`HEAD == origin/main == remote main`

Then obtain direct hosted CI:

- Backend Ubuntu PASS
- Backend Windows PASS
- Frontend Ubuntu PASS
- Frontend Windows PASS

Do not apply any further timing correction automatically if a different failure appears.

## 11. Stage 4.5 acceptance state

After direct hosted 4/4 green:

- the Stage 4.5 engineering/product correction baseline remains `36f4979...`;
- the count-122 successor is tests-only timing maintenance;
- production behavior remains unchanged;
- Stage 4.5 still requires owner final visual/result acceptance before freeze.

Leave the application running if already available.

Do not begin freeze, 316SS, or another stage.

## 12. Completion report

Report:

1. starting baseline/count;
2. diagnosis of the parameterized test;
3. exact timeout change;
4. five previously failing case runtimes;
5. 10/10 Windows stability;
6. changed paths;
7. production/dependency/workflow/tag counts;
8. full backend QA;
9. full frontend QA;
10. coverage/static/build/security;
11. Stage 4.5 acceptance matrix/fixtures/sweeps;
12. historical freeze regressions;
13. successor commit hash/subject/count;
14. object-isolated verification;
15. push/final refs;
16. hosted CI run/attempt and four results;
17. final clean tree;
18. confirmation no production behavior changed;
19. confirmation Stage 4.5 remains unfrozen;
20. confirmation no 316SS/later-stage work began.

**END OF STAGE 4.5 WINDOWS FRONTEND TIMING CORRECTION ORDER R3 — DO NOT PROCEED IF THIS LINE IS MISSING**
