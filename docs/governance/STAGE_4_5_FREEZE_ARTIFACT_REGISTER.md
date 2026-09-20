# Stage 4.5 freeze artifact and acceptance register

This stage-specific register supplements the historical aggregate registers without rewriting their frozen content. For Stage 4.5 current acceptance and freeze publication only, it supersedes earlier PENDING/not-yet-authorized status text. It does not supersede any historical engineering authority.

## Accepted identities

- Engineering implementation: `45d4a13590f4551926cae5762982284dfd6dc591` (119).
- Accepted UI/default/centering correction: `36f4979e2a4e1ef4cf144c9640974614e18bce03` (121), following R1 `636cfd133c3f88a09c22063d6428713fa818cb3d` (120).
- Tests-only Windows timing successor: `7e81a64d587d5dcfaa13b0936de2b6aabe95a8a5` (122).
- Owner final visual/result acceptance: **Stage 4.5 visual accepted**.
- Product CI #117 attempt 1: Backend Ubuntu/Windows and Frontend Ubuntu/Windows SUCCESS; 5,021 backend / 848 frontend tests, 100% configured coverage, zero full/runtime audit findings.
- Authorized tests-only freeze-scope successor and actual pre-freeze baseline: `8c8c26afdc80910889e09a5ddcdf86c5eb8a89f0` (123).
- Maintenance CI #118 attempt 1: all four jobs SUCCESS. Complete local and depth-one/no-tags/no-alternates QA: 5,045 backend / 848 frontend, 100% coverage, static/build/security PASS, both audits zero.

## Controlled artifacts

The original order and acceptance matrix remain unchanged. The owner explicitly authorized archival of the three Downloads successor orders, byte-for-byte, with no rewrite, formatting or line-ending normalization. Repository-copy hashes and raw/canonical Git blob identities match.

| Repository path | Approved SHA-256 |
| --- | --- |
| `docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_CODEX_ORDER_RC1.md` | `6D6CCA01C8AE979BF00F369D6D36317AE98E41BC8BF0F2DA4020F429B1614135` |
| `backend/tests/golden/stage_4_5_acceptance_matrix_rc1.json` | `68695DFC75C51E85982ED07E76ED7A4D0B344F1CCE7AE4425A9842260967074D` |
| `docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_UI_DEFAULTS_AND_ACTION_RENDERING_CORRECTION_ORDER_R1.md` | `06EEA4B207E55763C522622F148938EA5F006C51124B33CD8A532A06C07B693C` |
| `docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_CENTERED_ANGLES_AND_TWO_BOLT_DEFAULT_CORRECTION_ORDER_R2.md` | `4E9663E11EE3654FC5B46FC1D28BD68D10ACEA4F30418DF41906911C4A024D58` |
| `docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_WINDOWS_FRONTEND_TIMING_CORRECTION_ORDER_R3.md` | `59B466EFB3621AC442B3FC926FD1D2035BBCD7C2B6AF513D5B42A29DEF19288D` |
| `docs/governance/FRP_MASTER_CONNECTION_STAGE_4_5_FREEZE_CODEX_ORDER.md` | `3296113BA1AEC00F13811401A4B81A1CD1AA8A807644C027CEFC912A7A8DCFA3` |

The controlling freeze order's final sentinel was verified. The archive clarification changes only the storage/registration of existing approved authority, not engineering behavior.

## Freeze manifest and publication gate

Manifest: `docs/governance/STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_FREEZE_MANIFEST.json`.

SHA-256: `4ACF09E480FF843E7700FD580EFFF347611DCD523E93C523381E8D51A5EB1B4E`.

The manifest seals all 818 pre-freeze Git entries and all twelve existing annotated-tag objects/peeled targets. Stage 4.4 remains at `99befa9780e7c7abf72c8a33e5eb45b9e368d916`. No existing file is modified by this governance commit; its exact seven added paths are listed in the manifest.

Governance SELF has parent `8c8c26afdc80910889e09a5ddcdf86c5eb8a89f0`, subject `chore: freeze Stage 4.5 W/I RHS SRS column moment bases baseline`, and expected count 124. Stage 4.5 becomes FROZEN only after complete governance local/object-isolated QA, normal main push, direct governance hosted 4/4 SUCCESS, and verified publication of annotated tag `stage-4.5-wi-rhs-srs-column-moment-bases-freeze`, annotation `Stage 4.5 W/I RHS SRS column moment bases freeze`, pointing to SELF.

Actual governance commit/CI/tag identities are reported externally after those gates occur, without amendment or circular self-hashing. See [freeze QA record](../qa/STAGE_4_5_FREEZE.md). No 316SS or later-stage work is authorized.
