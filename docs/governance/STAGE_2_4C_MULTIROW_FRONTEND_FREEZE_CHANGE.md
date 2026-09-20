# Stage 2.4C-R3 solid-fastener-hardware frontend freeze change

## Authorization and correction history

Baraa Misto authorized Stage 2.4C-R1 after visual review rejected the pushed Stage 2.4C
workspace split. Commit `19c5b59` and frontend tree
`cf71cf158afd3525aba0849e207746b6a6842f73` were hosted-CI-green, and their backend
multi-row engine, planning, orchestration, and API remain valid, but that frontend tree
is a visually rejected interim successor. It is historical provenance and is not an
accepted active frontend identity.

R1 places row/bolt controls, multi-row preview, physical bolt selection, and multi-row
results inside the familiar Stage 2.3 connection workspace and its canonical Three.js
scene. The original annotated freeze tag is not moved, deleted, recreated, or pushed.
The exact R1 commit later passed all four hosted Ubuntu/Windows backend/frontend jobs
in 2 minutes 54 seconds with 167 frontend tests, but user
visual review identified fastener-scale visibility and the missing opposing side view.

R2 retains the unified workflow. It renders canonical bolt and physical-hole diameter
with exact-radius, non-pickable presentation outlines, makes the multi-row physical
scene use the same backend-derived standard hole as its engineering snapshot, and
replaces the single Side preset with orthographic Side 1 and exact opposing Side 2.

R3 retains all accepted R2 behavior and removes only the open-ended bolt-shank
wireframe overlay that read as a hollow cage. One shared frontend renderer now keeps
the canonical shank capped and solid, preserves authoritative washers, and adds
schematic closed hex head/nut primitives. The approved display-only head ratios are
1.50 diameter across flats and 0.625 diameter high; the nut ratios are 1.50 diameter
across flats and 0.875 diameter thick. They are not engineering dimensions and enter
no backend contract, fingerprint, validation, resistance, utilization, or report.

## Controlled identities

| Control | Identity |
|---|---|
| Original freeze tag | `stage-2.3-interface-geometry-freeze` |
| Immutable tag target | `5bc545ab8251f9bd49dedc776962937ed5e822a2` |
| Historical Stage 2.3/R8 `frontend/src` tree | `df664801ea31a5a33e582e886dc787bf4f9be8aa` |
| Hosted-CI-green but visually rejected interim tree | `cf71cf158afd3525aba0849e207746b6a6842f73` |
| Historical accepted Stage 2.4C-R1 unified-workspace tree | `8f8b5c65559f162363d3ea2bb58f2e21cf18ba9d` |
| Historical accepted Stage 2.4C-R2 fastener/view tree | `f95396ff7ce5604f08f40b04b7b5e216271672c6` |
| Active Stage 2.4C-R3 solid-hardware tree | `deb93d01646580ae62c9f90a507446d84019bd87` |
| Unchanged `frontend/package.json` blob | `b753abd55004168eee5844879f0596d435fe4b5a` |
| Historical R8 lock blob | `f2a594dae8c871d5c1c78e69f1023d6e77adf6e6` |
| Accepted secure lock blob | `ae1831268db42005517343bf555f054a673ae520` |
| Accepted secure lock SHA-256 | `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254` |

The active R3 identity is filled only from `git write-tree` and
`<staged-tree>:frontend/src` after every reviewed frontend source change is staged.
Pre-commit audit reads the repository-authoritative index tree; clean-checkout and
hosted audit read `HEAD:frontend/src`. Historical Git objects are not required in a
depth-one checkout.

## R3 source shape and preserved invariants

R1 removed the separate `MultiRowEngineeringWorkspace.tsx` and made
`SingleBoltEngineeringWorkspace.tsx` the unified connection-state owner. Existing
visualization and API-contract modules accept the backend-authoritative physical
multi-row snapshot. No package declaration, lockfile, dependency, workflow, or tag is
changed.

R2 keeps that ownership and adds no frontend engineering authority. Bolt radius is
exactly canonical diameter divided by two; physical-hole radius is independently the
backend physical-hole diameter divided by two. The always-visible outlines reuse those
exact radii and cannot be picked. Side 1 uses the former global `+X` viewing direction;
Side 2 uses global `-X`, with the same fit target, global `+Z` up vector, and
orthographic projection. View switching changes no request or design state.

R3 keeps the hole outline but removes it from the shank. `fastenerPresentation.ts`
derives only the controller-approved schematic head/nut display proportions from the
canonical bolt diameter. `UNDER_HEAD` and `UNDER_NUT` washer identity determines the
outside placement; absent washers fall back to the authoritative stack ends. Washer
diameter/thickness, shank diameter/axis/span, and every multi-row placement remain
backend-authored. The same selectable renderer is used for every group size and view.

The accepted audit recognizes only the historical R8 tree with its approved historical
or secure lock and the new R3 tree with the secure lock. It explicitly rejects the
visually rejected interim tree and the historical R1/R2 predecessors as current active
identity, arbitrary third trees, source mutation/addition/
deletion/rename, package mutation, and unapproved lock identities. The audit remains
invariant to path separators, checkout location, line endings, and enumeration order.

Backend authority, zero-equation preview, explicit design execution, stale-result and
request-race protection, session-only state, viewport behavior, U.S./SI presentation,
external-demand boundaries, and Stage 2.1–2.4 numerical results remain regression
obligations.

## Acceptance state

Local engineering, security, freeze, automated UI, and real-browser evidence is
recorded by the Stage 2.4C-R3 completion report. Hosted R3 CI and the user's post-push
visual acceptance remain pending until directly verified for the exact pushed commit.
This record does not mark Stage 2.4C formally accepted and contains no licensed
standards text.
