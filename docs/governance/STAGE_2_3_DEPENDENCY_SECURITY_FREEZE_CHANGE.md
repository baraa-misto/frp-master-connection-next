# Stage 2.3 dependency-security freeze change

## Authorization and boundary

Baraa Misto authorized this narrow security-only change by transmitting the complete
Stage 2.4B Dependency-Security Prerequisite R1 and Controlled Stage 2.3 Freeze-Change
order. This is a prerequisite correction, not a Stage 2.4B implementation commit or a
global product freeze. Stage 2.4B remains unaccepted and its complete work-in-progress
remains unstaged.

The correction addresses GitHub reviewed advisory `GHSA-2v37-7h3g-55p8` /
`CVE-2026-67213`. The accepted lockfile resolved development-only transitive
`nanoid@3.3.17`; the patched version is `3.3.18`.

## Exact dependency change

The dependency path is:

```text
vite@8.2.0 -> postcss@8.5.25 -> nanoid@3.3.17
```

`postcss@8.5.25` declares `nanoid` as `^3.3.16`, which permits `3.3.18` without a
parent update. npm `11.16.0` generated the successor in an isolated temporary
directory using:

```text
npm update nanoid --package-lock-only --ignore-scripts --save=true --audit=false
```

The exact reviewed lockfile delta changes only the `node_modules/nanoid` entry's
`version`, `resolved`, and `integrity` fields:

| Field | Original R8 value | Security-successor value |
|---|---|---|
| Version | `3.3.17` | `3.3.18` |
| Resolved | `https://registry.npmjs.org/nanoid/-/nanoid-3.3.17.tgz` | `https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz` |
| Integrity | `sha512-xQLf0A3HOMlgHq0n247/LRuAOYmB7dXJ/DvAxGvsSBij45XtBSmQycu+F8ODbHwns/XyFZagyL1+J0Offw1E0g==` | `sha512-DTg4MJbGMWkfi6VZFdNt2/caMbQy4Ou+Op/hJQvGEWcnVfoA1QA+xzRKAzw9jD6+GVOOeYr/mIcuDSdug6F6+w==` |

No other package version, package entry, dependency edge, lockfile version, root
metadata, script, engine, workspace, or ordering changes. `frontend/package.json` is
byte-for-byte unchanged; no direct dependency or override was added; no parent package
was upgraded; and no runtime dependency changed. The runtime-only audit was already
clean before this correction and remains required to be clean.

## Controlled identities

| Artifact | Historical/active identity |
|---|---|
| Frozen `frontend/src` tree | `df664801ea31a5a33e582e886dc787bf4f9be8aa` |
| Frozen `frontend/package.json` blob | `b753abd55004168eee5844879f0596d435fe4b5a` |
| Original R8 `frontend/package-lock.json` blob | `f2a594dae8c871d5c1c78e69f1023d6e77adf6e6` |
| Approved Nano ID security-successor package-lock blob | `ae1831268db42005517343bf555f054a673ae520` |
| Original package-lock SHA-256 | `43C85D832FEA4DCEA7A35E2D87C4AABDCBE08FEC64A2C2C6B716240FB3C601E4` |
| Security-successor package-lock SHA-256 | `20205C82940ABF46288DE6704245E6F7E5AA91B0686BA605B687590A0D17C254` |

The original R8 package-lock identity remains historical freeze provenance. The audit
recognizes exactly that historical identity and the one approved security successor;
no third lockfile identity is allowed. A separate active-security assertion requires
the checked-out lockfile to be the successor and to resolve only `nanoid@3.3.18`, so a
future return to the vulnerable R8 lockfile fails even though its historical identity
remains recorded.

The annotated tag `stage-2.3-interface-geometry-freeze` remains immutable at
`5bc545ab8251f9bd49dedc776962937ed5e822a2`. It is not moved, deleted, recreated, or
repushed by this change.

## Preserved behavior and regression obligations

`frontend/src` and `frontend/package.json` retain their one exact frozen identity.
Regression tests must reject source changes/additions/deletions/renames, package.json
mutation, arbitrary lockfile mutation, a third lockfile identity, and vulnerable active
Nano ID state. Git-object comparison remains invariant to path separators, checkout
location, line endings, and enumeration order. Complete backend/frontend/integrated
gates, both npm audits, exact controlled engineering hashes, and freeze-tag identity
must pass.

No frontend production source, API, application orchestration, preview, engineering
method, RC1/RC2 artifact, persistence, reporting, authentication, billing, deployment,
dependency declaration, or tag changes.

## Stage 2.4B WIP preservation

Before correction, the Stage 2.4B WIP comprised 13 modified tracked files and 8
untracked files. Its tracked diff hash, excluding the authorized dependency and freeze
paths, was `07023ba986c9ebc8791c1c84d6576661e3d2fc82`. Every path and per-file SHA-256
matched the preceding stopped attempt. The same fingerprint and manifests must match
after every gate and after push; no Stage 2.4B path may enter this correction commit.

## Verification and acceptance state

GitHub Actions run #27 for commit
`c61f5862e44f8d5b142ed7b353b967329bc03c34` completed with overall status
`FAILURE` in 2 minutes 31 seconds. Backend Ubuntu and Backend Windows each reported
1 failed, 1260 passed, with 100% line and branch coverage. Frontend Ubuntu and
Frontend Windows each passed all 123 tests.

The failed test was
`test_security_successor_lock_diff_is_exactly_nanoid_metadata`. It attempted to read
historical R8 package-lock blob `f2a594dae8c871d5c1c78e69f1023d6e77adf6e6`
directly with `git cat-file blob`. That object exists in the long-lived development
repository but is absent from a normal object-isolated depth-1 hosted checkout, so the
command returned status 128 on both hosted operating systems.

R2 removes that historical-object availability dependency. The audit reads the exact
reachable successor blob from `HEAD`, verifies its Git and SHA-256 identities,
reconstructs the historical bytes by replacing the one exact Nano ID metadata block,
and verifies the reconstructed historical Git and SHA-256 identities. It then reverses
the replacement byte-for-byte and confirms semantically that only `version`,
`resolved`, and `integrity` differ. It performs no history fetch and does not read or
write the historical Git object.

- Local QA: passed. Dependency validation, backend QA, frontend QA, integrated QA,
  controlled-artifact hashing, freeze-identity checks, and Stage 2.4B WIP-preservation
  checks were green before the dedicated correction commit.
- Correction commit/push: this record is included only in the dedicated commit with
  subject `fix: remediate nanoid audit with freeze-compatible lockfile update`; its
  exact commit identity and normal `origin/main` push result are recorded in the
  completion report because a commit cannot self-reference its own hash.
- R2 hosted CI: `PENDING USER VERIFICATION`; the dependency-security prerequisite
  remains unaccepted.
- Required hosted evidence: Backend Ubuntu, Backend Windows, Frontend Ubuntu, and
  Frontend Windows green for the exact correction commit; both audits zero; freeze
  audit green; no unexpected artifacts.

Stage 2.4B remains unaccepted, unstaged, uncommitted, unpushed, and not resumed until
the prerequisite correction receives direct hosted-CI verification and acceptance.
