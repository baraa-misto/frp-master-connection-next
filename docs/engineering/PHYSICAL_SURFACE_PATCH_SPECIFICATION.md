# Physical Surface Patch Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-005 |
| Stage | 1.3C2A — physical surface patches and bounded support surfaces |
| Status | Approved geometric meaning implemented; software representation provisional; not frozen |
| Implementation | `backend/src/frp_master_connection/geometry/surfaces.py` |
| Placement authority | `backend/src/frp_master_connection/geometry/placement.py` |
| Section authority | `backend/src/frp_master_connection/geometry/section.py` |
| Calculation engine | Not implemented |
| Engineering rule set | Not implemented |

## Purpose and safety boundary

Stage 1.3C2A derives exact authoritative surface patches from one already placed
Stage 1.3C1 member or connector. It also introduces one explicit bounded planar
surface for an `AssemblySupport`. Surface patches are canonical geometry identities,
not rendering subdivisions and not camera-relative selections.

This stage implements geometric targetability only. A targetable patch is eligible
for a later connection-target contract; it is not attached, calculation-supported,
bolt-accessible, structurally credited, or adequate. No interface target, connection
zone, hole, bolt, force point, eccentricity, resistance, capacity, utilization, or
engineering `PASS` or `FAIL` is implemented.

The surface modeling, exposure, disposition, identity, normal, and targetability
meaning in this document is approved. Exact module, class, enum, field, helper,
ordering, and validation-exception names remain Provisional Implementation Decisions.

## Separate surface and physical identities

A physical section element is a material-bearing occurrence. A surface patch is a
bounded part of its geometric boundary. They are intentionally separate:

- one element can own several exterior, void-facing, and end-cut patches;
- every patch retains its source physical-element or deferred-feature ID;
- surface IDs are scoped to the owning participant and remain stable under proper
  placement changes;
- a patch never replaces its source element or material region; and
- surface sets from different participants are never merged.

Separate physical occurrences remain separate even when they share a material region.
Top and bottom W/I flanges still reference `FLANGES`; opposite tube walls still use
their applicable wall-pair region; no surface patch merges those occurrences.

## Exact surface geometry

The only authoritative Stage 1.3C2A surface geometry kinds are:

| Kind | Exact representation |
|---|---|
| Planar rectangle | Proper resolved surface frame plus finite positive in-plane y/z extents. |
| Planar annulus | Proper resolved surface frame plus exact outer and inner radii. |
| Analytic cylinder | Proper axis frame, finite longitudinal extent, positive radius, and outward/inward radial normal sense. |

No polygon soup, arbitrary mesh, Boolean solid, CAD/B-rep, or permanent
tessellation is authoritative geometry.

### Planar surface frame

Every planar surface frame is proper, right-handed, and orthonormal:

```text
surface local +x = signed canonical geometric normal
surface local +y = first in-plane direction
surface local +z = second in-plane direction
+x cross +y = +z
```

The frame origin is the exact patch center. Rectangle corners use one deterministic
surface-local y/z order. Annular patches retain their exact center. A negative-facing
patch has a different signed frame from the corresponding positive-facing patch;
normal sign is never inferred from a camera.

### Analytic cylinders

Round-tube side surfaces retain the component-derived axis and clocking, exact finite
local-x extent, exact radius, and a radial normal rule. The outer cylinder is radial
outward; the inner cylinder is radial inward. A cylinder has no fixed global normal,
sampled circumferential angle, material CW vector, or stored tessellation.

## Signed normals and material axes

Geometric normals are signed directions. Stage 1.2 material axes remain
sign-independent `PrincipalAxisFamily.X`, `Y`, or `Z`. Opposite geometric normals do
not create different material families, strengths, or behaviors. The round-tube
material rule remains axial LW, tangential CW, and radial TT without choosing an
evaluation angle.

## Patch identity, source, and references

Each patch retains:

- a stable participant-scoped ID and separate label;
- exact member, connector, or support participant ownership;
- exactly one physical-element, deferred-feature, or support source;
- one exposure classification and one disposition;
- exact surface geometry; and
- targetability derived only from exposure and disposition.

Impossible mixed source combinations are rejected. Component source IDs must resolve
within the exact placed component. Support sources must match the exact
`AssemblySupport` participant. A `SurfacePatchReference` contains the participant and
scoped patch ID, so the same patch ID on another participant cannot resolve across
surface sets.

`ConnectionInterface` is unchanged and does not store a surface reference in this
stage.

## Exposure, disposition, and targetability

The controlled exposure values are:

- `EXTERIOR_EXPOSED` — boundary between modeled material/deferred geometry and
  exterior space;
- `VOID_EXPOSED` — boundary between a physical element and an explicit canonical
  section opening;
- `END_CUT` — positive-area minimum- or maximum-local-x cut of one physical or
  deferred finite-area occurrence; and
- `INTERNAL_JUNCTION` — an authoritative meeting boundary that is not an exposed
  connection target.

The dispositions are `REGULAR` and `DEFERRED`. The sole derived targetability rule is:

| Patch state | Geometrically targetable |
|---|---|
| Regular exterior-exposed physical patch | Yes |
| Regular void-exposed physical patch | Yes |
| Regular physical end cut | Yes |
| Explicit regular bounded support patch | Yes |
| Internal junction | No |
| Any deferred-feature patch | No |
| Any patch with deferred disposition | No |

There is no caller override that can make a deferred patch targetable. A void-facing
patch remains owned by the adjacent physical element; the void is nonmaterial and
owns no surface patch.

## Component surface set

`ComponentSurfaceSet3D` is an immutable aggregate for exactly one
`PlacedComponentGeometry3D`. It retains the exact participant, exact placed aggregate,
and a deterministic immutable tuple of patches. It rejects participant mismatch,
duplicate or non-deterministic patch IDs, unknown source IDs, incompatible source
geometry kinds, duplicate authoritative geometry, support patches, and cross-component
references.

The standard factory consumes the existing placed aggregate. It does not re-enter
section dimensions, create a second placement, mutate source geometry/topology, or
attach runtime geometry to domain entities. A custom topology fails closed because no
approved generic custom-surface model exists.

## WIDE_FLANGE and I_SECTION

Both families use the same patch topology.

The web owns its negative- and positive-TT broad void-facing surfaces and a separate
minimum/maximum end cut. It does not own CW edge faces at flange meetings.

Each flange owns:

- one exterior outer TT broad patch;
- two separate void-facing inner TT strips, split on the negative- and positive-CW
  sides of the web;
- two exterior CW edge patches; and
- separate minimum/maximum end cuts.

The two source web/flange meeting lines each become one exact planar rectangular
internal-junction patch spanning the full longitudinal extent. They are deferred,
non-targetable, material-free, and not duplicated by web or flange patches.

## CHANNEL

The canonical web remains at local `-y` and the opening remains toward local `+y`.
The web owns one exterior back broad patch, one void-facing inner broad patch, and two
end cuts. Each flange owns one exterior outer broad patch, one void-facing inner strip
from the web edge to the free tip, an exterior negative-CW back edge, an exterior
positive-CW free tip, and two end cuts.

Exactly two deferred web/flange meeting patches remain authoritative. No standard
channel is mirrored; global orientation changes only through proper component
rotation.

## TEE

The stem remains toward local `-z` and owns both broad void-facing surfaces, its
exterior free edge, and two end cuts. It does not own the flange meeting face.

The flange owns one exterior outer broad patch, two inner void-facing strips split
around the stem, both exterior CW edges, and two end cuts. One exact deferred
stem/flange junction patch spans the source meeting line and is non-targetable.

## RECTANGULAR and square tube

Each of the four physical walls owns only:

- one exterior broad patch;
- one `VOID_EXPOSED` interior broad patch; and
- separate minimum/maximum end cuts.

No regular wall edge duplicates a corner interface. Each of the four deferred corner
prisms owns two exterior boundary patches, two internal-junction patches adjacent to
physical walls, and two deferred end cuts. All six patches per corner are deferred
and non-targetable. Square tubes use the same topology. No rounded corner or corner
material/structural credit is introduced.

## ANGLE

Each physical leg owns two broad surfaces, one exterior free edge, and two end cuts.
The open-area-facing broad patch is `VOID_EXPOSED`; the outer broad patch is
exterior-exposed. Neither leg owns the edge coincident with the deferred heel.

The heel owns two exterior boundary patches, two internal-junction patches adjacent
to the legs, and two deferred end cuts. All heel patches are deferred,
non-targetable, and assigned to neither leg.

## PLATE and doubler

The one `PLATE` prism owns exactly six regular targetable patches: positive- and
negative-TT broad exterior surfaces, positive- and negative-CW exterior edges, and
separate minimum/maximum end cuts. The availability of those patches implies no
attachment, boltability, structural credit, or calculation support.

## ROUND_TUBE

The analytic annular cylinder owns exactly four regular targetable patches:

1. exterior outer cylinder with radial-outward normal sense;
2. void-exposed inner cylinder with radial-inward normal sense;
3. minimum-x annular end cut with normal `-local x`; and
4. maximum-x annular end cut with normal `+local x`.

Both end annuli retain the exact positive inner radius and outer radius of the source
placed annular cylinder. No mesh, angle sample, fixed material CW vector, hole, or
interface target is created.

## End-cut rules

Every positive-area physical element receives its own minimum- and maximum-x cut.
For a member these remain START and END respectively; for a connector they retain
neutral minimum/maximum identity. Patch IDs, geometry, and normals do not change when
the member's connected end changes.

Deferred heel/corner prisms receive deferred end cuts. A zero-thickness ruled
junction has only boundary lines at its ends and therefore creates no additional
positive-area end patch.

## Bounded planar support surface

The pure support builder requires an `AssemblySupport`, caller-supplied surface ID and
label, explicit proper resolved surface frame, and finite positive in-plane extents.
Surface-local +x is the outward normal. The result is one support-owned, regular,
exterior-exposed, geometrically targetable planar patch.

Nothing is inferred from `SupportKind`. The builder creates no support body,
thickness, concrete dimensions, foundation volume, anchors, interface, or resistance.

## Transformation and offset invariants

All geometry derives from the Stage 1.3B section, Stage 1.3C1 placed physical and
deferred primitives, component frame, longitudinal extent, and section offset. Under
any proper component rotation/translation:

- points and planar normals transform consistently;
- cylinder axes and radial-sense meaning remain consistent;
- patch IDs, exposure, disposition, and targetability remain unchanged; and
- section offsets shift the surface geometry exactly with its component.

Changing connected member end changes none of those surface values.

## Deterministic validation

The implementation validates stable IDs, labels, tuple immutability, patch-ID
uniqueness/order, participant ownership, exact source combinations and resolution,
standard-family compatibility, geometry-kind/source compatibility, proper surface
frames, finite positive extents, valid radii/intervals, derived targetability,
deferred/internal non-targetability, authoritative-geometry uniqueness, and
participant-scoped reference resolution. Invalid custom generation and corrupt
standard-shape data fail closed.

These are geometry-contract checks only. They validate no engineering suitability,
tool access, bolt clearance, source applicability, or calculation coverage.

## Explicit Stage 1.3C2B and later boundary

Stage 1.3C2A does not implement interface surface targets, connection zones, contact
pairing, gaps, clearances, interface origins/frames, holes, bolt axes/paths/stacks,
penetrated layers, support bodies, anchors, force-reference or joint-point positions,
eccentricity discovery, automatic moment shifting, collision/fit, section/material
properties, calculations, API exposure, frontend rendering, persistence, or reports.

Stage 1.3C2B now resolves these authoritative participant-scoped references into
planar whole-patch or rectangular-subzone connection zones. It accepts planar
rectangles and whole planar annuli, rejects analytic cylindrical sides and all
deferred/internal patches, and retains the exact source patch. The targeting layer
does not change surface identity, geometry, exposure, disposition, or targetability;
see `INTERFACE_TARGETING_AND_CONNECTION_ZONE_SPECIFICATION.md`.

Stage 1.3C3 adds the required `SurfacePatchRole` semantic dimension to every factory
patch. Negative/positive thickness faces, edges, rectangular end cuts, analytic outer/
inner cylinders, annular ends, deferred junctions, and support faces are explicit and
validated. The role is assigned by the authoritative standard-shape or support factory;
it is never inferred from IDs, labels, aspect, area, material, renderer geometry, or
view state. Existing source, exposure, disposition, targetability, and exact geometry
remain unchanged. Only opposing regular physical rectangular thickness faces are
eligible for a through-hole layer.

## Stage 2.3R3 W-flange strip identities

Each W/I flange retains historical whole `OUTER_TT_BROAD` and adds exact outer
negative/positive crosswise strips paired with existing inner negative/positive
strips. The current template targets `TOP_FLANGE:OUTER_NEGATIVE_CW_STRIP` for exterior
contact and `TOP_FLANGE:INNER_NEGATIVE_CW_STRIP` for web-side contact. Positive/
negative thickness roles and global normals are explicit. The additive split does not
rename physical elements or add fit-up, fabrication, contact, or resistance meaning.
