# Component Placement and Extrusion Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-004 |
| Stage | 1.3C1 — component placement, longitudinal extrusion, and physical end planes |
| Status | Approved placement conventions implemented; software representation provisional; not frozen |
| Implementation | `backend/src/frp_master_connection/geometry/placement.py` |
| Spatial authority | `backend/src/frp_master_connection/geometry/spatial.py` |
| Cross-section authority | `backend/src/frp_master_connection/geometry/section.py` |
| Topology authority | `backend/src/frp_master_connection/domain/section_topology.py` |
| Stage 1.3C2A companion | `PHYSICAL_SURFACE_PATCH_SPECIFICATION.md` |
| Calculation engine | Not implemented |
| Engineering rule set | Not implemented |

## Purpose and safety boundary

Stage 1.3C1 is the first exact three-dimensional placement layer for an
`AssemblyMember` or `ConnectorComponent`. It associates one component identity, one
resolved proper global frame, one explicit local longitudinal extent, one explicit
section-construction-datum offset, and one exact Stage 1.3B
`CrossSectionGeometry2D`. It then exposes exact analytic extrusion and longitudinal
boundary-plane descriptors without changing the source cross-section or topology.

This is geometry development, not a connection-strength stage. Placement validity
means only that the controlled geometric contract is internally valid. It does not
mean engineering adequacy. Stage 1.3C1 implements no design-code equation, material or
section property, force distribution, equilibrium, stress, resistance, capacity,
utilization, limit-state result, or engineering `PASS` or `FAIL`.

The approved placement conventions below are authoritative. Exact module, class,
enum, field, helper, validation-exception, and analytic-descriptor hierarchy choices
are **Provisional Implementation Decisions**. They may change without changing the
approved geometric meaning.

The current provisional implementation exposes these principal placement contracts:

| Contract | Controlled role |
|---|---|
| `PlacedComponentGeometry3D` | Immutable placed member/connector aggregate and canonical access point for mapping, boundaries, and extrusions. |
| `LongitudinalExtent` | Exact finite local interval with `x_end > x_start`. |
| `SectionDatumOffset` | Explicit finite local-y/local-z construction-datum offset. |
| `LocalRectangularPrism3D` | Exact local rectangular-prism descriptor for a physical, deferred, or void rectangle according to its owning wrapper/status. |
| `LocalAnnularCylinder3D` | Exact finite analytic annular-cylinder descriptor. |
| `LocalRuledSurface3D` | Exact zero-thickness surface produced by longitudinally extruding a deferred section line. |

These names and their class hierarchy remain provisional; the approved identity,
analytic geometry, and noncalculation boundaries do not.

## One authoritative resolved global placement

Every placed member or connector has exactly one authoritative resolved placement in
the canonical global frame. The placement stores one proper right-handed
`CartesianFrame3D` as its global placement representation. A
`RigidTransform3D` may be derived or used during composition, but an independently
editable frame and independently editable transform must not coexist as two placement
authorities.

The resolved placement contains translation and proper rotation only. It cannot
contain reflection, scale, shear, skew, projective transformation, or hidden
mirroring. Relative construction may compose Stage 1.3A transforms, but the retained
component placement is resolved directly in canonical global coordinates. Stage
1.3C1 adds neither an unresolved parent-transform hierarchy nor a joint-origin or
`JointAssembly` placement registry.

The placement participant kind is exactly member or connector component. A support is
not placeable through this contract. Placement remains a separate
framework-independent geometry-layer association; START/END coordinates and placement
fields are not added to `AssemblyMember`, `ConnectorComponent`, or `JointAssembly`.

## Local axes, cross-section plane, and section clocking

Component local `x` is the longitudinal extrusion direction and is perpendicular to
the Stage 1.3B local `y-z` cross-section plane. For a member:

```text
local +x = START -> END
```

The member frame origin is START and never reverses because the connected end is END.
For a standard unrotated W/I section, local `y` is flange width and local `z` is web
depth. Other families retain the controlled Stage 1.3B section-datum axes. Round-tube
local `y/z` axes provide geometric clocking only.

Section clocking comes only from the canonical resolved component frame. Member
placement reuses `build_member_frame(START, END, explicit_local_z_reference)`;
connector placement accepts one explicit resolved proper global frame. There is no
second stored roll angle, section-rotation angle, clocking angle, or mirror flag. A
future input convenience may be converted to the canonical frame before storage, but
it cannot remain as a contradictory placement authority.

Proper component rotation may orient a channel, angle, tee, tube, or other section.
Reflection cannot be used to mirror or exchange physical element sides. A genuinely
distinct future handed geometry must be modeled explicitly in topology/geometry under
a later controlled stage; Stage 1.3C1 does not introduce it.

## Construction datum, reference line, and section offset

The Stage 1.3B section construction datum remains `(y=0, z=0)`, the center of the
nominal outside bounding box before placement offset. The placed component frame's
local x axis defines the **component reference line** through component-local
`(x, 0, 0)`. This is a geometric placement reference only.

Every placement carries an explicit immutable section-construction-datum offset:

- `offset_y` is the local-y location of the Stage 1.3B construction datum relative to
  the component reference line; and
- `offset_z` is the local-z location of that datum relative to the reference line.

The **section-datum line** passes through local `(x, offset_y, offset_z)`. It coincides
with the component reference line only when both offsets are zero. Zero offset means
only that the construction datum lies on the reference line.

Neither line nor the construction datum is automatically an area centroid, shear
center, elastic neutral axis, center of mass, structural-analysis or member analytical
line, analytical joint point, connection reference point, or force reference point.
No such identity or coincidence is inferred from symmetry, section family, connector
kind, member role, another component, a drawing, or manufacturer geometry.

Offsets are explicit, finite, traceable, and interpreted in the same assembly length
basis as the associated cross-section and placement dimensions. They may be positive,
negative, or zero. Placement applies them as a separate layer and never mutates or
recenters the source `CrossSectionGeometry2D`.

## Numeric and unit rules

Placement dimensions use the associated assembly/component geometry's one declared
length basis. Stage 1.3C1 performs no unit conversion and accepts no per-field unit
override. Numeric placement values reject Boolean and non-real values, NaN, positive
or negative infinity, and any nonfinite derived value.

Exact dimensional inequality applies. There is no clamping, swapping, absolute-value
repair, rounding, or hidden length tolerance. The Stage 1.3A
`DIMENSIONLESS_MATHEMATICAL_TOLERANCE` remains limited to unit-vector,
orthogonality, proper-rotation, and angular near-parallel checks. It is not reused as a
length, fabrication, collision, end-plane, fit-up, or geometry-acceptance tolerance.

## Longitudinal extent

Every placement has one finite immutable local interval:

```text
x_start < x_end
length = x_end - x_start
```

For a member built from physical START and END points, the exact extent is
`[0, distance(START, END)]`. The physical START plane is local `x=0`; the physical END
plane is local `x=length`. Coincident START and END are rejected.

For a connector, callers supply the explicit extent. Its start and end may be
negative, positive, or straddle local zero, provided `x_end > x_start`. Connector
length is never inferred from connector kind, topology, geometry, another component,
or an interface.

## Controlled member and connector builders

The pure member builder accepts one `AssemblyMember`, a compatible
`CrossSectionGeometry2D`, physical global START and END points, an explicit local-z
reference, and an explicit section offset whose default is the explicit zero value. It:

1. reuses the Stage 1.3A `build_member_frame` operation;
2. retains the member identity and authoritative `AssemblyMember.connected_end`;
3. requires the cross-section family to equal `AssemblyMember.section_family`;
4. requires exact equality between cross-section physical-element IDs and the
   member's explicit `SectionTopology` element IDs; and
5. creates no hidden offset, roll, mirror, joint point, or action transformation.

The pure connector builder accepts one `ConnectorComponent`, one compatible
`CrossSectionGeometry2D`, one explicit proper resolved global frame, one explicit
longitudinal extent, and one explicit section offset. It preserves the connector
identity, including a connector shared by several future interfaces, but performs no
interface placement or demand distribution. Connector kind never silently creates or
replaces topology, geometry, section family, or length.

Both builders reject missing topology, missing or unknown physical elements,
duplicate physical-element geometry, and geometry belonging to a different component
topology. Material-region membership remains authoritative on the supplied Stage 1.2
`SectionTopology`; placement neither copies nor redefines it. There is no
material-property compatibility check because material properties do not yet exist.

## Exact point and line mapping

For local longitudinal coordinate `x`, Stage 1.3B point `(y, z)`, and section offset
`(offset_y, offset_z)`, the exact component-local position is:

```text
(x, y + offset_y, z + offset_z)
```

The global position is obtained only through the placement's canonical resolved
frame. Component-reference-line and section-datum-line points are respectively:

```text
reference(x) = global(frame, (x, 0, 0))
datum(x)     = global(frame, (x, offset_y, offset_z))
```

Inverse mapping first transforms a global point to component-local `(x, local_y,
local_z)`, then reports section coordinates `(local_y-offset_y,
local_z-offset_z)`. It retains component-local x explicitly. It does not project the
point to a section plane and does not clamp x into the longitudinal extent. Extent
membership is a separate explicit caller query.

## Physical longitudinal boundary planes

Each placed component has exactly two immutable renderer-neutral boundary-plane
descriptors:

| Boundary | Local x | Global outward normal | Reference-line point | Section-datum point |
|---|---:|---|---|---|
| Minimum local x | `x_start` | global image of `-local x` | mapped `(x_start,0,0)` | mapped `(x_start,offset_y,offset_z)` |
| Maximum local x | `x_end` | global image of `+local x` | mapped `(x_end,0,0)` | mapped `(x_end,offset_y,offset_z)` |

Each descriptor retains component identity, boundary identity, local x, both global
points, and the global outward unit normal. A member descriptor also retains START or
END identity and whether that plane is the connected end. Member START maps to the
minimum-x boundary and END maps to the maximum-x boundary. The connected-end plane is
selected deterministically from `AssemblyMember.connected_end`; the frame, extent,
stored actions, and START/END identity do not reverse.

A connector retains neutral minimum/maximum-x boundary identities and gains no member
START/END semantics. Boundary normals are signed geometric directions, not new
material-property directions. These planes are geometry only: they are non-targetable
and carry no interface, general connection-face identity, hole, bolt, material
resistance, force demand, or engineering status.

## Exact analytic extrusion descriptors

Every Stage 1.3B primitive is extruded exactly over the placement's local
`[x_start, x_end]` interval. The authoritative data are analytic descriptors, not a
Boolean solid, CAD/B-rep, or permanent mesh.

### Physical rectangular prism

An `AxisAlignedRectangle2D` becomes one exact local rectangular-prism descriptor. It
retains x minimum/maximum; offset y minimum/maximum; offset z minimum/maximum; and its
source physical-element identity. Volume, mass, centroid, inertia, contact, collision,
and fit are not calculated.

### Physical annular cylinder

An `Annulus2D` becomes one exact finite annular-cylinder descriptor. It retains x
minimum/maximum, the offset local y-z center, exact inner radius, exact outer radius,
and source physical-element identity. The circle is not polygonized or tessellated,
and no volume or section property is calculated.

### Deferred rectangle prism and line surface

A Stage 1.3B deferred rectangle becomes an exact deferred rectangular prism. A
deferred line becomes the exact zero-thickness ruled surface obtained by extruding the
line along local x. Both remain deferred, non-targetable, without newly assigned
material ownership or structural credit. A line is never thickened, and no fillet or
junction volume is invented.

### Void prism

A Stage 1.3B rectangular void becomes an exact local void-prism descriptor. It remains
nonmaterial, nonphysical, and non-targetable. Stage 1.3C1 preserves the analytic void
description and performs no Boolean subtraction.

## Physical-element and material-region identity

Each placed physical-element descriptor retains component identity, the existing
physical-element ID, its exact primitive descriptors, source targetability eligibility,
and access to the one global placement frame. Separate physical occurrences are never
merged merely because they share a material region:

| Family | Preserved placed geometry |
|---|---|
| W/I | Separate `WEB`, `TOP_FLANGE`, and `BOTTOM_FLANGE` prisms; two void prisms; deferred web/flange ruled surfaces. Both flanges remain separate while their topology references shared `FLANGES`. |
| Channel | Web remains on local `-y`, opening toward `+y`; separate top/bottom flange prisms; deferred junction surfaces. Proper rotation, never reflection, controls global orientation. |
| Tee | Separate `STEM` and `FLANGE` prisms with flange on local `+z`; deferred meeting surface; no interface distribution. |
| Rectangular/square tube | Four distinct wall prisms, four deferred corner prisms, and one exact interior void prism. Opposite walls remain separate while topology may retain wall-pair material regions. |
| Angle | Separate `LEG_1` and `LEG_2` prisms, one deferred heel prism owned by neither leg, and one open-area void prism. |
| Plate/doubler | One exact `PLATE` prism; the extent supplies physical length but creates no attachment or structural credit. |
| Round tube | One exact `CURVED_WALL` annular cylinder; no mesh, polygon, or fixed circumferential material vector. |

Stage 1.2 topology remains the only authority for material-region membership and
material-orientation semantics. The placement layer carries identity references; it
does not duplicate material properties or reinterpret shared region membership.

## Round-tube placement

Round-tube geometry remains analytic. Local x is axial; local y/z provide geometric
clocking; and the placed wall is one finite annular cylinder with exact shifted center
and exact radii. Stage 1.2 material semantics remain LW axial, CW
circumferential/tangential, and TT radial. Stage 1.3C1 selects no circumferential
evaluation angle, creates no fixed material CW vector, adds no cylindrical coordinate
field, and performs no tessellation.

## Bounds and renderer-neutral data

The canonical placement can deterministically derive its local x interval and its
Stage 1.3B outside bounds shifted by the section offset. For a flat profile, applying
the one resolved global frame to the eight shifted local box corners produces
deterministic global nominal-bounds corners. For an annular profile, exact radial bounds
remain analytic. These are nominal outside bounds, not collision, fabrication,
clearance, fit-up, or connection envelopes.

Future visualization must derive component local axes, global placement, component
START/END markers where applicable, connected-end marker, component reference line,
section-datum line, physical-element extents, deferred zones, voids, and boundary-plane
normal data from the same canonical Stage 1.3C1 placement objects. Camera, pixel,
color, line style, display scale, mesh, tessellation, and frontend state are absent from
the placement contract. No Three.js, React Three Fiber, SVG, Canvas, WebGL, frontend
control, API schema, or renderer is implemented in this stage.

## Deterministic validation invariants

Stage 1.3C1 enforces, as applicable:

1. immutable frozen placement values and tuple collections;
2. finite real placement dimensions with Booleans rejected;
3. exactly one proper resolved global frame;
4. member or connector participant kind only;
5. exact `x_end > x_start` without dimensional tolerance;
6. finite explicit section offset;
7. member frame origin at START and local x from START to END;
8. member extent exactly `[0, member length]`;
9. exact member section-family compatibility;
10. exact physical-element-ID compatibility with explicit topology;
11. no missing, unknown, or duplicate physical-element geometry;
12. no reflected transform or second roll/mirror state;
13. minimum/maximum boundary normals with approved opposite signs;
14. connected-end resolution to the correct member plane;
15. deferred features remain deferred and non-targetable;
16. voids remain nonmaterial and non-targetable;
17. source 2D geometry and Stage 1.2 identity remain unchanged; and
18. deterministic issue or descriptor ordering wherever ordering is exposed.

Validation language is geometric: valid or invalid placement, geometry validation
issue, minimum/maximum-x boundary, START/END plane, connected-end plane, deferred, and
non-targetable. It does not use adequate/inadequate, capacity, utilization, or
engineering `PASS`/`FAIL`.

## Framework, determinism, and reproducibility boundary

Placement code remains in the framework-independent geometry package and imports only
the Python standard library plus existing framework-independent domain/geometry
contracts. It imports no API, DTO, web, database, reporting, infrastructure,
authentication, renderer, or frontend package and adds no dependency. Equal inputs
produce equal descriptors on Windows and Linux without file-system, network, clock,
locale, time-zone, random, native-geometry-library, or environment dependence.

Stage 1.3C1 adds no public serialization, API DTO, persistence mapping, schema
migration, calculation fingerprint, or report model. A future versioned representation
must preserve the component identity, participant kind, one authoritative frame,
longitudinal extent, section offset, exact source geometry/topology association,
physical/deferred/void descriptors, boundary identities/normals, and member
START/END/connected-end meaning without replacing analytic data with a mesh.

## Stage 1.3C2A surface companion and remaining deferrals

Stage 1.3C1 deliberately does not implement:

- a `JointAssembly` placement or joint-origin registry, unresolved transform hierarchy,
  analytical joint point, support placement, or interface origin;
- general side- or end-face identity, connection-face reference, interface or physical
  face targeting, contact, overlap, collision, clearance, or fit;
- hole centers/axes/diameters, bolt centers/axes, penetrated layers, bolt stacks,
  alignment, grip length, access, or any other hole/bolt geometry;
- force-reference-point placement, permitted template points, member-end action-point
  resolution, connector/interface/bolt-group point placement, eccentricity discovery,
  or automatic moment shifting;
- centroid, shear center, neutral axis, area, inertia, torsion constant, warping
  constant, effective property, or any other section property;
- material-property values, source qualification, engineering equations, force or
  bolt-group distribution, equilibrium, demand, resistance, capacity, utilization,
  result status, optimization, or structural credit;
- Boolean solids, CAD/B-rep, canonical mesh, manufacturer fillets/radii, arbitrary
  custom geometry, or a cylindrical material-direction field; or
- API exposure, frontend implementation, persistence, reports, and calculations.

Stage 1.3C2A now derives exact participant-scoped physical and deferred surface
patches from these unchanged placement objects. It introduces signed geometric
normals, exposure/disposition, derived geometric targetability, analytic cylindrical
and annular surface descriptors, and explicit bounded support planes. It does not
change the placement, extrusion, source topology, or domain entities. The companion
contract is controlled by `PHYSICAL_SURFACE_PATCH_SPECIFICATION.md`.

Stage 1.3C2B now targets the planar physical surface patches derived from these
placement objects without modifying the placement, extent, boundary-plane, or source
section contracts. Its explicit interface frame is derived from selected surface
normals and a caller-supplied in-plane reference; it is not another component placement
and does not alter member START/END mapping.

Stage 1.3C3 now consumes exact placed components and their element-level surfaces
without changing placement. Flat-element opposing thickness faces support intended
penetrated layers, and the member connected-end reference resolves to the exact
connected boundary-plane section-datum point. Physical longitudinal boundary-plane
descriptors remain distinct from element-level surface patches and round holes.
Placement still creates no hole, interface, reference point, or calculation by itself.

## Stage 2.3R3 template clocking

Backend template placement combines selected flange side, connected angle leg,
outstanding-leg interface side, brace axis, and selected contact normal to construct a
proper right-handed angle frame. Reflection and frontend mesh roll are forbidden.
Section offsets are derived from supplied angle and W dimensions. The valid web-side
station lies on the negative flange strip with canonical separation from the web while
preserving Stage 2.3R2 member lengths; an invalid side/clocking combination is never
silently changed. Default exterior extents and the 45-degree J1 result are unchanged.

## Stage 2.3R6 engineering ends and display extensions

The current template retains one authoritative connected brace end plane and creates
the selected bolt/end relationship from the engineering `e1` input. That physical
placement remains the only source for target surfaces, hole containment, bolt path,
and code-distance mapping. A change in `e1` changes canonical placement and may
change the existing calculation result and fingerprint.

Finite connection-view member extensions are separate renderer-neutral preview
records. They reuse the exact section geometry and proper placed frame but are
non-targetable and cannot create or replace physical boundary planes or surface
patches. Brace and column view lengths may therefore change presentation bounds
without recentering the engineering joint or moving the connected end or Bolt 1.
