# Stage 3.5A shared-platform freeze-change record

Date: 2026-08-28
Accepted starting commit: `2303ec713d6d038b935e076b909c3b639ced0e09`

Stage 3.5A adds a separate Beam-to-Concrete Wall — Paired FRP Clip Angles
connection type. It does not replace or reinterpret Direct, single-member Tee,
Single or Paired Clip-Angle, or Multi-Member Tee requests.

## Narrow shared changes

- `api.routes` and `api.client` gain two additive, stateless Stage 3.5A paths.
- `ShearConnectionsWorkspace` gains one separately routed selector option; the
  existing default remains Direct.
- `sceneModel`, `fastenerPresentation`, and `EngineeringScene` gain an opt-in
  external-anchor presentation mode. Existing through-bolt rendering remains the
  default and retains its head/nut/washer behavior.
- All remaining production changes are confined to Stage 3.5A domain,
  orchestration, transport, fixtures, workspace, and scene adaptation.
- The active Stage 3.5A frontend source tree is
  `8ce23b8990cb1bc5f682bde92d686c2a1cd4c46e`; the historical frozen Stage 3.4
  frontend tree remains `21676d8011c07d804fb334393499cfd42145849d`.
- The active Stage 3.5A backend source tree is
  `ec6fd1d6828de423ddd78521102795d55f1ba2b6`; the historical frozen Stage 3.4
  backend tree remains `91c91446a9c31440693b37c88195be02e60c98b1`.

## Freeze proof

- Frozen Direct geometry/result/fingerprint change: `NONE`.
- Frozen single-member Tee geometry/result/fingerprint change: `NONE`.
- Frozen Single and Paired Clip-Angle geometry/result/fingerprint change: `NONE`.
- Frozen Multi-Member Tee geometry/result/fingerprint change: `NONE`.
- Stage 2.3, Stage 3.2, Stage 3.3, and Stage 3.4 manifest/tag change: `NONE`.
- Package, lock, dependency, and workflow change: `NONE`.
- New demand equation count: `0`.
- New resistance equation count: `0`.
- Concrete-capacity and anchor-capacity equation count: `0`.

The immutable tags remain unmoved and are verified by their annotated tag-object
and peeled-commit identities. Complete configured-coverage regression, exact
controlled hashes, frozen fingerprints, tag-aware and tagless successor-safe
freeze audits, and depth-one no-alternates committed-state verification are
mandatory evidence. Any non-`NONE` frozen transition invalidates this record and
stops Stage 3.5A.
