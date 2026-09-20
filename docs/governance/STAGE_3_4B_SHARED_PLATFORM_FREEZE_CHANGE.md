# Stage 3.4B shared-platform freeze-change record

Date: 2026-08-28
Accepted starting commit: `51fd10ffe269fd4b07000eb3dd234411315d7429`

Stage 3.4B expands only the separate Multi-Member Tee connection type. It does not
replace or reroute the frozen single-member Tee or Clip-Angle families. The accepted
Stage 3.4A `3.4A-RC1` transport, default geometry, support wrench, and fingerprints
remain available without translation.

## Narrow shared change

- `frontend.api.client.isMultiMemberTeePreview` and
  `frontend.api.client.isMultiMemberTeeDesign` accept the additive controlled
  `3.4B-RC1` Multi-Member Tee response identity in addition to `3.4A-RC1`; all other
  response guards and every frozen-family API call remain unchanged.
- The remaining production changes are confined to the Stage 3.4A/3.4B
  Multi-Member Tee domain, mapping, orchestration, contracts, fixtures, workspace,
  and scene adapter.
- The active frontend source tree is
  `21676d8011c07d804fb334393499cfd42145849d`; historical Stage 3.4A-R2 tree
  `6f75da7944281c4e4b78af40934738d9fa5404f2` remains recorded as a predecessor.

## Freeze proof

- Frozen single-member Tee geometry/result/fingerprint change: `NONE`.
- Frozen Single and Paired Clip-Angle geometry/result/fingerprint change: `NONE`.
- Direct/reference behavior/result/fingerprint change: `NONE`.
- Stage 3.4A default geometry/result/support-wrench/fingerprint change: `NONE`.
- Stage 2.3, Stage 3.2, and Stage 3.3 freeze-manifest change: `NONE`.
- Package, lock, dependency, and workflow change: `NONE`.
- New demand equation count: `0`.
- New resistance equation count: `0`.

The immutable tags remain unmoved:

- `stage-2.3-interface-geometry-freeze` peels to
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- `stage-3.2-tee-connection-freeze` peels to
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- `stage-3.3-clip-angle-family-freeze` peels to
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`.

Full configured-coverage regression, exact controlled hashes, immutable-tag audits,
and a depth-one no-alternates committed-state clone are mandatory evidence. Any
non-`NONE` frozen transition invalidates this record and stops Stage 3.4B.
