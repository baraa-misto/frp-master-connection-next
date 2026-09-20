# Toolchain Record

## Stage 0.1 detected inventory

Detection date: 2026-08-03

Stage: 0.1

Purpose: environment inventory only

| Command | Detected output |
|---|---|
| `git --version` | `git version 2.54.0.windows.1` |
| `python --version` | `Python 3.14.6` |
| `py -0p` | `-V:3.14 * C:\Users\green\AppData\Local\Python\pythoncore-3.14-64\python.exe` |
| `node --version` | `v24.18.0` |
| `npm --version` | `11.16.0` |

No packages were installed or upgraded in Stage 0.1. No exact application dependency versions were selected. Supported runtime ranges, reproducible environment files, package-manager policy, lockfile policy, and CI versions remained pending Stage 0.2 architecture review.

The Stage 0.1 values document the initialization environment; they are not approved production constraints.

## Stage 0.2.1 compatibility preflight

Evidence timestamp: 2026-08-03T20:12:59.0628429-05:00

Starting baseline: `9cf4781256870d307feb24d654608201998e35f5`

Purpose: isolated runtime, dependency, tool, build, and audit compatibility evidence before scaffolding

Review status: **Stage 0.2.1 evidence reviewed and accepted as a provisional implementation baseline; final production toolchain approval and freeze remain pending**

Full evidence, matrices, declared engine/peer constraints, commands, intermediate failures, alternatives, risks, and cleanup confirmation are in [`docs/architecture/TOOLCHAIN_AND_DEPENDENCY_COMPATIBILITY.md`](docs/architecture/TOOLCHAIN_AND_DEPENDENCY_COMPATIBILITY.md).

### Detected and tested tools

| Tool | Detected version / status | Path where practical | Test scope | Provisional Stage 0.2.2/0.2.3 position | Approved |
|---|---|---|---|---|---|
| Git | 2.54.0.windows.1 | `C:\Program Files\Git\cmd\git.exe` | Repository preflight and validation | Continue for repository controls | No |
| CPython | 3.14.6 | `C:\Python314\python.exe` | Two isolated backend resolutions; controlling venv retained bundled pip 26.1.2 | Accepted as the exact provisional Stage 0.2.2 implementation runtime; supported range and production freeze remain pending | No |
| pip | 26.1.2 detected; disposable 26.1.2 controlling and 26.2 corroborating | Python module | Exact installs, `pip check`, metadata, freeze comparison, CLI inspection | Standard project-local `venv` plus pip accepted provisionally; exact backend hash-lock generation mechanism remains pending | No |
| Python launcher | 3.14 target only | `C:\windows\py.exe` → `C:\Users\green\AppData\Local\Python\pythoncore-3.14-64\python.exe` | Interpreter identity only; no alternate runtime needed | Optional launcher, not a second supported baseline | No |
| Node.js | 24.18.0 | `C:\Program Files\nodejs\node.exe` | Exact frontend tree, full engine scan, type, lint, test, build, audit | Accepted as the exact locally tested Stage 0.2.3 baseline; newer Node 24 patch evaluation is deferred to controlled maintenance | No |
| npm | 11.16.0 | `C:\Program Files\nodejs\npm.ps1` | Install/tree/audit and exact-save behavior | Accepted provisionally with future exact direct versions, a committed `package-lock.json`, and `npm ci` | No |
| uv | Unavailable; command exit 1 | None | Not tested | Separate installation/evaluation approval required | No |
| pipx | Unavailable; command exit 1 | None | Not tested | Not required for the first shell | No |
| Corepack | 0.35.0 | `C:\Program Files\nodejs\corepack.cmd` | Detection only; not enabled | Do not enable/select without separate approval | No |
| pnpm | 11.9.0 | Codex fallback runtime path | Detection only | Not selected; npm already passed | No |
| Yarn | Unavailable; command exit 1 | None | Not tested | Not selected | No |

### Exact package sets tested

Backend direct candidates:

`fastapi==0.141.1`, `pydantic==2.13.4`, `pydantic-settings==2.14.2`, `uvicorn==0.52.1`, `sqlalchemy==2.0.51`, `alembic==1.18.5`, `psycopg[binary]==3.3.4`, `pytest==9.1.1`, `pytest-cov==7.1.0`, `hypothesis==6.165.0`, `httpx==0.28.1`, `ruff==0.16.1`, and `mypy==2.3.0`.

Controlling backend result: install, `pip check`, all imports, 4 tests, 100% smoke coverage, Ruff, strict mypy, Uvicorn help, and Alembic help all exited 0 with zero conclusive warnings.

Frontend final direct candidates:

`react@19.2.8`, `react-dom@19.2.8`, `typescript@6.0.3`, `vite@8.2.0`, `@vitejs/plugin-react@6.0.5`, `vitest@4.1.10`, `@testing-library/react@16.3.2`, `@testing-library/dom@10.4.1`, `@testing-library/jest-dom@7.0.0`, `jsdom@30.0.1`, `eslint@9.39.5`, `@eslint/js@9.39.5`, `typescript-eslint@8.66.0`, `eslint-plugin-react-hooks@7.1.1`, `eslint-plugin-react-refresh@0.5.3`, `three@0.185.1`, `@types/three@0.185.3`, `@react-three/fiber@9.7.0`, `@types/react@19.2.18`, `@types/react-dom@19.2.4`, and `@types/node@24.13.3`.

Final frontend result: dependency tree and 307-manifest engine scan, TypeScript, one Vitest/Testing Library test, ESLint, Vite production build, React Three Fiber compilation, and full/runtime npm audits exited 0. The build retained one chunk-size warning. ESLint 10 was rejected because its declared Node range excludes 24.18.0. Optional `@react-three/drei@10.7.7` was metadata-evaluated only and is deferred.

## Status boundaries

- **Detected** does not mean installed by or selected for this repository.
- **Tested** applies only to the exact runtime patches and package versions in disposable Windows environments.
- **Reviewed** means the Stage 0.2.1 evidence was accepted for implementation planning.
- **Provisionally accepted** means the exact tested baselines may be used only in separately authorized Stage 0.2.2/0.2.3 tasks.
- **Approved/frozen** remains pending for the production toolchain, supported runtime ranges, backend lock-generation mechanism, CI images, and production constraints.

No permanent application manifest, lockfile, source, virtual environment, `node_modules` directory, calculation code, or production configuration was created. The entire temporary compatibility root was deleted after evidence capture.

This review requires no global tool installation or upgrade.

## Stage 0.2.2 backend implementation evidence

Evidence date: 2026-08-03

Starting baseline: `4dc8a8b1ec0f5198d9deb5479f14b89ccf956359`

Status: **Implementation complete and reviewed; accepted as a provisional backend
foundation for Stage 0.2.3 planning. The development toolchain remains provisional
and is not a production or deployment freeze.**

### Permanent direct baseline

| Group | Exact versions |
|---|---|
| Runtime/API | FastAPI 0.141.1; Pydantic 2.13.4; pydantic-settings 2.14.2; Uvicorn 0.52.1 |
| Optional persistence declarations | SQLAlchemy 2.0.51; Alembic 1.18.5; psycopg 3.3.4 with binary extra |
| Development | pytest 9.1.1; pytest-cov 7.1.0; Hypothesis 6.165.0; HTTPX 0.28.1; Ruff 0.16.1; mypy 2.3.0 |
| Tooling | pip-tools 7.6.0; Setuptools 83.0.0; Wheel 0.47.0 |
| Runtime | CPython 3.14.6 with environment-provided pip 26.1.2; pip was not upgraded |

`backend/pyproject.toml` is the direct-dependency and QA-configuration authority.
Setuptools 83.0.0 is the exact PEP 517 build backend. The PEP 621 package and
application version is the development-only `0.0.0.dev0`.

### Disposable tooling preflight

Temporary path:
`C:\Users\green\AppData\Local\Temp\frp-master-connection-stage-0-2-2-tooling-3d9d12f5b6af4c7ebd503f9a5a5e77d1`

| Gate | Result | Practical duration |
|---|---|---|
| `python -m venv <temporary-path>` | Exit 0 on the required authorized retry; Python 3.14.6 and pip 26.1.2 | 2,213 ms |
| Exact pip-tools/Setuptools/Wheel install | Exit 0; 7.6.0 / 83.0.0 / 0.47.0; no warning or error output; pip 26.2 availability notice only | 1,923 ms |
| `python -m pip check` | Exit 0; no broken requirements | 270 ms |
| `python -m piptools compile --help` | Exit 0; CLI available | 329 ms |
| `python -m piptools sync --help` | Exit 0; CLI available | 313 ms |
| `python -m wheel version` | Exit 0; Wheel 0.47.0 | 73 ms |
| distribution-version import report | Exit 0; pip-tools 7.6.0, Setuptools 83.0.0, Wheel 0.47.0 | 206 ms |

The compile help contains pip-tools' own two-line future-behavior `WARNING:`
documentation for `--allow-unsafe`; it was help text, not an execution warning. The
first network-restricted install could not reach package artifacts and was repeated
with authorized network access. Two version-report diagnostics also failed before the
conclusive result: Windows quoting removed Python string delimiters, and the first
metadata lookup used import name `piptools` instead of distribution name `pip-tools`.
Neither failure indicated candidate incompatibility.

The exact tooling root and three sandbox pip scratch directories were deleted and
verified absent. No global or user-site package was installed.

### Lock, local environment, QA, and build

The generated lock is
`backend/requirements/requirements-dev-py314.lock.txt`. It contains 48 exact
distribution entries and 817 dependency-artifact SHA-256 hashes. Two independent final
generations in the same disposable environment were byte-for-byte equal at 72,754
bytes. No lock-file checksum is registered as a controlled artifact hash during draft.

This file is specifically a provisional CPython 3.14 Windows development lock. It is
not the final Linux, CI, container, cloud, or production-deployment lock. Cross-platform
validation remains pending, and the lock must not be generalized beyond its tested
environment without another controlled validation task.

The clean lock installation used `pip install --require-hashes
--only-binary=:all:` and exited 0; all artifacts resolved as wheels and `pip check`
reported no broken requirements. The ignored `backend/.venv` was then created by
`scripts/backend-bootstrap.ps1`, received the same lock, and installed the package
editable with `--no-deps --no-build-isolation`.

The conclusive `scripts/backend-check.ps1` result was:

- `pip check`: no broken requirements;
- Ruff format: 28 files already formatted;
- Ruff lint: all checks passed;
- strict mypy: no issues in 26 source files;
- pytest: 53 passed;
- coverage: 118/118 statements and 12/12 branches, 100%;
- Uvicorn and Alembic help: exit 0; and
- runtime and optional-persistence imports, including psycopg binary implementation:
  exit 0.

The local package wheel was built outside the repository with `pip wheel --no-deps
--no-build-isolation`. Exactly one wheel,
`frp_master_connection-0.0.0.dev0-py3-none-any.whl`, was produced. Its 26 entries
included the package and `py.typed` and excluded tests, docs, private/generated content,
environment files, and databases. A third clean environment installed the hashed
wheel-only lock and the project wheel with `--no-deps`; `pip check`, package/application
imports, exact version assertions, and `/health` and `/api/v1/meta` TestClient calls
passed. The explicitly supplied test identity resolver was invoked once and identity
was not exposed.

The clean TestClient smoke emitted Starlette's documented deprecation warning for its
HTTPX fallback and recommendation to install the separately deferred `httpx2`. The
warning remains visible; no untested dependency was added and no warning was suppressed.
The HTTPX/TestClient migration remains a future controlled maintenance task.

All disposable lock, comparison, installation, wheel, and clean-install directories
were deleted and verified absent. `backend/.venv` remains locally by design and is
ignored by the existing `.venv/` rule.

### Status boundaries and remaining work

This evidence is Windows/CPython 3.14.6 development evidence only. Linux/CI
reproduction, production lock and deployment design, Python vulnerability/license/
provenance scanning, PostgreSQL execution and production driver selection, and final
production toolchain approval remain pending. Stage 0.2.2 implementation is complete,
reviewed, committed, and provisionally accepted, but no engineering calculation,
persistence, report, frontend, or deployment capability was established by those
results. The subsequent Stage 0.2.3 frontend disposition follows.

## Stage 0.2.3 frontend implementation evidence

Starting baseline: `f31940ea232ade6df935f5612393a7126fa56e30`

Status: **Implementation complete and reviewed; validation passed; provisionally
accepted as the frontend application foundation. The Windows development toolchain
remains provisional and is not a production or cross-platform freeze.**

The permanent frontend uses Node 24.18.0 and npm 11.16.0. `packageManager` is
`npm@11.16.0`; engine controls are Node `>=24.18.0 <24.19.0` and npm
`>=11.16.0 <11.17.0`. The npm package is private, intentionally has no `version`, and
uses only `engine-strict=true` and `save-exact=true` project-local controls.

Permanent runtime dependencies:

- `react@19.2.8`
- `react-dom@19.2.8`

Permanent development dependencies:

- `typescript@6.0.3`
- `vite@8.2.0`
- `@vitejs/plugin-react@6.0.5`
- `vitest@4.1.10`
- `@vitest/coverage-v8@4.1.10`
- `@testing-library/react@16.3.2`
- `@testing-library/dom@10.4.1`
- `@testing-library/jest-dom@7.0.0`
- `jsdom@30.0.1`
- `eslint@9.39.5`
- `@eslint/js@9.39.5`
- `typescript-eslint@8.66.0`
- `eslint-plugin-react-hooks@7.1.1`
- `eslint-plugin-react-refresh@0.5.3`
- `@types/react@19.2.18`
- `@types/react-dom@19.2.4`
- `@types/node@24.13.3`

Before permanent inclusion, a disposable package using Vitest 4.1.10,
`@vitest/coverage-v8` 4.1.10, and TypeScript 6.0.3 passed `npm ls --all`, Vitest help,
a one-test V8 coverage run at 100% statements/branches/functions/lines, and a full npm
audit with zero vulnerabilities. Optional peer declarations were visible and produced
no invalid, missing-required, or peer-conflicted dependency.

`frontend/package-lock.json` is the authoritative exact resolved tree for Stage 0.2.3.
It is lockfile version 3, resolves only through `https://registry.npmjs.org/`, and
records 290 nonroot entries plus the root record, for 291 total. Its unchanged SHA-256
is `E0F3FE693B6FDED14ADB4282E2820E9862B4E442145C24F3A6290F814B42DA65`.
The controlling install and reproducibility command is `npm ci`.

Two independent clean installations consumed that existing lock. Each produced 266
normalized installed locations; their identical normalized tree hash was
`E9BF9E4B1AA0A28402E2B262C2758C4365651F7AC6BB791D890DD6F59CD63192`.
`npm ci` and the subsequent QA changed none of `package.json`, `package-lock.json`, or
`.npmrc`.

Generating a fresh lock from `package.json` alone is an update-availability operation,
not the controlling Stage 0.2.3 reproducibility test. That separate resolution found
`electron-to-chromium` 1.5.401 available in place of the accepted lock's 1.5.400 and
`node-releases` 2.0.52 in place of 2.0.51. Those transitive updates are deferred to a
separate controlled dependency-maintenance task; they do not establish a defect in the
accepted lock.

The permanent quality gates passed as follows:

- ESLint: exit 0 with zero warnings;
- strict TypeScript: exit 0;
- Vitest: 2 files and 35 tests passed;
- V8 coverage: 19/19 statements, 6/6 branches, 9/9 functions, and 19/19 lines, all
  100%;
- Vite 8.2.0 build: 22 modules transformed, three output files, no warning, and no
  source map;
- output sizes: `index.html` 529 bytes, main JavaScript 195,692 bytes, and CSS 5,212
  bytes; and
- preview: loopback-only HTTP 200 with built asset references, followed by verified
  process shutdown.

Both the full and `--omit=dev` npm audit reports returned zero info, low, moderate,
high, critical, and total vulnerabilities. Their dependency metadata reported 4
production, 287 development, 26 optional, 0 peer, and 290 total entries. Both
OS-temporary clean installations ran exact Node/npm checks, `npm ci`, `npm ls --all`,
lint, typing, tests with the same 100% coverage, build, and both audits successfully.
Their 266 normalized installed locations and three-file builds reproduced the local
results, and the temporary copies were deleted.

Three.js, `@types/three`, React Three Fiber, and Drei remain deferred. No router, state
library, CSS/component framework, API client, authentication SDK, billing SDK,
analytics/telemetry SDK, browser E2E package, or untested permanent package was added.

This is Windows/Node 24.18.0/npm 11.16.0 development evidence only. Real-browser
screen-reader, automated contrast, browser zoom, real-device responsive, real-browser
reduced-motion, end-to-end browser, Linux/CI, and current Node patch validation remain
pending, as do API integration, authentication, project ownership, engineering
geometry, visualization, calculation capability, production dependency provenance/
license review, deployment design, and final production toolchain approval. The 100%
frontend coverage applies only to the current Stage 0.2.3 executable shell; it does not
validate engineering mathematics, an engineering calculation engine, or commercial
use. At the Stage 0.2.3 disposition, Stage 0.2.4 had not started, and the toolchain
remained provisional and not frozen.

## Stage 0.2.4 integrated QA and initial CI

Starting baseline: `1176cb4a85efc3287b92cbb33a1616958f74aa74`

Status: **Implemented and locally validated; pushed workflow awaiting hosted GitHub
Actions confirmation. The toolchain remains provisional and not frozen.**

The repository-level local command is:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-all.ps1
```

It validates the handoff manifest, bootstraps and checks the backend, bootstraps and
checks the frontend, runs both npm audits, checks `git diff --check`, and requires an
empty index. Passing it is software-foundation evidence only and is not engineering
validation.

The initial `CI` workflow uses only `actions/checkout@v7`,
`actions/setup-python@v7`, and `actions/setup-node@v7`. Backend and frontend jobs run
independently on `ubuntu-24.04` and `windows-2025`, with exact Python 3.14.6 and Node
24.18.0 runtimes. Top-level permissions are `contents: read`; checkout credential
persistence is disabled, and the workflow uses no secrets, artifact upload,
publication, deployment, Git write, or environment.

The backend job preserves the exact hash and binary-only lock-install controls. A
Linux incompatibility must fail visibly and trigger a separate cross-platform-lock
decision. The frontend job uses the authoritative existing package lock through `npm
ci` and runs the existing lint, strict-type, coverage, build, and audit commands.

Hosted CI confirmation remains pending until the first pushed workflow run is reviewed.
macOS, real-browser accessibility, production lock design, immutable action-SHA pins,
engineering-domain validation, and all calculation validation remain outstanding.
