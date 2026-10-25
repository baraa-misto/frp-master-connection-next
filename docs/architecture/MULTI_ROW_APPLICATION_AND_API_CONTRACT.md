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

## Direct OR2 F3 physical engineering geometry extension

The Direct Angle-to-W adapter adds server-authored `direct_engineering_geometry`
to Direct previews and their authenticated design snapshots. Each bolt and
penetrated element records physical ends, free side edges, internal junctions,
represented obstructions, exact coordinates, physical-source identities,
eligibility, separate evaluated checks and explicit model limitations. The
ordinary Chapter 8 e2 minimum remains 1.5d. Hole and washer radii are separate
physical checks. Selected contact patches retain interface/penetration identity;
their subdivision boundaries supply no engineering limit without a physical
mapping. Raw patch witnesses remain under `direct_clearance_provenance` and are
explicitly computational diagnostics.

The owner-authorized Direct reconciliation rebuilds the Angle's physical length
from its existing native bolt-layout boundary rule while retaining the exact
frame and bolt anchors. The owner 135-degree 2 × 1 case has submitted, native,
physical and Chapter 8 loaded-end distance 3 in / 76.2 mm. Presentation extents
remain separate. The additional application metadata uses a Direct-only preview
subclass; other families keep their original serialization and fingerprints.
Clients cannot submit physical-check results. The report renderer reads the
signed snapshot and supplies no geometry or resistance authority.

See `docs/qa/SHEAR01_DIRECT_OR2_F3.md` for the bounded cases and QA gates. This
successor activates no engineering source, qualification or missing method.

## Direct OR2 F3 R1 supporting-W longitudinal ends

Direct requests add `supporting_w_longitudinal_ends`, with `condition` equal to
`UNSPECIFIED`, `CONTINUOUS_THROUGH_CONNECTION`, `FINITE_BOTH_ENDS`,
`FINITE_NEGATIVE_END_ONLY`, or `FINITE_POSITIVE_END_ONLY`. Only selected finite
ends accept `negative_end_distance` / `positive_end_distance` quantities in in/mm;
they must be positive. Omission on the Direct route means UNSPECIFIED and blocks
design readiness with INPUT NEEDED. Other families reject this declaration.

The backend emits `direct_support_end_authority`: stable projected interface
reference, real end coordinates/null, raw/canonical per-bolt station witnesses,
force-selected existing end, separately labeled presentation crop coordinates,
and source applicability. Clients cannot submit resolved authority or results.
The owner examples explicitly declare continuous support. Legacy extrusion
lengths survive only as display context or explicitly declared historical test
geometry. W end-dependent paths lacking an independent method remain unevaluated;
pin bearing and unaffected Angle mechanics retain exact authority.

Direct preview identity excludes presentation view extents/extension primitives,
while end condition and real-end distances remain design-affecting. UI/report
rendering reads signed authority to place visible real end caps; rendering creates
no engineering result or check. Other family fingerprints/serialization remain
unchanged. See `docs/qa/SHEAR01_DIRECT_OR2_F3_R1.md`.
# Direct ASTM F593 catalog selector — F4 RC1

Direct MAT1 design requests may select `CATALOG / FASTENER-F4-RC1` with controlled revision, alloy group, alloy, condition and shear-thread status. Nominal diameter comes from the physical request; the backend resolves the table row and lower Fnt before calling the existing engine. The authenticated `/api/v1/fasteners/resolve` route exposes the same current source resolution for UI presentation. Client strength/result fields are forbidden. Historical DEFAULT/FASTENER-OR1-RC1 and SESSION contracts remain available; non-Direct catalog binding is deferred. See [F4 source and verification record](../qa/SHEAR01_DIRECT_OR2_F4.md).
# Direct F9 final-status successor

The current API inventory has 64 paths / 64 operations. MAT1 Direct design results
now include one backend-authoritative final decision, retaining every native and F8
engineering result. See [Direct F9 final status](DIRECT_F9_FINAL_STATUS.md).
## Direct MC1 material-input extension

New Direct MAT1 requests may declare the explicit SHEAR01-DIRECT-MC1 policy, one
design_temperature and an optional chemical_strength_factor. The backend validates
physical equality to both existing sustained/maximum temperature fields. Custom
chemical factors must be exact finite decimal strings in (0, 1]; they apply only
to applicable FRP strength. Modulus retains independently supported CM/CT candidate
values with chemical applicability UNEVALUATED, never an assumed chemical factor.
Unmarked historical requests retain their original schema and calculations.
See [the MC1 specification](DIRECT_MC1_MATERIAL_CONDITIONS.md). Route inventory,
authentication, geometry, demand, F9 precedence and F8 qualification authority
are unchanged. No other family accepts this calculation-policy marker.
