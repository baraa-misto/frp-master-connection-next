# Scripts

Stage 0.2.2 adds two Windows PowerShell entry points for the backend foundation:

- `backend-bootstrap.ps1` creates and validates the project-local Python environment
  from the hash-bearing, binary-only dependency lock.
- `backend-check.ps1` runs the backend QA gates in a fail-fast sequence.

Both scripts derive paths from `$PSScriptRoot`, require the provisional CPython 3.14.6
and pip 26.1.2 baseline, and avoid global or user-site installation. They do not run an
engineering calculation and do not validate any engineering result.

Stage 0.2.3 adds two corresponding frontend entry points:

- `frontend-bootstrap.ps1` verifies Node 24.18.0 and npm 11.16.0, runs `npm ci`,
  validates the complete dependency tree, and reports exact direct-tool versions.
- `frontend-check.ps1` runs dependency-tree, zero-warning ESLint, strict TypeScript,
  100%-threshold Vitest coverage, and production-build gates in fail-fast order.

The frontend scripts derive all paths from `$PSScriptRoot`, install only into the
ignored project-local `frontend/node_modules`, and never upgrade or install a runtime
globally. They implement and validate no engineering calculation.

The reviewed Stage 0.2.3 validation ran both scripts successfully. The bootstrap used
the authoritative existing `package-lock.json` through `npm ci` and produced a valid
dependency tree without changing `package.json`, `package-lock.json`, or `.npmrc`.
The aggregate check passed zero-warning ESLint, strict TypeScript, 35 tests in two
files, 100% coverage for the current executable shell, and the production build. These
results establish no engineering or commercial validation.

Stage 0.2.4 adds `check-all.ps1`, the repository-level Windows PowerShell orchestrator.
It validates the handoff manifest, runs both backend scripts followed by both frontend
scripts, runs full and runtime-only npm audits, checks repository whitespace, and
requires an empty Git index. It derives paths from `$PSScriptRoot`, restores the
caller's working directory, exposes command output, and fails immediately on a nonzero
exit code. Its success means only that the current software foundations passed their
configured gates; it does not validate engineering calculations, and none are
implemented.
