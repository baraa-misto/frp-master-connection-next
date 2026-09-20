# Bolt Path, Hole, and Layer Geometry Specification

| Control | Value |
|---|---|
| Stage | 1.3C3 — bolt-group placement, hole paths, and penetrated layers |
| Status | Implemented geometry contract; locally validated; not frozen |
| Implementation | `backend/src/frp_master_connection/geometry/bolt_paths.py` |
| Joint context | `backend/src/frp_master_connection/geometry/joint_context.py` |
| Calculation support | Not implemented |

## Purpose and boundary

This specification controls framework-independent bolt-group placement, authoritative
master centers and axes, exact round-hole cylinders, intended penetrated physical
layers, ordered layer stacks, bounded containment, and raw geometric clearances. It
implements geometry only. It defines no fastener hardware, drilling permission,
fabrication tolerance, contact, fit, bearing, shear-plane classification, resistance,
force distribution, utilization, or engineering result.

`JointAssembly`, `BoltGroup`, `BoltLocation`, and `ConnectionInterface` remain the
logical domain records. Separate immutable geometry specifications and resolved
records retain those exact objects. Geometry-supported holes and paths do not make a
bolt calculation-supported.

## Physical surface semantics

Every `SurfacePatch3D` now carries one explicit `SurfacePatchRole` assigned by the
authoritative shape factory:

- `NEGATIVE_THICKNESS_FACE` and `POSITIVE_THICKNESS_FACE` identify opposing broad
  faces of one flat physical element;
- `EDGE_FACE` identifies a free or boundary edge face;
- `END_CUT_FACE` identifies a rectangular physical-element longitudinal cut;
- `OUTER_CYLINDRICAL_FACE`, `INNER_CYLINDRICAL_FACE`, and `ANNULAR_END_FACE` preserve
  analytic round-tube meaning;
- `JUNCTION_FACE` identifies every deferred/junction-owned patch; and
- `SUPPORT_FACE` identifies an explicit bounded support surface.

The role is required canonical data. It is never inferred from patch ID, label, area,
aspect ratio, material, renderer mesh, visibility, or camera orientation. Existing
source, exposure, disposition, signed normal, targetability, and participant identity
remain authoritative. The role does not create calculation support.

## Staged joint geometry context

`JointGeometryBasis` is complete before any bolt resolver runs. It retains one exact
valid assembly, explicit joint-local resolved frame, every placed member and connector,
their exact surface sets, declared bounded support surfaces, and every resolved logical
interface. Coverage and order must match the assembly exactly, and cross-assembly
objects fail closed.

`JointGeometryContext` adds exactly one `ResolvedBoltGroupGeometry` for every logical
bolt group in assembly declaration order. This staged construction prevents circular
frame resolution. The final context resolves `GLOBAL`, `JOINT_LOCAL`, `MEMBER_LOCAL`,
`CONNECTOR_LOCAL`, `INTERFACE_LOCAL`, and `BOLT_GROUP_LOCAL` symbolic references while
retaining the original reference, exact resolved frame, and exact owner provenance.
There is no owner, axis, or global-frame fallback.

## Bolt-group placement and master geometry

A `BoltGroupGeometrySpecification` names the exact logical bolt group, one declared
primary interface, two finite origin coordinates in that interface's local plane, an
explicit in-plane direction, one explicit geometric comparison tolerance, and exactly
one ordered path definition per logical bolt location.

The logical group must use its matching `BOLT_GROUP_LOCAL` frame and matching
`BOLT_GROUP_ORIGIN` reference. The resolved group origin is obtained at interface-local
`x = 0`; it is not projected from a member, centroid, section datum, or rendered point.
Group local `+x` is the primary interface `+x`. Group `+y` is the normalized projection
of the explicit in-plane reference normal to `+x`, and `+z = +x cross +y`; `+y` is
recomputed from `+z cross +x`. Zero, parallel, antiparallel, and near-parallel inputs
fail without fallback.

Every logical `BoltLocation.position.x` must equal exactly zero. Its existing `y` and
`z` values create the one master center in the resolved group frame. Duplicate local
`y-z` centers are invalid. The authoritative infinite bolt axis passes through that
master center in group `+x`. Those centers and axes are the canonical source for all
resolved holes; no drawing or layer-specific duplicate becomes authoritative.

## Intended layers and eligible faces

Each `BoltPathDefinition` retains the bolt-location ID and a nonempty declared-order
tuple of `IntendedPenetratedLayer` records. A layer has a path-scoped ID, exact
participant, physical-element ID, distinct entry and exit patch references, nonempty
interface-zone references, and an explicit positive hole diameter in the assembly
length unit. Supports are prohibited as penetrated layers.

An eligible layer resolves both patches from the exact participant's component surface
set. Both patches must be regular, targetable, physical-element-owned planar
rectangles for the named physical element. Entry must be the explicit negative-
thickness broad face with its signed normal opposing bolt `+x`; exit must be the
positive-thickness broad face with its signed normal aligned with bolt `+x`. Entry and
exit are never swapped, repaired, or inferred.

The resolved layer retains the exact placed physical-element occurrence and the exact
comparison-tolerance object used. A participant/physical-element host may occur only
once in one bolt path; duplicating the same convex flat-walled layer under a second
layer ID fails closed.

The axis-plane intersection is analytic. The resolved round hole is one exact cylinder
from the entry intersection to the exit intersection, centered on the authoritative
bolt axis with radius `hole_diameter / 2`. No Boolean solid, permanent mesh, oversized
hole class, countersink, slot, or hardware geometry is created.

## Patch and connection-zone containment

For each rectangular patch intersection, the raw edge clearance is:

```text
min(half_extent_y - abs(local_y), half_extent_z - abs(local_z))
```

The complete disk is contained only when raw clearance plus the explicit distance
tolerance is at least the hole radius. The raw value is retained without clamping,
including accepted values slightly below the radius within the comparison band.

Every layer zone reference names a declared bolt-group interface, canonical first or
second side, and side-scoped zone ID. It must resolve to the layer entry or exit patch.
Whole rectangular patches and rectangular subzones use the same complete-disk rule;
the subzone clearance uses its exact local bounds. Annuli, analytic cylinders, support
surfaces, unrelated interfaces, missing zones, and zones on other patches fail closed.

The primary interface must be represented in every bolt path. Across the resolved
group, the union of referenced interfaces must equal the logical group's interface
tuple exactly. Multi-interface groups retain all logical interfaces, each raw normal
alignment with the primary bolt axis, and each signed plane offset along group `+x`.
Additional normals must be parallel or antiparallel within the explicit angular
tolerance. One canonical axis is used; no independent interface-only center or axis is
created.

## Ordered layer stacks and raw geometry

Layer declaration order is physical and is never replaced by an axis-coordinate sort.
Each layer must have positive entry-to-exit separation. The raw gap between consecutive
layers is:

```text
following.entry_axis_parameter - preceding.exit_axis_parameter
```

A gap below the negative distance tolerance is invalid. A small negative value inside
the explicit comparison band is retained without clamping. Zero and positive gaps are
also retained. The path's `geometric_stack_span` is final exit parameter minus first
entry parameter; it is not a qualified grip length. Different bolt locations may
declare different layer sequences; no group-
wide layer stack is invented.

## Tolerances, units, and exclusions

The Stage 1.3C2B `GeometryComparisonTolerance` is supplied explicitly and has no
default. Its distance value uses the assembly length unit; its angular value is
dimensionless. Neither is the Stage 1.3A mathematical tolerance, a fabrication limit,
fit-up acceptance, or code criterion. Raw clearances, gaps, thicknesses, and spans are
never converted or rounded. The exact `EngineeringUnitSystem` identity is retained;
Stage 1.3C3 performs no unit conversion.

Hardware, washers, nuts, grip, threads, shear planes, bearing eligibility, access,
interference, drilling acceptance, material properties, forces, equilibrium,
distribution, capacities, utilization, source mapping, API, frontend, persistence,
reports, and PASS/FAIL remain unimplemented.
