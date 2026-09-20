# Stage 3.4A-R2 Multi-Member Tee blank-workspace correction

## Observed failure

Selecting **Brace/beam node — Multi-member Tee connector** blanked the application in both the Vite development server and the production-build preview. The route and workspace mounted, the default all-three-slot `3.4A-RC1` request completed with HTTP 200, and the response passed the top-level transport-version check before the first render exception.

The first exception was `Cannot read properties of undefined (reading 'base_connection')`. The frontend contract and synthetic fixture named each backend slot snapshot `tee_visualization`, while the strict backend dataclass serializer correctly emitted its controlled field name, `visualization`. `buildMultiMemberTeeSceneModel` therefore passed `undefined` to `buildTeeSceneModel`; React unmounted the application root after that uncaught render exception.

## Correction

- Bind the frontend slot contract and scene adapter to the backend-authored `visualization` field.
- Make current-contract validation require the slot wrapper and minimum Tee scene shape before accepting a response; obsolete or unknown wrappers remain fail-closed as response errors.
- Make the frontend fixtures reproduce the actual serialized backend contract.
- Include the authoritative per-slot arrow ID in projected action-label keys so repeated force components from independent slots remain distinct React presentation records.
- Cover selector routing, loading, valid, invalid, transport-failure, unsupported-contract, persistent-viewer, and every one/two/three-slot topology with explicit window-error trapping.
- Advance the active frontend-source Git-tree assertion to this authorized successor while retaining the Stage 3.4A tree as an explicitly rejected historical predecessor.

No placeholder geometry, frontend engineering calculation, fallback slot, or backend production change is introduced.

## Engineering transitions

`NONE`.

Stage 3.4A G1-G20 values, support-wrench assembly, slot demand values, geometry, group identities, engineering fingerprints, and all frozen Direct/Tee/Clip-Angle fingerprints remain unchanged. This correction changes only the frontend transport binding, response guard, presentation identity, fixtures/tests, active-successor freeze assertion, and this QA evidence. Visual acceptance may resume only after full local, object-isolated, hosted-CI, and real-browser gates complete.
