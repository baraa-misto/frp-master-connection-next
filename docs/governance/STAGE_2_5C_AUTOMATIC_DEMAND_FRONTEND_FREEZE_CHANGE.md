# Stage 2.5C automatic-demand frontend freeze change

## Authorization and scope

Stage 2.5C extends the accepted unified Shear connection workspace with an explicit
demand-source selector, backend-authored automatic per-bolt demand visualization, and
the accepted Stage 2.5A-to-Stage 2.5B design path. Explicit resolved connection demand
remains the default and remains available. This controlled successor changes no
dependency, lockfile, workflow, original freeze tag, equation, engineering golden, or
calculation-engine identity.

Automatic preview resolves the canonical member-end force and reference point through
the application service and executes Stage 2.5A demand analysis only. It executes zero
resistance. **Run Design Check** executes Stage 2.5A and then Stage 2.5B; compatible
resistance is reached only through Stage 2.5B. The frontend maps backend-returned
vectors and performs no force transformation or bolt-demand calculation.

Member-end moments remain untransferred, interface-normal force does not generate
bolt-axis tension or prying, eccentric first-row net tension and inter-row shear-out
remain unsupported, and block shear remains conditional on canonical compatibility.
The successor therefore does not claim general six-component action distribution.

## Controlled identities

| Control | Identity |
|---|---|
| Original freeze tag | `stage-2.3-interface-geometry-freeze` |
| Immutable tag target | `5bc545ab8251f9bd49dedc776962937ed5e822a2` |
| Historical Stage 2.3/R8 `frontend/src` tree | `df664801ea31a5a33e582e886dc787bf4f9be8aa` |
| Hosted-CI-green but visually rejected interim tree | `cf71cf158afd3525aba0849e207746b6a6842f73` |
| Historical Stage 2.4C-R1 unified-workspace tree | `8f8b5c65559f162363d3ea2bb58f2e21cf18ba9d` |
| Historical Stage 2.4C-R2 fastener/view tree | `f95396ff7ce5604f08f40b04b7b5e216271672c6` |
| Historical Stage 2.4C-R3 solid-hardware tree | `deb93d01646580ae62c9f90a507446d84019bd87` |
| Active Stage 2.5C automatic-demand tree | `035af7c9c44c49914c63c68edf6ec4eea5521bcf` |
| Unchanged `frontend/package.json` blob | `b753abd55004168eee5844879f0596d435fe4b5a` |
| Historical R8 lock blob | `f2a594dae8c871d5c1c78e69f1023d6e77adf6e6` |
| Accepted secure lock blob | `ae1831268db42005517343bf555f054a673ae520` |
| Accepted secure lock SHA-256 | `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254` |

The active identity was derived from the complete reviewed `frontend/src` working
state through an isolated Git index. The repository audit reads the staged index when
frontend source is staged and `HEAD:frontend/src` after commit. It accepts only the
historical Stage 2.3 source with an approved lock or the active Stage 2.5C source with
the secure lock. All interim/predecessor trees are preserved as provenance but rejected
as current identities. Change, addition, deletion, rename, arbitrary-tree, package,
and lock mutations remain fail-closed, with path-separator, line-ending,
enumeration-order, checkout-location, and depth-one invariance retained.

## Acceptance state

Automated backend/frontend coverage and freeze regression are recorded in the Stage
2.5C QA authorities. Local real-browser review passed the explicit default, U.S./SI
automatic preview, optional backend-vector overlay, explicit design, distinct supported
failure, fail-closed limitations, stale state, five views, Fit, and Reset. Isolated
committed-state verification, hosted CI, and user post-push visual acceptance remain
separately reported evidence.
The original tag is not moved, deleted, recreated, or replaced, and no new tag is
created.
