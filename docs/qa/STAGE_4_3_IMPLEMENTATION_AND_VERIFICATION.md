# Stage 4.3 RC1 — implementation and verification record

## Authority and baseline

The sole Stage 4.3 order is `STAGE_4_3_WI_BEAM_FRP_SUPPORT_MOMENT_CONNECTION_CODEX_ORDER_RC1.md`, SHA-256 `1872CB38BE1A3CFED548CE6DEE5D4D183DAD3F3D3957197D61E376EB6D62BC33`. The acceptance matrix is `backend/tests/golden/stage_4_3_acceptance_matrix_rc1.json`, SHA-256 `3E277AF2388F15BA5C2CA2AA0B52ED9AAE7064F15DCFA354C8C233B174EB5043`. Both were read completely and verified before mutation; the exact final order sentinel is present. No earlier Stage 4.2 execution instruction is imported as Stage 4.3 authority.

Starting HEAD, origin/main and remote main were `c8094293e6da49aa830b5801f49aae537cccae2b`, clean main, 109 commits. Stage 4.2 freeze CI #104 attempt 1 was directly verified 4/4 SUCCESS; its tag object is `5ad81fe69c1ea17bc0a76daf34cf27f44963cecf`, peeled to that baseline. The mandatory consolidated pre-mutation capability/source/freeze audit is `STAGE_4_3_PREMUTATION_AUDIT.md`. Its source/geometry/native applicability probes found no unresolved engineering conflict; missing production qualifications are prescribed fail-closed states, not authority to invent a response.

One implementation commit is required: `feat: add W/I beam-to-FRP-support moment connection`, expected count 110. No amendment or tag is authorized. Exact-commit isolated verification, publication and hosted CI occur after this record is committed and are recorded in the external final report. They are not preclaimed here.

## Actual implemented product and dependency seams

Product `WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION`, contract `4.3-RC1`, appears as the fourth Moment Connections option. It is separate from all historical product requests. Incoming beam remains W/I. Receiving supports are exactly W/I flange, W/I web, hollow square, solid square and Channel web. FRP is the only connector provider.

New backend modules under `backend/src/frp_master_connection/`:

| Path | Responsibility |
|---|---|
| `domain/wi_frp_support_moment.py` | Immutable input, five-mode domain, exact unit canonicalization and view/engineering separation |
| `application/wi_frp_support_profile.py` | Actual selected profile/face, native Channel centroid and physical receiving layers |
| `application/wi_frp_support_moment_geometry.py` | Four angles, beam, support, finite bolt paths, exterior hardware envelopes, clearances, contacts and region axes |
| `application/wi_frp_support_moment_orchestration.py` | Native Slice 5, four Slice 7 cores, Stage 2.5A flange and Slice 8 web/support in-plane demand; complete support contribution/proofs |
| `calculation/support_attachment_response.py` | Qualified coupled support response, unilateral contact, exact six-component proof, physical bolt sections and per-layer participation |
| `calculation/sourced_bolt_interaction.py` | Explicitly source-specified Fnt/Fnv Eq.8-3 interface with native area/tension/shear/Decimal conventions |
| `application/wi_frp_support_moment_sources.py` | Five independent source categories, exact fixture/assembly binding and empty production registry |
| `application/wi_frp_support_local_checks.py` | Actual layer/material-direction bearing, both pull-through branches and applicable native local group paths |
| `application/wi_frp_support_moment_design.py` | Explicit resistance orchestration, completeness/status precedence and current failure records |
| `api/wi_frp_support_moment_schemas.py` | Strict untrusted DTOs; no client-supplied qualification/strength override |
| `api/wi_frp_support_moment_mapping.py` | Canonical domain mapping and unchanged native value serialization |

Two additive POST routes in `api/routes.py` retain trusted server identity:

- `/api/v1/calculations/wi-beam-frp-support-moment/preview`
- `/api/v1/calculations/wi-beam-frp-support-moment/design-check`

New frontend paths are `api/wiFrpSupportMomentContracts.ts`, `api/wiFrpSupportMomentClient.ts`, `fixtures/wiFrpSupportMomentBenchmarks.ts`, `visualization/wiFrpSupportMomentSceneModel.ts`, and four `workspace/` files: `WIFrpSupportMomentWorkspace.tsx`, `wiFrpSupportMomentWorkflow.ts`, `wiFrpSupportMomentFailures.ts`, `wiFrpSupportMomentWorkspace.css`. Historical shared changes are limited to the additive selector, optional exact backend head/nut geometry in `sceneModel.ts` and its optional branch in `fastenerPresentation.ts`. Historical cylinders omit that field and retain their previous path. The two exact OpenAPI route-inventory tests include only the two new routes.

No existing calculation engine is edited. Native helper reuse is at material-neutral seams; the concrete orchestration and concrete response wrapper are never invoked. Stage 4.2 remains untouched. Slice 5 outputs, all four Slice 7 core results and native Stage 2.5A/8 results are consumed directly. Web coordinates remain A=±1.5, B=1.25/2.75 at reference (0,2) in; free moment is explicit, not an invented eccentric force. Channel centroid comes from the native accepted Channel section engine, never a W/I web-centered surrogate. Algebraic target, native serialized aggregate and exact residual diagnostic remain distinct. Fractions prove reference/response mechanics independently of ambient Decimal precision; no epsilon or residual redistribution is introduced.

## Physical presets, paths and limits

All U.S. presets use incoming W/I 10×8 with tw=tf=0.5 in, four FRP angles 8×4×4×0.5 in, inside radius 0.25 in, gap 0.5 in, 2×2 member/support groups, flange gauge 5 in, web gauge 3 in, pitch 1.5 in and centroid distance 2 in. Support physical length is 48 in; preview clip is 36 in. Explicit hardware: 0.5-in bolt, 0.563-in hole, 1.25×0.125-in washers, 0.75-in head/nut across flats, head height 0.3125 in, nut height 0.4375 in, extension 0.125 in. These are explicit preset geometry, not inferred ASTM strength or qualification.

| Support | Preset | Physical path / authority boundary |
|---|---|---|
| W/I flange | D16, BF12, tw=tf0.5 | Angle leg + selected flange; rear hardware clears web/junction |
| W/I web | D16, BF8, tw=tf0.5 | Angle leg + selected web only; full perpendicular flanges remain physical |
| Hollow square | 12×12, wall0.5 | Angle leg / near wall / void / far wall, exterior hardware only; no sleeve, cavity material or equal wall share |
| Solid square | 12×12 | Continuous full-depth solid crossing, exterior hardware; no thin-wall or thin-plate surrogate |
| Channel web | D16, BF6, tw=tf0.5 | Actual web/opening/flanges and native asymmetric centroid; rear/opening hardware clearance |

Four distinct support groups have 16 uniquely identified support bolts. Twelve physical member bolts include the shared web crossings. Fourteen eligible selected faces are tested. Full hole/washer footprints, actual fillet/heel regions, head/nut/extension envelopes, adjacent/perpendicular members, group overlap, invalid gap, asymmetry and square dimensions are validated without auto-correction. Loads do not move physical geometry. View lengths affect only backend drawing clipping, not engineering ends, source domains, capacities or fingerprints. Receiving LW follows the vertical support; beam and angle regions retain their own R14B bases.

## Support response and numerical checks

Thin single-lap support projections use accepted Slice 8 in-plane demand only. Fn/Mu/Mv remain intact and unavailable normal tension is not zero. Hollow/solid participation requires actual qualified response before assigning any local wall/section demand.

`QUALIFIED_FRP_SUPPORT_ATTACHMENT_RESPONSE_RC1` binds all four group wrenches, geometry, selected face/profile/centroid, material, fastener and hardware, physical layers, units, contact assumptions, load case, native fingerprints and source provenance. Bolt tensions are nonnegative total values including prying, contact is compression-only in the opposite direction, and authorized couples are separate ledger records. External actions recover all six components exactly. Internal shaft sections and receiving-layer forces are separately bound; they cannot duplicate external reaction or hide tension by declaring zero section demand. Long-bolt and multi-wall coverage is mandatory where applicable. Closure alone is never qualification.

Separate qualifications cover (1) angle body/heel, (2) member attachment including out-of-plane demand, (3) coupled support response, (4) fastener strength/condition/thread/grip, and (5) local support-zone capacity and intergroup interaction. Production registry is empty. Test sources are not reachable through application selectors or by typing their reference.

Verified test-only response/strength records drive actual numerical shear, tension and combined-bolt checks on all five physical topologies. F593 without a bound approved Fnt/Fnv remains SOURCE_REQUIRED. No two-wall penetration is converted into automatic double-shear capacity.

Local bearing uses each actual layer's thickness and LW/CW direction, with native thread/single-lap factors once. Pitch reduction uses actual physical row coordinates only for an established cardinal constant-force row mapping. Unsupported oblique/independent-moment row mapping is named `CONSTANT_FORCE_DIRECTION_ROW_PITCH_AUTHORITY_REQUIRED`; it is not rounded into applicability. Pull-through uses the lesser of both accepted Eq.8-4 branches, actual seated washer and required FSH_LT/through-thickness plus FSH_INT authority, without copying the bearing pitch factor. Hollow near-wall absence of an exterior washer is not repaired by inventing internal hardware. Full solid depth does not become thin-plate failure thickness.

Native first-row/interrow/block/shear/cleavage behavior is used only when actual direction, physical free ends, junction exemptions, rows and current method applicability establish it. Uncovered face bending, junction transfer, shared net/block paths, common-region interaction, long-bolt/hollow-wall response, or solid 3-D load spread/splitting require explicit local assembly coverage. No arbitrary Chapter 7 panel or out-of-plane/prying formula is created. A local-zone source must cover every unresolved required local-check ID as well as mode-specific and common-group requirements; evaluated native failure still governs.

## Results and qualification boundaries

For all five default combined-load presets the result is FAIL with native `FIRST_ROW:TOP_FLANGE_ANGLE` governance. Native first-row, bearing and interrow failures remain visible, with missing qualifications subordinate but explicit. The eight-load sweep has FAIL for nonzero presets and SOURCE_REQUIRED for zero: absent response/preload authority is not a proof of zero demand. Support fasteners and local zones cannot claim complete success without all required source/response coverage. Highest covered state is review-required qualified success, never ordinary PASS. Whole receiving-member analysis, foundation reactions, stiffness, rotation capacity and full-strength classification remain external/not evaluated.

The frontend displays current backend scope statuses and failure records, not a second governing selection. Group wrenches are labeled as group wrenches, and support demand/sections/contact/layers/method/source records are retained in expanded traces. There is no inherited concrete/anchor warning in the new product. All historical products keep their own messages and limitations.

## Acceptance matrix and independent evidence

`STAGE_4_3_ACCEPTANCE_COVERAGE.json` maps all 90 literal IDs and all six fixture references. Five supports × eight loads × U.S./SI gives 80 executable product cases (40 parametrized tests invoking both units). Direct independent native calls check Slice 5, Slice 7, Stage 2.5A and Slice 8 equality; no second precision path is an oracle. Exact small fixtures F43-R01–R04 prove tension, unilateral contact, reversal and six-component response; F43-T01 proves the reference shift; F43-B01 proves the explicit stress interface. Synthetic source fixtures are validator/integration evidence only.

Additional tests cover all 14 physical faces, hardware and containment negatives, source mutation/absence/qualification/coupled interaction, per-wall participation, layer/shaft mismatch, native local row/factor boundaries, zero/pure free moment, ambient Decimal 6/28/80/120 contexts, source unit equivalence, backend trusted identity, strict rejection of unapproved actions/material/provider/profile, request races, display-only fingerprint stability and all historical regressions.

Supplemental native catalogue SHA-256: `F8A15BEBD6351045C311341D40A4F97331DB31BE59F49BE9C005F2796A981D8E`. It records native results/fingerprints and separate proof fields, not a replacement engineering golden. Five compact frontend fixtures are reproducible projections of native responses; their raw hashes are pinned in `backend/tests/test_stage43_governance.py`. Historical manifest SHA-256: `061081B63B21960DD3501C28EE667499B4D03794ED936AE11E29AACA08A7E471`, with 446 baseline blobs and all ten tag objects/peeled targets. Historical object resolution uses the pinned baseline or sealed manifest, never successor HEAD as a historical tree.

## Local QA and browser evidence

Full local backend QA passed: 3,453 tests, 100% configured statement/branch coverage, Ruff format/lint, strict mypy, pip consistency, runtime/import smoke. Full frontend QA passed: 642 tests in 45 files; 100% statements (5332/5332), branches (4516/4516), functions (1891/1891), lines (3758/3758); ESLint, strict TypeScript, production build and dependency validation. Both npm audit variants returned zero findings. Existing timeouts/coverage targets/dependencies/workflows are unchanged. All Stage 4.2 G1–G128, Slice 5 G1–G52, Slice 7 G1–G72, Slice 8 G1–G80 and historical freeze tests remain in the full suite.

The actual built-in browser selector exercised all five supports with default, pure shear, pure moment and simultaneous moment/shear reversal (20 design cases), plus SI/default identity and final owner-ready default. 3D/top/side/X-ray views show actual support profiles, far-wall/solid-depth shanks, exterior head/nut/washer endpoints and region material axes. The inherited diagnostic hole-axis overlay intentionally draws through opaque solids; it was switched off to inspect actual solid occlusion, then X-ray inspected hidden hardware separately. This is a presentation toggle, not geometry correction.

Browser checks also covered unknown source references, geometry-triggered source invalidation, invalid zero gap with disabled design and retained last-valid canvas, load-induced stale design, view-only clipping with identical fingerprint/current design, delayed obsolete request cancellation, a deliberately injected ConnectionFailed preview and retry recovery, rapid historical/new product switching, 800-pixel compact fieldsets and 125% page-scale inspection (restored), and repeated view/Fit/Reset operations with zero API requests. No console errors or uncaught exceptions were observed. The only failed request was the deliberately injected one; expected superseded requests were aborted. Raw interception was cleared and temporary viewport/zoom settings restored. No production defect required a browser-driven source change.

External browser evidence is under the current task's approved visualization directory: `stage43-browser-evidence.json`, `stage43-wi-flange-default.png`, `stage43-wi-web-top-xray.png`, `stage43-hollow-default.png`, `stage43-hollow-top-xray.png`, `stage43-hollow-solid-hole-overlay-off.png`, `stage43-solid-default.png`, `stage43-solid-top-xray.png`, `stage43-channel-default.png`, `stage43-channel-top-xray.png`, `stage43-invalid-gap-last-valid-model.png`, `stage43-deliberate-failed-preview.png`, `stage43-narrow-fieldsets.png`, `stage43-125-percent-zoom.png`, `stage43-final-owner-default.png`. These local request/response/screenshots are not copied into source. This record does not claim owner acceptance.

Local application: `http://127.0.0.1:5173/`, backend `http://127.0.0.1:8000/`. The existing repository Vite process was safely reused. The old repository backend was identified by its exact command, found to expose only historical routes, and restarted with the new source; persistent backend terminal session 80820. Final report records current PIDs/session evidence after isolated verification/publication. No unrelated process was stopped.

## Remaining publication gates and hygiene

Review/stage explicit named paths only; verify cached whitespace, byte-exact order/matrix, all historical blobs/tags and no PDF/dependency/workflow/lock/secret residue. One commit at count110 must then pass complete fresh depth-one/no-tags/no-alternates QA using locked dependencies, exact source identity and clean Git-aware status checks. Do not amend or push a failed isolated result.

Only after those gates may the exact unchanged commit be pushed normally to main with no tags. Direct hosted Backend Ubuntu/Windows and Frontend Ubuntu/Windows conclusions must be recorded with run, attempt and commit. No hosted success is inferred. Owner final visual/result acceptance remains pending even after green CI. Leave the verified app running; do not freeze Stage 4.3, begin 316SS or a later connection family.
