[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"

function Invoke-QualityGate {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,

        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    Write-Host "==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

try {
    $repositoryRoot = Split-Path -Parent $PSScriptRoot
    $backendRoot = Join-Path $repositoryRoot "backend"
    $virtualEnvironmentPython = Join-Path $backendRoot ".venv\Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $virtualEnvironmentPython -PathType Leaf)) {
        throw "Backend environment is missing. Run scripts/backend-bootstrap.ps1 first."
    }

    $environmentPythonVersion = (& $virtualEnvironmentPython --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Backend Python version check failed with exit code $LASTEXITCODE."
    }
    if ($environmentPythonVersion -ne "Python 3.14.6") {
        throw "Backend checks require Python 3.14.6; found '$environmentPythonVersion'."
    }
    Write-Host "Backend interpreter: $virtualEnvironmentPython ($environmentPythonVersion)"

    Push-Location $backendRoot
    try {
        Invoke-QualityGate "Dependency consistency" {
            & $virtualEnvironmentPython -m pip check
        }
        Invoke-QualityGate "Ruff formatting" {
            & $virtualEnvironmentPython -m ruff format --check .
        }
        Invoke-QualityGate "Ruff linting" {
            & $virtualEnvironmentPython -m ruff check .
        }
        Invoke-QualityGate "Strict mypy analysis" {
            & $virtualEnvironmentPython -m mypy --strict src tests
        }
        Invoke-QualityGate "Pytest with branch coverage" {
            & $virtualEnvironmentPython -m pytest `
                --cov=frp_master_connection `
                --cov-branch `
                --cov-report=term-missing `
                --cov-fail-under=100
        }
        Invoke-QualityGate "Uvicorn CLI availability" {
            & $virtualEnvironmentPython -m uvicorn --help
        }
        Invoke-QualityGate "Alembic CLI availability" {
            & $virtualEnvironmentPython -m alembic --help
        }
        Invoke-QualityGate "Runtime and persistence import smoke test" {
            & $virtualEnvironmentPython -c @'
import alembic
import fastapi
import httpx
import hypothesis
import mypy
import psycopg.pq
import pydantic
import pydantic_settings
import pytest
import ruff
import sqlalchemy
import uvicorn

assert psycopg.pq.__impl__ == 'binary'
'@
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "All backend quality gates passed."
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
