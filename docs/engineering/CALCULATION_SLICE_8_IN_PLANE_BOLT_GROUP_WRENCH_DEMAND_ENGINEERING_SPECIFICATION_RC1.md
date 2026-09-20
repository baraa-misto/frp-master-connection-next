# FRP Master Connection — Calculation Slice 8 — Generalized In-Plane Bolt-Group Wrench Demand — Engineering Specification RC1

## 1. Status

Controlled backend calculation authority.

Accepted baseline before implementation:

`d940192ea8eecb7e35f9601c38f3ad841f580916`

Expected commit count:

`104`.

Physical Stage 4.2 has not begun.

## 2. Problem statement

The existing Stage 2.5A eccentric-demand engine does not transfer independently applied member/group moments.

That behavior is accepted and frozen.

Moment-connection successors require a shared engine that accepts a complete in-plane wrench without:

- discarding `M_C`;
- fabricating a force line;
- translating free moment into an invented eccentricity;
- mutating Stage 2.5A.

## 3. Method

`RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1`.

RC1 assumption:

- all bolts in the evaluated group participate with equal in-plane translational stiffness.

No slip-critical stiffness, nonlinear contact, bolt clearance sequencing, or unequal-stiffness distribution is introduced.

## 4. Input contract

Required:

- `bolt_coordinates`: ordered list of unique finite `(A_i,B_i)` coordinates;
- `wrench_reference`: finite `(A_R,B_R)`;
- signed finite `F_A`;
- signed finite `F_B`;
- signed finite free moment `M_C,R`.

Units must be consistent.

Input numeric types:

- Decimal / losslessly parsed decimal strings;
- exact integers where supported.

Binary floats are prohibited at the calculation boundary.

## 5. Coordinate convention

Right-handed local plane:

`A × B = C`.

Positive `M_C` follows the right-hand rule.

Per-bolt moment contribution about the group centroid:

`(A_i-A_c)q_B,i - (B_i-B_c)q_A,i`.

## 6. Exact arithmetic authority

Convert each finite Decimal input losslessly to an exact rational value.

Use exact rational arithmetic for:

- centroid;
- coordinate deltas;
- `J`;
- reference transport;
- direct shares;
- elastic corrections;
- per-bolt vector components;
- equilibrium proofs.

Recommended implementation may use Python standard-library exact rational infrastructure.

No new dependency is authorized.

## 7. Centroid

For `n >= 1`:

`A_c = ΣA_i/n`

`B_c = ΣB_i/n`.

Centroid is based on equal bolt stiffness/participation.

## 8. Group polar coordinate sum

`ΔA_i=A_i-A_c`

`ΔB_i=B_i-B_c`

`J=Σ(ΔA_i^2+ΔB_i^2)`.

`J >= 0`.

For any physically noncoincident multi-bolt group:

`J > 0`.

## 9. Wrench transport

Exact moment at centroid:

`M_C,c = M_C,R + (A_R-A_c)F_B - (B_R-B_c)F_A`.

This transports the full wrench.

`M_C,R` is a true free moment and is never replaced by an equivalent force eccentricity.

## 10. Direct force

For equal stiffness:

`q_A,d=F_A/n`

`q_B,d=F_B/n`.

## 11. Moment correction

When `M_C,c != 0` and `J > 0`:

`q_A,m,i=-M_C,c ΔB_i/J`

`q_B,m,i=+M_C,c ΔA_i/J`.

When `M_C,c=0`:

both corrections are exact zero.

## 12. Total bolt vector

`q_A,i=q_A,d+q_A,m,i`

`q_B,i=q_B,d+q_B,m,i`.

Retain signed components.

## 13. Exact equilibrium proof

Require exact rational identities:

`Σq_A,i=F_A`

`Σq_B,i=F_B`

`Σ(ΔA_i q_B,i - ΔB_i q_A,i)=M_C,c`.

Also return the equivalent moment about the original wrench reference and prove exact recovery of `M_C,R`.

## 14. Pure moment

For `F_A=F_B=0`, `M_C,R != 0`, `J>0`:

- direct force shares are zero;
- moment corrections are nonzero;
- total bolt force sum is exactly zero;
- bolt moment sum exactly equals the applied free moment.

Status:

`CALCULATED`.

## 15. Force-only / eccentric-force compatibility

When `M_C,R=0`, the transported centroid moment contains only the physical force-reference eccentricity.

Within equal-share Stage 2.5A applicability, Slice 8 shall reproduce Stage 2.5A per-bolt vectors.

Compatibility is a mandatory regression test, not a reason to modify Stage 2.5A.

## 16. Single-bolt behavior

For one bolt:

`J=0`.

If transported `M_C,c=0`, transfer the full in-plane force to that bolt.

If transported `M_C,c != 0`:

`CALCULATION_NOT_SUPPORTED_ZERO_GROUP_POLAR_SUM`.

Do not fabricate a couple.

## 17. Zero wrench

For a valid group and zero full wrench:

all exact vectors and Decimal projections are zero.

## 18. Invalid input

Fail closed for:

- empty coordinate list;
- duplicate physical bolt coordinates;
- nonfinite inputs;
- prohibited binary-float calculation inputs;
- inconsistent/missing coordinate components;
- nonzero transported moment with `J=0`.

No auto-repair.

## 19. Exact rational output

For every rational field return canonical numerator/denominator form.

At minimum:

- centroid;
- deltas;
- `J`;
- transported moment;
- per-bolt `q_A`;
- per-bolt `q_B`;
- exact proof sums.

Canonical equivalent fractions shall normalize sign to the numerator and denominator positive.

## 20. Decimal projection

For existing downstream Decimal resistance engines, project exact rational force components under a local context:

- precision `80`;
- rounding `ROUND_HALF_EVEN`.

Never depend on ambient/global Decimal context.

No quantization to a fixed number of decimal places.

## 21. Magnitude

Per bolt:

`q_i = sqrt(q_A,i^2 + q_B,i^2)`.

The squared magnitude is retained exactly as a rational.

The magnitude itself is projected to Decimal-80 / `ROUND_HALF_EVEN`.

## 22. Fingerprint

Include:

- method/version;
- ordered canonical coordinate set;
- reference;
- input wrench;
- exact centroid/J;
- exact transported moment;
- exact rational per-bolt vectors;
- numeric projection contract;
- applicability/status;
- proof identity.

Fingerprint excludes presentation formatting.

## 23. Deterministic ordering

Result bolt order follows the input physical bolt identity/order.

Fingerprint must also bind bolt identity/order so vectors cannot silently attach to different bolts.

A separate unordered-geometry fingerprint may be provided if existing architecture supports it, but shall not replace the physical result ordering.

## 24. Translation invariance

If every bolt coordinate and the wrench reference are translated by the same in-plane vector:

- deltas unchanged;
- `J` unchanged;
- transported centroid moment unchanged;
- per-bolt vectors unchanged.

Mandatory test.

## 25. Sign reversal

Negating the complete wrench:

`(F_A,F_B,M_C,R) -> (-F_A,-F_B,-M_C,R)`

must negate every per-bolt vector exactly.

Magnitudes remain unchanged.

## 26. U.S./SI equivalence

Equivalent converted geometry/actions preserve the physical solution and exact dimensionless relationships.

Decimal display conversion remains presentation-only.

## 27. Default Stage 4.2 positive-web fixture

Coordinates:

`(-1.5,-0.75)`

`(+1.5,-0.75)`

`(-1.5,+0.75)`

`(+1.5,+0.75) in`.

Reference:

`(0,0) in`.

Input:

`F_A=+5 kip`

`F_B=+3.6 kip`

`M_C=+1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.

This is the exact Stage 4.2 positive web member-interface in-plane wrench identified by the halted audit.

The negative-web fixture reverses `F_A` and `M_C`, while retaining `F_B`.

## 28. Pure-moment benchmark

Same 2×2 group.

Input:

`F_A=0`

`F_B=0`

`M_C=+9 kip-in`.

Exact bolt vectors:

- Bolt 1: `(+0.6,-1.2) kip`;
- Bolt 2: `(+0.6,+1.2) kip`;
- Bolt 3: `(-0.6,-1.2) kip`;
- Bolt 4: `(-0.6,+1.2) kip`.

Exact force sum zero.

Exact moment sum `+9 kip-in`.

## 29. Eccentric-force compatibility benchmark

Same group.

Reference:

`(0,+2) in`.

Input:

`F_A=+8 kip`

`F_B=0`

`M_C,R=0`.

Transported moment:

`-16 kip-in`.

This shall match the existing Stage 2.5A equal-share eccentric-force solution for the equivalent accepted force/reference case.

## 30. Arbitrary-reference benchmark

Same group.

Reference:

`(+2,+1) in`.

Input:

`F_A=+4 kip`

`F_B=-2 kip`

`M_C,R=+3 kip-in`.

Exact centroid moment:

`-5 kip-in`.

Require exact force and moment recovery.

## 31. Stage 4.2 successor seam

After Slice 8 acceptance, Stage 4.2 shall use Slice 8 only for member-side in-plane groups where an independent `M_C` must transfer.

Existing Stage 2.5A remains used where its accepted force/eccentricity-only applicability is sufficient.

Stage 4.2 R3 is outside this implementation.

## 32. Downstream vector consumption

Slice 8 returns actual per-bolt in-plane vectors suitable for existing downstream:

- bolt shear magnitude checks;
- local FRP bearing direction checks;
- unequal/common-bolt two-plane methods.

Those downstream methods remain unchanged.

## 33. No resistance

Slice 8 calculates demand only.

It does not calculate:

- bolt capacity;
- FRP capacity;
- bearing;
- net tension;
- shear-out;
- block shear;
- prying;
- pull-through;
- anchor/concrete capacity.

## 34. Frontend/API boundary

Frontend production change:

`0`.

New public product endpoint:

`0`.

No selector/workspace change.

## 35. Dependencies/workflows/tags

Authorized changes:

- dependencies `0`;
- lockfiles `0`;
- workflows `0`;
- tags `0`.

## 36. Controlled golden

Companion RC1 golden contains exactly `G1-G80`.

## 37. Acceptance

Accept only if:

- independent free moment is transferred without invented force eccentricity;
- pure moment works;
- exact rational force/moment proofs close;
- Decimal projection is deterministic/local-context;
- compatibility with existing Stage 2.5A eccentric-force fixtures passes;
- Stage 2.5A remains unchanged;
- Slices 5 and 7 remain unchanged;
- full QA/coverage/object-isolated/hosted CI passes.

**END OF CALCULATION SLICE 8 IN-PLANE BOLT-GROUP WRENCH DEMAND ENGINEERING SPECIFICATION RC1**
