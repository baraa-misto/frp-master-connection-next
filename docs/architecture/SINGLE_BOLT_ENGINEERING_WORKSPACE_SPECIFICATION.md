# Single-Bolt Engineering Workspace Specification

Status: Stage 2.3R2 implemented contract; locally validated; provisional; not frozen.

## Scope and authority

Stage 2.3 provides the first interactive engineering workspace for the verified
single-bolt, single-row calculation slice. It does not create a whole-connection
design method. The backend remains authoritative for geometry, directions,
calculation plans, numerical results, engineering statuses, governing identities,
qualification flags, versions, and fingerprints. The frontend contains no
resistance, capacity, utilization, demand-distribution, or code-applicability
formula.

The implemented product selection remains exactly `Shear Connections` and `Moment
Connections`. Shear opens this workspace. Moment remains visibly not implemented.
The implemented classification is brace-to-column-flange, one brace, direct bolting,
one selected logical bolt, and one row.

## Session workflow

The workspace is session-only. It has no local storage, session storage, project
record, database write, report, account, or entitlement behavior. A user can load
the verified J1 U.S. or SI input profile, enter a case label, inspect or edit the
supported geometry/bolt/load/factor inputs, select a demand mode, evaluate through
the same-origin API, and inspect the returned result and canonical visualization.
Changing an engineering or case input clears the current result and marks it stale
until reevaluation.

J1 loaders contain input fixtures only; production source contains no expected J1
resistance, utilization, aggregate status, or governing result. J1 remains subject
to whole-connection Section 2.3.2 qualification and is never presented as an
ordinary whole-joint PASS.

## Units and editable input boundary

The case unit system is either `US_CUSTOMARY` (in, kip, ksi) or `SI` (mm, kN, MPa).
The UI does not live-convert user-entered decimal strings. Changing profiles after
an edit requires confirmation and resets the complete case to the corresponding
verified J1 profile. Every request physical magnitude remains a decimal string with
an explicit unit.

Supported inputs are the J1 angle dimensions, W-section dimensions, selected bolt
diameter, authoritative hole display, washer geometry, thread states, lap
configuration, one explicit factored member-end force/moment sextuple, explicit
resolved one-bolt force/tension/prying demand, layer loading sense, time-effect
category, and `CM`, `CT`, and `CCH`. The locked ICE development material is
read-only and engineering-review-required. The locked 316/316L F593 fastener source
remains read-only, and its `Fnt` source remains pending.

## Demand modes

`Explicit resolved one-bolt demand — development / advanced` sends an independently
resolved demand bound to the selected interface, bolt group, bolt, and penetrated
layer stack. It is a development input and does not imply an implemented distribution
method. `Member-end action` deliberately removes that demand. The server then returns
the existing fail-closed
`BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED` engineering outcome through HTTP
200. The UI does not divide, shift, equilibrate, or otherwise generate bolt demand.

## Canonical visualization snapshot

API transport `0.3.0-draft` includes the required deterministic renderer-neutral
`visualization` object to the existing response. The route calls Stage 2.2A exactly
once and builds this snapshot from the same canonical request geometry and returned
orchestration identity. It neither changes nor fingerprints camera, color, pixel,
selection, or WebGL state.

The snapshot contains:

- exact physical component/element identities and renderer-neutral box, annular-
  cylinder, deferred, bounded-support, planar-rectangle, and planar-annulus data;
- global, joint, member, connector, interface-local, and bolt-group frames with
  numerical orthonormal/right-handed inspection;
- exact planar FRP `LW`, `CW`, and `TT` material axes, with cylindrical or non-FRP
  directions explicitly not applicable rather than invented;
- interface connection zones, the authoritative bolt center/axis, ordered round-hole
  paths, penetrated participants/elements, and stack ends;
- joint/interface/bolt-group/bolt/action reference points plus physical member START,
  END, and connected-end provenance; and
- separate positive sign-convention and applied signed `FX`, `FY`, `FZ`, `MX`, `MY`,
  and `MZ` directions, including negative-axis reversal, zero state, units, member
  end, action reference, and axial tension/compression sense.

Geometry display is never a source of resistance or demand. Display tessellation,
camera manipulation, visibility, and presentation scaling cannot modify the snapshot
or the calculation response.

## Three.js presentation and views

The visualization adapter uses exact-pinned `three` and `@react-three/fiber` with
Three.js `OrbitControls`. React Three Fiber is presentation-only; the pure scene
model performs deterministic snapshot parsing, view selection, bounds, camera fit,
and toggle mapping outside WebGL.

The four views are:

- `3D`: fitted perspective inspection;
- `Front`: orthographic view along global negative Y with global positive Z up;
- `Top`: orthographic view along global positive Z with global positive Y up; and
- `Side`: orthographic view along global positive X with global positive Z up.

Reset camera refits the current canonical bounds. Controls expose global axes,
selected/all/off member axes, connector axes, interface-local axes, bolt-group axes,
material axes, START/END and other reference points, bolt/hole geometry, positive
arrows, applied arrows, and zero-action visibility. Numerical frame, material-axis,
and reference/action inspectors remain available outside the canvas. For a selected
penetrated layer, the material inspector presents the server-returned bearing and
net-tension directions and force/material angle alongside every exact LW/CW/TT axis;
it does not infer a property selection or recompute the angle.

## Results and status presentation

The summary displays the server aggregate, governing/co-governing IDs,
qualification/review flags, calculation fingerprint, engine/rule/contract versions,
and unit system. The detailed table preserves plan order and separately displays
availability, numerical comparison, demand, nominal/design resistance, utilization,
direction/property selection, qualification, source, and the returned calculation
trace. Known numerical failure remains failure; HTTP status does not reinterpret it.
Unsupported, source-pending, not-applicable, review, and qualification conditions
remain explicit.

## Accessibility and responsive behavior

All inputs, selects, buttons, view controls, toggles, and inspectors have semantic
labels and keyboard focus treatment. The canvas has an accessible description of
its authoritative content and view. Important engineering values and status are not
canvas-only. Layouts collapse for narrower screens, tables scroll without clipping
the document, and reduced-motion preference suppresses nonessential transitions.

## Validation boundary

Backend tests cover deterministic snapshots, exact standard-shape/support/zone
geometry, frames, material axes, interface/bolt data, references, action signs,
unsupported distribution, US/SI equivalence, API transport, and immutable existing
results. Frontend tests cover the pure scene model, client boundary, J1 loaders,
workflow, inputs, modes, stale/error/status behavior, views, toggles, inspectors,
scope audits, and absence of frontend formulas/persistence. WebGL itself is
build/type/lint verified while tests mock the Canvas adapter.

## Explicit limitations and future controlled work

Stage 2.3 does not implement approved bolt-demand distribution, multiple bolts or
rows, block shear, generated prying, custom manufacturer material editing/library,
project persistence, authentication/account/entitlement, reports, or the Moment
workflow. It does not resolve J1 whole-connection qualification, ICE production
qualification, or locked F593 `Fnt` sourcing. Those require later controlling orders;
none begins in this stage.

## Stage 2.3R visual and workflow refinement

Stage 2.3R keeps the Stage 2.1B engine, RC2 golden values, Stage 2.2A orchestration,
and Stage 2.2B engineering API outcomes unchanged. The controlled J1 visual fixture
applies one proper rigid transform to the complete assembly: the W-column local
positive x-axis is global positive Z, W START is below W END, and the brace is
diagonal in a vertical plane. The transform preserves the verified sign-independent
45-degree material relationship, penetrated-layer/path meanings, explicit demand,
Section 2.3.2 qualification, governing W-flange net-section-tension check, and every
unrounded Q12 result. The historical RC2 J1 fixture remains unchanged.

The workspace is connection-first: a compact independently scrolling property
sidebar sits beside a persistent large viewer and a collapsible results drawer.
Sidebar groups are General / Case, Connection, Members, Geometry, Bolt / Interface,
Materials, Fastener, Loads, Demand, Factors, Results / Status, and Advanced /
Diagnostics. The primary viewer toolbar provides 3D, Front, Top, Side, Fit
Connection, Reset view, solid/X-ray display, and grouped overlays.

Solid role colors distinguish the muted blue-gray W column, dark-blue brace, and
orange/gold selected bolt. The clean default shows physical geometry, bolts/holes,
global axes, the selected member-local frame, the bolt axis, and nonzero applied
actions. Deferred geometry, interface zones, connector/interface/bolt-group frames,
material axes, reference points, positive sign arrows, and zero actions begin off and
remain opt-in diagnostics. Numeric inspectors preserve stable internal IDs.

Normal force/resistance display uses three decimal places. Utilization uses three
decimals plus percent. Exact returned decimal strings, factors, intermediate traces,
sources, and IDs remain available in expanded details; presentation rounding never
feeds engineering status, governing selection, a request, or a fingerprint. Editable
decimal fields use concise presentation formatting while unfocused and the unchanged
exact request string while focused; the display transition never mutates the request
value. Member-end mode states that distribution is unavailable and fails closed.
Explicit one-bolt demand is an advanced independently resolved input and is never
represented as being derived by the workspace.

## Stage 2.3R2 controlled template geometry

For the current verified brace-to-column-flange slice, the browser sends only a
`BRACE_TO_COLUMN_FLANGE` template selection and its supported parameters. The backend
constructs all member placements, section datums, target surfaces, connection zones,
bolt paths, frames, references, actions, and resolved-demand bindings. The frontend
does not use trigonometry or cached member placements as engineering geometry
authority.

The brace-to-column angle is the acute, sign-independent angle between the brace
longitudinal axis and the W-column longitudinal axis. It is finite, strictly greater
than 0 degrees, at most 90 degrees, and defaults to 45 degrees. The brace remains in
the current verified vertical plane and quadrant; its out-of-plane plan angle is
fixed at 0 degrees. W local positive x remains global positive Z. The backend preserves
proper right-handed frames at the 45-degree default, 90 degrees, and near-longitudinal
angles at or below 5 degrees.

`Column segment below connection` and `Column segment above connection` are positive
local presentation extents from the fixed connection station, not physical member
end-design assumptions. The U.S. defaults are 8.7426406871192848 in below and 1.5 in
above; the SI defaults are the exact physical equivalents 222.06307345282983392 mm
and 38.1 mm. Their 10.2426406871192848 in total is exactly four times the former
2.5606601717798212 in segment. The intentionally asymmetric split preserves the
existing loaded-end geometry-to-code distance, connection/bolt/path station, Q12
engineering results, qualification, governing W-flange net-section-tension result,
and existing comparison precision. Brace segment length is independently positive,
editable, and defaults to 4 in (101.6 mm).

Changing any template control marks results stale and clears current result authority
until reevaluation. The returned material-axis relationship is server-resolved. Normal
labels say `W Column Flange` while `TOP_FLANGE` and all other stable IDs remain visible
in diagnostics and traces. The material inspector shows ICE `Ft,L`, `Ft,T`, `Fbr,L`,
`Fbr,T`, and `Fsh,LT`; it does not fabricate `Fc,T`. Demand copy distinguishes
independently resolved one-bolt demand from unsupported member-end distribution and
retains `Section 2.3.2 Qualification Required.` punctuation.

The visualization uses exact-known geometry only. The bolt shank is the known nominal
diameter over the resolved layer-stack span. A washer is drawn only when its existing
under-head or under-nut flag, outside diameter, thickness, and exact path entry/exit
placement are known. Head, nut, threads, protrusion, and unprovided washer placement
remain absent rather than estimated. Camera fit remains centered on the connection
and includes the complete longer canonical extents.

## Stage 2.3R3 connection orientation workflow

The current brace-to-column-flange template exposes three engineering geometry inputs:
`EXTERIOR` versus `WEB_SIDE`, connected angle `LEG_1` versus `LEG_2`, and a discrete
positive/negative outstanding-leg side about interface-local z. The backend maps those
semantics to canonical section elements, exact surface patches, and a proper
determinant-positive member frame. The browser never derives roll, contact side, or
interference. The default remains exterior, Leg 1, positive interface side, 45 degrees,
and plan angle zero; its verified J1 result set is unchanged.

The viewer highlights the exact selected W Column Flange contact face. Model picking
and sidebar selection share canonical member, bolt, and surface IDs but remain
presentation-only. A screen-corner global X/Y/Z triad is on by default, rotates with
the camera without translating with model pan, and is distinct from optional full
model-space global axes. Only the selected member's labeled local x/y/z axes are on by
default; material LW/CW/TT and positive-convention overlays remain optional.

## Stage 2.3R4 viewport-navigation contract

Viewport navigation is presentation-only. One `OrbitControls` instance is created for
each mounted camera/canvas lifecycle, and the same lifecycle removes its single change
listener and disposes the controls. Left-drag rotates, right-drag pans, and the wheel
zooms. Navigation does not edit geometry, submit an API request, invalidate an existing
result, or change a fingerprint. Physical geometry remains editable only through the
controlled engineering inputs.

The corner global triad remains fixed to the viewer corner. A controls change projects
the camera quaternion and writes the six line endpoints and three label positions
directly to its SVG elements, followed by renderer invalidation. It does not write
React workspace state on camera changes, and no frame loop or animation frame is used
for the triad.

Canvas picking and controls share the pointer stream. Pointer-down only records the
candidate canonical target and screen position; it does not stop propagation. A
matching primary-button pointer-up selects only when movement is at most four CSS
pixels, then applies the established contact-face, bolt, member hit priority. A drag
therefore navigates even when it starts on selectable geometry, while a click still
selects W column, angle brace, bolt, or selected contact surface. Static SVG and HTML
legends are pointer-transparent. Dragging a member never moves or edits it.

## Stage 2.3R5 preview and design-check workflow

The workspace automatically requests a backend-authoritative canonical preview after
preview-affecting edits. Preview supplies model geometry, resolved action, material
relationship, selected contact and bolt path, interference findings, model status,
and design readiness only. It does not evaluate or expose resistance, capacity,
utilization, governing checks, design PASS/FAIL, or a calculation fingerprint.

`Run Design Check` replaces `Evaluate Connection` and remains the only operation that
calls the design endpoint. Model/Geometry Status is independent of Design Results.
Any preview-affecting change marks a prior design result stale without hiding it;
invalid or incomplete geometry additionally blocks the design action. A design
response is accepted only for the still-current preview revision.

Preview-affecting inputs are geometry-template, orientation, action, material-
direction, demand-mode, and explicit resolved-demand values. Design-only inputs are
resistance factors, lap configuration, and thread-status choices. The case label and
viewer controls are presentation-only. Numeric preview edits use a provisional 200 ms
debounce; discrete choices request immediately. Superseded fetches are aborted and a
monotonic revision/sequence guard enforces latest-response-wins. Orbit, pan, zoom,
Fit/Reset/view changes, overlays, and selection neither request preview nor stale a
design result.

## Stage 2.3R6 input authority and action editing

The controlled engineering input `Bolt-to-brace-end distance e1` places the
canonical connected brace end relative to Bolt 1. It defaults to `2.000 in` or the
separately authored exact SI value `50.8 mm`, requests preview, and makes a prior
design result stale. The equation layer never consumes the typed value directly;
the established geometry-to-code mapper re-derives `e1` from canonical boundaries.

`Brace view length`, `Column view extent below connection`, and `Column view extent
above connection` form the separate preview-only class. They change only
backend-authored display context, request preview, and do not increment the design
revision. They are excluded from design DTOs, calculation fingerprints, code
distances, capacities, and result staleness. Presentation controls remain a fourth
class that requests neither preview nor design.

Brace geometry uses the explicit directed-angle meaning `0 < theta < 180` in the
verified vertical plane. Geometry angle and the server-returned sign-independent
acute material angle are labeled separately. Applied force and moment labels are on
by default, show source/component/sign/unit, and edit the same member-action strings
used by the sidebar. Enter or valid blur commits, Escape cancels, invalid drafts
request nothing, and no edit automatically runs design.

## Stage 2.3R7 applied-action label workflow

The normal viewer no longer uses a detached upper-left action-card list as the
primary action display. Every visible applied force and moment component is identified
at a camera-projected point beside its corresponding straight arrow or curved arc.
The label retains Member source identity for the current member-end action snapshot;
any future explicit Bolt 1 action visualization must say `Bolt 1` and cannot imply a
distributed demand. U.S. labels use `kip`/`kip-in`, SI labels use `kN`/`kN-mm`, and
the display formatter always includes the sign without altering the exact input.

The applied label is a keyboard-focusable button using the same action strings and
updater as the sidebar. Enter/Space uses native button activation; valid Enter or blur
commits, Escape cancels, and invalid text commits nothing and schedules no preview.
A valid edit immediately stales a prior design and schedules the existing canonical
preview, whose returned action direction/value remains authoritative. It never calls
the design endpoint. Applied/value/zero visibility is coupled to the matching
primitive; positive-convention labels are nonnumeric and noneditable. Camera and
selection changes reposition labels only and request neither preview nor design.
