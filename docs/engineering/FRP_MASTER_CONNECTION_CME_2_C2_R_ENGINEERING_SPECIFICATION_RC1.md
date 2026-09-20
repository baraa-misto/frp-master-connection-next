# FRP Master Connection
# CME-2 C2-R Trusted Stainless Response Envelope Engineering Specification - RC1

**Provider identity:** `C2_R_TRUSTED_STAINLESS_RESPONSE_ENVELOPE_RC1`

**Status:** Approved isolated implementation authority. No public family activation.

## 1. Purpose

C2-R provides a trusted response/provenance envelope for stainless connector-body calculations.

It validates already-resolved connection response and narrowly accepts existing material-neutral/prescriptive response modes. It does not invent a new general stiffness/contact/prying solver.

## 2. Required trusted identity

Every response envelope binds:

- route ID;
- canonical body IDs;
- physical fastener/shaft IDs;
- material/source/product fingerprints;
- geometry fingerprint;
- exact action/load-combination identity;
- input and output reference points;
- coordinate frames and sign conventions;
- response mode;
- response-source/model version;
- applicability evidence;
- demand vectors/resultants;
- common-shaft/contact/prying records where relevant;
- units/source system;
- family-activation false.

A client string/hash/flag cannot create this trusted record.

## 3. Accepted response modes

### 3.1 MATERIAL_NEUTRAL_TRANSPORT

May preserve/shift/sum an already-qualified wrench using the existing native transport authority.

It may not:

- repartition demand among bodies;
- infer a missing wrench;
- change active contacts;
- generate prying;
- change shaft-plane participation.

### 3.2 ASCE74_FRP_STEEL_PRESCRIBED_ROWS

Available only when the frozen ASCE/SEI 74-23 interface applicability is satisfied.

Prescribed fractions:

- two rows: 0.60 / 0.40;
- three rows: 0.50 / 0.30 / 0.20.

No interpolation/extrapolation.

The frozen row ordering and geometry requirements remain unchanged.

### 3.3 NATIVE_EQUAL_BOLT_STIFFNESS_ECCENTRIC

Consumes a resolved snapshot from the existing native rigid/equal-bolt-stiffness eccentric-demand method.

Required applicability includes:

- the exact accepted native method/version;
- equal in-plane translational bolt stiffness assumption;
- no unqualified slip transition;
- no material-dependent contact/prying allocation;
- no hidden unequal fixture stiffness;
- no response mode outside the native solver's accepted domain.

C2-R does not recompute the native demand.

### 3.4 NATIVE_LOCKED_SYMMETRY

Only where the current route already has an explicit native symmetry predicate.

All participating stainless branches must be identical in:

- product/source;
- Fy/Fu/E;
- section/geometry;
- thickness;
- fastener and hole arrangement;
- fixture/support condition;
- action symmetry.

If any identity differs, symmetry qualification is lost.

### 3.5 QUALIFIED_EXTERNAL_MATERIAL_SPECIFIC_RESPONSE

Permits a trusted EOR/test/analysis response record with:

- model/source identity;
- material and geometry;
- fasteners/fixture;
- applicable load domain;
- active contact state;
- prying treatment;
- demand vectors;
- numerical precision/tolerance authority;
- qualification date/version.

C2-R validates identity and conservation but does not replace the source analysis.

## 4. Fail-closed response cases

Return no authoritative material-dependent response for:

- missing source;
- stale/mismatched source or geometry;
- unsupported response mode;
- unresolved material dependence;
- mismatched frame/reference;
- unsupported row count;
- failed native symmetry;
- common-shaft closure failure;
- duplicate shaft layer;
- contact/prying required but unqualified;
- source-total prying convention conflict.

## 5. Common fastener graph

A physical shaft occurs once.

Each shaft record contains:

- physical shaft ID;
- ordered layers;
- interface/plane IDs;
- per-layer force vectors;
- cumulative cut vectors;
- near/far endpoints if applicable;
- hardware source identity.

Requirements:

- no duplicate layer ID within a shaft;
- vectors share one frame/reference authority;
- cumulative cut after layer `i` equals the signed sum of the first `i` layer forces;
- terminal cut closes to the trusted source reaction convention;
- external support/foundation action is counted once.

C2-R never copies one bolt capacity to each body alias.

## 6. Contact/prying

If the source record says prying is physically relevant:

- total bolt tension must be supplied by qualified response authority;
- if a separate prying component is supplied, it must reconcile with source total;
- `prying_included_in_total=true` prohibits any second multiplier/increment.

Contact records retain:

- physical footprint;
- active state;
- compression-only sign;
- resultant force/moment;
- reference/frame;
- source/model.

C2-R does not solve an unknown contact patch.

## 7. Numerical precision

Reuse native quantity and canonical fingerprint helpers.

Do not introduce C2-R conversion constants.

Transport/conservation uses the existing project Decimal/exact conventions.

## 8. Result contract

Return separate:

- source qualification;
- response-mode qualification;
- equilibrium/conservation result;
- common-fastener result;
- contact/prying result;
- demand provenance;
- numerical applicability;
- family activation state.

A response envelope may be `QUALIFIED_RESPONSE` without implying any body/FRP/fastener/foundation strength PASS.

## 9. Fingerprint

Bind all result-affecting fields including:

- route/body/shaft identities;
- material/product/source fingerprints;
- action/load combination;
- frames/references;
- response mode/source/model;
- all resolved demands;
- row/symmetry/equal-stiffness applicability;
- contact/prying state;
- ordered layers/cuts.

Display units and ambient Decimal context shall not change physical identity.

## 10. Public isolation

No existing public material planner or family dispatcher may import or call C2-R under this stage.

No public response-ingestion API is authorized.

`family_activation = false` for every C2-R result.
