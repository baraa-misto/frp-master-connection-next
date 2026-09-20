# T-Connector Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-004 |
| Stage | 0.1 |
| Document status | Draft controlled specification |
| Engineering implementation | Not implemented |

## Purpose

A T-section is a first-class ConnectingComponent that may participate in several interfaces at one joint. One shared T may connect a beam and multiple braces to a supporting member while direct member-to-member interfaces also exist elsewhere in the same JointAssembly.

This specification establishes the canonical component and demand topology. It does not approve a T-section material, qualification basis, internal-force distribution method, resistance, or connection check.

## Canonical T-component record

| Field group | Required content |
|---|---|
| Identity and ownership | T-component identifier, owning joint, revision, user-facing label, and shared-component indicator |
| Geometry | Canonical profile and extent, constituent geometric regions, ends, transitions, and controlled reference geometry |
| Material | Material-data reference, material-data version, provenance, and qualification status |
| Material orientation | Explicit material-axis orientation in a named component or joint frame |
| Zones | Addressable component zones used to associate interfaces, holes, demand, and future results without deriving resistance from meshes |
| Faces | Stable face identifiers and orientations used by attachments, holes, dimensions, and view definitions |
| Interfaces | Member-to-T and T-to-support interface references; every participating interface remains a distinct first-class object |
| Bolt groups and stacks | References to canonical master centers, holes, groups, and ordered stacks associated with each interface or shared region |
| Internal-force stations | Named, located stations for recording future component demand and result provenance; station selection and engineering use remain pending |
| Load-path links | Explicit incoming and outgoing interface links and any shared-region references |
| Capability status | Separate geometry-support and calculation-support status, with source, version, and approval metadata |

## Approved topology and consistency rules

- One T component can have several attached interfaces and can receive demand from several connected members.
- Checking attached interfaces independently is not sufficient when the T, a bolt group, the T-to-support interface, or the supporting-member region is shared.
- The load-transfer graph must identify each member-to-T interface, the shared T component, the T-to-support interface, and relevant supporting regions. No hidden or invented load path is permitted.
- The same canonical T geometry, material orientation, faces, zones, bolt centers, and interface locations drive calculation inputs, 3D, 2D, dimensions, persistence, and reports.
- Rendering geometry cannot be used to infer section properties, resistance, load distribution, or qualification.
- A direct bolted interface may coexist with the shared T in one joint without an artificial connector being inserted into the direct load path.

## Demand and result levels

The future engineering model must preserve, as separate but linked records:

1. demand at each member-to-T interface;
2. combined demand on the shared T;
3. demand at controlled internal-force stations;
4. demand at the T-to-support interface;
5. individual and combined demand for any shared bolt group or bolt stack;
6. demand on each applicable shared supporting-member region; and
7. whole-joint equilibrium and result status.

Combined actions cannot be split into unrelated checks when they act through the same component, bolt group, interface, or FRP region. The exact combination, distribution, station, and equilibrium methods are not approved in Stage 0.1.

## Fail-closed behavior

- Missing component, face, zone, interface, bolt, material-orientation, station, or load-path information required by an approved capability produces INCOMPLETE INPUT.
- An unresolved or contradictory interface topology produces INVALID GEOMETRY only where an approved geometry rule exists; otherwise it remains unsupported or review-required.
- An unqualified T material, unapproved shared-demand method, unsupported topology, or unmapped condition produces CALCULATION NOT SUPPORTED, NOT COVERED BY SELECTED CODE, or ENGINEERING REVIEW REQUIRED, as applicable.
- Geometry support never implies calculation support.
- No placeholder T, interface, or whole-joint check may return PASS or FAIL.
- Warnings are supplemental and cannot replace a required fail-closed status.

## Pending engineering decisions

The following remain **Pending Engineering Decision**:

- acceptable T-connector material options and material orientation rules;
- manufacturer-data, standard, or qualification/test-data basis;
- mapping to governing clauses, tables, equations, edition, and verified errata;
- applicability limits for T geometry, faces, zones, interfaces, and bolt arrangements;
- methods for interface demand transfer, component combined demand, internal-force stations, and T-to-support demand;
- treatment of shared bolt groups and shared supporting-member regions;
- treatment of eccentricity, prying, deformation, and other relevant behaviors;
- unsupported-condition triggers for each future calculation family; and
- independent verification and qualified engineering approval.

## Stage 0.1 limitation

No T-section engineering equation, resistance, capacity, demand-distribution method, utilization, or PASS/FAIL calculation is specified or implemented. Material and qualification basis remain pending.
