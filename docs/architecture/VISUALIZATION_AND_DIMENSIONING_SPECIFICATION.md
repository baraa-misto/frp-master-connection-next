# Visualization and Dimensioning Specification

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 1.3C2A - canonical physical/support surface data and future display requirements |
| Status | Draft / not frozen |
| Visualization implementation | No frontend graphics; backend spatial, direction, exact nominal section, placement/extrusion, and renderer-neutral surface-patch data implemented |

## Purpose

This document specifies synchronized engineering visualization and dimensioning for a complete `JointAssembly`. It governs what views communicate and where their data comes from. Stage 1.3A defines canonical axes, renderer-neutral action directions, and numerical frame-inspection data. Stage 1.3B defines exact nominal standalone standard cross-sections. Stage 1.3C1 defines one renderer-neutral global placement and exact analytic longitudinal extrusion per placed member/connector. Stage 1.3C2A defines stable exact physical/deferred/support surface patches and geometric targetability. None of these stages draws frontend graphics. This document does not define interface targeting, resistance calculations, stress analysis, drawing standards, or numerical dimension criteria.

## Authoritative data boundary

**Approved:** calculation, 3D, 2D, dimensions, and reports derive from the same canonical engineering values. Rendering and annotation are consumers of the canonical engineering model; they are not alternate sources of engineering truth.

The following controls apply:

- engineering geometry is authored and validated in canonical framework-independent
  geometry contracts; Stage 1.3C1 placement remains a separate component association
  and is not yet a `JointAssembly` registry;
- Stage 1.3B standard cross-sections are exact canonical rectangles, lines, voids, or
  analytic annuli, not rendered meshes;
- Stage 1.3C1 placement stores one proper resolved global component frame, explicit
  local-x extent, explicit section offset, analytic physical/deferred/void extrusion
  descriptors, and physical longitudinal boundary planes, not a rendered mesh;
- Stage 1.3C2A surface sets store participant-scoped patch identity, exact source,
  exposure/disposition, signed planar normals or cylinder radial sense, and derived
  geometric targetability, not selection meshes or connection zones;
- render meshes, tessellation, screen coordinates, linework, camera transforms, and measured pixels are never inputs to a resistance calculation;
- derived 2D and 3D representations must retain stable links to their source members, components, physical section elements, material regions, interfaces, bolts, stacks, load paths, shared regions, actions, and results;
- the same master bolt centers and penetrated-layer definitions control holes, calculation inputs, 3D, 2D, dimensions, and reports;
- camera, zoom, orbit, pan, visibility, display units, color theme, selection, and other display state cannot change engineering inputs or results; and
- changing an engineering value occurs only through an explicit, validated update to the canonical model and makes prior results stale.

Future display geometry, arrows, and axis triads must consume the same resolved
`CartesianFrame3D`, Stage 1.3C1 placement, proper rotations, and action-direction
functions used by future engineering calculations. The frontend may choose pixels,
colors, arrow length, tessellation, visibility, and display scale; it may not maintain
an independent placement, axis, sign, connected-end, or moment convention.

A renderer may tessellate an analytic annulus only as a derived display operation.
The tessellated vertices, segment count, chord error, camera, scale, or viewport never
replace or modify the analytic inner/outer radii. Rectangular section regions and
deferred line/area features likewise retain their exact local coordinates regardless
of display scale or projection.

Geometry-supported and calculation-supported are separate statuses. A view may display supported geometry for a calculation-unsupported topology only when the unsupported state is conspicuous and no visual treatment implies engineering acceptance.

## Synchronized view set

| View | Intended communication | Required characteristics |
|---|---|---|
| 3D | Overall assembly topology, orientation, interfaces, access, and selection context | Navigable derived model with stable object identity; no resistance inferred from mesh or appearance. |
| Front | Orthographic relationship in the defined front frame | Vector-style linework and dimensions derived from canonical geometry. |
| Side | Orthographic relationship in the defined side frame | Vector-style linework and dimensions derived from canonical geometry. |
| Top | Orthographic plan relationship | Vector-style linework and dimensions derived from canonical geometry. |
| Drawing Sheet | Controlled composition of named 2D views, notes, legends, dimensions, and status | References the same view definitions and snapshot data; it is not an independent geometry model. |
| Interface-normal | Geometry projected normal to a selected interface | Shows the actual interface participants, hole/bolt arrangement, local orientation, and relevant dimension layers. |
| End | Member/component end geometry and attachment relationship | Uses the selected object's explicit frame and end. |
| Section | Penetrated layers, component relationships, internal locations, or supporting regions at an explicit cut | Cut plane and viewing direction are stored; clipped display geometry does not alter the model. |
| Bolt-stack | Ordered layers along a selected bolt axis | Communicates head, nut, washers, penetrated layers, holes, grip, bearing layers, and shear-plane classifications without assigning capacity. |

Front, Side, Top, and other named orientations identify their explicit source frame. The approved global frame has horizontal `+X` and `+Y` and vertical-up `+Z`. Member local `+x` is fixed `START` to `END`; for a standard unrotated W/I section, local `y` is flange width and local `z` is web depth. For channels, tees, rectangular tubes, angles, and other sections, `y` and `z` are controlled section-datum axes, not silently calculated principal axes.

Complex joints may use multiple interface-normal, end, section, and bolt-stack views. The system must not force all details into a single projection when doing so obscures the physical topology or load path.

## Synchronization behavior

All open views observe one canonical joint revision and, when results are displayed, one calculation snapshot. Synchronization includes:

- selection and hover identity across the assembly tree, 3D, 2D views, result list, and report references;
- visibility and isolation of the same physical object without changing its engineering participation;
- action arrows anchored to the same member, frame, and reference point;
- consistent member/component labels and interface IDs;
- dimensions sourced from the same canonical values; and
- result highlighting sourced from the same immutable result record.

A view that cannot be regenerated for the current canonical revision must show an explicit unavailable or stale condition. It must not display a previous view as though it represents current engineering inputs.

## Standard cross-section visualization

Future cross-section views must derive from `CrossSectionGeometry2D` and preserve its
component-local `y-z` coordinates, `(0,0)` outside-bounds construction datum, exact
profile kind, and source physical-element IDs. A 2D profile itself still supplies no
local-x extent or global position. When placed, those values must come only from its
associated Stage 1.3C1 canonical placement object; a renderer must never infer them
from family, appearance, or another component.

The standard orientations shown to the user are W/I flange-width y and web-depth z;
channel web at `-y` opening to `+y`; tee flange at `+z` with stem toward `-z`;
rectangular-tube width y/depth z with side walls at `-y` and `+y`; angle `LEG_1`
toward `+y`, `LEG_2` toward `+z`, and heel at the negative-y/negative-z corner;
plate width y and thickness z; and round annulus centered at the datum. These are
construction axes, not calculated principal axes or a centroid/shear-center claim.

Physical element selection is per occurrence. A future selector must independently
highlight each web, flange, wall, stem, leg, plate, or curved wall. In particular:

- top and bottom flanges remain independently selectable despite sharing `FLANGES`;
- top and bottom tube walls remain independently selectable despite sharing
  `WALL_PAIR_1`;
- side walls remain independently selectable despite sharing `WALL_PAIR_2`; and
- selecting a material region may highlight its member elements but may not merge or
  replace their identities.

Deferred web/stem-to-flange junctions, the angle heel, and rectangular/square-tube
corners must be visually distinguishable from ordinary targetable physical elements.
They must never be presented as connection targets or as structurally credited
material until a future approved engineering model supports them. Nominal voids must
read as openings/missing space and not as material. Displaying any of this geometry
does not authorize interface, face, hole, bolt, or penetration targeting.

Round-tube display tessellation is transient renderer data. Changing tessellation
resolution may change only visual smoothness, never the exact analytic annulus,
selection identity, dimensions, or any future calculation input. No frontend section
renderer or selection behavior is implemented in Stage 1.3C1.

## Canonical component placement visualization

Future 3D and applicable 2D visualization must derive all component placement data
from the same Stage 1.3C1 placement objects. At minimum, this includes:

- the one resolved global component frame and local-axis triad;
- the global component reference line through local `(x,0,0)`;
- the shifted section-datum line through local `(x,offset_y,offset_z)`;
- the explicit local-x extent and global minimum/maximum boundary-plane data;
- member START and END markers, mapped respectively to minimum and maximum local x;
- the member connected-end marker derived from `AssemblyMember.connected_end`;
- connector neutral minimum/maximum-x boundary markers without member semantics;
- exact physical-element prism or annular-cylinder extents;
- exact deferred prism or zero-thickness ruled-surface extents;
- exact void-prism extents; and
- shifted local outside bounds and any deterministically derived global bound corners.

The component reference line and section-datum line remain visually and semantically
distinguishable when the offset is nonzero. Neither may be labeled a centroidal,
shear-center, analytical, joint, or force line. Boundary-plane normals are geometric
`-local x` and `+local x` directions only; the planes must not be presented as
connection targets or engineering statuses.

Section clocking and global orientation come only from the canonical proper frame. A
renderer may not add an independent roll, mirror, reflection, or family-specific
flip. Exact rectangular prisms and annular cylinders remain authoritative analytic
data. A transient mesh may approximate them for display, but mesh vertices,
tessellation, Boolean unions, camera state, screen projection, and measured pixels
cannot replace placement or physical-element identity.

Deferred junction surfaces, heel/corner prisms, and void prisms must remain visibly
distinct and non-targetable. Shared material-region highlighting may group related
physical elements, but it may not merge their occurrences. One shared connector
placement remains one component identity even if later interfaces reference it more
than once; visualization cannot invent those interfaces or distribute force.

Stage 1.3C1 implements no Three.js, React Three Fiber, SVG, Canvas, WebGL, frontend
control, 3D viewport, axis triad widget, component renderer, START/END marker widget,
load arrow, input field, or API call. This section controls future derivation only.

## Canonical surface-patch visualization

Future surface display and selection must derive from the exact Stage 1.3C2A patch
set. It must preserve participant-scoped patch IDs, source physical/deferred identity,
element-level end cuts, exposure/disposition, signed planar normals, and analytic
round-tube cylinder/annulus data. Camera-facing triangles, renderer mesh indices,
tessellation, clipping, and highlight state cannot replace a patch or change its
targetability.

Regular exterior, void-facing, end-cut, and bounded support patches may be shown as
geometrically eligible for later targeting. Internal-junction, tube-corner,
angle-heel, and every deferred patch must remain visibly distinct and unavailable for
targeting. Geometric eligibility must never be styled as calculation support,
attachment, boltability, capacity, or adequacy. No interface target or connection
zone exists until Stage 1.3C2B.

## Force and sign visualization

The future UI has two deliberately separate modes:

1. **Positive sign-convention mode** shows permanent positive component directions at the selected frame and explicit reference point. `FX`, `FY`, and `FZ` are straight arrows along `+x`, `+y`, and `+z`. `MX`, `MY`, and `MZ` are right-hand rotations about those positive axes. These arrows do not reverse when entered values change.
2. **Applied-action mode** shows the actual signed force and moment components for the selected load combination. A negative linear component reverses its axis. A negative moment reverses rotational sense, equivalently using the negative axis. Zero is explicitly represented and may be hidden only through a visible zero-value control. The signed numerical value remains authoritative.

For the approved member-on-joint convention, a positive local `Fx` at connected end `START` means tension and a negative value means compression. At connected end `END`, negative means tension and positive means compression. Zero is zero. This interpretation does not rewrite the value or reverse the member frame.

Stage 1.3A implements `ActionComponent`, linear/rotational kind, positive-direction data, and applied signed-direction data as immutable renderer-neutral backend contracts. Direction data retains component, kind, signed value, parent/global axis, sign/sense, and zero status. It stores no pixel length, color, screen coordinate, mesh, camera, display scale, or curved-arrow tessellation. It is reference-point agnostic; the caller must preserve the action's existing explicit `ReferencePoint` or resolved point identity.

No Canvas, SVG arrow, Three.js, React Three Fiber, load-input control, axis toggle, section renderer, or API integration is implemented in Stage 1.3B.

## Mandatory future force-entry visualization behavior

Manual force entry is not complete until the future frontend provides all of the following behavior in both positive-convention and applied-action workflows as applicable:

1. A global-axis toggle.
2. A local-axis toggle.
3. Selection of the selected member only or all members.
4. Visible `START` and `END` markers.
5. A visible connected-end marker.
6. Positive sign-convention arrows.
7. Applied signed-force arrows.
8. Applied signed-moment arrows.
9. Signed values and units.
10. An explicit reference-point marker.
11. The selected frame identity.
12. Numerical global/parent components of all local axes.
13. Right-handedness and orthonormality information.
14. Negative force arrows that reverse direction.
15. Negative moments that reverse rotational sense.
16. A zero-value visibility toggle.
17. The same canonical direction data in 3D and every relevant 2D view.
18. Display-scale changes that never change numerical actions.
19. Display logic derived from canonical frame mathematics rather than a frontend convention.
20. Updated arrows visible before the user accepts or saves the load assignment.

In positive sign-convention mode the selected reference point must also show the local-axis triad, the global-axis triad when enabled, component labels, and the reference-point marker. In applied-action mode the display must retain the selected load combination, coordinate frame, connected member end, derived axial sense for member-local `Fx`, selected-member/all-members choice, and optional zero hiding. Unsupported components cannot be omitted; they receive an explicit unsupported indication.

## Numerical frame inspection

`FrameInspection3D` exposes the origin; local x, y, and z expressed in the parent/global frame; all three norms; all pairwise dot products; determinant; right-handed status; orthonormal status; and a geometric validity flag. Raw invalid basis data may be inspected, but it cannot be represented as a valid `CartesianFrame3D`.

The UI must use geometric wording such as `Valid frame`, `Invalid frame`, `Right-handed`, and `Orthonormal`. It must not label frame inspection as engineering `PASS`, engineering `FAIL`, design status, resistance, capacity, utilization, or adequacy.

## Dimension model and layers

Dimensions are annotations linked to canonical geometry features, not values measured from rendered output. Each dimension records its semantic feature references, engineering value, unit/display formatting, view association, and presentation placement. Display rounding cannot overwrite the canonical value.

Stage 1.3B shape dimensions are canonical construction inputs: W/I/channel/tee depth,
width, web/stem thickness and flange thickness; tube outside width/depth and wall
thickness; angle leg extents and thickness; plate width/thickness; and round-tube
outside diameter/wall thickness. Stage 1.3C1 adds the exact local-x extent and explicit
section offset as canonical placement values. A future dimension annotation may
display those exact values and derived exact boundaries, but it may not measure a
mesh, infer a centroid/shear center, or reinterpret a physical boundary plane as a
connection face. The construction datum is not automatically a dimension origin for
fabrication or connection layout.

The view system should support separable dimension layers so a user can control density without changing the model. Initial layers are conceptual and may include:

- **Assembly:** overall member/component extents, primary offsets, and relative placement.
- **Interface:** interface boundaries, edge relationships, and connection location.
- **Bolt layout:** master bolt-center spacing, rows/columns, gages, pitches, and relevant edge relationships, when those terms are approved for the template.
- **Bolt stack:** ordered layer thickness presentation, grip-related geometry, washers, head/nut, and classified planes.
- **Component:** T-section, plate, angle, bracket, gusset, or doubler geometry and orientation.
- **Section/detail:** section cut locations and detail-specific feature relationships.
- **Reference:** axes, frames, force reference points, and non-fabrication context.

These layer names organize presentation only. They do not approve a geometry check or numerical criterion. Initial supported templates may use template-specific dimension placement. Automatic general-purpose dimension layout is not required for the initial checking engine.

If dimension placement collides or cannot communicate a value reliably, the system should flag review or allow controlled presentation adjustment; it must not alter the underlying engineering value to improve appearance.

## Assembly tree and selection

The assembly tree exposes the physical and analytical structure without inventing components. At minimum it can organize:

- members/components, their distinct physical section elements, and their material-region grouping;
- connecting and reinforcement components;
- interfaces;
- bolt groups, bolts, and bolt stacks;
- load combinations and member-end actions;
- load paths and shared regions;
- view definitions; and
- calculation checks/results and snapshots.

Selecting an item highlights the same identified entity and its relevant relationships in all views. A direct member-to-member interface appears as the direct interface between its actual members, not beneath a synthetic connector. A shared T or shared supporting region exposes all contributing interfaces/load paths so combined demand is not visually concealed.

Stage 1.2 creates these element and material-region identities, Stage 1.3B maps exact
nominal section geometry to each physical identity, and Stage 1.3C1 preserves the same
identities in placed extrusion descriptors; none implements rendering. Future
selection must allow two flanges or opposite tube walls to remain separately
selectable even when they reference one material region; selecting the region may
highlight the group without replacing the element identities. Deferred features are
visible inspection identities only and are never selection targets for connection
assignment.

## Result visualization

Failed-check highlighting must link to the exact structured result and affected canonical entities. Highlighting is supplemental communication and never determines result status.

The view layer must distinguish at least:

- `PASS` and `FAIL` from qualified completed checks;
- `INVALID GEOMETRY`;
- `NOT APPLICABLE`;
- `NOT COVERED BY SELECTED CODE`;
- `ENGINEERING REVIEW REQUIRED`;
- `CALCULATION NOT SUPPORTED`;
- `INCOMPLETE INPUT`; and
- `STALE RESULTS`.

Non-success conditions must not be collapsed into warnings, hidden by a filter, colored as passing, or replaced by a neutral-looking blank. Warnings remain supplemental and cannot stand in for a required status. Placeholder results may never be highlighted as `PASS` or `FAIL`.

Whole-joint highlighting must not show an optimistic overall pass while a required interface, component, shared-region, equilibrium, or applicability result is missing. The exact whole-joint aggregation rule is a **Pending Engineering Decision**; until it is approved, ambiguous aggregation fails closed.

## Prohibited and controlled visual claims

- No structural resistance may be calculated from rendered meshes or drawing measurements.
- No stress contour, heat map, deformed shape, or similar field plot may be shown unless it comes from a validated stress analysis appropriate to the claim. This product is not a nonlinear connection FEA program, and decorative stress contours are prohibited.
- Apparent contact, overlap, symmetry, restraint, or load transfer in a rendering cannot create engineering topology.
- Visual completeness cannot imply calculation coverage, source coverage, material qualification, or commercial validation.
- Occlusion, hidden-object state, clipping, exploded views, or transparency cannot remove an object from calculation participation.
- A screenshot or drawing sheet cannot substitute for a versioned immutable calculation/report snapshot.

## Consistency and QA expectations

Future validation must verify:

- 3D, each 2D view, dimensions, calculations, and reports use identical canonical values;
- bolt centers and holes align across all penetrated layers and representations;
- view orientation and applied-action arrows remain correct for reversed member directions and signed-force cases;
- saved and reopened view definitions reproduce their intended engineering view while camera/UI state remains non-engineering;
- visual regression detects unintended drawing/mesh changes without treating screenshots as engineering verification; and
- stale, unsupported, incomplete, review-required, passing, and failing states remain visibly distinct.

Future geometry-display tests must also verify that exact standard orientation and
physical-element identity survive placement/projection; component reference and
section-datum lines preserve their distinct offsets; START/END and connected-end
markers derive from boundary descriptors; proper rotation controls clocking without
reflection; deferred features remain distinct and non-targetable; annulus tessellation
is display-only; and camera, scale, or tessellation changes never change canonical
dimensions or geometry.

Stage 1.3A backend tests verify canonical positive axes, applied sign reversal,
right-hand moment sense, zero status, rotated-frame consistency, and numerical frame
inspection. Stage 1.3B backend tests verify exact nominal primitive coordinates,
topology mappings, deferred status, profile consistency, and analytic round geometry.
Stage 1.3C1 backend tests verify explicit extents/offsets, member/connector placement,
point round trips, START/END and connected-end planes/normals, exact physical/deferred/
void extrusions, analytic annular cylinders, identity preservation, renderer neutrality,
and prohibited-scope boundaries. They do not constitute frontend, 3D, 2D,
accessibility, or real-browser verification. Those application tests remain required
when rendering is implemented.

## Provisional implementation direction

The following are **Provisional Architecture Decisions**, not approved dependencies:

- React and TypeScript with Vite for the future frontend.
- Three.js through React Three Fiber for future 3D.
- SVG-based vector-style dimensioned 2D views.
- Versioned JSON-compatible contracts between canonical model projections and the UI.

Regardless of selected libraries, engineering geometry, calculation authority, and immutable result status remain outside display-library control.

## Pending decisions

### Pending Engineering Decision

- Template-specific permitted reference points and supporting-reaction signs.
- Engineering feature terminology and required dimension sets for each qualified template.
- Which section/interface views are mandatory for each calculation slice.
- Whole-joint status aggregation and exact failed/shared-region presentation requirements.

### Pending Architecture Decision

- Final client rendering architecture, performance limits, drawing export format, accessibility/color standard, and view-definition contract.

Pending choices must be surfaced as unresolved; a rendering default is not an engineering approval.

## Future Stage 1.3C2B visualization requirements

A future interface editor must expose participant order and allow independent selection
and highlighting of the first and second participants, every selected physical patch,
every bounded connection zone, the primary zone, explicit interface origin, local
`x/y/z` triad, and signed plane separation. It must show canonical patch/component/
physical-element identity, source normal, targetability or deferred state, and exact
subzone bounds.

The renderer may derive display meshes and annotations but may not merge canonical
patches, flip normals, swap participants, move the explicit origin, choose a fallback
axis, or change the raw separation. A geometrically valid target must not be styled or
labeled as calculation-supported without a separate approved capability. No frontend
implementation is part of Stage 1.3C2B.

## Stage 1.3C3 renderer-neutral inspection data

Future synchronized views must derive bolt-group origins/triads, master centers,
authoritative axes, exact round-hole cylinders, participant and physical-element layer
identity, entry/exit faces, referenced connection zones, declared layer order, raw
clearances/gaps/spans, resolved action points, target points, eccentricity vectors, and
source/shifted force-moment systems from the canonical Stage 1.3C3 objects.

Display tessellation, clipping, snapping, camera orientation, exploded stack spacing,
dimension rounding, or selection state may not move a center or hole, reorder a stack,
change a raw clearance/gap, reverse an axis, infer a point, or alter a shifted moment.
Geometry-supported holes and action traces must not be presented as calculated or
engineering-approved. No frontend rendering is implemented.

## Stage 2.1A presentation exclusion

Stage 2.1A adds no renderer, API exposure, result panel, report view, or frontend
behavior. Future UI may display quantity values in either approved unit profile and
may inspect source, qualification, mapping, readiness, and issue provenance, but must
not present a planned check as a resistance result or convert `NOT_EVALUATED` into a
visual `PASS` or `FAIL`.

Display-unit choice, display rounding, camera, visibility, selection, and other
presentation state are deliberately excluded from the calculation-contract
fingerprint. The authoritative physical quantity, published hole-source basis,
authoritative stored hole diameter, mapping identities, and engineering state remain
unchanged by visualization.

## Stage 2.3 canonical visualization implementation

Stage 2.3 implements the first rendering adapter without making rendering an
engineering authority. API transport `0.3.0-draft` returns a deterministic
renderer-neutral snapshot built from the same canonical `JointGeometryContext` used
by orchestration. It includes exact component/element primitives, bounded support
surfaces, interface zones, global/joint/member/connector/interface/bolt-group frames,
frame inspections, planar material axes, bolt and round-hole paths, physical START/
END and other reference points, and separate positive/applied action directions.
Negative applied actions reverse their display axis; zero actions remain explicit.

The React Three Fiber adapter presents 3D, Front, Top, and Side views, camera fit,
visibility controls, and numerical inspectors. Camera, style, selection, visibility,
tessellation, and display scaling remain presentation state and cannot modify the
snapshot, result, or fingerprint. The complete workspace contract is recorded in
`SINGLE_BOLT_ENGINEERING_WORKSPACE_SPECIFICATION.md`.

## Stage 2.3R role-based presentation and camera fit

The J1 presentation fixture is a proper rigidly rotated assembly, not a display-only
member swap or independent mesh rotation. The same transform is applied to member
placements, frames, surfaces, zones, bolt centers/axes, holes, reference points, and
action locations. The W local positive x-axis is global positive Z, its START is
lower than END, and the angle brace remains diagonal in a vertical plane.

The default renderer is solid and role-based: W column muted blue-gray, brace dark
blue, selected bolt orange/gold, with an optional X-ray mode. The controlled clean
overlay defaults expose physical solids, bolt/hole geometry, global axes, selected
member axes, bolt axis, and nonzero applied actions. Engineering diagnostics are
available but default off. `Fit Connection` derives bounds from the complete
canonical assembly and uses presentation-only scaling targeted near 72 percent of
the viewport, so equivalent U.S. and SI scenes have equivalent framing. Camera,
display mode, color, overlay, selection, and fitted scale remain non-authoritative.

## Stage 2.3R2 parametric extents and exact-known hardware

The narrow brace-to-column-flange presentation is now generated by the backend from
validated template parameters. The W column remains vertical and continuous through
the fixed connection station. Positive local extents below and above that station and
positive brace segment length control only the represented local member segments. The
acute sign-independent brace angle is `(0, 90]` degrees in the current vertical plane;
the plan angle is fixed at 0 degrees. No browser trigonometry or display mesh is
canonical geometry.

`Fit Connection` retains the selected bolt as its target and computes radius from
every point of every full canonical primitive and segment. Longer column extents
therefore remain visible without moving the connection target or silently clipping
the model. A 90-degree brace remains valid and horizontal; near-longitudinal cases at
or below 5 degrees retain proper frame inspection and are not clamped.

Bolt display is intentionally incomplete when physical data are incomplete. The
resolved stack span and nominal diameter define the shank. Exact source washer flags,
outside diameter, thickness, and path positions define only known washers. The
renderer does not invent head or nut dimensions, thread geometry, protrusion, or an
unidentified washer. Holes remain distinct wireframe void geometry.

## Stage 2.3R3 selected surfaces, axes, and picking

Visualization snapshot `1.2.0-draft` adds backend-resolved orientation semantics,
selected flange element/patch/role, selected angle patch/role, global contact normal,
brace and fixed plan angles, and interference classifications. The selected contact
rectangle is highlighted without making the W member transparent. R3F pointer events
map boxes, the selected bolt, and the selected contact plane back to canonical IDs;
selection never mutates an engineering input or fingerprint.

The persistent corner triad is a screen-anchored overlay whose X/Y/Z directions follow
camera orientation. Full global axes through the model are a separate diagnostic and
default off. Model-space global axes are labeled X/Y/Z, selected-member axes x/y/z,
and material axes LW/CW/TT. Text and the legend carry meaning so color is not the only
encoding. No camera, color, pixel, selection, or legend state enters engineering data.

## Stage 2.3R4 navigation, picking, and triad lifecycle

The 3D camera contract is left-drag rotate, right-drag pan, and wheel zoom. A single
`OrbitControls` instance owns those mappings for one mounted camera/canvas lifecycle;
cleanup removes its one change listener and disposes it. View changes, Fit Connection,
and Reset may replace the camera lifecycle, but cannot accumulate controls, listeners,
frame loops, or other retained resources.

Camera changes update the viewport-fixed global triad by direct SVG attribute mutation
and demand-render invalidation. They do not update React workspace state on every
change. The triad follows camera rotation but not model pan; the optional full global
axes remain model-space geometry. Static triad and legend overlays do not receive
pointer events.

Selection is resolved as a click gesture, not at pointer-down. Movement exceeding four
CSS pixels is navigation, including when it begins over a member, bolt, or contact
surface. A stationary primary-button click retains the established contact, bolt, and
member picking behavior and canonical selection identity. Navigation is excluded from
API requests, result-staleness rules, engineering geometry, calculations, and
fingerprints. No rendered member is directly draggable or editable.

## Stage 2.3R5 live visualization source

The current scene is driven by the latest accepted backend preview visualization;
when a design result is current, its identical canonical snapshot may support result
inspection. The frontend performs no member placement, section clocking, collision
test, contact selection, bolt-path construction, action transformation, or material-
angle calculation. Backend-reported interference participants and physical element
IDs alone control the live red interference highlight.

Preview-affecting edits update member extents, brace angle, orientation/contact,
bolt/washer geometry, applied signed arrows, material LW/CW/TT relationship, and
interference feedback without calculating resistance. Stale design results do not
replace the newer preview scene. R4 OrbitControls lifecycle, click/drag picking,
viewport-corner triad, Fit/Reset behavior, and pointer-event isolation remain intact;
navigation and presentation controls issue no preview requests.

## Stage 2.3R6 view extensions and action labels

Visualization snapshot `1.3.0-draft` distinguishes targetable engineering
`primitives` from backend-authored `view_extension_primitives`. A view extension
reuses the exact section and proper member frame around the fixed connection station,
is rendered in the same member role, and is included in presentation bounds. It has
no targeting, surface, hole, path, interference, end-plane, code-distance, capacity,
or fingerprint role. The renderer replaces the short engineering solid for the same
owner only in the displayed scene; the engineering primitive remains in the
snapshot unchanged.

The default viewer shows signed applied force/moment value labels in a pointer-isolated
DOM overlay outside the WebGL canvas. Labels carry source, component, value, and the
server-returned unit. Positive sign-convention arrows remain noneditable. Zero-value
labels follow the existing zero-action visibility control. Editing a label updates
the same workspace action field as the sidebar and relies on the next backend preview
for arrow direction; no frontend sign, geometry, or material-angle authority is
introduced. Camera controls outside or around the labels remain navigable.

## Stage 2.3R7 projected action-value presentation

Each visible applied `Fx`, `Fy`, `Fz`, `Mx`, `My`, and `Mz` now has its primary
numeric label beside its own rendered arrow or moment arc. A presentation point is
derived from the already-rendered primitive and projected through the active Three.js
camera into a pointer-transparent DOM overlay. Deterministic component offsets avoid
complete overlap while preserving the force/arc association through orbit, pan, zoom,
3D/Front/Top/Side, Fit Connection, and Reset View. Camera changes update label element
positions imperatively and do not create a React frame-loop state path.
Fit-derived, unit-scaled camera near/far planes keep the same physical scene visible
for U.S. and SI snapshots; they are presentation clipping only and do not clamp,
round, resize, or otherwise alter canonical geometry.

Applied labels identify source, component, explicit sign, concise value, and the
server-returned U.S. or SI unit. Only each label's own bounds accept pointer input;
clicking opens the shared action editor, while the rest of the overlay remains
transparent to OrbitControls and canonical picking. Zero labels follow the existing
zero-action policy, and hiding applied arrows or action values hides their numeric
labels. Optional positive-convention labels remain separate `+Fx` through `+Mz`
symbols with no numeric value or edit behavior. Projection, offsets, formatting, and
editing add no geometry, direction, resistance, demand-distribution, status, or
fingerprint authority.
