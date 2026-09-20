# Calculation Slice 7 RC2 — Implementation and verification record

## Authority and pre-mutation gates

The earlier CS7-RC1 package was never implemented, committed, or pushed. It is
superseded before execution. RC2 is the only current authority. Specification
section 23 explicitly retains the earlier test-only signed strength numbers for
arithmetic verification; those numbers exist only in tests, not production.

Before mutation, `main`, `origin/main`, and remote `main` were exactly
`18419606f4143f27240a39374b25e294a9f39253`, count 103, with no staged, modified,
or untracked paths. All nine annotated freeze tag objects and their peeled
commits matched the established remote. No RC1 worktree cleanup was necessary.

All seven supplied files were read completely. The four prescribed SHA-256
values matched before mutation and the repository copies remain byte-exact:

| RC2 authority | SHA-256 |
| --- | --- |
| Decision | `930517D8198A553206BCBC18CA4435D04DA98E7922186DDDEDBA8F4CAAB8CFC2` |
| Specification | `DB578929B9E3355E77A8B703AB8857DC713F100FA9D1884D1D071B4751939F83` |
| Golden, exactly G1–G72 | `74CC12CB079A3C8429BD7249E0DE4E16CE066B156D50AF824992000E27701722` |
| Authority ledger | `3A214576C1BF7DB976010CD4AEC0F1D1FAFEFC92B99D3B7633A5559E89E46D9D` |

All prescribed text sentinels are present. The external controlling order's
computed SHA-256 is
`5BDEB6262F90C25A96048E7D7248EF84882508E50E65AB31972B955EF00FF487`.
Neither PDF is copied, reproduced, or tracked in the repository.

## Read-only source audit

ASCE/SEI 74-23 source SHA-256:
`A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`.
Erratum 1 SHA-256:
`5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`.
The new copies are byte-identical to the previously reviewed sources; all pages
were covered, with visual inspection of the applicable equation, figure,
qualification/eccentricity provisions, commentary, and both erratum pages.

Equation 8-15 is the FRP clip-angle instep shear check only. The provider uses
the RC2 prescribed 0.70 resistance factor and adjusted in-plane shear property.
Sections 2.3.2, 2.9, and 8.1.2 retain qualification and eccentricity obligations.
Commentary C8.1.3/C8.3.4 does not provide a universal heel, delamination, prying,
or individual anchor-distribution model. The January 13, 2026 erratum changes a
Chapter 5 elastic-modulus direction label; it does not revise Equation 8-15.

## Shared-architecture audit (completed before mutation)

| Responsibility | Exact reuse / additive boundary |
| --- | --- |
| Angle geometry validation | `domain.member_profile.AngleProfileDimensions`; unchanged. New quantity-aware radius and physical end-cutback record. |
| Quantity vectors | `calculation.eccentric_demand.ExactQuantityVector3D`; unchanged canonical `PhysicalQuantity` unit conversions. |
| Wrench transport | Existing `actions.transforms.shift_force_moment_reference` establishes the reference/sign convention but uses floating-point geometry. New exact local transport retains all six components without modifying it. |
| Frame / references / equilibrium | Additive right-handed `AngleConnectorFrame`, `AngleWrench`, and `AngleCoreRequest`; heel origin is exactly zero; exact independently shifted negative support reaction must equilibrate. |
| Canonical fingerprints | Reuse `calculation.fingerprint._canonicalize`; separate core, geometry, reference, material, source-binding, and provider identities. No historical serializer change. |
| Provenance / adjusted properties | Reuse `EngineeringPropertySource`, `MaterialPropertySnapshot`, `EndUsePropertyTrace`, `FactorAssemblyTrace`, and Chapter 8 source snapshots. No duplicate Section 2.4 adjustment. |
| Generic core | `backend/src/frp_master_connection/calculation/angle_connector_core.py` |
| Provider contract / explicit registry | `backend/src/frp_master_connection/calculation/angle_connector_providers.py` |
| FRP provider only | `backend/src/frp_master_connection/calculation/frp_angle_connector_provider.py` |

The core has no material-family, strength, factor, qualification-package, or
resistance-provider input. Exact rational arithmetic over the existing Decimal
quantities prevents intermediate rounding in cross products and equilibrium;
finite results are returned as Decimal quantities. Nonterminating exact
transport cannot be silently rounded. Utilizations are rendered at 80 digits;
exact rational comparisons decide the boundary, including `U=1`.

Frontend production, API, physical product, dependencies, workflows, lockfiles,
existing controlled authorities, and existing-tag changes are all zero. Only
three new production modules are authorized; no old production module changes.

## Engineering implementation

The default heel force is `(4,6,-1) kip`, heel moment `(-1,-0.5,-9) kip-in`.
The connector-on-support wrench is `(4,6,-1) kip`, `(11,-8.5,-9) kip-in`.
The support-on-connector reaction is its exact negative. Shifting that reaction
back to the heel gives exactly zero force and moment residuals.

The provider-independent core fingerprint includes geometry, frame, references,
input wrench, transported wrenches, and equilibrium. FRP, unsupported 316SS,
and unknown-provider requests do not change it. Provider results/fingerprints
are separate; unsupported selections never fall back to FRP. The immutable
registry implements FRP only; no stainless property, equation, prying method,
UI option, or physical Stage 4.2 product is supplied.

The FRP provider maps extrusion to LW, each physical leg's in-plane transverse
direction to its own CW, and TT to the corresponding physical normal. Instep
length is derived from actual heel-intersecting end cutbacks. The check covers
only `abs(F_A)`; the default design resistance is 22.4 kip and utilization is
the approved G26 value. Existing adjusted property traces are consumed once;
their inherited 60-digit conversion precision is not overwritten or rounded to
make a test pass.

A qualified full-wrench package is immutable and binds geometry, material and
property trace, member fasteners, support fixture, frame/references, and source
revision. There is no interpolation or anonymous numeric production source.
Each demanded sign selects its own already-design strength. Nonzero full-wrench
evaluation requires explicit complete assembly coverage (including heel, both
legs, out-of-plane/TT/delamination, contact, connector prying and secondary bolt
bending) and explicit linear-interaction authorization. No partial-coverage
mechanics or implicit demand-specific waiver is invented. Zero demand needs no
qualified body source. Missing sign, source, binding, interaction, or coverage
fails closed. A supported result is review-qualified, never ordinary PASS.

Default qualified utilization is the approved G34 value. Review metadata and
Section 2.3.2 qualification remain mandatory. Exact group-level support handoff
is independent of provider success. Flexible-fixture/prying distribution and
all anchor/concrete capacities remain external; no individual anchor force is
fabricated.

## Verification and publication gates

Local verification passed on 2026-09-05: 3,044 backend tests, including 94 new
CS7 tests, and 603 unchanged frontend tests (42 test files). Both configured
coverage gates are 100%; the three new modules have 349 statements and 76
branches with no uncovered lines or branches. Ruff formatting/lint, strict
mypy (244 source files), ESLint, strict TypeScript, production build, hash-locked
backend installation, `pip check`, runtime/CLI smoke tests, `npm ci`, and
`npm ls --all` passed. Full and runtime-only npm audits each reported zero
vulnerabilities. All 55 tracked/new JSON files parsed; existing protected files
and all nine freeze tag identities remained unchanged. The first focused test
invocation encountered a local pytest-cache write issue after assertions passed;
the normal complete QA run passed without changing repository configuration.

Known unchanged frontend diagnostics: jsdom reports unsupported document
navigation in one historical test; Vite warns about existing large chunks.
Neither is an assertion, type, lint, build, or security failure. No timeout,
dependency, workflow, or production workaround was introduced.

`backend/tests/calculation/test_angle_connector_core_and_frp_provider.py` maps
all G1–G72, adverse input/source cases, all six demanded signs, exact boundary
and failure cases, source changes, U.S./SI equivalence, provider independence,
and historical freeze identities. Historical audits use their accepted
manifest/object resolution, not a successor HEAD/source comparison or required
local tag reference.

Full local backend/frontend QA, configured 100% branch coverage, strict static
checks, build, JSON/whitespace validation, dependency/security audits, all
historical fingerprints and freeze audits are required before commit. Fresh
depth-one/no-tags/no-alternates full QA and clean-tree verification are required
after commit and before push. Logs and final object identities are external so
they can describe the final commit without a self-referential hash or amendment.

Exact required subject: `feat: add angle connector core and FRP resistance provider`.
Expected final count: 104. One implementation commit, no amendment, no tags.
Hosted CI remains pending until direct four-job evidence is available. Physical
Stage 4.2 is not begun and cannot begin until separate acceptance/authority.
