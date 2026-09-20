# FRP Master Connection — Stage 3.3A Single FRP Clip-Angle Connector — Authority Ledger RC1

## 1. New authority

Stage 3.3A authorizes:

1. one physical `SINGLE_CLIP_ANGLE` connector component;
2. one connected-member leg and one support leg;
3. two perpendicular, independently resolved bolted interfaces;
4. exact unequal-leg geometry, thickness, length, hand, length anchoring, and body position;
5. connected Brace/Beam roles using the existing profile library;
6. W Column Flange and W Beam Flange support roles;
7. independent bolt-group geometry on the two legs;
8. shared Stage 2.5/2.6 demand and supported resistance integration;
9. shared member-end trim using a clip-angle support-leg/heel clearance plane;
10. deterministic Clip-Angle API/application/visualization contracts;
11. complete backend-authoritative 3D presentation.

## 2. Topology authority

The controlled load path is:

```text
Connected Member
→ Connected Member ↔ Clip-Angle Connected Leg
→ Single Clip-Angle Body
→ Clip-Angle Support Leg ↔ Support
→ W Support
```

The two interfaces are physical and independent.

No one-to-one bolt matching is required.

## 3. Geometry authority

Stage 3.3A controls:

- connector frame `S_C / P_C / L_C`;
- positive/negative clip-angle hand;
- connected/support leg widths;
- thickness;
- connector length;
- length anchor and body position;
- flat broad-face regions;
- heel/junction exclusions;
- finite connector ends;
- independent bolt axes and layer stacks.

The existing sharp-corner Angle profile geometry is reused.

Manufacturing radii are not introduced.

## 4. Shared-platform authority

Stage 3.3A shall reuse:

- Stage 3.2 workspace shell;
- profile/surface registry;
- fixed-grid and group-offset placement;
- advanced edge-distance representation;
- computed clearances;
- fastener presentation;
- trim kernel;
- connector length anchoring;
- region-specific material bases;
- embedded material-axis renderer;
- preview/design state machine;
- exact units/fingerprints.

Duplicated Tee-specific implementations are prohibited.

## 5. Frozen Stage 3.2 boundary

The immutable Stage 3.2 freeze remains historical authority.

Shared refactors may occur only with:

- an explicit Stage 3.2 freeze-change governance record;
- exact Tee regression evidence;
- zero Tee engineering behavior/fingerprint change;
- unchanged freeze tag and manifest.

Stage 3.3A does not supersede any frozen Tee engineering contract.

## 6. Material authority

The initial connector body is:

```text
PULTRUDED_FRP
DIRECTIONAL_FRP
```

Material properties require explicit Stage 3.1 source/provenance authority.

The initial fastener system is source-backed 316SS ASTM F593.

No material label supplies strength.

No 316SS/carbon-steel clip-angle body is authorized by Stage 3.3A.

## 7. Action and calculation authority

Stage 3.3A reuses, without equation changes:

- Stage 2.5A eccentric bolt-group demand;
- Stage 2.5B resistance handoff;
- Stage 2.6A compatible group modes;
- Stage 2.6B application integration;
- existing Stage 2.4B supported resistance.

The same canonical global action/reference is transformed independently into both interface frames.

The application shall not invent load sharing, line aggregation, prying, or bolt-axis tension.

## 8. Connector-body limitation

Required check:

```text
SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE
```

Status:

```text
NOT_EVALUATED
```

This includes leg bending, heel/fillet action, connector shear/rupture/torsion, prying, and single-angle eccentric body behavior.

Ordinary whole-connection PASS is prohibited.

A supported interface numerical failure retains FAIL precedence.

## 9. Trim authority

The existing trim kernel may use the connector-specific:

```text
CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE
```

The user-entered clearance is perpendicular plane-to-plane geometry.

Trimmed-edge resistance mapping remains fail-closed unless an existing accepted method unambiguously consumes the same physical edge.

No new resistance equation is authorized.

## 10. Fingerprint authority

Stage 3.3A creates new deterministic identities for the new connector family.

Clip-angle fingerprints include:

- physical connector geometry/hand/position;
- both interface geometries;
- material/fastener provenance;
- action/reference;
- trim state;
- parent engine versions.

They exclude presentation state.

Existing Direct/Tee controlled fingerprints remain exact.

Equivalent U.S./SI inputs have identical engineering fingerprints.

## 11. Explicitly not authorized

Stage 3.3A does not authorize:

- double/paired clip angles;
- assumed equal load sharing;
- support-web connections;
- concrete anchors;
- round-hollow flat-leg contact;
- connector-body strength;
- prying;
- bolt-axis tension generation;
- blind fasteners;
- slip-critical friction;
- welded behavior;
- moment connections;
- new material properties/equations.

## 12. Acceptance rule

Stage 3.3A is accepted only when:

- all controlled golden cases pass;
- frozen Stage 3.2 behavior remains exact;
- full local and object-isolated QA passes;
- hosted Backend/Frontend Ubuntu/Windows CI passes;
- required visual acceptance passes;
- connector-body limitation remains explicit.

**END OF AUTHORITY LEDGER RC1**
