# Interface and Load Path Model

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 2.2A - one selected planar interface/bolt path may enter bounded calculation orchestration |
| Status | Draft / not frozen |
| Engineering implementation | Canonical geometry and explicit one-bolt-demand orchestration implemented; bolt-group distribution, joint equilibrium, multirow, block shear, and whole-connection calculation remain unsupported |

## Purpose

This document defines how a complete `JointAssembly` records physical interfaces and explicit load transfer. It prevents an interface-only checker from overlooking shared connectors, combined demand, or supporting-member regions. It defines topology and traceability, not resistance equations, force-distribution methods, capacities, or numerical applicability limits.

**Approved boundary:** the software records only a load path supported by user-defined physical topology and an approved engineering method. It must not invent a connector, contact, tributary distribution, restraint, support reaction, or alternate load path to make a joint calculable.

## Physical interface types

Stage 1.2 supplies stable component-scoped `PhysicalSectionElement` and
`MaterialRegion` identities. Stage 1.3B supplies exact local-y/local-z section
primitives, and Stage 1.3C1 supplies exact placed/extruded physical, deferred, and void
geometry for one member or connector at a time. `ParticipantReference`,
`ConnectionInterface`, and `BoltGroup` still target whole declared
participants/interfaces; they do not target a web, flange, wall, leg, stem, physical
longitudinal boundary plane, general face, hole, or penetration. A `JointAssembly`
frame/placement registry is not implemented. The existence of an element ID, placed
analytic extrusion descriptor, end plane, or transform does not create contact, transfer,
distribution, or a load-path edge.

## Stage 1.3C1 placement and Stage 1.3C2A surface boundary

Each Stage 1.3C1 placed member or connector retains one proper resolved global frame,
one explicit local-x extent, one explicit section offset, exact physical-element
extrusions, deferred/void extrusions, and two longitudinal boundary planes. Member
START maps to the minimum-x plane and END to the maximum-x plane; the authoritative
connected end selects one of them without reversing the frame. Connector boundaries
retain neutral minimum/maximum identities, and one shared T connector remains one
component identity even when several future interfaces reference it.

The boundary planes and every deferred/void extrusion are non-targetable geometry.
They are not `ConnectionInterface` records or connection-face references, and they
cannot accept interfaces, holes, bolts, demand, resistance, or engineering status.
Stage 1.3C1 performs no interface placement, participant-face selection, demand
distribution, shared-region definition, or force-reference/eccentricity placement.
Stage 1.3C2A now supplies stable participant-scoped exact physical, end-cut,
void-facing, deferred-junction, and bounded support surface patches. Regular exposed
and end patches are geometrically targetable, while internal/deferred patches are
not. Stage 1.3C2B now associates separate planar target-side geometry with the exact
logical interface and defines bounded zones without modifying `ConnectionInterface`.
That geometric association creates no contact or calculated load-transfer edge.
Holes/bolts are deferred to Stage 1.3C3 or later; force-reference/eccentricity
placement is deferred specifically to Stage 1.3C3.

### Direct member-to-member interface

A `DirectBoltedInterface` represents two physical members bolted directly together. Its participants are the actual member regions and penetrated layers. No artificial plate, connector, or other intermediate component is created simply to satisfy a software data shape.

Examples in the approved roadmap include an angle brace connected directly to a column flange and an angle-column leg connected to the back of a channel beam. These are planning examples only; their engineering bases remain unsupported until source mapping, applicability definition, independent verification, and engineering approval are complete.

### Member-to-connecting-component interface

This interface represents a member attached to a real `ConnectingComponent`, such as a T-section, plate, angle, gusset, or bracket. Each interface identifies both participants, the participating faces/regions, fasteners or other classified attachment, and its association with load paths.

### Component-to-support interface

A connecting component may transfer accumulated demand to a supporting member through a separate interface. For a shared T-section, the brace-to-T and beam-to-T interfaces do not replace the T-to-support interface. Demand reaching the T must be retained and transferred through the actual T-to-support attachment and region.

### Reinforcement participation

A doubler or other reinforcement is a first-class component. Its attachment and claimed participation must be explicit. Merely overlapping a host in geometry does not transfer load or grant structural credit. Structural-credit methods for doublers are a **Pending Engineering Decision**.

## Shared entities

### Shared connecting component

A shared connecting component participates in more than one interface or receives more than one concurrent demand contribution. One T-section may, for example, attach a beam and two braces and then transfer their combined demand to a column.

Independent interface checks do not establish adequacy of the shared component. The model must preserve the concurrent demands for component-level checks, internal-force stations where applicable, its support attachment, and any shared bolt group.

### Supporting-member region

A supporting-member region is the physically bounded portion of a member relied upon to receive one or more interface/component demands. It is identified separately from the full member so that overlapping or interacting demands are not lost.

### Shared region

A `SharedRegion` is an explicit aggregation boundary used when two or more load paths affect the same component zone, supporting-member region, reinforcement region, bolt group, or other qualified engineering region. It records contributors, combinations, participating physical region, and intended check association.

The method for deciding which supporting regions interact and how their demands combine is a **Pending Engineering Decision**. Until approved, the affected condition is not calculation-supported.

A Stage 1.2 `MaterialRegion` is not this `SharedRegion`: material-region membership
records common LW/CW/TT classification, whereas shared-region membership records
future demand interaction under an approved method.

## Load-transfer graph

The load-transfer graph is a directed, traceable representation of physical transfer within one joint and one load combination.

### Node roles

- action application/reference points on connected members;
- participating member regions;
- direct or connector-assisted interfaces;
- bolt groups or other explicitly classified attachment groups;
- connecting and reinforcement components or their engineering zones/stations;
- shared regions; and
- supporting-member regions or an explicitly defined reaction boundary.

### Transfer edges

An edge means that an approved engineering model transfers demand between two named physical participants. Each edge retains the combination, symbolic frame identity, resolved-frame provenance when explicitly associated, source and destination reference points, source and destination participants, applicable interface or region, and method/basis identity when implemented. A Stage 1.3C1 component placement may later supply geometric frame provenance, but never creates the edge.

Stage 1.3A proper rotations and rigid transforms may express a declared edge in a common frame only after later integration, but they do not authorize an edge or distribute demand. Stage 1.3C1 does not invoke them to resolve force points or discover eccentricity. Force and moment rotate at the same physical reference point with the same proper rotation. Moving a force/moment system between explicit physical points is a separate operation in one identified common frame:

```text
F_Q = F_P
M_Q = M_P + (r_P - r_Q) cross F
```

No edge may reverse that offset, infer either point, or shift an action automatically.

Rendering adjacency, mesh intersection, drawing coincidence, naming similarity, or template membership cannot create an edge. Every transfer edge must be traceable to canonical topology and an approved calculation capability.

### Branching, convergence, and cycles

- A branch is recorded only when a qualified method defines how demand is distributed among real outgoing paths.
- A convergence identifies the shared component or region receiving combined concurrent demand.
- An ambiguous branch is not automatically divided equally or by apparent stiffness.
- An unexplained cycle or alternate path is invalid topology or requires engineering review; it is not resolved through a hidden solver assumption.

## Building and evaluating a load path

For each load combination, the conceptual process is:

1. Start with each signed `MemberEndAction`, including its member, explicit frame, and explicit reference point.
2. Preserve any eccentricity between that reference point and the first physical interface; perform a shift only through an explicit source point, target point, and common frame.
3. Follow only declared interfaces through actual bolts, penetrated layers, connecting components, reinforcement, and supporting regions.
4. Retain signed vector/directional context, symbolic and future resolved frame provenance, connected-end identity, explicit reference point, and the contributing source at every transfer; do not replace concurrent demands with unrelated scalar interface checks.
5. Aggregate contributions at shared components, bolt groups, and regions only under a qualified method.
6. Trace every credited path to its defined reaction boundary and perform or verify whole-joint equilibrium under an approved method.
7. Produce results at every required scope and retain traceability between parent and child results.

This is a conceptual control sequence, not an implemented force-distribution algorithm.

Member local x remains `START` to `END` regardless of connected end. Under the approved
member-on-joint action convention, positive local `Fx` at `START` is tension and negative
is compression; at `END`, negative is tension and positive is compression. Zero is zero.
This controlled interpretation does not rewrite `Fx`, create an edge, or reverse a frame.

## Combined-demand requirements

**Approved:** shared connectors receive combined-demand checks, and shared supporting-member regions receive combined checks where applicable. Moment and shear demands are not treated as unrelated when they share a component or FRP region.

Accordingly:

- a passing result for every member-to-T interface cannot substitute for a check of the shared T;
- a passing result for a shared T cannot substitute for its T-to-support interface, shared bolt group, or supporting-member region;
- results from different load combinations are kept distinct unless an approved envelope rule explicitly relates them;
- contributions within the same combination retain sign and direction; and
- incomplete contributor sets or an unqualified combination method fail closed.

The exact multi-interface combination methods, T internal-force model, shared-region methods, and whole-joint aggregation rule are **Pending Engineering Decisions**.

## Result hierarchy

| Result level | Required question | Typical association | Boundary |
|---|---|---|---|
| Interface | Can this specific physical interface be evaluated for this demand and basis? | Direct interface, member-to-component interface, component-to-support interface | Does not establish adequacy of a shared component or host region. |
| Component | Can the actual connecting/reinforcement component and its qualified zones be evaluated for all applicable contributions? | T-section, doubler, shared bolt group | Must include combined demand when shared. |
| Shared region | Can interacting contributions in the same physical region be evaluated by a qualified method? | Supporting-member region, overlapping component zone | Cannot be omitted because incoming interface checks pass. |
| Whole joint | Are required child scopes present, equilibrium addressed, and the complete assembly acceptable under an approved aggregation rule? | `JointAssembly` and load combination/envelope | Exact status aggregation is pending; no optimistic default is permitted. |

Every higher-level result references the lower-level results and contributors on which it relies. A missing required child result cannot be interpreted as `PASS`.

## Equilibrium and reaction boundary

Joint equilibrium must be calculated or verified, but the supporting-reaction convention and approved equilibrium procedure are **Pending Engineering Decisions**. The approved member convention does establish global `+Z` upward, member local x fixed `START` to `END`, and connected-end axial interpretation. The model must retain all applied member actions, explicit reaction boundary assumptions, transformations, and unresolved components needed for independent verification.

If the reaction boundary is missing, a force component is unsupported, an eccentricity is discarded, or the path does not terminate through qualified physical topology, the joint cannot receive `PASS` or `FAIL` from a placeholder. It must fail closed with the applicable non-success state.

## Capability and status controls

Geometry support and calculation support are independent. A load-transfer graph may be visualized for an unqualified joint, provided it is clearly labeled conceptual/unsupported and does not imply a validated calculation.

The controlled result states are:

- `PASS`
- `FAIL`
- `INVALID GEOMETRY`
- `NOT APPLICABLE`
- `NOT COVERED BY SELECTED CODE`
- `ENGINEERING REVIEW REQUIRED`
- `CALCULATION NOT SUPPORTED`
- `INCOMPLETE INPUT`
- `STALE RESULTS`

`PASS` and `FAIL` are reserved for complete, applicable, source-mapped, versioned, verified, and engineer-approved calculation capabilities. Warnings add context but cannot replace a required unsupported, incomplete, stale, or review-required status.

Examples of fail-closed triggers include:

- an undeclared or disconnected load path;
- apparent geometric contact without a modeled physical interface;
- an unsupported action component or unresolved reference-point eccentricity;
- an unqualified demand distribution, combination, shared-region, or doubler-credit method;
- an unqualified material or manufacturer data source;
- omitted shared component, shared bolt-group, supporting-region, or reaction-boundary checks;
- invalid or incomplete bolt-stack/layer topology; and
- missing standard edition, errata, rule-set, or applicability evidence.

## Mixed-topology example boundary

The foundation geometry prototype may depict one column, one beam, two braces, one shared T connector, one direct bolted interface, one doubler, multiple member directions, bolt groups, and bolt stacks. It may illustrate simultaneous direct and connector-assisted paths and their shared regions. It must produce no engineering `PASS` result.

## Pending and provisional items

### Pending Engineering Decision

- Supporting-reaction convention and template-specific allowed reference points.
- Multi-interface demand combination and shared supporting-region methods.
- T-connector qualification and internal-force evaluation.
- Doubler structural-credit method.
- Engineering bases for unsymmetrical angle-brace and moment-resisting FRP connections.
- Whole-joint status aggregation.

### Provisional architecture

- Represent load transfer as an explicit graph derived from canonical domain topology.
- Use deterministic, side-effect-free calculation functions after engineering qualification.
- Record versioned, JSON-compatible traceability and canonical fingerprints.

These items remain non-approved until processed through the decision register. No implementation may silently settle a pending engineering matter.

## Stage 1.3C2B geometry association

The logical `ConnectionInterface` remains the only participant relationship and
transfer-intent record. A separate framework-independent geometry specification retains
that exact interface and resolves participant-scoped Stage 1.3C2A patches into bounded
first and second target sides. `participant_a` is always first, its signed surface
normal defines interface `+x`, and no participant or normal is automatically reversed.

Multi-patch zones, the primary geometric reference, explicit interface origin, local
frame, and raw signed plane separation do not create a load-path calculation, contact
state, force distribution, or calculation-support declaration. Geometry support and
calculation support remain separate under APR-022.

## Stage 1.3C3 geometry available to future load paths

Resolved bolt groups now retain exact logical interface participation, master centers,
axes, intended penetrated layers, surface/zone associations, round holes, and ordered
raw stack geometry. Resolved manual actions retain exact physical source points and may
be explicitly shifted to an explicitly resolved target with full eccentricity
provenance. These records are geometric/action prerequisites only. They do not create a
load-transfer edge, decide a permitted template point, distribute demand, combine
interfaces, establish equilibrium, classify bearing or shear planes, or approve a
calculation capability.

## Stage 2.1A demand and applicability boundary

The first-slice `ResolvedDemand` binds an already resolved C3 force at an explicit
point and frame to one physical layer. It records the in-plane resultant, loading
sense, bolt-axis demand when explicitly supplied, and an explicit distribution state.
It never infers a load path, chooses a reference point, shifts a moment, discovers
eccentricity or prying, or distributes a joint/interface demand to a bolt.

Applicability planning may declare a limit state ready, not applicable, unsupported,
incomplete, invalid, source-pending, engineering-review-required, or
demand-distribution-unsupported. These states do not create a load-transfer edge or
numerical result. The J1 one-leg angle-to-W fixture additionally retains the
whole-connection ASCE/SEI 74-23 Section 2.3.2 qualification requirement; independent
Chapter 8 single-bolt plans do not satisfy that whole-connection requirement.

## Stage 2.2A selected-interface and bolt-path use

Orchestration requires the selected planar interface to be represented by connection
zones in the exact selected bolt path. It preserves the authoritative bolt center,
axis, ordered penetrated layers, entry/exit surfaces, and interface set. An explicit
resolved demand must bind to that interface, group, bolt location, load combination,
and source-action provenance before demand-dependent checks can execute. A member-end
action alone remains undistributed: there is no equal-share, centroid, elastic-vector,
moment-shift, prying, equilibrium, multirow, or block-shear inference.
