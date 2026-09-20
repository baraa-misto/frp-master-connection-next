# Stage 2.5C-R2 loaded-boundary placement frontend freeze change

## Authorization and defect reconciliation

Stage 2.5C-R2 corrects one backend-authoritative placement defect in the unified
multi-row connection workflow. `loaded_boundary_to_row_1_distance` reached the API,
application request, validation, planning, preview scheduling, stale-state logic, and
fingerprints, but `_build_geometry` used it only to enlarge the loaded-side boundary.
Canonical bolt centers therefore did not move. The physical snapshot then subtracted
the resolved Row 1 coordinate, independently erasing any future whole-group
translation before the shared Three.js scene received it.

The correction keeps the accepted loaded boundary fixed in the existing local
connection coordinate system. The independent distance now places Row 1 back from
that boundary, and every other row follows at unchanged pitch. Physical bolt, hole,
and washer positions use the same canonical longitudinal offset from the accepted
single-bolt station. The Stage 2.5A input receives those corrected physical bolt
coordinates without downstream patching.

## Controlled identities

| Artifact | Historical/active identity |
|---|---|
| Immutable Stage 2.3 freeze tag | `stage-2.3-interface-geometry-freeze` |
| Immutable tag target | `5bc545ab8251f9bd49dedc776962937ed5e822a2` |
| Historical Stage 2.3/R8 `frontend/src` tree | `df664801ea31a5a33e582e886dc787bf4f9be8aa` |
| Stage 2.5C-R1 predecessor `frontend/src` tree | `035af7c9c44c49914c63c68edf6ec4eea5521bcf` |
| Active Stage 2.5C-R2 `frontend/src` tree | `cd25332af05c101aa008934a7b900d8c220938f3` |
| Unchanged `frontend/package.json` blob | `b753abd55004168eee5844879f0596d435fe4b5a` |
| Accepted secure lock blob | `ae1831268db42005517343bf555f054a673ae520` |
| Accepted secure lock SHA-256 | `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254` |

The active identity is derived from the complete reviewed `frontend/src` tree. The
audit accepts only the historical Stage 2.3 source with an approved lock or this active
R2 source with the secure lock. R1 and every other interim predecessor remain
provenance but are rejected as active identities. Content change, addition, deletion,
rename, arbitrary-tree, package, and lock mutations remain fail-closed with
path-separator, line-ending, enumeration-order, checkout-location, and depth-one
invariance.

## Frontend scope

The frontend retains one session state and maps
`BoltGroupState.loadedBoundaryToRow1` exactly to
`loaded_boundary_to_row_1_distance`. It performs no placement arithmetic. The shared
scene continues to consume backend `physical_bolts` for 3D, Front, Top, Side 1, and
Side 2. The optional 2D diagnostic consumes backend planar bolt coordinates and now
labels the backend-reported loaded boundary explicitly.

No dependency, lockfile, API schema, equation, controlled specification, golden,
workflow, persistence, report, authentication, billing, or freeze-tag change is made.

## Acceptance state

Focused backend and frontend placement tests pass locally. Local real-browser review
compared 2 in and 4 in loaded-boundary cases in 3D, Front, Top, Side 1, Side 2, and
the optional 2D diagnostic. The server-authored bolt/hole group translated together,
pitch and gauge remained independent, geometry remained valid, no design ran
automatically, and the loaded-boundary label remained clear of the demand annotation.
The pre-existing Three.js clock deprecation warning remained; no browser error was
reported.

Full local QA, object-isolated committed-state verification, push, hosted
Ubuntu/Windows CI, and direct user visual acceptance are recorded only after their
respective evidence is available. Hosted success and final Stage 2.5C visual
acceptance remain pending until then.
