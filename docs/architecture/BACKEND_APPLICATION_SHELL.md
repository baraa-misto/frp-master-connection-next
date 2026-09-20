# Backend Application Shell

**Stage:** 2.2B stateless calculation transport added over the retained shell

**Starting baseline:** `4dc8a8b1ec0f5198d9deb5479f14b89ccf956359`

**Review disposition:** Accepted as a provisional backend foundation for Stage 0.2.3
planning. The production toolchain and deployment are not approved or frozen;
engineering approval remains limited to the separately controlled single-bolt slice.

## 1. Purpose and scope

Stage 0.2.2 establishes the first permanent, installable backend package, a minimal
FastAPI service shell, a trusted-identity boundary, and repeatable backend QA. It does
not establish an engineering calculation engine, persistence implementation, project
workflow, report generator, or commercial release.

## 2. Package structure and boundaries

The package uses the `backend/src/frp_master_connection` layout. `api`, `application`,
`infrastructure`, `reporting`, and `security` are outer or integration boundaries.
`domain`, `units`, `geometry`, `actions`, `topology`, `engineering_basis`,
`capabilities`, and `calculation` are framework-independent engineering-core package
boundaries. At this stage, the core packages contain documentation and empty public
exports only; no engineering model or numerical behavior exists.

An AST-based test recursively rejects external framework imports and outer-layer
imports from every engineering-core source file. It reports the offending file, line,
and import.

## 3. Packaging and dependency groups

`backend/pyproject.toml` is the single authoritative Python configuration. It uses
PEP 621 metadata, a static package/application version of `0.0.0.dev0`, a
`>=3.14,<3.15` packaging range, Setuptools 83.0.0 as the exact build backend, src-layout
package discovery, and `py.typed` package data.

The dependency groups are deliberately separate:

- Runtime: FastAPI 0.141.1, Pydantic 2.13.4, pydantic-settings 2.14.2, and Uvicorn
  0.52.1.
- Optional persistence declarations: SQLAlchemy 2.0.51, Alembic 1.18.5, and
  psycopg 3.3.4 with its binary extra. Their availability is validated; persistence
  itself is not implemented.
- Development: pytest 9.1.1, pytest-cov 7.1.0, Hypothesis 6.165.0, HTTPX 0.28.1,
  Ruff 0.16.1, and mypy 2.3.0.
- Tooling: pip-tools 7.6.0, Setuptools 83.0.0, and Wheel 0.47.0.

## 4. Lock generation and installation policy

`backend/requirements/requirements-dev-py314.lock.txt` contains runtime, persistence,
development, and tooling dependencies resolved on Windows with CPython 3.14.6 and pip
26.1.2. Every distribution is exactly pinned and SHA-256 hashed. No private index,
trusted-host override, direct URL, VCS reference, editable external dependency, or
local path is permitted.

This is specifically a provisional CPython 3.14 Windows development lock. It is not
the final Linux, CI, container, cloud, or production-deployment lock. Cross-platform
validation remains pending, and the lock must not be generalized beyond its tested
environment without another controlled validation task.

From `backend/`, the exact generation invocation is:

```powershell
$env:CUSTOM_COMPILE_COMMAND = 'python -m piptools compile --quiet --rebuild --extra dev --extra persistence --extra tooling --generate-hashes --resolver backtracking --strip-extras --allow-unsafe --upgrade --upgrade-package pip==26.1.2 --no-build-isolation --no-emit-index-url --no-emit-trusted-host --no-config --newline lf --output-file requirements/requirements-dev-py314.lock.txt pyproject.toml'
python -m piptools compile --quiet --rebuild --extra dev --extra persistence --extra tooling --generate-hashes --resolver backtracking --strip-extras --allow-unsafe --upgrade --upgrade-package pip==26.1.2 --no-build-isolation --no-emit-index-url --no-emit-trusted-host --no-config --newline lf --output-file requirements/requirements-dev-py314.lock.txt pyproject.toml
```

The final lock and a separately generated temporary copy must compare byte-for-byte.
Installation must use `pip install --require-hashes --only-binary=:all:`. These controls
must not be weakened to accommodate an incompatible artifact. Dependency changes
require controlled regeneration and the complete QA sequence.

## 5. Local environment and application factory

`scripts/backend-bootstrap.ps1` creates the ignored `backend/.venv`, verifies exact
Python and pip versions, installs the lock under hash and wheel-only enforcement,
installs the local package editable with `--no-deps --no-build-isolation`, and runs
`pip check`. It never upgrades pip or installs globally.

`frp_master_connection.api.app:create_app` is the composition root. Callers may select
local, test, or production application configuration and may inject a trusted identity
resolver. The module-level `frp_master_connection.api.app:app` is provided for local
Uvicorn execution only. Future production deployment must compose `create_app()` with
an explicitly supplied trusted production resolver. The module-level app is not the
final production composition root and must not be treated as one.

## 6. Endpoint contracts

`GET /health` returns a typed response containing only `status="healthy"`, product ID,
and application version. It requires no identity. Healthy means that the service
process can respond; it is not an engineering `PASS`, does not imply that calculations
exist, and reveals no secret, path, database identifier, internal address, or dependency
inventory.

`GET /api/v1/meta` consumes the trusted identity dependency and returns typed,
truthful runtime metadata: product ID; application, project-schema, calculation-engine,
and engineering-rule-set versions; code basis; errata status; and false calculation and
report availability flags. It returns no identity or ownership data and no engineering
result. The Stage 0.2.2 product OpenAPI path set contains only these two endpoints;
FastAPI documentation routes remain framework facilities.

## 7. Trusted identity boundary

`TrustedIdentity` is an immutable, framework-independent value object containing opaque
account and optional organization identifiers, roles, and authentication source.
`TrustedIdentityResolver` is the API-boundary abstraction. Identity is supplied by a
trusted server-side resolver, never a request body, query, path, or arbitrary client
header.

The resolver establishes trusted server-side identity context only. Identity resolution
alone is not project authorization, organization authorization, product entitlement,
billing enforcement, or subscription validation. Those controls remain future backend
responsibilities and require explicit server-side policy decisions for each protected
operation.

`LocalDevelopmentIdentity` deterministically supplies a fixed backend-owned development
account and no organization. It is production-incapable and is selected automatically
only for local or test configuration. Production construction fails closed unless an
explicit resolver marked production-capable is supplied; production also rejects the
local resolver. No authentication provider, login, session, JWT, OAuth, entitlement,
billing, user database, or organization database is selected or implemented.

The resolver's `production_capable` property is a composition guard: it prevents known
local/test resolvers from being selected while the application is configured for
production. It is not cryptographic proof, external-provider certification, or a
replacement for security review. Every future production adapter requires independent
implementation and security validation.

## 8. QA and package validation

`scripts/backend-check.ps1` runs, fail-fast: `pip check`, Ruff format, Ruff lint, strict
mypy over `src` and `tests`, pytest with 100% line and branch fail-under, Uvicorn and
Alembic CLI checks, and runtime/persistence import smoke checks. Tests cover endpoint
contracts, trusted identity injection and spoof resistance, production fail-closed
behavior, metadata consistency, OpenAPI scope, configuration safety, dependency imports,
and recursive architecture boundaries.

The 100% line and branch coverage result applies only to the current Stage 0.2.2
executable shell. It does not establish connection-calculation correctness, engineering
validation, or commercial validation.

Package validation builds exactly one wheel outside the repository with dependency
resolution and build isolation disabled. The wheel is audited for the package and
`py.typed`, and against tests, documentation, private references, generated artifacts,
environment files, and databases. A third clean Python 3.14.6 environment installs the
hash-checked binary lock and wheel, then repeats dependency, import, endpoint, identity,
and exact-version smoke checks. All temporary environments and wheel outputs are deleted
after validation.

The clean-wheel TestClient smoke exposed a visible Starlette deprecation warning for
its HTTPX fallback. The required smoke passed, no warning was suppressed, and no
untested replacement dependency was added. HTTPX/TestClient migration remains a future
controlled maintenance task.

## 9. Explicit exclusions

This shell contains no database table, ORM entity, migration, connection string,
project storage or endpoint, engineering geometry, member, material, bolt, action,
calculation request or result, fingerprint, equation, numerical code criterion,
capacity, resistance or time-effect factor, force distribution, utilization, limit
state, engineering `PASS`/`FAIL`, visualization, report, frontend, CI workflow, Docker
configuration, licensed standard excerpt, or private engineering source.

## 10. Remaining risks

- Linux reproduction and CI validation are pending.
- A production-specific lock and deployment design are pending.
- Python dependency security, license, and provenance scanning are pending.
- PostgreSQL execution and production driver selection are pending.
- An authentication provider has not been selected.
- Entitlement and billing behavior are not implemented.
- The calculation engine and all engineering slices remain unimplemented.

Stage 0.2.2 implementation is complete and reviewed and is accepted as a provisional
backend foundation for Stage 0.2.3 planning. Stage 0.2.3 has not started. Nothing in
this disposition is an engineering approval, commercial validation, production
approval, or production toolchain/deployment freeze.

## 11. Stage 2.2B API extension

The shell now registers exactly one engineering route in addition to `/health` and
`/api/v1/meta`: `POST /api/v1/calculations/single-bolt/evaluate`. It reuses the same
trusted identity dependency and delegates through a strict Pydantic transport mapper
to the framework-independent Stage 2.2A service. The route is stateless, creates no
project or calculation record, accepts no client identity/result/version/fingerprint
authority, and calls no equation primitive. Valid engineering FAIL, unsupported,
review, qualification, source-pending, and unavailable-distribution results use HTTP
200; malformed transport uses HTTP 422. Frontend, persistence, reports,
authorization, entitlement, billing, and deployment remain absent.
