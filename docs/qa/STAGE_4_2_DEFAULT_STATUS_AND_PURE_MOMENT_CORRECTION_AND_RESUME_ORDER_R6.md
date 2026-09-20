# FRP Master Connection — Stage 4.2 — Default Status and Pure-Moment Correction and Resume Order R6

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Resolve the two blockers from the consolidated R5 read-only audit and resume Stage 4.2 implementation.

No Stage 4.2 repository mutation has occurred.

## 1. Baseline

Require exactly:

`HEAD == origin/main == remote main == 473a3c8cd43f13022d254dae2477084895478c74`

Commit count:

`106`.

Worktree/index:

`clean`.

If different: STOP.

## 2. New controlling files

### R6 Clarification

SHA-256:

`02CEF33BB0BFF2AE691736D6F1E13EE58D33F52F449C129D1C005DC14B07E934`

Required sentinel:

`END OF STAGE 4.2 DEFAULT STATUS AND PURE-MOMENT NUMERIC AUTHORITY CLARIFICATION R6`

### Replacement Golden RC1-R6

SHA-256:

`04A21C3DB1E024CAB997745061139324A6A95D27BDBC6978137B8F705CF1001E`

Must parse exactly:

`G1-G128`.

The SHA-256 for this R6 order is supplied in the owner handoff message.

Any mismatch: STOP.

## 3. Supersession

The RC1-R5 golden is superseded before implementation.

Continue all R3/R4/R5 and original Stage 4.2 requirements except where R6 explicitly changes G103/G104/G110 status/numeric authority and related fingerprint metadata.

## 4. G103 production-default material/factors

Use the exact current production-default locked ICE material record and existing native factor path.

Do not change material properties, factors, or default selection to obtain a desired status.

Before mutation, identify/report exact repository material and factor fingerprints used by this fixture.

## 5. G103 production-default status

Run all required evaluated checks that are applicable before final status aggregation.

G103 must compare to the direct native Stage 4.2 local-check/design path.

Expected governing status:

`FAIL`.

Reason:

`EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE`.

The top-flange-angle local bearing failure identified by the audit must remain visible as the governing internal failure if reproduced by the unchanged native path.

Missing connector/attachment qualified sources must also remain visible, but shall not replace `FAIL` as governing status.

Do not hard-code the approximate audit demand/capacity values as a new resistance oracle.

## 6. G104 success-status contract

Treat G104 as a status-aggregation contract test only.

It is **not** the production-default physical fixture.

Supply/test aggregation preconditions where all required evaluated checks are already PASS and all required qualified source/coverage states are present/applicable/pass.

Require:

`PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`.

Ordinary `PASS` prohibited.

Do not invent alternate physical material properties to construct G104.

## 7. G110 pure moment

For:

`P=0, V=0, M=+100`

require:

- top tension;
- bottom compression;
- retained web local moment;
- Slice 8 web independent-moment path;
- all native connector/web equilibrium proofs.

The algebraic target is:

- right-hand wall moment `-100 kip-in`;
- structural wall moment `+100 kip-in`.

The controlling numerical integration output is the exact native relational pipeline result.

Audit residuals versus the targets:

- right-hand `+2E-78 kip-in`;
- structural `-2E-78 kip-in`.

No tolerance.

No rounding-to-target.

No residual redistribution.

## 8. Exhaustive pre-mutation sweep

Before mutation, continue the already-authorized exhaustive read-only sweep through the entire R6 package wherever technically safe.

Do **not** stop after the first newly discovered pre-mutation discrepancy.

Collect all remaining blockers into one consolidated report, except where continuing the audit itself would require mutation or be technically impossible.

Engineering stop conditions remain fully in force.

## 9. Standing QA network authorization

Owner standing authorization is already granted for this repository to run:

`npm audit --json`

and:

`npm audit --omit=dev --json`

against:

`https://registry.npmjs.org/`

including npm security-advisory endpoints.

Authorized disclosure is limited to dependency metadata required by npm audit.

Do not ask again unless destination/command/data scope changes.

No `npm audit fix`.

## 10. Local browser/dev authorization

Use the existing backend/frontend dev commands and localhost ports for the mandatory R3 visual QA.

Codex is authorized to start/stop only the local dev-server processes it starts and to inspect localhost using the built-in browser/CDP.

No new startup dependency/script.

## 11. Continue implementation

After all pre-mutation gates pass, resume all unchanged R5/R4/R3 Stage 4.2 requirements.

Expected implementation commit remains:

`feat: add W/I beam-to-concrete-wall moment connection`

Expected final commit count:

`107`.

## 12. Push authorization after gates

After:

- complete local QA;
- required local built-in-browser/CDP visual QA;
- successful commit;
- successful object-isolated verification;

owner pre-authorizes a **normal non-force push of that exact unchanged Stage 4.2 implementation commit to `main`**, with no tags, solely to publish the verified commit and trigger hosted CI.

Do not amend/rebase/squash the commit.

If the commit or QA state differs from the prescribed accepted state, this pre-authorization does not apply.

## 13. Hosted CI

After push require direct four-job evidence:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

If GitHub authentication is unavailable, report CI pending without changing code.

## 14. QA additions

Require explicit tests proving:

1. G103 uses the unchanged locked production-default ICE material/factors.
2. G103 native evaluated failure governs as `FAIL`.
3. Missing sources remain visible but subordinate in G103.
4. G104 is status-aggregation-only and does not invent material properties.
5. G104 highest success state is review-required, never ordinary PASS.
6. G110 algebraic targets are `-100/+100`.
7. G110 exact integration result equals the native relational pipeline.
8. G110 serialized residuals are `+2E-78/-2E-78`.
9. No tolerance or residual redistribution exists.
10. R6 G1-G128 passes.
11. all Slice 5/7/8, Stage 2.5A, and freeze regressions remain exact.

## 15. Completion report addition

Explicitly report:

- exact production-default ICE material/factor fingerprints;
- native G103 governing failure/status;
- subordinate missing-source trace;
- G104 aggregation-only proof;
- G110 exact native relational result;
- G110 algebraic target and `±2E-78` diagnostics;
- R6 golden hash/G1-G128 result.

**END OF STAGE 4.2 DEFAULT STATUS AND PURE-MOMENT CORRECTION AND RESUME ORDER R6 — DO NOT PROCEED IF THIS LINE IS MISSING**
