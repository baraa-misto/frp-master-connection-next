# FRP Master Connection — Stage 4.2 — Slice 8 Integration Correction and Implementation Order R3

**RECOMMENDED CODEX EFFORT:** EXTRA HIGH

## Purpose

Resume and implement the physical:

`WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION`

contract:

`4.2-RC1`

using accepted Calculation Slice 8 for the previously unsupported independently applied web-group in-plane free moment.

R3 also corrects the final serialized wall-moment diagnostic to `±6E-79 kip-in`.

This is the controlling Stage 4.2 implementation order.

## 1. Starting baseline

Require exactly:

`HEAD == origin/main == remote main == 473a3c8cd43f13022d254dae2477084895478c74`

Expected commit count:

`106`.

Worktree/index:

`clean`.

If different: **STOP before mutation.**

## 2. Accepted Calculation Slice 8 authority

Engineering implementation:

`9f86a5685be840b271929cf3298f17a5e401b7c8`

Subject:

`feat: add in-plane bolt-group wrench demand engine`

Test-only stabilization successor:

`473a3c8cd43f13022d254dae2477084895478c74`

Hosted acceptance:

GitHub Actions run `#101`, attempt `2`:

- Backend Ubuntu PASS
- Backend Windows PASS
- Frontend Ubuntu PASS
- Frontend Windows PASS

Calculation Slice 8 is formally accepted.

Do not modify it.

## 3. New controlling R3 files

### Clarification R3

SHA-256:

`EF4A38B563C63B31AABBF9BE6EB05247280EAEEE068AE64D17869F06D5D10569`

Required sentinel:

`END OF STAGE 4.2 SLICE 8 INTEGRATION AND FINAL NUMERIC AUTHORITY CLARIFICATION R3`

### Replacement Golden RC1-R3

SHA-256:

`3CEB5EB07BF346DAC38684FBEFEA2DD3C52939F462C634814346E688EF548CFE`

Must parse exactly:

`G1-G128`.

The SHA-256 for this R3 order is supplied in the owner handoff message.

Any mismatch: **STOP.**

## 4. Prior Stage 4.2 authority

Continue using the previously supplied:

- Stage 4.2 Decision;
- Stage 4.2 Engineering Specification RC1;
- Stage 4.2 Authority Ledger;
- original Stage 4.2 main Codex Order;
- R1 Decimal clarification;
- R2 cross-engine clarification;

except where R3 explicitly supersedes them.

The original RC1, RC1-R1, and RC1-R2 Stage 4.2 goldens are superseded before implementation.

Only RC1-R3 is current.

## 5. Immutable dependencies

Preserve exactly:

- Calculation Slice 5;
- Calculation Slice 7;
- Calculation Slice 8;
- Stage 2.5A;
- all frozen historical families/fingerprints.

Do not mutate a dependency to make Stage 4.2 easier.

## 6. Mandatory pre-mutation audit

Report:

1. Slice 5 invocation seam;
2. Slice 7 four-core invocation seam;
3. Slice 8 invocation/result seam;
4. Stage 2.5A top/bottom applicability;
5. exact Stage 2.5A independent-moment path that must not be used for web groups;
6. common web-bolt two-plane consumer;
7. qualified member-attachment source infrastructure;
8. Stage 3.5 finite-wall reuse;
9. frontend Moment Connections workspace reuse;
10. actual backend/frontend local dev commands and ports;
11. all frozen modules/fingerprints that remain untouched.

If any dependency/freeze must change: **STOP.**

## 7. Demand-engine dispatch

Use Stage 2.5A only within its accepted applicability.

For Stage 4.2 RC1:

- top flange member-side in-plane group -> Stage 2.5A;
- bottom flange member-side in-plane group -> Stage 2.5A;
- positive web member-side in-plane group -> Slice 8;
- negative web member-side in-plane group -> Slice 8.

A valid Stage 4.2 web path must not emit:

`MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL`.

## 8. Positive web Slice 8 input

Default exact input:

`F_A=+5 kip`

`F_B=+3.6 kip`

`M_C,R=+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`

Use actual common 2×2 web-bolt coordinates and exact group reference.

Require exact equality between Stage 4.2 integration output and a direct accepted Slice 8 invocation.

Do not recompute vectors in Stage 4.2.

## 9. Negative web Slice 8 input

Default exact input:

`F_A=-5 kip`

`F_B=+3.6 kip`

`M_C,R=-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`

The negative moment must be the full exact mathematical negative.

Require exact equality to a direct accepted Slice 8 invocation.

## 10. Common web bolts

Use actual positive/negative Slice 8 per-plane vectors in:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

No blind equal-plane assumption.

No force/n replacement.

No blind `2×` capacity.

## 11. Out-of-plane member attachment

Slice 8 evaluates only the member-leg in-plane wrench.

Retain:

- `F_C`;
- `M_A`;
- `M_B`;

as qualified member-attachment source demand.

Do not invent:

- bolt tension;
- pull-through;
- delamination;
- prying;
- secondary bolt-bending capacity.

## 12. Slice 7 native boundary

Preserve R2 exactly:

- Stage 4.2 passes exact member-interface wrench to unchanged Slice 7;
- Slice 7 native core numerics govern heel/support outputs;
- FRP provider receives native Slice 7 heel wrench;
- Stage 4.2 consumes outputs verbatim;
- no Decimal-80 wrapper/quantization around Slice 7.

## 13. Slice 8 native boundary

Preserve accepted Slice 8 authority:

- exact rational mechanics/proofs;
- local Decimal-80 / ROUND_HALF_EVEN projection;
- no ambient Decimal dependence;
- no Stage 2.5A rounding emulation;
- no Stage 4.2 vector recomputation.

## 14. Final serialized diagnostics

Controlling diagnostics:

- axial residual: `+3E-79 kip`;
- right-hand wall major-moment residual: `+6E-79 kip-in`;
- structural wall major-moment residual: `-6E-79 kip-in`.

These are audit diagnostics only.

No tolerance.

No redistribution.

## 15. Global equilibrium

Prove compositionally from:

1. accepted Slice 5 algebraic equilibrium proof;
2. exact Stage 4.2 component allocation;
3. two Slice 8 web-group equilibrium proofs;
4. four Slice 7 connector-core equilibrium proofs;
5. exact frame transforms;
6. exact wall reference shifts/sums.

Algebraic target remains:

- force `(20,-10,0) kip`;
- right-hand wall moment `(0,0,-105) kip-in`;
- structural wall major moment `+105 kip-in`.

## 16. G1-G128

Implement replacement RC1-R3 exactly.

Where the golden declares a dependency-exact or relational expectation, compare against the direct immutable dependency/result relation.

Production code must not read the golden.

## 17. Qualified attachment test fixtures

For test-only qualified member-attachment results, compare Stage 4.2 integration exactly against a direct invocation of the baseline accepted qualified signed-wrench source infrastructure with the same member-interface wrench and test-only source.

Do not create a duplicate precision path.

No test-only source becomes a production default.

## 18. Physical Stage 4.2 product

Execute all unchanged requirements from the original Stage 4.2 order, including:

- finite concrete wall;
- W/I beam;
- positive gap;
- top flange FRP angle;
- bottom flange FRP angle;
- paired web FRP clip angles;
- member bolts;
- four external wall-anchor groups;
- exact support handoffs;
- FRP provider/source status;
- qualified member-attachment source status;
- external anchor/concrete status;
- preview/design separation;
- result trace;
- 3D/X-ray;
- invalid/current/last-valid/request-failure behavior.

## 19. 316SS

Do not implement or expose 316SS.

Preserve material-neutral provider architecture only.

## 20. Dependencies/workflows/tags

Authorized changes:

- dependencies `0`;
- lockfiles `0`;
- workflows `0`;
- tags `0`.

Preserve the existing targeted 15-second historical Windows test timeout exactly.

## 21. Local browser visual QA — mandatory before publication

After implementation and complete local QA:

1. start the existing backend and frontend dev servers in separate persistent Codex terminal sessions;
2. use the repository's existing commands only;
3. wait for both servers to be healthy;
4. open the local frontend in the Codex built-in browser;
5. use Browser Use and CDP/developer mode when available;
6. inspect console, failed network requests, React/runtime errors, preview/design payloads, request states, and 3D behavior;
7. capture/report any discrepancy before proceeding;
8. terminate only the dev-server processes Codex started.

### Default combined

Use:

`P=+20, V=-10, M=+100`.

Verify:

- finite wall;
- full W/I beam;
- positive gap;
- four intended angles;
- common web bolts;
- flange bolts;
- four wall-anchor groups;
- no collisions;
- action arrows;
- Slice 5 trace;
- two Slice 8 web-group traces/proofs;
- four Slice 7 connector traces;
- external support status;
- algebraic structural wall target `+105 kip-in`;
- serialized structural diagnostic `-6E-79 kip-in`.

### Pure shear

Use:

`P=0, V=-10, M=0`.

Verify top/bottom connector demand zero and correct web signs.

### Pure moment

Use:

`P=0, V=0, M=+100`.

Verify:

- top tension;
- bottom compression;
- nonzero web independent in-plane moment goes through Slice 8;
- no Stage 2.5A unsupported-moment warning on the valid web path.

### Sign reversal

Reverse `V`, then separately reverse `M`.

Geometry must remain unchanged.

Signed demands must reverse consistently.

### X-ray / invalid / request state

Verify all hardware and no blank root/workspace.

Owner final visual acceptance remains required before freeze.

## 22. Full QA

Require all original Stage 4.2 QA plus:

- replacement Stage 4.2 G1-G128;
- Slice 5 G1-G52;
- Slice 7 G1-G72;
- Slice 8 G1-G80;
- positive/negative direct Slice 8 integration equality;
- no valid web Stage 2.5A unsupported-moment warning;
- common web-bolt planes consume Slice 8 outputs;
- corrected `+6E-79/-6E-79` diagnostics;
- full backend;
- full frontend;
- 100% configured coverage;
- Ruff;
- strict mypy;
- ESLint;
- strict TypeScript;
- production build;
- JSON/whitespace;
- dependency/runtime audits;
- zero vulnerabilities;
- all freeze/historical regressions.

## 23. Staging

Review every changed path.

Stage explicit paths only.

Do not use:

`git add .`

or:

`git add -A`.

Require:

`git diff --cached --check`.

## 24. Commit

Create exactly:

`feat: add W/I beam-to-concrete-wall moment connection`

Do not amend.

Do not tag.

Expected final commit count:

`107`.

## 25. Object-isolated verification

After commit and before push, use a fresh depth-one / no-tags / no-alternates clone.

Require:

- R3 G1-G128;
- Slice 5 G1-G52;
- Slice 7 G1-G72;
- Slice 8 G1-G80;
- default combined;
- pure shear;
- pure moment;
- sign reversals;
- exact Slice 8 web integration;
- four Slice 7 core equilibria;
- exact wall proof;
- corrected diagnostics;
- full QA;
- all freeze regressions;
- clean tree.

Failure: **STOP before push.**

## 26. Push

Normal non-force push `main`.

No tags.

Verify:

`HEAD == origin/main == remote main`.

If the environment requires owner authorization to push before hosted CI can run, STOP and request that authorization without changing the commit.

## 27. Hosted CI

Require direct:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

Do not infer.

If authentication is unavailable, report CI as pending rather than claiming acceptance.

## 28. Owner acceptance

Stage 4.2 remains open until owner reviews the visual/result evidence.

Do not freeze automatically.

## 29. Completion report

Report numbered:

1. baseline;
2. R3 hashes/sentinels;
3. accepted Slice 8 evidence;
4. dependency/freeze audit;
5. Stage 2.5A dispatch;
6. positive web Slice 8 input/result;
7. negative web Slice 8 input/result;
8. Slice 8 proofs/fingerprints;
9. common web-bolt two-plane demand;
10. retained out-of-plane demand;
11. Slice 7 native boundary;
12. top/bottom Stage 2.5A demand;
13. Slice 5 component mapping;
14. four connector cores/equilibria;
15. FRP provider/source results;
16. qualified member-attachment source;
17. physical geometry;
18. wall/beam/gap;
19. four angles;
20. member bolts;
21. four anchor groups;
22. four support handoffs;
23. wall aggregate/proof;
24. `+3E-79 / +6E-79 / -6E-79` diagnostics;
25. preview;
26. design;
27. statuses/disclaimer;
28. API;
29. frontend workspace;
30. result trace;
31. 3D/X-ray;
32. invalid/request-state behavior;
33. default combined visual QA;
34. pure shear visual QA;
35. pure moment visual QA;
36. sign-reversal visual QA;
37. console/network/CDP findings;
38. G1-G128;
39. Slice 5 G1-G52;
40. Slice 7 G1-G72;
41. Slice 8 G1-G80;
42. U.S./SI;
43. fingerprints;
44. backend QA;
45. frontend QA;
46. coverage/static/build/security;
47. historical/freeze regressions;
48. changed paths;
49. dependency/workflow/tag counts;
50. staged diff;
51. commit hash/subject/count;
52. object-isolated verification;
53. push/final refs;
54. hosted CI;
55. owner acceptance status;
56. deviations/risks;
57. confirmation 316SS/later moment families not begun.

Stop after reporting.

**END OF STAGE 4.2 SLICE 8 INTEGRATION CORRECTION AND IMPLEMENTATION ORDER R3 — DO NOT PROCEED IF THIS LINE IS MISSING**
