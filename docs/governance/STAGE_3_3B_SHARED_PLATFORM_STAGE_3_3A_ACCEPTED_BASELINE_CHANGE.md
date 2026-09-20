# Stage 3.3B shared-platform Stage 3.3A accepted-baseline change

## Accepted baseline

The accepted Stage 3.3A-R4 baseline is commit
`f4ae7d308644024ed31bcf0114b550426f4e45ef`. Its active `frontend/src` tree is
`c6056618e25c6ff0c6205cdcf6503f3d85a633b9`.

## Shared symbols before and after

- `ClipAngleBoltTrace.layer_ids` changes from an exact two-item tuple to an immutable
  ordered tuple/array so one physical common through-bolt can publish the controlled
  positive-angle/member/negative-angle three-layer stack. Existing single-angle traces
  still contain exactly two layers in the same order.
- `evaluate_multirow_connection_with_resolved_demand` gains an optional empty-by-default
  layer-demand-allocation argument. Its accepted single-angle calls omit that argument
  and retain the exact Stage 2.5B handoff. Stage 3.3B supplies controlled per-layer
  fractions while preserving the parent common-group demand object.
- Shared domain/application/API exports, API routing/client registration, the connection
  selector, and visualization bindings gain additive paired-angle symbols. Direct, Tee,
  and Single Angle defaults and accepted request/response paths remain unchanged.

## Stage 3.3B reason

One symmetric pair has a single physical common through-bolt group with three ordered
layers and two mirrored support groups. Reusing the accepted geometry, trim, demand,
resistance-handoff, viewport, and live-preview seams avoids duplicate calculation and
workspace authority. No resistance equation or accepted resistance meaning changes.

## Stage 3.3A regression evidence

The complete Stage 3.3A G1-G10 numerical and fingerprint suite, five-profile placement
and trim matrix, preview/design classification, API, frontend state, visualization, and
single-angle exact-two-layer assertions remain mandatory in component, integrated, and
object-isolated QA. The exact final test counts are recorded in the Stage 3.3B completion
report after committed verification.

Stage 3.3A geometry/result/fingerprint change: `NONE`.

The Stage 3.3B active `frontend/src` successor tree is
`d51bd05103a2530ea3bea9bdb10e020cc18deb57`; the Stage 3.3A-R4 tree remains historical
provenance. Package, secure lock, workflows, and both immutable freeze tags are unchanged.
