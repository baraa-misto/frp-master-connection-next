# Single-Bolt Calculation Orchestration Specification

## Status and purpose

This original controlled document records the implemented Stage 2.2A application
boundary. It connects one canonical `JointAssembly` and its exact
`JointGeometryContext` to the already verified Stage 2.1A planning contracts and
Stage 2.1B single-bolt evaluator. It adds no engineering equation and changes no
approved RC2 value, calculation-engine version, or engineering rule-set version.

The only public application operation is
`evaluate_single_bolt_connection(SingleBoltOrchestrationRequest)`. It is synchronous,
deterministic, side-effect free, framework independent, filesystem and network free,
and independent of clock, random, environment, API, persistence, reporting, and user
identity state.

## Canonical request

`SingleBoltOrchestrationRequest` identifies exactly one calculation, assembly,
geometry context, planar interface, logical bolt group, logical bolt location, load
combination, fastener snapshot, bolt diameter, code unit basis, time effect, end-use
factors, and lap configuration. It carries an immutable tuple of explicit
`PenetratedLayerMaterialAssignment` records and may carry both an explicit source
action identity and an `ExplicitBoltDemandAssignment` for that exact interface,
group, and bolt.

The request does not contain display precision, HTTP state, a serialized DTO,
database identity, current time, or a demand-distribution method. One selected bolt
in a multi-bolt logical group is eligible for evaluation only when the caller supplies
an already resolved demand for that exact bolt. The orchestrator never divides a
member-end action by bolt count or iterates the group and labels the result a group
calculation.

## Canonical response

`SingleBoltOrchestrationResponse` retains:

- calculation, assembly, interface, bolt-group, bolt-location, and combination IDs;
- engineering unit system and unchanged project-schema, calculation-contract,
  calculation-engine, and engineering-rule-set versions;
- the existing Stage 2.1A calculation fingerprint when enough input is resolved;
- the exact load combination and unshifted source-action trace when supplied;
- the explicit resolved one-bolt demand, if any;
- the caller-authoritative penetrated-layer order, physical identities, surfaces,
  zones, hole sizes, material assignments, code mappings, and validations;
- the exact fastener snapshot and Stage 2.1B calculation result;
- aggregate status, governing and co-governing check IDs, qualification flags,
  deterministic issues, and warnings.

Frozen slotted records make request and response state immutable. Issue order follows
the deterministic resolution path; only semantically unordered qualification sets are
sorted by stable controlled value. Source objects are retained or read, never mutated.

## Identity resolution and fail-closed behavior

Resolution uses canonical object identity as well as IDs. The supplied geometry
context must retain the exact supplied assembly. The logical and resolved interface,
bolt group, bolt center, bolt path, load combination, participants, physical elements,
material regions, and source action must all belong to that context. The primary
interface must occur in the selected path's connection zones. Unknown, mismatched,
cross-joint, duplicate, or conflicting identities produce explicit orchestration
issues and prevent numerical execution.

The selected physical bolt center and authoritative bolt axis come from the resolved
path. Ordered penetrated layers, entry and exit patches, raw geometry provenance, and
connection zones remain caller-authoritative. A support surface is not accepted as a
penetrated physical layer. Curved or otherwise unsupported targeting and invalid code
geometry propagate as fail-closed issues. The ordinary executable release supports
exactly one shear plane; multiple planes remain unsupported.

## Material and fastener assignment

Every supported FRP penetrated layer requires one explicit assignment keyed by
participant, physical element, and material region. No material is inferred from a
section family, participant kind, label, neighboring layer, or another component.
Several layers may explicitly share the same immutable snapshot. The Stage 2.1B
single-material evaluator cannot consume distinct material snapshots in one call, so
such a request fails closed instead of silently substituting one snapshot.

Metallic penetrated layers are preserved in path provenance and excluded from FRP
resistance plans. Unsupported non-FRP/nonmetal material kinds are not treated as
steel. The locked ICE snapshot remains engineer-provided development data and retains
`ENGINEERING_REVIEW_REQUIRED`. Material orientation is taken from the actual selected
component and region; it controls LW/CW direction selection independently for every
FRP layer.

The fastener snapshot is explicit and unchanged. Its identity, specification and
edition, alloy group, condition, tensile-source status, thread state, diameter,
washer, shear-plane count, and provenance flow into existing planning and evaluation.
The locked ASTM F593-17 Group 2 316/316L snapshot remains source-pending for `Fnt`;
the orchestrator never invents that value. A synthetic snapshot with an explicit,
permitted `Fnt` can run the authorized bolt checks without creating an ASTM F593
qualification claim. Thread status in an FRP bearing layer and thread status in the
bolt shear plane remain independent inputs.

## Actions and explicit bolt demand

Manual member-end actions remain factored member-on-joint actions. When a source
action is selected, it is resolved in its declared frame and at its declared physical
reference point. The response retains that action, the selected bolt center, and the
raw source-to-bolt offset. Stage 2.2A does not automatically shift its moment, discard
eccentricity, distribute it to a bolt group, infer equal sharing, apply an elastic
vector distribution, or invent prying.

`ExplicitBoltDemandAssignment` binds a previously resolved one-bolt demand to the
exact selected interface, group, bolt location, load combination, and source action.
A conflicting binding fails closed. With a source member-end action but no explicit
one-bolt demand, no demand-dependent resistance equation runs and the response retains
`BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED`. With neither a demand nor a source
action, the response reports `RESOLVED_DEMAND_REQUIRED`. This stage defines no demand
distribution equation or provenance for one.

## Geometry-to-code mapping and unit bridge

Stage 2.2A calls the existing Stage 2.1A geometry mapper and validator for each
supported FRP layer. The mapper derives thickness, loaded-end distance, two boundary
traces, effective width, force-to-LW angle, direction family, and authoritative hole
data from the resolved C3 geometry. The selected component's material axes govern
direction; the approved 90-degree endpoint selects the transverse family. No
perpendicular return-element exemption is credited automatically.

One centralized conversion bridge converts finite stored geometry scalars through
`PhysicalQuantity.from_finite_real` and `decimal_from_finite_real`. The source
geometry unit is inches for `US_CUSTOMARY` assemblies and millimetres for `SI`
assemblies. Values are converted through the Stage 2.1A quantity system without
display rounding, quantization, or mutation of geometry. Equivalent US/SI P1 and P2A
requests therefore share physical results, property selection, statuses, governing
IDs, and the existing fingerprint where the approved fingerprint policy defines the
inputs as identical. J1 US/SI calculations reproduce the same approved engineering
values and branch decisions; stored finite geometry remains the unrounded input.

## Planning, equations, aggregation, and fingerprints

The orchestrator builds existing `LayerPlanningInput` and `SingleBoltPlanningInput`
records and reuses Stage 2.1A hole, lap-factor, geometry-factor, mapping, validation,
applicability, status, and fingerprint functions. It then calls only the exported
Stage 2.1B `calculate_single_bolt` entry point. Bolt area, bolt tension, one-plane
shear, combined interaction, pull-through, bearing, net tension, shear-out, and both
cleavage branches remain solely in `frp_master_connection.calculation`; no equation
is copied into the application package.

The Stage 2.1B result remains authoritative for availability, numerical comparison,
aggregate precedence, governing/co-governing results, factor traces, and equation
provenance. Known failure remains visible when another required check is unsupported.
The orchestration layer adds qualification and issue projections but cannot turn an
unsupported, source-pending, or review-required result into ordinary `PASS`.

There is one fingerprint authority: the existing Stage 2.1A
`calculation_fingerprint`. The application supplies its canonical resolved inputs and
does not create a second orchestration fingerprint. Display state, object ordering
where semantically irrelevant, current time, locale, and environment do not enter it.

## Controlled fixture behavior

The canonical orchestration suite exercises P1, PT1, P2A, P2B, J1-T, J1-C, and B1
through real domain, placement, surface, interface, bolt-path, material, fastener,
action, mapping, planning, and numerical objects. P2B retains bearing and net-tension
failure, shear-out pass, unsupported oblique cleavage, and the combined fail-plus-
unsupported aggregate. J1 uses an actual pultruded angle connected leg and W top
flange; the W flange maps to the transverse family, net tension governs J1-T among
calculated checks, and unsupported W-flange cleavage remains visible. Both J1 cases
retain `SECTION_2_3_2_QUALIFICATION_REQUIRED`; no whole-connection ordinary `PASS`
is produced. B1 uses explicit synthetic fastener provenance and does not alter the
locked F593 preset.

The repository RC2 golden JSON is test-only and unchanged. Production orchestration
does not import approved expected values. Direct Stage 2.1B regression tests and the
orchestration fixtures independently reproduce the approved numerical results.

## Stage boundary and API exposure

The Stage 2.2A application core adds no API route or DTO, frontend behavior, persistence, serialized
project/snapshot format, report, authentication, entitlement, billing, dependency,
deployment, multirow equation, block shear, automatic bolt-demand distribution,
joint equilibrium, generated prying, oblique cleavage, additional shear plane, or
whole-connection calculation. It does not qualify ICE data, resolve locked F593
`Fnt`, or qualify J1 under Section 2.3.2.

Stage 2.2B exposes this service through one stateless POST adapter. Strict Pydantic
transport DTOs are mapped into the canonical domain, geometry, and orchestration
contracts; the route then calls `evaluate_single_bolt_connection` exactly once and
serializes its authoritative result without recomputing any equation, status,
fingerprint, or governing identity. HTTP, JSON, identity injection, and decimal-string
transport remain in `frp_master_connection.api`; no delivery concern moves into the
domain, geometry, action, calculation, or application core.

The API requires explicit resolved one-bolt demand for demand-dependent execution.
A valid member-end-action request without an approved distribution method remains a
successful HTTP exchange with the fail-closed engineering outcome
`BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED`. Stage 2.2B adds no distribution,
frontend, persistence, report, or broader calculation behavior.

## Stage 2.3 presentation projection

Stage 2.3 does not change `evaluate_single_bolt_connection`. The API maps the request,
invokes that service once, and passes the unchanged response plus the same canonical
request context to the renderer-neutral visualization builder. The builder may expose
resolved physical geometry, frames, material directions, reference points, and action
directions; it may not distribute demand, invoke an equation, alter a result/status,
or create another fingerprint. Member-end-only requests therefore retain the existing
fail-closed engineering response while still receiving inspectable canonical geometry.

## Stage 2.3R2 server-owned template mapping

The API's `BRACE_TO_COLUMN_FLANGE` template mapper is an outer-boundary constructor,
not a second orchestrator. It validates the current verified member/section/identity
combination and constructs the complete canonical domain and geometry graph before
the same single `evaluate_single_bolt_connection` call. The acute vertical-plane
angle and positive local member extents determine placements on the server; plan
angle remains fixed at zero. The mapper also resolves the action frame and explicit
one-bolt demand reference against that server-built graph.

At the 45-degree defaults the selected bolt, interface, path/layers, code-mapped
loaded-end distance, explicit demand, directional selection, Q12 results, governing
W-flange net-tension result, and Section 2.3.2 qualification are unchanged at the
existing comparison precision. Stage 2.3R2 adds no application service, equation,
demand distribution, status interpretation, fingerprint authority, or calculation
normalization rule.

## Stage 2.3R3 template orientation and interference gate

The orchestration request may carry a resolved brace-to-column template orientation
context containing its semantic inputs and deterministic interference findings.
Findings are evaluated before any resistance plan. Any positive-volume angle/W
intersection returns `INVALID_GEOMETRY` with stable participant, element, and
classification identities and no plans, calculation result, governing check, or
fingerprint. Boundary contact is permitted; arbitrary clearance is not invented.

The current narrow rectangular-prism implementation uses an analytic oriented-box
separating-axis comparison over exact section dimensions and canonical placements.
Dimensional overlap is compared only with the existing interface-distance comparison
policy, while the existing dimensionless mathematical tolerance is used solely to
recognize numerically parallel axes. It is not applied as an inch or millimetre
clearance. This is bounded template validation, not a general CAD/contact engine.

## Stage 2.3R5 preview-resolution boundary

`preview_single_bolt_connection` is a framework-independent, non-design application
service. It reuses the same assembly/context, interface, bolt-group, bolt-location,
bolt-path, penetrated-layer, material-direction, action, geometry-to-code, and
interference resolvers as the design orchestration path. This prevents the browser
from acquiring a second geometry or action authority.

The preview service stops after canonical resolution, visualization projection,
model-status aggregation, and design-readiness classification. It never constructs
or executes a Stage 2.1B resistance plan/evaluator, never aggregates utilization or
design PASS/FAIL, and never creates a calculation fingerprint. A valid member-end
action may therefore preview geometry and action while remaining not design-ready
when explicit one-bolt demand is unavailable. Invalid interference remains fail-
closed and cannot be design-ready. Stage 2.2A design orchestration is unchanged.

## Stage 2.3R6 canonical end-distance provenance

The brace-to-column transport adapter constructs an engineering brace whose selected
bolt station is separated from the connected `START` end plane by the requested
`bolt_to_brace_end_distance`. The existing Stage 2.2A geometry-to-code resolver then
re-derives layer code distances from the placed physical patches and bolt path. No
requested scalar bypasses that mapper or enters a Stage 2.1B equation directly.

Connection-view extents never enter the orchestration request. A separate preview
adapter supplies them only to visualization projection, so changing them cannot
alter the joint station, physical target patches, interference checks, penetrated
layers, hole containment, calculation result, governing identity, or fingerprint.
Directed geometry angles above 90 degrees are resolved by the canonical placement
path; material property direction continues to use the existing backend-resolved
sign-independent acute relationship.
