# Joint Assembly Domain Model

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 2.2A - canonical in-memory calculation resolution without domain mutation |
| Status | Draft / not frozen |
| Implementation status | Framework-independent domain/geometry/action contracts, Stage 2.1B bounded calculations, and Stage 2.2A exact application resolution implemented; no serialized `JointAssembly` registry, API, persistence, frontend workflow, or report |

## Purpose and scope

This document defines the conceptual engineering domain and its boundaries. The central engineering object is `JointAssembly`: a complete physical joint, not an isolated interface or a drawing template. **Provisional — PRV-015:** a project schema may contain one or more joint assemblies while the initial user experience may expose only one assembly.

This model supports manual member-end actions, mixed direct and connector-assisted interfaces, shared connectors and supporting regions, synchronized views, deterministic calculation records, and immutable report records. Stage 1.3A establishes reusable resolved Cartesian mathematics and renderer-neutral direction contracts. Stage 1.3B adds standalone exact nominal standard cross-sections. Stage 1.3C1 adds a separate geometry-layer association that places and extrudes one member or connector at a time, but still does not add placement to `JointAssembly`. It does not define connection targeting, holes/bolts, force-reference placement, section properties, equations, capacities, numerical engineering acceptance criteria, optimization, automatic connection selection, or force import.

Labels in this document are intentional:

- **Approved** statements restate requirements in FMC-BL-001 and the controlled Approved entries in the decision register.
- **Provisional** statements are architectural recommendations subject to architecture approval.
- **Pending Engineering Decision** and **Pending Architecture Decision** identify unresolved matters. They are not defaults.
- **Fail closed** means the software must return an explicit non-success state rather than infer missing engineering content or emit `PASS` or `FAIL` from placeholder logic.

## Aggregate and ownership boundaries

| Concept | Responsibility | Boundary |
|---|---|---|
| `ProjectRecord` | Ownership, optional organization association, lifecycle, access metadata, and references to saved engineering documents and snapshots. | It is the persistence/security envelope. Ownership and entitlement metadata are not engineering inputs. |
| `EngineeringProjectDocument` | Versioned, portable, JSON-compatible engineering input document. | It contains the canonical engineering values required to reconstruct the domain aggregate, but not authorization decisions. |
| `ConnectionProject` | In-memory engineering aggregate instantiated from an engineering project document. | It coordinates project-level settings, assemblies, engineering-data references, and snapshot requests. It does not establish account ownership. |
| `JointAssembly` | Complete joint topology, geometry, actions, load paths, shared regions, views, and calculation association. | It is the central unit of joint reasoning and may include multiple members and interfaces. |

**Provisional architecture:** keep `ProjectRecord` separate from `EngineeringProjectDocument`; allow one or more `JointAssembly` objects in the project schema even if the MVP exposes one. Exact persistence tables and API DTOs are not approved.

## JointAssembly contents

### Members and spatial frames

A `MemberInstance` represents a physical member occurrence, including its section and material references, placement, orientation, ends, and participating regions. A joint may contain several members approaching from different directions and inclinations.

Spatial frames identify the coordinate system in which geometry or actions are expressed. Frames must be explicit, addressable, and transformable without discarding handedness or direction. The approved global frame is right-handed with horizontal `+X` and `+Y` and vertical-up `+Z`. A member's local `+x` is fixed from `START` to `END`; it does not reverse when the connected end changes. For a standard unrotated W/I section, local `y` is the flange-width datum direction and local `z` is the web-depth datum direction. Other unsymmetrical sections retain section-datum axes rather than claiming calculated principal axes.

For the standard W/I representation, this geometric convention remains consistent with
Stage 1.2 material identities: shared `LW = X`; web `CW = Z`, `TT = Y`; and flange
`CW = Y`, `TT = Z`. This is direction identity only and performs no stress, force-sharing,
resistance, or utilization calculation. For a round tube, local y/z supply geometric
clocking but do not create a fixed circumferential material CW direction; the Stage 1.2
cylindrical material-orientation rule remains authoritative.

Stage 1.3A keeps two frame concepts distinct:

- `CoordinateFrameReference` is symbolic identity and provenance (`GLOBAL`, joint-local, member-local, connector-local, interface-local, or bolt-group-local, with an owner where required).
- `CartesianFrame3D` is a resolved finite origin and right-handed orthonormal basis expressed in one parent frame.

`GLOBAL_FRAME` is the immutable resolved frame at `(0, 0, 0)` with canonical unit axes. The pure member-frame builder takes finite `START`, `END`, and an explicit local-z reference. It fixes the origin at `START`, normalizes `END - START` as local x, projects the reference perpendicular to x, and recomputes y and z so `x cross y = z`. Coincident points, zero references, parallel or numerically near-parallel references, scaled/skewed bases, and reflected bases are rejected. No global axis, prior frame, or other fallback is silently selected.

The dimensionless mathematical tolerance `1.0e-12` is Provisional and is limited to unit-length, orthogonality, determinant, and angular near-parallel checks. It is not a fabrication, fit-up, hole-alignment, dimensional geometry, or engineering acceptance tolerance.

Stage 1.3C1 does not add start/end coordinates to `AssemblyMember` or place any
component in `JointAssembly`. Instead, its pure geometry-layer builders associate one
member or connector with one exact cross-section and one resolved global frame. No
interface, face, hole, bolt, support, analytical joint point, or force point is placed,
and no frame registry resolves symbolic references.

### Physical components

`ConnectingComponent` is the **Provisional** internal umbrella for physical connectors such as T-sections, plates, angles, gussets, and brackets. It is deliberately distinct from `Fastener`; `Bolt` is a fastener specialization. T-sections are first-class connecting components, and one T-section may connect several braces and a beam in one joint.

Reinforcement components, including `Doubler`, are explicit physical objects with a host, face/side, geometry, material orientation, layers, offsets, holes, attachment classification, structural-credit classification, and qualification source. A doubler is not an implicit increase in its parent component thickness.

### Stage 1.2 symbolic section topology

Each executable `AssemblyMember` or `ConnectorComponent` may carry one explicit
`SectionTopology`. `PhysicalSectionElement` identifies separate web, flange, wall,
stem, leg, plate, curved-wall, or custom occurrences without dimensions or coordinates.
Each element references exactly one component-scoped `MaterialRegion`. A material
region groups shared material-direction identity and never merges the physical
occurrences that reference it.

Pultruded FRP declares one component-local shared LW family through
`FRPComponentOrientation`; planar regions declare their own CW/TT families and a
round-tube wall uses a symbolic cylindrical rule. Steel and other materials may use
the same physical topology without FRP orientation. Standard topology construction is
explicit rather than inferred by member or connector constructors, and custom topology
can split or group regions through explicit scoped IDs.

`MaterialRegion` is distinct from the load-path `SharedRegion` below. The former groups
material orientation/property basis; the latter is a future combined-demand boundary.
They may later be related but are not interchangeable. Material properties, exact
geometry, junction/corner regions, solid-round behavior, interface/face targeting,
and calculations remain outside Stage 1.2.

### Stage 1.3B standalone standard cross-sections

`CrossSectionGeometry2D` is owned by the geometry package and consumes an explicit
standard `SectionTopology`. It maps every existing physical-element ID exactly once
and preserves material-region membership on the topology. It is not a field on
`AssemblyMember` or `ConnectorComponent` in Stage 1.3B, so it has no assembly owner,
local-x extrusion, global position, resolved frame, interface, hole, or bolt target.
Stage 1.3C1 now performs that association in a separate immutable geometry-layer
placement without changing the Stage 1.3B source object or domain entity.

Each standard profile is exact within the approved nominal idealization. Flat-wall
W/I, channel, tee, rectangular/square tube, angle, and plate/doubler geometry uses
sharp-corner axis-aligned rectangles in the local `y-z` plane; round tube uses one
analytic annulus. The construction datum `(0,0)` is the nominal outside-bounding-box
center, not a centroid, shear center, analytical line, joint point, or force reference
point. The 2D source object remains x-free; Stage 1.3C1 supplies local-x extent and
extrusion only through a separate placement object.

Physical web/flange/wall/stem/leg/plate/curved-wall occurrences remain separate.
W/I/channel and tee meeting boundaries are explicit deferred zero-area features. The
angle heel and rectangular/square-tube corners are explicit deferred finite zones.
All are non-targetable and own no material region. Nominal voids are explicit missing
space. Exact custom geometry, fillets/radii, solid round, section properties, and
connection targeting remain deferred. The controlled coordinates and dimensions are
defined by `STANDARD_CROSS_SECTION_GEOMETRY_SPECIFICATION.md`.

### Stage 1.3C1 placed member and connector geometry

The Stage 1.3C1 placement aggregate references one `AssemblyMember` or
`ConnectorComponent`, one compatible `CrossSectionGeometry2D`, one authoritative
proper resolved global `CartesianFrame3D`, one exact local-x extent, and one explicit
finite local-y/local-z section offset. It is not stored on `JointAssembly`, does not
accept a support, and does not create an unresolved transform hierarchy.

For a member, the frame origin is START, local +x remains START to END, and the extent
is exactly `[0,member_length]`. START maps to the minimum-x physical plane and END to
the maximum-x plane. `AssemblyMember.connected_end` selects the connected plane without
reversing the frame or action identity. For a connector, callers supply one proper
global frame and an explicit increasing extent that may straddle local zero; its
boundaries retain neutral minimum/maximum identities.

The component reference line through local `(x,0,0)` remains distinct from the shifted
section-datum line through `(x,offset_y,offset_z)`. Neither is a centroid, shear center,
analytical line, joint point, or force point. Physical boundary planes retain outward
normals `-local x` and `+local x`, but are non-targetable geometry rather than
connection faces.

Stage 1.3B rectangles and annuli become exact rectangular-prism and
annular-cylinder descriptors. Deferred rectangles become deferred prisms, deferred
lines become zero-thickness ruled surfaces, and rectangular voids become void prisms.
Separate physical-element identity and shared material-region membership are
preserved. The source cross-section is not mutated; no Boolean solid, canonical mesh,
force distribution, structural credit, or engineering result is created. Detailed
behavior is controlled by
`COMPONENT_PLACEMENT_AND_EXTRUSION_SPECIFICATION.md`.

### Stage 1.3C2A physical surface patches

Stage 1.3C2A adds a separate geometry-layer surface set for one placed member or
connector. Each exact patch retains participant-scoped identity, its physical-element
or deferred-feature source, signed geometric normal or radial sense, exposure,
disposition, and derived geometric targetability. Standard W/I, channel, tee, tube,
angle, plate/doubler, and round-tube factories preserve the exact source topology and
separate element-level end cuts. Internal junctions, tube corners, and the angle heel
remain deferred and non-targetable.

A narrow builder accepts an explicit `AssemblySupport`, proper surface frame, ID,
label, and positive in-plane extents to create one bounded support patch. It infers
nothing from support kind and creates no support body. Surface patches remain outside
`JointAssembly`; `ConnectionInterface` is unchanged. Geometric targetability is only
eligibility for Stage 1.3C2B and creates no interface, load-path edge, or calculation
support. The full contract is controlled by
`PHYSICAL_SURFACE_PATCH_SPECIFICATION.md`.

### Interfaces

A `ConnectionInterface` describes an actual physical transfer boundary and the participants on its two sides. A `DirectBoltedInterface` connects members directly and must not introduce an artificial connector. A connector-assisted interface joins a member, support, or another component to a real connecting component. One joint may contain both kinds simultaneously.

Interface geometry support and calculation support are separate capabilities. The presence of drawable geometry never establishes a qualified resistance calculation.

### Bolts, bolt groups, and bolt stacks

A `Bolt` has one master center and a physical definition. A `BoltGroup` identifies bolts acting together for a specified interface or shared check. A `BoltStack` records the ordered penetrated layers, their holes, head, nut, washers, grip, shear planes, and bearing layers. The same master bolt centers and penetrated-layer definitions must drive engineering inputs, holes, 3D, 2D, dimensions, and reports.

### Load combinations and member-end actions

A load combination groups a concurrent set of signed actions. `MemberEndAction` belongs to exactly one connected member and one combination and identifies an explicit coordinate frame and `ForceReferencePoint`.

**Approved semantics:** manually entered member-end actions are actions applied by the member to the joint assembly. They are initially final factored design actions. The application must not silently apply additional load factors. Unsupported force components must not be dropped, and eccentricities between the action reference point and interfaces must be preserved.

The treatment of combinations that are not factored is a **Pending Engineering Decision**.

Stage 1.3A implements pure spatial operations without mutating `MemberEndAction` or resolving it in an assembly. Force and moment vectors rotate through the same proper rotation at a fixed physical reference point. Point transformations include translation; vector, force, and moment rotations do not. Explicit reference-point transfer in one identified common frame uses:

```text
F_Q = F_P
M_Q = M_P + (r_P - r_Q) cross F
```

The operation requires both points to identify the same `CoordinateFrameReference`; it never infers a target point or shifts a user-entered action automatically. For the approved member-on-joint convention, local `Fx` at `START` is tension when positive and compression when negative. At `END`, the interpretation reverses: negative is tension and positive is compression. Zero remains zero, and interpretation never rewrites the stored signed component or reverses the member frame.

### Load paths and shared regions

A `LoadPath` is an explicit trace from an applied member action through physical interfaces, fasteners/components, and supporting-member regions. It may branch or converge. It cannot be inferred merely because two rendered objects touch.

A `SharedRegion` identifies a component or supporting-member region that receives demand from more than one interface or path. Shared connecting components receive combined-demand checks. Shared supporting-member regions receive combined checks where applicable. Independently checking incoming interfaces is not sufficient when their demands meet in a shared component or region.

### Results

Results are structured records associated with checks at interface, component, shared-region, and whole-joint levels. They carry applicability and provenance in addition to engineering values. They are outputs, never inputs back into the canonical assembly.

The permitted result states are:

- `PASS`
- `FAIL`
- `INVALID GEOMETRY`
- `NOT APPLICABLE`
- `NOT COVERED BY SELECTED CODE`
- `ENGINEERING REVIEW REQUIRED`
- `CALCULATION NOT SUPPORTED`
- `INCOMPLETE INPUT`
- `STALE RESULTS`

Warnings are supplemental and cannot replace a required unsupported, incomplete, stale, or review-required state. Placeholder calculations may never return `PASS` or `FAIL`.

### View definitions

A view definition identifies an engineering view intent, source frame, orientation, section/cut plane when applicable, visible objects, and requested dimension layers. It does not own geometry and cannot change engineering values. Camera position, zoom, clipping used only for display, selection, highlighting, and other UI state are outside the engineering model.

Approved view families include synchronized 3D, Front, Side, Top, Drawing Sheet, interface-normal, end, section, and bolt-stack views. Detailed presentation behavior is controlled by the visualization specification.

Stage 1.3A provides immutable renderer-neutral positive and applied action directions for `FX`, `FY`, `FZ`, `MX`, `MY`, and `MZ`, plus numerical frame inspection containing parent-coordinate axes, norms, pairwise dot products, determinant, right-handedness, and orthonormality. Stage 1.3B provides exact renderer-neutral section primitives, including an analytic annulus that a renderer may tessellate only for display. Stage 1.3C1 provides the one global component placement, local axes, START/END and connected-end plane data, reference/datum lines, physical/deferred/void extents, and analytic annular-cylinder placement. These objects contain no pixels, colors, camera state, canonical mesh, curved-arrow tessellation, or display scale. `Valid frame` and `Invalid frame` are geometric validation terms; frame inspection must never be labeled engineering `PASS`, engineering `FAIL`, or adequacy. No frontend graphics are implemented in this stage.

### Calculation and report snapshots

A `CalculationSnapshot` is an immutable record of normalized canonical engineering inputs, version/provenance identifiers, fingerprint, and structured results for a completed calculation attempt. An unsuccessful or unsupported attempt may still be recorded, but cannot be represented as a successful calculation.

A `ReportSnapshot` is an immutable presentation record tied to an immutable calculation snapshot and the report definition/version used. Summary and Detailed reports must consume the same immutable result data. A report may not recalculate, reinterpret, or improve a result status.

Engineering input changes make prior results stale for the current document. Historical snapshots remain viewable as historical records and are not silently rewritten.

## Canonical-model rule and representation boundaries

**Approved:** calculation, visualization, dimensioning, and reporting use one canonical engineering model.

| Representation | May contain | Must not become authoritative for |
|---|---|---|
| Canonical engineering domain | Physical topology, engineering geometry, referenced properties, actions, frames, load paths, and shared regions | Account authorization, camera/UI state, or rendered mesh approximations |
| Persistence document | Versioned serialization of canonical engineering values | New engineering meaning introduced only by storage shape |
| Calculation input | Validated projection of canonical values plus explicit rule/data versions | Hidden factors, hidden load paths, or values harvested from rendered geometry |
| Rendering/dimension model | Derived meshes, linework, annotations, labels, and display transforms | Structural resistance or engineering geometry overrides |
| Result model | Traceable outcomes and intermediate records from a calculation snapshot | Mutating original inputs or replacing applicability checks |
| Report model | Presentation derived from immutable result and calculation snapshots | Recalculation or independent status logic |
| UI state | Selection, panels, camera, visibility, transient edits | Engineering results until an explicit validated edit updates the canonical model |

Rendering geometry must never be used to calculate resistance. A persistence DTO, API DTO, mesh, drawing primitive, report field, or UI state object may not silently become a second engineering source of truth.

Resolved spatial mathematics is likewise canonical: future calculation and display code must consume the same `CartesianFrame3D`, rigid-transform, action-rotation, reference-shift, and direction operations. A frontend may choose arrow length and styling, but it may not independently reinterpret signs, axes, connected ends, or moment sense.

Exact nominal cross-section geometry is likewise canonical. Render meshes and annulus
tessellations are derived display artifacts; they cannot replace analytic/rectangular
geometry, change coordinates, merge physical element identities, or turn a deferred
feature into a target.

Placed component geometry is likewise canonical within the separate Stage 1.3C1
geometry layer. A view derives global position, local axes, reference/datum lines,
longitudinal bounds, end markers, connected-end marker, exact physical/deferred/void
extents, and round-tube analytic placement from the same placement object. A mesh,
camera, or drawing projection cannot replace that placement or infer contact,
interface targeting, force points, or a `JointAssembly` registry.

## Domain invariants

1. A joint represents the complete physical assembly, including every participant relied upon by a calculation.
2. Every interface names its actual participants; direct member-to-member bolting has no artificial connector.
3. Every engineering geometry value has one canonical origin and all downstream representations derive from it.
4. Every member-end action identifies member, combination, signed components, coordinate frame, and reference point.
5. Every credited transfer has an explicit load path through real interfaces and components.
6. Every convergence of demands identifies an applicable shared component or region and retains combined demand.
7. Joint equilibrium is calculated or explicitly verified only by an approved implementation; absence of a qualified method fails closed.
8. `Moment` classification means at least one intentionally moment-resisting interface; moment and shear demands sharing components or FRP regions are not treated as unrelated.
9. Unsupported inputs, geometry, force components, basis, or qualification never disappear through normalization or rendering.
10. Geometry-supported and calculation-supported are independently recorded.
11. Automatic optimization and automatic connection selection are outside the initial checking engine.
12. SAP2000 or other force import is outside the initial MVP; manual entry remains primary.
13. Symbolic frame identity and resolved Cartesian geometry remain separate until an explicit assembly-resolution contract is approved.
14. Every rigid transform uses a proper rotation; scaling, reflection, shear/skew, and projective transforms are prohibited.
15. A reference-point shift is explicit, uses one identified common frame, preserves force, and uses `(r_P - r_Q) cross F`.
16. Positive action directions and applied signed directions derive from the same resolved axes that future calculations consume.
17. Standard cross-section geometry maps every supplied standard-topology physical element exactly once and never redefines material-region membership.
18. Deferred heel, corner, and junction features remain explicit, non-targetable, and without material ownership.
19. Construction datum, centroid, shear center, analytical line, joint point, and force reference point remain distinct concepts.
20. Every placed member or connector has one proper resolved global frame, explicit
    local-x extent, and explicit section offset; no second roll/mirror state exists.
21. Member START is minimum local x and END is maximum local x; connected-end identity
    selects a plane without reversing the member frame.
22. Physical longitudinal boundary planes and deferred/void extrusions remain
    non-targetable and create no load-path or calculation authority.
23. Stage 1.3C2A surfaces and Stage 1.3C2B targeting remain outside `JointAssembly`;
    hole/bolt placement is deferred to Stage 1.3C3 or later, and
    force-reference/eccentricity placement specifically to Stage 1.3C3.

## Fail-closed capability boundary

The model may store and display geometry before a calculation method is qualified. A calculation request must establish complete inputs, applicable geometry, covered force components, qualified materials/data, source mapping, rule-set version, and engineer approval for the requested slice. If any required condition is absent or unresolved, the result must use the corresponding non-success state. Missing capacity fields remain absent; they are never converted to zero, infinity, `PASS`, or `FAIL`.

## Unresolved decisions

### Pending Engineering Decision

- Supporting-reaction convention and template-specific allowed force reference points.
- Exact canonical unit system and treatment of non-factored combinations.
- Whole-joint status aggregation rule.
- Material/manufacturer-data qualification, T-connector qualification, doubler structural credit, unsymmetrical angle-brace basis, and moment-joint basis.

### Pending Architecture Decision

- Final persistence provider, API shape, schema migration mechanics, identity provider, billing provider, deployment topology, and MES integration method.

### Provisional architecture

- A framework-independent Python engineering core with pure deterministic calculation functions.
- Versioned JSON-compatible contracts, canonical serialization, and SHA-256 calculation fingerprints.
- Server-authoritative calculations with provider integrations behind replaceable ports/adapters.
- API DTO libraries, web frameworks, databases, and rendering libraries remain outside the domain dependency boundary.

These provisional and pending items may not be treated as approved implementation requirements until entered and approved through the decision register.

## Stage 1.3C2B boundary

`JointAssembly` and `ConnectionInterface` are unchanged. Interface targeting is a
separate geometry-layer aggregate associated with one exact logical interface; exact
surface objects and connection zones are not embedded into the domain entity. The
resolved geometry preserves participant order and source identities but is not a
`JointAssembly` placement registry, persistence model, API DTO, or calculation record.

## Stage 1.3C3 resolved joint geometry context

Stage 1.3C3 leaves every domain entity unchanged and adds a separate staged in-memory
geometry context. `JointGeometryBasis` requires exact complete member, connector,
surface, support-surface, and interface geometry before bolt resolution.
`JointGeometryContext` then adds exactly one resolved geometry aggregate for every
logical bolt group. It becomes the framework-independent source for exact frame
bindings and physical reference-point resolution, but is not serialized, persisted, or
used as a calculation result.

Bolt paths retain master centers, authoritative axes, intended physical-element layers,
entry/exit surfaces, connection-zone references, round-hole cylinders, declared order,
and raw clearances/gaps. Manual actions retain original symbolic provenance and may be
rotated at an unchanged resolved point or shifted only through a caller-directed,
fully traced transform. No hardware, load path, force distribution, equilibrium,
property, resistance, capacity, or result is implemented.

## Stage 2.1A calculation-input projection

Stage 2.1A consumes the exact in-memory Stage 1.3C3 geometry context through a separate
calculation-input projection. The projection preserves assembly, member, interface,
bolt-group, physical-layer, surface-patch, connection-zone, hole, authoritative-axis,
ordered-stack, force-direction, and provenance identities. It maps only the authorized
one-logical-bolt, one-row, rectangular pultruded-FRP layer family.

Material and fastener snapshots are immutable calculation inputs rather than new
`JointAssembly` registries. Planned checks and aggregate readiness are not attached to
the aggregate as calculated results. No domain serialization, project-schema change,
persistence model, API contract, report snapshot, resistance, capacity, utilization,
or physical-input `PASS`/`FAIL` is introduced.

## Stage 2.2A application resolution

The application layer now accepts one exact `JointAssembly` together with the exact
`JointGeometryContext` that retains it. It resolves, but does not add to the domain,
one interface, bolt group, bolt location/path, load combination, and optional manual
action. Every participant, element, region, and assignment must belong to that same
canonical object graph. This identity bridge does not create a `JointAssembly`
geometry registry, attach calculation results to domain entities, or establish API,
persistence, report, or serialization behavior.
