# FRP Master Connection — Stage 4.4 Angle-Column Two-Leg Moment Base Freeze — Codex Order

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Freeze the owner-accepted Stage 4.4 product:

`ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION`

Contract: `4.4-RC1`.

This is governance-only unless one of the bounded nonproduction maintenance rules below is triggered. Do not begin Stage 4.5 or 316SS.

## 1. Accepted baseline

Require exactly:

`HEAD == origin/main == remote main == d11012e771556f0ed5cac46f39ab40cb0a53273e`

Subject:

`fix: synchronize Stage 4.4 preview and last-valid state`

Commit count: `116`.

Engineering implementation commit:

`e8bc2355bcecaabd70d31332cf1af3ee6eb17712`

Accepted correction commit:

`d11012e771556f0ed5cac46f39ab40cb0a53273e`

Require clean worktree/index.

Accepted evidence:

- 3,949 backend tests;
- 710 frontend tests;
- 100% configured coverage;
- static/build checks passed;
- full/runtime audits zero;
- object-isolated verification passed;
- CI #111 attempt 1: Backend Ubuntu/Windows + Frontend Ubuntu/Windows all PASS;
- owner visual acceptance: `Stage 4.4 visual accepted`.

If baseline differs: STOP and consolidate discrepancies.

## 2. Freeze engineering behavior

Freeze:

- one vertical FRP angle column;
- two exterior FRP base-angle connectors, one on each different column leg;
- equal-leg and unequal-leg geometry;
- independent connector/member/foundation hardware geometry;
- signed N, Vx, Vy, Mx, My;
- no user-input Mz in RC1;
- reference-generated Mz retained;
- exact required total foundation wrench;
- no automatic 50/50 branch sharing;
- complete two-leg base-response source required where branch/contact sharing is unresolved;
- unknown branch demand is never treated as zero;
- direct column-end contact remains a separate physical contribution and is never double-counted;
- Slice 7 / Slice 8 / Stage 2.5A native authority within accepted applicability;
- dependency-native numerics and exact relational transport;
- no cross-engine tolerance or residual redistribution;
- applicable native member/bolt/local-FRP checks only when branch demand is available;
- foundation anchor/concrete capacity external;
- Section 2.3.2 engineering-review/qualification boundary;
- stiffness/rotation/full-strength classification not evaluated.

Freeze accepted frontend behavior:

- backend-authoritative geometry/actions;
- two independent base-angle editors;
- member/foundation hardware;
- explicit design check and source trace;
- required-total-foundation-action panel;
- separate Leg 1 / Leg 2 / direct-contact cards;
- valid edits refresh current preview/actions;
- invalid current inputs retain only a clearly marked `LAST VALID` scene;
- stale action arrows are hidden/noncurrent;
- validation reasons remain visible;
- invalid -> valid automatically recovers;
- superseded responses cannot replace newer current preview.

## 3. Future scope remains open

Do not freeze or implement:

- Stage 4.5 W/I/RHS/SRS biaxial moment bases;
- 316SS connector provider;
- generalized unqualified contact/sharing formulas;
- full foundation/anchor design;
- full column strength/stability;
- stiffness/rotation/full-strength classification.

## 4. Historical freezes

Verify all eleven existing local/remote freeze tags and peeled targets. Include:

`stage-4.3-wi-beam-frp-support-moment-connection-freeze`

which must peel to:

`1faa1ff522d0e0a39a42e2dc2d3974b5dba98479`.

Do not move/recreate/delete/retarget any existing tag.

## 5. Stage 4.4 controlled artifacts

Verify repository copies:

Stage 4.4 order/spec SHA-256:

`71C62369A68ED8CB61BB04539FF9F2C13D2B9B237C6B10449C3CBE5340487009`

Stage 4.4 acceptance matrix SHA-256:

`A09FB76C07AB12AB9C435CAD1B29806D4B4DB839B12191444BE4507DFE0D9BB8`

Do not rewrite them during freeze.

## 6. Exhaustive pre-mutation audit

Perform one complete read-only sweep before mutation. Verify:

- product exists once;
- equal/unequal presets;
- exactly two connectors on different legs;
- no automatic 50/50 allocation;
- exact total foundation action and generated Mz;
- unresolved branch sharing remains source-required;
- direct contact remains separate;
- acceptance matrix passes;
- all 14 reference fixtures pass;
- prescribed sweep/source-present cases pass;
- Slice 7/8 and Stage 2.5A regressions pass;
- Stage 4.3 freeze remains exact;
- all eleven historical freeze audits/tags pass;
- valid preview refresh and LAST VALID recovery behavior pass;
- full/runtime audits zero;
- dependency/workflow state unchanged;
- no Stage 4.5/316SS work exists.

Collect all safe preflight blockers into one report rather than stopping at the first known maintenance issue.

## 7. Standing successor-safety authority

Without another owner approval, Codex may make tests-only repository-wide corrections for the already-known brittle historical-test pattern where a historical digest/allowed-list is incorrectly compared against later authorized current-tree governance/test maintenance.

Requirements:

- historical frozen digest/object remains exact;
- tamper detection remains;
- frozen tags/manifests remain unchanged;
- unauthorized production/engineering/dependency/workflow changes still fail;
- never replace a historical hash with a current hash;
- never skip/xfail/delete protection.

If needed, consolidate all such test changes into one tests-only successor commit, run full QA/object isolation, push normally, require hosted 4/4 green, and resume this freeze automatically.

Suggested subject:

`test: make Stage 4.4 freeze guards successor-safe`

## 8. Standing security-maintenance authority

Existing npm-audit network authorization remains valid.

If a new **dev-only** audit finding appears and runtime audit remains zero, Codex may automatically make the minimal lockfile/patch/compatible-minor security successor provided there is:

- no major/toolchain migration;
- no new dependency;
- no production code change;
- no workflow change.

Any necessary successor-safe test maintenance may be included under §7. Full QA/object isolation/hosted 4/4 green is required before freeze resumes.

If a major/breaking or production change is required: STOP.

## 9. Standing Windows timing authority

For hosted Windows frontend only:

- retry once if the sole failure is a 5-second timeout with no assertion/application/network/runtime defect;
- if it repeats, a per-test timeout up to 15,000 ms is authorized;
- maximum three timing-only tests in this freeze cycle;
- require 10/10 local Windows passes for each;
- no global timeout, sleeps, skipped tests, weakened assertions or production changes.

A tests-only successor may be created/pushed and the freeze resumed automatically.

## 10. Verification-environment authority

Previously approved equivalents remain valid:

- `python -m mypy` if wrapper execution is blocked;
- existing trusted WSL/Linux for equivalent verification;
- Git-aware blob checks instead of false CRLF working-tree comparisons.

Do not weaken QA or security policy.

## 11. Freeze manifest

On the final accepted pre-freeze baseline, create:

`docs/governance/STAGE_4_4_ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_FREEZE_MANIFEST.json`

Bind at minimum:

- stage/product/contract;
- engineering commit `e8bc2355bcecaabd70d31332cf1af3ee6eb17712`;
- accepted correction `d11012e771556f0ed5cac46f39ab40cb0a53273e`;
- actual current pre-freeze baseline/count after any authorized maintenance;
- CI #111 attempt 1 product evidence;
- 3949/710 accepted product QA and 100% coverage;
- owner visual acceptance;
- Stage 4.4 order/matrix hashes;
- equal/unequal-leg support;
- different-leg topology;
- required-foundation-wrench authority;
- no-50/50 rule;
- direct-contact separation;
- source/qualification/foundation boundaries;
- inherited engine identities;
- Stage 4.3 freeze verification;
- eleven prior tag verification;
- LAST VALID correction provenance;
- any authorized maintenance successor provenance;
- future Stage 4.5/316SS boundary.

Compute/report manifest SHA-256.

## 12. Governance updates and scope gate

Update only the normal governance/documentation records needed to register the freeze.

Normal freeze-governance commit must change zero:

- backend/frontend production files;
- engineering calculation files;
- dependencies/lockfiles;
- workflows;
- tests;
- controlled Stage 4.4 order/matrix;
- existing tags.

Only governance/docs/freeze-manifest paths are authorized in the normal governance commit.

## 13. QA and governance commit

Run complete backend/frontend QA, 100% configured coverage, Ruff, strict mypy, ESLint, strict TypeScript, production build, pip check, both npm audits zero, JSON/whitespace/dependency checks, Stage 4.4 acceptance matrix, all 14 fixtures, prescribed sweeps, Slice 7/8, Stage 2.5A, Stage 4.3 freeze and all eleven historical freeze audits.

Normal-path governance commit:

`chore: freeze Stage 4.4 angle-column two-leg moment base baseline`

Normal expected count: `117`.

If authorized maintenance successors were needed, use the same governance subject and report the actual later count.

Do not amend accepted prior commits.

## 14. Object-isolated verification / push / CI

After governance commit:

- fresh depth-one / no-tags / no-alternates clone;
- complete QA again;
- freeze-manifest/register integrity;
- clean tree.

Then owner pre-authorizes a normal non-force push of the exact verified governance commit to `main`.

No tags yet.

Require direct hosted:

- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

Apply §9 automatically only when its exact timing-only conditions are met.

## 15. Freeze tag

After the **final accepted freeze-governance/finalization commit** has direct hosted 4/4 green, create and normally push:

`stage-4.4-angle-column-two-leg-moment-base-freeze`

Annotation:

`Stage 4.4 angle-column two-leg moment base freeze`

The tag must point to the final accepted freeze-governance/finalization commit, not merely the engineering implementation or preview correction.

Verify local/remote tag object and peeled commit.

## 16. Final identity

After tag verification, Stage 4.4 is:

`FROZEN`

Record separately:

- engineering implementation `e8bc2355bcecaabd70d31332cf1af3ee6eb17712`;
- accepted preview/state correction `d11012e771556f0ed5cac46f39ab40cb0a53273e`;
- any bounded nonproduction maintenance successors;
- final freeze-governance/finalization commit and count;
- freeze tag object and peeled commit.

Confirm Stage 4.5 and 316SS remain unstarted.

## 17. Completion report

Report baseline/count; owner acceptance; product CI; eleven historical tags; Stage 4.4 artifact hashes; matrix/fixture/sweep results; equal/unequal geometry; different-leg topology; required foundation wrench/generated Mz; branch/contact/source boundaries; preview/LAST VALID behavior; any bounded maintenance; manifest path/hash; governance changed paths; production/dependency/test/workflow counts; complete QA; governance/finalization commit; object-isolated verification; push refs; hosted CI; tag object/peeled commit; final clean state; no Stage 4.5/316SS; final frozen status.

**END OF STAGE 4.4 ANGLE COLUMN TWO-LEG MOMENT BASE FREEZE ORDER — DO NOT PROCEED IF THIS LINE IS MISSING**
