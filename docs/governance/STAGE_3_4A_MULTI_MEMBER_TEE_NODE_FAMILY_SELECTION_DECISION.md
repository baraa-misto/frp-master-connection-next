# FRP Master Connection — Stage 3.4A Multi-Member Tee Node Family Selection Decision

## Decision

The next controlled product stage is:

**Stage 3.4A — Multi-Member Tee Node Vertical Slice**

The connection is a successor/expansion of the frozen Stage 3.2 Tee family, but it is implemented as a separate connection type so every historical single-member Tee request remains unchanged.

Normal product name:

**Brace/beam node — Multi-member Tee connector**

## Confirmed physical topology

Up to three connected members attach to the **same exposed face of the same Tee stem**:

1. optional Upper Brace;
2. optional Middle Beam;
3. optional Lower Brace.

Each active member has its own independent physical bolt group.

The Tee flange has one separate support-side bolt group.

At least one connected-member slot shall be active.

Any one-slot, two-slot, or three-slot combination is permitted.

## Initial Stage 3.4A profile scope

- Upper Brace: FRP Angle only.
- Middle Beam: FRP Wide-Flange / I only.
- Lower Brace: FRP Angle only.
- Supporting Member: W Column Flange only.

A later controlled stage may expand connected profiles and support targets.

## Slot orientation constraints

- Upper Brace inclination: `0° <= θ_U <= +90°`.
- Middle Beam inclination: fixed at `0°` and frames horizontally into the Tee stem.
- Lower Brace inclination: `-90° <= θ_L <= 0°`.
- Profile roll remains independently available where supported by the shared profile architecture.

The semantic slot names remain physically meaningful; the system shall reject invalid sign/domain assignments rather than silently relabeling slots.

## Action contract

Every active slot owns one complete canonical global member-end wrench:

- Force X / Y / Z;
- Moment X / Y / Z;
- Reference Point X / Y / Z.

Actions are defined as actions applied by the connected member to the connection.

Disabled slots contribute exactly zero and create no hidden geometry, action, result, or fingerprint identity.

## Joint equilibrium

The same physical member actions are shifted and summed at the support-group reference point.

For active slots `i` and support reference point `r_S`:

`F_S = Σ F_i`

`M_S = Σ [ M_i + (r_i - r_S) × F_i ]`

The support-side bolt group receives this exact assembled transfer wrench.

The physical support reaction on the complete joint is equal and opposite; Stage 3.4A connection-demand reporting uses the transferred connection wrench above.

No scalar force-only summation and no hidden load redistribution are permitted.

## Engineering boundary

Stage 3.4A reuses existing Stage 2 demand/resistance methods only where their accepted applicability contracts hold.

Required unsupported checks include:

- `TEE_CONNECTOR_BODY_RESISTANCE`;
- `MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY`.

These remain `NOT_EVALUATED`.

Supported numerical failures retain overall `FAIL` precedence.

Ordinary whole-connection `PASS` is prohibited while required Tee-body/intergroup checks remain unsupported.

## Frozen-family boundary

The existing frozen single-member Tee connection remains separately available and unchanged.

The Stage 3.2 freeze tag and manifest remain immutable historical evidence.

Stage 3.4A introduces new contracts and fingerprints under a separate connection type.

## Superseded draft

The unapproved Stage 3.4A Gusset-Plate draft package is withdrawn and shall not be executed or registered as controlling project authority.

**END OF STAGE 3.4A MULTI-MEMBER TEE NODE FAMILY SELECTION DECISION**
