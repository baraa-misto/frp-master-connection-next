# SHEAR01-DIRECT-OR2-F4 — controlled ASTM F593 Group 2 catalog

Owner review required. This candidate continues `1eb1fc389d4d91f7c2296da6e0c0bb681b511acb` on `codex/shear01-direct-f1`. It does not finalize or freeze Direct.

## Source and scope

The controlling F4 order supplies and approves the four Group 2 316/316L austenitic rows. Source classification is `OWNER_APPROVED_ASTMF593_TABLE_TRANSCRIPTION_RC1`, catalog ID `ASTM_F593_17_GROUP_2_316_316L_RC1`, revision RC1. This is an owner-approved transcription, not an original ASTM-issued digital document. Stable canonical JSON SHA-256: `ecb9ca81764f33f5926b2404870322d82325558855ba03f5b077b692e1c7b9ec`.

| Row | Condition / marking | Inclusive diameter (in) | Specified tensile (ksi) | Design Fnt (ksi) | Yield minimum (ksi) | Hardness |
|---|---|---|---|---|---|---|
| G2-AF | AF / F593E | .250–1.500 | 65–85 | 65 | 20 | B85 max |
| G2-A | A / F593F | .250–1.500 | 75–100 | 75 | 30 | B65 to 95 |
| G2-CW1 | CW1 / F593G | .250–.625 | 100–150 | 100 | 65 | B95 to C32 |
| G2-CW2 | CW2 / F593H | .750–1.500 | 85–140 | 85 | 45 | B80 to C32 |

Cold worked resolves CW1 or CW2 by exact physical diameter. The open .625–.750-in gap stays unsupported. The lower tensile bound supplies the existing Chapter 8 engine; no interpolation or second bolt calculator. Its frozen Fnv functions, area, phi=.75 and bolt time factor remain unchanged. Unknown thread location prevents bolt shear evaluation. Mixed planes retain independent source records. Group 1 and other alloys remain unavailable.

## API and application boundary

Authenticated `POST /api/v1/fasteners/resolve` accepts nominal diameter and `FASTENER-F4-RC1` catalog selectors; it does not accept client strength/results. `GET /api/v1/fasteners/catalog` adds controlled datasets and preserves the historical source-pending RC0 record. The Direct MAT1 multi-row design envelope accepts the same catalog selector, resolves it again server-side against the actual physical bolt diameter, then seals source and native calculation evidence into the authenticated snapshot.

Pydantic source validation and digest authentication remain at the API boundary. Frozen plain catalog values enter application orchestration. The application supplies a catalog-bound fastener snapshot to the existing engine. The frozen source enum is bridged as ENGINEER_APPROVED_DEVELOPMENT / DEVELOPMENT_ONLY; the exact owner-transcription classification is explicit in the source record. This resolves numerical bolt source authority without activating whole-connection qualification. The frozen thread enum has only known states: unknown is gated before resistance evaluation and remains UNKNOWN in audit provenance.

Only Direct catalog binding is verified. Other families retain their previous behavior and are BINDING_DEFERRED. Legacy J1 regression controls retain the RC0 fastener source state. Custom records remain session-owned and cannot overwrite RC1.

## UI and reports

The normal Direct preset automatically resolves the selected row and displays its condition, marking, backend-converted lower Fnt and per-plane Fnv. Range maximum and source identity are in a collapsed technical disclosure. Procurement conformance is neutral information; no per-connection supplier certification is required. Source failure/gap and unresolved threads remain explicit. Historical geometry preview warnings are not used to declare current catalog source status: the separate authenticated catalog summary owns that status.

Engineer Report presents concise catalog basis and actual native bolt shear substitutions/results. Full Technical Audit retains complete raw source, range comparison, thread state, native operands and signed result detail. Rendering does not change any engineering value.

## Required-check schedule and safety

The owner 0.5-in CW1 excluded-thread case changes from 5 evaluated / 12 unresolved to 7 evaluated / 10 unresolved, derived from the actual 17-item schedule. Only the two bolt shear entries become calculated. ICE source, Tg, first-row net tension, continuous W method limits, block shear and Section 2.3.2 qualification remain explicit. Numerical bolt FAIL retains RED precedence.

All 53 protected engine files, geometry, support-end authority, non-bolt demands/resistances, FRP factors and method limitations must retain exact baseline parity. No engineering freeze identity, main ref or tag is changed.

## Publication gates and evidence

The configured collected backend count is 8054 (7959 baseline plus 95 F4 tests). Frontend count is 1246 (1236 baseline plus ten F4 tests). Required local isolated gates are complete coverage, lint, strict types, builds, dependency consistency and zero npm audit findings. The workflow preserves inherited tests and adds actual signed F4 PDF generation/upload on Windows and Ubuntu.

Publish normally only after local QA passes; require exact candidate SHA four-job CI and inspect both platform reports before assigning `SHEAR01_DIRECT_OR2_F4_F593_READY_FOR_OWNER_REVIEW`. Actual candidate SHA, CI jobs, source-byte manifests, reports, rendered pages, numerical parity and final repository refs are recorded externally in `SHEAR01_DIRECT_OR2_F4_F593_CATALOG_CLOSURE_PACKAGE.zip`. PR #1 stays draft with OWNER REVIEW REQUIRED / DO NOT MERGE.

