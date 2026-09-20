# Stage 4.1A W/I Major-Axis Moment Splice Freeze

## Control and accepted baseline

The controlling order was read completely before repository action. Its SHA-256 is
`0646F456A035C0A2C09492AFF4A59B4A4A8D8E665B346F1DC7B16443D79A3290`, and its final
sentinel is present. The accepted clean synchronized `main` product baseline is
`59713e53c522a6a301e19e458559986fb114d735`, subject
`feat: add W/I major-axis moment splice connection`, commit count 98.

The accepted chain is Calculation Slice 5 commit
`23813a5c2d015b74591e577fa95715950c34912c` followed by Stage 4.1A commit
`59713e53c522a6a301e19e458559986fb114d735`. GitHub Actions runs #92 and #93 each
passed Backend Ubuntu, Backend Windows, Frontend Ubuntu, and Frontend Windows in
approximately 5m26s and 6m05s. Owner acceptance is complete for the default combined,
negative-moment, pure-axial, and pure-moment scenes and the prescribed engineering,
hardware, status, source, and workflow invariants.

## Immutable identities

- `backend/src`: `70dca07ca9fac3bbc45b8363f0d5f21157a1bc52`
- `frontend/src`: `7deabca069f034e7f43f426ba31d7dca0c839419`
- workflows: `20edd491455e6329c4565bc72cd7b88e29d3f7b1`
- `docs/engineering`: `3bcf35139e636ce052f6082a59b4748752e5edda`
- `backend/tests/golden`: `3098c9113af244d04a0930dcecc31e70bc061a9d`
- `backend/requirements`: `d8e1a9f1c2c89a4e50a181db1997c52b3c9bdf58`
- backend project SHA-256: `39BEA635FCE709607E1A4AE11D8B31829DFD07B4CADE332E030486BE1456A116`
- backend lock SHA-256: `953E6D3F6879CBAA6037AA4E8BA0D41B48380761983DCA4CDABFE54576670E0E`
- frontend package SHA-256: `1085F25B94819ED98EEE10739CF4B419F39BD626CC654699B0380B26341F4359`
- frontend lock SHA-256: `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254`

All seven pre-existing annotated freeze tags were verified locally and remotely before
mutation. Their tag objects and peeled targets remain immutable.

## Frozen scope and limitations

The frozen product is `WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE` under `4.1A-RC1`, W/I only,
with signed axial, major shear, and major-axis moment. Calculation Slice 5 complete
top-flange/web/bottom-flange wrenches remain authoritative; web moment and flange-local
moments are retained, exact equilibrium is mandatory, and `M/z` is reference-only.

Each flange has one full-width outer FRP plate and two symmetric split inner strips;
the web has two symmetric plates. Every flange common bolt follows one continuous
outer-plate / beam-flange / corresponding-inner-plate path with two independently
loaded shear planes and exterior hardware. The accepted balanced force-line,
proof-gated inner split, rational face-sublayer, unequal-plane bolt, Calculation Slice 4
body, local FRP, and inherited Stage 3.6 web methods remain exact.

Bolt-axis force is zero under supported actions. Prying, secondary bolt bending,
stiffness, rotation capacity, and full-strength classification remain unevaluated.
Ordinary PASS is prohibited; complete supported success is
`PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED` with mandatory Section 2.3.2 qualification
and disclaimer `WI_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1`. ASTM F593
strength remains source-pending where controlled `F_nt/F_nv` is unavailable.

## Deterministic manifest and successor-safe audit

Manifest `docs/governance/STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_FREEZE_MANIFEST.json`
has SHA-256 `A77FACD1A05F60E947F3F394FCFB3FC5D28120922BF6EA9841E4EC9C80D4061F`. It inventories
4 Stage 4.1A artifacts, 4 Slice 5 artifacts, 38 inherited authorities, CI/owner evidence,
physical and engineering contracts, exact source/package/lock/workflow identities,
fingerprints, historical tags, and successor policy.

Audit `backend/tests/calculation/test_stage_4_1a_freeze_manifest.py` resolves exactly:

- `tag`: peel the immutable annotated Stage 4.1A tag and audit historical content;
- `object`: audit only an explicitly supplied exact freeze commit;
- `manifest_only`: authenticate pinned bytes, contracts, fingerprints, and limitations
  without treating successor `HEAD` as history.

Freeze-object parent proof reads the raw commit header with `git cat-file -p`. The audit
performs no fetch and uses no object alternates.

## Tamper-negative coverage

The audit rejects altered manifest bytes, source/dependency/workflow identities,
controlled artifacts, baseline/scope/topology, flange bolt path, sole-control `M/z`,
discarded web or branch moment, weakened symmetry or sublayer rules, equal-plane or
blind-capacity assumptions, invented prying or F593 strength, ordinary PASS, changed
status/qualification/fingerprints, wrong explicit objects or peeled tags, and automatic
successor-HEAD substitution.

## Change declaration and verification

Production-source changes: `0`. Engineering-method changes: `0`. Controlled engineering-
artifact changes: `0`. Dependency changes: `0`. Workflow changes: `0`. Existing-tag
changes: `0`. Only governance, documentation, and the freeze audit are authorized.

- Focused manifest audit: 35 passed before tag creation with `manifest_only` resolution.
- Complete local integrated QA: 2,845 backend tests passed at configured 100-percent
  coverage over 22,789 statements and 6,230 branches; 582 frontend tests across 40
  files passed at configured 100-percent coverage over 4,414 statements, 3,735 branches,
  1,553 functions, and 3,253 lines. Ruff, strict mypy, ESLint, strict TypeScript,
  production build, dependency consistency/tree, JSON/whitespace, runtime/CLI smokes,
  and both zero-vulnerability audits passed.
- Fresh depth-one, no-tags, no-alternates object-isolated QA: pending governance commit.
- Explicit historical-object mode: pending governance commit.
- Post-tag `source='tag'` audit: pending annotated tag creation.
- Freeze-commit hosted CI: pending direct 4/4 evidence after publication.

Stage 4.1B Channel Moment Splice and every later moment family were not begun.
