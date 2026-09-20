# FRP Master Connection — Stage 4.2 — Native Governing Failure Selection Clarification R7

## Status

**Controlled pre-implementation clarification R7.**

No Stage 4.2 repository mutation has occurred.

R7 resolves the final G103 conflict identified by the completed R6 read-only audit.

No physical mechanics, material property, factor, dependency behavior, or status precedence is changed.

## 1. Overall G103 status remains FAIL

The production-default physical fixture still governs as:

`FAIL`.

Reason:

`EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE`.

Missing qualified connector/member-attachment sources remain visible in the result trace but are subordinate to evaluated failure.

## 2. Native governing-check selection controls

R6 incorrectly required the top-angle bearing failure itself to remain the governing internal failure.

That requirement is superseded.

The accepted native:

`Stage 2.5A -> resistance handoff -> group-mode selection`

pipeline owns the governing-failure selection.

For the audited production-default fixture, the native governing group is:

`FIRST_ROW:TOP_FLANGE_ANGLE`.

Stage 4.2 shall preserve that native selection exactly.

Do not override the native governing selection merely because a particular failed limit state was discussed in a prior clarification.

## 3. Required failed checks remain visible

The completed read-only audit identified at least the following native failures in the top-flange-angle first-row path:

- first-row net tension;
- pin bearing;
- inter-row shear-out.

Displayed audit utilizations were approximately:

- net tension: `6.338667`;
- pin bearing: `3.169334`;
- inter-row shear-out: `2.498227`.

These values are noncontrolling audit evidence only.

The controlling values/statuses are the exact native outputs of the unchanged calculation/resistance pipeline.

All required failed checks shall remain visible in the result trace.

Pin bearing shall remain visible as a required failed check.

Pin bearing is **not required to be the governing selected failure**.

## 4. No forced limit-state override

Prohibited:

- forcing bearing to govern;
- suppressing net-tension or shear-out failure;
- reordering native group-mode selection solely to satisfy a golden;
- changing material properties or resistance factors;
- changing Stage 2.5A or resistance-handoff behavior;
- changing status precedence.

The golden shall follow the accepted native governing-selection output.

## 5. Fingerprints

The Stage 4.2 result/fingerprint shall bind:

- production-default material fingerprint;
- flange/web factor fingerprints;
- exact native failed-check records;
- exact native governing group/selection;
- missing-source trace;
- governing overall status.

Presentation-only approximate utilization strings are excluded from controlling fingerprints.

## 6. Supersession

The Stage 4.2 RC1-R6 golden is superseded before implementation.

The controlling golden is:

`FRP_MASTER_CONNECTION_STAGE_4_2_WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_GOLDEN_BENCHMARKS_RC1_R7.json`.

It contains exactly G1-G128.

R3/R4/R5/R6 and the original Stage 4.2 authority remain controlling in all other respects.

## 7. No other blocker

The R6 consolidated read-only audit reported no other blocker after this native-governing-selection conflict.

R7 authorizes implementation to resume once the replacement golden and clarification are verified.

**END OF STAGE 4.2 NATIVE GOVERNING FAILURE SELECTION CLARIFICATION R7**
