# Stage 3.7 Column-Base Shear Family Freeze

## Control and accepted baseline

The controlling order was read in full before repository action. Its SHA-256 is
`924F001299FD93FDE585B8B6AADBBC1EBDAACAA693264EC5A6048EE77C3270A2`, and its final
sentinel is present. The accepted product baseline is clean synchronized `main` at
`0403bc8a4ace0df95b45a84a55832c17b18d6008`, subject
`fix: correct angle-column single bolt path`, commit count 95.

The accepted chain is Stage 3.7A commit `e906ba6faad2e4a85f08cf954c8c95a49a0c6c9f`
followed by Stage 3.7A-R1 commit `0403bc8a4ace0df95b45a84a55832c17b18d6008`.
GitHub Actions runs #89 and #90 each passed Backend Ubuntu, Backend Windows, Frontend
Ubuntu, and Frontend Windows in approximately 5m49s and 5m56s. The owner accepted the
final six-case Angle matrix and all prescribed invariants on 2026-08-31.

## Immutable identities

- `backend/src`: `4de4c4dbdb15f8725e8164958fda35558a09acb7`
- `frontend/src`: `4ca442c7c68cb1658f030c36a21c36353d5d3aa1`
- workflows: `20edd491455e6329c4565bc72cd7b88e29d3f7b1`
- `docs/engineering`: `75187a9d8a29b0c1dade5b26c607d4edd44d77f2`
- `backend/tests/golden`: `5bdf7a833084e3e65b7ce2903f842b5471e7df85`
- `backend/requirements`: `d8e1a9f1c2c89a4e50a181db1997c52b3c9bdf58`
- backend project SHA-256:
  `39BEA635FCE709607E1A4AE11D8B31829DFD07B4CADE332E030486BE1456A116`
- backend lock SHA-256:
  `953E6D3F6879CBAA6037AA4E8BA0D41B48380761983DCA4CDABFE54576670E0E`
- frontend package SHA-256:
  `1085F25B94819ED98EEE10739CF4B419F39BD626CC654699B0380B26341F4359`
- frontend lock SHA-256:
  `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254`

All six pre-existing annotated freeze-tag objects and peeled targets were verified
locally and remotely before mutation. They remain immutable.

## Frozen scope

The frozen product is the Column connection using Single or Double FRP base angles over
concrete for W/I, RHS, SRS, and Angle columns. It includes historical W/I behavior,
rectangular full-through paths, exterior-only hardware, non-material RHS cavity, solid
SRS depth, and the Stage 3.7A-R1 Angle negative-face path correction.

Angle Single attaches one connector to one selected broad face. Angle Double places one
connector on each broad face of the same selected physical leg; the other leg remains
physical for interference. The actual Angle centroid/member reference, selected-leg
eccentricity, generated moments, backend frame, signed actions, component-demand traces,
foundation-once equilibrium, material directions, preview/design separation, external
concrete/anchor handoff, and every current limitation remain exact.

`ANGLE_COLUMN_TWO_DIFFERENT_LEGS_MOMENT_BASE = NOT_IN_STAGE_3_7_SCOPE`. No moment-base
topology or later family is begun.

## Deterministic manifest and audit

The deterministic manifest is
`docs/governance/STAGE_3_7_COLUMN_BASE_SHEAR_FAMILY_FREEZE_MANIFEST.json`, SHA-256
`8C7CD0238C7A95E54E4B6DC987E4A558AE2910DA80342137C7772B7FCF6EC9AE`. It inventories
4 controlled Stage 3.7 artifacts, 34 inherited authorities, CI and owner evidence,
the eight-case matrix, exact source/package/lock/workflow identities, representative
engineering/application/handoff and Angle-path fingerprints, limitations, historical
tags, and successor policy.

Audit `backend/tests/calculation/test_stage_3_7_freeze_manifest.py` resolves exactly:

- `tag`: peel the immutable annotated Stage 3.7 tag and audit historical content;
- `object`: audit only an explicitly supplied exact freeze commit;
- `manifest_only`: authenticate pinned bytes, identities, artifacts, fingerprints,
  contracts, and limitations without treating successor `HEAD` as history.

The freeze-object parent is read from the raw commit header through `git cat-file -p`.
No audit fetches from the network or uses object alternates.

## Tamper-negative coverage

The audit rejects modified manifest bytes; backend/frontend trees; package, lock, or
workflow identities; controlled artifacts; accepted baseline; profile matrix; Single or
Double topology; inclusion of the different-leg moment topology; Angle centroid/reference
or R1 negative-face rule; component-demand or foundation-once rule; material directions;
connection-normal or concrete/anchor boundary; engineering fingerprints; wrong explicit
objects; wrong peeled tag targets; and successor-HEAD substitution.

## Change declaration

Production-source changes: `0`. Engineering-method changes: `0`. Controlled engineering-
artifact changes: `0`. Dependency changes: `0`. Workflow changes: `0`. Existing-tag
changes: `0`. The only authorized implementation paths are governance, documentation,
and the new freeze audit.

## Verification status

- Focused manifest audit: 28 passed before tag creation with `manifest_only` resolution.
- Complete local integrated QA: 2,749 backend tests passed at configured 100-percent
  coverage over 21,542 statements and 5,986 branches; 571 frontend tests across 39
  files passed at configured 100-percent coverage over 4,178 statements, 3,531 branches,
  1,465 functions, and 3,129 lines. Static, build, runtime-smoke, dependency-tree,
  JSON/whitespace, and both zero-vulnerability audit gates passed.
- Fresh depth-one, no-tags, no-alternates object-isolated QA: pending governance commit.
- Explicit historical-object mode: pending governance commit.
- Post-tag `source='tag'` audit: pending annotated tag creation.
- Freeze-commit hosted CI: pending direct four-of-four evidence after publication.

The future different-leg Angle-column moment topology was not begun.
