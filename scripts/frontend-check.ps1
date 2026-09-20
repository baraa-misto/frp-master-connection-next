[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
    $frontendRoot = Join-Path $repositoryRoot "frontend"
    $nodeModules = Join-Path $frontendRoot "node_modules"
    $nodeCommand = Get-Command node -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $npmCommand = Get-Command npm -ErrorAction Stop | Select-Object -First 1

    $nodeVersion = (& $nodeCommand.Source --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $nodeVersion -ne "v24.18.0") {
        throw "Frontend checks require Node v24.18.0; found '$nodeVersion'."
    }
    $npmVersion = (& $npmCommand.Source --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $npmVersion -ne "11.16.0") {
        throw "Frontend checks require npm 11.16.0; found '$npmVersion'."
    }
    if (-not (Test-Path -LiteralPath $nodeModules -PathType Container)) {
        throw "Frontend dependencies are missing. Run scripts/frontend-bootstrap.ps1 first."
    }

    Write-Host "Frontend runtime: Node $nodeVersion; npm $npmVersion"
    Push-Location -LiteralPath $frontendRoot
    try {
        Invoke-QualityGate "Dependency tree" {
            & $npmCommand.Source ls --all
        }
        Invoke-QualityGate "ESLint" {
            & $npmCommand.Source run lint
        }
        Invoke-QualityGate "Strict TypeScript" {
            & $npmCommand.Source run typecheck
        }
        Invoke-QualityGate "Vitest with coverage" {
            & $npmCommand.Source run test:coverage
        }
        Invoke-QualityGate "Production build" {
            & $npmCommand.Source run build
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "All frontend quality gates passed."
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
