# Stage 3.6 W/I Web-Splice Family Freeze

## Freeze identity

- Accepted product baseline: `5f77abd0eeaf61718756e9962ae3a5a67d6db528`.
- Accepted chain: Stage 3.6A `80df7524417c752ab3c0f6194348e72aff40767a`,
  Calculation Slice 4 `a93aa5d127a51dc81a6c7cd108af15c44d59ff9f`, and
  Stage 3.6B RC2 `5f77abd0eeaf61718756e9962ae3a5a67d6db528`.
- Governance commit subject: `chore: freeze Stage 3.6 W/I web-splice family baseline`.
- Expected governance commit count: `93`.
- Authorized annotated tag: `stage-3.6-wi-web-splice-family-freeze`.
- Tag annotation: `Freeze accepted Stage 3.6 W/I Web-Splice Family baseline`.
- Controlling freeze order SHA-256:
  `B3D43B7D492A4CD538029EEFD59CC0B86FF318C18B82842464E59E6B89AE8E69`.
- Deterministic manifest SHA-256:
  `58AA05F545984EAAC0EDED666B4BA086BA05ADE40E59C39D3B7821BFFEB60658`.

## Accepted evidence

The accepted product chain has direct hosted evidence: Stage 3.6A GitHub Actions run
#85 rerun attempt 2 passed all four Ubuntu/Windows backend/frontend jobs without a
repository correction; Calculation Slice 4 run #86 passed 4/4 in approximately 4m48s;
and Stage 3.6B RC2 run #87 passed 4/4 in approximately 4m30s. The owner directly
accepted the W/I-only geometry, action, material-axis, rational body-interaction,
qualification/disclaimer, physical double-shear, source-pending, limitation, and
result-precedence behavior recorded in the controlling order.

## Frozen scope and limitations

This freeze covers only the symmetric W/I double-web-splice family: two locked-identical
collinear W/I beams, positive end gap, two mirrored flat FRP web plates, two distinct
mirrored Plate/Web/Plate groups, signed axial/major/minor force, and zero user-applied
moment. It preserves `3.6A-RC1`, Calculation Slice 4, and `3.6B-RC2` exactly.

The controlled rational body method remains
`RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1` over panel
`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`, with Section 2.3.2 qualification,
engineer-of-record review, and disclaimer
`WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1`. Supported numerical failure
governs `FAIL`; supported completion may only be
`PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`, never ordinary prescriptive PASS.

Physical common-bolt double shear requires a proved two-plane Plate/Web/Plate path and
the actual Stage 2.5A per-bolt vector. ASTM F593 remains `SOURCE_DATA_PENDING` without
explicit verified/custom strength authority. Minor-shear bolt-axis response remains
`NOT_EVALUATED`; user flexural moment remains `NOT_AUTHORIZED_IN_RC1`.

`CHANNEL_WEB_SPLICE = NOT_IN_STAGE_3_6_FROZEN_SCOPE`. A Channel centroid/reference axis
is generally offset from its web plane, so Channel support requires a separate successor
with explicit reference-axis/web-splice eccentricity and transfer-moment authority. No
Channel contract, equation, artifact, or product exposure is created here.

## Successor-safe audit

`backend/tests/calculation/test_stage_3_6_freeze_manifest.py` resolves the historical
freeze in exactly three modes:

1. `tag` — peel the annotated Stage 3.6 tag and audit that object;
2. `object` — audit only an explicitly supplied historical object; and
3. `manifest_only` — validate the immutable manifest, authorities, identities,
   fingerprints, limitations, and policies without inventing a historical object.

Parent identity comes from the raw commit object header, not shallow-sensitive
`git show --format=%P`. The resolver never substitutes successor `HEAD`, performs no
network fetch, and requires no object alternates. Negative tests reject changed manifest
bytes, source/dependency/workflow identities, each controlled authority group, baseline,
rational method or panel, disclaimer identity or meaning, F593 boundary, Minor/moment
limitations, Channel inclusion, fingerprints, wrong explicit objects, wrong tag targets,
and successor-HEAD substitution.

## Change declaration

This freeze changes zero production source, calculation method, controlled engineering
artifact, dependency, workflow, existing tag, result, or fingerprint. The manifest and
audit are additive governance/reproducibility records. All prior freeze tags remain
immutable. Hosted CI for the new governance commit remains pending until direct 4/4
evidence is supplied. Channel support and every later stage remain unstarted.
