# FRP Master Connection — CME-1 Tee Historical Default Limitation / Browser Gate Clarification R1

**RECOMMENDED CODEX EFFORT:** MEDIUM

## Purpose

Resume CME-1 after proving Classification B for the Tee default workspace:

- the current default Tee preview returns HTTP `422`;
- reason: `OUTSIDE_SELECTED_LEG_SURFACE`;
- the actual frozen Stage 3.2 startup/default request also returns HTTP `422` through its own frozen backend;
- therefore this is a **historical frozen default limitation**, not a CME-1 regression and not a later shared-geometry regression.

CME-1 shall not be blocked by requiring a browser behavior that the frozen Stage 3.2 product itself never satisfied.

This clarification does **not** authorize a Tee geometry/default correction.

Do not modify the frozen Stage 3.2 Tee baseline.

---

## 1. Baseline / preserved CME-1 work

Current accepted repository baseline remains:

`998911ea78872b852ef097dd4e20d666a33a935a`

Expected commit count:

`124`

The preserved uncommitted CME-1 work consists of 26 files plus the exact binary-capable preservation patch recorded by the Classification B report.

Before resuming:

1. verify every preserved CME-1 file hash against the recorded preservation ledger;
2. verify the saved patch/diff identity;
3. confirm both diagnosis checkouts remain clean;
4. confirm all 13 existing freeze tags remain unchanged.

If any preservation hash differs: STOP.

No Tee correction commit exists, so CME-1 remains based on count 124.

---

## 2. Historical Stage 3.2 authority

The immutable historical oracle is:

`stage-3.2-tee-connection-freeze`

Expected peeled target from project governance:

`d16b354732c90bf3bf7847c62be652c230a9f91e`

Verify actual Git tag identity/target locally and remotely.

Classification B is accepted only because the frozen default/startup request itself reproduces the same invalid-geometry result:

HTTP `422`

reason:

`OUTSIDE_SELECTED_LEG_SURFACE`

Do not move, rewrite, reinterpret or repair the historical freeze under CME-1.

---

## 3. Revised CME-1 browser-gate rule

For the Tee workspace only, the CME-1 browser gate shall test **baseline preservation**, not successful default preview.

The accepted Tee browser result for CME-1 is:

`HISTORICAL_DEFAULT_INVALID_GEOMETRY_PRESERVED`

with evidence:

- request reaches the expected Tee route/workspace;
- current default payload remains the inherited default unless CME-1 independently and legitimately changes only material-readiness metadata;
- response remains the historical `422 OUTSIDE_SELECTED_LEG_SURFACE`;
- CME-1 introduces no new/different geometry-validation reason;
- CME-1 does not mask or bypass the validation;
- workspace remains rendered and usable for editing/correction;
- CME-1 readiness/material diagnostics remain available without pretending the Tee default geometry is valid.

Do **not** count this one historical Tee default as a CME-1 browser failure.

The other 14 existing workspaces must still satisfy their normal successful browser checks.

---

## 4. CME-1 material-foundation behavior on invalid Tee default

CME-1 may expose its read-only connector-material readiness/role information for the Tee family even when the inherited default geometry is invalid.

It must not:

- run stainless resistance calculations;
- convert the `422` into a success;
- fabricate geometry;
- silently auto-repair the Tee dimensions/bolt offsets;
- suppress `OUTSIDE_SELECTED_LEG_SURFACE`;
- claim Tee 316SS readiness based on an invalid physical default.

The family inventory/material-policy record may classify the Tee product independently from the default geometry validity.

Recommended readiness trace shall distinguish at least:

- family material policy discovered;
- structural member role = FRP-only;
- connector-body role inventory;
- numerical stainless provider = not implemented in CME-1;
- default browser geometry = historical invalid baseline limitation.

---

## 5. Regression tests

Add or update CME-1 tests proving:

1. frozen Stage 3.2 default Tee result is historical `422 OUTSIDE_SELECTED_LEG_SURFACE`;
2. current baseline default Tee result is the same historical limitation;
3. CME-1 does not change the Tee geometry validation outcome;
4. CME-1 material-role/readiness inventory still includes the Tee family;
5. an invalid Tee default does not cause silent FRP/316SS provider fallback;
6. the Tee workspace remains mounted/rendered and editable after the invalid preview response;
7. changing to a valid Tee geometry through existing user controls continues to use existing Tee mechanics/validation with no CME-1 engineering alteration, if an existing valid fixture is already available;
8. all normal browser gates remain required for the other 14 workspaces.

Do not create a synthetic valid Tee default merely for this test.

---

## 6. Governance / limitation ledger

Record this as a known inherited limitation in the CME-1 implementation/readiness ledger:

`TEE_DEFAULT_GEOMETRY_HISTORICALLY_INVALID_AT_STAGE_3_2_FREEZE`

Include:

- Stage 3.2 freeze tag/target;
- inherited response `422 OUTSIDE_SELECTED_LEG_SURFACE`;
- evidence that current baseline matches frozen behavior;
- explicit statement that CME-1 does not repair or worsen it;
- future correction requires a separately controlled Tee product successor.

This limitation shall not be misclassified as:

- stainless source missing;
- stainless method unavailable;
- CME-1 regression;
- qualified-source requirement.

It is a geometry/default-product limitation.

---

## 7. Resume CME-1

After verifying this clarification:

1. return to the preserved CME-1 worktree;
2. verify all 26 preserved file hashes and patch identity;
3. continue the original CME-1 implementation order from baseline count 124;
4. apply only the minimal CME-1 test/governance changes required by this clarification;
5. rerun the complete browser matrix:
   - 14 normal workspaces must pass normally;
   - Tee must pass the historical-limitation preservation gate defined above;
6. continue complete local QA, object-isolated verification, normal push and hosted CI under the original CME-1 order.

Expected normal CME-1 implementation commit remains:

`feat: establish connector material foundation for FRP and 316SS`

Expected commit count remains:

`125`

No separate Tee correction commit shall be created.

---

## 8. Protected scope

Do not under this clarification:

- change Tee production geometry/defaults;
- weaken `OUTSIDE_SELECTED_LEG_SURFACE`;
- modify Stage 3.2 frozen artifacts/tags;
- change FRP engineering calculations;
- implement 316SS resistance equations;
- activate 316SS selectors in existing family editors;
- change dependencies/workflows;
- begin CME-2.

If CME-1 itself genuinely requires a Tee production change beyond material-foundation/readiness plumbing: STOP and report one consolidated conflict.

---

## 9. Completion evidence

The CME-1 final report shall explicitly include:

1. Classification B historical evidence;
2. Stage 3.2 tag/target;
3. frozen Tee 422 result;
4. current baseline Tee 422 result;
5. proof CME-1 preserved that outcome;
6. Tee readiness/material-policy inventory;
7. other 14 browser workspace results;
8. preserved-work hash verification;
9. confirmation no Tee correction was made;
10. future separate Tee-successor recommendation.

**END OF CME-1 TEE HISTORICAL DEFAULT LIMITATION BROWSER GATE CLARIFICATION R1 — DO NOT PROCEED IF THIS LINE IS MISSING**
