# Joint Geometry, Reference Point, and Eccentricity Specification

| Control | Value |
|---|---|
| Stage | 1.3C3 — resolved frame bindings, reference points, and explicit transforms |
| Status | Implemented geometry/action contract; locally validated; not frozen |
| Joint context | `backend/src/frp_master_connection/geometry/joint_context.py` |
| Action resolution | `backend/src/frp_master_connection/actions/reference_resolution.py` |
| Calculation support | Not implemented |

## Purpose and boundary

This specification controls exact symbolic-frame binding, physical reference-point
resolution, manual-action spatial resolution, and caller-directed eccentricity
transforms. It preserves original logical identity and provenance. It does not choose
a calculation-template reference point, discover a load path, automatically shift an
entered action, distribute demand, calculate equilibrium, or produce a result.

## Resolved frame bindings

`ResolvedFrameBinding` always retains the original `CoordinateFrameReference`, exact
context-owned `CartesianFrame3D`, and exact logical owner. The global binding uses the
canonical `GLOBAL_FRAME` and has no owner. Joint, member, connector, interface, and
bolt-group references must name an object in the exact assembly context. Missing,
wrong-owner, cross-assembly, incomplete, and duplicate bindings fail closed. A copied
numerically equal frame is not substituted for the context's exact frame.

## Reference-point resolution

`ResolvedReferencePointGeometry` retains the original `ReferencePoint`, global
position, source symbolic frame, exact source frame, controlled provenance, exact
owner, and the member connected-end boundary when applicable.

The controlled mappings are:

| Reference kind | Exact physical position |
|---|---|
| `JOINT_ORIGIN` | The explicit joint-local resolved frame origin for the named assembly |
| `MEMBER_CONNECTED_END` | The placed member's exact connected physical boundary-plane section-datum point |
| `INTERFACE_ORIGIN` | The resolved interface-local frame origin |
| `BOLT_GROUP_ORIGIN` | The resolved bolt-group frame origin |
| `EXPLICIT_POINT` | The stored coordinates transformed from an explicit caller-supplied symbolic/exact frame binding |

The member connected-end point is not the component reference-line point unless the
explicit section offset makes them coincident. START/END identity and the exact
`PhysicalLongitudinalBoundaryPlane3D` remain traceable. An explicit point has no
implicit global default; its binding must contain the same exact reference-point object
and the exact context frame named by its symbolic frame reference.

## Manual member-end action resolution

`resolve_manual_member_end_action` accepts only an exact assembly-owned
`ManualMemberEndAction`. It retains the exact action, member, load combination,
original frame reference, resolved frame binding, original reference point, resolved
physical point, unit-system identity, and original signed values through the logical
action object.

Force and moment are rotated from the declared resolved frame to global coordinates at
the unchanged physical point:

```text
F_global = R_frame_to_global F_authored
M_global_at_P = R_frame_to_global M_authored_at_P
```

No translation or eccentricity term is applied during action resolution. Connected-end
axial sense is derived only when the authored frame is the same member's local frame;
other frames receive no invented axial label.

## Explicit eccentricity transform

`shift_resolved_manual_action` is a separate caller-directed operation. The caller
supplies an already resolved source action, an explicit resolved target point, an
output `CoordinateFrameReference`, and the exact context-resolved output frame.
Nothing selects a target point or output frame automatically.

Global source vectors and both global positions are first expressed in the one output
frame. The raw offset and shifted system are then:

```text
r = r_P - r_Q
F_Q = F_P
M_Q = M_P + r cross F
```

The immutable `ExplicitEccentricityTransform` retains the source action and source
point, target point, symbolic/exact output frame, both output-frame positions, raw
source-minus-target offset, force, source moment, eccentricity moment, shifted moment,
and unit-system identity. Zero eccentricity remains an explicit zero cross product.
Transforming the same physical vectors through another proper output frame changes
components but not the physical system.

## Tolerances, units, and provenance

Reference-point resolution uses exact ownership and the existing resolved spatial
mathematics. It does not apply a distance tolerance, project a point, clamp an offset,
or round coordinates. Force, moment, and length values retain the assembly's declared
unit-system identity. No unit conversion occurs.

The Stage 1.3A dimensionless mathematical tolerance remains limited to proper-frame
mathematics. The Stage 1.3C2B/C3 explicit geometry comparison tolerance applies only
where the bolt/hole geometry specification says so. Neither value is an eccentricity,
fabrication, fit, or engineering acceptance tolerance.

## Explicit exclusions

Template-permitted force points, automatic reference selection, automatic action
transport, reaction signs, load paths, equilibrium, action aggregation, bolt demand
distribution, prying, contact, stiffness, resistance, capacities, utilization,
engineering statuses, source mappings, serialization, API, frontend visualization,
persistence, fingerprints, and reports remain unimplemented. PEN-ENG-005 remains open:
Stage 1.3C3 resolves explicitly supplied points but does not approve which points any
future calculation template permits.
