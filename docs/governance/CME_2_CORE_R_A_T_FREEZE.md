# CME-2 Core C2-R/C2-A/C2-T isolated stainless provider freeze

## Identity and acceptance

Status: accepted implementation scope freeze, subject to the publication gates below. This is not whole-connection stainless approval or public family activation.

- Accepted implementation: `1d730c70bc446901452f2eacecd9df3f9f36ff4b`, count 131.
- Subject: `feat: implement CME-2 core stainless response angle tee providers`.
- Parent frozen governance baseline: `88961da28de3421722290c2bf78af0c6191b81a1`, count 130.
- New annotated tag: `cme-2-core-r-a-t-freeze`.
- Annotation: `Freeze CME-2 core C2-R/C2-A/C2-T isolated stainless providers`.
- Tag object: `4729e0996ef7ff07144d88050c667691221017ef`; peeled target is exactly the accepted implementation, NOT the governance successor.
- All sixteen prior tag objects and peeled targets remain unchanged. Expected published total: seventeen.
- Controlling order: `FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_IMPLEMENT_ACCEPT_FREEZE_CODEX_ORDER.md`; computed SHA-256 `20823818AD5BC9D8DC36B516A98FD6D12BE4D5FFED42F59B8959882A348ED158`.
- External implementation report SHA-256: `6F6326AE4D40056094FBBCFF4F02998EBC641D4CFB9D4F6CBA3DF3A9A514213B`.
- Acceptance classification: `CME_2_CORE_R_A_T_ACCEPTANCE_PASSED`.
- External `CME_2_CORE_R_A_T_ACCEPTANCE_REPORT.md` SHA-256: `E7C1353BB001D08DA22F0AE66EC3DE1AA8CAD9EE58E7E5B34791042F57544B57`.

External reports and licensed PDFs are not imported. Historical engineering artifacts and prior freeze records are not rewritten.

## Accepted evidence

Implementation full QA: 5,705 backend tests, 855 frontend tests, configured coverage 100%, Ruff/format, strict mypy, ESLint, TypeScript, production build, dependency/governance checks PASS, full/runtime npm audits zero.

Direct implementation CI: workflow CI, #126, run 34741571531, attempt 1, exact accepted implementation SHA, overall SUCCESS. Backend Ubuntu SUCCESS 11m44s; Backend Windows SUCCESS 12m57s; Frontend Ubuntu SUCCESS 8m5s; Frontend Windows SUCCESS 8m32s. Total 13m0s; artifacts none; rerun none. This is not a substitute for governance CI.

Read-only acceptance: 809 targeted tests passed; 24 positive goldens, 27 fail-closed negatives and 16 invariants; independent Decimal numerical checks; nine fingerprint mutation categories; 43 exact frozen C2-M/P1/P2 outputs/fingerprints; 67 exact parent responses; 16 public routes and 39 connector bodies (21 angle/16 plate/2 Tee); focused browser/CDP smoke. Historical Tee default HTTP422 remains exact and explicit; it is not a successful default preview.

## Immutable artifact index

Resolve identities at the accepted implementation Git object, not mutable successor HEAD. Working copies and committed blobs were verified against approved hashes.

| Repository path | SHA-256 |
| --- | --- |
| `docs/engineering/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_SOURCE_AND_METHOD_RECONCILIATION_RC1.md` | `D47C1F5E62D17289A810D7AE0DBC824C44B4BC3A2BB4F1C4B2D0543740E5180E` |
| `docs/engineering/FRP_MASTER_CONNECTION_CME_2_C2_R_ENGINEERING_SPECIFICATION_RC1.md` | `498A6A44975A223BE2ACE05F26437B5999391363B5BA2DB60401646AA020E9E7` |
| `docs/engineering/FRP_MASTER_CONNECTION_CME_2_C2_A_ENGINEERING_SPECIFICATION_RC1.md` | `5A445189AB05D95F61A27A92F74C9C71373E864521DA894033A2D27E4ED0D0C1` |
| `docs/engineering/FRP_MASTER_CONNECTION_CME_2_C2_T_ENGINEERING_SPECIFICATION_RC1.md` | `A8230832154D961166F8BA006AB55B895C8B70FF76C354DD13B96826D804E380` |
| `backend/tests/golden/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_GOLDEN_BENCHMARKS_RC1.json` | `E89748C24CB53E25C559A7BAD2C02E442FD8A05A72DE308CA14826698C6C1938` |
| `docs/qa/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_RC1_INDEPENDENT_VALIDATION.md` | `C2EAE5CC55E0EC98DA00724DDF5D2A595BF74CBCF7361EBD42E32B936CE63B95` |
| `docs/governance/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_OWNER_APPROVAL_RECORD_2026-09-12.md` | `1A0738114280E0F84BB31E23FC604763A2AA4005FA93EABF269371011EB6CA08` |

Implementation-pinned executable authority comprises four new modules under `backend/src/frp_master_connection`: `domain/stainless_shape.py`, `calculation/stainless_response.py`, `calculation/stainless_angle.py`, `calculation/stainless_tee.py`; the four new response/angle/Tee/isolation tests and `docs/architecture/CME_2_CORE_ISOLATED_RESPONSE_ANGLE_TEE.md`. All remain unchanged by this freeze.

## Owner/EOR clarification and whitespace authority

Original I11 wording is superseded: H2 compression is nondecreasing in each positive demand term. Increasing tensile Pr increases H2-1 and decreases H2-2; both equations remain exact and their maximum governs. There is no global tensile-Pr monotonicity requirement. The independent decrease 0.457774159751 to 0.442230747487 is expected. I11 is replaced, not deleted; all other fifteen invariants and every approved benchmark value remain unchanged. Original artifacts retain their approved bytes.

Exactly `docs/qa/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_RC1_INDEPENDENT_VALIDATION.md` lines 4 and 5 retain approved Markdown hard breaks. SHA-256 remains `C2EAE5CC55E0EC98DA00724DDF5D2A595BF74CBCF7361EBD42E32B936CE63B95`. Every other new whitespace finding is forbidden. No Git/configuration/checker policy is weakened.

## Frozen numerical, product and response scope

Providers:

- `C2_R_TRUSTED_STAINLESS_RESPONSE_ENVELOPE_RC1`.
- `C2_A_AISC_370_25_A276_A484_HOT_SHAPE_LRFD_RC1`.
- `C2_T_AISC_370_25_A276_A484_HOT_SHAPE_LRFD_RC1`.

Owner/EOR policy remains unwelded hot-rolled/extruded ASTM A276/A276M plus A484/A484M 316-family angles/Tees, finish A or HF, conservative Fy25/Fu70/E28000/G10800 ksi. Trusted actual product/section records are required; no nominal catalogue or client-created source qualification.

C2-R validates bounded server-owned response envelopes. It reuses proven material-neutral transport, exact prescribed ASCE FRP-steel row fractions, trusted native stiffness/symmetry evidence and qualified material-specific response. Unique physical shaft identity, ordered layer vectors, cumulative cuts and terminal closure remain exact. Source-total tension already including prying is never augmented again. It does not solve unknown stiffness/contact or compute fastener/foundation capacity.

C2-A/T preserve D2/D3 tension, all four G6 zones, both-axis E3 and source-provided E4 elastic stress, all three F10 branches and complete H2 compression/tension. Every Curve-A use retains raw Fn and uses min(Fy,raw). F10 stability input requires trusted provenance. Both H2 tension equations remain visible, with the larger governing. Unsupported fabrication, slenderness, torsion, normal-plus-shear interaction, unequal-angle compression and unqualified local heel/junction/prying remain fail closed.

Local P1/P2 information is consumed only as a trusted pre-resolved body/region/request/source-bound snapshot. Frozen C2-M/P1/P2 modules and tests are unchanged and not production-imported by the core. Native numerical boundaries and physical/source fingerprints remain exact.

Final AISC 370-25 controls bounded stainless methods; ASCE/SEI 74-23 plus Erratum 1 remain FRP/interface authority. AISC 360-22 remains comparison-only. No source equation, property, factor or frozen authority changes in this governance commit.

## Public isolation and exclusions

All sixteen native routes and thirty-nine connector bodies remain unchanged. Primary members remain FRP-only. Public SS316 plans remain unavailable with the exact frozen provider-not-implemented boundary; no public core capacity/utilization, API endpoint, editor selection or family import is activated.

Connector-body, fastener and foundation authority remain separate. Native F593/F594/thread/grip/washer behavior is unchanged; anchor/concrete/foundation capacity remains external. Exact required foundation actions are not invented individual anchor forces.

No CME-3, welding/built-up/laser/formed-shape expansion, CSM, unknown contact/prying/stiffness solver, unsupported torsion/H3, automatic E4 eigenvalue or F10 stability solver, public 316SS family activation, frontend/dependency/workflow change or global stainless connection PASS.

## Governance and publication gates

This eight-path governance-only successor mirrors the established CME-2B/C2-P2 pattern. Subject: `chore: record CME-2 core C2-R/C2-A/C2-T freeze`; expected count 132. No amendment or production/test/golden/dependency/workflow/lockfile edit.

Before staging, complete integrated local QA again, JSON/governance consistency, all controlled hashes, exact whitespace verification and full diff review must pass. Explicit-path staging only. Push main normally with implicit tag following disabled, then only `refs/tags/cme-2-core-r-a-t-freeze`. Verify synchronized main, annotated/peeled tag and all sixteen prior tags.

Governance CI remains pending until direct exact-pushed-SHA inspection proves overall SUCCESS and all four Backend/Frontend Ubuntu/Windows jobs PASS. Actual governance SHA/count, local QA, publication and hosted evidence are recorded externally in `CME_2_CORE_R_A_T_COMBINED_COMPLETION_REPORT.md`; no circular self-hash or unverified CI assertion is introduced.
