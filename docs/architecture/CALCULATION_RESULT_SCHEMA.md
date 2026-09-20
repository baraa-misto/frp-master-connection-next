# Calculation Result Schema

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 2.2B - deterministic stateless API projection over canonical orchestration |
| Status | Draft / not frozen |
| Calculation engine | `0.1.0.dev1`; bounded single-bolt/single-row scope only |

## Purpose and boundary

This document defines the information a structured calculation result must preserve for traceability, applicability, reproducibility, future UI display, and reporting. Stage 2.1B implements the bounded internal result and Stage 2.2A projects it through an immutable application response. This document does not define an API payload, database table, equation, resistance factor, report schema, or broader capacity/utilization method.

A result records what an approved, versioned calculation attempt established. It must never manufacture engineering content that the calculation did not produce. Summary and Detailed reports consume the same immutable structured result data.

## Result scopes

Results may exist at four related levels:

| Scope | Purpose |
|---|---|
| Interface result | Records a check for one actual direct or connector-assisted interface. |
| Component result | Records a check for a connecting/reinforcement component or shared bolt group, including combined contributors where applicable. |
| Shared-region result | Records a check for interacting demands in a defined supporting/component region. |
| Whole-joint result | References required lower-level outcomes, equilibrium/applicability outcomes, and the joint-level status under an approved aggregation rule. |

Passing interface checks do not imply a passing shared component, supporting region, or whole joint. Required child results and contributor links must remain explicit. The exact whole-joint aggregation rule is a **Pending Engineering Decision**; an absent rule cannot default to `PASS`.

## Conceptual result fields

| Field | Meaning | Presence and control |
|---|---|---|
| Check ID | Stable identity of the check instance/type within the snapshot. | Required and unambiguous. It must not be reused for a different engineering meaning. |
| Project ID | Engineering project/document identity used for the calculation. | Required. Account/organization ownership is outside the engineering fingerprint. |
| Joint ID | Canonical `JointAssembly` identity. | Required for joint calculations. |
| Interface ID | Canonical interface associated with the result. | Required for interface-scoped checks; otherwise absent. A synthetic interface must not be invented. |
| Component ID | Canonical connecting, reinforcement, fastener group, or member component associated with the result. | Required when the check relies on a component; otherwise absent. |
| Physical section element ID | Component-scoped physical occurrence associated with a future local demand/check. | Future field; requires its owning participant/component ID and is not populated by Stage 1.2. |
| Material region ID | Component-scoped material-orientation/property grouping used by a future directional check. | Future field; distinct from a shared-demand region and not populated by Stage 1.2. |
| Cross-section geometry identity | Future immutable association to the component's exact nominal `CrossSectionGeometry2D`, its standard family, dimension inputs, idealization/profile kind, and owning length-unit context. | Future provenance only; Stage 1.3B creates no owner association, serialization, fingerprint, or result record. |
| Section geometry feature ID | Physical-element ID, deferred-feature ID, or nominal-void ID plus feature kind and geometry provenance. | Future trace field. Only a physical-element occurrence may become targetable; deferred features and voids must never be reported as calculated targets. |
| Construction datum | Exact local `(0,0)` outside-bounding-box center and component-local y-z convention. | Future geometry trace only; must remain distinct from centroid, shear center, analytical line, joint point, and action reference point. |
| Surface-patch reference | Future participant plus participant-scoped stable surface-patch ID. | Stage 1.3C2A geometry provenance only; `ConnectionInterface` does not use it and no calculation result is implemented. |
| Surface source and state | Physical-element/deferred-feature/support source, exact geometry kind, exposure, disposition, signed planar normal or radial sense, and derived geometric targetability. | Targetability is not applicability, code coverage, attachment, demand, resistance, or calculation support. |
| Symbolic coordinate-frame reference | `CoordinateFrameReference` identity and owner provenance for the frame in which an action or point was authored. | Future result/input provenance; Stage 1.3A does not serialize or populate result records. |
| Resolved frame basis | Finite origin and right-handed orthonormal x/y/z axes expressed in an identified parent/global frame, with frame-construction provenance. | Future directional trace only. It must not replace the symbolic frame reference or imply assembly placement. |
| Force/moment reference point | Explicit point identity and common-frame identity used for the reported force/moment system. | Future directional trace; a target point must never be inferred. |
| Reference-point shift provenance | Source point, target point, common frame, and explicit use of `M_Q = M_P + (r_P - r_Q) cross F`. | Future field only when an approved calculation explicitly performs the shift. Automatic shifting is prohibited. |
| Action direction provenance | Component (`FX` through `MZ`), linear/rotational kind, signed value, resolved parent/global axis, sign/sense, and zero status. | Future display/calculation trace derived from canonical Stage 1.3A mathematics; contains no rendering style. |
| Shared-region ID | Canonical shared/supporting region associated with the result. | Required for shared-region checks; otherwise absent. |
| Limit state | Controlled semantic name of the engineering condition evaluated. | Required for an engineering check. A placeholder name does not authorize a result. |
| Governing standard | Controlled source identifier for the governing basis. | Required when a standard governs; another basis classification must be explicit when it does not. No copyrighted equation text is stored here. |
| Edition | Edition of the governing source. | Required when source-dependent. |
| Errata | Verified errata/correction-set identifier or explicit verification-pending marker. | Required when source-dependent. Verification pending prevents unsupported source-dependent success. |
| Rule-set version | Version of the implemented and approved engineering mapping. | Required for a calculated engineering result. `Not implemented` is not a passing rule set. |
| Clause or equation reference | Precise source locator used for traceability. | Required when applicable and permitted; store a citation, not reproduced licensed content. |
| Applicability status | Structured conclusion about whether the selected rule/basis applies to the supplied condition. | Required and distinct from result status. Exact vocabulary and rules require engineering approval. |
| Inputs | Normalized engineering inputs actually consumed, with quantity identity, value, unit/dimension, source entity, and relevant frame/reference point. | Required for an executed check; protected/proprietary source content is referenced, not copied unnecessarily. |
| Intermediate values | Named, unit-aware values necessary to independently trace the approved method. | Present when produced by a supported check; absent when no approved calculation ran. |
| Nominal resistance | Unit-aware nominal resistance produced by the qualified method. | Present only when the approved method produces it. Optional/absent for unsupported, incomplete, not-applicable, or review-only outcomes. |
| Resistance factor | Identifier/value and provenance of the approved factor applied by the rule set. | Present only when applicable and produced by an approved method. No Stage 1.3B value is defined. |
| Design resistance | Unit-aware design resistance produced by the qualified method. | Present only when applicable and successfully calculated. |
| Demand | Unit-aware demand at the check scope, with traceable contributor/load-combination references. | Present only when it is defined and successfully derived without dropping unsupported components. |
| Utilization | Dimensionless comparison produced by the approved rule set. | Present only for a complete applicable calculation; never fabricated for presentation. |
| Result status | One controlled fail-closed result state. | Required. `PASS`/`FAIL` are reserved for qualified completed calculations. |
| Warnings | Supplemental structured issues with identifiers, severity/display information, and affected entities. | Optional; cannot substitute for a required non-success result status. |
| Assumptions | Explicit, controlled assumptions actually permitted by the approved method. | Present when used. Assumptions cannot silently settle a pending engineering decision. |
| Calculation fingerprint | Deterministic digest identifying normalized engineering inputs and applicable version/data context. | Required for a reproducible calculation snapshot after the fingerprint contract is approved. |

Where multiple IDs apply, all are retained. For example, a component result may also identify contributing interfaces and a shared region. An inapplicable identifier remains absent; it is not populated with a zero, empty synthetic object, or misleading default.

## Quantities and provenance

Inputs, intermediate values, demands, and resistances are conceptual unit-aware quantities rather than unlabeled numbers. Each stored quantity must retain enough metadata to determine its physical dimension, canonical value, display conversion, and source frame/reference point where directional behavior matters.

The exact internal canonical unit system is a **Pending Engineering Decision**. Until resolved, an implementation cannot claim unit-dependent equation verification. Display units never change an immutable engineering value.

Result provenance must connect to:

- the calculation snapshot and canonical input fingerprint;
- project schema and calculation-engine versions;
- engineering rule-set version;
- governing source, edition, errata set, and source locator;
- material, section, and manufacturer-data versions relied upon; and
- capability/applicability and engineer-approval records.

The private licensed source itself is not embedded in a result. Source citations and control metadata are sufficient for traceability.

The future directional trace is authored action and symbolic frame reference → resolved
Cartesian frame → explicit reference-point operation → owning component and its placed
cross-section → physical section element → material region → material orientation rule →
future material property set → qualified directional property. Stage 1.2 implements
element/region identities and orientation rules. Stage 1.3A implements reusable proper
rotations, rigid transforms, explicit force/moment shifting, axial-sense interpretation,
and renderer-neutral action directions. Stage 1.3B maps exact nominal standalone
geometry to standard-topology physical elements while preserving deferred non-targetable
features and nominal voids. It does not associate geometry with a `JointAssembly`,
resolve frames, target demand, implement `MaterialPropertySet`, calculate section
properties, perform property lookup, populate a result record, or calculate demand,
resistance, capacity, stress, or utilization.

## Controlled result states

| Result status | Intended meaning and boundary |
|---|---|
| `PASS` | A complete, applicable, qualified, versioned, source-mapped, independently verified, and engineer-approved check establishes acceptance under its approved rule set. |
| `FAIL` | The same qualified check establishes non-acceptance under its approved rule set. |
| `INVALID GEOMETRY` | Supplied geometry is internally invalid or violates a prerequisite that prevents the intended evaluation. It is not a zero-capacity result. |
| `NOT APPLICABLE` | This check is legitimately outside the condition requiring that specific check. It does not prove other required checks are present or passing. |
| `NOT COVERED BY SELECTED CODE` | The selected standard/rule basis does not cover the condition. Another basis may not be invented silently. |
| `ENGINEERING REVIEW REQUIRED` | The condition requires a qualified engineering determination that has not been encoded/approved or cannot be resolved automatically. |
| `CALCULATION NOT SUPPORTED` | Product capability for this requested calculation is not implemented, qualified, approved, or available. Geometry may still be displayable. |
| `INCOMPLETE INPUT` | One or more required engineering inputs, versions, frames, reference points, qualifications, or topology items are absent. |
| `STALE RESULTS` | The result belongs to an older engineering input/version context and is not current for the active document. The historical snapshot remains immutable. |

Warnings are supplemental. A warning cannot replace `CALCULATION NOT SUPPORTED`, `INCOMPLETE INPUT`, `STALE RESULTS`, `ENGINEERING REVIEW REQUIRED`, or any other required status.

## Fail-closed field rules

1. Capacity-related fields may be absent for unsupported, incomplete, invalid, not-applicable, not-covered, review-required, or stale contexts.
2. Absence of nominal resistance, resistance factor, design resistance, demand, utilization, intermediate values, or applicability evidence must never be converted to zero, infinity, a benign blank, `PASS`, or `FAIL`.
3. A placeholder, catch-all, unverified source mapping, or provisional equation may never return `PASS` or `FAIL`.
4. Unsupported force components, unresolved eccentricities, missing shared-component/region checks, and missing equilibrium verification remain visible in status and traceability.
5. An exception, timeout, data-access failure, or version mismatch is not an engineering `FAIL`; it produces a controlled non-success/error outcome and no fabricated engineering status.
6. A result with warnings but no required status is invalid result data.
7. Frontend formatting, visibility, filtering, or color never changes stored status.
8. A deferred heel, tube corner, web/stem-flange junction, or nominal void may never be
   promoted to a physical-element target or assigned a calculated demand/capacity by
   result normalization.
9. A rendered mesh or round-tube tessellation may never supply canonical geometry or
   section-property values to a result.

## Applicability versus result status

Applicability is recorded separately because a rule can be outside its valid scope before resistance is considered. The applicability record should identify the capability, basis classification, evaluated constraints, unsupported-condition trigger, evidence, and conclusion.

The exact applicability vocabulary and evaluation rules are **Pending Engineering Decisions**. Until a calculation slice has source mapping, defined applicability, independent verification, and engineer approval, its requested checks return an appropriate fail-closed non-success state rather than `PASS` or `FAIL`.

## Result tree and aggregation

A whole-joint result is a traceable tree or graph of required results, not a single detached flag. It records:

- load combination or approved envelope context;
- contributing member-end actions;
- interface results;
- component and shared bolt-group results;
- shared/supporting-region results;
- joint equilibrium/applicability results;
- missing or unsupported required checks; and
- the approved aggregation rule/version when one exists.

The whole-joint status cannot be more favorable than permitted by its required unresolved children. The precise precedence among non-success states and the treatment of `NOT APPLICABLE` are **Pending Engineering Decisions**. Until approved, ambiguity fails closed.

## Snapshots, reports, and staleness

A `CalculationSnapshot` preserves the normalized input document/version context, calculation fingerprint, calculation attempt metadata, structured result graph, and warnings/assumptions. It is immutable.

When engineering inputs change, the historical snapshot is not edited. The active project instead treats it as `STALE RESULTS` and requires an explicit recalculation under the currently selected versions. Historical viewing clearly identifies the old input and rule/data context.

A `ReportSnapshot` references one immutable calculation snapshot and freezes the report presentation context. Summary and Detailed reports use the same result graph. Report generation may format or select detail, but it may not recalculate values, change applicability, suppress a required non-success status, or turn missing capacity into a result.

## Versioning note

The application version is `0.0.0.dev0`, project schema is `0.1.0-draft`, and
calculation engine and engineering rule-set remain `not-implemented` at Stage 1.3C2B.
The resolved interface geometry's raw signed plane separation and coincidence comparison
are geometry inspection data, not contact, fit, adequacy, demand, resistance, status,
or a `CalculationResult`. Therefore this document authorizes no populated engineering
`PASS`, `FAIL`, resistance, utilization, capacity, section-property, contact, or
reference-shift result record. Serialization of Stage 1.3A through Stage 1.3C2B
geometry/action objects remains deferred.

Version contract, canonical normalization, fingerprinting, snapshot, migration, and stale-result controls are further specified in `DATA_VERSIONING_AND_REPRODUCIBILITY.md`.

## Stage 1.3C3 future result provenance boundary

A future calculated result that relies on Stage 1.3C3 geometry must preserve the exact
assembly and logical bolt-group identities; primary and participating interfaces;
group frame/origin; master centers and authoritative axes; path-specific declared layer
order; physical-element, entry/exit patch, and connection-zone references; exact round-
hole diameter/cylinder; raw patch/zone clearances, layer thicknesses, interlayer gaps,
and total spans; explicit geometric comparison tolerance; and unit-system identity.

For an action transfer it must also preserve the original action/frame/reference point,
resolved physical source and target points, exact output frame reference/basis, raw
source-minus-target offset, input force/moment, eccentricity cross product, and shifted
moment. Stage 1.3C3 creates no result schema instance, calculation snapshot,
fingerprint, capacity, utilization, or status.

## Stage 2.1A planned-check and status contract

Stage 2.1A implements the framework-independent schema that precedes a numerical
calculation result. A `PlannedCheck` preserves stable check identity, limit-state
identity, applicability/readiness, final availability, required/not-required state,
issues, source references, qualification references, and the future equation
reference. These are planning records, not calculated resistance results.

Final availability and numerical comparison are independent dimensions. Availability
is one of `READY`, `NOT_APPLICABLE`, `UNSUPPORTED`, `INCOMPLETE_INPUT`,
`INVALID_GEOMETRY`, `SOURCE_DATA_PENDING`, `ENGINEERING_REVIEW_REQUIRED`, or
`DEMAND_DISTRIBUTION_UNSUPPORTED`. Numerical comparison is exactly `PASS`, `FAIL`, or
`NOT_EVALUATED`; every physical Stage 2.1A plan is `NOT_EVALUATED`. The aggregate
status applies fail-closed precedence and may retain multiple co-governing check IDs
without choosing one arbitrarily.

Stage 2.1A also defines immutable source/property/fastener snapshots, resolved demand,
geometry-to-code mapping, check plans, aggregate status, and a canonical fingerprint.
It does not create resistance, capacity, utilization, calculated physical-input
`PASS`/`FAIL`, a persisted calculation snapshot, an API schema, or a report result.
Stage 2.1B now supplies those fields only for `READY` plans in the authorized
single-bolt slice. `FinalCalculationResult` retains its complete `PlannedCheck`, final
availability, independent numerical comparison, demand, nominal/design resistance,
utilization, structured equation trace, source snapshot, and warnings. An unavailable
result contains no numerical data and remains `NOT_EVALUATED`.

`SingleBoltCalculationResult` preserves exact plan/result order, aggregate status,
governing/co-governing check IDs, input fingerprint, calculation-engine version, and
engineering-rule-set version. Exact equality passes; no tolerance changes a component
PASS/FAIL comparison. The single `1E-12` tolerance is used only to retain governing
ties. Known failure precedes unsupported required work, while unsupported required
work prevents aggregate PASS in the absence of a known fail. Persistence, API DTOs,
project serialization, and reports remain absent.

## Stage 2.2A orchestration projection

The framework-independent application service now projects one canonical request into
the existing result without changing its meaning. Its immutable response carries the
selected assembly/interface/bolt identities, ordered physical-layer and assignment
traces, explicit demand or unshifted source-action provenance, versions, the one
existing fingerprint, the complete Stage 2.1B result, aggregate status, governing
IDs, qualifications, and deterministic fail-closed issues. Application issues never
replace or soften calculation availability or aggregation. This is an in-memory
contract only; it is not an API DTO, persistence schema, report model, or project-
schema change.

## Stage 2.2B transport projection

The API response is a transport DTO, not a second result model. It preserves the
Stage 2.2A response and Stage 2.1B plan/result order, availability, independent
comparison, traces, aggregate, governing IDs, qualifications, issues, and fingerprint
without recalculation. Decimal values are strings and physical values have explicit
profile units. Concise source locators replace internal source objects; licensed text
and PDF paths are excluded. HTTP 200 also carries valid engineering non-success
states, while HTTP 422 is limited to malformed transport/canonical mapping.
Persistence and report schemas remain unimplemented.

## Stage 2.3 workspace and visualization projection

The workspace renders the Stage 2.2B result without creating a frontend result model
or expected-result oracle. Aggregate, governing IDs, qualification/review flags,
fingerprint, versions, plans, results, source IDs, warnings, issues, and equation
traces remain server-authoritative. A valid known numerical failure is shown as a
failure; unsupported/source-pending/not-applicable work remains non-calculated; J1
qualification is not presented as ordinary PASS.

The additive `visualization` object is adjacent renderer-neutral evidence, not a
calculation result and not fingerprint input. Editing any case or engineering input
removes the currently displayed response and marks it stale until reevaluation.

## Stage 2.3R compact presentation projection

The result remains unchanged. The normal table projects exactly seven columns:
component/layer, limit state, status, demand, design resistance, utilization, and
source/details. User-facing labels are presentation mappings over stable server IDs.
For normal reading, force and resistance quantities use three decimals and
utilization uses three decimals plus percent. Expanded details retain exact returned
decimal strings, factors, intermediates, source/equation identifiers, warnings, and
internal check/component/layer IDs. Rounded values are never compared or sent back
as calculation authority.
