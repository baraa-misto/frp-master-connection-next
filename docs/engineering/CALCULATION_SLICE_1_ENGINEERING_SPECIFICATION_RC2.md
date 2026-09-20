# First Calculation Slice Engineering Specification - RC2

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 2.1A |
| Status | Approved engineering meaning; contract/applicability implementation only |
| Approval authority | Baraa Misto |
| Standard | ASCE/SEI 74-23, Chapter 8 |
| Errata | Erratum 1, effective 2026-01-13; Chapter 8 unaffected |
| Numerical implementation | Not authorized until Stage 2.1B |

## Purpose and controlling boundary

This repository record summarizes the approved RC2 meaning for the first calculation
slice. The controlling Stage 2.1A order governs implementation scope; the approved RC2
source specification and golden JSON govern engineering meaning and fixtures; the
licensed standard and erratum were read-only concordance sources. Neither PDF is
reproduced or tracked.

Stage 2.1A implements immutable quantities, sources, material and fastener snapshots,
resolved demand, geometry-to-code mapping, code-geometry prerequisites, applicability,
readiness, future result vocabularies, canonical input fingerprints, and controlled
golden fixture ingestion. It implements no resistance, capacity, utilization, or
calculated physical-input `PASS`/`FAIL`.

## Authorized physical family

The first family is one physical bolt in one row through one or more explicit flat
rectangular pultruded-FRP layers. It uses a round standard hole, an authoritative C3
bolt center/axis/path/layer stack, explicit resolved per-bolt demand, and explicit
single- or double-lap metadata. Member-end actions are not distributed automatically.
The one-leg angle-to-W configuration remains subject to Section 2.3.2 qualification at
whole-connection level.

Excluded conditions include multirow strength behavior, more than one bolt for this
implementation slice, slots, unequal physical hole diameters in one logical connection,
curved or annular checked layers, arbitrary polygons, multi-hole net paths, inferred
prying, automatic eccentricity or action shifting, automatic perpendicular-return
credit, automatic equilibrium, and whole-joint qualification.

## Direction, demand, and geometry

The signed force acting on a checked layer defines the forward loaded-end ray and
`e1`; force reversal swaps forward and reverse distances. The material angle is acute
and sign-independent. Angles through 5 degrees inclusive select longitudinal
properties; angles greater than 5 through 90 degrees inclusive select transverse
properties. Exactly 90 degrees is transverse under interpretation
`TRANSVERSE_ENDPOINT_INCLUDED`.

The effective-width resolver retains both raw physical side distances. It implements
only the equal-side case, the one-near/one-beyond-cap case, and the both-beyond-cap
case. Unequal sides both within the cap remain raw and return
`CALCULATION_NOT_SUPPORTED`; there is no generalized `min()` rule. Bounds come from
the physical material rectangle, not a connection zone, viewport, component envelope,
or full section.

## Units and published code constants

One physical calculation path supports U.S. customary and SI profiles. Canonical
fingerprint units are millimetres, newtons, newton-millimetres, megapascals, and one.
Public calculation numbers are finite `Decimal` values; ordinary constructors reject
floats and Booleans. Conversions do not apply display rounding.

The ordinary-hole generator retains its printed source column. A U.S.-source hole adds
exactly 0.063 in.; an SI-source hole adds exactly 1.6 mm. The generated physical hole
diameter is authoritative. Display conversion never regenerates it, so the U.S. and SI
examples are physically distinct even though both printed increments describe the
standard's dual-unit presentation.

## Development material and default fastener

`ICE_LOCKED_PULTRUDED_FRP` is a locked engineer-approved development snapshot. It is
not independently verified as an ASTM D7290 characteristic set. `FC_T` is explicitly
absent. The three discrete pull-through values remain development data and are not
substituted for the Chapter 8 pull-through equation plan. ICE property use carries
`ENGINEERING_REVIEW_REQUIRED`; the development bearing-factor policy does not permit
an ordinary qualified pass.

`ASTM_F593_17_GROUP_2_316_316L` is the locked default F593-17 Group 2, 316/316L
cold-worked fastener-system snapshot with F594-15 nut, compatible stainless washers,
snug-tight installation, and ordinary diameter range 0.375 through 1.0 in. `Fnt` is
absent and `SOURCE_PENDING`; no generic tensile value is substituted. Synthetic
explicit-`Fnt` fixtures remain separate and never claim F593 qualification.

Thread inclusion/exclusion is recorded separately for every bolt shear plane and every
FRP bearing layer.

## Factors, applicability, and statuses

Time-effect, end-use, lap, and one-row geometry-factor selections remain separately
traceable metadata. No factor is assembled into a resistance in Stage 2.1A. End-use
factors require explicit source/approval metadata; golden fixtures explicitly select
unity. The single-lap 0.60 value is metadata only for applicable in-plane FRP checks
and excludes metallic bolt and pull-through plans.

Every physical check plan uses `NOT_EVALUATED`. `READY` means only that inputs are
ready for a future Stage 2.1B numerical implementation. Source gaps, missing input,
unsupported mapping, invalid geometry, engineering review, bolt-demand distribution,
and Section 2.3.2 qualification remain distinct fail-closed states. A supplied golden
fixture failure may exercise aggregate precedence without calculating it; P2B retains
`FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK` when a supplied fail coexists with unsupported
cleavage.

## Reproducibility and fixtures

Fingerprints use SHA-256 over compact sorted UTF-8 JSON. Physical quantities serialize
as canonical decimal strings in canonical units. Ordered physical sequences retain
order; explicitly unordered collections sort by stable ID. Source/version,
interpretation, material and fastener qualification, physical geometry, mapping,
demand, factors, lap, threads, published constant basis, and readiness are included.
Display, camera, color, visibility, report profile, ownership, entitlement, billing,
and nonengineering timestamps are excluded.

The controlled JSON contains P1, PT1, P2A, P2B, J1_T, J1_C, B1_SYNTHETIC,
DIRECTION_90, HOLE_US_SOURCE, and HOLE_SI_SOURCE. Numerical resistance and utilization
values in that file are inert expected data. Production code does not load or evaluate
the fixture.

## Release statement

Stage 2.1A establishes calculation contracts and applicability only. The product is
not usable for an engineering design decision. Stage 2.1B is required before any
authorized numerical resistance implementation or benchmark reproduction.
