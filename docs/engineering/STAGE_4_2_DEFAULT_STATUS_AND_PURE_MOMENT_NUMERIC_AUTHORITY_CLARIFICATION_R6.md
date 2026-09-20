# FRP Master Connection — Stage 4.2 — Default Status and Pure-Moment Numeric Authority Clarification R6

## Status

**Controlled pre-implementation clarification R6.**

No Stage 4.2 repository mutation has occurred.

R6 resolves the two remaining blockers reported by the consolidated R5 read-only audit:

1. G103 production-default status/material ambiguity;
2. G110 pure-major-moment algebraic-target versus native-serialized-result ambiguity.

No accepted dependency, physical topology, material property, resistance factor, or engineering method is changed.

## 1. Production default material/factor authority

Do **not** change the locked production-default ICE material record merely to make the default Stage 4.2 result reach `SOURCE_REQUIRED`.

Do **not** change native resistance/modification factors merely to make a benchmark pass.

The controlling production-default physical fixture uses:

`CURRENT_LOCKED_ICE_MATERIAL_RECORD_UNCHANGED`

and:

`CURRENT_ACCEPTED_NATIVE_FACTOR_PATH_UNCHANGED`.

Codex shall identify and bind the exact repository material/factor fingerprints used by the current production-default fixture.

## 2. Status precedence controls G103

The accepted Stage 4.2 FRP-side precedence remains:

1. invalid input/geometry;
2. evaluated required failure -> `FAIL`;
3. missing required qualified source -> `SOURCE_REQUIRED`;
4. unavailable coverage/interaction -> `NOT_EVALUATED`;
5. all required internal checks pass -> `PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`.

The consolidated audit proved that, for the production-default physical fixture, an evaluated top-flange-angle local bearing failure exists before missing qualified sources can govern.

Therefore the controlling G103 result is:

`FAIL`.

Missing connector/attachment qualified sources remain present and visible in the trace, but they are subordinate to the evaluated failure.

For audit only, Codex observed approximately:

- native top-flange demand `3.850740 kip/bolt`;
- transverse bearing capacity `2.7 kip` with unity modifiers/excluded threads;
- `1.62 kip` with the single-lap factor.

Those approximate numbers are **not** new controlling golden literals. The actual native local-check result/status from the accepted production path is the oracle.

## 3. No pass-by-material substitution

Prohibited:

- selecting another production default material to force `SOURCE_REQUIRED`;
- changing the ICE material properties;
- changing bearing factors;
- suppressing an evaluated local failure because a qualified source is absent;
- short-circuiting local checks before status precedence is evaluated.

The software must expose the real production-default result.

A default configuration is allowed to fail.

## 4. G104 success state clarified

G104 is **not** a claim that the production-default physical fixture passes.

G104 is a status-aggregation contract case.

It proves only that when:

- every required evaluated local/member/fastener check is PASS;
- every required qualified connector source is present/applicable/pass;
- every required qualified member-attachment source is present/applicable/pass;
- all required coverage/interaction authority is available;

the highest allowed internal success state is:

`PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`.

Ordinary `PASS` remains prohibited.

G104 shall not define or invent alternate material properties or factors.

G103 remains the production-default physical status case.

## 5. Pure-major-moment native result

For:

- `P_L=0`;
- `V_V=0`;
- `M_T=+100 kip-in`;

the complete accepted native pipeline returns an exact finite serialized wall result whose right-hand major moment differs from the algebraic target by:

`+2E-78 kip-in`.

The algebraic target is:

`-100 kip-in`.

The equivalent structural algebraic target is:

`+100 kip-in`.

The corresponding structural serialized residual is:

`-2E-78 kip-in`.

## 6. G110 comparison rule

G110 shall retain both authorities:

### Algebraic proof target

Right-hand:

`-100 kip-in`.

Structural:

`+100 kip-in`.

### Native serialized result

The controlling numerical result is the exact relational sum produced by the prescribed immutable-engine pipeline.

The golden shall compare Stage 4.2 output to that exact native relational pipeline result.

The `±2E-78 kip-in` values are audit residuals versus the algebraic target.

No tolerance is introduced.

No dependency result is rounded or modified.

No residual is redistributed.

## 7. Pure-moment equilibrium proof

Pure-moment equilibrium is accepted by composition of:

1. Slice 5 algebraic equilibrium proof;
2. exact Stage 4.2 component allocation;
3. two Slice 8 web-group equilibrium proofs;
4. four Slice 7 connector-core equilibrium proofs;
5. exact Stage 4.2 signed coordinate transforms and reference shifts.

The tiny native serialization residual does not replace or weaken this proof.

## 8. Cross-engine rule

R6 continues the established project rule:

**immutable accepted engines own their native numerical outputs.**

A successor product shall not create a second numerical oracle by independently re-evaluating the same mechanics at another precision or through another unit-conversion path.

## 9. Supersession

The Stage 4.2 RC1-R5 golden is superseded before implementation.

The controlling golden is:

`FRP_MASTER_CONNECTION_STAGE_4_2_WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_GOLDEN_BENCHMARKS_RC1_R6.json`.

It contains exactly G1-G128.

R3/R4/R5 and the original Stage 4.2 authority remain controlling in all other respects.

## 10. No scope change

R6 changes no:

- geometry;
- load allocation;
- Slice 5 behavior;
- Slice 7 behavior;
- Slice 8 behavior;
- Stage 2.5A behavior;
- material properties;
- resistance factors;
- qualified-source requirements;
- external concrete/anchor boundary;
- 316SS scope;
- later moment-family scope.

**END OF STAGE 4.2 DEFAULT STATUS AND PURE-MOMENT NUMERIC AUTHORITY CLARIFICATION R6**
