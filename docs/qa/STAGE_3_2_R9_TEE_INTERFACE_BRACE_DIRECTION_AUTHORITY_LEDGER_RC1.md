# FRP Master Connection — Stage 3.2-R9 Tee Interface Independence + Brace Direction + Fastener Presentation — Authority Ledger RC1

## New R9 authority

R9 newly authorizes only:

1. explicit geometry-domain independence of the `Brace ↔ Tee Stem` and `Tee Flange ↔ Support` bolt-group counts/layouts;
2. backend-authoritative in-plane brace inclination for the current Tee brace template, separate from profile roll;
3. deterministic transformation of existing connected-member/interface geometry using the already accepted R5 trigonometric authority;
4. backward-compatible API/result identity for `brace_inclination_degrees` with default `0°`;
5. presentation parity of Tee fasteners with the accepted direct/reference viewer, including existing schematic head/nut ratios and existing washer authority.

## Inherited calculation authority

R9 does not alter:

- Stage 2 row-distribution applicability;
- Stage 2.5A demand equations;
- Stage 2.5B resistance handoff;
- Stage 2.6A eccentric group-mode compatibility;
- Stage 3.1 material/fastener authority;
- Stage 3.2 two-interface action transformation;
- Stage 3.2 normal-action fail-closed behavior;
- Tee-body `NOT_EVALUATED` status;
- R7/R8 profile bolt-path geometry.

## Independent interface rule

No engineering authority requires equal bolt counts between the two Tee interfaces.

Geometry may represent different row/count combinations per interface when finite geometry is valid.

A calculation method that does not support a chosen group configuration must fail closed on that interface; it must not force the other interface to adopt a matching count and must not invent a new distribution method.

## Brace inclination rule

R9 controls a planar signed brace inclination relative to the existing Tee template's `0°` brace direction.

- domain: `-90° <= θ <= +90°`;
- `0°`: exact legacy placement;
- positive: toward canonical template up;
- negative: opposite canonical template up;
- arbitrary decimal values inside the domain are allowed.

The complete connected member and Interface A placement are backend-derived from the inclination.

The user-entered current global/canonical action is not silently rotated with the brace.

## Profile roll distinction

Profile roll remains a separate pre-existing engineering input describing cross-section orientation about the member longitudinal axis.

R9 does not redefine its existing semantics.

## Fastener presentation authority

Accepted presentation-only schematic dimensions remain:

- bolt head across flats = `1.50 d`;
- bolt head height = `0.625 d`;
- nut across flats = `1.50 d`;
- nut thickness = `0.875 d`.

These are not engineering resistance/geometry authority and shall not enter engineering fingerprints.

Washers remain governed by existing authoritative fastener data/presentation behavior.

## Not authorized

R9 does not authorize:

- a new single-row/multi-row force-distribution equation;
- automatic resizing/repositioning of invalid bolt layouts;
- out-of-plane/skew brace direction beyond the current planar inclination;
- member-axis automatic load input mode;
- new fastener strength values;
- exact ASTM/ASME head/nut dimensions;
- Tee-body strength;
- prying;
- new member-body limit states.

## Legacy fingerprint rule

Omitted/default `0°` inclination is semantically identical to the prior Stage 3.2 Tee placement.

All previously controlled default/zero-angle fingerprints must remain exact.

No existing fingerprint transition is authorized by R9.

**END OF AUTHORITY LEDGER RC1**
