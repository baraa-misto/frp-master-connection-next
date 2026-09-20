# Interface Targeting and Connection Zone Specification

## Status and purpose

This Stage 1.3C2B specification controls renderer-neutral planar interface targeting.
It defines bounded selections on the Stage 1.3C2A surface patches, participant-safe
multi-patch target sides, an explicit interface datum and local Cartesian frame, and
signed plane-separation data. It is geometry support only. It implements no contact,
fit, force, bolt, capacity, utilization, design-code equation, or engineering result.

## Logical interface and geometric targeting

The immutable domain `ConnectionInterface` remains the logical relationship. Its
`participant_a`, `participant_b`, transfer intent, ID, and label are unchanged. A
separate `ConnectionInterfaceGeometrySpecification` retains that exact object and adds
first- and second-side surface selections. Resolution creates a
`ResolvedConnectionInterfaceGeometry`; it never writes exact surfaces into the logical
domain entity and never invents a connection template.

Participant order is canonical. The first side must equal `participant_a`; the second
must equal `participant_b`. Resolution neither swaps participants nor reverses sides.

## Authoritative surface resolution

Every connection zone retains one exact participant-scoped `SurfacePatchReference`.
The caller supplies an immutable tuple of authoritative Stage 1.3C2A `SurfacePatch3D`
objects. A reference must resolve exactly once by participant and patch ID. Missing,
duplicate, wrong-participant, deferred, internal-junction, non-targetable, unsupported,
and analytic-cylinder targets fail closed. The resolved zone retains the exact source
patch; it does not duplicate surface geometry.

A bounded support surface created by `create_bounded_support_surface` participates in
the same resolution path without a component body, thickness, material, stiffness, or
anchor model.

## Connection zones

Zone IDs are stable only within one target side. The same ID may occur on the other
side or another interface. Labels and source references remain explicit, and resolved
zones use deterministic lexicographic ID order.

Exactly two zone kinds exist:

- `WHOLE_PATCH` selects one complete targetable planar rectangle or planar annulus.
- `RECTANGULAR_SUBZONE` selects exact bounds in one planar rectangle's source-frame
  local `y-z` coordinates.

A whole-patch zone has no additional geometry parameters. It is prohibited on analytic
cylinders, deferred patches, internal junctions, and any non-targetable patch.

A rectangular subzone declares finite `min_y`, `max_y`, `min_z`, and `max_z`, with
strictly positive spans. Bounds must lie exactly within the source rectangle's half
extents. There is no tolerance, coordinate exchange, clamping, rounding, or implicit
centering in this check. Rectangular subzones are prohibited on annuli. Stage 1.3C2B
supports a round-tube annular end only as one whole patch; annular sectors and radial or
circumferential subzones remain deferred.

On one rectangular patch, subzone interiors may not overlap with positive area. Exact
edge, line, and point touching are permitted. A whole-patch zone is exclusive on its
patch. Duplicate zone geometry is rejected.

## Multi-patch target sides and primary zone

An `InterfaceTargetSideSpecification` contains one participant, a nonempty zone tuple,
and exactly one primary-zone ID. Zone IDs must be unique and every zone must reference
the side participant. Multiple distinct, disconnected patches are retained; they are
not merged and need not form one continuous polygon.

The primary zone supplies only the primary plane and source surface frame. It does not
mean governing contact, demand, load path, structural priority, largest area, section
centroid, or bolt-group center.

All zones on one side must be planar, have the primary zone's signed normal direction,
and be coplanar with its plane. With the caller's explicit tolerance, same-direction
comparison uses `1 - dot(n_primary, n_zone)` and coplanarity uses the absolute signed
normal offset from the primary plane. Normals are never averaged or flipped.

Examples of full-end multi-patch sides are:

- W/I: separate web, top-flange, and bottom-flange physical end patches;
- rectangular tube: four separate wall end patches, excluding all deferred corner
  end patches;
- tee: separate stem and flange end patches.

Separate physical patch identity remains visible even where patches are coplanar and
adjacent.

## Explicit geometric-comparison tolerance

`GeometryComparisonTolerance` is immutable and has no defaults. The caller must supply
a finite, strictly positive `distance_tolerance` and `angular_tolerance`; booleans are
not real-number inputs. The distance value uses the assembly's common coordinate length
unit. The angular value is dimensionless. Neither is converted, rounded, clamped, or
replaced with the Stage 1.3A dimensionless mathematical tolerance.

These values are comparison aids, not fabrication tolerances, fit criteria, code limits,
or engineering acceptance criteria.

## Opposing sides and signed plane separation

The second primary surface normal must oppose the first primary normal, evaluated by
`1 + dot(n_first, n_second) <= angular_tolerance`. Same-direction and oblique sides are
rejected. No second-side normal is silently reversed.

Signed plane separation is retained exactly as:

```text
dot(second_primary_plane_point - first_primary_plane_point, first_normal)
```

The first normal is consistent with “toward the second side” only when the raw value is
at least the negative distance tolerance. A small negative value within that comparison
band is retained without clamping. `is_coincident_within_tolerance` means only that the
raw absolute separation does not exceed the supplied distance tolerance. Positive or
near-zero values are not called contact, fit, interference, bearing, or adequacy.
In-plane translation of either plane point does not alter separation.

## Explicit interface origin

`InterfaceOriginSpecification` names the primary first-side zone and supplies finite
local `y` and `z` coordinates in its exact source surface frame. The resolved global
origin is constructed directly from the surface origin and axes. It is never projected
from an arbitrary point or inferred from a centroid, shear center, section datum, bolt
group, joint point, or member reference line.

The datum may lie outside the selected zone and outside the material footprint. In
particular, the center of a whole round-tube annular end is a valid interface datum even
though it lies in the void.

## Interface-local frame

The resolved frame is a proper right-handed `CartesianFrame3D`:

- local `+x` is the first-side primary signed normal and therefore follows the canonical
  first-to-second participant convention;
- local `+y` is the normalized projection of the caller's explicit in-plane reference
  into the plane normal to `+x`;
- local `+z` is `normalize(+x cross +y)`, followed by recomputation of `+y` as
  `normalize(+z cross +x)` to remove numerical drift.

Zero, parallel, antiparallel, and near-parallel reference directions are rejected using
the supplied dimensionless angular tolerance. Distance tolerance is not used for that
decision. There is no global-axis, camera-axis, participant-role, or other fallback.
Proper rotation and translation transform the origin and axes consistently without
changing the underlying interface meaning.

## Renderer-neutral inspection and future visualization

The resolved aggregate retains the exact logical interface, participants, target sides,
source zones and references, interface frame, raw signed plane separation, normals, and
comparison tolerance. A future UI must be able to select and highlight each participant,
patch, zone, primary zone, origin, local triad, and separation. It must display canonical
patch/component/physical-element identity, signed normal, targetability, deferred state,
zone bounds, and participant order. Display state cannot alter any canonical value or
imply calculation support.

## Geometry/calculation boundary and deferrals

APR-022 remains controlling: a geometrically resolvable target is not a supported
calculation. Stage 1.3C2B deliberately does not implement:

- analytic cylindrical-side zones, cylindrical strips, circumferential positions,
  meshes, or partial annular sectors;
- arbitrary polygons, circular zones, splines, Boolean zones, or merged contact regions;
- contact, fit, interference, tolerances for fabrication, bearing, pressure, friction,
  stiffness, overlap adequacy, or collision;
- holes, bolt axes, bolt groups, penetrated layers, drilling permission, anchors, or
  concrete breakout;
- forces, moments, load combinations, force reference points, eccentricity discovery,
  action transfer, demand distribution, capacities, utilization, or PASS/FAIL;
- API serialization, frontend implementation, persistence, reports, or calculation
  support declarations.

Stage 1.3C3 now consumes these exact resolved interfaces and zones. One declared primary
interface supplies bolt-group origin and axis orientation. Each intended penetrated
layer names connection zones on its entry or exit face; a complete round-hole disk must
be contained in every referenced whole rectangle or rectangular subzone. The primary
interface appears in every path, and a multi-interface group represents exactly all
logical group interfaces across its paths. Targeting remains geometry only and creates
no contact, drilling acceptance, bolt demand, capacity, or result.

## Stage 2.3R3 semantic template targets

The brace-to-column-flange template resolves semantic `EXTERIOR` and `WEB_SIDE`
choices from canonical W topology, not from camera direction, global orientation,
color, or frontend meshes. Exterior contact binds the exact outer negative
crosswise flange strip; web-side contact binds the exact inner negative crosswise
flange strip. The chosen angle leg and W strip remain separate canonical
participants with stable patch, zone, role, and physical-element identities.

Interface-local positive/negative z identifies the two discrete outstanding-leg
clocking alternatives. It is an engineering geometry input rather than a renderer
flip. A selected contact zone provides highlighting and inspection data only; it
does not establish fit, resistance, utilization, or general contact analysis.
