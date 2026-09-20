# FRP Master Connection — Stage 4.2 — Native Governing Failure Selection Correction and Resume Order R7

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Resolve the final G103 governing-failure-selection conflict found by the completed R6 read-only sweep and resume Stage 4.2 implementation.

No repository mutation has occurred.

## 1. Baseline

Require exactly:

`HEAD == origin/main == remote main == 473a3c8cd43f13022d254dae2477084895478c74`

Commit count:

`106`.

Worktree/index:

`clean`.

If different: STOP.

## 2. New controlling R7 files

### R7 Clarification

SHA-256:

`6AC4C13F013FC024ABA513AD0C09169AA3E7860FB80586683485DCD16CECA145`

Required sentinel:

`END OF STAGE 4.2 NATIVE GOVERNING FAILURE SELECTION CLARIFICATION R7`

### Replacement Golden RC1-R7

SHA-256:

`6F8A22388BEEFFB1CE1B4EF9556261C63200C632E5D50F5447F4011D2C15EA2B`

Must parse exactly:

`G1-G128`.

The SHA-256 for this R7 order is supplied in the owner handoff message.

Any mismatch: STOP.

## 3. Supersession

The Stage 4.2 RC1-R6 golden is superseded before implementation.

Continue all original/R3/R4/R5/R6 authority except where R7 explicitly corrects G103 governing-failure selection.

## 4. G103 overall status

Use the unchanged production-default material/factor records.

Require overall governing internal status:

`FAIL`.

Reason:

`EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE`.

Missing qualified sources remain visible but subordinate.

## 5. Native governing selection

Do not force bearing to govern.

The unchanged native Stage 2.5A -> resistance-handoff/group-mode pipeline is the exact governing-selection oracle.

For the audited production-default fixture, require native governing group:

`FIRST_ROW:TOP_FLANGE_ANGLE`.

Stage 4.2 integration must equal the direct native pipeline result/selection exactly.

If the unchanged direct native pipeline does not reproduce that group on the exact fixture, STOP and report instead of forcing it.

## 6. Visible failures

Require the result trace to preserve the exact native failed-check records for at least:

- first-row net tension;
- pin bearing;
- inter-row shear-out.

Bearing must remain visible as failed.

Bearing does not have to be the selected governing limit state.

Do not hard-code approximate displayed utilization values as resistance oracles.

## 7. No native-selection override

Do not:

- reorder failed checks;
- modify group-mode selection;
- suppress a failure;
- modify material/factors;
- modify Stage 2.5A;
- modify resistance handoff;
- change status precedence;
- use tolerance.

## 8. Completed sweep disposition

The R6 read-only audit reported no additional blocker beyond this G103 conflict.

After verifying R7, do not repeat already-passed expensive pre-mutation gates solely because R7 changes only the G103 golden/selection authority, unless repository state changed or a dependent check is directly affected.

Perform targeted verification of R7 plus the required final pre-mutation consistency check, then resume implementation.

If a genuinely new engineering blocker emerges during implementation, follow the existing stop rules.

## 9. Continue all unchanged Stage 4.2 requirements

Resume all prior requirements, including:

- R4 physical web reference `(0,2)`;
- Slice 8 web demand;
- Stage 2.5A native flange demand;
- Slice 7 connector boundary;
- native qualified-source behavior;
- G110 pure-moment relational authority;
- combined/pure/sign-reversal proofs;
- `+3E-79 / +6E-79 / -6E-79` combined diagnostics;
- pure-moment `+2E-78 / -2E-78` diagnostics;
- finite wall / W-I beam / four FRP angles;
- external anchor/concrete boundary;
- full QA;
- local built-in-browser/CDP visual QA;
- object-isolated verification;
- previously authorized normal non-force push;
- direct hosted 4/4 CI;
- owner final visual acceptance.

## 10. Commit

Expected implementation commit remains:

`feat: add W/I beam-to-concrete-wall moment connection`

Expected final commit count:

`107`.

Do not amend.

Do not tag.

## 11. QA additions

Require explicit tests proving:

1. G103 direct native pipeline overall status is FAIL.
2. G103 direct native governing group is `FIRST_ROW:TOP_FLANGE_ANGLE`.
3. Stage 4.2 governing selection equals direct native selection exactly.
4. net tension failure remains visible.
5. bearing failure remains visible.
6. inter-row shear-out failure remains visible.
7. bearing is not artificially forced to govern.
8. missing sources remain visible but subordinate.
9. material/factor fingerprints remain exact.
10. replacement R7 G1-G128 passes.

## 12. Completion report addition

Explicitly report:

- exact native governing group/selection;
- exact native failed-check list;
- bearing visibility;
- confirmation no limit-state override occurred;
- G103 overall FAIL;
- subordinate missing-source trace;
- R7 golden hash/G1-G128 result.

**END OF STAGE 4.2 NATIVE GOVERNING FAILURE SELECTION CORRECTION AND RESUME ORDER R7 — DO NOT PROCEED IF THIS LINE IS MISSING**
