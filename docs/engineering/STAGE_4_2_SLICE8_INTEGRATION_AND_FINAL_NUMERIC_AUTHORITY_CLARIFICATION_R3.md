# FRP Master Connection — Stage 4.2 — Slice 8 Integration and Final Numeric Authority Clarification R3

## Status

**Controlled pre-implementation clarification R3.**

No physical Stage 4.2 repository mutation has occurred.

R3 is the controlling successor clarification for Stage 4.2 RC1 implementation.

It supersedes only the conflicting portions of prior Stage 4.2 R1/R2 concerning:

- member-side web in-plane bolt-group demand;
- use of Stage 2.5A for independently applied `M_C`;
- final serialized wall-moment diagnostic values.

All previously approved Stage 4.2 physical topology, FRP connector-provider authority, qualified-source boundaries, finite-wall geometry, external anchor/concrete design boundary, freeze protection, and future-316SS boundary remain unchanged.

## Accepted starting baseline

Stage 4.2 R3 starts from:

`473a3c8cd43f13022d254dae2477084895478c74`

Commit count:

`106`.

This includes:

### Calculation Slice 8 engineering implementation

`9f86a5685be840b271929cf3298f17a5e401b7c8`

Subject:

`feat: add in-plane bolt-group wrench demand engine`.

### Test-only Windows frontend CI stabilization successor

`473a3c8cd43f13022d254dae2477084895478c74`

Subject:

`test: stabilize Windows multi-row workspace timeout`.

The stabilization changes no production or engineering behavior.

### Hosted acceptance

GitHub Actions:

- run `#101`;
- attempt `2`;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS.

Calculation Slice 8 is formally accepted.

## Stage 2.5A boundary

Stage 2.5A remains immutable.

It shall continue to be used within its accepted scope, including the Stage 4.2 top/bottom flange member-side in-plane groups where no independently applied in-plane free moment must be transferred.

Stage 2.5A shall **not** be used for the Stage 4.2 web member-side groups because those groups receive a true independent `M_C` at their member-interface centroid.

The accepted warning:

`MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL`

must not be triggered as a normal Stage 4.2 web calculation path.

## Calculation Slice 8 boundary

For the positive and negative web-angle member-side groups, use:

`RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1`.

Pass the complete in-plane wrench:

- `F_A`;
- `F_B`;
- independently applied `M_C,R`;

with the actual physical 2×2 common web-bolt coordinates and exact group reference.

Slice 8 owns:

- exact rational centroid/J;
- exact wrench transport;
- direct equal shares;
- independent/eccentric moment correction;
- exact rational force/moment proof;
- Decimal-80 projected per-bolt vectors/magnitudes;
- fingerprint.

Stage 4.2 consumes those outputs verbatim.

Do not recompute the vectors in Stage 4.2.

Do not emulate Stage 2.5A's native rounding.

## Stage 4.2 default web inputs

Positive web:

- `F_A=+5 kip`;
- `F_B=+3.6 kip`;
- `M_C,R=+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

Negative web:

- `F_A=-5 kip`;
- `F_B=+3.6 kip`;
- `M_C,R=-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

The negative `M_C` is the exact full mathematical negative of the positive value.

## Common web-bolt two-plane demand

The physical shank remains:

`NEGATIVE_WEB_CLIP_ANGLE_MEMBER_LEG -> W/I_WEB -> POSITIVE_WEB_CLIP_ANGLE_MEMBER_LEG`.

Use:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

Its two actual plane vectors come from the two accepted Slice 8 web-group outputs.

No blind equal-plane assumption.

No blind double-shear capacity sum.

No stage-level force/n shortcut.

## Out-of-plane member attachment boundary

Slice 8 evaluates only the member-leg in-plane wrench components.

The member-interface:

- `F_C`;
- `M_A`;
- `M_B`;

remain explicit qualified member-attachment source demand exactly as previously approved.

Slice 8 does not authorize pull-through, prying, through-thickness, or bolt-axis capacity.

## Cross-engine numeric authority

R3 preserves native-engine boundaries.

### Slice 5

Calculation Slice 5 retains its accepted Decimal-80 / `ROUND_HALF_EVEN` output authority and algebraic equilibrium proof.

Stage 4.2 consumes its component outputs verbatim.

### Stage 4.2 pre-core/member-interface construction

Stage 4.2-owned finite Decimal calculations use the accepted Decimal-80 / `ROUND_HALF_EVEN` contract.

### Slice 7

Once a member-interface wrench enters Slice 7, unchanged Slice 7 native exact-rational transport/serialization governs.

Slice 7 heel/support outputs and FRP-provider results are consumed verbatim.

### Slice 8

Once a web in-plane member-group wrench enters Slice 8, Slice 8 exact-rational mechanics govern.

Its Decimal-80 projections are consumed verbatim by downstream accepted resistance/vector consumers.

### Wall assembly

Connector support wrenches are transformed by exact signed axis permutations and exact rational reference shifts/sums on the finite dependency outputs.

No dependency output is rounded or modified to force an algebraic target.

## Correct final wall diagnostic

Following the complete prescribed R3 pipeline gives the default serialized aggregate diagnostic:

- axial residual versus `20 kip`: `+3E-79 kip`;
- right-hand wall major-moment residual versus `-105 kip-in`: `+6E-79 kip-in`;
- structural wall major-moment residual versus `+105 kip-in`: `-6E-79 kip-in`.

The prior `±5.85E-79 kip-in` diagnostic is superseded.

The difference arises because the full prescribed pipeline includes the Stage 4.2 Decimal-80 pre-core member-wrench construction before native Slice 7 transport.

These residuals are audit diagnostics only.

They are not:

- tolerances;
- equilibrium failures;
- physical residual forces/moments;
- values to redistribute.

Never alter any connector, bolt, anchor group, wall group, or reaction to remove them.

## Global equilibrium proof

Global equilibrium is proven compositionally from:

1. accepted Slice 5 algebraic equilibrium proof;
2. exact Stage 4.2 component allocation;
3. two Slice 8 exact in-plane web-group wrench proofs;
4. four unchanged Slice 7 connector-core equilibrium proofs;
5. exact Stage 4.2 signed coordinate transforms;
6. exact Stage 4.2 rigid-body reference shifts/sums.

The algebraic default target remains:

- force `(20,-10,0) kip`;
- right-hand wall moment `(0,0,-105) kip-in`;
- structural wall major moment `+105 kip-in`.

No epsilon comparison.

No residual dumping.

## Golden authority

The controlling Stage 4.2 golden is now:

`FRP_MASTER_CONNECTION_STAGE_4_2_WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_GOLDEN_BENCHMARKS_RC1_R3.json`.

It contains exactly `G1-G128`.

For immutable dependency outputs, it uses direct dependency-exact or relational authority rather than duplicate precision-specific numeric strings where appropriate.

Production code shall not read the golden.

## Implementation commit

After all R3 pre-mutation gates pass, the Stage 4.2 implementation commit remains:

`feat: add W/I beam-to-concrete-wall moment connection`.

Starting count:

`106`.

Expected final count:

`107`.

## Visual QA

Because Stage 4.2 is a physical frontend product, local visual QA is mandatory before final publication.

Codex shall:

1. start existing backend and frontend development servers in persistent terminal sessions;
2. wait for health/readiness;
3. open the local application in the Codex built-in browser;
4. execute the prescribed Stage 4.2 visual/result matrix;
5. inspect console/network/CDP evidence when available;
6. capture/report discrepancies before correction;
7. terminate only the server processes it started after review.

Owner final visual acceptance remains required before freeze.

## No other scope change

R3 does not implement:

- 316SS;
- concrete/anchor capacity;
- minor shear;
- minor-axis moment;
- torsion;
- stiffness/rotation/full-strength classification;
- later moment families.

**END OF STAGE 4.2 SLICE 8 INTEGRATION AND FINAL NUMERIC AUTHORITY CLARIFICATION R3**
