# FRP Master Connection — Stage 4.2 — Web Group Reference Correction and Resume Order R4

**RECOMMENDED CODEX EFFORT:** HIGH

## Purpose

Resolve the R3 pre-mutation web-group reference conflict and resume the unchanged Stage 4.2 implementation.

No repository mutation has occurred.

## 1. Baseline

Require exactly:

`HEAD == origin/main == remote main == 473a3c8cd43f13022d254dae2477084895478c74`

Commit count:

`106`.

Worktree/index:

`clean`.

If different: STOP.

## 2. New controlling files

### R4 Clarification

SHA-256:

`9788C1D92252E3F03C5D71ADA4F02A20713D3BD62D4F3326A16B2D3D53B35380`

Required sentinel:

`END OF STAGE 4.2 WEB GROUP REFERENCE CLARIFICATION R4`

### Replacement Golden RC1-R4

SHA-256:

`111D6DEDD14664D552AB0319BEE7089CDFD464F9C2A53F50C07E27D4EBF3B0D0`

Must parse exactly:

`G1-G128`.

The SHA-256 for this R4 order is supplied in the owner handoff message.

Any mismatch: STOP.

## 3. Supersession

The Stage 4.2 RC1-R3 golden is superseded before implementation.

Continue to use the R3 clarification and R3 implementation order except where R4 explicitly corrects:

- G66/G68 web wrench reference;
- G66-G70 stale case labels;
- G67/G69 relational input-case names;
- G71 plane-vector source case names;
- web reference/fingerprint provenance.

All physical topology and engineering methods remain unchanged.

## 4. Controlling physical coordinate system

Use heel-local angle coordinates.

G60 remains:

- `(-1.5,1.25)`;
- `(+1.5,1.25)`;
- `(-1.5,2.75)`;
- `(+1.5,2.75) in`.

Prove exact centroid:

`(0,2.0) in`.

The physical web member-interface wrench reference is:

`(0,2.0) in`.

Do not use `(0,0)` with G60 coordinates.

Do not recenter G60 physical coordinates to `B=±0.75` in Stage 4.2 production records.

## 5. Positive web Slice 8 call

Use G60 coordinates.

Use reference:

`(0,2.0) in`.

Use:

`F_A=+5 kip`

`F_B=+3.6 kip`

`M_C,R=+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

Require:

`M_C,c=M_C,R`

exactly.

Require Stage 4.2 result equal a direct accepted Slice 8 call with this exact physical coordinate/reference set.

## 6. Negative web Slice 8 call

Use G60 coordinates.

Use reference:

`(0,2.0) in`.

Use:

`F_A=-5 kip`

`F_B=+3.6 kip`

`M_C,R=-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

Require:

`M_C,c=M_C,R`

exactly.

Require exact direct Slice 8 integration equality.

## 7. Translation-equivalence regression

As a test only, compare the physical heel-local call against a translated centroid-relative call:

Physical:
- G60 coordinates;
- reference `(0,2)`.

Translated:
- coordinates `A=±1.5`, `B=±0.75`;
- reference `(0,0)`.

Require:

- identical `J`;
- identical transported centroid moment;
- identical per-bolt exact rational vectors by corresponding physical bolt identity;
- identical Decimal projections/magnitudes.

Do **not** require identical reference-bound fingerprints.

The production Stage 4.2 fingerprint must bind the physical heel-local representation.

## 8. Case IDs

Require exact R4 IDs:

- `G66_POSITIVE_WEB_SLICE8_INPUT`;
- `G67_POSITIVE_WEB_SLICE8_OUTPUT`;
- `G68_NEGATIVE_WEB_SLICE8_INPUT`;
- `G69_NEGATIVE_WEB_SLICE8_OUTPUT`;
- `G70_SLICE8_EXACT_RECOVERY`.

G67 input reference must point to G66.

G69 input reference must point to G68.

G71 vector sources must point to G67 and G69 respectively.

## 9. Unchanged R3 requirements

Continue all R3 requirements, including:

- Stage 2.5A only for top/bottom accepted-scope groups;
- Slice 8 for positive/negative web in-plane full wrench;
- Slice 7 native connector boundary;
- qualified out-of-plane member attachment;
- common web-bolt unequal two-plane method;
- finite concrete wall;
- four FRP angles;
- four external wall-anchor groups;
- no per-anchor fabrication;
- anchor/concrete capacity external;
- corrected `+3E-79 / +6E-79 / -6E-79` diagnostics;
- no 316SS;
- no later moment family;
- no dependency/workflow/tag changes.

## 10. QA additions

Before commit require explicit tests proving:

1. G60 centroid is exactly `(0,2)`;
2. G66/G68 reference is exactly `(0,2)`;
3. no unintended `±10 kip-in` transport occurs;
4. positive `M_C,c` equals positive `M_C,R`;
5. negative `M_C,c` equals negative `M_C,R`;
6. physical and centroid-relative representations produce identical physical bolt vectors;
7. their reference-bound fingerprints are allowed/expected to differ;
8. Stage 4.2 production fingerprint uses physical heel-local reference;
9. G66-G71 relational references are internally consistent;
10. replacement G1-G128 passes.

Then continue all R3 full QA, built-in-browser/CDP local visual QA, object-isolated verification, normal push, direct hosted 4/4 CI, and owner final acceptance requirements.

## 11. Commit

Expected implementation commit remains exactly:

`feat: add W/I beam-to-concrete-wall moment connection`

Expected final commit count remains:

`107`.

Do not amend.

Do not tag.

## 12. Completion report addition

Explicitly report:

- G60 centroid;
- physical G66/G68 wrench reference;
- absence of unintended reference-generated moment;
- translation-equivalence test;
- fingerprint distinction;
- R4 golden hash/G1-G128 result.

**END OF STAGE 4.2 WEB GROUP REFERENCE CORRECTION AND RESUME ORDER R4 — DO NOT PROCEED IF THIS LINE IS MISSING**
