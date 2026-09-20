# Backend

Stage 0.2.2 provides an installable proprietary Python package and a minimal FastAPI
service shell. It exposes service health and truthful product metadata only. It has no
project management, persistence implementation, engineering calculation, geometry,
visualization, or report capability, and it is not an engineering design tool.

## Local setup

From the repository root, use the controlled scripts. They require CPython 3.14.6 and
its environment-provided pip 26.1.2; neither script installs globally or upgrades pip.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\backend-bootstrap.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\backend-check.ps1
```

The bootstrap creates the ignored `backend/.venv`, installs the fully hashed lock with
binary-only enforcement, installs this package editable without dependency resolution
or build isolation, and runs `pip check`. The check script runs dependency consistency,
formatting, lint, strict typing, line and branch coverage, CLI smoke checks, and import
checks in a fail-fast sequence.

Run the local service from the repository root with:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn frp_master_connection.api.app:app --app-dir .\backend\src --host 127.0.0.1 --port 8000
```

The product endpoints are limited to `GET /health` and `GET /api/v1/meta`. `/health`
reports process/service health, never an engineering `PASS`. The metadata route consumes
a trusted server-side identity but does not return identity data.

`frp_master_connection.api.app:app` is a local-development entry point that uses the
fixed local-development identity. Future production deployment must call `create_app()`
with an explicitly supplied trusted production resolver. The module-level app is not
the final production composition root and must not be treated as production identity
configuration.

See `requirements/README.md` for lock provenance and
`../docs/architecture/BACKEND_APPLICATION_SHELL.md` for the controlled architecture.
