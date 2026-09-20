# Stage 3.4A shared-platform freeze-change record

Date: 2026-08-27
Accepted starting commit: `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`

Stage 3.4A adds the Multi-Member Tee as a separate connection type. It does not
replace, route through, or change the frozen single-member Tee or Clip-Angle
contracts. The superseded Gusset-Plate draft is unapproved and is neither copied nor
registered.

## Narrow shared changes

- `application.tee_orchestration`: exposes the existing resolved Tee assembly,
  bolt expansion, profile-solid, and visualization adapters and accepts node-only
  connected-member placement parameters. Every parameter defaults to the historical
  single-member behavior.
- `api.routes`: adds only the two strict Multi-Member Tee endpoints.
- `frontend.api.client`: adds only the typed Multi-Member Tee preview/design calls.
- `SupportingMemberEditor`: adds an optional target filter whose omitted default is
  the complete historical target registry.
- `ShearConnectionsWorkspace`: adds one separate selector value while retaining the
  existing default and every existing workspace branch.
- `test_scope_boundaries`: records active frontend source-tree successor
  `1783fe6165d89328f8e92bb6a9828906a5f41521`; the historical Stage 3.3C3-R1 tree
  remains recorded.

## Freeze proof

- Frozen single-member Tee geometry change: `NONE`.
- Frozen single-member Tee result change: `NONE`.
- Frozen single-member Tee fingerprint change: `NONE`.
- Frozen Clip-Angle behavior/result/fingerprint change: `NONE`.
- Direct behavior/result/fingerprint change: `NONE`.
- Stage 2.3, Stage 3.2, and Stage 3.3 freeze-manifest change: `NONE`.
- Package, lock, dependency, and workflow change: `NONE`.
- New demand or resistance equation count: `0`.

The immutable tags remain unmoved:

- `stage-2.3-interface-geometry-freeze` →
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- `stage-3.2-tee-connection-freeze` →
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- `stage-3.3-clip-angle-family-freeze` →
  governance commit `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`; its manifest separately records
  accepted product baseline `a15f6f9bc820bc7e2d466db8519bcb9582b96e55`.

Full configured-coverage regression, exact controlled hashes, immutable-tag audits,
and a depth-one no-alternates committed-state clone are mandatory evidence. Any
non-`NONE` frozen transition invalidates this record and stops Stage 3.4A.
