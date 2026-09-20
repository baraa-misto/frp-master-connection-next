# Stage 3.3C2-R1 Preview Integration Correction

## Authority and baseline

The controlling external order was read completely and verified at SHA-256
`57856A56EE83B0AFCF0B8C181B59E156E1111101B70CCE9D0139956DCAD34566`, including its
final sentinel. Work began from clean synchronized `main` commit
`eda492fa6ebab89bd8ef4f54ed595ebd787b6b1c` with both immutable freeze tags exact.

## Pre-mutation diagnosis

The exact Tee workspace C2 request selected the connected RHS `Y_POS_FACE` with
`Y_NEG_FACE` opposite, 4-inch width, 0.5-inch walls, 3-inch cavity, and a 0.375-inch Tee
stem. It failed HTTP 422 before full-through composition because Interface A called the
historical same-wall `resolve_profile_wall_bolt_path` path. That resolver was correct for
legacy contracts but cannot represent the authorized C2 near-wall/cavity/far-wall path.

All five required Single Clip-Angle profile/support probes returned HTTP 200 and real
backend geometry, but the response constructor hard-coded `3.3A-RC1`. The frontend
correctly required current `3.3C2-RC1`, so its strict response guard rejected otherwise
valid previews. There was no frontend geometry or state-authority defect.

## Correction

Only exact current C2 Tee RHS Interface A bypasses the legacy connected-member
single-wall layer; the existing rectangular full-through builder then composes Tee stem,
near RHS wall, free cavity span, and far RHS wall on one axis and one shank. Older Tee
contracts still use the accepted same-wall resolver. Single Clip-Angle preview/design
results now echo the validated request contract version. Unknown future versions still
fail closed in strict backend and frontend guards.

The full-through result retains two independent exterior-face containment results,
external-only hardware, zero internal hardware, and trim-compatible hollow geometry.
No production frontend file changes.

## Engineering and regression evidence

There is no engineering transition. Exact current fingerprints remain:

- Tee C2 RHS: `a089c44a4652b207ff1145d8a5790154855c1078cf006a6022c8d649f947a6f9`
- Single-Angle C2 Brace RHS: `16ae7ce854c5b5b4d34da713373bcf5924f5fc411687e5dc0a765928e5db3288`
- Single-Angle C2 Beam RHS: `1c995ab0e90b76cd405bff1c5f4990bef2fdbba83e12daac47dffd9fbace7c51`
- Legacy Tee R8 RHS: `9269fc498a1c350089002518d325764dad6535900329e38702aeb7a5004c89f3`
- Legacy Single-Angle Brace RHS: `8228c0573f32282cc00097d9ab037538abca29518a3b5f97c568abf4a8a31d33`
- Legacy Single-Angle Beam RHS: `2c168d03538ec9a98e996141fd9e8cf07b1588e7a4cf246562a2f7fa3c3ae563`

C1 G1-G12, C2 G1-G18, Direct, non-RHS frozen Tee, Stage 3.3A, Stage 3.3B, one-bolt,
material-axis, placement, trim, preview-state, and freeze regressions remain green.

## Local QA

- Backend: 2,285 tests passed; Ruff format/lint, strict mypy, dependency and runtime
  checks passed; exact 100% coverage over 16,598 statements and 4,986 branches.
- Frontend: 376 tests in 26 files passed; ESLint, strict TypeScript, and production build
  passed; exact 100% coverage over 2,541 statements, 2,201 branches, 854 functions, and
  2,074 lines.
- Dependencies changed: zero. Workflows changed: zero. Freeze tags changed: zero.
- Integrated QA passed, including clean bootstrap, both zero-vulnerability audits,
  JSON, whitespace, dependency, build, controlled-hash, and freeze checks.
- The staged backend tree is `b679181fef86b9f3598dcb82efdd1e34a1f7cbc6`; the staged
  frontend tree is `17f6614ab521313127e6c7fccd89826d5736be9d`; and the unchanged
  frontend production-source tree is `abf01a3941c320bcf347e05fc9c0cce582767120`.
- Object-isolated, push, hosted CI, and visual evidence are recorded only after their
  respective gates. Hosted CI and visual acceptance are not inferred.

Stage 3.3C3 is not started.
