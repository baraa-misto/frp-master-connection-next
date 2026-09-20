# Stage 2.6B group-mode frontend freeze change

## Authorized change

Stage 2.6B extends the accepted unified Shear workspace only to consume and present the
backend-authoritative automatic eccentric group-mode result. The frontend displays
actual line resultants, supported shear-out resistance/utilization, structured line
states, and the separate eccentric first-row limitation. It does not aggregate bolt
vectors, select engineering compatibility, run resistance, change preview behavior, or
alter the explicit-demand workflow.

## Controlled identities

| Identity | Git object / digest |
|---|---|
| Immutable Stage 2.3 tag target | `5bc545ab8251f9bd49dedc776962937ed5e822a2` |
| Historical Stage 2.3/R8 `frontend/src` tree | `df664801ea31a5a33e582e886dc787bf4f9be8aa` |
| Stage 2.5C-R2 historical predecessor tree | `cd25332af05c101aa008934a7b900d8c220938f3` |
| Active Stage 2.6B `frontend/src` tree | `b73469788561bebf61262f2211b6e39c3e3a699c` |
| Unchanged `frontend/package.json` blob | `b753abd55004168eee5844879f0596d435fe4b5a` |
| Unchanged secure `frontend/package-lock.json` blob | `ae1831268db42005517343bf555f054a673ae520` |
| Unchanged secure lock SHA-256 | `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254` |

The active tree was derived from the complete reviewed staged `frontend/src` index.
All previously accepted successor trees remain historical provenance, not alternate
active identities. The audit accepts the immutable original identity under its
approved lock combinations or the Stage 2.6B active tree under the secure lock. It
rejects the Stage 2.5C-R2 predecessor and arbitrary third trees as active states.
Before commit, the audit snapshots the complete working `frontend/src` path through a
temporary isolated Git index, so the exact successor tree is checked while the real
index remains empty for integrated QA. In committed and isolated checkouts the same
procedure resolves the identical `HEAD` content. This is Git object verification, not
a raw checkout-byte digest, and the real repository index is proven unchanged.

## Preserved controls

The Git-object audit remains independent of checkout location, path separators, line
endings, and filesystem enumeration order. Exact tree identity detects additions,
deletions, renames, and content changes. The package and secure lock identities are
unchanged; `npm ci`, dependency-tree validation, and full/runtime zero-vulnerability
audits remain required.

The annotated tag `stage-2.3-interface-geometry-freeze` is not moved, recreated, or
replaced. No new tag exists. Existing 3D/Front/Top/Side 1/Side 2 views, navigation,
selection, solid hardware, loaded-boundary placement, per-bolt overlay, stale-state,
session-only, preview/design separation, and all engineering authority hashes remain
regression obligations.

## Acceptance status

Full local and integrated gates pass 1,501 backend and 185 frontend tests at configured
100 percent coverage, both zero-vulnerability audits, and the exact freeze identity.
Local browser review passed small supported-line PASS/fail-closed first row, large
supported-line and whole-result FAIL, explicit separation, SI presentation, five views,
Fit/Reset non-staling, solid fasteners, and zero console errors. Automated tests cover
the zero-line and zero-residual presentation states; their specific live browser
configurations and direct user visual acceptance remain pending. Object-isolated
committed verification, push, and hosted Ubuntu/Windows CI are recorded separately and
must not be inferred from this source-identity approval.
