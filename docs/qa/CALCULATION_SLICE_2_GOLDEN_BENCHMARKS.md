# Calculation Slice 2 Golden Benchmarks

## Controlled identities

- Engineering specification: `CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1`
- Specification SHA-256:
  `44431A8921CF1ADF9C7D0F7F022C9615265308A41BE589B1EE5150A7D7886F99`
- Golden benchmark: `CALCULATION_SLICE_2_GOLDEN_BENCHMARKS_RC1`
- Golden SHA-256:
  `C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610`
- Repository fixture: `backend/tests/golden/calculation_slice_2_rc1.json`
- Prior Slice 1 RC2 fixture SHA-256 (unchanged):
  `39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392`

The attached Slice 2 JSON is stored byte-for-byte unchanged. It is a controlled
test oracle, never a production lookup table or calculation input.

## Benchmark coverage

The fixture records deterministic cases for physical row/line resolution, two- and
three-row prescribed distributions, conservative five- and six-row full-row
scenarios, engineer-defined demand, lap context, first-row planning, inter-row
planning, L- and U-shaped block paths, half-hole corner accounting, raw Section 2.10
net-area status, the transverse-plate source conflict, and applicability/qualification
boundaries. Expected identifiers and exact values are asserted by the test suite;
the implementation is changed when it disagrees with the approved oracle, not the
other way around.

## Integrity and regression controls

Tests verify the exact file hash, schema/approval marker, case identifiers, source
and specification identities, rational fractions, raw geometry/area evidence,
statuses, warnings, deterministic fingerprints, and U.S./SI representations. They
also verify the unchanged Slice 1 RC2 hash and numerical regression, the unchanged
Stage 2.2A/2.2B behavior, absence of new equation execution, absence of fixture access
from production code, and the frozen Stage 2.3 frontend/API boundaries.

Local acceptance requires the complete backend, frontend, and integrated gates,
strict JSON validation, whitespace validation, dependency/lock checks, and both npm
audit scopes. Hosted Ubuntu/Windows evidence is recorded only after it exists; local
success is not reported as hosted success.

The 2026-08-12 local Stage 2.4A run passed 1,240 backend tests with 100 percent
statement and branch coverage and retained the unchanged 123-test frontend suite at
configured 100 percent coverage. Integrated QA and both zero-vulnerability npm audits
also passed. The feature commit's hosted run later failed only the cross-platform
raw-checkout-byte freeze audit in both backend jobs; both frontend jobs passed.

Stage 2.4A-R1 directly parameterizes the production prescribed-distribution selector
from this unchanged fixture's `FRP_FRP_2`, `FRP_STEEL_2`, `FRP_FRP_3`, and
`FRP_STEEL_3` values and requires every exact Decimal sequence to sum to one. The
audit confirmed production was already correct; the erroneous generic three-row
description existed only in the completion report and two derivative documents.
Full R1 local validation passed 1,254 backend and 123 frontend tests at configured
100 percent coverage, all integrated/lint/type/build gates, and both zero-vulnerability
npm audits. Correction hosted CI remains pending.
