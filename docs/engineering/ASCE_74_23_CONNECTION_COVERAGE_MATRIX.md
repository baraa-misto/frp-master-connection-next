# ASCE/SEI 74-23 Connection Coverage Matrix

| Control | Value |
|---|---|
| Document ID | FMC-ENG-MATRIX-001 |
| Stage | 2.2B stateless API overlay on the Stage 0.1 planning register |
| Matrix status | Draft planning register with bounded first-slice implementation status |
| Source mapping | Chapter 8 first-slice mapping verified; broader connection mapping pending |
| Calculation implementation | Authorized Stage 2.1B single-bolt/single-row slice, Stage 2.2A canonical orchestration, and Stage 2.2B stateless transport only; broader roadmap rows not started |

## Control rules

Each row is a versioned capability-coverage record. Stage 0.1 planning rows do not claim calculation support. Geometry support, source coverage, calculation implementation, verification, and engineer approval are independent states. A capability remains fail-closed unless all required states are explicitly approved for its stated scope.

The only allowed **Basis classification** values are:

- Directly covered by ASCE/SEI 74-23.
- Covered elsewhere in ASCE/SEI 74-23.
- Governed by another standard.
- Manufacturer-data dependent.
- Qualification/test-data dependent.
- Documented engineer-defined method.
- Not currently supported.

A clause, table, or equation entry is a controlled reference locator, not reproduced source content. Blank, unknown, or pending source fields cannot be interpreted as code coverage.

## Planning matrix

| Capability ID | User-facing capability | Joint category | Interface or component | Proposed limit state or geometry check | Basis classification | Primary source | Edition | Errata set | Clause, table, or equation reference | Required engineering inputs | Applicability constraints | Unsupported-condition trigger | Verification method | Implementation status | Engineer approval status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CAP-001 | Direct angle brace to W-section column flange | Shear | DirectBoltedInterface between angle brace and column flange; associated BoltGroup, BoltStacks, and supporting region | Interface, member-region, bolt-group, bolt-stack, geometry, and applicability checks to be defined by source mapping | Not currently supported | SRC-001; mapping pending | ASCE/SEI 74-23 | Verification pending | Not mapped | Canonical member geometry and orientation; qualified materials; interface geometry; master bolt centers; holes and ordered stacks; signed member-end actions with combination, frame, and reference point; shared-region context | Not defined; geometry prototyping does not establish calculation applicability | All engineering calculation requests until the source basis, limits, force treatment, and qualification scope are approved; thereafter any condition outside that scope | Controlled source mapping; applicability review; independent hand calculations; known PASS and FAIL cases; boundary and invalid cases; unit-system equivalence; qualified engineering review | Not started | Pending | First target calculation slice. Source mapping required before implementation or commercial validation. Unsymmetrical-angle basis is an open risk. |
| CAP-002 | Angle-column leg directly connected to the back of a channel beam | Shear | DirectBoltedInterface between angle-column leg and channel-beam region; associated BoltGroup, BoltStacks, and shared region | Interface, member-region, bolt-group, bolt-stack, geometry, eccentricity, and applicability checks to be defined by source mapping | Not currently supported | SRC-001; mapping pending | ASCE/SEI 74-23 | Verification pending | Not mapped | Canonical member geometry and directions; qualified materials; connected faces and offsets; master bolt centers; holes and ordered stacks; signed member-end actions with combination, frame, and reference point; load-path and shared-region context | Not defined; exact reference-point and eccentricity treatment remain pending | All engineering calculation requests until source coverage, load path, force treatment, and applicability are approved; thereafter any condition outside that scope | Controlled source mapping; applicability review; independent hand calculations; positive and negative force cases; reversed directions; boundary and invalid cases; unit-system equivalence; qualified engineering review | Not started | Pending | Second target calculation slice. Source mapping required before implementation or commercial validation. |
| CAP-003 | One T-section connecting one beam and two braces to a column | Shear | Shared T ConnectingComponent; three member-to-T interfaces; T-to-support interface; shared bolt groups and supporting region | Per-interface, combined T-component, T-to-support, shared-bolt-group, supporting-region, geometry, equilibrium, and applicability checks to be defined | Not currently supported | SRC-001; other basis may be required and is pending | ASCE/SEI 74-23 | Verification pending | Not mapped | Canonical joint topology; T geometry, faces, zones, material orientation, and qualification; all interface geometry; bolt groups and stacks; signed member-end actions by combination, frame, and reference point; explicit load paths; internal-force stations; shared-region definitions | Not defined; T material basis, combined-demand method, station method, and supporting-region method remain pending | All engineering calculation requests until every required basis and combined-demand method is approved; any missing interface, unqualified material, unsupported force component, or condition outside the eventual scope | Controlled multi-source mapping as needed; applicability review; independent hand calculations; equilibrium and combined-action cases; English/SI equivalence; property-based and integration tests; qualified engineering review | Not started | Pending | Third target calculation slice. Source mapping and T qualification are required before implementation or commercial validation. Independent interface checks alone are insufficient. |
| CAP-004 | Moment beam-to-column connection with optional braces | Moment | Intentionally moment-resisting beam-to-column interface; optional brace interfaces; shared components, bolt groups, and supporting regions as modeled | Combined moment-and-shear interface, component, supporting-region, whole-joint, geometry, equilibrium, and applicability checks to be defined | Not currently supported | SRC-001; other standard, manufacturer, test, or engineer-defined basis may be required and is pending | ASCE/SEI 74-23 | Verification pending | Not mapped | Canonical joint and member geometry; moment-resisting intent; qualified material and component records; all interfaces, bolts, stacks, load paths, and shared regions; signed member-end actions by combination, frame, and reference point; relevant eccentricities | Not defined; engineering basis for moment-resisting FRP joints remains pending | All engineering calculation requests until a complete engineering basis, applicability scope, combined-action method, and qualification path are approved; thereafter any condition outside that scope | Controlled source and qualification mapping; applicability review; independent hand calculations; known PASS and FAIL cases; sign reversal and combined-action cases; boundary and invalid cases; reproducibility tests; qualified engineering review | Not started | Pending | Fourth target calculation slice. Source mapping required before implementation or commercial validation. Optional braces cannot be checked as unrelated when demands share components or FRP regions. |

## Approval and change control

Changing a row from Not currently supported requires a controlled source mapping, verified errata, explicit applicability and unsupported-condition rules, implementation traceability, independent verification, and qualified engineering approval. Implementation status alone never authorizes commercial use. Any change to source edition, errata, material data, manufacturer data, or engineering method reopens the affected verification and approval scope.

## Stage 0.1 limitation

These are roadmap rows, not capability claims. No equation text, numerical criterion, resistance, capacity, utilization, or PASS/FAIL calculation is recorded or implemented.

## Stage 2.1A contract and Stage 2.1B numerical coverage overlay

This overlay controls the authorized first calculation slice and does not mark any
family validated. The broader roadmap rows above remain unsupported except to the
limited contract/applicability extent stated here.

| First-slice area | Schema and applicability | Resistance equation | Source status | Qualification status | Next stage |
|---|---|---|---|---|---|
| Chapter 8 general factor and one-bolt/one-row geometry prerequisites | Implemented as immutable metadata, validation, and planned checks | Implemented only for the authorized Stage 2.1B single-bolt/single-row equations and factors | ASCE/SEI 74-23 Chapter 8 verified; Erratum 1 effective 2026-01-13 does not modify Chapter 8 | Calculation family not independently validated for commercial use | Broader connection scope and independent engineering verification remain future controlled work |
| FRP pin bearing, net tension, shear-out, cleavage, and pull-through planning | Direction, loading-sense, required-input, and fail-closed applicability implemented for the authorized rectangular pultruded-FRP layer family | Executable only for `READY` Stage 2.1B plans; unresolved plans remain uncalculated | Clause/equation references cataloged; no licensed table, figure, commentary, or PDF reproduced | ICE bearing values require engineering review; locked development property set is not an ASTM D7290 characteristic qualification | Multirow, block shear, demand distribution, generated prying, and automatic return-element credit remain excluded |
| Metallic bolt tension, shear, and combined planning | Thread-location and explicit-demand prerequisites implemented | Pure tension and exactly one-plane shear/combined equations implemented for explicit `Fnt` | Locked ASTM F593-17 Group 2 316/316L `Fnt` remains `SOURCE_DATA_PENDING`; synthetic explicit-`Fnt` fixture is non-F593 | No locked F593 resistance qualification is claimed | Zero shear planes remain incomplete and multiple shear planes remain unsupported |
| J1 one-leg angle-to-W resolved fixture | Geometry-to-code mapping and independent check planning implemented; automatic bolt-demand distribution prohibited | Ready constituent single-bolt checks execute; unsupported or inapplicable checks remain uncalculated | Chapter 8 references verified for the constituent planned checks | Whole connection remains `SECTION_2_3_2_QUALIFICATION_REQUIRED`; constituent results do not qualify it | Stage 2.1B does not implement or validate a complete J1 connection design |

Stage 2.1B assigns physical-input `PASS` or `FAIL` only to calculated `READY` checks
inside this bounded overlay. Stage 2.1A planning records and every unavailable check
remain `NOT_EVALUATED`.

## Stage 2.2A orchestration overlay

The implemented application boundary resolves one canonical interface, one selected
bolt in one logical group, its authoritative path, explicit FRP layer assignments, an
explicit fastener snapshot, and an explicit resolved one-bolt demand into the bounded
Stage 2.1A/2.1B slice. P1, PT1, P2A, P2B, J1-T, J1-C, and synthetic B1 are exercised
through canonical geometry in both supported unit systems where required. This does
not expand code coverage: multirow, block shear, group distribution, generated
prying, multiple shear planes, oblique cleavage, automatic return-element credit, and
whole-connection design remain unsupported. J1 remains Section 2.3.2 qualification-
required, ICE remains development-only, and locked F593 `Fnt` remains source-pending.

## Stage 2.2B transport overlay

One strict stateless POST route exposes the existing Stage 2.2A service. The route
rebuilds canonical geometry, material, fastener, and demand inputs; injects trusted
server identity; invokes orchestration once; and serializes its deterministic
response. Transport-valid engineering fail, unsupported, review-required,
qualification-required, source-pending, and no-distribution outcomes remain HTTP 200;
only invalid transport or canonical mapping returns HTTP 422.

This overlay adds no source, equation, applicability, qualification, or connection-
family coverage. Multirow equations, block shear, automatic demand distribution,
generated prying, whole-J1 qualification, ICE production qualification, and locked
F593 `Fnt` resolution remain excluded.
