# Calculation Status and Fingerprint Specification

## Separate state dimensions

Planning readiness is separate from future result availability and numerical
comparison. Stage 2.1A readiness values include `READY`, `NOT_APPLICABLE`,
`INCOMPLETE_INPUT`, `SOURCE_DATA_PENDING`,
`SECTION_2_3_2_QUALIFICATION_REQUIRED`, `ENGINEERING_REVIEW_REQUIRED`,
`CALCULATION_NOT_SUPPORTED`, `INVALID_GEOMETRY`, and
`BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED`.

Future result availability is `CALCULATED`, `NOT_APPLICABLE`, `INCOMPLETE_INPUT`,
`SOURCE_DATA_PENDING`, `SECTION_2_3_2_QUALIFICATION_REQUIRED`,
`ENGINEERING_REVIEW_REQUIRED`, `CALCULATION_NOT_SUPPORTED`, `INVALID_GEOMETRY`, or
`STALE_RESULT`.

Numerical comparison is exactly `PASS`, `FAIL`, or `NOT_EVALUATED`. Every Stage 2.1A
physical check plan is `NOT_EVALUATED`; only supplied fixture/result objects may carry
known `PASS`/`FAIL` values for schema and precedence testing.

## Planned check

Each immutable plan retains check/limit-state/component/layer/bolt IDs, source
section/equation locator, readiness, `NOT_EVALUATED`, reason codes, required property,
selected direction/theta, required geometry, factor metadata, qualification flags,
warnings, assumptions, unsupported conditions, and input fingerprint. It has no
resistance, capacity, utilization, or calculated acceptance field.

## Canonical fingerprint

The digest is lowercase SHA-256 over compact, key-sorted, UTF-8 JSON. Engineering
numeric values are canonical decimal strings in canonical units; raw JSON floats are
rejected. Case-sensitive IDs are retained. Ordered engineering sequences preserve
order. Explicitly unordered collections sort by stable ID.

Included fields cover governing source/edition/errata/interpretation, schema and
calculation-contract versions, future engine-version field, material and fastener
source/qualification, exact physical geometry, code mapping, resolved demand, factors,
lap, threads, published unit basis, and readiness decisions.

Excluded fields cover display units/rounding/formatted strings, camera/color/
visibility/selected tab, report profile, ownership/organization/entitlement/billing,
and nonengineering timestamps. Human display names in locked snapshots do not affect
the digest. A physical value, source basis, source state, qualification, property, or
demand change does.

Historical calculated snapshots will become stale when a calculation-relevant input
or version changes. Stage 2.1A implements deterministic input identity; Stage 2.1B
retains that fingerprint in an immutable in-memory final result but creates no
persisted snapshot.

## Stage 2.1B final-result behavior

Only ready plans become `CALCULATED` and receive exact demand, nominal/design
resistance, utilization, PASS/FAIL, equation trace, and source trace. Every other plan
maps to its corresponding final availability and remains `NOT_EVALUATED` with no
numerical fields. The demand-distribution-unsupported state is preserved explicitly in
final availability.

Exact demand/resistance equality passes. A nonpositive design resistance fails without
clamping and has no utilization. Known required failure controls aggregation, with a
distinct failure-plus-unsupported outcome. Governing ties use `1E-12` only for
governing identity, not PASS/FAIL. Exact physical unit conversion changes neither the
fingerprint nor any result/status identity.

## Stage 2.2A status and fingerprint reuse

Orchestration returns the Stage 2.1B aggregate and governing/co-governing IDs without
reinterpretation, and exposes deterministic application issues alongside them. Known
failure plus unsupported required work, source-pending fastener behavior, engineering
review, and Section 2.3.2 qualification therefore remain visible. The service calls
the existing canonical fingerprint function and defines no second hash authority.
Canonical explicit demands are normalized to the existing physical quantity basis;
display state, ordering of semantically unordered assignments, and runtime state do
not enter the fingerprint.

## Stage 2.2B HTTP and engineering-status separation

HTTP status describes transport validity, not engineering acceptance. A schema-valid,
canonically mappable request returns HTTP 200 even when its authoritative engineering
outcome is fail, unsupported, source-pending, review-required, qualification-required,
or demand-distribution-unsupported. Malformed DTOs and requests that cannot be mapped
to canonical contracts return HTTP 422 and do not call orchestration.

The API response exposes the existing calculation fingerprint only. It accepts no
client-supplied fingerprint, version identity, owner identity, calculated result, or
engineering status, and it defines no API-specific hash. Deterministic serialization
changes representation only; it does not reinterpret aggregation, governing ties,
comparison, readiness, or result availability.
