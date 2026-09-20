# FRP Master Connection
# CME-3 Conditional Public 316SS Connector-Body Activation Engineering / Product Specification — RC1

**Activation authority:** `CME_3_316SS_PUBLIC_CONNECTOR_BODY_ACTIVATION_RC1`  
**Status:** Approved implementation authority for final conditional public 316SS connector-body activation.

## 1. Frozen baseline

Implementation starts from:

`2e33c562fe131cef4526390c151be024a8a734a8`

commit count `132` with `cme-2-core-r-a-t-freeze` frozen at `1d730c70bc446901452f2eacecd9df3f9f36ff4b`.

CME-3 must preserve all 17 existing freeze tags.

## 2. Route activation matrix

### No connector-body material target

These routes remain exactly unchanged:

- `single-bolt`;
- `multi-row`;
- `direct-side-lap-concrete`.

They expose no connector-body material selector and produce no connector-body material targets.

### Plate activation routes

- `beam-web-splice`;
- `wi-major-axis-moment-splice`;
- `channel-major-axis-moment-splice`.

### Angle activation routes

- `clip-angle`;
- `paired-clip-angle`;
- `beam-concrete-paired-angle`;
- `column-base-web-angles`;
- `wi-beam-concrete-wall-moment`;
- `wi-beam-frp-support-moment`;
- `angle-column-two-leg-moment-base`;
- `wi-rhs-srs-column-moment-base`.

### Tee activation routes

- `tee-connector`;
- `multi-member-tee`.

Counts remain:

- 16 routes;
- 13 material-selectable body routes;
- 3 no-body routes;
- 39 canonical bodies;
- 21 ANGLE / 16 PLATE / 2 TEE.

## 3. Public material enum

Frontend labels:

- `FRP`;
- `316 Stainless Steel`.

Canonical backend values:

- `FRP`;
- `SS316`.

Accepted SS316 aliases retain the frozen C2-M normalization contract.

Missing selection -> FRP.

CME-3 RC1 uses one connection-wide connector-body material value.

Mixed connector-body materials return:

`STAINLESS_MIXED_CONNECTOR_BODY_MATERIALS_NOT_SUPPORTED_IN_CME3_RC1`.

## 4. Planning contract

The material plan endpoint/workflow remains non-calculating.

### FRP

Existing behavior remains:

`NATIVE_FRP_DELEGATION_AVAILABLE`.

### SS316 eligible target

Return:

`STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE`.

Retain:

- route;
- canonical body identity;
- body form;
- selected material;
- required provider stack;
- public activation authority;
- applicability/status list.

Plan-level capacity and utilization remain null.

### No-body route

Return no connector-body targets.

No selector is shown.

## 5. Design dispatch

### 5.1 General

For SS316:

- build canonical material assembly;
- identify all active canonical connector bodies;
- require all body targets to use SS316;
- establish trusted C2-R response;
- construct server-owned provider snapshots;
- execute applicable C2 body providers;
- preserve all non-body native authorities;
- aggregate once.

Do not use FRP connector-body strength for an SS316 target.

### 5.2 Plate bodies

Use:

- frozen C2-M;
- frozen C2-R;
- frozen C2-P1;
- frozen C2-P2 as applicable.

The adapter shall not modify/import-couple frozen providers in a way prohibited by their freeze contracts.

Where frozen providers require pre-resolved snapshots, construct them through a new CME-3 adapter rather than modifying frozen provider APIs.

### 5.3 Angle bodies

Use:

- frozen C2-R;
- frozen C2-A;
- optional bound P1/P2 local-region snapshots.

The adapter must establish:

- canonical body identity;
- approved A276/A484 product route;
- trusted section/product snapshot;
- required response authority;
- applicable stability records;
- demand/reference/frame.

If any required record cannot be established, return the frozen fail-closed status.

### 5.4 Tee bodies

Use:

- frozen C2-R;
- frozen C2-T;
- optional bound P1/P2 local-region snapshots.

The same trusted-product/response/stability/local-region rules apply.

## 6. Native FRP result separation

Existing family solvers may produce mixed FRP body/member/hardware result trees.

For SS316 activation the adapter shall explicitly identify connector-body checks by canonical body/role.

Those native FRP body resistance checks are **not** authoritative and shall not govern the SS316 public result.

They may be retained only as non-governing historical/debug trace if clearly marked superseded and excluded from aggregation.

FRP member, hardware, support, foundation, anchor, concrete and unrelated native checks remain authoritative and must be counted exactly once.

## 7. Provider trace

Every evaluated SS316 body result shall trace:

- `CME_3_316SS_PUBLIC_CONNECTOR_BODY_ACTIVATION_RC1`;
- route/body identity;
- selected material;
- frozen C2 provider IDs and fingerprints;
- response mode/fingerprint;
- product/source record;
- local-region snapshots if used;
- non-body native authority retained.

No result may collapse those into an opaque scalar.

## 8. Overall connection summary

Maintain detailed numerical and qualification channels.

Summary:

### FAIL

If one or more required evaluated checks fail numerically.

Do not hide FAIL because another required item is unavailable.

### ENGINEERING_REVIEW_REQUIRED

If no required evaluated check fails but at least one required check/source/response/product/stability/local mechanism remains unresolved.

### PASS

Only if every required applicable connection check passes and no required blocker remains.

This summary applies across body, member, fastener and support/foundation domains.

## 9. Geometry precedence

Canonical geometry validation occurs before material-body dispatch.

If geometry is invalid:

- preserve the historical geometry status/HTTP behavior;
- do not attempt to manufacture a stainless body result.

## 10. Public trust boundary

Public clients may submit the material selection only.

They may not submit authoritative:

- provider fingerprints;
- source hashes;
- A276/A484 certification flags;
- custom Fy/Fu/E/G;
- C2-R trusted response records;
- E4 Fe;
- F10 Ly/Lr/Fcr;
- P1/P2 trusted snapshots.

Any such attempted trust injection shall be ignored/rejected according to API style and must not qualify engineering authority.

## 11. Product/source defaults

### Plate

The activation adapter uses the frozen C2-M A240/A480 conservative policy.

### Angle/Tee

The activation adapter uses the frozen C2-A/T public product policy:

- ASTM A276/A276M + A484/A484M;
- hot-rolled or extruded;
- condition A/HF;
- unwelded;
- 316-family;
- Fy25/Fu70/E28000/G10800.

The public UI does not offer alternate fabrication/source routes.

If actual section/property authority cannot be built from controlled canonical server data, design fails closed.

## 12. Capabilities and readiness

CME-3 shall update the public capability/readiness response only as necessary to declare the controlled activation.

Required semantics:

- `primary_members = FRP_ONLY`;
- eligible connector-body materials include FRP and 316 Stainless Steel;
- stainless connector-body activation is `CONDITIONAL`;
- no-body routes have no target;
- hardware/foundation remain independent;
- custom stainless properties remain disabled.

## 13. Frontend

For every eligible workspace:

- show `Connector Body Material`;
- default FRP;
- option `316 Stainless Steel`;
- material control reflects current design state;
- change stales prior design;
- preview may update;
- explicit design action remains required;
- result pane shows body material and source/provider coverage;
- blocker reasons are engineer-facing and not collapsed into generic failure.

For no-body workspaces:

- no connector-body material control.

Do not add custom property/source editing in RC1.

## 14. Visual material representation

A visual distinction for SS316 may be added only as presentation.

It shall not:

- encode engineering state solely by color;
- alter geometry;
- alter fingerprints;
- alter capacity;
- auto-select material.

Text labeling remains authoritative.

## 15. Historical Tee

Tee material control may be present.

Default invalid geometry remains invalid.

Do not automatically change face, leg, orientation, bolt path or dimensions to make SS316 evaluable.

## 16. API/fingerprint compatibility

For historical FRP:

- missing material and explicit FRP must canonicalize to the frozen FRP calculation identity;
- no FRP capacity/result/fingerprint changes are permitted.

For SS316:

- selected material and CME-3 activation authority enter the activation/public-result fingerprint;
- all underlying frozen provider fingerprints are retained.

Changing only display units does not change physical activation fingerprint.

## 17. State staleness

Material selection is design-affecting.

FRP -> SS316 or SS316 -> FRP:

- marks design stale;
- invalidates material/provider trace from prior design;
- updates preview/material labels;
- does not auto-run design.

## 18. Fail-closed examples

Examples include, without limitation:

- unqualified response;
- section properties unavailable;
- E4/F10 stability unavailable;
- slender shape;
- unequal-leg angle compression;
- shape torsion;
- combined normal/shear where unsupported;
- angle heel/prying method unavailable;
- Tee junction/flange local method unavailable;
- plate P2 combined normal/shear unsupported;
- stale/mismatched body snapshot.

These are expected conditional activation outcomes, not reasons to fall back to FRP.

## 19. No-body request defense

If API clients try to attach connector-body material to a no-body route, it shall not create a target.

Use/retain an explicit non-applicability result:

`CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE`

where the endpoint contract returns a status.

Do not manufacture a connector body.

## 20. Mixed-material defense

If any lower-level request attempts multiple connector-body material identities in one connection:

`STAINLESS_MIXED_CONNECTOR_BODY_MATERIALS_NOT_SUPPORTED_IN_CME3_RC1`.

No mixed response is attempted.

## 21. Golden authority

The companion RC1 golden contains:

- 20 positive activation cases;
- 18 negative/fail-closed cases;
- 18 invariants;
- the complete 16-route activation matrix.

Production shall not regenerate expected values from its own output.

## 22. Regression requirements

Acceptance shall compare against frozen baseline `2e33c562fe131cef4526390c151be024a8a734a8`.

At minimum:

### Exact FRP comparisons

- all 32 native preview/design-or-evaluate response cases used by the prior acceptance harness;
- all 16 FRP material plans;
- both historical Tee errors.

Capabilities/readiness and SS316 material plans are intentionally changed and therefore require controlled expected-delta comparisons, not blind equality.

### Inventory

- 16 routes;
- 39 bodies;
- 21/16/2 forms.

### Frozen core

C2-M/P1/P2/R/A/T direct tests and provider fingerprints remain unchanged.

## 23. Browser acceptance

Product-level acceptance shall exercise all current UI products/workspaces.

At minimum:

- all 15 UI products;
- all 16 native routes;
- all 13 eligible material selectors;
- all three no-body workspaces/modes;
- FRP default behavior;
- SS316 selection;
- design staleness;
- representative calculated/blocked SS316 outcomes for plate, angle and Tee;
- historical Tee 422;
- no runtime exceptions, duplicate-key errors or unexpected 5xx.

The automated route/configuration matrix shall cover all principal route/body identities and the existing inventory/mode tests.

## 24. Final scope

A successful CME-3 freeze establishes conditional public 316SS connector-body activation.

It does not certify every selectable configuration as numerically complete.

The product must visibly preserve conditional/fail-closed outcomes where the frozen C2 scope does not cover a configuration.
