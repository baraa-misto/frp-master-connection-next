# Calculation Slice 8 RC1 / R1 — implementation and verification

## Controlling authority and baseline

Before mutation, local HEAD, origin/main and remote main were exactly
`d940192ea8eecb7e35f9601c38f3ad841f580916`, main, 104 commits, clean index/worktree.
No physical Stage 4.2 implementation existed. All original RC1 files and the
R1 clarification/replacement golden/correction order were read completely.
R1 supersedes only the original golden and the conflicting negative-web / G62
comparison semantics; no accepted historical engine is reinterpreted.

| Authority | Approved and verified SHA-256 |
| --- | --- |
| RC1 decision | `DBA6F3EE9B753A29AE6930E9D2FCBEE08E8D0E6CA2523329D828114FCFAA443D` |
| RC1 specification | `BB883A48BC340FCF4012BCBF9B6E240B3C1EDE5BE43EB6F5F7FCC4DCE9D839E6` |
| RC1 authority ledger | `913629A90E4354990F55FD8CAD3C44476320B0DADC288AC242F8A863B4A39A07` |
| R1 clarification | `C02DC1CAFB88CD67B2B857C08B7EAD7F4FB257388AB6420409E227C40C89201D` |
| Replacement RC1-R1 golden, exactly G1–G80 | `E854CEDB44EC02115014A7139C81BCACA7531E6FE3E789DC509A21BA5B70C48C` |
| External original Codex order | `268B2B66E2065BEA45827993416D8ACFF5EAF381164F3B4D1E05F8A60356F91C` |
| External R1 correction order | `E0C0CB5D05881C53133678D60A4818D3BDFFEF73EA2BBECCB3A18D124A703B35` |

All required Markdown final sentinels are present. The five current repository
authority copies are byte-exact. The superseded original G1–G80 golden is not
copied or used by production/tests. This rational mechanics slice requires no
new PDF extraction; neither licensed PDF is copied into the repository.

## Mandatory pre-mutation architecture audit

1. Existing API: `calculation.eccentric_demand.EccentricDemandInput` and
   `calculate_eccentric_bolt_group_demand`; input binds force, member/independent
   moments, explicit reference/frame, physical geometry and direct demand plan.
2. `_base_warnings` emits
   `MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL` for nonzero
   member-end or independent connection moments. Those moments remain trace-only.
3. The main function's zero-force/nonzero-moment path returns
   `CALCULATION_NOT_SUPPORTED`, no scenarios and
   `PURE_CONNECTION_MOMENT_NOT_SUPPORTED`. Both paths were reproduced read-only.
4. `_centroid_and_polar` uses physical coordinates and equal participation.
   `_calculate_scenario` transports only force-reference eccentricity, retains
   approved direct shares, and uses `-ratio*centered_y`, `ratio*centered_x`
   for the residual-moment correction. Independent free moment is not added.
5. Existing immutable quantity/vector/result records and canonical dimensional
   SHA-256 architecture remain untouched. Stage 2.5A has its accepted native
   Decimal-80 intermediate path and native equilibrium tolerance. Slice 8 does
   not copy that rounding path or adopt its tolerance.
6. Stage 2.5B `resistance_handoff._handoff_demand`, `_bearing_selection`, and
   `_bundle_with_bolt_demand` consume actual signed components and magnitudes.
   The new projections can enter these typed consumer seams without changing
   capacity or fabricating a parent Stage 2.5A result/proof envelope.
7. `wi_moment_splice_resistance.FlangePlaneDemand` and
   `evaluate_asymmetric_two_plane_bolt` consume each plane's actual signed vector
   independently. No equal-plane assumption or new nominal bolt source is added.
8. Safest seam: the single new module
   `backend/src/frp_master_connection/calculation/in_plane_wrench_demand.py`.
   It imports the established quantity unit factors and `InPlaneQuantityVector`;
   no old API, export module or product orchestration is changed.
9. Historical `eccentric_demand.py`, `resistance_handoff.py`,
   `wi_moment_splice_resistance.py`, `quantities.py`, `fingerprint.py`,
   `wi_moment_resultants.py`, `angle_connector_core.py`,
   `angle_connector_providers.py`, `frp_angle_connector_provider.py`, and all
   other pre-existing production files remain unchanged. New tests bind their
   normalized source identities without requiring local tags or successor HEAD.

## API, exact mechanics and output

`InPlaneWrenchRequest` contains immutable ordered `WrenchBolt` records (stable ID,
A, B), a two-component reference, signed forces/free moment and explicit length,
force and moment units. Scalars accept finite Decimal, lossless decimal strings
or integers; float, Boolean, missing/malformed coordinates, duplicate IDs/points,
nonfinite values and dimensionally invalid units fail closed via a coded
`WrenchInputError`. There is no silent conversion from binary float.

`calculate_in_plane_wrench_demand` converts each input to a standard-library
Fraction before multiplication by the established exact finite unit factors.
The authoritative solution uses mm, N and N-mm. It retains exact centroid,
deltas, J, reference wrench, centroid moment, direct shares, corrections, totals,
and squared magnitudes. All Fractions expose canonical numerator/denominator
records in `canonical_json`; denominators are positive and fractions reduced.

`M_C,c = M_C,R + (A_R-A_c)F_B - (B_R-B_c)F_A` transports the complete wrench.
Direct shares are `F_A/n`, `F_B/n`. Corrections are
`-M_C,c*DeltaB/J`, `+M_C,c*DeltaA/J`. Exact proof records compare targets with
independently recovered A force, B force, centroid moment and original-reference
moment. No epsilon, projected-residual check or residual redistribution exists.
An internal proof failure raises; it cannot produce a calculated result.

`solution.in_units(length_unit, force_unit)` produces a lossless rational view.
`projected_bolts()` yields the existing dimensional vector and magnitude types
at Decimal precision 80 / ROUND_HALF_EVEN, using a fresh explicit Context.
Projection is independent of ambient precision, rounding, traps and exponent
settings. Magnitude is the square root of the projected exact squared magnitude,
not a square root computed from already-rounded force components. No fixed
decimal-place quantization is applied. The dimensional moment unit in a view is
its force unit multiplied by its length unit.

Fingerprinting binds contract/method, stiffness assumption, ordered stable IDs,
canonical physical coordinates/reference/wrench, every exact result/proof,
status, projection authority and R1 compatibility authority. U.S./SI-equivalent
requests have identical canonical identities. Presentation is not an input.
No resistance result or engineering PASS is implied by `CALCULATED`.

## Numerical and compatibility evidence

The default four-bolt group has centroid `(0,0) in`, J=`45/4 in2`.
The positive web fixture uses `(5,3.6) kip` and the complete positive free moment.
The negative fixture uses `(-5,3.6) kip` and exactly
`-1.553553800592300098716683119447186574531095755182625863770977295162882527147088 kip-in`.
G39–G47 prove lossless sign reversal, all corrected exact vectors/proofs and
the swapped magnitude pairs; no ambient Decimal unary negation shortens digits.

Pure moment `9 kip-in` gives `(3/5,-6/5)`, `(3/5,6/5)`, `(-3/5,-6/5)`,
`(-3/5,6/5) kip`, zero force sum and exact moment recovery. Zero wrench yields
zero vectors. One bolt with zero transported moment transfers the entire force;
nonzero transported moment at J=0 returns
`CALCULATION_NOT_SUPPORTED_ZERO_GROUP_POLAR_SUM`, with no fabricated bolt couple.
An eccentric reference with a canceling free moment is also tested.

G55–G62: reference `(0,2) in`, force `(8,0) kip`, free moment zero produces
exact `-16 kip-in`. Direct Stage 2.5A invocation verifies identical physical
group/reference/forces/J, equal direct shares, the same correction mechanics,
and its native equilibrium/status. Slice 8 independently proves exact recovery.
Its A-components are `14/15` and `46/15 kip`. Native final Decimal places differ
as documented by R1; tests retain that difference as evidence, not a defect.
No cross-engine epsilon, output rounding-to-match or intermediate emulation is
used. Additional accepted concentric, eccentric, diagonal and reversed-force
Stage 2.5A equal-share fixtures are compared within their native authority.

Arbitrary reference `(2,1) in`, force `(4,-2) kip`, free moment `3 kip-in`
produces exact centroid moment `-5 kip-in`; recovery at the original reference
is exactly `3 kip-in`. Irregular and collinear patterns, translation, full sign
reversal, U.S./SI equivalence and context independence are explicitly tested.

Downstream tests feed actual signed vectors/magnitudes into Stage 2.5B consumers
and existing calculations, and distinct plane vectors into the unchanged
two-plane bolt check. A test-only controlled nominal strength is used solely in
that test; missing source remains NOT_EVALUATED. No production strength is added.

## Verification and publication gates

Focused verification: 114 tests including G1–G80 pass; the new module has 182
statements and 40 branches, all covered. Ruff and strict mypy pass. Complete
local backend/frontend QA, all historical and freeze regressions, dependency
consistency/security, JSON/whitespace and runtime smoke checks are required
before commit. The final full local run passed 3,158 backend tests and 603
unchanged frontend tests. Both configured line/branch coverage gates were 100%.
Ruff, strict mypy, ESLint, TypeScript, production build, hash-locked backend
installation, pip check, npm ci/ls and runtime CLI/import smoke passed. Full
and runtime-only npm audits reported zero vulnerabilities. The final backend run
includes the additional long-input / half-even tie / mixed-unit test and the
strengthened downstream explicit-demand consumption assertion: 24,673 statements,
6,672 branches, none missed; 109.27 seconds. All 56 tracked/new JSON files parse.
Every existing protected path and historical handoff field is unchanged. Remote
main remains the required parent and all nine remote tag/peeled identities match.
Final source/object audit and publication evidence are recorded externally.

Known unchanged frontend diagnostics are the historical jsdom navigation
message and Vite large-chunk warning; neither is an assertion/build failure.

Exactly one commit is authorized:
`feat: add in-plane bolt-group wrench demand engine`, final count 105.
No amendment and no tag. After commit, a fresh depth-one/no-tags/no-alternates
checkout must pass complete QA and clean-tree checks before normal main push.
Final object/log/ref evidence is external to avoid a self-referential commit
hash or amendment. Hosted four-job CI remains pending until direct evidence.
The configured browser shows GitHub's signed-out private-repository 404; there
is no configured GitHub CLI/token connection. No credentials were extracted or
account settings changed. Local success is not evidence of hosted success.

All nine freeze tag objects and peeled identities are preserved. Frontend,
public API, historical production, dependencies, workflows, lockfiles and tag
change counts are zero. Physical Stage 4.2 is not implemented or resumed.
