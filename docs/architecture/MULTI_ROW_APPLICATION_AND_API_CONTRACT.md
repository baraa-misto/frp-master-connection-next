# Multi-row application and API contract

## Controlled scope

Stage 2.4C exposes the verified Stage 2.4B multi-row engine through a pure application
orchestration service and exactly two trusted, stateless HTTP operations:

- `POST /api/v1/calculations/multi-row/preview`
- `POST /api/v1/calculations/multi-row/design-check`

The dependency direction is `API -> application orchestration -> Stage 2.4A
geometry/planners -> Stage 2.4B calculation engine`. The API does not import equation
or engine modules. The frontend communicates only through the API. Production code
does not load golden fixtures.

## Versions

| Contract | Version |
|---|---|
| Multi-row orchestration | `2.4C-RC1` |
| Multi-row API transport | `0.1.0-draft` |
| Multi-row preview | `0.1.0-draft` |
| Multi-row visualization | `0.1.0-draft` |
| Unchanged Slice 2 calculation contract | `2.4B-RC2` |

These identities are additive. Existing single-bolt orchestration, API, preview,
visualization, calculation, golden, and fingerprint identities are unchanged.

## Canonical request

The strict public request carries identities, source metadata, display system, physical
row and bolt-line dimensions, source-unit ordinary-hole identity, ordered FRP layers,
material axes, end-use factors, signed in-plane connection demand, row-demand method,
provenance, optional per-bolt axis tension, lap/time-effect context, first-row method,
and block-shear force-line offset. Boolean-as-number, nonfinite Decimal text, ambiguous
engineer allocation, duplicate identities, client-authored internal results, and extra
fields are rejected.

The backend constructs explicit physical bolt coordinates and boundaries and passes the
actual signed force direction to the accepted geometry resolver. Row identities never
come from input-array order. Source `unloaded_end_e1` and the loaded-boundary-to-Row-1
distance are distinct; both are re-derived from canonical geometry before calculation.
Signed force reversal rebuilds physical row ordering and changes the calculation
fingerprint while demands remain nonnegative.

## Preview boundary

`preview_multirow_connection` resolves geometry, row/line identity, planning
availability, applicability, qualification, material direction, axes, dimensions,
demand graphics, block-path candidates, warnings, and a deterministic preview
fingerprint. Display-only state is excluded from that fingerprint. Preview calls zero
resistance equations, never calls `calculate_multirow_connection`, and returns no
resistance, utilization, numerical comparison, or governing resistance identity.

## Design boundary

`evaluate_multirow_connection` constructs one deeply immutable
`MultiRowExecutionBundle`, including complete block plans rather than path IDs, and
calls `calculate_multirow_connection` exactly once. It returns the accepted engine
result without recalculating or reclassifying it. Warnings, availability,
applicability, qualification, numerical comparison, governing/co-governing identities,
traces, versions, and fingerprints remain engine-authoritative.

The demand is an externally resolved signed connection resultant. The service does not
transform member-end actions, perform general bolt-group distribution, take friction
credit, or generate prying. Missing required bolt-axis tension remains incomplete.

## Public supported scope

The first public family is rectangular, nonstaggered, constant-pitch/constant-gauge
geometry with at least two rows and one or more identical bolts per row; ordinary
source-unit holes; FRP/FRP and FRP/steel material pairs; prescribed two- and three-row
methods; conservative full-row envelopes; and engineer-defined fractions or direct row
forces with confirmed provenance. Physical geometry may contain more than three rows
or bolts per row, but unsupported or nonprescriptive checks fail closed or require the
accepted qualification. Advanced arbitrary layouts and other backend-only plans are
not public controls.

This contract adds no persistence, authentication, reporting, billing, friction,
automatic demand distribution, generated prying, or new engineering method.

## Stage 2.6B automatic group-mode extension

The existing routes and request boundary remain unchanged. Multi-row API transport
schema `0.3.0-draft` adds an optional automatic group-mode integration result to design
responses only. Clients cannot submit Stage 2.6A inputs, results, fingerprints, line
membership, or internal compatibility state.

For automatic design, orchestration runs the accepted Stage 2.5A and Stage 2.5B flow,
constructs each Stage 2.6A input from those exact immutable parents, and calls
`calculate_eccentric_group_mode_compatibility` once per scenario. It never recomputes
line resultants or calls Stage 2.4B directly for eccentric shear-out. The application
merge contract `2.6B-RC1` preserves known FAIL precedence, fail-closed unsupported and
incomplete states, qualification, trace layers, and deterministic fingerprints.

Preview returns no Stage 2.6A result and executes zero Stage 2.6A or Stage 2.4B
resistance. The explicit resolved-demand design path remains byte-for-byte separate and
returns no automatic integration object. The API maps application objects only; it
contains no engineering reduction or calculation entry-point import.
