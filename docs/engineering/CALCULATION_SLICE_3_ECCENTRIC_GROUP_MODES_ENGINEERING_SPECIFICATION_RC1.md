# FRP Master Connection
# Calculation Slice 3 Eccentric Group-Mode Compatibility Engineering Specification — RC1

**Document status:** Candidate engineering specification pending Baraa Misto approval  
**Not a Codex implementation order**  
**Proposed implementation stage after approval:** Stage 2.6A  
**Calculation family:** Eccentric inter-row shear-out handoff and first-row net-tension compatibility boundary  
**Primary standard:** ASCE/SEI 74-23  
**Parent demand authority:** Calculation Slice 3 RC1 / Stage 2.5A  
**Parent resistance authority:** Calculation Slice 2 RC2 / Stage 2.4B  
**Parent compatibility authority:** Stage 2.5B Resistance Handoff RC1

## 1. Purpose

This RC1 extends the accepted eccentric demand-to-resistance compatibility model only where the source mechanics and existing resistance equations support a defensible mapping.

It has two objectives:

1. authorize a controlled eccentric inter-row shear-out demand handoff when an actual physical bolt-line resultant remains aligned with the connection-force direction; and
2. formally resolve that a general automatic eccentric first-row net-tension handoff is not established by the current ASCE source model or approved project mechanics.

This RC1 does not change the Stage 2.5A bolt-demand equations or Stage 2.4B resistance equations.

## 2. Source basis

ASCE/SEI 74-23 Section 2.9 requires eccentric fastener effects to be analyzed using established mechanics.

Commentary C8.1 states that moment-induced internal forces are distributed linearly with distance from the center of rotation.

Section 8.3.3.1 and Appendix CA8.3.3 define first-row net tension for a connection force perpendicular to the bolt rows.

Commentary C8.3.3.1 explains that the first-row net-tension model combines the stress concentration caused by first-row bolt bearing with the stress concentration from the bypass load. Appendix CA8.3.3.1 assumes identical bolts contact their holes in the direction of the connection force and that each bolt within a row bears an equal share of the row load.

Section 8.3.3.2 defines shear-out strength per line of bolts. The Chapter 8 single-row wording likewise identifies shear-out per bolt in a line parallel to the direction of applied force.

The standard does not supply a general noncollinear eccentric first-row net-tension stress model.

## 3. Evidence classification

### 3.1 Direct source-derived

- existing first-row resistance equations and Appendix full formulae;
- existing inter-row shear-out resistance equations;
- physical definition of bolt rows, pitch, and bolt lines;
- requirement to account for actual eccentric load effects.

### 3.2 Approved parent mechanics

- Stage 2.5A actual per-bolt total in-plane vectors;
- Stage 2.5A deterministic bolt identities and coordinates;
- Stage 2.4A physical row and bolt-line identities;
- Stage 2.4B existing first-row and shear-out resistance functions.

### 3.3 New project rational extension

`RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF`

This method sums the actual Stage 2.5A bolt vectors on one complete physical bolt line and permits the existing shear-out resistance comparison only when that resultant remains parallel to the canonical connection-force direction.

### 3.4 Deliberate unsupported boundary

A general nonzero-residual-moment first-row net-tension handoff remains unsupported in RC1.

This is not a software omission. It is an engineering limitation based on the assumptions of the source model.

## 4. Canonical connection-force direction

Let the nonzero in-plane connection resultant be `F_p`.

Define the canonical unit direction:

`e_f = F_p / |F_p|`

Use the accepted Decimal/vector architecture.

Screen orientation has no authority.

If `|F_p| = 0`, no eccentric shear-out handoff is available under this RC1.

## 5. Physical bolt-line resultant

For each complete physical bolt line `k` identified by accepted Stage 2.4A geometry:

`R_line,k = sum(Q_i)`

for all physical bolts `i` belonging to that line, where `Q_i` is the exact Stage 2.5A total in-plane bolt-demand vector.

Retain the individual vectors in trace.

Do not use direct components only, row-average force, total force divided equally between lines, maximum bolt force copied to a line, or screen geometry.

## 6. Parallel / transverse decomposition

Calculate:

`q_parallel,k = R_line,k · e_f`

and the signed in-plane transverse component using the repository canonical two-dimensional vector/cross-product convention.

No new arbitrary angular or force tolerance is introduced.

The deterministic canonical Decimal representation established by Stage 2.5A and Stage 2.5C remains authoritative.

## 7. Shear-out handoff states

### 7.1 Zero line demand

If `R_line,k = 0`:

`handoff = NOT_REQUIRED_ZERO_LINE_DEMAND`

No utilization is fabricated.

### 7.2 Positive parallel line demand

If the transverse component is zero and `q_parallel,k > 0`:

`handoff = AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT`

and:

`V_u,line,k = q_parallel,k`

Use the existing Stage 2.4B shear-out resistance for that physical line and geometry.

### 7.3 Nonparallel line resultant

If the transverse component is nonzero:

`handoff = CALCULATION_NOT_SUPPORTED`

with:

`ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE`

Do not use resultant magnitude or an arbitrary projection as a replacement.

### 7.4 Reversed line demand

If the transverse component is zero and `q_parallel,k < 0`:

`handoff = CALCULATION_NOT_SUPPORTED`

with:

`ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED`

RC1 does not automatically rebuild an opposite-end shear-out failure path for one reversed bolt line.

## 8. Shear-out resistance

When authorized, reuse the accepted Stage 2.4B resistance method applicable to that physical line:

- Equation 8-12 for the accepted two-row case;
- Equation 8-13 for the accepted three-row case;
- the already approved actual-row-span rational extension for more than three rows.

Do not change `e1`, pitch, row span, thickness, `Fsh`, `phi`, `lambda`, `C_lap`, `C_delta`, end-use factors, or qualification.

Only the required line demand changes to the actual Stage 2.5A line resultant.

## 9. Why the eccentric shear-out mapping is limited to parallel line resultants

The source strength is defined for a bolt line parallel to the applied connection force.

A nonparallel line resultant creates a coupled line-force state for which RC1 has no source-defined shear-out interaction.

Using full resultant magnitude would assume that transverse force produces the same shear-out mechanism.

Using only the parallel projection while ignoring a nonzero transverse component would discard part of the actual load state.

Both are prohibited without a separately approved mechanics model.

## 10. First-row net-tension source assumptions

The accepted first-row method is based on:

- connection force perpendicular to bolt rows;
- first-row bolt bearing in that connection-force direction;
- row bearing proportion `L_br`;
- bypass load `1 - L_br`;
- equal sharing between identical bolts within a row;
- bearing/bypass stress-concentration interaction in Appendix CA8.3.3.2.

These assumptions are explicit in the commentary and Appendix basis.

## 11. Nonzero residual moment and first-row net tension

For the Stage 2.5A equal-stiffness eccentric correction, a nonzero residual moment creates bolt-vector components that are not generally collinear with the connection resultant.

For ordinary rectangular multi-row geometry, first-row bolt forces may differ in magnitude across the row, include components transverse to the original connection-force direction, and create a row resultant that is not collinear with the connection force.

The current source model does not define how these noncollinear/unequal bearing forces combine with bypass loading to establish first-row net-tension strength.

Therefore, for `M_res != 0`, the default RC1 result is:

`first_row_net_tension_handoff = CALCULATION_NOT_SUPPORTED`

with:

`ECCENTRIC_FIRST_ROW_NET_TENSION_GENERAL_METHOD_NOT_ESTABLISHED_RC1`

## 12. Legacy-equivalent first-row case

When `M_res = 0`, the existing Stage 2.4B first-row method remains fully authorized and unchanged.

No new first-row calculation path is introduced by this RC1.

If a future nonzero-residual case is shown to satisfy every source assumption exactly, including equal per-bolt bearing within each row and collinearity of bearing and bypass force with the connection force, it requires a separately approved engineering review before automatic implementation.

RC1 does not infer that exception.

## 13. Why no new actual-Lbr formula is approved here

Although the Appendix equations contain `L_br`, the source obtains it from a row-load model in which bolts bear in the connection-force direction and share row load equally.

Substituting only the scalar resultant of an eccentric first row would discard the actual noncollinear and unequal bolt-bearing state.

Therefore RC1 shall not automatically calculate `L_br,eccentric = |R_row1| / |F_p|` or any similar scalar replacement.

## 14. Failure precedence and whole-result disposition

A known failure from an authorized eccentric shear-out line remains `FAIL` even when first-row net tension is unsupported.

If all authorized checks pass but first-row net tension remains required and unsupported:

- ordinary PASS is prohibited;
- whole result remains fail-closed (`NOT_EVALUATED` or repository equivalent).

Unsupported checks remain visible.

## 15. Required check exemptions

Preserve accepted source-authorized exemptions.

If first-row net tension or shear-out is not required because the existing canonical connection configuration meets an accepted exemption, do not manufacture an unsupported required check.

The eccentric compatibility model does not revoke existing exemptions.

## 16. More-than-three-row geometry

The existing Stage 2.4B rational actual-row-span shear-out extension may consume an authorized eccentric line demand under this RC1.

It remains outside prescriptive scope and retains Section 2.3.2 qualification.

No eccentric first-row extension is added for more-than-three-row geometry.

## 17. Result contract

The group-mode compatibility result shall retain:

- parent Stage 2.5A result fingerprint;
- parent Stage 2.5B handoff/result identity;
- physical line IDs;
- bolt IDs contributing to each line;
- individual `Q_i` vectors;
- line resultant vector;
- parallel scalar;
- transverse scalar;
- handoff status;
- line demand;
- existing shear-out resistance result where authorized;
- first-row compatibility status;
- unsupported/failed/required IDs;
- qualification;
- warnings;
- governing/co-governing results;
- deterministic fingerprint;
- method/source trace.

## 18. Version identities

Proposed implementation identities:

`calculation_contract_version = 2.6A-RC1`

`eccentric_group_mode_engine_version = 0.1.0.dev1`

`eccentric_group_mode_rule_set_version = asce74-23-ch8-eccentric-group-modes-rc1.dev1`

`eccentric_group_mode_result_schema_version = 0.1.0-draft`

`eccentric_group_mode_fingerprint_schema_version = 0.1.0-draft`

These do not replace parent calculation identities.

## 19. Fingerprinting

Include Stage 2.5A result fingerprint, physical bolt-line membership, actual line resultant vectors, compatibility classifications, existing shear-out plan/resistance identity, first-row unsupported status, and RC1 version/method identities.

Exclude presentation-only state.

## 20. Numerical policy

Reuse accepted Decimal/vector/unit behavior.

No authoritative binary float.

No intermediate engineering rounding.

No new arbitrary zero/angle tolerance.

Golden values serialize to 12 decimal places with `ROUND_HALF_EVEN`.

## 21. Deliberate exclusions

RC1 does not define:

- general eccentric first-row net-tension demand;
- a scalar eccentric `L_br` replacement;
- nonparallel shear-out interaction;
- reversed-line opposite-end shear-out path generation;
- member-end moment transfer;
- bolt-axis tension distribution;
- prying;
- friction/slip;
- new resistance equations;
- frontend/API/application integration.

## 22. Benchmark authority

The companion golden is the candidate machine-readable benchmark authority after owner approval.

Production must derive every value.

Parent goldens remain immutable.

## 23. Implementation sequence after approval

After specification, golden, and independent ledger approval:

- Stage 2.6A may implement the framework-independent eccentric group-mode compatibility engine;
- it may extend Stage 2.5B supported shear-out handoff;
- it shall preserve first-row net tension as unsupported for general nonzero residual moment;
- no frontend/API/application integration is authorized in Stage 2.6A.

A future first-row eccentric mechanics stage shall require new source/test evidence or a separately approved rational/experimental model.
