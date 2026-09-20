# FRP Master Connection — Calculation Slice 8 — Negative-Web Precision and Stage 2.5A Compatibility Clarification R1

## Status

**Controlled pre-implementation clarification R1.**

This clarification resolves two controlled-package defects found by Codex before any repository mutation.

No accepted engine is changed.

## 1. Negative-web input correction

The original Slice 8 RC1 golden accidentally constructed the negative Stage 4.2 web moment through a Decimal operation that applied the ambient Decimal context and shortened the value.

That was a package-generation defect.

The controlling negative-web moment is the exact mathematical negative of the positive-web input:

Positive:

`+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`

Negative:

`-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`

No digit may be dropped.

G39-G46 in the replacement RC1-R1 golden are recomputed from that exact full negative value.

G47 requires exact reversal of `F_A` and `M_C` with `F_B` retained.

## 2. Stage 2.5A overlap compatibility correction

The original G62 incorrectly required exact per-bolt Decimal identity between:

- immutable Stage 2.5A native Decimal projections; and
- Slice 8 exact-rational mechanics projected to Decimal-80.

Codex proved that the two engines use numerically different intermediate projection paths even though the governing equal-stiffness mechanics agree.

For the G55-G61 eccentric-force fixture:

- physical group is identical;
- reference is identical;
- force is identical;
- transported centroid moment is exactly `-16 kip-in`;
- direct equal-share force model is the same;
- equal-stiffness elastic correction equations are the same;
- force-recovery target is `(8,0) kip`;
- centroid-moment-recovery target is `-16 kip-in`.

Slice 8 exact rational A-components are:

- lower row: `14/15 kip`;
- upper row: `46/15 kip`.

Slice 8 Decimal-80 projections therefore end with repeating-3 / repeating-6 rounding under its own controlled projection contract.

Stage 2.5A native projected values differ in the final places because its accepted intermediate Decimal path is different.

## 3. Governing cross-engine rule

G62 is now a **mechanics compatibility** test, not a cross-engine numeric-serialization identity test.

Required:

1. same physical bolt group;
2. same wrench reference;
3. same direct equal-share model;
4. same generated centroid moment;
5. same equal-stiffness elastic correction mechanics;
6. same force-recovery target;
7. same centroid-moment-recovery target;
8. both native-engine proofs/statuses pass within their own accepted authority.

Not required:

- exact equality of the two engines' projected per-bolt Decimal strings.

No tolerance is introduced.

No engine output is rounded to match the other engine.

No Stage 2.5A rounding path is emulated inside Slice 8.

## 4. Slice 8 authority remains exact rational

Slice 8 mechanics remain governed by exact rational arithmetic.

Its Decimal-80 projection remains only its deterministic downstream interoperability representation.

The replacement golden does not weaken Slice 8's internal exact force/moment proof.

## 5. Stage 2.5A remains immutable

No modification to Stage 2.5A is authorized.

Its:

- native Decimal projections;
- warning behavior;
- pure-moment unsupported behavior;
- historical tests;
- fingerprints

remain exact.

## 6. Replacement golden

The controlling golden is:

`FRP_MASTER_CONNECTION_CALCULATION_SLICE_8_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_GOLDEN_BENCHMARKS_RC1_R1.json`.

It contains exactly G1-G80.

It supersedes the original Slice 8 RC1 golden before implementation.

All other Slice 8 Decision/Specification/Ledger provisions remain controlling except where this clarification explicitly corrects G39-G47 and G62 cross-engine comparison semantics.

**END OF CALCULATION SLICE 8 NEGATIVE-WEB AND STAGE 2.5A COMPATIBILITY CLARIFICATION R1**
