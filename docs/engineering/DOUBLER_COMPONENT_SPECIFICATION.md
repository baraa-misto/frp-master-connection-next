# Doubler Component Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-003 |
| Stage | 0.1 |
| Document status | Draft controlled specification |
| Engineering implementation | Not implemented |

## Purpose

A doubler is a first-class reinforcement component attached to a defined host component and face. This specification controls its identity, geometry relationships, qualification metadata, and demand/result separation. It does not approve a structural-credit, load-sharing, composite-action, or resistance method.

The first-class treatment of doublers is an **Approved** product requirement. Any structural credit remains a **Pending Engineering Decision** until its source, scope, applicability, validation, and approval are controlled.

## Canonical doubler record

| Field group | Required content |
|---|---|
| Identity | Doubler identifier, project and joint context, revision, and optional user-facing label |
| Host relationship | Host component identifier and specific host-face identifier; the relationship cannot be inferred only from visual contact |
| Side | Explicit side relative to the controlled host-face orientation; exact side labels depend on pending axis conventions |
| Geometry | Canonical boundary, thickness, openings, edges, and any modeled segmentation needed to describe the physical component |
| Material | Controlled material-data reference, material-data version, qualification status, and provenance |
| Material orientation | Explicit material axes or orientation reference appropriate to the selected material record |
| Layers | Ordered physical layer records when the doubler is laminated or consists of more than one modeled layer |
| Position and offsets | Placement in a named host or joint frame, including explicit offsets from controlled reference geometry |
| Hole pattern | Hole records linked to the same master bolt centers and bolt stacks used by interfaces, views, dimensions, and reports |
| Attachment classification | Controlled description of how the doubler is attached to the host; permitted classifications and engineering effects remain pending |
| Structural-credit classification | One of the controlled states defined below |
| Qualification source | Source-register identifier and, when applicable, manufacturer/test record, edition or version, approved scope, verification date, and approval authority |
| Demand and results | Separate doubler-demand references, combined-action references, applicability status, result status, warnings, and assumptions |

## Structural-credit classification

| Classification | Meaning |
|---|---|
| NO STRUCTURAL CREDIT | The doubler may be represented geometrically, but it cannot increase or replace any resistance in an engineering result. |
| ENGINEERING REVIEW REQUIRED | Potential structural participation has been identified, but no approved method and scope are available for automated use. |
| QUALIFIED FOR SPECIFIED SCOPE | Credit may be considered only after a controlled source or test basis, applicability limits, implementation verification, and qualified engineering approval are recorded for the specific scope. This Stage 0.1 document grants no such qualification. |

The classification is engineering metadata, not a user-selected shortcut around qualification.

## Approved modeling rules

- The host component, host face, side, geometry, material, material orientation, layers, position, offsets, holes, attachment classification, structural-credit classification, and qualification source are explicit canonical data.
- A doubler and its host remain distinct components even when their faces coincide.
- Doubler holes reference the canonical bolt centers and participating bolt stacks; rendered holes are not independent data.
- Demand assigned to the doubler is stored separately from demand assigned to the parent component.
- Combined actions affecting the doubler, its attachment, the parent region, or shared bolts must remain identifiable at the relevant interface, component, shared-region, and whole-joint result levels.
- Doubler thickness and parent thickness must **not** be added automatically for resistance, stiffness, bearing, or any other structural credit.
- Visual contact, matching hole patterns, or an attachment label does not establish composite action or load sharing.
- Calculation, rendering, persistence, dimensions, and reporting derive from the same canonical record.

## Fail-closed behavior

- Missing host/face, side, material orientation, required layer, hole, attachment, or qualification metadata produces INCOMPLETE INPUT for a calculation that requires it.
- Incompatible or unresolved canonical geometry produces INVALID GEOMETRY only under an approved geometry rule; otherwise it remains unsupported or subject to engineering review.
- Requested structural credit without an approved method and qualified source produces ENGINEERING REVIEW REQUIRED or CALCULATION NOT SUPPORTED; it cannot produce PASS.
- A geometry-supported doubler remains calculation-unsupported until its calculation scope is separately approved.
- Warnings are supplemental and cannot substitute for an unsupported, incomplete, or review-required status.

## Pending engineering decisions

The following remain **Pending Engineering Decision**:

- permitted doubler materials and orientation requirements;
- attachment classifications and their qualification requirements;
- structural-credit and load-transfer methods;
- treatment of separate and combined actions;
- interaction with the host component, bolt groups, bolt stacks, and shared supporting region;
- whether and when any composite action may be recognized;
- applicability limits and unsupported-condition triggers;
- manufacturer-data and qualification/test-data workflow;
- source, clause, table, equation, and errata mapping; and
- independent verification and qualified engineer approval requirements.

## Stage 0.1 limitation

No attachment criterion, structural-credit method, resistance, capacity, utilization, or PASS/FAIL calculation is specified or implemented.
