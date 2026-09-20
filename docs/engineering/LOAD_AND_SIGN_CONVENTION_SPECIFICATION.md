# Load and Sign Convention Specification

| Control | Value |
|---|---|
| Document ID | FMC-ENG-SPEC-001 |
| Stage | 1.3A — member-on-joint action signs and renderer-neutral directions |
| Document status | Controlled specification; approved Stage 1.3A conventions; not frozen |
| Mathematical implementation | `backend/src/frp_master_connection/actions/transforms.py` |
| Engineering calculation | Not implemented |

## Purpose and scope

This specification controls the ownership, sign interpretation, explicit
reference-point treatment, and future presentation of manually entered member-end
actions. It uses the resolved frame mathematics controlled by
`SPATIAL_FRAME_AND_ACTION_TRANSFORM_SPECIFICATION.md`.

Stage 1.3A implements pure force/moment rotation, explicit common-frame moment shift,
connected-end axial interpretation, and renderer-neutral direction data. It does not
factor loads, calculate reactions or equilibrium, distribute force, determine
connection demand or resistance, or implement an engineering PASS/FAIL result.

## Status interpretation

- **Approved** statements control the Stage 1.3A coordinate and sign meaning and may
  change only through governance.
- The dimensionless mathematical tolerance is **Provisional** and is not an
  action-value or engineering acceptance tolerance.
- **Pending Engineering Decision** items remain unavailable for calculation use.

## Approved action requirements

| Rule ID | Status | Requirement |
|---|---|---|
| LSC-A01 | Approved | A `ManualMemberEndAction` represents actions applied **by the member to the joint assembly**. It is not a supporting reaction and is never silently reversed. |
| LSC-A02 | Approved | Every action belongs to one member and one load combination and preserves its declared connected end. |
| LSC-A03 | Approved | Every action identifies the symbolic coordinate frame in which its components are expressed and the reference point at which they act. |
| LSC-A04 | Approved | The admitted input basis is final factored-strength action. Stage 1.3A never silently applies another load factor. |
| LSC-A05 | Approved | Positive sign-convention mode and applied signed-action mode are distinct synchronized views. |
| LSC-A06 | Approved | Positive mode explains permanent positive axes; applied mode reflects actual signed values. Neither view is an independent engineering-data source. |
| LSC-A07 | Approved | An unsupported force or moment component cannot be dropped, zeroed, reinterpreted, or hidden from an eventual calculation input. |
| LSC-A08 | Approved | Reference-point eccentricity is preserved. An action moves from P to Q only through an explicit common-frame shift operation. |
| LSC-A09 | Approved | Calculation and display directions must derive from the same canonical resolved frame and action-direction functions. |
| LSC-A10 | Approved | A changed signed value must update future arrows before the user accepts or saves the assignment; display state never changes the numerical action. |
| LSC-A11 | Approved | Global X/Y are project-horizontal, global Z is vertical upward, and the global frame is right-handed. |
| LSC-A12 | Approved | Member local x is fixed START to END and never reverses based on which end is connected. |
| LSC-A13 | Approved | A member frame requires an explicit local-z reference and has no silent fallback. |
| LSC-A14 | Approved | Axial tension/compression sense depends on both connected end and signed local `Fx`. |
| LSC-A15 | Approved | Positive moment directions follow the right-hand rule about positive resolved axes. |

## Canonical frame and component directions

The global basis is:

```text
X = (1, 0, 0)
Y = (0, 1, 0)
Z = (0, 0, 1)
```

For a member, local x always runs START to END. The explicit local-z reference controls
clocking, and the final local frame is proper right-handed and orthonormal. For a
standard unrotated W/I datum, local y is flange width and local z is web depth.

`ActionComponent` contains exactly:

```text
FX, FY, FZ, MX, MY, MZ
```

Their permanent positive directions are:

| Component | Direction kind | Positive direction |
|---|---|---|
| `FX` | `LINEAR` | resolved local +x |
| `FY` | `LINEAR` | resolved local +y |
| `FZ` | `LINEAR` | resolved local +z |
| `MX` | `ROTATIONAL` | right-hand rotation about resolved local +x |
| `MY` | `ROTATIONAL` | right-hand rotation about resolved local +y |
| `MZ` | `ROTATIONAL` | right-hand rotation about resolved local +z |

`positive_action_direction` returns this permanent axis in the resolved frame's
parent coordinates. It does not create a reference point or graphic style.

## Stored values and applied directions

`ManualMemberEndAction` retains without inference:

- action, member, connected-end, and load-combination identities;
- `FACTORED_STRENGTH` input basis through its load combination;
- symbolic `CoordinateFrameReference`;
- existing `ReferencePoint`;
- all three signed force components and all three signed moment components; and
- the `MEMBER_ON_JOINT` convention.

`applied_action_direction(component, signed_value, resolved_frame)` returns immutable
`AppliedActionDirection3D`:

- a positive value uses the permanent positive axis and `POSITIVE` sense;
- a negative value reverses that axis and uses `NEGATIVE` sense;
- a zero value uses `ZERO` sense and `is_zero = true`; its canonical positive axis is
  retained for component identity and it is eligible to be hidden; and
- the exact finite signed value remains authoritative.

The returned axis is expressed in the resolved frame's parent coordinates. For a
rotational component, reversing the axis reverses the right-hand rotational sense.
No action-value tolerance changes positive, negative, or zero classification.

The direction record stores no display length, color, pixel/screen coordinate, mesh,
curve tessellation, camera, or display scale. The caller must retain the action's
existing reference point because the direction operation is reference-point agnostic.

## Connected-end axial interpretation

Local x is always START to END. `interpret_member_end_axial_sense` returns exactly
`TENSION`, `COMPRESSION`, or `ZERO` under the member-on-joint convention:

| Connected end | Stored local `Fx` | Axial loading sense |
|---|---:|---|
| `START` | `Fx > 0` | `TENSION` |
| `START` | `Fx < 0` | `COMPRESSION` |
| `END` | `Fx < 0` | `TENSION` |
| `END` | `Fx > 0` | `COMPRESSION` |
| `START` or `END` | `Fx = 0` | `ZERO` |

The stored `Fx` sign is never rewritten. Positive `Fx` cannot be labeled tension at
both ends, and the local frame cannot be reversed to make that label convenient.

## Force and moment rotation

At the same physical point, the resolved proper rotation `R` applies equally to force
and moment:

```text
F_parent = R F_local
M_parent = R M_local
```

`rotate_force` returns `ForceVector3D`, and `rotate_moment` returns
`MomentVector3D`. Rotation applies no translation and adds no eccentricity moment.

## Reference points and explicit shifting

The stored `ReferencePoint` remains the action's traceable point identity.
`PointInFrame3D` is the Stage 1.3A mathematical wrapper used only when an existing
finite position and its symbolic frame have been resolved explicitly. It does not add
assembly placement or resolve a symbolic point by itself.

For `ForceMomentSystem3D` at P shifted explicitly to Q:

```text
F_Q = F_P
M_Q = M_P + (r_P - r_Q) × F
```

Both `PointInFrame3D` values must contain the same `CoordinateFrameReference`.
`shift_force_moment_reference` rejects a mismatch and uses the offset in the shown
order; it never reverses `r_P - r_Q`.

Canonical example:

```text
P = (a, 0, 0)
Q = (0, 0, 0)
F = (0, Fy, 0)
M_P = (0, 0, 0)

M_Q = (0, 0, a Fy)
```

No stored action is shifted automatically. Stage 1.3A does not infer the intended
target point, discover eccentricity, distribute the force to bolts, or calculate
interface demand.

## Mandatory future visual verification

Axis and action visualization is an engineering-verification requirement, not
decoration. Future manual force entry is incomplete until the user can see the
direction information before accepting or saving the assignment.

Positive sign-convention mode must show:

- independent local-axis and global-axis visibility toggles;
- straight +Fx/+Fy/+Fz arrows;
- right-hand +Mx/+My/+Mz arrows;
- local-axis triad and an optional global-axis triad;
- component and frame labels;
- reference-point marker;
- START, END, and connected-end markers where applicable; and
- numerical axis components, norms/dot products or equivalent inspection, determinant,
  right-handedness, and orthonormality.

Applied-action mode must show:

- actual signed force and moment directions for the selected load combination;
- reversed arrows/sense for negative values;
- signed values and units;
- reference point, selected frame, connected end, and derived axial sense;
- selected member only or all members; and
- optional hiding of explicit zero values.

The same renderer-neutral direction data must support 3D and applicable 2D views.
Arrow scaling affects presentation only. No frontend implementation is part of Stage
1.3A.

## Remaining pending decisions and deferrals

These subjects remain pending or outside Stage 1.3A:

| Subject | Current boundary |
|---|---|
| Supporting-reaction sign convention | No reaction is inferred or displayed as an entered member-on-joint action |
| Allowed reference points per connection template | Every action retains an explicit point, but no template set is approved |
| Non-factored combinations | Only the existing factored-strength identity is admitted |
| Internal canonical unit system | Assembly unit identity is preserved; no conversion policy is selected |
| Assembly placement and frame registry | Symbolic identities are not resolved automatically |
| Exact section and connection geometry | Not implemented |
| Force distribution, equilibrium, stress, resistance, capacity, utilization | Not implemented |
| API, persistence, frontend rendering, and reports | Not implemented |

Missing future calculation support must fail closed under the capability/result
contracts adopted later. Stage 1.3A itself emits no `INCOMPLETE INPUT`, calculation
support result, engineering review status, capacity, utilization, PASS, or FAIL.

## Stage 1.3C3 physical point and explicit-shift integration

Manual actions now may be resolved against the exact in-memory joint geometry context.
The stored action, signed values, member, connected end, combination, original frame,
and original point remain authoritative. Rotation to global occurs at the unchanged
resolved point. Axial sense is derived only for the same member's local frame.

Movement to another resolved point remains a separate explicit operation. It requires
the target point and exact output frame and preserves a complete trace of
`(r_P - r_Q) cross F`. The implementation does not choose a permitted template point,
discover eccentricity, shift on save, distribute force, or calculate demand. PEN-ENG-005
therefore remains pending.

## Stage 2.1A resolved-demand contract

The Stage 2.1A calculation input stores a finite force vector at an explicit resolved
physical point and frame. Geometry mapping projects that vector into the physical
layer plane, records the signed loading sense, calculates only direction/property
selection metadata, and retains an explicitly supplied bolt-axis demand separately.
This is input resolution and applicability, not resistance or demand distribution.

The calculation package does not shift a moment, infer prying, infer bolt-axis demand,
or distribute a group/interface/member demand. An unresolved distribution state fails
closed as `DEMAND_DISTRIBUTION_UNSUPPORTED`. Exactly 90 degrees from the layer LW axis
selects transverse properties under the approved interpretation trace; it is not a
near-zero or display-rounding convention.
