# Stage 4.1B-R1 — Channel workspace bootstrap/runtime correction

## Authority and scope

The owner approved executing the attached R1 order. Its complete content and final
sentinel were read before mutation. SHA-256:
`42022F21D8B26AFC08F25B93EA485A01AC2660EE4767A030BBA5AAD04C7005D9`.
The final sentinel is **END OF STAGE 4.1B-R1 CHANNEL WORKSPACE BOOTSTRAP / RUNTIME
CORRECTION ORDER — DO NOT PROCEED IF THIS LINE IS MISSING**.

This is a frontend runtime/transport correction, not engineering authority.
Stage 4.1B remains OPEN until direct four-job CI evidence and repeated owner
visual acceptance. No freeze or later family is authorized.

## Pre-mutation diagnosis

The clean main baseline was `bd0529e71ae20b6b456b92e2692f6eca7269f9f8`,
with 101 commits and matching local HEAD, origin/main and remote main.
The eight historical freeze tag objects and peeled targets matched the remote.
All five prescribed predecessor artifact/order hashes matched the R1 order.
Stage 4.1B and Slice 6 goldens remain G1-G112 and G1-G72, respectively.

The real browser reproduced the owner's blank-root defect after a successful
HTTP 200 / VALID preview. W/I -> Channel, historical Shear -> Moment -> Channel,
U.S. preset and SI preset all produced the same exception and zero root children:

```text
TypeError: Cannot read properties of undefined (reading 'l')
  point                                  channelMomentSpliceSceneModel.ts:6
  buildChannelMomentSpliceSceneModel      channelMomentSpliceSceneModel.ts:67
  ChannelMomentSpliceWorkspace useMemo    ChannelMomentSpliceWorkspace.tsx:50
  updateMemo -> useMemo -> renderWithHooks -> updateFunctionComponent
```

The backend correctly serialized `visualization.channel_shear_center_l_v_t`.
The frontend contract, adapter and handwritten fixture incorrectly expected
`shear_center_l_v_t`. The client accepted the top-level discriminators without
checking that reference. Scene construction then dereferenced an absent vector.
This is the first-loss boundary; the backend geometry and response are correct.
Existing tests replaced the visualization panel and used a synthetic fixture with
the same wrong field name, so they did not test the real response contract.

The DTO audit also found the unused frontend equilibrium member
`beam_a_b_equal_opposite`; the backend name is
`beam_a_b_equal_opposite_complete_wrenches`. Only the TypeScript/fixture name changed.

Before fixing the design button, a separate reproduced state showed a valid model
retained after a backend-invalid gap edit while Run Design Check stayed enabled.
It now requires CURRENT_VALID preview state, retaining the existing last-valid model.

Before mutation, initial local-invalid (gap 0), backend-invalid (gap 100), HTTP 503
and network-failed requests already preserved the shell. The blank root prevented
testing last-valid state until the field binding was repaired. No URL/session
restoration or direct product deep link exists; direct initial component mount is
tested without introducing routing or persistence.

Raw request/response payloads, complete generated stacks and browser screenshots
were captured outside the repository in the task host temporary directory:
`frp-41br1-before-evidence.json`, `frp-41br1-dev-evidence.json`, and
`frp-41br1-production-evidence.json`, with corresponding PNGs. These are diagnostic
evidence, not source authority. No PDF or engineering artifact was copied.

## Correction and regression method

Four frontend production files changed: the Channel response interfaces, strict
preview reference-vector guard, Channel scene reference binding, and Channel
design-button current-preview gate. No generic/global exception suppression or
invented fallback geometry was added. Malformed references become the existing
typed transport error, handled by the existing preview hook; loading, failed,
invalid and last-valid states remain explicit.

`frontend/tests/fixtures/channelMomentSpliceWire.json` contains exact projections
of actual unchanged backend U.S./SI responses and requests. It is test transport
data, not a new controlled engineering golden. A backend test recursively verifies
every fixture field against fresh API serialization, including decimal strings,
units and fingerprints; it checks deterministic repeated bytes and physical paths.
SI visualization lengths and internal engineering quantities are compared using
canonical values, not unlike display units.

The new frontend test keeps App, actual selector, client, workflow hook, scene
adapter, visualization panel and trace real; only the WebGL canvas boundary is
replaced. StrictMode selector tests assert no console errors (the spy must remain
unused), both transition paths, Channel/WI/Channel, six plates, references, source
pending state and X-ray binding. Direct mount tests cover loading and both presets;
invalid/HTTP/network/malformed tests cover last-valid retention and disabled design.
No global or per-test timeout was increased.

The actual installed Edge browser separately rendered the real WebGL scene in
development and production builds: 14 scenarios each, zero uncaught page errors,
one root child throughout. Valid/last-valid cases had one canvas; initial failed
requests correctly had a visible prompt instead. Cases: both selector paths,
US/SI, pure shear, pure moment, reversed moment, reversed shear, local invalid,
backend invalid, initial 503/network failure, last-valid 503/malformed reference.
Views, Fit Connection and X-ray remained usable. No navigation or preview edit
automatically called design-check. One explicit design click retained the actual
default FAIL, unavailable source checks and ordinary_pass_allowed=false; source
pending does not override a genuine governing failure or hide the scene.

## Engineering invariance

Backend production, all controlled artifacts, engineering goldens, Slice 5/6,
dependency/lock/workflow files and historical freeze manifests/tests are unchanged.
Default U.S. engineering fingerprint remains
`eb589c21a8d84375ec6d7ded0b8ac147e0960e411b84adbbbc4e883140153617`;
SI remains `927c5fb5f56c3e2f239db05970aab27562281fdeb901531bbdd6765f4109ff4b`.
The exact centroid/shear-center/generated-torsion values and full component
wrenches are checked without recomputation in the frontend. Back/opening shear
remains -19.0625/+9.0625 kip. Flange force lines, local moments, unequal bolt planes,
two same-opening Channels, six plates, 24 Plate/Channel/Plate physical bolts,
material regions, review/disclaimer and Section 2.3.2 qualification remain exact.
Stiffness, rotation, full-strength and warping limitations are unchanged.

## Local QA and release gates

Local Windows Python 3.14.6 / Node 24.18.0 / npm 11.16.0:

- Backend: 2,896 passed; 24,142 statements and 6,556 branches, 100% coverage.
- Frontend: 603 passed in 42 files; 4,666 statements, 3,965 branches, 1,648 functions,
  3,385 lines, all 100% configured coverage.
- Hash-locked backend install, pip check, Ruff format/lint, strict mypy,
  Uvicorn/Alembic CLI and runtime/optional-persistence imports passed.
- Locked npm install, dependency consistency, ESLint, strict TypeScript, build,
  full and runtime npm audits passed; zero vulnerabilities.
- All Stage 4.1B G1-G112, Slice 6 G1-G72, Slice 5 and historical freeze regressions
  are part of the full backend run. No skipped matrix or altered golden.
- Existing non-failing Vite chunk-size and Three.Clock deprecation warnings remain
  outside this narrow correction. No dependencies were changed to remove them.
- The first locked reinstall encountered a native-module file lock held by the
  task's preview servers. Stopping those servers released it; retry succeeded.

Commit is gated on reviewed explicit staging and whitespace validation, subject
`fix: restore Channel moment splice workspace rendering`, expected count 102.
No amend or tag is authorized. After commit a fresh depth-one/no-tags/no-alternates
clone must pass complete backend/frontend QA, browser/root regression and all
freeze audits before a normal main-only push. Post-commit isolated/push/ref/CI
facts cannot be self-recorded in this single commit; the final completion report
must supply them. Failure stops before push, without amendment.

## Numbered completion-report index

1. Baseline: bd0529e, main clean/synchronized, count 101.
2. Predecessor hosted CI: owner-controlled order reports #96, 4/4 PASS; not independently retrieved.
3. Owner defect reproduced: blank root after Channel selection.
4. Controlled verification: all prescribed predecessor hashes and R1 sentinel verified.
5. Freeze protection: eight tag objects/targets preserved; all audits run.
6. Pre-mutation matrix: four valid/preset failures; four controlled invalid/network cases.
7. Exception: absent vector `.l`, scene point -> scene builder -> workspace useMemo.
8. Network: valid 200 response with correct backend field; raw payloads captured.
9. First loss: frontend DTO/adapter field-name mismatch.
10. Root cause: incorrect synthetic fixture duplicated the frontend assumption.
11. Frontend findings: field mismatch, absent reference validation, stale design-button gate.
12. Backend findings: correct geometry/serialization; no production correction needed.
13. Changed symbols: Channel interfaces, isChannelMomentSpliceReference/Preview, scene marker, button gate.
14. Selector transition: actual App/root regression and both browser builds pass.
15. Direct load: direct component initial mount passes; product deep-link restoration is unsupported.
16. Loading/failure: explicit prompt/error, root retained, retry available.
17. Invalid/last-valid: previous model retained; design disabled until current valid preview.
18. Default preview: mounted, six plates, exact trace.
19. U.S. preset: passes.
20. SI preset: passes.
21. References/torsion: exact unchanged backend values/fingerprints.
22. Web branches: -19.0625/+9.0625 kip unchanged.
23. Flange branches: full exact equilibrium retained.
24. Topology: six plates, two same-opening Channels retained.
25. Common bolt planes: actual unequal physical vectors retained.
26. Results/review: classification/disclaimer and all unsupported boundaries unchanged.
27. G1-G112: full regression passes, no authority edits.
28. Slice 6 G1-G72: full regression passes, no authority edits.
29. Historical/freeze: full suite passes; isolated gate required after commit.
30. Paths: four production files, one existing test fixture, three new regression-data/test files, QA and handoff.
31. Backend production changes: zero.
32. Frontend production changed files: four.
33. Dependencies/workflows/tags: zero changes.
34. Backend QA: 2,896 tests, 100% line/branch coverage.
35. Frontend QA: 603 tests, 100% configured coverage.
36. Static/build/security: passed, zero vulnerabilities.
37. Staged diff: reviewed explicit paths/whitespace required before commit.
38. Commit identity/author: final report after commit; exact required subject above.
39. Final count: required 102, verified after commit in final report.
40. Object-isolated: mandatory after commit, outcome in final report.
41. Push: only normal main after isolated gates; outcome in final report.
42. Final refs: require HEAD=origin/main=remote main; final report supplies hash.
43. R1 hosted CI: pending direct four-job evidence after push.
44. Owner acceptance: pending repeated visual acceptance after R1 CI.
45. Risks/deviations: no scope expansion; no URL restoration exists; historical display warnings retained.
46. No later moment family or freeze begun.
