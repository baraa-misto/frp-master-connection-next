# Coordinate, Material-Axis, and Force Conventions

| Control | Value |
|---|---|
| Stage | 1.3C2A — physical surface patches and bounded support surfaces |
| Status | Approved coordinate/sign/datum/placement/surface conventions implemented; software representation and mathematical tolerance provisional; not frozen |
| Scope | Symbolic and resolved frames, component placement, local y-z section geometry, local-x extrusion, signed geometric surface normals, FRP material-axis families, force/moment transformations, and axial sense |
| Detailed mathematics | `SPATIAL_FRAME_AND_ACTION_TRANSFORM_SPECIFICATION.md` |
| Detailed cross-sections | `STANDARD_CROSS_SECTION_GEOMETRY_SPECIFICATION.md` |
| Detailed placement | `COMPONENT_PLACEMENT_AND_EXTRUSION_SPECIFICATION.md` |
| Detailed surfaces | `PHYSICAL_SURFACE_PATCH_SPECIFICATION.md` |

## Safety boundary

This document controls coordinate, material-axis, and member-on-joint action meaning.
Stage 1.3A implements general finite spatial mathematics and explicit transformation
operations. Stage 1.3B implements exact nominal standard cross-sections in the local
`y-z` plane. Stage 1.3C1 now places member/connector geometry in one proper resolved
global frame, applies an explicit section offset, extrudes along explicit local-x
extents, and identifies physical longitudinal boundary planes. It still implements no
design-code equation, material or section property, joint/interface placement, force
distribution, resistance, capacity, utilization, equilibrium result, or engineering
PASS/FAIL.

The licensed engineering source is not reproduced here. No Stage 1.3A, 1.3B, or
1.3C1 convention is a claim that a calculation method or commercial design capability
is approved.

## Global coordinate frame

The immutable canonical `GLOBAL_FRAME` is right-handed:

```text
origin = (0, 0, 0)
X = (1, 0, 0)
Y = (0, 1, 0)
Z = (0, 0, 1)
X × Y = Z
```

Global X and Y are project horizontal directions. Global Z is vertical upward. The
global origin is not an inferred analytical joint origin.

## Symbolic references and resolved frames

`CoordinateFrameReference` remains the Stage 1.1 symbolic identity/provenance
contract:

| Frame kind | Required owner |
|---|---|
| `GLOBAL` | No owner |
| `JOINT_LOCAL` | The `JointAssembly` |
| `MEMBER_LOCAL` | An `AssemblyMember` |
| `CONNECTOR_LOCAL` | A `ConnectorComponent` |
| `INTERFACE_LOCAL` | A `ConnectionInterface` |
| `BOLT_GROUP_LOCAL` | A `BoltGroup` |

The aggregate validates owner identity. A symbolic reference does not contain an
origin or basis and is not replaced by `CartesianFrame3D`.

`CartesianFrame3D` is resolved geometric data: a finite parent-coordinate origin and
three parent-coordinate unit axes. It is constructible only when its basis is
orthonormal and proper right-handed within the provisional dimensionless mathematical
tolerance. Stage 1.3C1 retains one resolved global frame per separately placed member
or connector but does not add a `JointAssembly` placement registry or resolve every
symbolic frame. Two resolved frames supplied to `transform_between_frames` must share
one common parent coordinate system.

## Member local frame

For start point S, end point E, and explicit local-z reference `vz`:

```text
x_raw = E - S
ex = normalize(x_raw)

z_projected = normalize(vz) - dot(normalize(vz), ex) ex
ez = normalize(z_projected)

ey = normalize(cross(ez, ex))
ez = normalize(cross(ex, ey))
```

`build_member_frame` places the resolved origin at START. Local x always runs START to
END and does not reverse when the member's connected end is END. The final relation is
`cross(ex, ey) = ez`.

The builder rejects coincident points; zero x or z-reference directions; parallel,
antiparallel, and numerically nearly parallel z references; nonfinite values; and an
improper basis. It never silently substitutes a global axis, another reference, or a
prior frame. Any template-supplied z reference must remain explicit traceable input.

## Section plane, datum, and standard orientations

Every Stage 1.3B cross-section lies in the owning component-local `y-z` plane. No
Stage 1.3B section point has an x coordinate. Stage 1.3C1 uses local `x` as the exact
extrusion direction and keeps the source 2D geometry unchanged while associating it
with one explicit extent, offset, and global placement.

The construction datum is `(y=0, z=0)`, exactly the center of the nominal outside
bounding box. This datum is distinct from and does not imply a centroid, shear center,
calculated principal-axis origin, analytical line, joint point, force reference point,
interface, face, hole, or bolt location.

For a standard unrotated W or I section:

- x is member START to END;
- y is flange width; and
- z is web depth.

Thus `Fx` is axial, `Fy` is shear along flange width, `Fz` is shear along web depth,
`Mx` is torsion, `My` is major/strong-axis bending, and `Mz` is minor/weak-axis
bending for that standard W/I datum.

The approved standard orientations for the other Stage 1.3B families are:

| Family | Local-y/local-z convention |
|---|---|
| `CHANNEL` | Depth along z; web on `-y`; opening toward `+y`. |
| `TEE` | Flange on `+z`; stem extends toward `-z`. |
| `RECTANGULAR_TUBE` | Width along y; depth along z; `SIDE_WALL_1` at `-y`, `SIDE_WALL_2` at `+y`. |
| `ANGLE` | `LEG_1` extends toward `+y`; `LEG_2` extends toward `+z`; outside heel is at the negative-y/negative-z corner. |
| `PLATE` | Width along y; thickness along z; placed length follows the explicit Stage 1.3C1 local-x extent. |
| `ROUND_TUBE` | Annulus centered at `(0,0)`; y/z provide geometric clocking only. |

These are controlled construction axes. They are not claimed to be calculated
principal axes for unsymmetrical shapes. The standard channel/tee/angle factories
have one stable orientation and create no hidden mirrored topology. Stage 1.3C1
placement may reorient geometry only through its one approved proper resolved frame;
reflection, scale, shear, skew, and a second roll/mirror state remain prohibited.

For a round tube, x is axial and y/z provide geometric clocking. The exact Stage
1.3C1 annular-cylinder placement does not create a fixed material CW direction around
the circumference or select an evaluation angle.

W/I/channel/tee meeting boundaries, the angle heel, and rectangular-tube corners have
the deferred status defined in the cross-section specification. Their coordinates do
not make them material regions or connection targets.

## Placement reference, offset, and boundary directions

The placed frame's local x axis is the component reference line through local
`(x,0,0)`. The Stage 1.3B construction datum is located through an explicit finite
section offset `(offset_y,offset_z)`, producing the distinct section-datum line through
`(x,offset_y,offset_z)`. A source point `(y,z)` maps to component-local
`(x,y+offset_y,z+offset_z)` and then globally through the one resolved frame. Neither
line is automatically a centroid, shear center, analytical line, joint point, or force
point, and no offset is inferred.

Every placement has exact finite `x_start < x_end`. For a member, START is local
`x=0`, END is local `x=member_length`, and the connected end selects one of those
planes without reversing the frame. For a connector, the supplied interval may
straddle zero and its planes retain neutral minimum/maximum-x identities.

The minimum-x boundary's outward normal is `-local x`; the maximum-x boundary's
outward normal is `+local x`. These are signed global geometric unit normals after
placement. They are not material-property directions, interfaces, connection faces,
force directions, or engineering statuses. Physical longitudinal boundary planes
remain non-targetable in Stage 1.3C1.

Stage 1.3C2A derives exact element-level surface patches without changing those
Stage 1.3C1 plane descriptors. For every planar patch, surface-local +x is its signed
normal and y/z are in-plane. Regular exterior, void-facing, physical end-cut, and
explicit bounded support patches are geometrically targetable. Internal junctions
and all deferred patches are non-targetable. Round-tube outer/inner cylinders use
outward/inward radial normal rules rather than a fixed normal.

## Signed geometric directions and sign-independent material families

Resolved geometric directions are signed:

```text
+x, -x, +y, -y, +z, -z
```

Stage 1.2 material-property identity is sign-independent:

```text
PrincipalAxisFamily.X
PrincipalAxisFamily.Y
PrincipalAxisFamily.Z
```

`+X` and `-X` are the same material family, and likewise for Y and Z. An outward
surface-normal sign does not create another material direction. Tension versus
compression is a loading/property-selection sense, not positive versus negative LW
identity.

Stages 1.3B and 1.3C1 do not alter the Stage 1.2 material topology. A
pultruded-FRP component still owns
one `FRPComponentOrientation` with a matching component-local frame and shared LW
family. Each material region still owns either:

- `PLANAR_FIXED`, with distinct regional CW and TT families that are also distinct
  from LW; or
- `CYLINDRICAL`, with axial LW, circumferential/tangential CW, and radial TT and no
  false fixed Cartesian CW/TT pair.

Separate physical occurrences may share a material region despite opposite future
outward normals. Physical identity remains separate from material identity.

## W/I geometric and material compatibility

For the approved W/I local frame:

| Region | LW | CW | TT |
|---|---|---|---|
| `WEB` | `X` | `Z` | `Y` |
| `FLANGES` | `X` | `Y` | `Z` |

Top and bottom flanges remain separate physical occurrences that may reference the
same `FLANGES` material region. This table confirms direction identity only; it
performs no force sharing, stress, property lookup, resistance, or utilization.

## Point and vector transformation

Let `R` have local `ex`, `ey`, and `ez` as columns and let `o` be the frame origin in
the parent frame:

```text
p_parent = o + R p_local
p_local = transpose(R) (p_parent - o)

v_parent = R v_local
v_local = transpose(R) v_parent
```

Translation affects positions and never free vectors. `Rotation3D` and
`RigidTransform3D` accept proper rotations only. `then(next)` always means apply the
receiver first and `next` second. Inversion uses the rotation transpose and the
corresponding inverse translation.

## Force and moment transformation

At one unchanged physical reference point:

```text
F_parent = R F_local
M_parent = R M_local
```

`rotate_force` and `rotate_moment` use the same proper rotation. Rotation does not
shift the reference point and does not add a moment.

For an explicit transfer from point P to point Q in one identified common frame:

```text
F_Q = F_P
M_Q = M_P + (r_P - r_Q) × F
```

`PointInFrame3D` supplies the position and symbolic frame identity.
`shift_force_moment_reference` requires P and Q to have equal frame references and
rejects a mismatch. It never discovers eccentricity, infers Q, automatically moves an
entered action, distributes force, or calculates interface demand.

## Manual member-end actions and axial sense

`ManualMemberEndAction` preserves all six supplied signed values, the member and load
combination, connected end, symbolic frame, reference point, and
`MEMBER_ON_JOINT` convention. Stage 1.3A transformation functions are explicit pure
operations; storing an action does not transform or shift it automatically.

Because local x remains START to END, axial interpretation is:

| Connected end | `Fx` sign | Member-on-joint sense |
|---|---:|---|
| `START` | positive | `TENSION` |
| `START` | negative | `COMPRESSION` |
| `END` | negative | `TENSION` |
| `END` | positive | `COMPRESSION` |
| Either | zero | `ZERO` |

`interpret_member_end_axial_sense` returns only that controlled sense. It does not
rewrite the supplied sign, reverse the frame, or use a near-zero tolerance.

## Positive and applied directions

`ActionComponent` is exactly `FX`, `FY`, `FZ`, `MX`, `MY`, and `MZ`.

- `FX`, `FY`, and `FZ` are `LINEAR` along resolved +x, +y, and +z.
- `MX`, `MY`, and `MZ` are `ROTATIONAL` with right-hand sense about resolved +x, +y,
  and +z.

`positive_action_direction` exposes the permanent positive axis in parent/global
coordinates. `applied_action_direction` preserves the signed value, uses that axis for
a positive value, reverses it for a negative value, and records an explicit `ZERO`
sense and zero status for zero. Zero retains the canonical positive axis for component
identity and is eligible to be hidden by a renderer.

These immutable results contain no color, arrow length, pixel or screen position,
mesh, camera, tessellation, or display scale. They are reference-point agnostic; the
caller must preserve the action's existing `ReferencePoint` or resolved point
identity.

## Numerical frame inspection and visualization

`FrameInspection3D` exposes origin, parent-coordinate axes, all axis norms, all
pairwise dot products, determinant, right-handed status, orthonormal status, and
combined valid-frame status. These are geometric inspection values, never engineering
PASS/FAIL.

Future positive-convention, applied-action, and section display modes must derive from
the same canonical spatial, cross-section, and Stage 1.3C1 placement objects. Placement
supplies component global position, local axes, START/END and connected-end planes,
component reference line, shifted section-datum line, exact physical/deferred/void
extents, and boundary normals. Display modes must provide local-axis and global-axis
visibility toggles and show frame identity, local axes, optional global axes,
START/END and connected-end markers, reference point, component labels, signed values
and units, reversed negative directions/senses, numerical axes, and handedness and
orthonormality. The frontend must show the applicable arrows before accepting or
saving a force assignment. Section rendering must derive from exact rectangles,
deferred lines/zones, voids, and the analytic annulus; display tessellation must never
replace the annulus. No frontend rendering is implemented in Stage 1.3C1.

## Provisional mathematical tolerance

`DIMENSIONLESS_MATHEMATICAL_TOLERANCE` is `1.0e-12` and remains Provisional. It
controls only unit-vector, orthogonality, determinant, and angular near-parallel
checks. It is not a dimensional geometry, fabrication, fit-up, hole, eccentricity,
material, resistance, or acceptance tolerance.

## Units and explicit deferrals

Positions, translations, cross-section dimensions, placement extents, and section
offsets use the assembly's declared length unit; force and moment use its declared
force and force-length units. Rotations, unit vectors, direction senses, frame
identity, and the mathematical tolerance are dimensionless. A standalone Stage 1.3B
geometry object has no independent unit field; Stage 1.3C1 associates it with one
component and the containing assembly's length basis without conversion. Stages 1.3A
through 1.3C2B do not resolve the future internal canonical-unit policy.

Arbitrary custom section geometry, section properties, cylindrical radial/tangent
evaluation vectors, `JointAssembly` placement, support bodies, cylindrical-side and
deferred-zone targeting, holes and bolts, allowed force reference points per calculation
template, supporting-reaction signs, eccentricity discovery, automatic shifts,
material properties, equations, equilibrium, distribution, capacity, utilization,
persistence, API integration, frontend rendering, and reports remain deferred. Stage
1.3C2B planar interface targets use signed geometric normals only and do not assign
FRP material direction or a force sign.

Stage 1.3C3 now binds all six symbolic frame kinds against one complete exact joint
geometry context. Primary-interface `+x` controls bolt-group and authoritative bolt-axis
`+x`; an explicit projected in-plane direction controls group `+y`, with no fallback.
Flat physical elements expose explicit negative/positive thickness-face roles rather
than deriving them from names or rendering. Hole intersections, layer thicknesses,
clearances, and ordered gaps use the assembly length identity without conversion.

Reference-point mappings preserve the exact joint origin, connected-member physical
section-datum point, interface origin, bolt-group origin, or explicit coordinates in an
explicit bound frame. Manual actions rotate to global at the unchanged point. A caller-
directed shift alone applies `M_Q = M_P + (r_P - r_Q) cross F`; no point, frame,
eccentricity, or action shift is inferred.

## Stage 2.1A unit and directional-property conventions

One Decimal-based physical quantity engine serves two explicit source/display profiles.
Canonical calculation magnitudes are `mm`, `N`, `N-mm`, `MPa`, and dimensionless
`one`; approved exact conversion constants preserve U.S./SI equivalence. A published
U.S. standard-hole increment and a published SI standard-hole increment are distinct
source bases, while the generated physical hole diameter is one authoritative stored
quantity.

For a mapped rectangular FRP layer, the acute in-plane angle between resolved force
and LW selects longitudinal properties through 5 degrees inclusive and transverse
properties above 5 degrees through 90 degrees inclusive. Exactly 90 degrees selects
transverse and retains the `TRANSVERSE_ENDPOINT_INCLUDED` interpretation trace. This
direction selection does not evaluate stress, resistance, capacity, utilization, or
acceptance.

## Directed brace geometry versus material relationship

For the current brace-to-column template, `brace_to_column_directed_angle_deg` is a
directed angle in the verified vertical plane from W-column longitudinal `+x` toward
the established brace approach side. Its strict domain is `0 < theta_g < 180`
degrees. The backend constructs a proper frame; reflection is forbidden and the
connection-side, connected-leg, and outstanding-leg choices remain explicit.

FRP property selection remains sign-independent. The backend resolves
`theta_material = acos(abs(x_brace dot x_column))` in `[0, 90]`, so directed geometry
angles 120, 150, and 175 degrees report material relationships 60, 30, and 5 degrees.
The frontend displays those returned relationships and performs no trigonometry.
Signed applied action labels likewise display the backend snapshot direction/value;
editing changes only the shared source action input and waits for preview resolution.
