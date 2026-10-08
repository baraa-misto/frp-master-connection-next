# F8-G1 security and publication gate

Owner order SHA-256:
`1513DDC440D256AA6CCDC506D851675D262DB048A11062A3F100FE00280EAA6F`.
The existing F8 implementation is preserved. G1 changes only security tooling,
exact dependency governance, tests, documentation and CI support.

## Dependency authority

Mako remains Alembic's transitive dependency: 1.3.12 -> exactly 1.4.2.
pip remains tooling: 26.1.2 -> exactly 26.2.0. Official PyPI publishes that
zero-patch release as 26.2; its wheel metadata and installed version say 26.2.
PEP440 version equality and exact official artifact hashes establish the identity.
The lock retains the explicitly authorized spelling `pip==26.2.0`.
SciPy 1.18.1 and its only new transitive package NumPy 2.5.3 remain unchanged.
No other package or frontend dependency changes.

Two isolated pip-tools resolutions changed only the Mako/pip blocks and controlled
generation header. Unrelated package blocks are byte-identical. The only output
normalization spells generated `pip==26.2` as its identical zero-patch version
`pip==26.2.0`; no artifact or package version changes in that normalization.

The exact successor manifest preserves both before/after security blocks and
headers. Tests pin the whole manifest/lock, reject version/hash/URL/missing/duplicate
block mutations, unrelated changes, extra bytes, truncation and predecessor
repinning. Reversing security changes reconstructs pre-G1 F8 SHA-256
`FA0A6A2C49C73E484969DE546F4A569925FA071EB9C4011A8764CC320FFBA63A`;
removing the exact SciPy/NumPy additions reconstructs F7 SHA-256
`C1A1B1428B11F0A817653B29E3539DC2CBC06AD63385AA20A602C0B03CF5F3D8`.
All older dependency identities remain unchanged.

## Supported installation and QA

Run `scripts/backend-bootstrap.ps1` in a fresh isolated checkout. It accepts the
historical Python-provided seed pip or the exact approved successor, installs the
hash-locked wheel-only environment, then strictly verifies Mako/pip/SciPy/NumPy.
The governed installed environment must contain one Mako and one pip distribution
and no older copy. The bootstrap's exact predecessor is reconstructible.

Run all 8,568 backend tests with configured 100% statement/branch coverage,
Ruff format/lint, strict mypy, dependency consistency, source/wheel builds,
runtime/provider/admin smoke, and the full 55-package OSV audit. No advisory waiver.
Run the unchanged frontend's 1,275 tests with all four coverage measures 100%,
TypeScript, ESLint, production build and both zero-finding npm audits.

Both hosted backend jobs print the exact installed security/statistical versions,
verify the successor chain, audit every locked package, and upload the audit.
Existing F8 tests and actual signed PDF generation execute on Windows and Ubuntu.
Cross-platform numerical/scope/record/report evidence and rendered-page inspection
are mandatory before owner-review readiness.

## Preserved engineering boundaries

No statistical equation, record authority, qualification activation, scope or
factor contract changes. All eight F7 analytical records and all 53 frozen
identities remain unchanged. No real approved record is installed; owner remains
8 evaluated / 6 unresolved / YELLOW, heel bounded N/A and two material reviews
neutral. No F9, main merge, tag, freeze or owner acceptance.

One ordinary candidate commit/push follows complete local gates. One exact-SHA
four-job CI execution follows. PR #1 stays draft with an F8 evidence update.
