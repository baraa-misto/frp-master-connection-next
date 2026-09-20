# Engineering Domain Contracts

| Control | Value |
|---|---|
| Stage | 1.3C2A — physical surface patches and bounded support surfaces |
| Status | Implemented geometry contracts; approved coordinate, datum, placement, nominal geometry, surface, and targetability conventions; provisional software representation; not frozen |
| Executable boundaries | `backend/src/frp_master_connection/domain/`, `geometry/`, and `actions/` |
| Spatial module | `backend/src/frp_master_connection/geometry/spatial.py` |
| Section geometry module | `backend/src/frp_master_connection/geometry/section.py` |
| Placement geometry module | `backend/src/frp_master_connection/geometry/placement.py` |
| Surface geometry module | `backend/src/frp_master_connection/geometry/surfaces.py` |
| Action module | `backend/src/frp_master_connection/actions/transforms.py` |
| Calculation engine | Not implemented |
| Engineering rule set | Not implemented |

## Purpose and authority

Stage 1.3C2A preserves the immutable Stage 1.1 joint-assembly, Stage 1.2 symbolic
section-topology, Stage 1.3A spatial/action, and Stage 1.3B exact nominal
cross-section contracts. It adds authoritative framework-independent placement of a
member or connector through one proper resolved global frame, one explicit local-x
extent, one explicit local-y/local-z section offset, exact analytic extrusion
descriptors, and physical longitudinal boundary planes. It adds no `JointAssembly`
placement registry, section property, material value, interface target, force-point
placement, or connection calculation.

The approved global/member-axis, member-on-joint sign, cross-section datum, standard
orientation, nominal sharp-corner, and analytic-annulus conventions now have exact
software meaning. That approval does not approve a source mapping, effective section
model, applicability rule, material rule, design-code equation, resistance, force
distribution, joint equilibrium method, result status, or commercial use. The
controlled decision register remains authoritative for decision IDs and status. The
dimensionless mathematical tolerance and exact software representation choices remain
Provisional and cannot become engineering acceptance criteria by implication.

## Framework-independent implementation

The public framework-independent boundaries are `frp_master_connection.domain`,
`frp_master_connection.geometry`, and `frp_master_connection.actions`. Their
implementation uses only Python standard-library modules and other core packages and
has no import from FastAPI, HTTPX, Pydantic, SQLAlchemy, Alembic, psycopg, Starlette,
Uvicorn, or an application, API, infrastructure, reporting, or security package. An
AST-based test enforces that boundary recursively.

All values, entities, geometry records, factory outputs, aggregate collections, and validation issues are immutable.
Collections must be tuples; callers are not silently coerced from mutable lists.
Controlled vocabularies are string enums, and arbitrary strings are rejected at the
domain boundary.

## Unit-system identity

Each `JointAssembly` declares exactly one `EngineeringUnitSystem`:

| System | Length | Force | Moment | Stress |
|---|---|---|---|---|
| `SI` | millimetre (`mm`) | newton (`N`) | newton-millimetre (`N-mm`) | megapascal (`MPa`) |
| `US_CUSTOMARY` | inch (`in`) | pound-force (`lbf`) | pound-force-inch (`lbf-in`) | pounds per square inch (`psi`) |

Every numeric position, translation, cross-section dimension, placement extent/offset,
force, and moment value associated with an assembly is interpreted in the declared
system's corresponding base. Stages 1.3A through 1.3C1 perform no conversion and do
not accept or infer per-field unit overrides. Callers must not mix systems within one
assembly. A standalone Stage 1.3B geometry object has no independent unit field;
Stage 1.3C1 placement associates it with one component and one assembly length basis
without adding a second unit field. This per-assembly input identity does not resolve
PEN-ENG-006 or select the future calculation engine's internal canonical-unit policy.

## Stable identifiers and labels

- Entity identifiers are case-sensitive, nonempty ASCII tokens of at most 128
  characters. They start with a letter or digit and may then contain letters, digits,
  hyphens, underscores, periods, or colons.
- Human-readable labels are separate, nonblank values of at most 256 characters and
  contain no control characters.
- IDs are unique within every top-level aggregate collection.
- Under PRV-028, the assembly and all top-level entity collections share one global ID
  namespace so cross-kind collisions fail validation.
- Bolt-location IDs are scoped to their owning bolt group and must be unique within
  that group.
- Physical-section-element and material-region IDs are scoped to their owning member
  or connector topology. Identical IDs in different components are valid.
- Stage 1.3B physical geometry and Stage 1.3C1 placed/extruded geometry retain those
  existing scoped element IDs and create no parallel element identity. Deferred-feature
  and void IDs are unique within one cross-section geometry but are not physical-element
  or material-region IDs.
- Every element references one region in the same topology; unresolved references,
  duplicate scoped IDs, and orphan regions are deterministic validation issues.
- No ID, label, tuple, vector, or supplied sign is rewritten during construction or
  validation.

## Value contracts

`PositionVector3D`, `ForceVector3D`, and `MomentVector3D` remain distinct immutable
types. `Vector3D` is a separate finite geometric displacement/direction vector, and
`UnitVector3D` requires norm one within the provisional dimensionless mathematical
tolerance. Every component must be a finite real number; Boolean, NaN, and infinite
values are rejected. No public type permits a position, geometric vector, force, or
moment to be substituted for another.

`Vector3D` supplies addition, subtraction, negation, scalar multiplication, dot
product, cross product, Euclidean norm, and normalization. `vector_between(A, B)` is
`B - A`; `translate_point(P, d)` is `P + d`. Zero-vector normalization and every
nonfinite input or result are rejected. These are geometric operations, not a unit
conversion or engineering calculation.

`CoordinateFrameReference`, `ReferencePoint`, `FRPComponentOrientation`, and the
material-orientation rules carry explicit symbolic identities. Their ownership and
axis-family rules are controlled in
`COORDINATE_MATERIAL_AXIS_AND_FORCE_CONVENTIONS.md`.

`SignedPrincipalAxis` remains the signed geometric-axis vocabulary. The separate
`PrincipalAxisFamily` vocabulary contains exactly `X`, `Y`, and `Z` for
sign-insensitive material-direction classification. Thus `+X` and `-X` map to the
same material axis family without defining tensile or compressive behavior.

## Resolved spatial contracts

`CoordinateFrameReference` remains symbolic identity/provenance. It is not replaced
by `CartesianFrame3D`, which contains an actual finite origin and right-handed
orthonormal unit basis expressed in one parent frame. Stage 1.3C1 retains one resolved
global `CartesianFrame3D` for each separate placed member/connector, but adds no
assembly registry that resolves all symbolic frame identities.

`Rotation3D` is proper and right-handed; scale, reflection, shear/skew, projective
behavior, and nonorthogonal bases are rejected. `RigidTransform3D` combines one such
rotation with a translation. Points receive both rotation and translation, while
vectors receive rotation only. Inversion and `then(next)` composition are immutable;
`then` explicitly applies the receiver first and `next` second.

The canonical immutable `GLOBAL_FRAME` has origin `(0, 0, 0)` and exact +X, +Y, and
+Z axes, with +Z vertical upward. `build_member_frame` uses START as origin, START to
END as local x, and an explicit local-z reference. It projects that reference normal
to x, constructs `y = normalize(z × x)`, and recomputes
`z = normalize(x × y)`. Coincident endpoints, zero input directions, parallel or
nearly parallel references, and improper bases are rejected without fallback.

`FrameInspection3D` derives origin, axes, norms, pairwise dot products, determinant,
right-handed status, orthonormal status, and valid-frame status. These are numerical
geometric diagnostics rather than engineering PASS/FAIL.

`DIMENSIONLESS_MATHEMATICAL_TOLERANCE` is exactly `1.0e-12` and remains
Provisional. It applies only to unit-vector, orthogonality, determinant, and angular
near-parallel checks. It is not a length, fit-up, fabrication, hole-alignment,
eccentricity, resistance, or acceptance tolerance.

Detailed formulas and construction order are controlled by
`SPATIAL_FRAME_AND_ACTION_TRANSFORM_SPECIFICATION.md`.

## Action transformation and direction contracts

At an unchanged physical reference point, `rotate_force` and `rotate_moment` apply
the same proper rotation and no translation. `PointInFrame3D` associates an existing
position with one symbolic frame, while `ForceMomentSystem3D` associates force and
moment with one such point.

`shift_force_moment_reference` implements only the explicit common-frame operation:

```text
F_Q = F_P
M_Q = M_P + (r_P - r_Q) × F
```

The two points must carry equal `CoordinateFrameReference` values. The operation does
not discover eccentricity, choose Q, resolve a symbolic point, distribute force, or
calculate interface demand.

`interpret_member_end_axial_sense` returns exactly `TENSION`, `COMPRESSION`, or
`ZERO` under the `MEMBER_ON_JOINT` convention. Because local x is fixed START to END,
START with positive `Fx` and END with negative `Fx` are tension; the opposite signs
are compression. The original sign is preserved.

`ActionComponent` is exactly `FX`, `FY`, `FZ`, `MX`, `MY`, and `MZ`.
`PositiveActionDirection3D` exposes the permanent positive local-axis/right-hand
direction in parent coordinates. `AppliedActionDirection3D` preserves the exact
signed value, reverses the axis for a negative value, and records explicit zero
status. These records contain no graphic styling or scale and do not invent a
reference point.

## Entity contracts

| Entity | Preserved Stage 1.1/1.2 content and local invariants |
|---|---|
| `AssemblyMember` | Existing identity/classification plus required `FRPComponentOrientation` and `SectionTopology` for pultruded FRP; non-FRP topology remains optional |
| `ConnectorComponent` | Existing identity/classification with the same explicit topology and material-orientation behavior as members; connector kind does not silently create topology |
| `AssemblySupport` | ID, label, and concrete/foundation/other classification |
| `ParticipantReference` | Typed reference to a member, connector component, or support |
| `ConnectionInterface` | Two distinct typed participants and declared `SHEAR_ONLY` or `MOMENT_RESISTING` transfer intent |
| `BoltLocation` | ID and finite position in its owning bolt group's local frame |
| `BoltGroup` | Matching local frame, group origin or explicit reference point, one or more distinct interface IDs, and one or more locations |
| `LoadCombination` | ID, label, and the only admitted Stage 1.1 basis: `FACTORED_STRENGTH` |
| `ManualMemberEndAction` | ID, member and connected-end identity, load-combination ID, frame, reference point, three forces, three moments, and the only admitted convention: `MEMBER_ON_JOINT` |

## Section topology and material regions

`SectionTopology` stores immutable tuples of `PhysicalSectionElement` and
`MaterialRegion`. A physical element is one occurrence that later may own geometry,
faces, holes, penetrations, interfaces, demands, dimensions, and visualization
identity. A material region is not geometry; it groups one or more occurrences that
share the same material basis and orientation rule. Membership exists only on the
element through `material_region_id`, so there is no second membership list.

The explicit standard factory supports `WIDE_FLANGE`, `I_SECTION`, `CHANNEL`, `TEE`,
`RECTANGULAR_TUBE`, `ANGLE`, `PLATE`, and `ROUND_TUBE`. W/I/channel topology preserves
separate `WEB`, `TOP_FLANGE`, and `BOTTOM_FLANGE` elements while both flanges reference
one `FLANGES` region. Rectangular and square tubes preserve four walls grouped by the
neutral `WALL_PAIR_1` and `WALL_PAIR_2` regions. Tee stem/flange, angle legs, a flat
plate/doubler, and the round-tube curved wall retain the controlled memberships defined
by the factory. Entities never invoke that factory implicitly.

For pultruded FRP, `FRPComponentOrientation` owns only the matching component-local
frame and shared LW axis family. Each planar region carries a `PLANAR_FIXED` rule whose
CW and TT axis families are distinct from each other and from LW. A round-tube region
carries `CYLINDRICAL`, meaning axial LW, circumferential/tangential CW, and radial TT
without false fixed Cartesian CW/TT values. Steel and `OTHER` topologies carry neither
component FRP orientation nor region FRP rules.

Custom topology uses caller-defined scoped IDs and explicit references. It may group
several elements into one region or split a nominal standard group, including one wall
of a tube, when product, layup, qualification, or orientation later requires it. Since
Stage 1.2 has no property or qualification source, material-basis equivalence is not
executably assessed; splitting remains the fail-closed representation when equivalence
is not established.

An interface may directly connect two members without a fictitious connector. Several
interfaces may reference one shared connector, and direct and connector-assisted
interfaces may coexist. A transfer-intent declaration records topology intent; it
does not distribute demand or create calculation support.

Section and component families remain classifications. Stage 1.3B factories use a
standard family to validate and construct its approved nominal geometry; they still
store no section properties, material properties, bolt diameters, stack layers, holes,
connection geometry, or manufacturer values.

## Standard cross-section geometry

`CrossSectionGeometry2D` is a standalone immutable geometry-package value. It does not
become a field on `AssemblyMember` or `ConnectorComponent` in Stage 1.3B. A factory
consumes and validates an explicit standard `SectionTopology`, maps every existing
physical element exactly once, maps no unknown element, and preserves all
`material_region_id` values through identity rather than copying or redefining them.

All coordinates are in the component-local `y-z` plane. Local `x` is the deferred
extrusion direction. The construction datum is exactly `(0,0)`, the center of the
nominal outside bounding box; it is not a centroid, shear center, calculated principal
origin, analytical line, joint point, or force reference point. Dimensions are finite,
strictly positive values in the owning assembly's length unit and obey exact
shape-specific inequalities. No conversion, rounding, dimensional tolerance, or
repair is applied.

Otherwise-valid finite inputs are rejected if an IEEE floating-point half-dimension
or derived primitive boundary/span becomes nonfinite, collapses, or loses its required
strict ordering. This exact representability guard prevents silent rounded or
degenerate nominal coordinates; it is not a dimensional tolerance, fabrication
criterion, fit-up rule, or engineering acceptance limit.

Flat-wall standard shapes use an exact sharp-corner composite of axis-aligned physical
rectangles, deferred finite zones or meeting lines where required, and nominal void
rectangles. W/I/channel web-to-flange and tee stem-to-flange meeting lines are deferred.
The angle's finite heel and the four rectangular/square-tube corner squares are
deferred, carry no material ownership, and are non-targetable. A round tube is one
exact analytic annulus mapped to `CURVED_WALL`; no polygon or permanent tessellation
replaces it.

`PhysicalElementGeometry2D` records future targetability but implements no connection
targeting. `DeferredSectionFeature2D` is explicitly deferred and non-targetable.
`SectionVoid2D` represents missing/open space, not material. Custom symbolic topology
remains supported by Stage 1.2, but arbitrary custom geometry and standard-factory use
with a custom topology are rejected. Detailed dimensions, exact coordinates, profile
consistency, and visualization boundaries are controlled by
`STANDARD_CROSS_SECTION_GEOMETRY_SPECIFICATION.md`.

## Component placement and longitudinal extrusion

Stage 1.3C1 associates an `AssemblyMember` or `ConnectorComponent` with one compatible
`CrossSectionGeometry2D` in the separate immutable provisional
`PlacedComponentGeometry3D` contract. A support is not accepted. The placement retains
one authoritative resolved global `CartesianFrame3D`, one `LongitudinalExtent` with
exact `x_end > x_start`, and one finite `SectionDatumOffset`. There is no second roll,
mirror, independently editable transform, or unresolved parent hierarchy.

For a member, the pure builder reuses `build_member_frame`, sets the origin at START,
keeps local +x from START to END, and assigns exact extent `[0,member_length]`.
`AssemblyMember.connected_end` selects the connected physical plane without reversing
the frame, extent, action, or START/END identity. The member cross-section family must
match `AssemblyMember.section_family`. For a connector, callers supply one explicit
proper global frame and one explicit interval, which may straddle local zero; connector
kind does not infer a family, topology, geometry, or length.

Both builders require exact equality between source physical-element IDs and the
component's explicit topology. Missing topology, missing/unknown/duplicate element
geometry, and cross-component topology mismatches are rejected. Material-region
membership remains on `SectionTopology` and is not copied or redefined by placement.

The component reference line is the placed-frame x axis through local `(x,0,0)`. The
Stage 1.3B construction datum maps to the distinct section-datum line through
`(x,offset_y,offset_z)`. A source section point `(y,z)` maps to local
`(x,y+offset_y,z+offset_z)` and then globally through the one frame. Inverse mapping
retains x and subtracts the offset; it neither projects nor clamps. Neither line is a
centroid, shear center, analytical line, joint point, or force point.

Minimum and maximum local-x boundary-plane descriptors retain component identity,
local x, global reference/datum points, and global outward normals `-local x` and
`+local x`. Member START maps to minimum x and END to maximum x. Connector boundaries
have no START/END meaning. Boundary planes are non-targetable geometry and are not
connection-face references.

Exact physical rectangles become `LocalRectangularPrism3D` descriptors and the
analytic annulus becomes one `LocalAnnularCylinder3D`. Deferred rectangles become
deferred rectangular prisms, deferred lines become zero-thickness
`LocalRuledSurface3D` descriptors, and rectangular voids become void prisms. Separate
physical occurrences and shared material-region identity are preserved. Deferred and
void geometry remains non-targetable and without new material ownership or structural
credit. No Boolean solid or canonical mesh is created. The full contract is controlled by
`COMPONENT_PLACEMENT_AND_EXTRUSION_SPECIFICATION.md`.

## Physical surface patches and bounded support surfaces

Stage 1.3C2A derives a separate immutable `ComponentSurfaceSet3D` from one exact
`PlacedComponentGeometry3D`. A `SurfacePatch3D` retains participant-scoped identity,
its physical-element or deferred-feature source, exposure, disposition, exact planar
rectangle/annulus or analytic-cylinder geometry, and geometric targetability derived
without a caller override. Component surface sets reject unknown sources, duplicate
IDs/geometry, participant mismatch, custom topology, and non-deterministic ordering.

Planar surface-local +x is the signed canonical normal and y/z are in-plane. Signed
normals remain distinct from sign-independent material-axis families. Round-tube side
patches retain outward/inward radial normal rules and no fixed circumferential normal.
Regular exterior, void-facing, and end-cut patches are geometrically targetable;
internal-junction and every deferred patch are non-targetable. Targetability creates
no interface or calculation support.

The standard factory preserves the exact shape-specific split around W/I, channel,
and tee junctions; keeps tube corners and the angle heel deferred; retains separate
element-level end cuts; and produces exact outer/inner cylinders plus annular ends
for round tubes. A separate pure builder creates one explicit bounded planar support
patch from an `AssemblySupport`, caller-supplied proper frame, ID/label, and positive
extents. It infers nothing from `SupportKind` and creates no support body.

The complete surface contract is controlled by
`PHYSICAL_SURFACE_PATCH_SPECIFICATION.md`. `ConnectionInterface` remains unchanged;
the separate Stage 1.3C2B geometry layer now resolves bounded planar zones as specified
by `INTERFACE_TARGETING_AND_CONNECTION_ZONE_SPECIFICATION.md`.

## JointAssembly aggregate

`JointAssembly` remains the immutable root aggregate. Stage 1.3C1 does not add a
placement registry or geometry field to it. It contains the unit system, exactly
one `SHEAR` or `MOMENT` design category, and tuple collections for members, connector
components, supports, interfaces, bolt groups, load combinations, and manual actions.

Aggregate validation is exhaustive rather than fail-fast. A valid assembly under the
preserved Stage 1.2 aggregate contract:

- has at least one member and one interface;
- has at least two distinct participants that resolve through declared interface
  references;
- has unique collection and provisional global top-level IDs;
- resolves every typed participant, bolt-group interface, local-frame owner,
  symbolic-reference-point owner, action member, and action load combination;
- gives each action the member's declared connected end;
- has no more than one action for a member/load-combination pair;
- gives a `MOMENT` assembly at least one moment-resisting interface; and
- gives a `SHEAR` assembly no moment-resisting interface.

For every stored component topology, validation also reports duplicate scoped element
or region IDs, unresolved element-to-region references, orphan regions, and a stored
standard topology that differs from its canonical symbolic definition. Pultruded FRP
requires one matching component-local LW orientation, a topology, and one FRP rule on
every region. Steel and `OTHER` prohibit FRP component and region orientation while
remaining free to carry physical topology.

Connector components, supports, bolt groups, load combinations, and manual actions may
otherwise be empty. Construction does not require a bolt group merely because an
interface exists and does not invent missing topology or actions.

## Validation issue contract

`JointAssembly.validate()` returns an immutable tuple of all detected
`ValidationIssue` records. Each issue includes a stable `ValidationCode`, a human
message, a logical path, and an optional related entity ID. Issues are ordered by
logical path, code, related ID, and message so identical invalid input yields identical
diagnostics. `JointAssembly.require_valid()` raises `DomainValidationError` containing
that same ordered issue tuple.

Local type and shape violations raise `TypeError` or `ValueError` during value/entity
construction. Aggregate cross-reference and topology violations are returned through
the issue contract. Neither path produces `PASS`, `FAIL`, a capacity, a utilization,
or a calculated engineering result.

## Explicit exclusions and next-stage boundary

Stage 1.3C2A does not implement:

- interface/`JointAssembly` placement, interface surface targets, connection zones,
  bolt stacks, layers, holes, penetrations, attachment geometry, contact, or fit;
- a `JointAssembly` resolved-frame registry, automatic symbolic-frame resolution,
  eccentricity discovery, automatic action shifting, or template-specific allowed
  reference points;
- material or section property values, `MaterialPropertySet`, source qualification,
  directional property lookup, off-axis constitutive behavior, or property transforms;
- load factoring, combinations beyond manually supplied factored-strength identities,
  reactions, equilibrium, force distribution, shared-demand calculation, or limit
  states;
- arbitrary custom cross-section geometry, solid round, fillets/radii, CAD Boolean
  operations, meshes as canonical geometry, or any centroid, shear-center, area,
  inertia, torsion, warping, effective, or other section property;
- persistence schemas, serialization, migrations, API routes, frontend integration,
  rendered visualization, reports, fingerprints, or deployment; or
- engineering equations, capacities, utilization, optimization, or result statuses.

The cylindrical material rule records only axial LW with circumferential CW and radial
TT semantics. The placed analytic annular cylinder and general rotations do not give
that rule an angle, evaluation location, or fixed radial/tangent vector. Deferred
junction/corner surfaces gain no structural credit.

Stage 1.3C2B preserves `ConnectionInterface` unchanged and associates its exact
participant order with a separate immutable geometry specification and resolved
aggregate. Bounded zones, planar target sides, an explicit local frame, and raw signed
plane separation are geometry only. They do not enter `JointAssembly`, establish
contact, modify transfer intent, or create a calculation result.

## Stage 1.3C3 resolved geometry and action boundary

Stage 1.3C3 adds the separate immutable `JointGeometryBasis` and
`JointGeometryContext`, explicit surface semantic roles, primary-interface bolt-group
placement, authoritative master centers/axes, exact round-hole cylinders, intended
physical-element layers, ordered path stacks, raw clearances/gaps, exact symbolic-frame
bindings, physical reference-point resolution, global manual-action resolution, and
caller-directed eccentricity transforms. Exact assembly ownership, declaration order,
participant-scoped source identity, unit-system identity, and original logical objects
are retained. See `BOLT_PATH_HOLE_AND_LAYER_GEOMETRY_SPECIFICATION.md` and
`JOINT_GEOMETRY_REFERENCE_AND_ECCENTRICITY_SPECIFICATION.md`.

The context is an in-memory geometry registry, not a domain mutation, schema, API,
persistence record, load path, calculation input, or result. Hardware, drilling
approval, contact/fit, force distribution, equilibrium, properties, equations,
resistance, capacity, utilization, and engineering status remain absent. PEN-ENG-005
remains unresolved because explicit point resolution does not approve template-
permitted force points.

## Stage 2.1A calculation contracts

The framework-independent `calculation` package now defines exact dual-unit physical
quantities; standard-hole source/physical records; calculation, material, fastener,
washer, time/end-use, lap, and interpretation snapshots; resolved demand; C3
geometry-to-code mapping; prerequisite validation; limit-state readiness plans;
fail-closed aggregate status; and a canonical SHA-256 calculation-contract
fingerprint.

The authorized family is limited to one logical bolt and one row penetrating one or
more declared rectangular pultruded-FRP layers with a common authoritative round hole.
Direction selection, required-input checks, source/qualification state, and
whole-connection qualification are explicit. Exactly 90 degrees selects transverse;
ICE bearing use requires engineering review; the locked ASTM F593 Group 2 316/316L
`Fnt` remains source-pending; no return-element exemption or bolt-demand distribution
is automatic; and J1 retains its Section 2.3.2 whole-connection qualification.

The package contains no executable resistance or combined-stress equation, capacity,
utilization, calculated physical-input `PASS`/`FAIL`, equilibrium solution, API,
frontend, persistence, or report integration. The non-executable equation catalog and
golden future values are controlled references for a separately authorized Stage
2.1B, which has not begun.
