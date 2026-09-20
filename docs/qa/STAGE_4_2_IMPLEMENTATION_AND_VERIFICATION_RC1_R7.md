# Stage 4.2 RC1-R7 — Implementation and verification record

This is the additive W/I beam-to-concrete-wall major-axis moment product, not a change to any frozen family. Publication and owner acceptance are separate gates. This record describes the candidate; the final completion report supplies the committed SHA, isolated checkout and hosted evidence without amending a published implementation.

## Authority and pre-mutation disposition

The accepted baseline was verified clean on main with HEAD, origin/main and remote main all at 473a3c8cd43f13022d254dae2477084895478c74, count 106. R7 was read completely; its three approved hashes and final sentinels matched, and replacement G1–G128 parsed completely. The targeted native pipeline reproduced FIRST_ROW:TOP_FLANGE_ANGLE and FAIL before mutation. The owner-accepted R6 consolidated sweep had no other outstanding blocker; already-passed expensive pre-mutation gates were not repeated solely for R7.

The byte-exact package inventory is [STAGE_4_2_CONTROLLED_PACKAGE.json](STAGE_4_2_CONTROLLED_PACKAGE.json). Original decision/specification/ledger/order remain unchanged, interpreted under cumulative R3–R7. Only RC1-R7 golden is registered. R7 hashes are:

- Clarification: 6AC4C13F013FC024ABA513AD0C09169AA3E7860FB80586683485DCD16CECA145
- Golden: 6F8A22388BEEFFB1CE1B4EF9556261C63200C632E5D50F5447F4011D2C15EA2B
- Order: F80FE7A41479916377505DE2CC14B280915CEF50849315B6E9F67BFB8A8AD188

ASCE/SEI 74-23 and Erratum 1 effective January 13, 2026 were reused as read-only sources. Their pinned hashes are in the inventory. Source review covered Sections 2.3.2, 2.9, 8.1/8.1.1/8.1.2, 8.3/8.3.2/8.3.4/8.3.4.1/8.3.4.2 and relevant C8.1.3/C8.3.4 commentary. No PDF, long source quotation or new normative equation is copied into this stage.

## Shared-architecture and prior-error-prevention audit

The successor consumes existing W/I and finite-wall/anchor quantity contracts, angle geometry/core/provider contracts, physical region/box presentation contracts, shared material-axis renderer, full-wrench and group-demand engines, adjusted properties/factors, trusted request identity, and persistent viewer/request-state architecture. New code is limited to Stage 4.2 placement, native-engine composition, source binding, transport and scene/workspace integration.

The pre-mutation audit preserved CS5 precision 80/ROUND_HALF_EVEN, CS7 native arithmetic, Stage 2.5A native demand/handoff/group-mode selection and CS8 exact rational mechanics/Decimal projection. It distinguished algebraic equilibrium from serialized native cross-engine diagnostics. It checked physical web references, signed negative-web demand, pure free moment, locked ICE/factors, F593 source-pending behavior and default failure precedence. Backend material bases remain authoritative; the frontend applies a proper rigid rotation (L,V,T) to (X,Z,-Y), determinant +1, and does not reflect or reconstruct engineering geometry.

The API fixture is generated from native backend results and verified as an exact reduced subset; frontend assertions are not a second engineering oracle. Last-valid scenes bind their accepted preview actions, never newly edited sidebar actions. AbortController and latest-response-wins protect preview/design independently. Frozen source identities are resolved historically, never by comparing successor HEAD frontend source to a prior freeze.

## Ordered completion matrix

1. Baseline: accepted Slice 8 test-only successor above, count 106.
2. Freezes: all nine existing freeze tags and their manifests remain untouched; all historical audits are required.
3. Artifacts: byte-exact inventory and R7-only golden above; no superseded golden registration.
4. Slice 5: direct complete top/web/bottom resultants; G1–G52 regression unchanged.
5. Slice 7: four direct neutral-core calls and native FRP provider; G1–G72 unchanged.
6. Stage 3.5: reuse finite wall and external-anchor geometry contracts, not concrete capacity.
7. Sources: pinned standard/erratum read-only verification, no repository PDFs.
8. Architecture: additive successor adapter; inherited calculation/dependency identities recorded in STAGE_4_2_INHERITED_IDENTITIES.json.
9. Product: WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION, contract 4.2-RC1, third Moment selector option.
10. Frame: physical L/V/T, finite wall at L=0, positive beam-wall gap.
11. Actions: signed axial P_L, major shear V_V and structural major moment M_T only.
12. Negative-end adapter: physical right-hand moment equals negative structural moment.
13. Geometry: one complete W/I beam, finite wall, exact user quantities and full physical bolt/anchor endpoints.
14. Topology: one top angle, one bottom angle, mirrored positive/negative web angles.
15. Angle frames: top (+T,+L,+V), bottom (-T,+L,-V), positive web (-V,+L,+T), negative web (+V,+L,-T).
16. References: separate heel, member and support references; web heel-local A=±1.5, B=1.25/2.75, centroid/reference (0,2).
17. Interference: bounded parts, positive gap, leg/heel/hole clearances, overlaps, locked-pair and finite wall/embedment checks; no auto-repair.
18. Slice 5: every region force and local moment is retained; M/z is not substituted.
19. Top: complete top-flange wrench shifted to its physical interface.
20. Bottom: complete bottom-flange wrench shifted independently, signed reversal retained.
21. Web pair: exact physical symmetry gates half-sharing of the complete wrench.
22. Positive web: default F_A=5, F_B=3.6, M_C=1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in.
23. Negative web: default F_A=-5, F_B=3.6 and the exact negative of item 22's moment.
24. Four cores: member/heel/support equilibrium is inherited and checked; no wrapper arithmetic replaces CS7.
25. Provider: FRP only; neutral core remains material-independent, unsupported 316SS fails closed.
26. Instep: top/bottom zero direct instep shear; both web extrusion-force checks use existing Equation 8-15 authority. Flexible-fixture prying remains external.
27. Connector sources: exact-bound full-wrench packages, six signed positive/negative strength pairs and source-authorized interaction; no test source exposed in production.
28. Member attachment: F_C/M_A/M_B remain complete and require exact-bound qualified coverage; no invented bolt tension, pull-through, delamination or prying.
29. Flanges: direct native Stage 2.5A outputs consumed verbatim, independent native oracle equality; no controlling N/4 recomputation.
30. Web bolts: one common physical Angle/Web/Angle shank per axis, two actual planes.
31. Web demand: R3 supersedes the original Stage 2.5A web dispatch. Direct CS8 calls retain independent M_C at (0,2), with M_C,c=M_C,R.
32. Local FRP: existing eligible material-direction-specific bearing/net/interrow/group consumers. Nonstandard holes and unsupported reverse/general group paths remain explicitly unevaluated; no false standard-hole net area or resistance extension.
33. Out-of-plane: retained separately from in-plane local checks, never silently dropped.
34. Anchors: four 2×2 default blind anchor groups, exterior hardware only, no fictitious far-side hardware.
35. Handoffs: four complete group wrenches at exact physical references, no individual anchor forces.
36. Wall assembly: exact shifts and sum; native combined diagnostics +3E-79 kip axial, +6E-79 kip-in right-hand / -6E-79 structural. These are not tolerances or redistributed actions.
37. Wall reaction: exact equal-and-opposite assembled wrench, foundation transfer counted once.
38. External boundary: no anchor steel/concrete/breakout/pullout/pryout capacity or fabricated force split.
39. Preview: geometry, complete demand, eight source plans, handoffs and proofs; resistance calls are patched to fail in tests and remain zero.
40. Design: only explicit Run Design Check requests resistance; edits stale prior results.
41. Internal status: default FAIL, EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE.
42. Whole status: EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED, never ordinary whole-connection PASS.
43. Qualification: backend disclaimer retained; stiffness/rotation/full-strength classification unevaluated.
44. API: strict decimal strings, trusted server identity, additive preview/design routes, engineering status distinct from HTTP, deterministic native response.
45. Frontend: persistent shared shell/viewer, locked flange/web pair controls, U.S./SI loaders, no frontend mechanics.
46. Sources UI: flange/web connector and member-attachment source references only; no invented qualified strengths.
47. Trace: complete Slice 5, four core/member/heel/support/demand traces, source plans, all native failed checks and subordinate missing sources.
48. Scene: 12 solid parts, 12 member bolts, 16 blind anchors, 11 FRP material regions, references and signed actions; shared solid/X-ray/navigation.
49. State: debounce, abort, latest response, invalid/last-valid/request failure/retry, no blank-root fallback and no automatic design.
50. Pure/sign cases: pure axial/shear/moment and reversed signs; pure-moment native diagnostics +2E-78/-2E-78 kip-in remain relational evidence.
51. G1–G128: grouped exact mechanics/native-oracle tests plus immutable inheritance/entire historical regression evidence; no tolerance.
52. Slice 5 G1–G52: unchanged full regression required.
53. Slice 7 G1–G72: unchanged full regression required; Slice 8 G1–G80 and Stage 2.5A compatibility are also required.
54. Units: exact U.S./SI quantities and engineering identity; renderer conversion is presentation-only.
55. Fingerprints: native core, source-plan-bound engineering and design-result identity; historical fingerprints are unchanged.
56. Historical regressions: full suite includes all nine successor-safe tag/object/manifest-only freeze audits and every accepted family.
57. Changed paths: additive Stage 4.2 code/tests/artifacts plus narrow routes, Moment selector and governance updates; final staged inventory recorded at commit.
58. Backend production paths: eight new modules plus additive routes.py = 9.
59. Frontend production paths: six new modules plus additive Moment selector = 7.
60. Dependencies/workflows/lockfiles/tags: zero changes. Slice 8 Windows stabilization is byte-identical.
61. Backend QA: targeted 93 tests and full 3251/3251 suite passed; 100% statements/branches (25525 statements, 6842 branches), including all inherited engines and freeze audits.
62. Frontend QA: 615/615 across 43 files; all configured coverage 100% (4931 statements, 4184 branches, 1752 functions, 3520 lines).
63. Static/build/security: full locked installs/dependency checks, backend Ruff/format, strict mypy and runtime imports/CLI checks, frontend ESLint, TypeScript and build all passed; both npm audits report zero vulnerabilities. All 60 repository JSON files parse.
64. Staging: explicit approved paths only; cached whitespace and scope audit required before commit.
65. Commit: required subject feat: add W/I beam-to-concrete-wall moment connection; no amend. Final SHA/author supplied in final completion evidence.
66. Count: exactly 107 after the single implementation commit.
67. Isolated: fresh depth-one/no-tags/no-alternates full QA required after commit, before push; failure stops publication.
68. Push: normal non-force main only after all prepublication gates; no tags.
69. Refs: require local HEAD=origin/main=remote main=candidate SHA.
70. Hosted CI: direct Backend/Frontend Ubuntu/Windows evidence required; pending until retrieved.
71. Owner acceptance: final visual/result review pending, never inferred from tests or local browser.
72. Deviations/risks: no engineering authority deviation. General reverse/group paths without existing applicability remain explicitly unevaluated; F593 strength, qualified connector/attachment packages and concrete/anchor design are not fabricated. Existing bundle-size warning and historical jsdom navigation notice are not hidden.
73. Scope stop: no 316SS resistance/exposure and no next moment family begun.

## R7 native failed-check record

The exact native failure sequence is preserved without sorting or selection override:

1. PIN_BEARING:TOP_FLANGE_ANGLE:B_R1_L1
2. PIN_BEARING:TOP_FLANGE_ANGLE:B_R1_L2
3. PIN_BEARING:TOP_FLANGE_ANGLE:B_R2_L1
4. PIN_BEARING:TOP_FLANGE_ANGLE:B_R2_L2
5. FIRST_ROW:TOP_FLANGE_ANGLE
6. INTERROW:TOP_FLANGE_ANGLE:BOLT_LINE_1
7. INTERROW:TOP_FLANGE_ANGLE:BOLT_LINE_2
8. PIN_BEARING:WI_TOP_FLANGE:B_R1_L1
9. PIN_BEARING:WI_TOP_FLANGE:B_R1_L2
10. PIN_BEARING:WI_TOP_FLANGE:B_R2_L1
11. PIN_BEARING:WI_TOP_FLANGE:B_R2_L2
12. FIRST_ROW:WI_TOP_FLANGE
13. INTERROW:WI_TOP_FLANGE:BOLT_LINE_1
14. INTERROW:WI_TOP_FLANGE:BOLT_LINE_2
15. FIRST_ROW:BOTTOM_FLANGE_ANGLE

All are FAIL. Native governing selection is FIRST_ROW:TOP_FLANGE_ANGLE, not an overridden pin-bearing result. All four CONNECTOR_SOURCE:SOURCE_REQUIRED and all four MEMBER_ATTACHMENT_SOURCE:SOURCE_REQUIRED entries remain visible and subordinate. The exact material and flange/web factor fingerprints are tested against G103. Qualified golden strengths are arithmetic-only test sources and are never production material/qualification claims.

## Browser and final verification evidence

Backend and frontend development servers were started automatically in persistent Codex terminal sessions at localhost:8000 and localhost:5173. The Codex built-in browser mounted the product through the real Moment Connections selector. Browser/CDP inspection verified the following against real backend responses:

- U.S. default: current valid preview, explicit design FAIL, native FIRST_ROW:TOP_FLANGE_ANGLE, all 15 ordered failures and eight subordinate source requirements visible. The engineering fingerprint is 4629228f806f8ec9e80c24eca9ee3c33b22dab5f3195eea75490772c94fd0624.
- SI loader: identical canonical engineering fingerprint, depth 254 mm and correctly formatted wall structural moment 11863.41 kN-mm. U.S. wall display is 105 kip-in; native exact values remain unchanged in the complete trace.
- Pure axial, pure shear, pure moment, reversed shear and reversed moment: unchanged geometry, complete accepted native wrenches, equilibrium proofs passed, zero automatic resistance/design requests. Pure moment preserves zero web forces and nonzero opposite web local moments; it is not reduced to flange M/z.
- Positive-gap and physical interference invalid cases: design disabled, explicit invalid-geometry reason, last valid canvas retained. A deliberate CDP block of only the localhost preview endpoint verified request-failure/retry recovery; the block was removed and retry returned a current valid preview.
- Arrow-value editing updates the same sidebar axial-load state and the backend preview without triggering design. Existing design results stale on engineering edits.
- Solid/X-ray, 3D/Front/Top/Side 1/Side 2, model selection, material/reference/global overlays and inspectors were exercised. All 11 FRP material regions retain backend LW/CW/TT bases; concrete has no fabricated FRP axes.
- Navigation stress completed 21 rounds: 147 view/Fit/Reset actions, 42 orbit/pan drags and 42 wheel actions, totaling 66.636 seconds of active interaction. CDP request wall-clock evidence shows zero application requests during this stress; the canvas remained responsive and current.
- No unexpected runtime exceptions, console errors, failed application requests or blank-root failures occurred. The intentional blocked-preview failure and normal aborted superseded preview requests were distinguished from unexpected failures. Existing Three.Clock deprecation warnings during shared-view changes, Vite bundle-size warnings and historical jsdom navigation notices were retained, not hidden by dependency or shared-source changes.

Browser review led to two Stage 4.2-only presentation corrections: readable moment-unit formatting (without changing native serialized authority), and a neutral containing wrapper so the sticky viewer cannot cover the trace cards. Both corrections were covered by the final complete frontend QA rerun. A Windows npm reinstall initially encountered a native-library file lock held by the development server; stopping that server, rerunning the complete QA successfully, and restarting it resolved the operational issue without any package/lock change.

Object-isolated verification, committed-state refs and hosted status are supplied in the separate final completion report after those gates finish. Owner final visual/result acceptance remains pending and is not inferred from this local matrix. No pending gate is deemed passed by this document.
