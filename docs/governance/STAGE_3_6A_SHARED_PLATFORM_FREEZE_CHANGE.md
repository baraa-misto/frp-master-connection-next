# Stage 3.6A Shared-Platform Freeze-Change Record

## Scope

Stage 3.6A is an additive successor after the immutable Stage 3.5 Concrete-Support
Shear Family freeze. It introduces a separate symmetric double web-splice product and
does not change a frozen request, result, equation, geometry, status, or fingerprint.

## Shared symbols changed

- `frp_master_connection.domain.__init__`: additive exports for the `3.6A-RC1`
  web-splice contract and default request.
- `frp_master_connection.api.routes.create_api_router`: two additive stateless
  `/api/v1/calculations/beam-web-splice/*` routes.
- `frontend/src/api/client.ts`: additive web-splice preview/design paths and clients.
- `ShearConnectionsWorkspace`: additive Beam-connection selector option and isolated
  `WebSpliceWorkspace` mount.

All other Stage 3.6A production modules are new and connection-specific. Package,
lock, dependency tree, workflow, and freeze-manifest files are unchanged.

## Frozen-family proof

Stage 2.3, Stage 3.2, Stage 3.3, Stage 3.4, and Stage 3.5 manifests, annotated tags,
historical contracts, representative requests/results, and fingerprints remain exact.
The selector default and every preexisting selector value/mount remain unchanged. The
new routes do not intercept an existing route. The shared clients add no state or
engineering authority to an existing workspace.

## Authorized transition

The transition count for every frozen family is zero. Stage 3.6A creates no tag and
does not alter or recreate an existing tag. Hosted CI and owner visual acceptance remain
pending direct evidence after the implementation commit is pushed.
