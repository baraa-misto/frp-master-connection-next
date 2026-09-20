# Standard Cross-Section Geometry Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-003 |
| Stage | 1.3B — exact nominal standard cross-section geometry |
| Status | Approved modeling conventions implemented; software representation provisional; not frozen |
| Implementation | `backend/src/frp_master_connection/geometry/section.py` |
| Topology authority | `backend/src/frp_master_connection/domain/section_topology.py` |
| Stage 1.3C1 companion | `COMPONENT_PLACEMENT_AND_EXTRUSION_SPECIFICATION.md` |
| Stage 1.3C2A companion | `PHYSICAL_SURFACE_PATCH_SPECIFICATION.md` |
| Calculation engine | Not implemented |
| Engineering rule set | Not implemented |

## Purpose and safety boundary

This specification controls exact two-dimensional nominal geometry for the supported
standard section families. Exact means exact within the approved nominal idealization:
flat-wall sections use the nominal sharp-corner idealization and a round tube uses an
analytic annulus. Each outside bounding box is exact within that idealization. It does
not mean manufacturer-exact, as-built, fabrication-exact,
code-effective, or analysis-effective geometry.

Stage 1.3B contains no design-code equation, licensed-source content, material or
section property, stress, resistance, force distribution, connection check, capacity,
utilization, or engineering `PASS` or `FAIL`. Geometry support and calculation support
remain separate capabilities.

The approved modeling conventions in this document are authoritative. Exact module,
class, enum, field, helper, and exception names and the internal no-overlap algorithm
are **Provisional Implementation Decisions**. They may change without changing the
approved engineering meaning.

## Plane, extrusion direction, datum, and units

Every cross-section is constructed in the owning component's local `y-z` plane. A
`SectionPoint2D` therefore has only `y` and `z`; it has no `x` coordinate. Local `x`
is the member/component extrusion direction. The Stage 1.3B source geometry remains
strictly two-dimensional; Stage 1.3C1 associates it with a separate owner placement,
explicit local-x extent, section offset, exact analytic extrusion descriptors, and
physical longitudinal boundary planes.

The construction datum is exactly `(y=0, z=0)`, the center of the nominal outside
axis-aligned bounding box. It is a construction reference only. It must not be called,
inferred to be, or silently substituted for any of the following:

- the area centroid;
- the shear center;
- a calculated principal-axis origin;
- an analytical line;
- a joint point;
- a force or moment reference point; or
- an interface, hole, bolt, or attachment location.

Dimensions are finite real values interpreted in the owning assembly's declared
length unit. Stage 1.3B performs no unit conversion and stores no per-field unit
override. Booleans, non-real values, NaN, infinities, zero, and negative dimensions
are rejected. Inputs are never made valid by absolute value, swapping, clamping,
rounding, tolerance, or implicit conversion. The Stage 1.3A dimensionless
mathematical tolerance is not a dimensional geometry tolerance; the strict
inequalities below are exact nominal constraints.

An otherwise-valid finite dimension set is also rejected when the required
half-dimensions or derived primitive boundaries/spans collapse, become nonfinite, or
change their required strict ordering in the runtime's IEEE floating-point
representation. Factories therefore never silently round an exact nominal boundary
into a coincident or degenerate coordinate. This is an exact representability check on
the software value, not a dimensional tolerance, fabrication criterion, fit-up rule,
or engineering acceptance limit.

Because the geometry object is standalone and is not attached to a `JointAssembly`,
its numeric values do not independently declare a unit. Stage 1.3C1 placement
associates it with one member or connector and interprets the geometry, extent, and
offset in that owner's declared assembly length basis without silently converting or
mixing units. The source `CrossSectionGeometry2D` itself remains owner- and unit-field
free.

## Canonical two-dimensional contracts

The implemented immutable, frozen, slotted contracts are:

| Contract | Controlled meaning |
|---|---|
| `SectionPoint2D` | One finite `(y, z)` point. |
| `SectionBoundingBox2D` | Finite `min_y`, `max_y`, `min_z`, and `max_z`, with positive width and depth. |
| `AxisAlignedRectangle2D` | Exact rectangle with positive local-y and local-z spans. Shared boundaries are permitted. |
| `SectionLineSegment2D` | Exact nonzero segment used only for a deferred zero-area meeting boundary. It is not area or material. |
| `Annulus2D` | Exact center, positive outer radius, nonnegative inner radius, and outer radius greater than inner radius. |
| `PhysicalElementGeometry2D` | One existing Stage 1.2 physical-element ID mapped to an immutable tuple of exact physical primitives. |
| `DeferredSectionFeature2D` | Stable ID, controlled kind, label, exact rectangle or line, and permanently explicit deferred/non-targetable status for this stage. |
| `SectionVoid2D` | Stable ID, label, and exact rectangular nominal opening or missing region. It is neither material nor a target. |
| `CrossSectionGeometry2D` | Datum, outside bounds, family, idealization, physical mappings, deferred features, nominal voids, and profile representation. |

The implementation-level primitive aliases, controlled enum member names, and common
class hierarchy are provisional. The engineering distinctions are not: a physical
element, a deferred feature, and a void are different concepts and cannot masquerade
as one another.

`PhysicalElementGeometry2D.is_targetable` describes future targetability of the
identified physical occurrence; it does not implement targeting. Each deferred feature
has `is_deferred = True` and `is_targetable = False`. A deferred feature owns no
`MaterialRegion` and cannot be used as a substitute physical element.

## Exact profile representations and idealizations

Flat-wall standard sections use `RECTANGULAR_COMPOSITE` representation with
`NOMINAL_SHARP_CORNER` idealization. Their authoritative nominal profile is expressed
by the outside bounds, exact physical rectangles, exact deferred finite-area zones
where required, exact deferred meeting lines where required, and exact nominal void
rectangles. No fillet, radius, local thickening, material credit, arbitrary polygon,
CAD Boolean, spline, or mesh is implied.

Round-tube geometry uses `ANALYTIC_ANNULUS` representation and idealization. The
annulus remains the canonical geometry. Polygon vertices and rendering tessellation
are not stored in it and cannot replace it.

For standard factory output:

- every physical rectangle, deferred rectangle, void, and deferred line endpoint lies
  within the outside bounds;
- separate physical-element rectangle interiors do not overlap, although boundaries
  may meet;
- deferred finite-area interiors do not overlap physical interiors or each other;
- void interiors do not overlap physical or deferred finite-area interiors or each
  other;
- the construction datum is `(0,0)` and equals the outside-bounds center; and
- round-tube center and radii reproduce its declared bounds.

These checks are targeted profile-consistency checks, not a universal polygon-Boolean
engine and not an engineering adequacy calculation.

## Topology authority and material continuity

`SectionTopology` remains the only source of physical-element identity and
element-to-material-region membership. A standard geometry factory consumes an
explicit standard topology; it does not infer or create hidden topology from
dimensions. The supplied topology must be canonical for its declared standard
family, and that family must match the requested geometry. Every topology element is
mapped exactly once and no unknown element is accepted. The factory does not mutate
the topology.

`PhysicalElementGeometry2D` carries only the physical element ID and geometry. It does
not copy, redefine, or override `PhysicalSectionElement.material_region_id`. Thus:

- top and bottom W/I/channel flanges remain separate physical occurrences even when
  they share `FLANGES`;
- top and bottom rectangular-tube walls remain separate occurrences sharing
  `WALL_PAIR_1`;
- the two side walls remain separate occurrences sharing `WALL_PAIR_2`;
- tee stem/flange, angle legs, plate, and round curved wall retain their Stage 1.2
  memberships; and
- the round `CURVED_WALL` remains in `CYLINDRICAL_WALL`, with axial LW,
  circumferential/tangential CW, and radial TT semantics.

Geometry never creates material properties, evaluates cylindrical direction at an
angle, or establishes material equivalence. Custom symbolic topology remains valid,
but exact custom geometry is deferred and a standard factory rejects it.

## Dimension contracts

The implementation uses descriptive Python field names. The engineering symbols and
exact validation rules are:

| Shape | Inputs | Exact constraints |
|---|---|---|
| W or general I | `d` overall depth, `bf` flange width, `tw` web thickness, `tf` flange thickness | `d > 2 tf`; `bf > tw` |
| Channel | `d` overall depth, `b` flange width, `tw` web thickness, `tf` flange thickness | `d > 2 tf`; `b > tw` |
| Tee | `d` overall depth, `bf` flange width, `tw` stem thickness, `tf` flange thickness | `d > tf`; `bf > tw` |
| Rectangular/square tube | `B` outside width, `H` outside depth, `t` wall thickness | `B > 2t`; `H > 2t`; square requires `B == H` |
| Angle | `Ly` local-y leg extent, `Lz` local-z leg extent, `t` thickness | `Ly > t`; `Lz > t` |
| Plate/doubler | `b` local-y width, `t` local-z thickness | `b > 0`; `t > 0` |
| Round tube | `Do` outside diameter, `t` wall thickness | `Do > 2t`; `Ro = Do/2`; `Ri = Ro - t > 0` |

The corresponding provisional implementation classes are `ISectionDimensions`,
`ChannelDimensions`, `TeeDimensions`, `RectangularTubeDimensions`, `AngleDimensions`,
`PlateDimensions`, and `RoundTubeDimensions`. A square tube uses the rectangular-tube
contract with equal outside dimensions; equality does not create another engineering
topology. A doubler uses the plate cross-section contract. Solid-round geometry is not
implemented.

## WIDE_FLANGE and I_SECTION

Both families use one construction. Local `y` is flange width and local `z` is web
depth. With `y0 = bf/2`, `z0 = d/2`, `yw = tw/2`,
`zb = -d/2 + tf`, and `zt = d/2 - tf`:

| Region | Exact local coordinates |
|---|---|
| Outside bounds | `y ∈ [-bf/2, bf/2]`, `z ∈ [-d/2, d/2]` |
| `TOP_FLANGE` | `y ∈ [-bf/2, bf/2]`, `z ∈ [zt, d/2]` |
| `BOTTOM_FLANGE` | `y ∈ [-bf/2, bf/2]`, `z ∈ [-d/2, zb]` |
| `WEB` | `y ∈ [-tw/2, tw/2]`, `z ∈ [zb, zt]` |
| `LEFT_WEB_VOID` | `y ∈ [-bf/2, -tw/2]`, `z ∈ [zb, zt]` |
| `RIGHT_WEB_VOID` | `y ∈ [tw/2, bf/2]`, `z ∈ [zb, zt]` |

The top junction is the line from `(-tw/2, zt)` to `(tw/2, zt)`; the bottom
junction is the line from `(-tw/2, zb)` to `(tw/2, zb)`. Both are deferred
`WEB_TO_FLANGE_JUNCTION` features. No finite fillet region is added. `WEB`,
`TOP_FLANGE`, and `BOTTOM_FLANGE` map to their same-named Stage 1.2 physical
elements; the two flanges remain independently selectable while sharing `FLANGES`.

## CHANNEL

The one standard orientation has depth along local `z`, web on local `-y`, and opening
toward local `+y`. With `yi = -b/2 + tw`, `zb = -d/2 + tf`, and
`zt = d/2 - tf`:

| Region | Exact local coordinates |
|---|---|
| Outside bounds | `y ∈ [-b/2, b/2]`, `z ∈ [-d/2, d/2]` |
| `TOP_FLANGE` | `y ∈ [-b/2, b/2]`, `z ∈ [zt, d/2]` |
| `BOTTOM_FLANGE` | `y ∈ [-b/2, b/2]`, `z ∈ [-d/2, zb]` |
| `WEB` | `y ∈ [-b/2, yi]`, `z ∈ [zb, zt]` |
| `CHANNEL_OPENING` | `y ∈ [yi, b/2]`, `z ∈ [zb, zt]` |

The top and bottom web-to-flange junction lines span `[-b/2, yi]` at `zt` and
`zb`, respectively. They are deferred and receive no fillet area. The standard
factory does not create a hidden mirrored topology. Stage 1.3C1 placement may reorient
the section only through its approved proper resolved global frame; the Stage 1.3A
transform contract does not permit reflection.

## TEE

The one standard orientation has its flange on local `+z` and stem extending toward
local `-z`. Let `yf = bf/2`, `ys = tw/2`, and `zf = d/2 - tf`:

| Region | Exact local coordinates |
|---|---|
| Outside bounds | `y ∈ [-bf/2, bf/2]`, `z ∈ [-d/2, d/2]` |
| `FLANGE` | `y ∈ [-bf/2, bf/2]`, `z ∈ [zf, d/2]` |
| `STEM` | `y ∈ [-tw/2, tw/2]`, `z ∈ [-d/2, zf]` |
| `LEFT_STEM_VOID` | `y ∈ [-bf/2, -tw/2]`, `z ∈ [-d/2, zf]` |
| `RIGHT_STEM_VOID` | `y ∈ [tw/2, bf/2]`, `z ∈ [-d/2, zf]` |

The stem-to-flange junction is the deferred line from `(-tw/2, zf)` to
`(tw/2, zf)`. A T connector may use this same cross-section definition, but no
interface or load distribution is created.

## RECTANGULAR_TUBE and square tube

Let `y- = -B/2 + t`, `y+ = B/2 - t`, `z- = -H/2 + t`, and
`z+ = H/2 - t`:

| Region | Exact local coordinates |
|---|---|
| Outside bounds | `y ∈ [-B/2, B/2]`, `z ∈ [-H/2, H/2]` |
| `TOP_WALL` | `y ∈ [y-, y+]`, `z ∈ [z+, H/2]` |
| `BOTTOM_WALL` | `y ∈ [y-, y+]`, `z ∈ [-H/2, z-]` |
| `SIDE_WALL_1` (local `-y`) | `y ∈ [-B/2, y-]`, `z ∈ [z-, z+]` |
| `SIDE_WALL_2` (local `+y`) | `y ∈ [y+, B/2]`, `z ∈ [z-, z+]` |
| `TUBE_INSIDE_OPENING` | `y ∈ [y-, y+]`, `z ∈ [z-, z+]` |
| `CORNER_NEGATIVE_Y_NEGATIVE_Z` | `y ∈ [-B/2, y-]`, `z ∈ [-H/2, z-]` |
| `CORNER_POSITIVE_Y_NEGATIVE_Z` | `y ∈ [y+, B/2]`, `z ∈ [-H/2, z-]` |
| `CORNER_NEGATIVE_Y_POSITIVE_Z` | `y ∈ [-B/2, y-]`, `z ∈ [z+, H/2]` |
| `CORNER_POSITIVE_Y_POSITIVE_Z` | `y ∈ [y+, B/2]`, `z ∈ [z+, H/2]` |

The authoritative complete nominal footprint is the four physical wall rectangles
plus the four deferred corner squares, excluding the inside opening. Each corner is a
`RECTANGULAR_TUBE_CORNER`, has no material ownership, and is non-targetable. A corner
is never assigned to one wall. Square tubes use the same topology and geometry with
`B == H`.

## ANGLE

The one standard orientation has `LEG_1` extending toward local `+y`, `LEG_2`
extending toward local `+z`, and its outside heel at the negative-y/negative-z corner
of the centered bounds. Let `yh = -Ly/2 + t` and `zh = -Lz/2 + t`:

| Region | Exact local coordinates |
|---|---|
| Outside bounds | `y ∈ [-Ly/2, Ly/2]`, `z ∈ [-Lz/2, Lz/2]` |
| `LEG_1` | `y ∈ [yh, Ly/2]`, `z ∈ [-Lz/2, zh]` |
| `LEG_2` | `y ∈ [-Ly/2, yh]`, `z ∈ [zh, Lz/2]` |
| `ANGLE_HEEL` | `y ∈ [-Ly/2, yh]`, `z ∈ [-Lz/2, zh]` |
| `ANGLE_OPEN_AREA` | `y ∈ [yh, Ly/2]`, `z ∈ [zh, Lz/2]` |

The authoritative complete nominal footprint is `LEG_1`, `LEG_2`, and the deferred
`ANGLE_HEEL`, excluding `ANGLE_OPEN_AREA`. The heel is not assigned to either leg,
has no Stage 1.2 material-region ownership, and is non-targetable. Geometry does not
infer which leg is connected and does not model a heel radius.

## PLATE and doubler

Width `b` runs along local `y`; thickness `t` runs along local `z`. The outside bounds
and the one `PLATE` physical rectangle are both:

```text
y ∈ [-b/2, b/2]
z ∈ [-t/2, t/2]
```

There is no void and no deferred junction. The contract may be reused for an approved
flat connector plate or doubler. It adds no local-x length, hole, host association,
offset, attachment, or structural credit.

## ROUND_TUBE

The construction datum and annulus center are `(0,0)`. With `Ro = Do/2` and
`Ri = Ro - t`, the exact physical primitive is one annulus centered at the datum with
outer radius `Ro` and strictly positive inner radius `Ri`. The outside bounds are:

```text
y ∈ [-Ro, Ro]
z ∈ [-Ro, Ro]
```

The topology's one `CURVED_WALL` maps to the annulus and remains in
`CYLINDRICAL_WALL`. The geometry chooses no circumferential evaluation angle and no
fixed Cartesian CW vector. It contains no polygon vertices, tessellation, solid round,
area, centroid, or other section property.

## Deferred and non-targetable geometry

Stage 1.3B deliberately represents unsupported geometry rather than silently crediting
or deleting it:

- W/I and channel web-to-flange meeting boundaries are deferred zero-area lines;
- the tee stem-to-flange meeting boundary is a deferred zero-area line;
- the angle heel is a deferred finite `t × t` rectangle; and
- rectangular/square-tube corners are four deferred finite `t × t` rectangles.

Deferred lines do not add or subtract area. Deferred finite zones preserve the
complete approved nominal footprint but carry no physical-element identity, material
region, future connection target, structural credit, or calculated property. A future
approved model must make any different junction/corner treatment explicit and
versioned; Stage 1.3B data must not be silently reinterpreted.

## Visualization-ready contract

The canonical engineering cross-section is the exact geometry described above, not a
rendered mesh. Future 2D/3D renderers derive display data from it and from the same
Stage 1.3C1 canonical placement objects that carry its resolved global frame, extent,
offset, boundary planes, and analytic extrusion descriptors. A renderer may
tessellate the annulus only for display; tessellation resolution, camera, scale, zoom,
linework, and screen coordinates cannot change the analytic annulus or any exact
rectangle/line/extrusion coordinate.

Future selection must retain each physical occurrence's Stage 1.2 identity. In
particular, top and bottom flanges and opposite tube walls remain independently
selectable even when each pair shares one material region. Deferred heel, corner, and
junction features must look distinct from ordinary targetable elements and must never
be offered as connection targets until a separately approved engineering model
supports them.

Stages 1.3B and 1.3C1 implement no frontend, mesh generator, view, camera, selection
workflow, dimension annotation, or API payload.

## Framework and assembly boundary

The geometry package may depend inward on Stage 1.2 topology contracts. Domain
entities do not import geometry, so no domain-to-geometry cycle is created.
`AssemblyMember` and `ConnectorComponent` gain no geometry field in Stage 1.3B or
Stage 1.3C1. The Stage 1.3C1 geometry layer now provides the authorized separate
immutable association among a component, its topology, its cross-section geometry,
one proper resolved global frame, one local-x extent, and one explicit section offset.

The implementation imports no web framework, DTO library, database layer, rendering
library, report layer, or infrastructure package. Values and factory output are
immutable and deterministic for equal inputs. No file, network, clock, random, global
state, or entity mutation participates in construction.

## Stage 1.3C1 placement and extrusion companion

`COMPONENT_PLACEMENT_AND_EXTRUSION_SPECIFICATION.md` controls how this unchanged
source geometry is placed and extruded. A section point `(y,z)` at local x maps to
component-local `(x,y+offset_y,z+offset_z)` and then to global coordinates only through
the placement's one proper resolved frame. The component reference line through
`(x,0,0)` remains distinct from the shifted section-datum line through
`(x,offset_y,offset_z)`.

Stage 1.3C1 converts physical rectangles to exact rectangular-prism descriptors, the
round-tube annulus to an exact annular-cylinder descriptor, deferred rectangles to
deferred prisms, deferred lines to zero-thickness ruled surfaces, and rectangular
voids to void prisms. Every descriptor retains its Stage 1.3B identity and status.
Section offset shifts all placed primitives and outside bounds consistently but does
not mutate this source geometry, the placement frame, or the component reference
line. No Boolean solid or canonical mesh is introduced.

The member START plane is the minimum-local-x boundary and END is the maximum-local-x
boundary, with outward normals `-local x` and `+local x`. Connector boundaries retain
neutral minimum/maximum identities. All are non-targetable geometry in Stage 1.3C1;
they are not connection-face references.

## Stage 1.3C2A surface derivation and source-contract deferrals

Stage 1.3C2A consumes the placed extrusion of this unchanged source geometry and
derives exact participant-scoped physical/deferred surface patches. It splits W/I and
tee inner flange surfaces around junction strips, retains channel opening geometry,
keeps tube corners and the angle heel deferred, preserves separate element-level end
cuts, and represents round-tube sides/ends analytically. Surface geometry does not
mutate this source or redefine material-region membership. See
`PHYSICAL_SURFACE_PATCH_SPECIFICATION.md`.

The standalone Stage 1.3B source object does not itself implement:

- local-x extent, extrusion, end planes, global placement, symbolic-frame resolution,
  or owner association; Stage 1.3C1 supplies these only in a separate immutable
  geometry-layer placement object;
- arbitrary custom geometry, polygon entry, custom holes, splines, CAD import,
  Boolean geometry, custom curved walls, fillets/radii, local thickening, or solid
  round;
- centroid, shear center, principal axes, area, moments of area, torsion constants,
  warping constants, effective properties, or any other section property;
- connection face, interface, hole, bolt, penetration, attachment, or load-path
  targeting, including targeting of every deferred zone;
- material property values, manufacturer qualification, source applicability,
  stresses, force distribution, equilibrium, reactions, resistances, capacities,
  utilization, optimization, or result status;
- persistence, public serialization, schema migration, API routes, frontend
  implementation, reporting, or calculation fingerprints; or
- Stage 1.3C2B interface targeting, Stage 1.3C3-or-later hole/bolt placement,
  or force-reference/eccentricity integration specifically in Stage 1.3C3.

These exclusions do not reduce the authority of the nominal geometry conventions.
They prevent geometry availability from implying targeting, material credit,
calculation coverage, or engineering approval. Stage 1.3C1 placement availability
does not weaken those boundaries.

## Stage 2.3R3 W-flange face semantics

The vertical global placement of the current W column does not rename the canonical
`TOP_FLANGE` physical element. Within local section coordinates, `EXTERIOR` means the
broad thickness face away from the web and `WEB_SIDE` the broad thickness face toward
the web. Mapping uses topology, web location, flange thickness direction, and surface
roles; camera direction, global view, color, and the word "top" are not authority.
Connected angle legs remain distinct `LEG_1` and `LEG_2` physical occurrences with
matching material-region identities.
