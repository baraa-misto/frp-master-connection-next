# FRP Master Connection — Stage 4.2 — Flange Stage 2.5A Numeric Authority Correction and Resume Order R5

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Resolve the R4 pre-mutation G64/G65 flange numerical-authority mismatch and resume the unchanged Stage 4.2 implementation.

No Stage 4.2 repository mutation has occurred.

## 1. Baseline

Require exactly:

`HEAD == origin/main == remote main == 473a3c8cd43f13022d254dae2477084895478c74`

Commit count:

`106`.

Worktree/index:

`clean`.

If different: STOP.

## 2. New controlling R5 files

### R5 Clarification

SHA-256:

`A2028399567F31227C5C872FC2C90180194B58056F0D563180CF3EBDADB8D9EC`

Required sentinel:

`END OF STAGE 4.2 FLANGE STAGE 2.5A NATIVE NUMERIC AUTHORITY CLARIFICATION R5`

### Replacement Golden RC1-R5

SHA-256:

`FE5A6EFD1CD2E4295B82828F249E0BD6B548381F5DDBD121D19C4FD2C1C12D42`

Must parse exactly:

`G1-G128`.

The SHA-256 for this R5 order is supplied in the owner handoff message.

Any mismatch: STOP.

## 3. Supersession

The Stage 4.2 RC1-R4 golden is superseded before implementation.

Continue using R3/R4 authority and the original Stage 4.2 package except where R5 explicitly corrects G64/G65 flange numerical authority and related fingerprint metadata.

## 4. G64 top flange

Use the unchanged accepted Stage 2.5A engine.

Stage 4.2 top-flange demand output must equal the direct native Stage 2.5A output for the exact same physical input/group.

Do not independently compute `N_top/4` as the controlling numeric expectation.

Do not round/quantize/project the Stage 2.5A result to another precision for equality.

No tolerance.

The observed native signed B-component may be retained as audit evidence, but direct dependency invocation is the oracle.

## 5. G65 bottom flange

Same rule.

Stage 4.2 bottom-flange demand output must equal the direct native Stage 2.5A output for the same physical input/group exactly.

Do not independently compute `N_bottom/4` as the controlling numeric expectation.

No tolerance or cross-precision normalization.

## 6. Supported-scope proof

Before mutation confirm:

- top/bottom Stage 4.2 flange groups are within Stage 2.5A accepted applicability;
- no independently applied free in-plane member-end moment is passed to Stage 2.5A in these paths;
- the unsupported-moment warning is absent from valid top/bottom paths.

If not: STOP.

## 7. Direct dependency tests

Require explicit tests:

1. Stage 4.2 G64 output equals a direct unchanged Stage 2.5A call by exact object/Decimal equality.
2. Stage 4.2 G65 output equals a direct unchanged Stage 2.5A call by exact object/Decimal equality.
3. Stage 4.2 does not calculate substitute `N/4` values for those result records.
4. No rounding/quantization adapter exists around Stage 2.5A.
5. No tolerance is used.
6. Stage 2.5A files, behavior, tests, and fingerprints remain unchanged.
7. Algebraic equal-share behavior remains consistent as a separate mechanics proof/diagnostic.
8. R5 G1-G128 passes.

## 8. Continue R4/R3 implementation

After R5 verification, continue all unchanged requirements, including:

- R4 physical web reference `(0,2)`;
- Slice 8 web member demand;
- Slice 7 native connector boundary;
- common web-bolt unequal plane vectors;
- qualified out-of-plane member attachment;
- finite wall / W-I beam / four FRP angles;
- four external anchor groups;
- external concrete/anchor capacity;
- `+3E-79 / +6E-79 / -6E-79` diagnostics;
- full QA;
- automatic built-in-browser/CDP local visual QA;
- object-isolated verification;
- normal non-force push;
- direct hosted 4/4 CI;
- owner final visual acceptance.

## 9. No scope additions

No:

- 316SS implementation;
- later moment family;
- dependency change;
- lockfile change;
- workflow change;
- tag change.

## 10. Commit

Expected Stage 4.2 implementation commit remains:

`feat: add W/I beam-to-concrete-wall moment connection`

Expected final commit count remains:

`107`.

Do not amend.

Do not tag.

## 11. Completion report addition

Explicitly report:

- direct G64 Stage 2.5A native result equality;
- direct G65 Stage 2.5A native result equality;
- absence of substitute `N/4` result construction;
- absence of rounding/tolerance adapter;
- unchanged Stage 2.5A fingerprint;
- R5 replacement golden hash and G1-G128 result.

**END OF STAGE 4.2 FLANGE STAGE 2.5A NUMERIC AUTHORITY CORRECTION AND RESUME ORDER R5 — DO NOT PROCEED IF THIS LINE IS MISSING**
