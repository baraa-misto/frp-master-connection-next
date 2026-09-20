# Stage 3.5C shared-platform freeze-change record

Date: 2026-08-29
Accepted starting commit: `f72663a54700d84ac03a06e82a0e5fd39b4a0120`

Stage 3.5C adds a separate Column connection — Single/double web base angles
to concrete product. It does not replace or reinterpret Direct, Tee, Clip-Angle,
Multi-Member Tee, or either existing Stage 3.5 concrete-wall product.

## Narrow shared changes

- `api.routes` adds two stateless Stage 3.5C paths and their strict mapping boundary.
- `api.client` adds Stage 3.5C response guards and preview/design request functions.
- `ShearConnectionsWorkspace` adds the `Column connections` selector group and
  mounts the separate Stage 3.5C workspace; every pre-existing option and the
  default Direct selection remain unchanged.
- `domain.__init__` and `application.__init__` export the new Stage 3.5C-owned
  types and orchestration functions. Existing symbols retain their identities.
- All other production changes are confined to Stage 3.5C domain,
  orchestration, transport, fixture, workspace, and scene-adaptation modules.

## Engineering and freeze proof

- Frozen Direct geometry/result/fingerprint change: `NONE`.
- Frozen single-member Tee geometry/result/fingerprint change: `NONE`.
- Frozen Single and Paired Clip-Angle geometry/result/fingerprint change: `NONE`.
- Frozen Multi-Member Tee geometry/result/fingerprint change: `NONE`.
- Historical Stage 3.5A/R1/R2/B/R1 fingerprint change: `NONE`.
- Stage 2.3, Stage 3.2, Stage 3.3, and Stage 3.4 manifest/tag change: `NONE`.
- Package, lock, dependency, and workflow change: `NONE`.
- New demand equation count: `0`.
- New resistance equation count: `0`.
- Concrete-capacity and anchor-capacity equation count: `0`.

The Stage 3.5C component-demand trace is deliberately serial/conservative:
the column web is checked for 100% of `Pu` in web `LW`, the base-angle system
is independently assigned 100% of `Pu` in vertical-leg `CW`, and a proven
symmetric Double pair receives `Pu/2` per branch. These component-design
demands do not add into foundation equilibrium; the physical foundation
reaction is recorded exactly once as `Pu`.

The immutable tags remain unmoved and must be verified by their annotated
tag-object and peeled-commit identities. Complete configured-coverage
regression, exact controlled hashes, frozen fingerprints, tag-aware and
tagless successor-safe freeze audits, and depth-one no-alternates
committed-state verification remain mandatory. Any non-`NONE` transition
invalidates this record and stops Stage 3.5C.
