# Engineering Source Register

| Control | Value |
|---|---|
| Document ID | FMC-ENG-REG-001 |
| Stage | 0.1 |
| Register status | Draft; source registered, technical mapping not started |
| Register owner | Engineering approval authority |

## Register

| Source ID | Source type | Title | Edition | Errata or correction set | Publisher | Applicable subject | Controlled-copy location | Verification date | Approval status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| SRC-001 | Private licensed standard | Load and Resistance Factor Design (LRFD) for Pultruded Fiber Reinforced Polymer Structures | ASCE/SEI 74-23 | Verification pending | American Society of Civil Engineers | Pultruded FRP LRFD connection subjects; capability-by-capability applicability mapping has not started | Outside tracked repository / reference-private when locally present | Not verified | Primary source registered; engineering mapping not started | Do not reproduce copyrighted content. Registration does not establish coverage, applicability, or implementation approval. |

## Field controls

- **Source ID** is the stable reference used by coverage, risk, verification, and future result records.
- **Source type** distinguishes licensed standards from public standards, manufacturer data, qualification/test data, and documented engineer-defined methods.
- **Edition** and **Errata or correction set** are mandatory parts of an eventual engineering basis; an edition alone is insufficient.
- **Applicable subject** is a scoped index only and must not be interpreted as a claim that a particular capability is covered.
- **Controlled-copy location** records where an authorized copy may be held without making it a repository artifact.
- **Verification date** is populated only after an authorized reviewer verifies the controlled source and correction set.
- **Approval status** distinguishes bibliographic registration, completed mapping, verified implementation, and engineering approval. The current entry has only bibliographic registration.

## Licensed-source controls

1. No licensed PDF is required or stored in Stage 0.1.
2. A locally held authorized copy must remain outside tracked content. If temporarily placed under reference-private, Git ignores it; only the explanatory README is eligible for tracking.
3. Equations, tables, figures, commentary, extended excerpts, and source-derived test fixtures are not reproduced in this repository during Stage 0.1.
4. Future coverage work records controlled clause, table, or equation references and a concise original description, not copied source text.
5. Errata must be verified against an authoritative controlled source before a calculation mapping can be approved.
6. Source access, mapping, independent verification, and engineering approval are separate controls.

## Stage 0.1 limitation

This register contains bibliographic and control metadata only. It does not contain or approve an engineering equation, numerical criterion, resistance, capacity, or calculation capability.

## Stage 2.4A source snapshot update

Stage 2.4A verified the externally held ASCE/SEI 74-23 source and Erratum 1 for the
Calculation Slice 2 RC1 planning scope without copying either PDF into the
repository. The controlled specification SHA-256 is
`44431A8921CF1ADF9C7D0F7F022C9615265308A41BE589B1EE5150A7D7886F99`; the controlled
golden SHA-256 is
`C5E38841EC97538AB5BEAB2954905951BC67431AC0EC0BC847CA735038A2F610`.

The transverse plate branch retains both concise source locators and records the
conservative `C_T = 0.50` planning interpretation as a structured source conflict.
The conflict is not hidden and no licensed source text is reproduced. Stage 2.4A
executes no new resistance equation.

## Stage 4.3 source/application mapping

The Stage 4.3 order and acceptance matrix (ART-335) control this new product only. Externally held ASCE/SEI 74-23 SHA-256 `A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC` and Erratum 1 SHA-256 `5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550` were verified read-only. No PDF is copied into the repository. Relevant locators: Sections 2.3.2, 2.4 and 8.3.2.1–8.3.2.6, including Eqs.8-3, 8-4a/b and the applicable bearing/local-group clauses. Existing controlled Slice 1/2 factor/applicability records remain authoritative and unchanged.

`calculation/sourced_bolt_interaction.py` adds an explicitly sourced Fnt/Fnv Eq.8-3 interface because the historical combined-bolt function is tied to its accepted F593 ratio authority. It reuses native bolt area/tension/shear functions, native Decimal-60 and quantity conversions, and requires a separate condition/thread/grip-bound strength source. F593 identification alone does not supply strength. F43-B01 independently tests the stress boundary. No historical equation is changed.

`application/wi_frp_support_local_checks.py` invokes existing bearing and lesser-of-both-branches pull-through using the actual layer thickness, washer, material basis and complete verified response. Bearing row-pitch reduction is used only where real geometry and a cardinal constant-direction row mapping establish applicability. Pull-through does not inherit the bearing pitch factor; both FSH_LT/through-thickness and interlaminar sources remain required. Oblique/free-moment row mappings outside accepted local authority remain named source limitations. Full solid depth is not a thin plate; hollow walls have separate qualified force participation and no equal sharing or automatic double-shear credit.

Five independent source categories are kept separate: Slice 7 angle-body qualification, member-attachment qualification, complete support/contact response, support fastener strength, and local support-zone capacity/interaction. Exact six-component equilibrium does not establish stiffness/contact/strength qualification. Production registry is empty. Synthetic evidence is restricted to tests and cannot be selected in the application. No normative out-of-plane panel, universal heel/prying, long-bolt or 3-D solid splitting formula is invented.

## Stage 4.4 RC1 current successor

`ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION` / `4.4-RC1` starts from
`1faa1ff522d0e0a39a42e2dc2d3974b5dba98479` (114 commits). Equal and unequal
FRP Angle columns each have exactly two independent FRP base angles, one on each
different leg, with actual member bolts and separate foundation attachment groups.

S1/S2 source hashes and actual reviewed locators, exact native call boundaries and separate qualified response/capacity scopes are recorded in the integration note. Section 8.4 is not treated as an anchor/contact solver. No licensed PDF, new universal heel/prying equation or production test source is added.

See [native integration/source boundaries](../engineering/STAGE_4_4_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md)
and [96-requirement QA catalogue](../qa/STAGE_4_4_ANGLE_COLUMN_MOMENT_BASE.md).
The exact implementation subject is `feat: add angle-column two-leg moment base connection`;
normal expected count 115. Local, browser and fresh object-isolated QA precede the
normal non-force main push; direct four-job CI follows it. Future CI is not inferred.
All eleven existing freeze tags remain immutable. Owner final visual/result acceptance
is PENDING; no Stage 4.4 freeze, Stage 4.5 or 316SS expansion is authorized.

## Stage 4.5 RC1 authorized successor

`WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION` / `4.5-RC1` starts from the accepted
Stage 4.4 freeze `99befa9780e7c7abf72c8a33e5eb45b9e368d916` (118 commits).
The owner-approved Stage 4.5 order and 120-requirement acceptance matrix authorize
W/I, hollow rectangular/square and solid rectangular/square columns, each with
TWO_X, TWO_Y and FOUR_XY arrangements. They supersede the preceding historical
handoff's prohibition on beginning Stage 4.5, not its engineering authority.

Source PDFs remain externally held. ASCE/SEI 74-23 SHA-256:
`A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`;
Erratum 1 SHA-256:
`5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`.
No licensed PDF or synthetic production qualification is registered.

See [native integration and source boundaries](STAGE_4_5_NATIVE_INTEGRATION_AND_SOURCE_BOUNDARIES.md)
and the [120-requirement evidence catalogue](../qa/STAGE_4_5_COLUMN_MOMENT_BASES.md).
All twelve historical freeze tags and native methods remain unchanged. Complete
base response, coupled shaft/receiving-layer participation, connector/member
attachment and common column-end-zone qualification remain distinct. No fixed
half/quarter split, cavity material, internal RHS hardware, automatic multi-plane
capacity, solid thin-plate approximation, universal prying or anchor capacity is
introduced. Stage 4.5 owner final visual/result acceptance remains PENDING.

## CME-2B isolated stainless authority — RC1 R1

Final ANSI/AISC 370-25 (December 8, 2025), SHA-256 `A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1`, controls only the approved C2-M/P1 flat-product methods. Relevant locators: B4.2a, B4.4b, D3, J3.2-J3.5, J3.10a, J4.1-J4.3. Owner-approved conservative 25/70 ksi U.S.-source properties, A240/A240M-24 / A480/A480M-24 chain and ASCE FRP/AISC stainless bridge are bound to the additive isolated method, never to frozen hardware or FRP providers. AISC 360-22 is comparison-only; corrected SHA-256 `6B1322440EEDAA0B82D617811DC4B2A2657E7492CF9067CBB3DEBDF9E610ABB7`.

See [registered controlled artifacts](../governance/ARTIFACT_AND_VERSION_REGISTER.md) and [provider/source boundaries](../architecture/CME_2B_ISOLATED_STAINLESS_PLATE_PROVIDER.md). Licensed PDFs remain outside the repository. No synthetic test source is production qualification; response/family activation remains unavailable.

## CME-2C C2-P2 isolated implementation

Additive internal clear-plate E3/F9/H2 provider from baseline `20fabefa90247dd3470d4698edda1b22d017e7c6` (128). See `docs/architecture/CME_2C_ISOLATED_CLEAR_PLATE_PROVIDER.md` for trusted pre-resolved frozen C2-M/P1 snapshots, the owner-approved raw-traced E3 Fy cap, native numerical authority, fail-closed boundaries and publication gates. Frozen production/tests and all fifteen tags remain unchanged; no public API, frontend, hardware or family material activation. One implementation commit is expected at count 129; exact-SHA hosted four-job verification is recorded externally after normal push. No new freeze tag or later-stage work.

## CME-2 core RC1 additive source registration

The [approved seven-artifact index](../architecture/CME_2_CORE_ISOLATED_RESPONSE_ANGLE_TEE.md) controls isolated C2-R/A/T only: final ANSI/AISC 370-25 SHA-256 A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1 and inherited ASCE74 interface applicability. A276/A484 unwelded hot-rolled/extruded 316-family source qualification is required; no catalogue or synthetic test source is registered as production qualification. Existing frozen C2-M/P1/P2 source entries remain unchanged.
