# Single-Bolt Calculation API Contract

| Control item | Value |
|---|---|
| Stage | 2.2B transport with Stage 2.3R2 template/visualization additions |
| Route | `POST /api/v1/calculations/single-bolt/evaluate` |
| Transport schema | `0.3.0-draft` |
| Application | `0.0.0.dev0` |
| Calculation engine | `0.1.0.dev1` |
| Engineering rule set | `asce74-23-ch8-single-bolt-rc2.dev1` |
| Status | Implemented, provisional, not frozen |

## Boundary

The route exposes the existing Stage 2.2A `evaluate_single_bolt_connection` service
for one selected logical bolt in the verified single-bolt/single-row slice. The API is
an outer transport adapter. It does not contain equations and does not call
`calculate_single_bolt` or equation primitives. Domain, geometry, actions,
calculation, and application packages do not depend on FastAPI or Pydantic.

Each request is a complete declarative calculation snapshot. The server validates
it, reconstructs actual canonical assembly, standard-section, placement, surface,
interface, bolt-path, material, fastener, action, demand, and `JointGeometryContext`
objects, calls orchestration exactly once, serializes the authoritative response, and
stores nothing. There is no project, calculation, report, cache, database, generated
identifier, timestamp, or filesystem payload.

## Trust and identity

The route reuses the single server-selected trusted identity resolver. Identity,
organization, roles, authorization, and entitlement are not request fields and do not
enter engineering results or fingerprints. Stage 2.2B adds no authorization or
entitlement policy. Production composition retains its existing fail-closed identity
configuration; clients cannot override identity through JSON or headers.

Clients also cannot provide authoritative engine/rule versions, fingerprints,
availability, comparison, capacity, utilization, or governing results. Those values
come only from the application/calculation response.

## Request

`SingleBoltEvaluationRequestDTO` uses forbidden extras, controlled enums, validated
identifiers, strict Boolean/string fields, and decimal-string quantities with explicit
controlled units. Numeric JSON floats and Booleans are rejected where decimal strings
are required; malformed, NaN, infinite, missing, extra, and unsupported values are
HTTP 422 transport errors.

The declarative geometry scope is intentionally narrow: placed member components
using plate, angle, wide-flange, or I-section standard factories; planar rectangular
surface patches and whole-patch zones; one planar interface; one logical bolt group;
ordered round-hole penetrated layers; and explicit tolerances/reference directions.
The mapper uses one centralized Decimal-to-finite-geometry scalar bridge and then the
unchanged Stage 2.2A geometry-to-Decimal bridge. Custom CAD, solid round, cylindrical
targeting, contact, and fit are excluded.

Material snapshots retain property source and qualification metadata. A client
claiming the locked ICE identity must reproduce the exact approved development
snapshot. Locked ASTM F593 Group 2 316/316L metadata are similarly protected and
retain missing `Fnt`; a generic stainless value is never substituted. Explicit
synthetic `Fnt` remains user-defined/development-only and makes no F593 qualification
claim.

Demand is either an explicit resolved one-bolt demand bound to the exact interface,
group, location, combination, source action, and reference, or a source member-end
action without resolved bolt demand. The latter is retained unshifted and returns the
existing `BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED` outcome. The API performs no
equal sharing, centroid distribution, joint equilibrium, automatic moment shift, or
generated prying.

## Response

`SingleBoltEvaluationResponseDTO` preserves selected identities, unit system,
versions, calculation fingerprint, material/fastener provenance, ordered layer and
mapping traces, source action or demand trace, ordered plans/results, availability,
independent numerical comparison, aggregate status, governing/co-governing IDs,
qualification flags, issues, warnings, concise structured source locators, and the
existing equation intermediates.

Engineering Decimals are serialized as strings. Physical quantities always include
units. The response profile is in./kip/ksi/kip-in (and in2) for `US_CUSTOMARY`, and
mm/kN/MPa/kN-mm (and mm2) for `SI`. Display conversion does not enter the
fingerprint, round intermediate values, or invoke another equation path.

Source locators contain only standard ID, edition, errata, section, and equation ID.
Licensed text and local PDF paths are absent. Responses contain no trusted identity,
environment values, filesystem paths, credentials, stack traces, internal reprs,
timestamps, or random values.

## HTTP and engineering status

HTTP status answers whether transport processing succeeded. Valid requests return
HTTP 200 for numerical PASS or FAIL and for engineering review, qualification,
unsupported, source-pending, incomplete, invalid-geometry, or unavailable-demand
outcomes. HTTP 422 is reserved for malformed schema or canonical mapping input.
Existing trusted-identity and unexpected-server-error behavior is unchanged.

## Verified current slice

HTTP integration exercises P1, PT1, P2A, P2B, J1-T, J1-C, B1, locked F593
source-pending, no-distribution, exact 90-degree transverse behavior, and required
U.S./SI equivalence. P1/P2A preserve required fingerprint equality. J1 preserves the
documented Q12 values, directions, statuses, and governing IDs without creating a new
independently reconstructed finite-geometry fingerprint requirement. J1 remains
Section 2.3.2 qualification-required; ICE remains engineering-review-required; F593
`Fnt` remains source-pending.

This is not a general connection-design API. Multirow equations, block shear,
automatic demand distribution, prying generation, frontend integration, persistence,
reports, authorization, entitlement, and production deployment remain future
controlled work.

## Stage 2.3 visualization response addition

Transport schema `0.3.0-draft` retains the required `visualization` member in a successful
response. This draft increment is transport-only: project schema, calculation
contract, engine, rule set, calculation fingerprint, results, aggregate status, and
governing behavior are unchanged. The route still invokes Stage 2.2A exactly once,
then projects the same canonical request geometry and returned identities into a
deterministic renderer-neutral snapshot. Decimal-string/unit serialization is reused.

The snapshot contains no camera, color, pixel, WebGL, user, ownership, expected-golden,
or result-authority field. It remains available for valid HTTP 200 engineering
non-success responses, including unsupported member-end distribution. The browser
client accepts only the exact draft transport and never treats HTTP success as an
engineering PASS.

## Stage 2.3R2 geometry-template request

Transport `0.3.0-draft` accepts exactly one of the historical explicit `geometry`
object or a strict `geometry_template`. The current template kind is
`BRACE_TO_COLUMN_FLANGE`; it carries a finite decimal-string brace-to-column angle in
`(0, 90]` degrees, positive column extents below/above the connection, positive brace
segment length, and the authoritative physical hole diameter with explicit units.
Extra fields, Boolean/numeric angle values, nonfinite values, unsupported member or
section identities, and neither/both geometry forms are rejected with HTTP 422.

Template mapping is server-owned and rebuilds the same canonical objects before the
unchanged single Stage 2.2A call. It preserves the connection station and binds the
explicit action/demand basis to the resolved server geometry. The version increment
changes transport representation and the renderer-neutral snapshot (now
`1.1.0-draft` for exact washer records) only. Project, calculation-contract, engine,
rule-set, fingerprints, result/status semantics, and the stateless trust boundary are
unchanged.

## Stage 2.3R3 orientation and invalid-geometry transport

API transport `0.4.0-draft` requires the current geometry template to state W-flange
connection side (`EXTERIOR` or `WEB_SIDE`), connected angle leg (`LEG_1` or
`LEG_2`), and outstanding-leg side (`POSITIVE_INTERFACE_Z` or
`NEGATIVE_INTERFACE_Z`). Strict DTO validation rejects missing, extra, numeric, or
unknown values. These fields are engineering geometry inputs and therefore make a
previous response stale when changed.

The server owns topology mapping, section clocking, and interference validation. A
mapped but physically interfering configuration remains an HTTP 200 engineering
outcome with aggregate `INVALID_GEOMETRY`, stable interference issue provenance,
and no calculation plans, results, governing check, or fingerprint. HTTP 422 remains
reserved for invalid transport or canonical-mapping input. Visualization snapshot
`1.2.0-draft` reports the resolved orientation and exact contact identities. No
Stage 2.1B equation, Stage 2.2A orchestration meaning, or Stage 2.2B status meaning
changes.

## Stage 2.3R5 canonical preview API

`POST /api/v1/calculations/single-bolt/preview` is a strict, stateless transport with
preview schema version `0.1.0-draft`. It uses the same server-injected trusted
identity boundary and the same canonical request mapping as the design endpoint. Its
request contains only geometry/action/material/bolt geometry and resolved-demand
inputs needed for preview; pure resistance factors, qualification inputs, client
identity, results, statuses, versions, and fingerprints are forbidden.

The deterministic response exposes trusted identity, preview version, model status,
design readiness, issues/warnings, resolved geometry/action/material mapping, and the
canonical visualization snapshot. It exposes no resistance plan, equation trace,
capacity, utilization, governing check, design PASS/FAIL, qualification outcome, or
calculation fingerprint. `VALID`, `INVALID_GEOMETRY`, `INCOMPLETE`, and
`UNSUPPORTED` are engineering preview outcomes returned with HTTP 200. DTO or
canonical-mapping failures remain HTTP 422. The existing design endpoint and its
Stage 2.2B response semantics are unchanged.

## Stage 2.3R6 transport separation

API transport `0.5.0-draft` replaces the former brace-angle and member-length
template meanings with explicit engineering
`brace_to_column_directed_angle_deg` and `bolt_to_brace_end_distance` fields. The
design DTO contains no view extent. Preview schema `0.2.0-draft` owns the distinct
`view_extents` object, required for the current template preview and forbidden for
the explicit-geometry path. `/api/v1` and trusted identity boundaries are unchanged.

Preview mapping removes `view_extents` before constructing the design/orchestration
request, maps them through a separate visualization-only adapter, and executes zero
resistance equations. Both preview and design return visualization snapshot
`1.3.0-draft`; preview may contain non-targetable `view_extension_primitives`, while
the design response leaves that collection empty. Decimal strings and explicit
units remain mandatory for every physical quantity.
