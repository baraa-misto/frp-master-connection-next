# Bolt Group and Bolt Stack Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-002 |
| Stage | 0.1 |
| Document status | Draft controlled specification |
| Engineering implementation | Not implemented |

## Purpose

This specification defines the canonical concepts needed to represent bolts, bolt groups, penetrated layers, and through-thickness bolt stacks consistently. It establishes data ownership and traceability only. It does not define bolt resistance, connection resistance, force distribution, detailing limits, or numerical acceptance criteria.

The explicit modeling of bolt stacks and penetrated layers is an **Approved** product requirement. Engineering treatment of those records remains subject to source mapping, applicability verification, independent validation, and qualified engineering approval.

## Controlled concepts

| Concept | Required content | Modeling rule |
|---|---|---|
| Bolt | Stable identifier, material reference, diameter, master center, axis/orientation, group membership, and stack reference | A bolt is a Fastener, not a ConnectingComponent. Material and diameter are inputs; their engineering qualification is separate. |
| Master bolt center | One canonical center in the owning bolt-group coordinate frame | It is the sole geometric source for the associated bolt, holes, views, dimensions, and reports. A display-specific duplicate is not authoritative. |
| Bolt group | Stable identifier, owning interface or component, coordinate frame, member bolt references, and group-level demand/result references | A group may be associated with an interface, a shared connecting component, or a supporting region. Its calculation support is stated separately from geometry support. |
| Hole in a penetrated layer | Hole identifier, master-center reference, penetrated-layer identifier, face/side, orientation, and controlled hole attributes | Every physical layer penetrated by a bolt has an explicit hole record. One generic hole cannot stand in for an unknown layer sequence. |
| Ordered bolt stack | Bolt reference, stack axis, head side, nut side, and ordered stack entries | Entries run in a declared direction from head side to nut side. Reversing the physical stack changes the stored order; it is not a camera operation. |
| Head, nut, and washers | Explicit hardware type, side, order, and applicable product/material reference | Hardware cannot be implied by rendering defaults. Omitted or unknown hardware is recorded as such. |
| Grip | Identification of the clamped portion of the ordered stack and the layers and hardware it contains | Grip is derived only from canonical stack geometry once the applicable definition is approved; no resistance consequence is assumed in Stage 0.1. |
| Shear plane | Explicit location within the ordered stack and a controlled future classification | Shear planes are not inferred solely from the count of visible member interfaces. Their engineering treatment is pending. |
| Bearing layer | Explicit penetrated-layer reference and future eligibility/classification metadata | A penetrated layer is not automatically granted bearing resistance. |
| Alignment | Relationship among bolt axis, master center, and the holes in every penetrated layer | Misalignment, unresolved offsets, or incompatible axes cannot be hidden by snapping rendered geometry. |
| Access and interference | Head-side access, nut-side access, installation/removal path, and clashes with modeled components | Visibility does not establish constructability. Unchecked access or interference remains an explicit unresolved condition. |

## Canonical relationships

- Each bolt occurrence references exactly one master bolt center and one ordered bolt stack.
- Each physical penetration references both that master center and the specific penetrated layer.
- Stack entries preserve physical order, layer identity, material orientation, and face/side identity.
- Co-located graphics do not merge distinct bolts, layers, holes, or interfaces.
- A bolt group can be shared. If it transfers demand for more than one interface, its combined group demand must be represented and cannot be replaced by unrelated interface-only checks.
- The same bolt centers control future calculations, hole locations, 3D geometry, 2D views, dimensions, selections, saved data, and reports.

Rendering meshes, drawing symbols, and dimensions are derived representations. Moving or rounding them for display cannot change a master center, stack order, hole record, grip record, or engineering input.

## Model-completeness and fail-closed behavior

Before a calculation family may claim bolt support, it must define the required bolt, group, hole, layer, stack, hardware, shear-plane, bearing-layer, alignment, access, and interference data for its approved scope.

- Missing required bolt or stack data produces INCOMPLETE INPUT.
- Physically inconsistent centers, layers, or stack order produce INVALID GEOMETRY when the applicable validation rule has been approved.
- A stack composition, hole condition, material, force component, or group topology outside an approved calculation scope produces CALCULATION NOT SUPPORTED, NOT COVERED BY SELECTED CODE, or ENGINEERING REVIEW REQUIRED, as applicable.
- Geometry-supported bolt placement does not mean calculation-supported bolt behavior.
- A warning may supplement, but cannot replace, a required fail-closed status.
- Placeholder processing may never return PASS or FAIL.

## Pending engineering decisions

All items below have status **Pending Engineering Decision**:

- permitted bolt, hardware, material, and diameter qualification sources;
- supported hole classifications and hole-geometry controls;
- approved definitions and treatment of grip, shear planes, threads, washers, and bearing layers;
- applicability boundaries for each bolt-group topology and penetrated material sequence;
- group-demand distribution and combined-action methods;
- alignment, access, installation, and interference acceptance rules;
- treatment of prying, slip, pretension, deformation, and other behavior where applicable;
- treatment of multiple FRP layers, reinforcement layers, gaps, fillers, and mixed materials;
- mapping to governing clauses, tables, equations, errata, and manufacturer data; and
- independent verification cases and qualified engineer approval.

## Stage 0.1 limitation

No numerical bolt criterion, resistance, force-distribution method, capacity, utilization, or PASS/FAIL calculation is specified or implemented here.

## Stage 2.1A approved first-slice contracts

For the authorized one-logical-bolt, one-row slice, the calculation projection consumes
one authoritative C3 bolt axis, one common physical round-hole diameter, and an
explicit ordered set of rectangular pultruded-FRP layers. It validates identity,
declared order, containment provenance, layer thickness, edge distances, end distance,
washer prerequisites, common bolt size/specification, and the limited Chapter 8
geometry/applicability boundaries without judging resistance.

A standard hole has one explicit published source basis: nominal bolt diameter plus
exactly `0.063 in` for the U.S. source profile, or plus exactly `1.6 mm` for the SI
source profile. The resulting physical hole diameter is stored authoritatively and is
not recomputed after unit conversion. Unequal hole diameters, mixed bolt size/grade,
unsupported layer arrangements, and missing required washer inputs fail closed.

The locked ASTM F593-17 Group 2 316/316L snapshot deliberately has no approved `Fnt`
and remains source-data-pending for metallic bolt strength planning. An explicit
synthetic `Fnt` fixture is separate and makes no F593 claim. Return-element exemption
and bolt-demand distribution are never inferred. No bolt resistance, combined-stress
equation, capacity, utilization, or calculated physical-input `PASS`/`FAIL` exists.
