# Toolchain and Dependency Compatibility

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Starting commit | `9cf4781256870d307feb24d654608201998e35f5` — `chore: establish FRP Master Connection Stage 0.1 foundation` |
| Stage | 0.2.1 — toolchain and dependency compatibility preflight |
| Evidence date and time | 2026-08-03T20:12:59.0628429-05:00 |
| Status | Reviewed / accepted as a provisional implementation baseline / not frozen |
| Toolchain status | Provisional; final production approval pending |
| Review disposition | Accepted for Stage 0.2.2/0.2.3 implementation planning |

## Purpose and scope

This record determines whether the detected Windows development runtimes can support a provisional backend and frontend package baseline before permanent manifests or application source are created. It records official registry metadata, exact package versions, disposable smoke-project behavior, dependency and engine compatibility, quality-tool results, security-audit observations, alternatives, and remaining decisions.

This was a compatibility and architecture-decision exercise only. It did not implement an application, a persistent API, a database, production configuration, engineering geometry, an engineering equation, a capacity, a resistance factor, a numerical criterion, a force-distribution method, a utilization calculation, a structural limit state, a connection template, a rendered connection, or report logic.

Compatibility on one Windows machine and exact runtime patch is accepted as evidence for Stage 0.2.2/0.2.3 implementation planning; it does not establish an approved support range, production-readiness claim, engineering validation, or final production toolchain approval.

## Repository isolation

The repository was verified before testing at:

`C:\Users\green\Documents\New project\frp-master-connection`

The starting branch was `main`, HEAD was `9cf4781256870d307feb24d654608201998e35f5`, the working tree was clean, `git diff --check` passed, and no remote or tag existed.

All smoke files, manifests, locks, virtual environments, `node_modules` content, caches, logs, build output, and test output were created only under:

`C:\Users\green\AppData\Local\Temp\frp-master-connection-stage-0-2-1-d33fa3d0c3604096b208958e51f5e495`

That exact uniquely named root was resolved beneath the operating-system temporary directory, removed recursively after evidence capture, and verified absent. No package was installed globally or to a user site. Corepack was not enabled. No Git configuration or system runtime was changed.

## Evidence sources and interpretation

- Python package versions and `Requires-Python` values came from official PyPI resolution/index data and installed `dist-info` metadata. Exact release metadata was checked through PyPI; for example, [FastAPI 0.141.1](https://pypi.org/project/fastapi/0.141.1/) and [psycopg-binary 3.3.4](https://pypi.org/project/psycopg-binary/3.3.4/).
- Frontend versions, `engines`, peer dependencies, deprecation flags, and dist-tags came from the configured official registry, `https://registry.npmjs.org/`, using `npm view`.
- [Python 3.14.6](https://www.python.org/downloads/release/python-3146/) is an official maintenance release dated 2026-06-10.
- The official [Node.js release table](https://nodejs.org/en/about/previous-releases) identified the Node 24 line as LTS on the evidence date. It also listed 24.19.0 as the latest Node 24 patch. Node 24.18.0 remains the accepted exact tested baseline; evaluating a newer Node 24 patch is deferred to a future controlled maintenance task and is not required by this review.
- The future packaging recommendation follows the one-authoritative-[`pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) boundary. npm lock semantics are described by the official [`package-lock.json` documentation](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/).

Every selected version is a stable, non-prerelease version string and was not marked deprecated by its registry metadata. FastAPI 0.141.1 has no prerelease identifier but retains PyPI's historical `Development Status :: 4 - Beta` classifier; that classifier is a review consideration rather than evidence of a prerelease artifact.

## Detected local toolchain

| Tool | Exact detected output | Executable path | Classification | Stage 0.2.2/0.2.3 recommendation / approval implication |
|---|---|---|---|---|
| Git | `git version 2.54.0.windows.1` | `C:\Program Files\Git\cmd\git.exe` | Required and used for repository gates | Continue provisionally; no production/CI version is approved |
| Python | `Python 3.14.6` | `C:\Python314\python.exe` | Required; controlling backend compatibility runtime | Accepted as the exact provisional Stage 0.2.2 implementation runtime; supported range and production freeze remain pending |
| pip | `pip 26.1.2 from C:\Python314\Lib\site-packages\pip (python 3.14)` | Python module | Required with the tested `venv` option | Bundled 26.1.2 is directly proven; locking mechanism still needs approval |
| Python launcher | `-V:3.14 * C:\Users\green\AppData\Local\Python\pythoncore-3.14-64\python.exe` | `C:\windows\py.exe` | Optional launcher; only installed alternate path found | No additional interpreter installation is required by this evidence |
| Node.js | `v24.18.0` | `C:\Program Files\nodejs\node.exe` | Required; controlling frontend compatibility runtime | Accepted as the exact locally tested Stage 0.2.3 baseline; newer Node 24 patch evaluation is deferred to controlled maintenance |
| npm | `11.16.0` | `C:\Program Files\nodejs\npm.ps1` | Required and used for the frontend tree | Accepted provisionally with future exact direct versions, a committed `package-lock.json`, and `npm ci` |
| uv | Command not found, exit 1 | Unavailable | Optional | Not tested or selected; separate installation/evaluation approval required |
| pipx | Command not found, exit 1 | Unavailable | Optional | Not needed for the proposed first shell |
| Corepack | `0.35.0` | `C:\Program Files\nodejs\corepack.cmd` | Optional and detected | Not enabled or used; enabling/selecting it requires a separate decision |
| pnpm | `11.9.0` | `C:\Users\green\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd` | Optional, detected through a Codex fallback runtime | Not tested or recommended for the repository; npm already passed |
| Yarn | Command not found, exit 1 | Unavailable | Optional | Not tested or selected |

Classification vocabulary:

- **Detected** means the command/path was observed locally.
- **Tested** means the exact runtime/package combination executed the recorded gates.
- **Reviewed** means the Stage 0.2.1 compatibility evidence was evaluated and accepted for implementation planning.
- **Provisionally accepted** means the exact tested baselines may be used only in separately authorized Stage 0.2.2/0.2.3 tasks.
- **Approved/frozen** remains pending for the production toolchain, supported runtime ranges, lock mechanism, CI images, and production constraints.

## Python runtime compatibility analysis

The actual backend smoke environment used `C:\Python314\python.exe`, CPython 3.14.6, Windows amd64. The Python launcher target was also CPython 3.14.6 but at a different path; it received an identity check only. `py -0p` exposed no Python 3.13 or 3.12 installation. Because the default 3.14.6 runtime passed, the alternate-runtime contingency did not trigger.

Python 3.14.6 is provisionally suitable for Stage 0.2.2 on this machine:

- every direct candidate's declared `Requires-Python` range admits 3.14;
- exact installation succeeded with both disposable pip 26.1.2 and 26.2 environments;
- CPython 3.14 Windows wheels resolved for the native packages used by the tree;
- imports, the HTTP endpoint, Pydantic/settings, SQLite metadata, SQLAlchemy typing, Hypothesis, coverage, Ruff, strict mypy, Uvicorn, and Alembic passed; and
- the controlling unupgraded pip 26.1.2 run ended with zero test warnings.

This does not establish Linux, container, deployment, or cross-platform lock compatibility. Clean Linux CI must reproduce the approved future lock before implementation proceeds beyond the shell.

## Backend dependency matrix

All rows installed from official PyPI resolution, imported where applicable, and reported `prerelease=False`.

| Package | Exact version | Requires Python | Installation/import/CLI evidence | Intended stage | Recommended status |
|---|---:|---|---|---|---|
| FastAPI | 0.141.1 | `>=3.10` | Installed; imported; `/health` ASGI request passed | First API shell | Provisionally recommended |
| Pydantic | 2.13.4 | `>=3.9` | Installed; imported; typed model round trip passed | First API shell | Provisionally recommended |
| pydantic-settings | 2.14.2 | `>=3.10` | Installed; imported; harmless defaults passed | First API shell | Provisionally recommended |
| Uvicorn | 0.52.1 | `>=3.10` | Installed; imported; module help exit 0 | First API shell | Provisionally recommended |
| SQLAlchemy | 2.0.51 | `>=3.7` | Installed from CPython 3.14 Windows wheel; typed mapping, SQLite metadata, and statement compilation passed | Persistence stage | Defer permanent addition until persistence begins |
| Alembic | 1.18.5 | `>=3.10` | Installed; imported; module help exit 0 | Migration/persistence stage | Defer permanent addition until migrations begin |
| psycopg | 3.3.4 | `>=3.10` | Installed through `psycopg[binary]`; imported; implementation reported `binary` | PostgreSQL stage | Defer permanent addition until PostgreSQL work |
| psycopg-binary | 3.3.4 | `>=3.10` | CPython 3.14 Windows binary installed and loaded | Local/CI development for PostgreSQL | Provisionally recommended for development only; deployment policy pending |
| pytest | 9.1.1 | `>=3.10` | Installed; 4 tests passed | First QA shell | Provisionally recommended |
| pytest-cov | 7.1.0 | `>=3.9` | Installed; 100% of 29 smoke statements | First QA shell | Provisionally recommended |
| Hypothesis | 6.165.0 | `>=3.10` | Installed; arbitrary-integer property test passed | Property/engineering QA | Compatible; add when property tests begin |
| HTTPX | 0.28.1 | `>=3.8` | Installed; direct `ASGITransport` endpoint test passed without warnings | First endpoint tests and future outbound HTTP | Provisionally recommended |
| Ruff | 0.16.1 | `>=3.7` | Installed native Windows wheel; final lint exit 0 | First QA shell | Provisionally recommended |
| mypy | 2.3.0 | `>=3.10` | Installed CPython 3.14 Windows wheel; strict check clean | First QA shell | Provisionally recommended |

The resolved supporting tree also selected compatible native wheels for greenlet, pydantic-core, coverage, and other applicable transitive packages. `pip check` found no broken requirement.

## Backend smoke-test design

The disposable package intentionally contained only framework-level compatibility material:

- a typed FastAPI app with `/health`;
- a Pydantic v2 response model and a harmless pydantic-settings object;
- direct HTTPX `ASGITransport` use;
- a typed SQLAlchemy 2 mapping, in-memory SQLite metadata creation, statement compilation, and explicit engine disposal;
- an Alembic import/configuration smoke;
- one deterministic endpoint/settings/persistence set plus one non-engineering Hypothesis integer property, totaling four tests;
- strict mypy and Ruff configuration; and
- no FRP domain object, physical geometry, force, material, bolt logic, equation, capacity, utilization, structural status, or proprietary behavior.

## Exact backend commands and results

The controlling environment retained the bundled pip:

~~~powershell
python -m venv .venv-pip-26-1-2
.\.venv-pip-26-1-2\Scripts\python.exe -m pip --version
.\.venv-pip-26-1-2\Scripts\python.exe -m pip install fastapi==0.141.1 pydantic==2.13.4 pydantic-settings==2.14.2 uvicorn==0.52.1 sqlalchemy==2.0.51 alembic==1.18.5 "psycopg[binary]==3.3.4" pytest==9.1.1 pytest-cov==7.1.0 hypothesis==6.165.0 httpx==0.28.1 ruff==0.16.1 mypy==2.3.0
~~~

| Command | Exit | Duration | Exact result |
|---|---:|---:|---|
| Exact-pin install above | 0 | 9.626 s | Installed without forced resolution; installation warning count 0 |
| `python -m pip check` | 0 | 0.314 s | `No broken requirements found.` |
| `python import_smoke.py` | 0 | 0.898 s | All requested runtime imports succeeded; psycopg implementation `binary` |
| `python -m pytest -ra` | 0 | 1.126 s | 4 passed, 0 warnings; pytest-reported duration 0.56 s |
| `python -m pytest --cov=backend_smoke --cov-report=term-missing` | 0 | 1.446 s | 4 passed, 0 warnings; 100% of 29 statements |
| `python -m ruff check .` | 0 | 0.073 s | `All checks passed!` |
| `python -m mypy --strict backend_smoke` | 0 | 0.315 s | No issues in 2 source files |
| `python -m uvicorn --help` | 0 | 0.203 s | Help rendered |
| `python -m alembic --help` | 0 | 0.414 s | Help rendered |

The same direct pins were first installed into another disposable venv after a precautionary pip 26.1.2-to-26.2 upgrade. Its install took 11.178 s and all final gates passed. A later clean A/B comparison showed that the two resolved trees differed only by pip itself. The upgrade was unnecessary and is a disclosed process deviation; pip 26.1.2 is the controlling evidence. Neither pip installation affected the global, user, or system environment.

### Retained intermediate failures and warnings

No real failure was suppressed:

1. The first sandboxed pytest attempt exited 1 after 4.013 s with zero tests collected and one collection error. Windows application-control policy blocked Hypothesis's native module, pytest could not create two cache paths, and the warning summary contained three warnings. An authorized rerun outside that process restriction passed; this was classified as a sandbox policy failure.
2. Starlette's convenience `TestClient` emitted a deprecation warning directing users toward a future `httpx2` package. The fixture was changed to HTTPX 0.28.1's supported direct `ASGITransport` API. `httpx2` was not installed or selected.
3. Ruff initially reported 13 fixture findings and later one import-order finding. The disposable fixture was corrected; no failure was ignored or broadly disabled. Final Ruff passed.
4. The first explicit coverage run passed but emitted an unclosed-SQLite `ResourceWarning`. The fixture added `engine.dispose()` in `finally`. The conclusive coverage run passed with zero warnings.
5. Two read-only metadata snippets failed with `SyntaxError` because PowerShell removed quoting. A base64-encoded equivalent then extracted installed metadata successfully. These were shell-quoting errors.

## Backend package-management and locking options

### Standard venv plus pip

This is the provisionally recommended Stage 0.2.2 option because it was available and directly proven on Windows with no global dependency:

- one future authoritative `pyproject.toml`;
- separate runtime and development/test dependency groups;
- an exact, complete, hash-bearing transitive lock or per-platform lock set generated from that declaration;
- exact Python patch pins for reviewed local and CI images while the supported range remains pending;
- clean `venv` creation and deterministic installation in Windows and Linux CI;
- separate production policy for psycopg versus the `binary` development extra; and
- controlled update changes that review metadata and lock diffs, reinstall from empty environments, and rerun dependency, test, coverage, lint, type, security, license, and supply-chain gates.

pip 26.1.2 exposes `pip lock`, but its help labels the command experimental and limits its guarantee to the current Python version and platform. It is not selected as the sole cross-platform locking mechanism here.

### uv

`uv` was unavailable and therefore not installed, tested, or selected. It remains a concrete alternative for a future cross-platform lock/workspace evaluation, but adopting it requires a separately approved provisioning and compatibility task.

No Poetry, Pipenv, or additional tool was introduced because the repository has no demonstrated need for another packaging layer at this stage.

## Node runtime compatibility analysis

The frontend smoke used Node 24.18.0 and npm 11.16.0. The final tree installed without `--force` or `--legacy-peer-deps`. A recursive engine scan parsed 307 installed package manifests:

~~~text
installed package manifests: 307
manifests with Node constraints: 172
incompatible Node constraints: 0
manifest parse errors: 0
~~~

Node 24.18.0 is therefore accepted as the exact locally tested provisional baseline for this candidate tree. This evidence does not approve all Node 24 patches or a broad range. Node 24.19.0 appeared as the current LTS patch on the official release page by the evidence date; evaluating a newer Node 24 patch is deferred to a future controlled maintenance task and is not required before Stage 0.2.3 planning.

The preflight caught a silent engine mismatch: npm installed ESLint 10.8.0 and `@eslint/js` 10.0.1 because `engine-strict=false` and emitted no warning, but their range `^20.19.0 || ^22.13.0 || >24` normalizes bare `>24` to `>=25.0.0`. Node 24.18.0 does not satisfy it. The final tree uses the newest tested compatible 9.x pair, 9.39.5.

## Frontend dependency matrix

All final direct specifications were exact, stable, non-deprecated registry releases.

| Package | Exact version | Declared Node engine | Material required peers | Test evidence / intended stage | Recommended status |
|---|---:|---|---|---|---|
| React | 19.2.8 | `>=0.10.0` | None | Render/test/build passed; first shell | Provisionally recommended |
| React DOM | 19.2.8 | None | React `^19.2.8` | Render/test/build passed; first shell | Provisionally recommended |
| TypeScript | 6.0.3 | `>=14.17` | None | `tsc --noEmit` passed | Provisionally recommended; 7.0.2 rejected for current lint peer range |
| Vite | 8.2.0 | `^20.19.0 || >=22.12.0` | Optional tool/preprocessor peers only | Production build passed | Provisionally recommended |
| `@vitejs/plugin-react` | 6.0.5 | `^20.19.0 || >=22.12.0` | Vite `^8.0.0` | Plugin compilation/build passed | Provisionally recommended |
| Vitest | 4.1.10 | `^20.0.0 || ^22.0.0 || >24.0.0` | Vite `^6 || ^7 || ^8`; optional jsdom and add-ons | 1 file/1 test passed | Provisionally recommended |
| `@testing-library/react` | 16.3.2 | `>=18` | Testing Library DOM `^10`; React/DOM `^18 || ^19` | Component test passed | Provisionally recommended |
| `@testing-library/dom` | 10.4.1 | `>=18` | None | Required testing peer; test passed | Provisionally recommended |
| `@testing-library/jest-dom` | 7.0.0 | Node `>=22`; npm `>=6` | Testing Library DOM `>10 <11` | Matcher test passed | Provisionally recommended |
| jsdom | 30.0.1 | `^22.22.2 || ^24.15.0 || >=26.0.0` | Optional Canvas `^3.2.3` | Vitest environment passed | Provisionally recommended |
| ESLint | 9.39.5 | `^18.18.0 || ^20.9.0 || >=21.1.0` | Optional `jiti` only | Flat-config lint passed | Provisionally recommended |
| `@eslint/js` | 9.39.5 | `^18.18.0 || ^20.9.0 || >=21.1.0` | None | Recommended-rule lint passed | Provisionally recommended |
| typescript-eslint | 8.66.0 | `^18.18.0 || ^20.9.0 || >=21.1.0` | ESLint `^8.57 || ^9 || ^10`; TypeScript `>=4.8.4 <6.1.0` | Typed-source lint passed | Provisionally recommended |
| eslint-plugin-react-hooks | 7.1.1 | `>=18` | ESLint `^3` through `^10` | Lint passed | Provisionally recommended |
| eslint-plugin-react-refresh | 0.5.3 | None | ESLint `^9 || ^10` | Lint passed | Provisionally recommended |
| Three.js | 0.185.1 | None | None | Fiber scene compiled and built | Compatible; defer permanent addition until visualization begins |
| `@types/three` | 0.185.3 | None | None | TypeScript scene check passed | Compatible; defer with Three.js |
| `@react-three/fiber` | 9.7.0 | None | React `>=19 <19.3`; Three `>=0.156`; React DOM `>=19 <19.3` optional for web | Canvas/mesh compiled and built | Compatible; defer permanent addition until visualization begins |
| `@types/react` | 19.2.18 | None | None | TypeScript passed | Provisionally recommended supporting type |
| `@types/react-dom` | 19.2.4 | None | `@types/react ^19.2.0` | TypeScript passed | Provisionally recommended supporting type |
| `@types/node` | 24.13.3 | None | None | Runtime-aligned Vite/config types passed | Provisionally recommended supporting type |

Material optional-peer metadata from the exact registry records:

- Vite: `tsx ^4.8.1`, `jiti >=1.21.0`, `less ^4.0.0`, `sass ^1.70.0`, `yaml ^2.4.2`, `stylus >=0.54.8`, `terser ^5.16.0`, `esbuild ^0.27.0 || ^0.28.0`, `sugarss ^5.0.0`, `@types/node ^20.19.0 || >22.12.0`, `sass-embedded ^1.70.0`, and `@vitejs/devtools ^0.4.0`.
- `@vitejs/plugin-react`: `@rolldown/plugin-babel ^0.1.7 || ^0.2.0` and `babel-plugin-react-compiler ^1.0.0`.
- Vitest: jsdom, happy-dom, `@vitest/ui 4.1.10`, `@types/node ^20.0.0 || ^22.0.0 || >24.0.0`, `@edge-runtime/vm`, `@opentelemetry/api ^1.9.0`, and matching 4.1.10 coverage/browser packages.
- Testing Library React: `@types/react ^18 || ^19` and `@types/react-dom ^18 || ^19`.
- jsdom: `canvas ^3.2.3`.
- ESLint: `jiti`.
- React Three Fiber: React DOM `>=19 <19.3` for web and Expo/React Native integration peers (`expo >=43`, `expo-gl >=11`, `expo-asset >=8.4`, `expo-file-system >=11`, and `react-native >=0.78`).

Optional `@react-three/drei` 10.7.7 was metadata-evaluated but not installed. Its peers—React/DOM `^19`, Three `>=0.159`, and Fiber `^9`—match the tested tree. It remains deferred because the smoke did not need it and its implementation value and transitive surface have not been reviewed.

The `npm ls --all` output contained 56 expected unmet **optional** entries for unused Expo/native Fiber integrations, Vite preprocessors/tooling, Vitest browser/coverage providers, jsdom Canvas, and platform-specific binaries. It contained zero invalid or required unmet entries.

## Frontend smoke-test design

The disposable Vite React TypeScript project contained:

- one minimal React component;
- one inline SVG component;
- one React Three Fiber `Canvas` and mesh sufficient to type-check and bundle Three/Fiber;
- one React Testing Library/Jest DOM test;
- a Vite/Vitest configuration;
- an ESLint flat configuration; and
- no product interface, connection template, engineering geometry, force arrow, structural result, equation, or production visual design.

## Exact frontend commands and results

The final direct tree was formed with exact-save commands:

~~~powershell
npm install --save-exact -- react@19.2.8 react-dom@19.2.8 three@0.185.1 '@react-three/fiber@9.7.0'
npm install --save-dev --save-exact -- typescript@6.0.3 vite@8.2.0 '@vitejs/plugin-react@6.0.5' vitest@4.1.10 '@testing-library/react@16.3.2' '@testing-library/jest-dom@7.0.0' '@testing-library/dom@10.4.1' jsdom@30.0.1 eslint@10.8.0 '@eslint/js@10.0.1' typescript-eslint@8.66.0 eslint-plugin-react-hooks@7.1.1 eslint-plugin-react-refresh@0.5.3 '@types/three@0.185.3' '@types/react@19.2.18' '@types/react-dom@19.2.4' '@types/node@26.1.2'
npm install --save-dev --save-exact -- eslint@9.39.5 '@eslint/js@9.39.5' '@types/node@24.13.3'
~~~

The second command records the initially evaluated ESLint 10 and Node 26 type candidates. The third command replaces them with the final compatible/runtime-aligned selections; the lock remained disposable.

| Command / operation | Exit | Duration | Exact result |
|---|---:|---:|---|
| Runtime install | 0 | 3.835 s | 18 packages added; 19 audited; 0 warning lines; 0 vulnerabilities |
| Initial development install | 0 | 10.400 s | 235 packages added; 254 audited; 0 warning lines; 0 vulnerabilities |
| ESLint/type alignment install | 0 | 1.655 s | 28 added, 1 removed, 11 changed; 281 audited; 0 warning lines; 0 vulnerabilities |
| `npm ls --all` | 0 | 0.522 s | 512 output lines; 0 invalid/required unmet; 56 expected unmet optional entries |
| Full recursive engine scan | 0 | Not separately timed | 307 manifests; 172 constrained; 0 incompatible; 0 parse errors |
| `npm run lint` | 0 | 1.348 s | 0 warnings |
| `npm test -- --run` | 0 | 1.425 s | Vitest 0.839 s; 1 file and 1 test passed; 0 warnings |
| `npm run build` | 0 | 2.524 s | Vite 0.991 s; 32 modules; production bundle emitted; 1 chunk-size warning |
| `npx tsc --noEmit` | 0 | 1.503 s | 0 warnings |
| `npm audit --json` | 0 | 0.627 s | 0 vulnerabilities at every severity |
| `npm audit --omit=dev --json` | 0 | 0.503 s | 0 runtime vulnerabilities |

The production build emitted:

~~~text
dist/index.html                     0.41 kB | gzip 0.28 kB
dist/assets/index-rFt5uMpP.css      0.18 kB | gzip 0.16 kB
dist/assets/index-BL92S4uJ.js   1,072.49 kB | gzip 294.19 kB
~~~

Its sole warning was Vite's default warning for a chunk above 500 kB. The deliberately minimal project statically bundled React, Three.js, and Fiber into one entry. A future production shell should lazy-load the 3D route/component or establish reviewed code-splitting.

The first sandboxed `npm test -- --run` and `npm run build` attempts each exited 1 when Vite's local Rolldown helper hit `spawn EPERM`. Authorized retries outside that process restriction passed. These were sandbox execution failures, not source, package, type, peer, test, or build incompatibilities.

## React Three Fiber compatibility

React 19.2.8, React DOM 19.2.8, Three.js 0.185.1, `@types/three` 0.185.3, and `@react-three/fiber` 9.7.0 satisfy the declared required peers. The minimal `Canvas`/mesh compiled under TypeScript 6.0.3, passed the full engine scan, and was included in the successful Vite production build. This proves framework/build compatibility only. It does not create canonical engineering geometry or calculation authority.

## Dependency-security observations

The final npm full audit reported:

| Classification | Count |
|---|---:|
| Direct runtime | 0 |
| Transitive runtime | 0 |
| Direct development | 0 |
| Transitive development | 0 |
| Info / low / moderate / high / critical | 0 / 0 / 0 / 0 / 0 |

Audit metadata reported 19 production, 286 development, 26 optional, 0 peer, and 304 total dependency entries. A separate runtime-only audit also returned zero.

`pip check` proves dependency consistency, not vulnerability absence. No Python vulnerability scanner or license scanner was installed because neither was in the authorized candidate list. Stage 0.2.2 needs an approved Python vulnerability, license, provenance, and hash-verification gate before a permanent lock is accepted.

Registry/audit results are time-bound observations from 2026-08-03. They must be repeated whenever packages or locks change and at appropriate CI/release cadence.

## Reviewed provisional Stage 0.2.2/0.2.3 implementation baseline

The following exact, locally tested baseline is accepted provisionally for Stage 0.2.2/0.2.3 implementation planning:

| Area | Provisional recommendation |
|---|---|
| Backend runtime | CPython 3.14.6, standard `venv`, bundled pip 26.1.2 |
| Backend first-shell runtime set | FastAPI 0.141.1, Pydantic 2.13.4, pydantic-settings 2.14.2, Uvicorn 0.52.1 |
| Backend first-shell QA set | pytest 9.1.1, pytest-cov 7.1.0, HTTPX 0.28.1, Ruff 0.16.1, mypy 2.3.0 |
| Backend deferred set | Hypothesis 6.165.0 until property tests; SQLAlchemy 2.0.51/Alembic 1.18.5/psycopg 3.3.4 until persistence |
| Backend declarations and lock | One future authoritative `pyproject.toml` with separated runtime and development declarations; a reproducible exact hash-bearing resolution is required, while its generation mechanism remains pending |
| Frontend runtime | Node 24.18.0 and npm 11.16.0 as the exact locally tested baseline; evaluation of a newer Node 24 patch is deferred to a future controlled maintenance task |
| Frontend first shell | Exact React/DOM, TypeScript 6, Vite/plugin, test, DOM, ESLint 9, React lint, and aligned type packages listed above |
| Frontend visualization | Three.js/Fiber/types are compatible but deferred until visualization work; future production code must lazy-load or otherwise split the 3D workspace from the initial route; Drei remains metadata-only and deferred |
| Frontend declarations and lock | One future `package.json`, exact direct specifications, committed `package-lock.json`, and `npm ci` in clean CI |
| Upgrade policy | Controlled change only; review registry metadata and diffs, regenerate lock, reinstall cleanly, rerun every gate and audits, and never use forced peer resolution without approval |

Stage 0.2.2 is the backend toolchain/API-shell review; it is not started by this record. Stage 0.2.3 is the frontend toolchain/application-shell review; it is also not started.

## Alternatives considered

| Alternative | Evidence and disposition |
|---|---|
| Python 3.13 or 3.12 | Not installed; not needed because 3.14.6 passed. No interpreter was installed. |
| Disposable pip 26.2 | Passed but the precautionary upgrade was unnecessary; retained as corroborating evidence, not the controlling baseline. |
| uv | Unavailable and not installed. Defer to a separate controlled lock/workspace evaluation. |
| pip's experimental `pip lock` | Help was inspected; current-platform guarantee is insufficient for an approved sole cross-platform strategy. |
| Poetry/Pipenv | No concrete repository need; not installed or evaluated. |
| Node 24.19.0 | Official page showed it as a newer Node 24 LTS patch; not installed or tested. Evaluation is deferred to a future controlled maintenance task and is not required by this review. |
| TypeScript 7.0.2 | Registry latest, but incompatible with typescript-eslint 8.66.0's `<6.1.0` peer; rejected for the candidate tree. |
| ESLint/`@eslint/js` 10.8.0/10.0.1 | Installed but declared engine ranges exclude Node 24.18.0; rejected despite npm's silent non-strict installation. |
| `@types/node` 26.1.2 | Installed initially, then replaced with 24.13.3 to align types with the Node 24 runtime. |
| pnpm/Corepack/Yarn | pnpm/Corepack were detected but not used; Yarn unavailable. npm passed and remains the narrowest supported proposal. |
| Starlette `TestClient` plus future `httpx2` | Current wrapper warned; direct HTTPX 0.28.1 `ASGITransport` passed. Evaluate `httpx2` separately if needed. |
| `@react-three/drei` 10.7.7 | Peer metadata is compatible, but it was not needed or installed. Defer until a reviewed visualization feature needs it. |

## Rejected or deferred options

- **Rejected for the exact candidate tree:** TypeScript 7.0.2, ESLint 10.8.0, and `@eslint/js` 10.0.1 because their controlling peer/engine ranges do not admit the selected companion tools or Node 24.18.0.
- **Replaced for runtime alignment:** `@types/node` 26.1.2 by `@types/node` 24.13.3.
- **Deferred pending a concrete feature or policy:** SQLAlchemy, Alembic, psycopg, Hypothesis, Three.js, React Three Fiber, and `@types/three` as permanent dependencies; optional Drei and `httpx2`; PostgreSQL execution; Python security/license tooling; `uv`; and any package-manager switch.
- **Not available to test:** Python 3.13/3.12, `uv`, pipx, and Yarn.

## Remaining blockers and risks

- PRV-018 through PRV-020 remain Provisional; final production toolchain approval and freeze remain pending.
- Supported Python/Node ranges, Linux CI, production images, deployment runtimes, and interpreter provisioning remain unverified.
- Node 24.18.0 is the exact tested baseline; evaluation of a newer Node 24 patch is deferred to a future controlled maintenance task and is not required by this review.
- The Python lock generator and cross-platform hash strategy remain unresolved; `pip lock` is experimental in pip 26.1.2 and `uv` was unavailable.
- Python vulnerability/license/provenance scanning remains to be selected and run.
- PostgreSQL connectivity, migration execution, deployment driver choice, and managed persistence were not tested; only imports/configuration and SQLite metadata compatibility were exercised.
- The frontend smoke's monolithic Three/Fiber bundle triggered one size warning; production route-level lazy loading or code splitting is a future implementation requirement.
- npm security results and registry metadata are point-in-time observations, not a continuing guarantee.
- Initial sandbox policy failures and access-restricted caches were environmental. The entire temporary root was nevertheless deleted successfully with authorized elevated cleanup.

## No-implementation and engineering-scope confirmation

Repository changes are documentation-only. This task introduced no:

- application package manifest, lockfile, source file, test, CI workflow, Dockerfile, migration, environment file, or database;
- ASCE or connection equation, capacity, resistance factor, numerical engineering or geometry criterion, force-distribution method, utilization, material/bolt strength, or structural limit-state calculation;
- placeholder or real engineering `PASS`/`FAIL` computation;
- connection template, rendered connection geometry, force arrow, calculation snapshot, generated report, or report logic; or
- private ASCE content, FRP Master Pro content, RAM Connection content, sibling-repository content, or other private engineering source.

Package names, tool output, and established result-status vocabulary appear only as compatibility/governance evidence.

## Temporary-environment cleanup

Cleanup is complete:

~~~text
resolved target:
C:\Users\green\AppData\Local\Temp\frp-master-connection-stage-0-2-1-d33fa3d0c3604096b208958e51f5e495

parent equals operating-system TEMP: True
unique Stage 0.2.1 prefix match: True
post-removal TEMP_EXISTS: False
~~~

The initial sandbox deletion could not enter access-restricted pytest cache remnants. After validating the exact resolved path and parent, an authorized recursive deletion of that one unique root succeeded. The removed content was disposable and is not recoverable from the temp path; all required evidence is preserved in this document.

## Approval status

Stage 0.2.1 compatibility evidence: **Reviewed and accepted for Stage 0.2.2/0.2.3 implementation planning.**

Toolchain status: **Provisional and not frozen. Final production approval remains pending.**

PRV-018 through PRV-020 remain **Provisional**. No permanent dependency manifest, lockfile, application implementation, or engineering implementation was created. Stage 0.2.2 and Stage 0.2.3 are not started.

No item in this record is Approved.

## Command ledger

Timing/transcript wrappers are omitted where they only measured and captured the exact external command shown. Registry-query commands were repeated for every package named in the associated list.

### Repository preflight

~~~powershell
Get-Location
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git log -1 --format=fuller
git status --short --branch
git status --porcelain=v1
git remote -v
git tag --list
git diff --check
~~~

### Tool discovery and interpreter identity

~~~powershell
git --version
python --version
python -m pip --version
py -0p
node --version
npm --version
uv --version
pipx --version
corepack --version
pnpm --version
yarn --version
Get-Command git, python, py, node, npm, uv, pipx, corepack, pnpm, yarn
python -c "import sys, platform; print('executable=' + sys.executable); print('version=' + sys.version.replace(chr(10), ' ')); print('implementation=' + platform.python_implementation()); print('architecture=' + platform.machine())"
py -3.14 -c "import sys, platform; print('executable=' + sys.executable); print('version=' + sys.version.replace(chr(10), ' ')); print('implementation=' + platform.python_implementation()); print('architecture=' + platform.machine())"
py -3.14 -m pip --version
Get-Date -Format o
~~~

### Repository document inspection

`Get-Content -Raw` or numbered `Get-Content`/`Select-String`/`rg` checks were run for:

- `TOOLCHAIN.md`
- `README.md`
- `HANDOFF_MANIFEST.json`
- `docs/governance/DECISION_REGISTER.md`
- `docs/governance/ARTIFACT_AND_VERSION_REGISTER.md`
- `docs/product/DEVELOPMENT_ROADMAP.md`
- `docs/architecture/DATA_VERSIONING_AND_REPRODUCIBILITY.md`
- `docs/architecture/JOINT_ASSEMBLY_DOMAIN_MODEL.md`
- `docs/security/SAAS_AND_SECURITY_ARCHITECTURE.md`
- `backend/README.md`
- `frontend/README.md`

`rg --files -g 'AGENTS.md'` returned exit 1/no matches. Decision/artifact IDs and manifest object shapes were also checked with read-only `Select-String` and Python JSON snippets.

### Backend registry, creation, installation, and gates

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip index versions <package>
.\.venv\Scripts\python.exe -m pip index --help
.\.venv\Scripts\python.exe -m pip index versions fastapi --json
.\.venv\Scripts\python.exe -m pip install fastapi==0.141.1 pydantic==2.13.4 pydantic-settings==2.14.2 uvicorn==0.52.1 sqlalchemy==2.0.51 alembic==1.18.5 "psycopg[binary]==3.3.4" pytest==9.1.1 pytest-cov==7.1.0 hypothesis==6.165.0 httpx==0.28.1 ruff==0.16.1 mypy==2.3.0
.\.venv\Scripts\python.exe -c <installed-metadata snippet>
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe .\import_smoke.py
.\.venv\Scripts\python.exe -m pytest -ra
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy --strict backend_smoke
.\.venv\Scripts\python.exe -m uvicorn --help
.\.venv\Scripts\python.exe -m alembic --help
.\.venv\Scripts\python.exe -m pytest --version
.\.venv\Scripts\python.exe -m ruff --version
.\.venv\Scripts\python.exe -m mypy --version
.\.venv\Scripts\python.exe -m uvicorn --version
.\.venv\Scripts\python.exe -m alembic --version

python -m venv .venv-pip-26-1-2
.\.venv-pip-26-1-2\Scripts\python.exe -m pip --version
.\.venv-pip-26-1-2\Scripts\python.exe -m pip install fastapi==0.141.1 pydantic==2.13.4 pydantic-settings==2.14.2 uvicorn==0.52.1 sqlalchemy==2.0.51 alembic==1.18.5 "psycopg[binary]==3.3.4" pytest==9.1.1 pytest-cov==7.1.0 hypothesis==6.165.0 httpx==0.28.1 ruff==0.16.1 mypy==2.3.0
.\.venv-pip-26-1-2\Scripts\python.exe -m pip check
.\.venv-pip-26-1-2\Scripts\python.exe .\import_smoke.py
.\.venv-pip-26-1-2\Scripts\python.exe -m pytest -ra
.\.venv-pip-26-1-2\Scripts\python.exe -m pytest --cov=backend_smoke --cov-report=term-missing
.\.venv-pip-26-1-2\Scripts\python.exe -m ruff check .
.\.venv-pip-26-1-2\Scripts\python.exe -m mypy --strict backend_smoke
.\.venv-pip-26-1-2\Scripts\python.exe -m uvicorn --help
.\.venv-pip-26-1-2\Scripts\python.exe -m alembic --help
.\.venv-pip-26-1-2\Scripts\python.exe -c "import psycopg.pq; print(psycopg.pq.__impl__)"
.\.venv\Scripts\python.exe -m pip freeze --all
.\.venv-pip-26-1-2\Scripts\python.exe -m pip freeze --all
Compare-Object <two freeze outputs>
Get-Command uv
.\.venv-pip-26-1-2\Scripts\python.exe -m pip lock --help
~~~

The `pip index versions <package>` command ran for FastAPI, Pydantic, pydantic-settings, Uvicorn, SQLAlchemy, Alembic, psycopg, psycopg-binary, pytest, pytest-cov, Hypothesis, HTTPX, Ruff, and mypy. Test/Ruff commands were rerun after each disclosed fixture correction and once conclusively in both venvs.

### Frontend registry, creation, installation, and gates

~~~powershell
npm config get registry
npm view "<package>@latest" name version dist-tags engines peerDependencies deprecated --json
npm view typescript@6 name version dist-tags engines peerDependencies peerDependenciesMeta --json
npm view eslint@9.39.5 name version dist-tags engines peerDependencies peerDependenciesMeta deprecated --json
npm view @eslint/js@9.39.5 name version dist-tags engines peerDependencies peerDependenciesMeta deprecated --json
npm view @types/node@24 version --json
npm view @types/node@24.13.3 name version dist-tags engines peerDependencies deprecated --json
npm install --save-exact -- react@19.2.8 react-dom@19.2.8 three@0.185.1 '@react-three/fiber@9.7.0'
npm install --save-dev --save-exact -- typescript@6.0.3 vite@8.2.0 '@vitejs/plugin-react@6.0.5' vitest@4.1.10 '@testing-library/react@16.3.2' '@testing-library/jest-dom@7.0.0' '@testing-library/dom@10.4.1' jsdom@30.0.1 eslint@10.8.0 '@eslint/js@10.0.1' typescript-eslint@8.66.0 eslint-plugin-react-hooks@7.1.1 eslint-plugin-react-refresh@0.5.3 '@types/three@0.185.3' '@types/react@19.2.18' '@types/react-dom@19.2.4' '@types/node@26.1.2'
npm config get engine-strict
node -e "<direct engine-range checks using installed semver>"
npm install --save-dev --save-exact -- eslint@9.39.5 '@eslint/js@9.39.5' '@types/node@24.13.3'
npm ls --all
npm ls --depth=0
npm run lint
npm test -- --run
npm run build
npx tsc --noEmit
npm audit --json
npm audit --omit=dev --json
npm pkg get dependencies devDependencies
node -e "<recursive installed-package engine scan using installed semver>"
~~~

The latest registry query ran for React, React DOM, TypeScript, Vite, `@vitejs/plugin-react`, Vitest, Testing Library React, jest-dom, jsdom, ESLint, `@eslint/js`, typescript-eslint, both React lint plugins, Three.js, `@types/three`, Fiber, and Drei. Supporting React/DOM/Node/Testing Library DOM metadata and all 21 final exact specs were also queried. The first registry call failed in the network-restricted sandbox with `ENOTCACHED` and was repeated successfully with authorized registry access. The first test and build commands were sandbox-blocked and were repeated successfully as disclosed above.

### Cleanup

~~~powershell
Resolve-Path -LiteralPath <exact temporary root>
[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
Remove-Item -LiteralPath <exact temporary root> -Recurse -Force
Test-Path -LiteralPath <exact temporary root>
~~~

The first removal attempt reported access denied for the sandbox-owned pytest cache and left the root present. The authorized exact-target retry returned exit 0 and `TEMP_EXISTS=False`.

## Stage 0.2.2 implementation disposition

This subsequent disposition records how the reviewed Stage 0.2.1 evidence was used by
the separately authorized Stage 0.2.2 task. It does not rewrite the historical preflight
record above.

- The permanent runtime pins are FastAPI 0.141.1, Pydantic 2.13.4,
  pydantic-settings 2.14.2, and Uvicorn 0.52.1.
- The optional persistence declaration pins are SQLAlchemy 2.0.51, Alembic 1.18.5,
  and psycopg 3.3.4 with its binary extra. Import availability is implemented and
  tested; PostgreSQL execution, ORM entities, migrations, and persistence behavior are
  not implemented.
- The permanent development pins are pytest 9.1.1, pytest-cov 7.1.0, Hypothesis
  6.165.0, HTTPX 0.28.1, Ruff 0.16.1, and mypy 2.3.0.
- A separate disposable Python 3.14.6/pip 26.1.2 tooling preflight accepted
  pip-tools 7.6.0, Setuptools 83.0.0, and Wheel 0.47.0. Setuptools 83.0.0 is the exact
  build backend.
- `backend/pyproject.toml` is the direct-dependency authority.
  `backend/requirements/requirements-dev-py314.lock.txt` is the provisional Windows/
  Python 3.14 development resolution generated by pip-tools with backtracking, stripped
  extras, unsafe tooling pins, exact direct pins, and SHA-256 hashes.
- Two final generations were byte-for-byte identical. Clean installations with
  `--require-hashes --only-binary=:all:` succeeded, `pip check` passed, and the package
  wheel passed content and third-environment install/API smoke audits.
- pip's experimental `pip lock` and a `pylock` workflow were not selected as the sole
  authority in this stage.

Stage 0.2.2 implementation is complete, reviewed, and committed and is accepted as a
provisional backend foundation. At the point captured by this Stage 0.2.2 disposition,
Stage 0.2.3 had not started. This
implementation remains provisional; it is not a final production freeze, deployment
approval, engineering calculation approval, or commercial release.

The generated requirements file is specifically a provisional CPython 3.14 Windows
development lock. It is not the final Linux, CI, container, cloud, or production-
deployment lock and must not be generalized beyond its tested environment without
another controlled validation task. Cross-platform reproduction, production lock and
deployment design, Python dependency vulnerability/license/provenance scanning,
PostgreSQL execution, and final production approval remain pending.

## Stage 0.2.3 implementation disposition

This subsequent disposition records how the reviewed Stage 0.2.1 frontend evidence was
used by the separately authorized Stage 0.2.3 task. It preserves the historical
preflight evidence above and does not convert any provisional selection into a final
production freeze.

- The exact runtime is Node 24.18.0 with npm 11.16.0. The private, unversioned package
  declares `npm@11.16.0`, exact direct pins, and narrow provisional engine ranges.
- Runtime pins are React 19.2.8 and React DOM 19.2.8.
- Tooling pins are TypeScript 6.0.3, Vite 8.2.0, `@vitejs/plugin-react` 6.0.5, Vitest
  4.1.10, `@vitest/coverage-v8` 4.1.10, React Testing Library 16.3.2, Testing Library
  DOM 10.4.1, jest-dom 7.0.0, jsdom 30.0.1, ESLint and `@eslint/js` 9.39.5,
  typescript-eslint 8.66.0, React Hooks plugin 7.1.1, React Refresh plugin 0.5.3,
  React types 19.2.18, React DOM types 19.2.4, and Node types 24.13.3.
- A separate disposable package proved Vitest 4.1.10 and
  `@vitest/coverage-v8` 4.1.10 together on the exact runtime: one test passed with 100%
  V8 coverage, the dependency tree was valid, and all npm audit severities were zero.
- `package-lock.json` is the authoritative exact resolved tree for Stage 0.2.3. It is
  lockfile version 3, uses only the public npm registry, and has unchanged SHA-256
  `E0F3FE693B6FDED14ADB4282E2820E9862B4E442145C24F3A6290F814B42DA65`.
  Public-registry lock records total 290 nonroot entries plus the root record, for 291
  total.
- `npm ci` is the controlling install and reproducibility command. Two independent
  clean installations consumed the accepted existing lock and produced 266 normalized
  installed locations each. Their identical normalized tree hash was
  `E9BF9E4B1AA0A28402E2B262C2758C4365651F7AC6BB791D890DD6F59CD63192`.
  `npm ls --all` reported no invalid, missing-required, or peer-conflicted dependency,
  and neither installation nor QA changed `package.json`, `package-lock.json`, or
  `.npmrc`.
- Fresh lock generation from `package.json` alone is dependency-update resolution, not
  the controlling reproduction test. That separate resolution found
  `electron-to-chromium` 1.5.401 available instead of the accepted lock's 1.5.400 and
  `node-releases` 2.0.52 instead of 2.0.51. Both transitive updates are deferred to a
  separate controlled dependency-maintenance task; the difference is not a defect in
  the accepted lock.
- The bootstrap and aggregate frontend-check scripts passed. Repository-local and both
  clean-copy quality gates passed zero-warning lint, strict typing, 35 tests in 2
  files, 100% statements/branches/functions/lines, and a three-file Vite production
  build with 22 transformed modules, zero warnings, and no source maps. Built sizes
  were 529-byte `index.html`, 195,692-byte JavaScript, and 5,212-byte CSS.
- Full and runtime-only npm audits each reported zero vulnerabilities at all
  severities. No audit result was suppressed or repaired automatically.
- The loopback-only production preview returned HTTP 200 and referenced built assets;
  its process and logs were removed. The build, coverage output, clean-install copies,
  normalized trees, caches, and validation logs were deleted after validation. No
  repository-controlled file changed.
- Three.js, `@types/three`, React Three Fiber, and Drei remain deferred. Future 3D
  implementation must derive from canonical geometry and lazy-load or otherwise split
  the visualization workspace from the initial route.

Stage 0.2.3 implementation is complete and reviewed, its controlled validation passed,
and the frontend package, lock strategy, and native-CSS shell are provisionally
accepted as the frontend application foundation. The exact Windows runtime remains
provisional. This is not a final production dependency freeze, supported cross-platform
range, deployment approval, engineering calculation approval, design-system freeze, or
commercial release. Stage 0.2.4 has not started.

Real-browser screen-reader, automated contrast, browser zoom, real-device responsive,
real-browser reduced-motion, end-to-end browser, Linux/CI, and current Node patch
validation remain pending, as do API integration, authentication, project ownership,
engineering geometry, visualization, calculation capability, production supply-chain
review, and final production approval. The 100% coverage applies only to the current
Stage 0.2.3 executable shell; it validates neither engineering mathematics nor an
engineering calculation engine or commercial use.

## Stage 0.2.4 integrated QA and CI disposition

This subsequent disposition records the separately authorized integrated repository
QA and initial CI implementation. It preserves the historical Stage 0.2.1 through
0.2.3 evidence above and does not convert a provisional toolchain into a production
freeze.

- `scripts/check-all.ps1` is the controlling repository-level Windows command. It
  validates the handoff JSON, runs the existing backend and frontend bootstrap/check
  scripts in order, runs both npm audits, checks repository whitespace, and requires
  an empty Git index.
- `.github/workflows/ci.yml` uses GitHub Actions with independent backend and frontend
  matrices on `ubuntu-24.04` and `windows-2025`. Both matrices use `fail-fast: false`
  and 25-minute timeouts.
- The workflow uses `actions/checkout@v7`, `actions/setup-python@v7`, and
  `actions/setup-node@v7` with exact Python 3.14.6 and Node 24.18.0 runtime values.
- Top-level permission is `contents: read`; checkout credential persistence is
  disabled. No secret, environment, artifact upload, package publication, release,
  deployment, Git commit, or Git push exists in the workflow.
- Backend CI retains `--require-hashes --only-binary=:all:` and editable
  `--no-deps --no-build-isolation` controls. A Linux incompatibility is allowed to
  fail visibly and requires a separate cross-platform-lock decision.
- Frontend CI uses the unchanged authoritative lock through `npm ci`, then runs the
  existing dependency-tree, lint, strict-type, coverage, build, and audit commands.

Local integrated QA passed before commit. The workflow is committed and pushed, but
hosted GitHub Actions confirmation remains pending manual review. macOS, real-browser
accessibility, production lock design, immutable action-SHA pinning, final supported
runtime ranges, engineering-domain validation, and calculation validation remain
pending. No dependency, source, test, engineering behavior, or production/deployment
configuration was added or changed by this disposition.

## Stage 2.3 visualization dependency disposition

The previously verified compatible versions are now exact permanent Stage 2.3
frontend dependencies: `three` `0.185.1`, `@react-three/fiber` `9.7.0`, and
`@types/three` `0.185.3`. Their declared peers remain satisfied by the existing exact
React 19.2.8, React DOM 19.2.8, TypeScript 6.0.3, and Vite 8.2.0 tree. The canonical
scene component is lazy-loaded so Three/Fiber do not enter the initial workspace
module synchronously.

No Drei, CSS framework, state library, decimal package, router, API client framework,
CAD/geometry library, or backend dependency was added. `npm ci`, `npm ls --all`, the
configured test/coverage gate, strict TypeScript, ESLint, production build, full
audit, and runtime-only audit remain required. This implementation evidence is not a
production runtime-range freeze or a final supply-chain approval.
