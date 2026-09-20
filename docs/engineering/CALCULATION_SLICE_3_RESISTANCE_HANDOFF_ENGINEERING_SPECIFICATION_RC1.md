# FRP Master Connection
# Calculation Slice 3 Resistance Handoff Engineering Specification — RC1

**Document status:** Candidate engineering specification pending Baraa Misto approval  
**Not a Codex implementation order**  
**Stage target after approval:** Stage 2.5B  
**Calculation family:** Eccentric bolt-group demand to directional FRP resistance compatibility and handoff  
**Primary standard:** ASCE/SEI 74-23  
**Parent demand authority:** Calculation Slice 3 RC1 / Stage 2.5A  
**Parent resistance authority:** Calculation Slice 2 RC2 / Stage 2.4B

## 1. Purpose

This RC1 defines the controlled compatibility layer between the accepted Stage 2.5A eccentric bolt-group demand engine and the accepted Stage 2.4B FRP resistance engine.

It does not create a new bolt-group demand algorithm and does not create new resistance equations.

Its purpose is to answer, check by check, which Stage 2.5A demand quantities may safely become Stage 2.4B resistance demands, which directional FRP properties must be selected, and which group failure modes must remain fail-closed when eccentric per-bolt force directions invalidate the assumptions of the existing multi-row resistance method.

## 2. Source basis

Use concise locators:

- ASCE/SEI 74-23 Section 2.9;
- Sections 8.3.2.1 through 8.3.2.3;
- Equation 8-6;
- Commentary C8.1;
- Commentary C8.3.2;
- Commentary C8.3.3.1;
- Commentary C8.3.3.3;
- Appendix CA8.3.3.1.

The source requires connection strength to be evaluated from the actual force distribution.

For pin bearing, the source defines the property family from the orientation of the resultant force at the bolt/FRP contact relative to the FRP pultrusion direction.

The multi-row first-row formulation and Appendix row distribution are based on bolts bearing in the direction of the connection force and on the Table C8-1 bearing/bypass distribution.

The source provides a distinct eccentric block-shear strength equation but notes the limited pultruded-FRP test basis.

## 3. Evidence classification

### 3.1 Direct source-derived compatibility

The following are source-derived or direct reuse of source-derived accepted behavior:

- each bolt's actual in-plane force magnitude is the bolt-shear demand;
- pin-bearing direction is based on the actual resultant force at that bolt/FRP interface;
- bolt combined tension/shear may use the actual in-plane bolt-shear demand with independently explicit bolt-axis tension;
- pull-through remains driven by independently explicit bolt-axis demand;
- Equation 8-14a/b block-shear comparison uses the connection-level in-plane resultant when the existing block-path/eccentricity context is physically compatible.

### 3.2 Inherited accepted behavior

When the Stage 2.5A residual moment is exactly zero, all per-bolt in-plane vectors remain the inherited direct vectors and are collinear with the connection resultant.

The existing Stage 2.4B demand and resistance semantics may then be reused without numerical reinterpretation.

### 3.3 Project fail-closed compatibility rules

For a nonzero Stage 2.5A residual moment:

- per-bolt bolt shear may calculate;
- per-bolt/per-layer pin bearing may calculate;
- combined bolt checks may calculate only with explicit bolt-axis tension;
- first-row net tension is not automatically handed off in RC1;
- inter-row shear-out is not automatically handed off in RC1;
- eccentric block shear is conditionally handed off only under the compatibility requirements in this specification.

These are conservative software/engineering compatibility rules, not new ASCE equations.

## 4. Parent-result immutability

Stage 2.5B shall consume the accepted Stage 2.5A demand result without modifying it.

The Stage 2.5A result shall continue to state:

`resistance_handoff = NOT_AUTHORIZED_IN_RC1`

That historical parent field is not rewritten.

Stage 2.5B produces a separate handoff authority/result identifying which checks are now authorized under this specification.

The parent demand fingerprint remains unchanged.

## 5. Handoff coverage

Use:

- `FULL_LEGACY_COLLINEAR`
- `PARTIAL_ECCENTRIC`
- `BLOCKED_INCOMPLETE_ACTION_TRANSFER`

### 5.1 Full legacy collinear

When:

`M_res = 0`

and no other unresolved action-transfer condition exists, Stage 2.5B may reproduce the accepted Stage 2.4B execution semantics in full.

No resistance or utilization may change merely because the demand passed through Stage 2.5A.

### 5.2 Partial eccentric

When:

`M_res != 0`

the noncollinear per-bolt vectors activate the partial handoff matrix in Section 11.

### 5.3 Blocked incomplete action transfer

A nonzero untransferred member-end moment prevents ordinary whole-connection resistance issuance.

A nonzero interface-normal force without the required explicit bolt-axis demand prevents completion of the affected bolt tension/pull-through checks.

Supported in-plane diagnostic checks may remain visible, but ordinary PASS is prohibited.

## 6. Per-bolt in-plane demand

For each physical bolt `i`, Stage 2.5B consumes the Stage 2.5A total in-plane vector:

`Q_i = (Q_i,u, Q_i,v)`

and magnitude:

`V_i = |Q_i|`

`V_i` is the required in-plane bolt-shear demand.

Do not use:

- the original row-average demand;
- total connection force divided by bolt count;
- direct component alone;
- moment component alone;
- maximum bolt force copied to every bolt.

## 7. Zero-demand bolt

If:

`V_i = 0`

then that bolt does not require:

- a bolt-shear comparison;
- a pin-bearing comparison.

Its bearing-force direction is:

`UNDEFINED_ZERO_DEMAND`

Do not manufacture an angle or a nonzero utilization for a zero-demand bolt.

Other independently required checks may still apply.

## 8. Per-bolt/per-layer bearing direction

For every penetrated FRP layer and every bolt with `V_i > 0`, determine the acute/sign-independent angle between the actual Stage 2.5A bolt vector `Q_i` and that layer's backend-authoritative LW axis.

The frontend/display orientation has no authority.

Use:

- `0° <= theta_i <= 5°`: `Fbr,L`
- `5° < theta_i <= 90°`: `Fbr,T`

Exactly 90 degrees remains the accepted project endpoint interpretation.

Do not interpolate between `Fbr,L` and `Fbr,T`.

The same physical bolt may therefore use different bearing property families in different penetrated FRP layers.

## 9. Pin-bearing demand

For each applicable FRP layer and bolt:

- demand = `V_i`;
- resistance = accepted Stage 2.4B/Slice 1 pin-bearing equation and factors;
- directional property = Section 8 selection above;
- geometry, thread factor, lap factor, pitch factor, end-use factors, `phi`, `lambda`, and qualification retain their accepted meanings.

Stage 2.5B changes the demand vector and directional-property selection only where required by actual force distribution.

It does not change Equation 8-5 or Equation 8-6.

## 10. Metallic bolt checks and pull-through

### 10.1 Bolt shear

Use:

`V_i = |Q_i|`

once per physical bolt.

### 10.2 Combined bolt tension/shear

When explicit bolt-axis tension is present under the accepted contracts:

- use `V_i` as the bolt shear demand;
- use the explicit bolt-axis tension unchanged;
- reuse the accepted combined bolt equation.

Stage 2.5B shall not generate bolt-axis tension.

### 10.3 Pull-through

Pull-through continues to require explicit bolt-axis demand.

Stage 2.5B shall not create prying or infer pull-through demand from eccentric in-plane force.

## 11. Nonzero-residual-moment compatibility matrix

For `M_res != 0`:

| Check family | RC1 handoff |
|---|---|
| Metallic bolt shear | Calculable using `|Q_i|` |
| Metallic combined tension/shear | Calculable only with explicit axis tension |
| Pull-through | Calculable only with explicit axis demand |
| Pin bearing | Calculable per bolt, per FRP layer, using `Q_i` direction |
| First-row net tension | `CALCULATION_NOT_SUPPORTED` |
| Inter-row shear-out | `CALCULATION_NOT_SUPPORTED` |
| Block shear | Conditionally calculable under Section 14 |
| Code geometry | Unchanged |
| Qualification | Preserved and may be strengthened, never weakened |

Unsupported required checks remain visible.

Do not remove them from the required-check set merely to obtain PASS.

## 12. Why first-row net tension is blocked for eccentric handoff RC1

The accepted first-row methods are tied to:

- the connection force direction;
- the first-row bearing proportion;
- bypass load;
- row geometry perpendicular to the connection force;
- the accepted Table C8-1 or engineer-defined direct row distribution.

Stage 2.5A's nonzero residual-moment correction creates bolt forces that are no longer all collinear with the connection resultant and alters the actual row bearing-force state.

RC1 does not define a verified transformation from those noncollinear per-bolt vectors to an effective `L_br`, bypass load, or first-row net-tension stress field.

Therefore, when `M_res != 0`:

`first_row_net_tension_handoff = CALCULATION_NOT_SUPPORTED`

Required warning:

`ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1`

Do not reuse the pre-eccentric row fraction as if it were the complete actual first-row force distribution.

## 13. Why inter-row shear-out is blocked for eccentric handoff RC1

The accepted shear-out equations are line/group modes oriented with the connection-force and row geometry.

Stage 2.5A may create both longitudinal and transverse components at an individual bolt line.

RC1 does not define whether the applicable shear-out demand is:

- line resultant magnitude;
- projection onto the connection-force direction;
- projection onto the shear plane;
- another coupled demand.

Therefore, when `M_res != 0`:

`interrow_shearout_handoff = CALCULATION_NOT_SUPPORTED`

Required warning:

`ECCENTRIC_INTERROW_SHEAROUT_HANDOFF_NOT_SUPPORTED_RC1`

Do not invent an average, projection, or magnitude rule.

## 14. Block-shear handoff

Block shear remains a connection/path-level failure mode.

For an existing accepted Stage 2.4B block-shear plan, Stage 2.5B may hand off:

`demand = |F_p|`

only when all of the following are true:

1. the block path is already accepted/valid under Stage 2.4A/2.4B;
2. material direction and path applicability remain valid;
3. the existing block-shear eccentricity context is present;
4. the existing eccentricity context is derived from the same canonical physical force line represented by the Stage 2.5A result;
5. the compatibility is explicitly proven by stable geometry/reference IDs, not by screen geometry;
6. any existing Section 2.3.2 qualification and limited-test-basis warning remain visible.

Use:

- Equation 8-14a for the existing concentric classification;
- Equation 8-14b for the existing eccentric classification.

Do not derive a new block-shear eccentricity from the bolt-force magnitudes.

If force-line/path compatibility is absent or unproven:

`block_shear_handoff = CALCULATION_NOT_SUPPORTED`

## 15. Member-end moments

If Stage 2.5A reports:

`MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL`

Stage 2.5B may display supported force-only resistance diagnostics, but:

- ordinary whole-connection PASS is prohibited;
- the overall handoff disposition is `NOT_EVALUATED` or repository-equivalent fail-closed state;
- no member-end moment is silently discarded from trace.

## 16. Out-of-plane force

If the Stage 2.5A result has nonzero `F_n`:

- do not generate bolt-axis tension;
- preserve the existing warning;
- in-plane bolt shear and bearing may calculate;
- bolt tension, combined bolt tension/shear, and pull-through remain incomplete unless explicit accepted axis demands are supplied;
- ordinary whole-connection PASS is prohibited while a required axis-demand check is incomplete.

Explicit axis demand is consumed, not derived.

## 17. Known failure precedence

A known failure in a supported handoff check remains `FAIL` even when other required checks are unsupported or incomplete.

Examples:

- a pin-bearing utilization > 1 under eccentric handoff remains a numerical failure;
- unsupported first-row net tension remains separately visible;
- qualification remains separately visible.

Do not downgrade a known failure to `NOT_EVALUATED`.

## 18. Supported-check PASS is not ordinary PASS

When all calculated supported checks pass but one or more required checks are unsupported under Sections 12 or 13:

- numerical comparison / whole-result disposition remains fail-closed;
- ordinary ASCE PASS is prohibited.

An incomplete compatibility matrix shall never masquerade as connection approval.

## 19. Result contract

The Stage 2.5B handoff result shall retain at minimum:

- parent Stage 2.5A input/result fingerprints;
- handoff contract/version identities;
- handoff coverage;
- parent action-transfer warnings;
- per-bolt actual in-plane vectors and magnitudes;
- per-bolt/per-layer material angles;
- selected bearing property family;
- check-specific handoff disposition;
- check-specific demand source;
- calculated supported resistance results;
- unsupported/incomplete required-check IDs;
- block-shear force-line compatibility identity;
- qualification;
- warnings;
- numerical comparison;
- governing/co-governing supported checks;
- overall fail-closed disposition;
- deterministic handoff result fingerprint.

The result must distinguish:

- demand calculation;
- compatibility classification;
- resistance calculation.

## 20. Version identities

Proposed Stage 2.5B identities:

`calculation_contract_version = 2.5B-RC1`

`resistance_handoff_engine_version = 0.1.0.dev1`

`resistance_handoff_rule_set_version = asce74-23-ch8-eccentric-demand-resistance-handoff-rc1.dev1`

`resistance_handoff_result_schema_version = 0.1.0-draft`

`resistance_handoff_fingerprint_schema_version = 0.1.0-draft`

These do not replace Stage 2.5A demand identities or Stage 2.4B resistance identities.

## 21. Fingerprinting

The Stage 2.5B fingerprint includes:

- exact parent Stage 2.5A result fingerprint;
- exact parent Stage 2.4B planning/execution identities used;
- per-bolt/per-layer direction selections;
- handoff coverage;
- unsupported-check classifications;
- block-shear force-line compatibility identity;
- explicit bolt-axis demand provenance where used;
- Stage 2.5B versions.

Exclude presentation state, display units, camera, UI selection, timestamps, and random IDs.

## 22. Units and numerical policy

Use the accepted Decimal and unit architecture.

No authoritative binary float.

No intermediate engineering rounding.

Use exact physical values for direction classification and resistance comparison.

Golden serialization uses 12 decimal places with `ROUND_HALF_EVEN`.

## 23. Required warnings

At minimum:

- `RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED`
- `ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1`
- `ECCENTRIC_INTERROW_SHEAROUT_HANDOFF_NOT_SUPPORTED_RC1`
- `BLOCK_SHEAR_FORCE_LINE_COMPATIBILITY_NOT_PROVEN`
- `MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL`
- `OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND`
- existing block-shear limited-test-basis and qualification warnings.

## 24. Deliberate exclusions

This RC1 does not define:

- eccentric first-row net-tension demand;
- eccentric inter-row shear-out demand;
- a new row-distribution method;
- member-end moment transfer;
- bolt-axis tension distribution;
- prying;
- friction/slip transfer;
- nonlinear instantaneous-center resistance coupling;
- heterogeneous bolt stiffness;
- new resistance equations;
- frontend/API/application integration.

## 25. Benchmark authority

The companion handoff golden is the machine-readable benchmark authority after approval.

Production shall derive all values.

Tests may use the golden as an oracle.

The parent Slice 2 and Slice 3 goldens remain immutable and independently authoritative for their own calculation families.

## 26. Implementation sequence after approval

After this specification, companion golden, and independent verification ledger are approved:

- Stage 2.5B may implement the framework-independent compatibility/handoff engine;
- existing Stage 2.5A and Stage 2.4B outputs must remain regression-stable;
- no frontend/API/application integration is authorized in Stage 2.5B;
- a later integration stage may connect the accepted handoff engine to the unified workspace.
