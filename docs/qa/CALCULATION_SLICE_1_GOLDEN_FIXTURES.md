# Calculation Slice 1 Golden Fixtures

## Controlled artifact

`backend/tests/golden/calculation_slice_1_rc2.json` is the approved RC2 fixture. Its
document status is `ENGINEERING_SPECIFICATION_RC2_APPROVED_FOR_STAGE_2_1A`. Tests load
it with duplicate-key detection, validate source/unit/material/fastener identities,
require the complete benchmark set, parse every decimal-form string, and recursively
freeze the loaded structure. Production code has no dependency on this file.

## Benchmark purposes

| ID | Stage 2.1A purpose |
|---|---|
| P1 | One-layer U.S.-source hole, double-lap, longitudinal tension readiness. |
| PT1 | Positive explicit bolt-axis demand activates pull-through planning. |
| P2A | Two ordered layers, common physical hole, single-lap metadata, independent plans. |
| P2B | 45-degree transverse property selection, unsupported cleavage, supplied-fail precedence. |
| J1_T | Resolved angle-to-W tension mapping and whole-connection Section 2.3.2 qualification. |
| J1_C | Compression applicability with net tension and cleavage not applicable. |
| B1_SYNTHETIC | Explicit non-F593 fixture `Fnt` makes future bolt plans ready. |
| DIRECTION_90 | Exactly-90 transverse endpoint and interpretation trace. |
| HOLE_US_SOURCE | 0.500 + 0.063 = 0.563 in., stored physical hole. |
| HOLE_SI_SOURCE | 12.7 + 1.6 = 14.3 mm, stored physical hole. |

Expected resistances and utilizations remain test-only data. Stage 2.1B production
calculates independently from physical inputs, while tests use the values as immutable
12-decimal oracles. P2B now produces its known physical-input failures and retains the
simultaneous unsupported cleavage check.

## Validation boundary

Fixture schema, applicability, canonical unit/source behavior, fingerprints, aggregate
precedence, every recorded numerical value, and exact converted U.S./SI equivalence are
tested. This validates only the approved RC2 single-bolt numerical slice. It does not
qualify ICE, the locked F593 preset, J1 as a whole, or a general calculation family.

## Stage 2.2A orchestration verification

The unchanged RC2 JSON is also the oracle for full application-path P1, PT1, P2A,
P2B, J1-T, J1-C, and synthetic B1 tests. Fixtures construct canonical assembly,
placement, surface, interface, bolt-path, material, fastener, load, and demand objects;
production code never imports expected values. Direct Stage 2.1B regressions run
beside orchestration assertions, including the 90-degree transverse endpoint and
physical US/SI equivalence. P2B retains failure plus unsupported cleavage, and J1
retains its Section 2.3.2 qualification boundary.
