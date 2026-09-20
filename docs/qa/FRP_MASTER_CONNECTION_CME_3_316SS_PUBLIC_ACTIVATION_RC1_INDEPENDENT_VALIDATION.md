# FRP Master Connection
# CME-3 316SS Public Connector-Body Activation RC1 Independent Validation

**Status:** PASS — independent validation of the approved CME-3 activation contract.  
**Frozen baseline:** `2e33c562fe131cef4526390c151be024a8a734a8`, count 132.  
**Frozen C2-core implementation:** `1d730c70bc446901452f2eacecd9df3f9f36ff4b`, tag `cme-2-core-r-a-t-freeze`.

## Independence and scope

This validation checks the public-activation policy, route/body matrix, dispatch boundaries, status aggregation rules, and regression obligations. It does not recompute frozen C2 engineering resistance equations; those equations are already independently accepted and frozen.

No production provider was imported or used to generate the expected activation matrix.

## Recomputed inventory

- Native routes: **16**.
- Body-bearing routes with conditional connector-material selection: **13**.
- No-body routes remaining without a connector-material selector: **3**.
- Canonical connector bodies: **39**.
- Form totals: **21 ANGLE / 16 PLATE / 2 TEE**.
- Plate routes: **3**.
- Angle routes: **8**.
- Tee routes: **2**.

The route/body totals independently reconcile to the frozen CME-1/CME-2 inventory.

## Public material contract

- Default and missing selection: `FRP`.
- Public stainless canonical value: `SS316`.
- Client display label: `316 Stainless Steel`.
- Approved aliases normalize to the same conservative C2 material identity.
- RC1 uses one connection-wide connector-body material selection.
- Mixed FRP/SS316 connector bodies in the same connection are not supported.
- Structural members remain FRP-only.
- Custom client stainless properties/source hashes are not public trust authority.

## Activation and result contract

Material planning and design execution remain separate.

For SS316 on a body-bearing route, planning exposes conditional provider availability but does not calculate capacity or utilization.

Design dispatch shall:

- preserve existing native geometry and non-body authority;
- exclude/supersede FRP connector-body resistance for SS316 targets;
- require the applicable frozen C2 response/body providers;
- retain every fail-closed C2 applicability status;
- prohibit FRP body fallback.

Whole-connection summary is deterministic:

1. any required evaluated numerical failure => `FAIL`;
2. otherwise any required unavailable/source/applicability/response blocker => `ENGINEERING_REVIEW_REQUIRED`;
3. only complete required coverage with all checks passing => `PASS`.

A known numerical failure is therefore never hidden by an unrelated missing qualification.

## Frozen-provider boundary

CME-3 is a public activation wrapper. It must not modify frozen C2-M/P1/P2/R/A/T provider results or their internal `family_activation` fields.

The wrapper supplies the new public activation authority and aggregation layer.

## Historical Tee

Material selection cannot repair geometry. The default historical Tee remains:

- HTTP 422;
- `CANONICAL_TEE_MAPPING_INVALID`;
- cause `OUTSIDE_SELECTED_LEG_SURFACE`.

## Validation result

Independent checks executed: **18**  
Passed: **18**  
Failed: **0**

Positive activation cases: **20**.  
Negative/fail-closed activation cases: **18**.  
Invariants: **18**.

**Result: PASS.**

The implementation/acceptance stage must additionally prove exact FRP response regression against `2e33c562fe131cef4526390c151be024a8a734a8` and exercise all 16 routes, all 39 body identities, both materials where applicable, browser selector behavior, design staleness, fail-closed C2 gates, and exact hosted CI.
