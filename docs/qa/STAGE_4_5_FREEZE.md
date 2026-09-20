# Stage 4.5 W/I, RHS and SRS column moment bases freeze

## Authority and accepted lineage

See [stage-specific artifact register](../governance/STAGE_4_5_FREEZE_ARTIFACT_REGISTER.md) and [freeze manifest](../governance/STAGE_4_5_WI_RHS_SRS_COLUMN_MOMENT_BASES_FREEZE_MANIFEST.json), SHA-256 `4ACF09E480FF843E7700FD580EFFF347611DCD523E93C523381E8D51A5EB1B4E`.

The accepted engineering implementation is `45d4a13590f4551926cae5762982284dfd6dc591`; corrected product baseline is `36f4979e2a4e1ef4cf144c9640974614e18bce03`; tests-only timing successor is `7e81a64d587d5dcfaa13b0936de2b6aabe95a8a5`. Product CI #117 attempt 1 is four-job SUCCESS. Owner acceptance is **Stage 4.5 visual accepted**, including visual/result review. It is not re-requested for this governance-only freeze.

## Preserved product

All nine W/I, RHS and SRS TWO_X/TWO_Y/FOUR_XY modes remain accepted. Units has exactly U.S. Units and S.I. Units. Separate shape choices are W/I Shape Column, Hollow Rectangular Tube and Solid Rectangular Tube; layout remains independent and dimensions editable. Nominal-size names remain historical fixture identifiers, not production controls.

Every generic active angle defaults to two horizontal member bolts (2 across / 1 along) and one foundation attachment (1x1). Count-one gauge/pitch controls are N/A/noncontrolling. Zero tangential extrusion offset centers the angle on its actual selected face's geometric tangential centerline, including column translation. Signed user offsets and U.S./SI round-trip remain exact.

Unique physical member-shank counts for TWO_X/TWO_Y/FOUR_XY are W/I 2/4/6 and RHS/SRS 2/2/4. Each active angle has two member-bolt bindings, with no duplicate shared shanks or inactive hardware. Foundation counts are 2/2/4. Accepted W/I web/flange paths, RHS near-wall/cavity/far-wall exterior hardware and continuous solid SRS paths remain unchanged. Cavity is not material; a full solid section is not a thin wall. FOUR_XY perpendicular families retain elevation staggering and collision clearance.

Signed N/Vx/Vy/Mx/My and reference-generated Mz remain in the exact required total foundation wrench, counted once. Independent input torsion remains outside RC1. Connector count, mirrored geometry, hollow-wall penetrations and opposite faces do not establish half/quarter sharing, equal-wall participation or double-shear capacity. Complete branch/contact/shank response requires applicable qualified complete-base-response authority. Missing demand remains unavailable, not zero; individual forces are not fabricated. Direct column-end contact is separate, and compression sign alone does not establish active contact. Anchor/concrete capacity and whole-column strength/stability remain external/not evaluated.

Each accepted native engine (Slice 7, Slice 8, Stage 2.5A and applicable local consumers) controls its own numerical output. No tolerance, normalization, residual redistribution or recreated second numerical path is introduced. Synthetic qualification remains test-only.

Frontend remains presentation-only: backend geometry/fingerprint, exact signed action record for labels/vectors, explicit design and source traces. Invalid current input never fabricates current geometry; LAST VALID is explicit, noncurrent arrows are hidden, validation reasons remain visible, recovery is automatic and latest-response-wins protection remains intact.

## Consolidated audit and bounded maintenance

The single exhaustive pre-mutation sweep passed all baseline gates: 5,021 backend / 848 frontend, 100% coverage, Ruff/strict mypy/pip, ESLint/strict TypeScript/build, dependency validation and zero full/runtime audits. Full suites include 120 acceptance requirements, 24 independent fixtures, 360 source-absent and 90 source-present integrations, all nine modes, centered/translated/signed-offset/unit tests, action-sign/preview tests, Slice 7/8, Stage 2.5A and historical freeze regressions. No production defect or new security/timing issue was found.

The known historical/current scope guard rejected a new freeze manifest in an in-memory probe. Under section 14, exactly two test files were corrected in `8c8c26afdc80910889e09a5ddcdf86c5eb8a89f0` (123), subject `test: make Stage 4.5 freeze guards successor-safe`. Twenty-four added cases prove only seven named new governance paths are admitted; original digests, historical tamper detection, protected unrelated current paths and all twelve tags remain exact. Full local and isolated QA passed 5,045 backend / 848 frontend tests at 100% coverage and all static/build/security gates.

Direct maintenance CI #118 attempt 1:
- [Backend Ubuntu](https://github.com/baraa-misto/frp-master-connection/actions/runs/34623338109/job/103342360646): SUCCESS, 8m 24s.
- [Backend Windows](https://github.com/baraa-misto/frp-master-connection/actions/runs/34623338109/job/103342360649): SUCCESS, 10m 20s.
- [Frontend Ubuntu](https://github.com/baraa-misto/frp-master-connection/actions/runs/34623338109/job/103342360320): SUCCESS, 6m 50s.
- [Frontend Windows](https://github.com/baraa-misto/frp-master-connection/actions/runs/34623338109/job/103342360614): SUCCESS, 8m 36s.

The owner resolved the sole artifact-registration discrepancy by explicitly authorizing byte-preserving R1/R2/R3 copies under docs/governance. All repository-copy SHA-256 values and canonical blob bytes match the approved sources. No controlled engineering content was changed. Preserved obsolete drafts in other worktrees remain untouched.

## Governance verification and publication

Normal governance scope is exactly seven NEW docs/governance/QA paths. Zero existing files, production, engineering, tests, dependencies, lockfiles, workflows or existing tags change. The stage-specific register supplements historical aggregate records rather than replacing their frozen whole-file identities.

Repeat complete local QA on this candidate and again in a fresh depth-one/no-tags/no-alternates clone of its exact commit. Require 100% configured coverage; Ruff/strict mypy; pip/dependency checks; ESLint/strict TypeScript/build; both audits zero; all acceptance/fixture/sweep and inherited freeze tests; JSON, whitespace, manifest/register integrity and a clean tree.

The external read-only verifier authenticates the manifest SHA-256 and its historical-entry digest, reconstructs the exact historical Git tree, tests tampering, checks controlled artifact canonical bytes and all available tag pins, and proves the governance commit only adds the seven registered paths. Historical object verification uses raw commit headers, never shallow-boundary parent traversal. Tagless manifest-only verification must not substitute successor HEAD for unavailable frozen authority; explicit-object and annotated-tag modes resolve the actual frozen governance object. Git status/diff establishes checkout cleanliness; canonical committed bytes come from Git blobs, not CRLF-transformed working-tree assumptions.

Governance subject: `chore: freeze Stage 4.5 W/I RHS SRS column moment bases baseline`. Expected parent `8c8c26afdc80910889e09a5ddcdf86c5eb8a89f0`, expected final count 124. No amendment to accepted prior commits. Normal non-force main push follows isolated success. Only after direct governance hosted Backend Ubuntu/Windows and Frontend Ubuntu/Windows SUCCESS may the annotated Stage 4.5 tag be created and pushed. Verify local/remote tag object and peeled commit.

Actual final QA logs, commit/refs, hosted run/job results, tag object/peeled target and clean state are captured externally after they occur; accepted product/maintenance CI is not represented as CI on the future governance commit. Final frozen scope excludes 316SS, later families, generalized unqualified contact/sharing, full foundation/column capacity and stiffness/rotation/full-strength classification.
