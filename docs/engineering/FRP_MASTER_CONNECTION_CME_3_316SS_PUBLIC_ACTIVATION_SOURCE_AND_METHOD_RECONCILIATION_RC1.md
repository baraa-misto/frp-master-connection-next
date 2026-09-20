# FRP Master Connection
# CME-3 316SS Public Connector-Body Activation Source and Method Reconciliation — RC1

**Status:** Approved RC1 authority for conditional public connector-body activation.  
**This document does not change any frozen C2 resistance equation or response method.**

## 1. Frozen baseline

- Governance baseline: `2e33c562fe131cef4526390c151be024a8a734a8`.
- Commit count: `132`.
- Frozen C2-core implementation: `1d730c70bc446901452f2eacecd9df3f9f36ff4b`.
- Freeze tag: `cme-2-core-r-a-t-freeze`.
- Freeze tag object: `4729e0996ef7ff07144d88050c667691221017ef`.
- C2-core combined completion report SHA-256: `C8995E52513858C284E2478B9FBA3BE0C2480E4DC673500F70A4A64EDDC93393`.
- C2-core final verification SHA-256: `AFEFD87BE830AA42AC2BAAD4EBA6C99F51FFD0CC939711E3297EDAD9C235E852`.
- C2-R/A/T readiness audit SHA-256: `B664C1FCE58C53575952A44EE2A11C474801821DF7A8C49C45890225DE42925C`.
- Final ANSI/AISC 370-25 SHA-256: `A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`.
- ASCE/SEI 74-23 SHA-256: `A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`.
- Erratum 1 SHA-256: `5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`.

All frozen C2-M, C2-P1, C2-P2, C2-R, C2-A, C2-T, FRP, hardware, foundation, route, geometry, and historical Tee behavior remains controlling.

## 2. Owner/EOR approval

Owner/EOR approved on 2026-09-13:

> Approved: proceed with CME-3 conditional public 316SS connector-body activation on the 13 body-bearing routes, preserving FRP-only primary members, independent hardware authority, all frozen C2 applicability gates, fail-closed unsupported configurations, the three no-body routes unchanged, and historical Tee behavior.

This closes the public-activation scope decision for CME-3 RC1.

## 3. What CME-3 changes

CME-3 changes **public dispatch and product integration only**.

It allows users to select the fixed connector-body material option:

`316 Stainless Steel`

on the 13 routes that contain canonical connector bodies.

It does not create new engineering strength equations.

CME-3 adds:

- public connector-body material selection;
- a public activation/dispatch layer;
- route/body mapping into the already-frozen C2 providers;
- public result aggregation;
- frontend selection/display;
- product capability/readiness metadata;
- fail-closed propagation of every frozen C2 applicability boundary.

## 4. What CME-3 does not change

CME-3 shall not alter:

- primary-member material policy;
- FRP member resistance;
- bolt/nut/washer material or capacity;
- thread/grip/washer authority;
- anchor/concrete/foundation authority;
- frozen C2 provider equations;
- C2 provider fingerprints;
- C2 provider internal `family_activation` fields;
- route geometry;
- existing default FRP behavior;
- historical Tee invalid-default geometry.

The public activation layer wraps frozen providers; it does not rewrite them.

## 5. Route scope

Exactly 16 native routes remain.

Exactly three routes have no connector body and remain unchanged:

- `single-bolt`;
- `multi-row`;
- `direct-side-lap-concrete`.

Exactly 13 routes expose connector-body material selection:

### Plate routes

- `beam-web-splice`;
- `wi-major-axis-moment-splice`;
- `channel-major-axis-moment-splice`.

### Angle routes

- `clip-angle`;
- `paired-clip-angle`;
- `beam-concrete-paired-angle`;
- `column-base-web-angles`;
- `wi-beam-concrete-wall-moment`;
- `wi-beam-frp-support-moment`;
- `angle-column-two-leg-moment-base`;
- `wi-rhs-srs-column-moment-base`.

### Tee routes

- `tee-connector`;
- `multi-member-tee`.

The canonical inventory remains exactly 39 route-qualified bodies:

- 21 ANGLE;
- 16 PLATE;
- 2 TEE.

## 6. Public material selection contract

CME-3 RC1 uses one **connection-wide connector-body material selection**.

Public choices:

- `FRP`;
- `316 Stainless Steel`.

Backend canonical values:

- `FRP`;
- `SS316`.

Approved 316-family aliases remain accepted by API normalization where the existing material contract permits them, but the frontend displays only `316 Stainless Steel`.

Missing material selection normalizes to `FRP`.

Explicit `FRP` selection shall preserve the historical FRP request/result/fingerprint path.

Mixed FRP/SS316 connector bodies in the same connection are not supported in CME-3 RC1 because no mixed-body response authority was approved.

## 7. Material planning vs design execution

Material planning remains separate from design.

A material plan for SS316 on an eligible route may state:

`STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE`

but shall not execute resistance equations.

Therefore planning returns no new design capacity/utilization.

Actual body checks are executed only by explicit design/evaluate action.

## 8. Public dispatch architecture

CME-3 shall introduce an activation layer that:

1. starts from canonical route geometry and body identities;
2. obtains/validates the appropriate frozen response authority;
3. constructs trusted server-owned C2 snapshots;
4. dispatches to the applicable frozen body provider;
5. excludes/supersedes the native FRP **connector-body** resistance for an SS316 target;
6. retains unchanged FRP-member, fastener, support, anchor, concrete, and foundation authority;
7. aggregates the complete public result without double counting.

No SS316 request may silently fall back to FRP connector-body resistance.

### Plate stack

Required authority is:

- C2-M material;
- C2-R response;
- C2-P1 local plate checks as applicable;
- C2-P2 clear-body checks as applicable.

Unsupported simultaneous normal/shear or other frozen P1/P2 boundary remains fail closed.

### Angle stack

Required authority is:

- C2-R response;
- C2-A full shape;
- C2-P1/P2 local-region snapshots only where independently applicable.

Unsupported torsion, slenderness, unequal-leg compression, heel/prying, response, or stability remains fail closed.

### Tee stack

Required authority is:

- C2-R response;
- C2-T full shape;
- C2-P1/P2 local-region snapshots only where independently applicable.

Unsupported Tee junction/flange mechanism, torsion, stability, response, or section authority remains fail closed.

## 9. Trusted authority boundary

A public request may choose only approved public material options.

It may not manufacture trusted engineering authority through:

- source hashes;
- product certifications;
- response qualification flags;
- E4/F10 stability records;
- P1/P2 local-region snapshots;
- C2-R trusted external response records.

Those records remain server-owned/internal and must arise from approved canonical adapters or existing trusted authority.

## 10. Section/product qualification in public activation

CME-3 does not create a public custom stainless section-property editor.

For plate bodies, the activation layer may construct the existing frozen C2-M/P1/P2 trusted snapshots only from canonical geometry and the frozen A240/A480 conservative policy.

For Angle/Tee bodies, activation may construct a C2-A/T trusted section/product snapshot only where the server can establish every required property and approved A276/A484 route identity from controlled canonical data.

If the server cannot establish the required section/product/stability information, the material selection remains valid but design fails closed with the frozen C2 status, such as:

`STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED`.

Conditional public activation therefore does not promise that every selectable configuration produces a numerical stainless body capacity.

## 11. Response qualification

C2-R remains authoritative.

CME-3 may build only the C2-R response mode whose applicability is established by the existing route state:

- material-neutral transport;
- approved ASCE FRP-steel two/three-row distribution;
- narrowly applicable native equal-bolt-stiffness eccentric response;
- locked native symmetry;
- qualified internal/external material-specific response already trusted by the backend.

No public activation adapter may infer missing material-dependent sharing, contact, prying, slip, or active-set response.

## 12. Result aggregation

CME-3 public results retain independent state for:

- geometry;
- connector material;
- connector-body provider;
- response authority;
- connector-body numerical checks;
- FRP member checks;
- hardware/fastener checks;
- support/foundation/anchor/concrete checks;
- qualification/source/applicability blockers.

A known supported numerical failure must remain visible.

Public whole-connection summary:

### FAIL

Use `FAIL` when at least one required supported numerical check has evaluated and failed.

Qualification blockers may coexist and shall remain visible.

### ENGINEERING_REVIEW_REQUIRED

Use `ENGINEERING_REVIEW_REQUIRED` when no required supported numerical check has failed, but at least one required source/applicability/response/check remains unavailable or unqualified.

### PASS

Use ordinary whole-connection `PASS` only when:

- every required applicable check is evaluated;
- every required numerical check passes;
- no required source, response, geometry, product, stability, local-mechanism, hardware, member, support, or foundation blocker remains.

An isolated C2 body PASS never overrides another required failure/blocker.

## 13. Frozen core activation semantics

Frozen C2 providers were deliberately implemented with no public family activation.

CME-3 shall not mutate those provider results.

The activation wrapper records separate public authority:

`CME_3_316SS_PUBLIC_CONNECTOR_BODY_ACTIVATION_RC1`.

The underlying C2 provider may still report its historical isolated-family-activation field as false; this is expected.

## 14. FRP backward compatibility

Missing connector-body material selection shall behave exactly as pre-CME-3 FRP.

Explicit FRP selection shall normalize to the same historical behavior.

CME-3 may intentionally change:

- capabilities/readiness metadata;
- material-planning SS316 provider status;
- frontend selector visibility;
- 316SS design responses.

It shall not change the existing FRP numerical result, warnings, statuses, traces, fingerprints, geometry, arrays, or historical invalid conditions.

## 15. Design-state behavior

Changing connector-body material is engineering-affecting.

After changing FRP <-> SS316:

- preview may refresh;
- existing design result becomes stale;
- design does not automatically rerun;
- explicit Run Design Check/evaluate remains required.

Presentation-only interactions remain non-staling.

## 16. Frontend behavior

On the 13 eligible body-bearing routes:

- expose a connector-body material control;
- choices exactly `FRP` and `316 Stainless Steel`;
- default `FRP`;
- changing material follows normal design-staleness rules;
- display selected connector-body material in result/source trace;
- show fail-closed engineering limitations without hiding them.

On the three no-body routes:

- do not render a connector-body material control.

No custom Fy/Fu/source/certification editor is activated in CME-3 RC1.

## 17. Historical Tee

The Tee workspace may expose the connector material control because Tee is a body-bearing route.

Material selection must not repair invalid canonical geometry.

The historical default remains:

- HTTP 422;
- `CANONICAL_TEE_MAPPING_INVALID`;
- cause `OUTSIDE_SELECTED_LEG_SURFACE`.

A separately valid Tee fixture may proceed to normal material dispatch.

## 18. Public capability/readiness contract

Capabilities shall state, semantically:

- primary members: FRP only;
- connector body materials: FRP and 316 Stainless Steel on eligible routes;
- 316SS activation: conditional;
- hardware authority: independent;
- foundation authority: independent;
- custom stainless properties: not publicly editable;
- no-body routes: no connector-material target.

If an existing capability flag named `stainless_editor_enabled` is specifically the fixed connector-material selector gate, it may transition to true.

If that field means custom property/source editing, preserve it as false and introduce/use a narrower selector capability.

Do not broaden field semantics silently.

## 19. Public API compatibility

Use the narrowest existing request/plan/design contract.

If a new material field is required:

- it must be optional/default FRP;
- absence must preserve historical serialized behavior where possible;
- canonical FRP calculation fingerprint must remain unchanged;
- SS316 must be bound into the new activation fingerprint;
- no public trusted-source objects are accepted.

Existing route URLs should remain unchanged unless the architecture makes that impossible; adding a separate public stainless engineering endpoint is not the preferred activation architecture.

## 20. Deployment boundary

CME-3 completes conditional connector-body activation only.

It does not introduce:

- user-defined stainless material values;
- mixed FRP/SS316 connector bodies in one connection;
- additional fabrication routes;
- new welding authority;
- new fastener strength;
- new foundation/anchor methods;
- proprietary section catalogues;
- new response mechanics beyond frozen C2-R;
- new resistance mechanics beyond frozen C2-P1/P2/A/T.

## 21. Source conclusion

No new resistance-source lock is open.

The final AISC 370-25, ASCE/SEI 74-23/Erratum, frozen C2 engineering specifications, frozen core implementation, and owner/EOR activation approval are sufficient for CME-3 RC1 public integration.

CME-3 is primarily a controlled dispatch, aggregation, API, and UI stage.

Unsupported configurations remain fail closed rather than blocking material selection globally.
