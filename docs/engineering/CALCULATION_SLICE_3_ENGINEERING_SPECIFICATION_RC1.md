# FRP Master Connection
# Calculation Slice 3 Engineering Specification — RC1

**Document status:** Candidate engineering specification pending Baraa Misto approval  
**Not a Codex implementation order**  
**Calculation family:** Member-end-force transfer and eccentric in-plane bolt-group demand  
**Primary standard:** ASCE/SEI 74-23  
**Relevant source locators:** Section 2.9; Commentary C8.1; Commentary C8.3.2  
**Parent calculation authority:** Accepted Calculation Slice 2 / Stage 2.4B multi-row engine

## 1. Purpose

Calculation Slice 3 begins removal of the current "externally resolved connection demand" limitation.

The first controlled family converts a canonical member-end **force vector** and its physical reference point into deterministic in-plane bolt-group demand vectors for the existing planar bearing-type rectangular bolt-group family.

This RC1 does **not** automatically transfer all six member-end actions. Member-end moments remain traceable context and out-of-plane demand remains explicit/fail-closed until a later approved engineering method resolves them.

## 2. Source basis

ASCE/SEI 74-23 Section 2.9 requires connection forces and deformations to be consistent with structural-analysis assumptions and requires eccentric fastener-group effects to be analyzed using established principles of mechanics.

Commentary C8.1 requires realistic internal-force distributions in equilibrium with applied forces and moments, consideration of relative stiffness and deformation capacity, and a linear moment-induced internal-force distribution proportional to distance from the center of rotation.

Commentary C8.3.2 requires connection strength to be evaluated from the actual force distribution.

The standard does not provide one complete numerical bolt-group demand algorithm for this software architecture. The elastic moment-correction algorithm in this RC1 is therefore an explicitly labeled project rational extension built to satisfy those source constraints.

## 3. Current controlled boundary

### 3.1 Automatically used member-end data

The automatic RC1 demand resolver uses:

- the canonical member-end force vector;
- the canonical force reference point;
- the canonical connection-interface frame;
- the canonical bolt coordinates;
- the existing accepted Stage 2.4A direct row-demand method and provenance.

### 3.2 Retained but not automatically transferred

The following remain in trace but do not create bolt-group demand in RC1:

- member-end bending moments;
- member-end torsional moments;
- independent connection moments.

If any such moment is nonzero, the force-only demand result may still be calculated, but automatic resistance handoff is prohibited and a structured warning is required.

### 3.3 Out-of-plane force

A connection-force component normal to the interface does not create automatic bolt-axis tension in RC1.

The force-only in-plane demand may still be calculated, but the result must identify that explicit bolt-axis tension or another future approved demand model is required.

No prying is generated.

## 4. Coordinate system

For the active connection interface define an orthonormal right-handed basis:

- `u`: first in-plane axis;
- `v`: second in-plane axis;
- `n = u × v`: interface normal.

All force and position inputs are transformed from canonical global geometry into this basis by backend-authoritative coordinate transforms.

Screen coordinates have no engineering authority.

## 5. Rigid-body force transfer

Let the member-end force be:

`F = (Fu, Fv, Fn)`

at physical reference point `P`.

Let the geometric bolt centroid be `C`.

For the in-plane force:

`Fp = (Fu, Fv)`

The scalar external moment about `C` caused only by the force-line offset is:

`Mext = [(P - C) × Fp] · n`

Member-end moments are not added to `Mext` in RC1.

This is a rigid-body reference-point transformation, not a resistance equation.

## 6. Existing direct-demand component

For each selected Stage 2.4A demand scenario, obtain each bolt's direct share `si`.

The shares must satisfy:

`si >= 0`

and:

`sum(si) = 1`

for the active scenario.

The direct in-plane demand vector at bolt `i` is:

`Di = si Fp`

The shares come from the already approved demand basis:

- ASCE prescribed distribution;
- conservative full-row envelope;
- engineer-defined distribution with provenance.

RC1 shall not invent a new direct row distribution.

## 7. Geometric bolt centroid and polar coordinate sum

For `N` physical bolts with in-plane coordinates `(xi, yi)`:

`xc = sum(xi)/N`

`yc = sum(yi)/N`

Define:

`x'i = xi - xc`

`y'i = yi - yc`

and:

`Jb = sum(x'i^2 + y'i^2)`

This is a geometric coordinate sum used only for the equal-stiffness elastic moment component. It is not a member torsion constant and shall not be named simply `J` in user-facing trace.

## 8. Direct-distribution moment

The existing direct distribution may itself carry a moment about the geometric centroid.

Calculate:

`Mdirect = sum(x'i Di,v - y'i Di,u)`

Do not assume it is zero.

## 9. Residual moment

The residual moment requiring elastic bolt-group distribution is:

`Mres = Mext - Mdirect`

This guarantees that the combined direct and moment components satisfy equilibrium.

## 10. Linear elastic moment component

For a supported identical-bolt group with `Jb > 0`, the moment-induced bolt-force vector is:

`Mi,u = -(Mres/Jb) y'i`

`Mi,v = +(Mres/Jb) x'i`

The magnitude of the moment-only component is therefore proportional to radial distance from the geometric centroid.

This is the RC1 project rational extension implementing the linear source requirement of Commentary C8.1 under the equal-bolt-stiffness assumption.

The total per-bolt in-plane demand vector is:

`Qi = Di + Mi`

and:

`|Qi| = sqrt(Qi,u^2 + Qi,v^2)`

No intermediate engineering rounding is permitted.

## 11. Equilibrium requirements

Every calculated demand scenario shall independently verify:

`sum(Qi) = Fp`

and:

`sum[(ri - C) × Qi] · n = Mext`

Failure of either equilibrium check is a calculation failure.

## 12. Supported automatic geometry

The first automatic family is limited to:

- one planar interface;
- rectangular, nonstaggered bolt groups;
- identical bolts;
- canonical physical bolt coordinates;
- existing Stage 2.4A direct demand plans;
- no friction transfer;
- no slip-critical behavior;
- no generated prying;
- no stiffness-weighted heterogeneous bolt model.

Physical geometry outside this family may remain representable without receiving automatic RC1 demand.

## 13. Degenerate and unsupported cases

If `Mres != 0` and `Jb <= 0`, return `CALCULATION_NOT_SUPPORTED`.

A single bolt may carry concentric direct force but cannot automatically equilibrate a nonzero in-plane eccentric moment under this model.

A pure independent moment with zero in-plane force is not supported by RC1.

Moment-resistant frame-connection behavior is outside this slice.

## 14. Method identity and qualification

The result shall keep separate identities for:

- rigid-body force/reference transformation;
- inherited direct row-demand method;
- `RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY` moment correction.

The rational moment correction shall never be described as a direct ASCE prescriptive row-distribution formula.

Any existing Section 2.3.2 qualification attached to the physical connection remains visible.

## 15. Member-end moments

Member-end moments remain canonical inputs and remain visible in the trace.

RC1 does not automatically decide that a simple connection transfers those moments into the bolt group.

If any member-end moment is nonzero, return warning:

`MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL`

The in-plane force-only demand may still be displayed as a diagnostic result.

## 16. Out-of-plane force

If `Fn != 0`, return warning:

`OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND`

RC1 shall not derive bolt-axis tension from `Fn`, in-plane bending moments, plate contact, or prying.

## 17. Result contract

The demand result shall retain at minimum:

- action-source identity;
- member/component identity;
- original global force vector;
- original member-end moments;
- original force reference point;
- interface basis;
- projected `(Fu, Fv, Fn)`;
- geometric bolt centroid;
- `Jb`;
- direct demand method and provenance;
- direct per-bolt vectors;
- `Mext`;
- `Mdirect`;
- `Mres`;
- moment per-bolt vectors;
- total per-bolt vectors and magnitudes;
- row and bolt identities;
- equilibrium residuals;
- method applicability;
- qualification;
- warnings;
- calculation availability;
- numerical trace;
- version identities;
- deterministic fingerprint.

## 18. Resistance handoff

RC1 is a demand-analysis authority only.

Automatic handoff of eccentric per-bolt vector demands to the existing Stage 2.4B resistance engine is **not authorized in RC1**.

Reason: eccentric moment can rotate individual bolt demand vectors relative to the connection resultant, while the accepted resistance family has directional FRP applicability and row/failure assumptions that require a separate compatibility review.

Every RC1 result shall therefore state:

`resistance_handoff = NOT_AUTHORIZED_IN_RC1`

A later controlled stage may approve the correct resistance integration after directional and applicability review.

## 19. Numerical policy

Use the repository's exact Decimal quantity architecture.

Target equation precision remains 60 decimal digits unless the accepted architecture establishes a stronger shared policy.

Do not use binary floating-point values as authoritative demand inputs or equation values.

No intermediate engineering rounding.

Serialized golden values use 12 decimal places and `ROUND_HALF_EVEN`.

## 20. Units

Use one physical calculation path.

Existing controlled conversion constants remain authoritative.

Changing display units must not change:

- physical bolt demand;
- equilibrium;
- method;
- applicability;
- qualification;
- warnings;
- fingerprint.

## 21. Fingerprinting

Fingerprint inputs shall include:

- canonical physical force vector;
- force reference point;
- interface frame;
- physical bolt coordinates and identities;
- inherited direct demand plan and provenance;
- rational-extension method identity;
- relevant versions.

Exclude camera, viewport, display units, formatting, UI selection, timestamps, and request timing.

## 22. Required warnings

At minimum:

- `MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL`
- `OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND`
- `PURE_CONNECTION_MOMENT_NOT_SUPPORTED`
- `DEGENERATE_BOLT_GROUP_FOR_ECCENTRIC_MOMENT`
- `RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED`

## 23. Deliberate exclusions

RC1 does not implement:

- general six-component connection-action transfer;
- moment-resistant frame-connection analysis;
- bolt-axis tension distribution;
- prying;
- contact/compression distribution;
- nonlinear instantaneous-center bolt-group analysis;
- friction or slip transfer;
- heterogeneous bolt stiffness;
- staggered automatic demand;
- new resistance equations;
- changes to Stage 2.4B numerical resistance;
- persistence, reporting, authentication, entitlement, billing, or deployment.

## 24. Benchmark authority

The companion `FRP_MASTER_CONNECTION_CALCULATION_SLICE_3_GOLDEN_BENCHMARKS_RC1.json` is the machine-readable candidate benchmark authority.

Production shall derive every result.

Tests may use the golden as an oracle.

## 25. Implementation sequence after approval

After this RC1 specification and golden are independently verified and approved:

- Stage 2.5A may implement framework-independent contracts and the demand-analysis engine;
- no resistance handoff is authorized in Stage 2.5A;
- a later controlled engineering review shall determine if and how eccentric per-bolt vectors may feed the directional FRP resistance engine.

