# FRP Master Connection — Stage 3.2-R7 Angle Bolt-Path Geometry — Authority Ledger RC1

## New authority

R7 authorizes only the correction of Angle-profile through-thickness geometry so a bolt through a selected exterior leg broad face can resolve the exact finite opposing boundary face of that same leg.

The opposing face is derived from the existing Angle solid union and excludes the internal heel-overlap region.

## Inherited authority

R7 inherits without modification:

- Stage 3.2-R2 Angle profile dimensions and selectable surfaces
- Stage 3.2 Tee two-interface topology
- Stage 2.5A demand mechanics
- Stage 2.5B resistance handoff
- Stage 2.6A group-mode compatibility
- Stage 3.1 material/fastener authority
- R6 current/invalid/last-valid preview behavior

## Not authorized

R7 does not authorize:

- treating an Angle as a flat plate
- tolerance/epsilon ray intersections
- internal heel planes as exposed opposing faces
- free-edge exits as broad faces
- new Angle resistance
- leg bending/prying/local-buckling equations
- new material directions
- new profile families
- UI-generated engineering geometry
- changing current layout semantics

## Fail-closed rule

A selected Angle bolt path remains invalid if it does not traverse from the selected finite exterior leg face to exactly one finite exposed opposing broad face at the exact leg thickness.

## Fingerprint rule

The corrected opposing-face result should be derived from already fingerprinted Angle geometry.

No accepted fingerprint transition is authorized by this ledger. If one is unavoidable, stop for explicit owner authority.

**END OF AUTHORITY LEDGER RC1**
