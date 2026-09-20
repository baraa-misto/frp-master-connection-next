# FRP Master Connection — Stage 3.3B Symmetric Paired FRP Clip-Angle — Authority Ledger RC1

## 1. New authority

Stage 3.3B authorizes:

1. one exact symmetric pair of pultruded-FRP clip angles;
2. one positive-side and one negative-side mirrored angle;
3. one common three-layer connected-member through-bolt group;
4. one positive support-leg bolt group and one negative mirrored support-leg bolt group;
5. exact pair symmetry geometry and action eligibility;
6. exact one-half branch-action allocation when symmetry is proven;
7. exact layer-specific demand allocation for the common stack;
8. Flat Plate, W/I Web, and qualified Channel Web connected regions;
9. W Column Flange and W Beam Flange supports;
10. shared full-profile trimming, preview/design state, material axes, visualization, and U.S./SI behavior.

## 2. Source authority

The engineering interpretation is based on ASCE/SEI 74-23 with Erratum 1:

- Section 8.1: simple frame connections may use a single clip angle or a pair;
- Section 8.3.4: simple framing connections are proportioned for reaction shear unless otherwise qualified;
- Commentary C8.3.4.1: when two clip-angle web shear planes are present, transmitted simple-frame shear is assumed equally distributed between them.

Erratum 1 contains no applicable Chapter 8 correction.

Equal sharing is therefore controlled only for the exact symmetric pair and action conditions in the Stage 3.3B specification.

## 3. Pair-symmetry boundary

The RC1 pair is locked symmetric:

- identical angle geometry;
- identical materials/sources;
- mirrored placement;
- one common symmetric member bolt group;
- identical mirrored support groups;
- identical fastener systems;
- parallel opposing connected-member faces;
- symmetric support geometry.

Unequal left/right inputs are not authorized.

## 4. Action-symmetry boundary

Stage 3.3B RC1 equal sharing is limited to pure reaction shear parallel to `L_P`.

At the pair datum, equal sharing requires:

```text
F_S = 0
F_P = 0
M_S = 0
M_P = 0
M_L = 0
reference_S = 0
```

Only `F_L` may be nonzero.

If symmetry is not proven, geometry may remain valid/current, but branch actions and design distribution remain `NOT_EVALUATED`.

No arbitrary 50/50 assumption is authorized.

## 5. Common-stack demand authority

The common through-bolt group is resolved once using the total pair action.

For each common-bolt total in-plane demand vector `d_total`, the controlled layer allocation is:

```text
positive angle connected leg = 0.5 d_total
connected member             = 1.0 d_total
negative angle connected leg = 0.5 d_total
```

This is an application/handoff allocation, not a new resistance equation.

The bolt-shank total force remains `d_total`.

## 6. Support-group demand authority

The positive and negative support groups each receive one exact half branch action after pair symmetry is proven.

Each branch uses the existing Stage 2.5A demand engine and Stage 2.5B/2.6A supported handoff path.

No direct resistance-engine bypass or application-side recalculation is authorized.

## 7. Shared platform authority

Stage 3.3B shall reuse:

- Stage 3.3A profile binding;
- exterior face-to-face placement;
- preview/design limitation separation;
- complete profile trimming and mesh binding;
- Stage 3.2 workspace, exact units, material bases, embedded material axes, hardware, and inspectors;
- existing Stage 2 demand/resistance engines.

A shared cause shall not be corrected independently in each family.

## 8. Material authority

Both clip angles are:

```text
PULTRUDED_FRP
DIRECTIONAL_FRP
```

with identical explicit source/provenance authority.

Initial fasteners are source-backed 316SS ASTM F593.

No material label supplies strength.

No unequal left/right material or fastener system is authorized in RC1.

## 9. Connected-profile authority

Authorized connected regions:

- Flat Plate;
- W/I Web;
- Channel Web only where finite geometry and assembly access are proven.

Angle and RHS connected members are not authorized for the RC1 paired topology.

Unsupported profiles shall not be silently approximated by plates or internal connectors.

## 10. Trim authority

The existing shared trim kernel may use:

```text
PAIRED_CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE
```

The user-entered clearance is exact perpendicular plane-to-plane geometry.

The full current connected profile solids are trimmed and rendered without untrimmed ghost geometry.

Trimmed-edge resistance remains fail-closed where existing authority cannot consume the new physical edge unambiguously.

## 11. Explicit unresolved checks

Required Stage 3.3B checks:

```text
PAIRED_CLIP_ANGLE_BODY_RESISTANCE
COMMON_THROUGH_BOLT_DOUBLE_SHEAR_RESISTANCE
PAIRED_CLIP_ANGLE_BRANCH_COMPATIBILITY
PAIRED_FRP_CLIP_ANGLE_QUALIFICATION
```

RC1 status:

```text
NOT_EVALUATED
```

The paired FRP clip-angle system remains qualification/review required.

Stage 3.3B does not authorize:

- clip-angle body/heel strength equations;
- metallic bolt double-shear capacity;
- pair torsion/warping;
- prying;
- unequal-stiffness load sharing.

## 12. Status authority

- True geometry invalidity remains fail-closed.
- Supported numerical interface failure governs overall `FAIL`.
- Equal-sharing not proven produces `NOT_EVALUATED`, not geometry invalidity.
- Required body/double-shear/compatibility limitations prohibit ordinary PASS.

## 13. Fingerprint authority

Stage 3.3B creates deterministic identities for:

- pair geometry;
- symmetry proof;
- branch actions;
- common group;
- mirrored support groups;
- layer-demand allocation;
- trim;
- result/application integration.

Equivalent U.S./SI inputs match.

Presentation state is excluded.

Direct, frozen Tee, and Stage 3.3A controlled fingerprints remain exact.

## 14. Explicitly not authorized

The paired FRP clip-angle system remains qualification/review required.

Stage 3.3B does not authorize:

- asymmetric paired angles;
- independent left/right support groups;
- separate one-sided member groups;
- support-web connections;
- Angle/RHS paired connected profiles;
- blind fasteners;
- moment connections;
- new material properties;
- new resistance equations;
- modification or movement of existing freeze tags.

## 15. Acceptance rule

Stage 3.3B is accepted only when:

- exact symmetric geometry/action eligibility is proven;
- common three-layer stack and hardware are physical;
- layer-demand allocation is exact and traceable;
- antisymmetric actions fail closed without invalidating valid geometry;
- all prior Stage 3.3A corrections remain effective;
- Direct and frozen Tee regressions remain exact;
- all controlled goldens, local/isolated QA, hosted CI, and visual acceptance pass.

**END OF AUTHORITY LEDGER RC1**
