# Unified single-bolt and multi-row engineering workspace specification

## Workflow ownership

Shear Connections owns one connection engineering workspace. The original Stage 2.3
single-bolt sidebar, canonical Three.js connection scene, camera controls, overlays,
inspectors, load editing, and results region remain the only primary workflow. Row count
and bolts-per-row are in-place connection properties; there is no single/multi-row mode
selector and no second engineering workspace.

Exactly `1 × 1` routes preview and explicit **Run Design Check** through the accepted
single-bolt service. Supported arrangements with two or more rows route through the
accepted multi-row service without replacing the surrounding workspace. A one-row group
with multiple bolts remains visible but fails closed because no accepted calculation
method currently owns that arrangement.

## State and interaction model

Case, units, members, orientation, material, fastener, actions, demand, factors, camera,
panels, and selection have one source of frontend state. Arrangement changes preserve
compatible presentation state, cancel obsolete requests, mark an accepted design result
stale, and enter the existing debounced/latest-response-wins preview flow. Preview updates
geometry/model status and the backend snapshot and invokes no resistance equation.
**Run Design Check** is the only design action and selects only the orchestration path
that owns the current arrangement.

Camera, view, overlay, panel, and selection changes are presentation-only. They do not
rerun preview, stale a design result, or change an engineering fingerprint. U.S. and SI
presentation converts supported inputs while authoritative physical quantities,
provenance, and fingerprints remain server-owned. The workspace is session-only.

## Backend-authoritative physical visualization

For multi-row arrangements, the application extends the preview visualization contract
with the canonical Stage 2.3 physical connection snapshot, every physical bolt, hole,
washer, penetrated-layer identity, row identity, bolt-line identity, and the externally
resolved connection-demand resultant. Every bolt is placed on the actual rendered
brace/angle/W-column interface by backend-resolved frames and coordinates.

The frontend composes that response into the existing React Three Fiber scene. It does
not calculate bolt coordinates, assign rows, reconstruct connected surfaces, infer
material direction, distribute demand, or execute resistance logic. Front, Top, Side,
Fit, Reset, display modes, axes, action overlays, and model picking therefore work the
same way for one bolt and a supported multi-row group. Selecting any physical bolt only
changes inspection/presentation state.

The former interface-plane SVG may remain as a collapsed **Bolt layout — optional 2D
diagnostic**. It is secondary and never replaces the canonical 3D connection.

## Inputs, results, and limits

Progressive disclosure exposes pitch, gauge, loaded and unloaded distances, side
distances, row-demand method, explicit provenance, lap/time-effect/factor selections,
first-row method, and optional per-bolt axis tension only when relevant. The demand copy
states that multi-row connection demand is externally resolved and is separate from
member-end actions.

The shared result region reports geometry/model state separately from design status and
shows aggregate disposition, applicability, qualification, governing identities, and
all deterministic check traces. More-than-three-row arrangements cannot be presented as
ordinary prescriptive PASS. No member-end transformation, general bolt-group demand
distribution, friction credit, generated prying, persistence, report, authentication,
billing, or new engineering method is implied.

Formal Stage 2.4C-R1 acceptance requires hosted CI evidence for the exact pushed commit
and the user's post-push visual review; both remain pending until directly supplied.

## Stage 2.6B automatic result presentation

After an automatic **Run Design Check**, the shared result region consumes the backend
Stage 2.6B payload and shows an **Eccentric group-mode checks** section. Each scenario
and physical bolt line presents contributing bolt identities, actual signed line
resultant components, authorized scalar demand when present, parallel/transverse
components, compatibility status, unchanged Stage 2.4B resistance/utilization when
executed, method/source trace, and warnings. The eccentric first-row net-tension status
is shown in its own section and is never implied to be solved.

Zero-line demand is explicitly not required. Nonparallel and reversed resultants remain
distinct unsupported states. A known supported line failure stays visible and governs
the overall summary even beside unsupported siblings; supported line PASS plus required
unsupported first-row behavior cannot appear as ordinary PASS. The exact-zero residual
legacy presentation and explicit-demand workflow remain unchanged.

The frontend does not sum bolt vectors, project forces, choose line membership, execute
resistance, or derive engineering status. Existing per-bolt overlays, five views, solid
fasteners, loaded-boundary placement, stale-state rules, and session-only behavior are
preserved. Display units and view changes remain presentation-only.
