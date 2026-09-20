# Stage 3.5 Concrete-Support Shear Family Freeze

## Accepted identity

- Accepted product baseline: `4c154b9d31e2a0100fd9f8c5cc90243e838a19c7`.
- Governance commit subject: `chore: freeze Stage 3.5 concrete-support shear family baseline`.
- Expected governance commit count: `89`.
- Manifest: `docs/governance/STAGE_3_5_CONCRETE_SUPPORT_SHEAR_FAMILY_FREEZE_MANIFEST.json`.
- Manifest SHA-256: `671DF6992BC35AFED3C7CE9CB0230F7778C74CE8E7F412C16A9467F080AB7258`.
- Authorized annotated tag: `stage-3.5-concrete-support-shear-family-freeze`.

## Accepted evidence

GitHub Actions runs #76 attempt 2 and #77–#83 are accepted four-of-four green
Ubuntu/Windows backend/frontend evidence. Run #83 completed in approximately 5m43s.
The owner completed final Stage 3.5A-R2, Stage 3.5B-R1, and Stage 3.5C-R2 visual
acceptance on 2026-08-29.

## Frozen scope

The manifest records 28 Stage 3.5 controlled artifacts and 47 inherited authorities.
It freezes the accepted Stage 3.5A paired-angle wall, Stage 3.5B direct side-lap wall,
and Stage 3.5C column-base web-angle products, including historical/current contracts,
exact fingerprints, external concrete/anchor boundary, generated transfer moments,
region-specific material axes, Stage 3.5C serial component-demand semantics,
preview/design separation, and visualization/request-state behavior.

Production source trees remain exactly:

- `backend/src`: `e493b512d59e6218b61a2dc43bf0aed8c00cce16`;
- `frontend/src`: `bf2f82d8d5f2b274feab64c674a75270eca3d497`.

Package, lock, and workflow identities remain exact. Existing Stage 2.3, Stage 3.2,
Stage 3.3, and Stage 3.4 annotated tags remain immutable.

## Successor-safe audit

`backend/tests/calculation/test_stage_3_5_freeze_manifest.py` uses only:

1. `tag` — peel and audit the immutable annotated Stage 3.5 tag;
2. `object` — audit an explicitly supplied historical commit object;
3. `manifest_only` — validate pinned manifest/artifact/identity evidence when the tag and
   historical object are unavailable.

The resolver never treats arbitrary successor `HEAD` as the historical freeze. Negative
coverage rejects manifest, source, package, lock, workflow, artifact, baseline, contract,
fingerprint, limitation, explicit-target, tag-target, and successor-substitution tampering.

## Change boundary

This freeze changes zero production source, calculation method, controlled engineering
artifact, dependency, workflow, or existing tag. Beam-to-beam web splice is planned only,
has not begun, and receives no design authority from this record. Hosted CI for the new
governance commit remains pending direct post-push evidence.
