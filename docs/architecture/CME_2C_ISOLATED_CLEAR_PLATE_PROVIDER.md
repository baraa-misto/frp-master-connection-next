# CME-2C isolated clear-plate provider

Provider: `C2_P2_AISC_370_25_CLEAR_RECTANGULAR_PLATE_LRFD_RC1`.
Baseline: `20fabefa90247dd3470d4698edda1b22d017e7c6`, count 128.

## Boundary and native authority

The sole new production module is `calculation/stainless_plate_clear_body.py`.
No existing production module imports it. It imports neither frozen C2-M nor
C2-P1; their code, tests and golden identities remain untouched. No public route,
registry entry, family provider or frontend selector is added. Primary members
remain FRP-only, all 16 routes / 39 route-qualified body identities retain their
native material policy, and public SS316 planning remains unavailable.

`FrozenPlateAuthority` carries pre-resolved material/source identity, exact frozen
fingerprints, source-system properties, same-section design thickness/rule/tolerance
evidence and same-section C2-P1 direct tensile endpoint. `TrustedClearRecord` binds
that snapshot to the complete request and server-owned geometry/demand authority.
An empty, duplicate, mismatching or incomplete catalogue record cannot authorize
resistance. Context records must be constructed only by trusted upstream engineering
code after resolving C2-M/P1. Client labels, hashes, capacities and booleans do not
create trusted context. There is intentionally no production qualification catalogue
or public context ingestion in this stage. Synthetic test contexts are not sources.

The snapshot is consumed verbatim: no copied thickness rule, no independently
recalculated tensile endpoint, no favorable MTR/cold-work/CSM basis. Test adapters
invoke frozen C2-M/P1 directly to obtain these values, including tolerance-credit
and 3/16-in boundary cases. Native `PhysicalQuantity` handles conversions and
`angle_fingerprint` handles canonical fingerprints. E3/F9/H2 arithmetic uses a
private Decimal-100 ROUND_HALF_EVEN context; input/output display does not round
the governing calculation. Pi is represented by a deterministic 100-digit decimal.

## Exact owner clarifications

The owner approved production-import isolation and a trusted pre-resolved snapshot
instead of frozen production imports. Frozen isolation tests remain unchanged.

The owner approved the conservative project cap `Fn = min(Fy, Fn_E3_raw)`.
The E3 trace retains raw and capped stress and whether the cap applied. This is
recorded as project-method authority, not misrepresented as an unmodified normative
E3 expression. Both principal flexural-buckling axes remain visible, and their
minimum available resistance governs. No E4 capacity is implemented.

The ten approved controlled-Markdown hard breaks are the only whitespace exception:
source reconciliation lines 6–8; specification lines 4–6; independent validation
lines 6, 81–82; owner approval line 4. Their five approved artifact hashes remain
exact. All other whitespace findings fail. No Git configuration, attribute or
repository checker is weakened; the external review validates the exact finding set.

## Calculations and fail-closed contracts

The snapshot binds a physical hole-free rectangular strip, actual bounds, nominal
and design thickness, references, frame and signed factored actions. Positive axial
action is tension; negative is compression; moments are right-hand, about z only.
The provider never generates a response or a moment from raw eccentricity.

E3 evaluates both trusted K/L axes only when E4 is qualified not controlling.
F9 retains q, My, Mp, branch candidate, actual Cb and authority, plastic cap and
available strength. Missing favorable Cb means exactly 1.0; untrusted favorable
credit and values outside [1,1.67] fail closed. H2 compression uses both available
endpoints. H2 tension retains both tension-side and compression-side expressions.
Pure tension consumes the frozen same-section C2-P1 endpoint; pure shear stays
outside P2. No unsupported endpoint is synthesized.

Geometry, source, method, demand, response, numerical comparison and activation
remain separate. An evaluated numerical failure stays visible alongside unresolved
external response; isolated PASS never means whole-connection PASS. Unknown E4,
missing lengths, holes/local mechanisms, arbitrary width, unsupported forms,
out-of-plane/biaxial bending, torsion, combined normal/shear and CSM fail closed.
No bolt/nut/washer/F593/F594, anchor/concrete, FRP or receiving-member capacity changes.

## Publication and exclusions

New tests execute all 14 positive goldens, 17 negative cases and 13 invariants,
owner-cap boundary cases, snapshot/tolerance/dimension adversaries, native public
isolation and fingerprint invariance. Complete existing regression QA remains
mandatory. Full local QA and direct exact-SHA hosted four-job CI must pass before
the external completion report declares success. One normal implementation commit,
no amendment, no tags. C2-P2 is not frozen by this order.

No C2-R, C2-A, C2-T, C2-P2 family activation, E4 numerical resistance, N-M-V,
CSM, welding/fabricated shapes, stiffness/contact/prying redistribution or CME-3.
