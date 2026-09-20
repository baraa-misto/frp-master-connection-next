# FRP Master Connection — Stage 3.5A-R2 Material-Axis Correction and Three-Component Force Expansion — Authority Ledger RC1

## Successor authority

Stage 3.5A-R2 authorizes two controlled successor changes:

1. correction of Stage 3.5A material-axis presentation while preserving accepted R14B material bases unless a pre-mutation audit proves otherwise;
2. three signed force inputs in the concrete-wall local frame:
   - Major shear along `V_W`;
   - Minor shear along `H_W`;
   - Axial force along `N_W`.

User-applied moment remains prohibited.

## Historical compatibility

Historical contracts remain accepted:

- `3.5A-RC1`;
- `3.5A-R1-RC1`.

New successor contract:

`3.5A-R2-RC1`.

Historical geometry/results/fingerprints remain exact.

## Exact wall-wrench authority

For complete user force:

`F = (V_minor, V_major, P_axial)`

and zero user free moment:

`M_wall = (r_member - r_wall) × F`.

This is exact wrench translation, not a new connection-design equation.

All geometry-induced moments remain in the external handoff.

## Pair-sharing applicability extension

The existing paired half-share equation remains unchanged.

Stage 3.5A-R2 authorizes equal branch sharing only when:

- all existing geometric/material symmetry conditions pass;
- `V_minor = 0`.

Then:

`F_+ = F_- = 0.5 (0,V_major,P_axial)`.

This extends the accepted symmetry proof to force components lying in the mirror plane.

When `V_minor != 0`, complete paired branch allocation is not authorized.

Required:

`MINOR_SHEAR_PAIRED_BRANCH_ALLOCATION = NOT_EVALUATED`.

The combined wall wrench and full anchor layout remain authoritative for external design.

## Common member-group authority

Major shear and axial force lie in the common connected-member/clip-leg plane and may enter existing accepted in-plane demand methods where applicable.

Minor shear acts along the common through-bolt axes.

Required for nonzero Minor shear:

`COMMON_MEMBER_GROUP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

No bolt tension/prying method is introduced.

## Axial wall-side boundary

For nonzero axial force:

- `CLIP_ANGLE_WALL_LEG_AXIAL_TRANSFER_AND_PRYING = NOT_EVALUATED`;
- `WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

No wall-leg bending/prying or contact/anchor partition method is introduced.

## Nonmajor-force qualification boundary

The original Stage 3.5A source basis remains the pure reaction-shear/simple-connection case.

When Minor shear or Axial force is nonzero:

`NONMAJOR_FORCE_CONNECTION_QUALIFICATION = NOT_EVALUATED`.

Exact force transfer and supported local checks may still execute; whole-connection qualification is not claimed.

## External handoff authority

When Minor shear is zero and symmetry proof passes:

- branch-resolved handoff is permitted.

When Minor shear is nonzero:

- use combined-layout handoff;
- preserve all anchor coordinates/group owners;
- preserve full combined wall wrench;
- branch allocation remains `NOT_EVALUATED`.

Specialized anchor software remains authoritative.

## Material-basis authority

Accepted R14B region-specific bases remain controlling.

For every FRP physical region:

- LW, CW, TT are unit;
- pairwise orthogonal;
- LW/CW lie in the physical region plane;
- TT is the through-thickness normal with controlled sign.

Stage 3.5A-R2 does not authorize a material-property or material-basis change.

If the pre-mutation audit finds a backend R14B violation, implementation shall stop for separate engineering-basis authority.

Otherwise only visualization/transform/binding corrections are authorized.

## Material-axis coverage

Required for:

- all connected profile regions;
- both clip-angle connected legs;
- both clip-angle wall legs.

Concrete has no FRP material axes.

RHS cavity has no material axes.

## No new calculation equation

Stage 3.5A-R2 introduces no new:

- demand equation;
- resistance equation;
- anchor/concrete capacity;
- prying/tension method;
- moment-connection method.

## Frozen-family boundary

No Direct, Tee, Clip-Angle, or Multi-Member Tee frozen fingerprint may change.

All freeze tags remain immutable.

**END OF AUTHORITY LEDGER RC1**
