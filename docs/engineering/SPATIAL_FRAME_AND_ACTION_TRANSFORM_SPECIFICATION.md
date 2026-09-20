# Spatial Frame and Action Transform Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-002 |
| Stage | 1.3A — spatial mathematics and action-direction contracts |
| Status | Implemented mathematical kernel; controlled engineering conventions; not frozen |
| Spatial implementation | `backend/src/frp_master_connection/geometry/spatial.py` |
| Action implementation | `backend/src/frp_master_connection/actions/transforms.py` |
| Stage 1.3B companion | `STANDARD_CROSS_SECTION_GEOMETRY_SPECIFICATION.md` |
| Stage 1.3C1 companion | `COMPONENT_PLACEMENT_AND_EXTRUSION_SPECIFICATION.md` |
| Calculation engine | Not implemented |
| Engineering rule set | Not implemented |

## Purpose and safety boundary

This specification controls the framework-independent three-dimensional mathematics
used to resolve Cartesian frames, transform points and vectors, rotate forces and
moments, shift a force/moment system between explicitly identified reference points,
interpret connected-end axial sense, and provide renderer-neutral direction data.
The same objects and functions are the future source for calculation and display
directions; a frontend must not implement a parallel sign convention.

Stage 1.3A is a mathematical and geometric-contract stage. This specification itself
does not define section geometry, component placement, force distribution, equilibrium,
stress, resistance, capacity, utilization, a design-code equation, a material property,
or an engineering result. Stage 1.3B defines exact nominal standalone standard
cross-sections, and Stage 1.3C1 now uses this kernel to place and analytically extrude
members and connectors through a separate geometry-layer contract. Neither companion
adds `JointAssembly` placement, interface placement, or calculation authority.
Terms such as *valid frame*, *right-handed*, and *orthonormal* are geometric validation
terms. They are not engineering `PASS`, `FAIL`, adequacy, or design status.

## Existing identity and quantity contracts

Stage 1.3A reuses these existing immutable domain types:

- `PositionVector3D` for a finite position in the owning assembly's length unit;
- `ForceVector3D` for finite force components;
- `MomentVector3D` for finite force-length components;
- `CoordinateFrameReference` for symbolic frame identity and provenance;
- `ReferencePoint` for an existing symbolic or explicit action reference point; and
- `MemberEnd` for `START` or `END` identity.

`Vector3D` is the new finite geometric displacement/direction vector, and
`UnitVector3D` is its unit-length specialization. Neither is interchangeable with a
position, force, or moment. Public typing therefore continues to prevent accidental
substitution among position, geometric vector, force, and moment quantities.

## Symbolic frame reference versus resolved frame

`CoordinateFrameReference` and `CartesianFrame3D` are deliberately different:

| Contract | Meaning |
|---|---|
| `CoordinateFrameReference` | Symbolic identity and owner provenance: `GLOBAL`, `JOINT_LOCAL`, `MEMBER_LOCAL`, `CONNECTOR_LOCAL`, `INTERFACE_LOCAL`, or `BOLT_GROUP_LOCAL` |
| `CartesianFrame3D` | A resolved finite origin and proper right-handed orthonormal basis expressed in one parent coordinate frame |

Stage 1.3A does not replace symbolic references, add coordinates to
`AssemblyMember`, or create a `JointAssembly` registry that resolves all references.
Stage 1.3C1 supplies one resolved global frame per separately placed member or
connector, but still creates no general symbolic-frame or joint-placement registry. A
caller that transforms between two resolved frames is responsible for supplying frames
expressed in the same common parent coordinates.

## Finite spatial values

Every component of `PositionVector3D`, `Vector3D`, `ForceVector3D`, and
`MomentVector3D` must be a finite real number. Boolean values, nonnumeric values,
`NaN`, positive infinity, and negative infinity are rejected. Spatial operations also
reject a result that cannot remain finite in the floating-point range.

`Vector3D` implements immutable Euclidean operations:

```text
u + v
u - v
-u
s u
dot(u, v)
cross(u, v)
norm(u)
normalize(u)
```

`vector_between(A, B)` returns `B - A`. `translate_point(P, d)` returns `P + d`.
A zero vector cannot be normalized. No nonzero displacement is treated as zero by a
hidden length tolerance.

The cross product follows the right-hand rule. In the canonical basis:

```text
ex × ey = ez
ey × ex = -ez
```

The cross product is orthogonal to both operands, subject only to finite
floating-point arithmetic.

## Provisional numerical tolerance

The centralized value is:

```text
DIMENSIONLESS_MATHEMATICAL_TOLERANCE = 1.0e-12
```

Its status is **Provisional**. It is used only for dimensionless mathematical checks:

- whether a supplied unit vector has norm one;
- whether resolved basis axes are mutually orthogonal;
- whether a proper-basis determinant is one;
- whether an explicit z-reference direction is angularly parallel or nearly parallel
  to the local x direction.

The near-parallel comparison is performed after normalization and projection, so the
compared magnitude is a dimensionless angular measure. The tolerance is not a length,
fabrication, fit-up, hole-alignment, eccentricity, acceptance, or engineering design
tolerance. It must not be reused for those purposes without a separate reviewed
decision. Action values use exact sign comparisons; the tolerance never converts a
small nonzero force or moment into zero.

## Approved global frame

The canonical immutable `GLOBAL_FRAME` is:

```text
origin = (0, 0, 0)
X = (1, 0, 0)
Y = (0, 1, 0)
Z = (0, 0, 1)
```

Global X and Y are project horizontal directions. Global Z is vertical upward. The
frame is right-handed because `X × Y = Z`, and it is orthonormal. Its origin is the
canonical global-coordinate origin, not an inferred project-specific joint origin.

## Resolved Cartesian frames and rotations

A `CartesianFrame3D` contains:

- finite parent-coordinate origin `o`;
- local unit x axis `ex` expressed in the parent frame;
- local unit y axis `ey` expressed in the parent frame; and
- local unit z axis `ez` expressed in the parent frame.

The columns of the corresponding `Rotation3D` matrix `R` are `ex`, `ey`, and `ez`.
Construction requires:

```text
norm(ex) = norm(ey) = norm(ez) = 1
dot(ex, ey) = dot(ex, ez) = dot(ey, ez) = 0
det(R) = +1
cross(ex, ey) = ez
```

The comparisons use only the provisional dimensionless tolerance. A scaled, skewed,
reflected, left-handed, nonfinite, or otherwise improper basis is not a
`CartesianFrame3D` or `Rotation3D`.

`IDENTITY_ROTATION` has the canonical X/Y/Z columns. `Rotation3D.then(next)` means
that the receiver is applied first and `next` is applied second. A rotation's inverse
is its transpose.

## Member-frame construction

`build_member_frame(S, E, vz)` is a pure operation. It does not mutate an
`AssemblyMember` and does not add placement to a `JointAssembly`. The Stage 1.3C1
member-placement builder reuses it unchanged and retains its result as the placed
member's one authoritative resolved global frame.

The member frame origin is `START`, and local x is fixed from `START` to `END`:

```text
x_raw = E - S
ex = normalize(x_raw)
```

The explicit local-z reference `vz` is normalized and projected onto the plane
perpendicular to `ex`:

```text
z_projected = normalize(vz) - dot(normalize(vz), ex) ex
ez = normalize(z_projected)
ey = normalize(cross(ez, ex))
ez = normalize(cross(ex, ey))
```

The recomputed `ez` removes accumulated projection error and enforces the approved
right-handed relation `cross(ex, ey) = ez`. `build_cartesian_frame` performs the same
construction from an explicit origin, x direction, and z-reference direction.

The operation rejects:

- coincident START and END points or any zero x direction;
- a zero z-reference direction;
- a z-reference direction parallel, antiparallel, or numerically nearly parallel to
  local x;
- every nonfinite input; and
- any resulting basis that is not proper, right-handed, and orthonormal.

There is no fallback. The operation never silently selects global X, Y, or Z, another
reference vector, or a previously resolved frame. A connection template may provide
the z-reference only as explicit traceable input.

The member-local x axis never reverses because the connected end is `END`. Connected
end affects the interpretation of axial action, not frame construction.

## Member section datum convention

For a standard unrotated W or I section:

- local x is member START to END and the section axial direction;
- local y is the flange-width direction; and
- local z is the web-depth direction.

Therefore:

| Component | Geometric interpretation |
|---|---|
| `Fx` | Axial |
| `Fy` | Shear along flange width |
| `Fz` | Shear along web depth |
| `Mx` | Torsion about local x |
| `My` | Major/strong-axis bending for the standard W/I datum |
| `Mz` | Minor/weak-axis bending for the standard W/I datum |

Stage 1.3B approves exact nominal local-y/local-z construction for channels, tees,
rectangular/square tubes, angles, plates/doublers, and round tubes. These remain
controlled section-datum axes and must not be described as calculated principal axes
for an unsymmetrical shape. Every section datum is the outside-bounding-box center
`(0,0)`, not a centroid, shear center, analytical-line point, joint point, or force
reference point. Stage 1.3C1 uses local x as the exact extrusion direction without
changing these datum meanings.

For a round tube, local x remains axial while y and z provide geometric clocking.
Those axes do not create a fixed material CW direction around the circumference. The
Stage 1.2 cylindrical material-orientation rule remains authoritative.

## Geometric axes and Stage 1.2 material axes

Geometric directions are signed:

```text
+x, -x, +y, -y, +z, -z
```

Material-property axis families remain sign-independent:

```text
X, Y, Z
```

An outward normal's sign does not create another material-property direction, and
tension/compression sense does not change LW identity. Stage 1.3A does not alter
`FRPComponentOrientation`, `SectionTopology`, or regional material-orientation rules.

For the standard W/I datum, the compatible Stage 1.2 representation is:

| Region | LW | CW | TT |
|---|---|---|---|
| `WEB` | `X` | `Z` | `Y` |
| `FLANGES` | `X` | `Y` | `Z` |

This table establishes geometric/material direction identity only. It does not
calculate axial stress, shear stress, force sharing, resistance, or utilization.

## Point and vector transformations

For a resolved frame whose rotation columns are local `ex`, `ey`, and `ez` and whose
parent-coordinate origin is `o`:

```text
p_parent = o + R p_local
p_local = transpose(R) (p_parent - o)

v_parent = R v_local
v_local = transpose(R) v_parent
```

Point transformations include translation. Vector transformations do not.
`CartesianFrame3D.local_to_parent_point`, `parent_to_local_point`,
`local_to_parent_vector`, and `parent_to_local_vector` implement these equations.
The operations are invertible up to finite floating-point roundoff.

## Rigid transforms

`RigidTransform3D` contains one proper `Rotation3D` and one finite parent-coordinate
translation. It supports points, vectors, inversion, composition, and round trips.
`RigidTransform3D.then(next)` applies the receiver first and `next` second; operation
order is therefore explicit rather than inferred.

`transform_between_frames(source, target)` maps source-local coordinates to
target-local coordinates. Both resolved frames must be expressed in the same common
parent frame. Stage 1.3A has no parent-frame registry and does not infer or verify that
external placement precondition.

No spatial contract supports scale, reflection, shear/skew, projective behavior, or a
nonorthogonal coordinate basis.

## Force and moment rotation

At the same physical reference point, force and moment use the same proper rotation:

```text
F_parent = R F_local
M_parent = R M_local
```

`rotate_force` and `rotate_moment` preserve the distinct public force and moment
types. Rotation alone does not add an eccentricity moment. Translation is not applied
to either vector merely because their coordinates are rotated.

## Explicit reference-point shifting

`PointInFrame3D` associates an existing finite position with one
`CoordinateFrameReference`. `ForceMomentSystem3D` associates a force and moment with
one such point. These wrappers identify the common coordinate frame; they do not
resolve symbolic points through a `JointAssembly`.

For the same physical force/moment system moved from point P to point Q, with every
point and component expressed in one identified common frame:

```text
F_Q = F_P
M_Q = M_P + (r_P - r_Q) × F
```

The offset is exactly `r_P - r_Q`. `shift_force_moment_reference` rejects P and Q
whose `CoordinateFrameReference` values differ. It does not infer Q, automatically
move entered actions, distribute force, resolve an interface, or calculate demand.

Canonical sign check:

```text
P = (a, 0, 0)
Q = (0, 0, 0)
F = (0, Fy, 0)
M_P = (0, 0, 0)

M_Q = (0, 0, a Fy)
```

Reversing the eccentricity reverses the added z moment. Shifting from P to Q and back
recovers the original force/moment system within finite floating-point roundoff.

## Connected-end axial sense

`interpret_member_end_axial_sense` applies only to the approved
`MEMBER_ON_JOINT` perspective. It returns exactly `TENSION`, `COMPRESSION`, or `ZERO`
without changing the stored `Fx` value or reversing the member frame.

| Connected end | `Fx` sign | Member-on-joint axial sense |
|---|---:|---|
| `START` | `Fx > 0` | `TENSION` |
| `START` | `Fx < 0` | `COMPRESSION` |
| `END` | `Fx < 0` | `TENSION` |
| `END` | `Fx > 0` | `COMPRESSION` |
| Either | `Fx = 0` | `ZERO` |

Positive `Fx` is therefore not automatically tension at both ends. No action-value
tolerance is applied to this interpretation.

## Canonical positive action directions

`ActionComponent` contains exactly `FX`, `FY`, `FZ`, `MX`, `MY`, and `MZ`.
`ActionDirectionKind` contains exactly `LINEAR` and `ROTATIONAL`.

For a resolved frame:

| Component | Kind | Permanent positive direction in parent coordinates |
|---|---|---|
| `FX` | `LINEAR` | local `+x` axis |
| `FY` | `LINEAR` | local `+y` axis |
| `FZ` | `LINEAR` | local `+z` axis |
| `MX` | `ROTATIONAL` | right-hand rotation about local `+x` |
| `MY` | `ROTATIONAL` | right-hand rotation about local `+y` |
| `MZ` | `ROTATIONAL` | right-hand rotation about local `+z` |

`positive_action_direction` returns immutable `PositiveActionDirection3D` containing
the component, kind, and positive unit axis expressed in the frame's parent
coordinates.

## Applied action directions

`applied_action_direction` returns immutable `AppliedActionDirection3D`. The result
retains component, direction kind, exact signed value, parent-coordinate unit axis,
`POSITIVE`/`NEGATIVE`/`ZERO` sense, and explicit zero status:

- a positive value uses the permanent positive axis;
- a negative value reverses the axis, including rotational right-hand sense;
- a zero value retains the canonical positive axis for identity but has `ZERO` sense
  and `is_zero = true`, so a renderer may hide it; and
- the signed numerical value remains authoritative.

The contract contains no pixel or world-display length, color, screen coordinate,
mesh, tessellation, camera, graphic style, or display scale. Changing graphic scale
must never change an action value.

The direction result is reference-point agnostic. A caller must preserve the existing
`ReferencePoint` or resolved point identity associated with the action; the direction
function never invents one.

## Frame inspection

`inspect_cartesian_basis` and `FrameInspection3D` provide immutable numerical data for
engineering review and future rendering:

- origin and all three axes in parent/global coordinates;
- x, y, and z norms;
- x-y, x-z, and y-z dot products;
- determinant;
- right-handed status;
- orthonormal status; and
- combined valid-frame status.

Inspection can report invalid raw basis data, but invalid data cannot be constructed as
a `CartesianFrame3D` or `Rotation3D`. The future interface can therefore show both a
graphical triad and numerical evidence without calling the result engineering PASS or
FAIL.

## Mandatory future visualization behavior

Stage 1.3A draws no graphics. The following future behavior is mandatory before manual
force entry is considered complete:

### Positive sign-convention mode

- independent local-axis and global-axis visibility toggles;
- straight arrows for `+Fx`, `+Fy`, and `+Fz`;
- right-hand curved arrows for `+Mx`, `+My`, and `+Mz`;
- local-axis triad and optional global-axis triad;
- component labels, frame identity, and reference-point marker;
- START, END, and connected-end markers where applicable; and
- numerical global/parent components of local axes with handedness and orthonormality.

These arrows remain fixed when entered values change.

### Applied-action mode

- actual signed force and moment arrows for the selected load combination;
- reversed arrow direction or rotational sense for negative values;
- signed values and units;
- selected coordinate frame and reference-point marker;
- connected member end and derived member-local axial sense;
- a zero-value visibility option; and
- selected-member-only or all-member display.

The same canonical direction data must support 3D and applicable 2D views. The display
must update before the user accepts or saves a force assignment. Frontend rendering,
load-entry controls, Canvas/SVG/Three.js integration, and API serialization are not
implemented in Stage 1.3A.

## Stage 1.3B and Stage 1.3C1 compatibility

`CrossSectionGeometry2D` remains standalone component-local geometry with no resolved
parent/global frame. Its local y and z coordinates use the same signed axes controlled
here. Stage 1.3C1 places it only through one explicit proper resolved global
`CartesianFrame3D` tied to one member or connector in a separate immutable placement
object. Scale, reflection, shear/skew, projective transforms, and silent mirroring
remain prohibited.

The Stage 1.3B construction datum is not automatically the component-frame origin or an
action reference point. Stage 1.3C1 preserves that identity through an explicit finite
local-y/local-z section offset. The frame's x axis defines a component reference line
through local `(x,0,0)`; the shifted section-datum line passes through
`(x,offset_y,offset_z)`. Zero offset establishes only coincidence of those two
geometric lines, not a centroid, shear center, analytical line, joint point, or force
point. Geometry placement cannot cause a force/moment reference-point shift.

Section point `(y,z)` at local x maps first to `(x,y+offset_y,z+offset_z)` and then to
global coordinates through that one frame. The inverse mapping preserves x and
subtracts the offset from local y/z; it does not project or clamp. Member START maps
to the minimum-local-x plane with outward normal `-local x`; END maps to the
maximum-local-x plane with outward normal `+local x`. The connected-end plane is
selected from `AssemblyMember.connected_end` without reversing the frame or action.
Connector boundaries retain neutral minimum/maximum identities.

Physical rectangles, deferred rectangles, deferred lines, rectangular voids, and the
analytic annulus are extruded through exact renderer-neutral prism, ruled-surface,
void-prism, and annular-cylinder descriptors. No permanent mesh or Boolean solid is
created. The same resolved frame controls section clocking; no second roll or mirror
state exists.

## Explicit deferrals

This Stage 1.3A spatial specification does not itself implement:

- local-x placement data or extrusion descriptors; Stage 1.3C1 supplies those in its
  separate companion geometry contract;
- interface, connection-face, hole, bolt, bolt-group, force-reference, or
  `JointAssembly` placement;
- a frame-reference registry or automatic symbolic-to-resolved-frame lookup;
- interface-face identity, bolt penetration, eccentricity discovery, or automatic
  reference-point shifting;
- section or material properties, qualified manufacturer data, directional property
  lookup, or material transforms;
- load combinations, reactions, equilibrium, force or bolt-group distribution,
  stress, design-code equations, resistance factors, time-effect factors, capacity,
  utilization, or engineering PASS/FAIL;
- persistence, API endpoints or schemas, frontend implementation, report generation,
  or network/file-system behavior; or
- Stage 1.3C2 face targeting, Stage 1.3C3-or-later hole/bolt placement, or
  force-reference/eccentricity integration specifically in Stage 1.3C3.

These exclusions do not weaken the approved spatial and sign conventions. They keep
the mathematical kernel separate from the Stage 1.3C1 placement layer and calculation
authority.

Stage 1.3C2B reuses `Vector3D`, `UnitVector3D`, and `CartesianFrame3D` to construct one
interface-local frame. Its `+x` is the first target-side signed normal, `+y` is the
projection of an explicit caller-supplied in-plane reference, and `+z = +x cross +y`.
Zero and near-parallel references fail with no fallback. Its explicit distance/angular
comparison contract is separate from the Stage 1.3A mathematical tolerance. This frame
contains no action, reference-point selection, force shift, or calculation.

## Stage 1.3C3 resolved-context integration

Stage 1.3C3 reuses this kernel unchanged to bind symbolic joint/member/connector/
interface/bolt-group frames, resolve physical reference points, rotate exact manual
actions to global coordinates at their unchanged points, and perform an explicit shift
only after source point, target point, output frame reference, and exact output frame
are supplied. The complete transform trace retains both points, raw source-minus-target
offset, force, source moment, cross-product contribution, shifted moment, and unit
identity. It adds no automatic reference selection or engineering calculation.
