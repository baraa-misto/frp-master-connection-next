# Single-Bolt Numerical Engine Specification

## Controlled scope

Stage 2.1B is the first executable calculation-engine slice. It evaluates only the
authorized ASCE/SEI 74-23 Chapter 8 single-bolt, single-row component checks from an
immutable Stage 2.1A `SingleBoltPlanningInput`. The pure entry point is
`calculate_single_bolt`; it reads no file, environment variable, clock, random source,
network service, database, API, frontend state, or report state.

The implementation versions are:

- calculation engine `0.1.0.dev1`;
- engineering rule set `asce74-23-ch8-single-bolt-rc2.dev1`;
- application `0.0.0.dev0` and project schema `0.1.0-draft`, unchanged; and
- freeze status `draft`.

The ICE snapshot remains development-only, the locked ASTM F593 preset remains
`SOURCE_DATA_PENDING`, and the J1 whole connection remains
`SECTION_2_3_2_QUALIFICATION_REQUIRED`. This stage is not a validated full connection
engine and does not establish commercial design use.

## Numeric policy

All authoritative physical and dimensionless arithmetic uses `Decimal`. A local
60-digit context is used for equation evaluation; the mutable global Decimal context
is never changed. Pi is centralized as
`3.1415926535897932384626433832795028841971693993751`. The net-tension noninteger
power is evaluated as `exp(Theta * ln(ratio))`. No production intermediate or result is
rounded. Tests alone quantize recorded RC2 comparisons to 12 decimals using
`ROUND_HALF_EVEN`.

Area is a first-class dimension with exact `in2` and `mm2` conversion. The calculation
path canonicalizes lengths to mm, areas to mm2, forces to N, and stresses to MPa. An
exact physical conversion of one stored U.S. fixture to SI produces identical
unrounded physical outputs, dimensionless intermediates, property selections,
statuses, governing checks, and fingerprint. It does not regenerate a separately
printed SI standard hole.

## Property and factor assembly

For every used FRP property, the adjusted value is
`F* = C_M * C_T * C_CH * F`. Each trace records source property, qualification, all
three end-use factors, and adjusted property. Resistance assembly is ordered and
recorded as `R_design = C_delta * C_lap * phi * lambda * R_nom`.

`C_delta` is exactly 1.0 for this one-bolt/no-pitch slice. `C_lap` is exactly 0.60 for
single-lap and 1.0 for double-lap on applicable in-plane FRP checks. It is always 1.0
for pull-through and metallic-bolt checks. Bolt checks consume neither FRP end-use
factors nor `C_lap`. No factor is inferred, duplicated, or silently omitted.

## Authorized equation set

Symbols refer to the explicit Stage 2.1A physical inputs and selected adjusted
properties. Every equation returns a structured immutable trace.

### Bolt body and metallic bolt checks

- Nominal body area: `A_b = pi * d^2 / 4`.
- One-plane nominal bolt shear stress: `F_nv = 0.60 F_nt` with threads excluded and
  `F_nv = 0.50 F_nt` with threads included.
- Pure tension: `R_nom = A_b F_nt`; `R_design = 0.75 R_nom`.
- Pure one-plane shear: `R_nom = A_b F_nv`; `R_design = 0.75 R_nom`.
- Combined tension/shear: `f_v = V/A_b` and
  `F'_nt,raw = 1.3 F_nt - [F_nt/(0.75 F_nv)] f_v`;
  `F'_nt = min(F'_nt,raw, F_nt)`; `R_design = 0.75 A_b F'_nt`.

The modified combined tensile stress has no lower clamp. A nonpositive resulting
design resistance fails with no utilization and an explicit warning. Combined bolt
tension/shear is also forced to fail if its required pure-shear comparison fails.

Numerical bolt shear and combined evaluation require exactly one explicitly identified
shear plane and thread status. Zero planes are `INCOMPLETE_INPUT`; more than one plane
is `CALCULATION_NOT_SUPPORTED`. This is a provisional release boundary, not a permanent
code interpretation.

### Pull-through

The two nominal branches are `R_8-4a = 0.5 pi d_w t F*sh,tt` and
`R_8-4b = 0.4 pi d_w t F*sh,int`. The lower nominal branch governs; an exact symbolic
tie retains both branch IDs. `phi = 0.50`, `C_lap = 1.0`, and positive explicit
bolt-axis tension plus externally supplied prying is the demand. Prying is consumed
only when explicitly supplied; it is never generated.

### Pin bearing

With threads excluded from the checked layer, `R_nom = d t F*br`. With threads
included, the nominal expression is multiplied by 0.60. Directional selection is
`FBR_L` for longitudinal and `FBR_T` for transverse, including the approved exact
90-degree transverse endpoint. `phi = 0.60`.

### Net-section tension

`S_pr = w/d`, `r = (S_pr - 1)/(S_pr + 1)`, and
`Theta = 1.5 - 0.5(w/e1)` when `e1/w <= 1`; otherwise `Theta = 1.0`.
`K_nt = C_i[S_pr - 1.5 exp(Theta ln(r))] + 1` and
`R_nom = (w - d_n)tF*t/K_nt`.

`C_i = 0.40` only for a longitudinal plate. It is 0.50 for longitudinal or transverse
shape elements and for a transverse plate. `FT_L` or `FT_T` is consumed exactly as the
applicability plan selected it. `phi = 0.45`. `w <= d_n`, nonpositive bolt diameter or
end distance, and a nonpositive power prerequisite fail closed as invalid input.

### Shear-out

`R_nom = 1.4(e1 - d_n/2)tF*sh,LT`, with `phi = 0.50`. The raw expression is retained;
nonpositive design resistance is not clamped.

### Cleavage

Branch A is
`R_a,nom = 0.15[(2e2 - d_n)F*t + 2e1F*sh,LT]t`, with `phi_a = 0.50`.

For branch B when `e1/d < 4`,
`R_b,nom = R_br,nom[10/9 - 4d_n/(9e1)]^2` and `phi_b = 0.50`.
At and above `e1/d = 4`, `R_b,nom = R_br,nom` and `phi_b = 0.60`.
The branch is selected by the lower fully factored design resistance, not by nominal
resistance. An exact design-level tie retains both branch IDs.

Cleavage is applicable only to supported longitudinal tension. It is not applicable
for compression or the exactly perpendicular transverse case and is unsupported for
oblique tension in this release.

## Planning, final results, and aggregation

Planning and numerical comparison remain separate. Only `READY` plans execute.
Unresolved plans retain their identity, source snapshot, readiness, final availability,
warnings, and `NOT_EVALUATED`; they acquire no resistance or utilization.

Calculated results retain plan/component/layer/bolt/source identities, demand,
nominal and design resistance, utilization, comparison, equation trace, input
fingerprint, engine version, and rule-set version. Exact demand/resistance equality is
`PASS`; any greater demand is `FAIL`. A positive resistance with zero demand has zero
utilization and passes when the plan is ready. No comparison tolerance alters PASS or
FAIL.

A known required `FAIL` controls the aggregate. If a required unsupported check also
exists, the aggregate is `FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK`; without a known fail,
an unsupported required check prevents aggregate PASS. Whole-connection qualification
and engineering-review states remain visible. Governing and co-governing calculated
checks use the single named utilization comparison tolerance of `1E-12` and preserve
deterministic plan order.

## Golden verification

Production computes from physical inputs and has no dependency on the golden JSON.
Tests use the repository RC2 JSON only as the immutable expected-value oracle. P1,
PT1, P2A, P2B, J1-T, J1-C, B1 synthetic, and the exact 90-degree case reproduce all
recorded values and dispositions. P1 and P2A Layer A retain bearing/cleavage ties;
P2B retains both known Layer B failures and unsupported cleavage; J1-T is governed by
W-flange transverse net tension while its whole-connection qualification remains;
B1 uses explicit synthetic `F_nt = 100 ksi` and does not alter the locked F593 preset.

The J1 W-flange projected `e1` is retained at its underlying exact physical value;
the JSON's `2.121320343560 in.` is its 12-decimal printed representation. This preserves
the RC2 shear-out oracle without modifying expected data.

## Fail-closed exclusions

No multirow equation, block shear, member-end-to-bolt demand distribution, prying
generation, automatic return-element exemption, whole-J1 qualification equation, API,
frontend, persistence, migration, project serialization, HTTP exposure, report, or
generated calculation snapshot is implemented. Licensed PDFs remain read-only outside
Git, and no source wording, table, figure, or commentary is reproduced here.

## Stage 2.2A invocation boundary

The application orchestrator is a caller of `calculate_single_bolt`; it is not part of
the equation engine. It builds existing planning records from canonical geometry,
material, fastener, factor, time-effect, and explicit demand inputs, then preserves the
returned traces, results, aggregate, and governing IDs. No equation primitive or
factor assembly is duplicated in `frp_master_connection.application`. Engine and rule-
set versions remain unchanged.

## Stage 2.2B API boundary

The stateless API adapter invokes the Stage 2.2A orchestration service and never calls
an equation primitive or `calculate_single_bolt` directly. Decimal-string quantities
are converted into the existing quantity contracts before orchestration, and response
values are projections of the returned plans, final results, traces, aggregate, and
governing IDs. No equation, approved golden value, engine behavior, or rule-set
behavior changes in Stage 2.2B. The engine and rule-set identifiers remain
`0.1.0.dev1` and `asce74-23-ch8-single-bolt-rc2.dev1`.
