[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-NativeSuccess {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Description
    )

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

$originalLocation = Get-Location

try {
    $repositoryRoot = Split-Path -Parent $PSScriptRoot
    $frontendRoot = Join-Path $repositoryRoot "frontend"
    $manifestPath = Join-Path $repositoryRoot "HANDOFF_MANIFEST.json"
    $backendBootstrap = Join-Path $PSScriptRoot "backend-bootstrap.ps1"
    $backendCheck = Join-Path $PSScriptRoot "backend-check.ps1"
    $frontendBootstrap = Join-Path $PSScriptRoot "frontend-bootstrap.ps1"
    $frontendCheck = Join-Path $PSScriptRoot "frontend-check.ps1"

    $pythonCommand = Get-Command python -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $powerShellCommand = Get-Command powershell -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $npmCommand = Get-Command npm -ErrorAction Stop | Select-Object -First 1
    $gitCommand = Get-Command git -CommandType Application -ErrorAction Stop |
        Select-Object -First 1

    Set-Location -LiteralPath $repositoryRoot

    Write-Host "==> Validate handoff manifest JSON"
    & $pythonCommand.Source -m json.tool $manifestPath
    Assert-NativeSuccess "Handoff manifest JSON validation"

    Write-Host "==> Bootstrap backend"
    & $powerShellCommand.Source -NoProfile -ExecutionPolicy Bypass -File $backendBootstrap
    Assert-NativeSuccess "Backend bootstrap"

    Write-Host "==> Run backend quality gates"
    & $powerShellCommand.Source -NoProfile -ExecutionPolicy Bypass -File $backendCheck
    Assert-NativeSuccess "Backend quality gates"

    Write-Host "==> Bootstrap frontend"
    & $powerShellCommand.Source -NoProfile -ExecutionPolicy Bypass -File $frontendBootstrap
    Assert-NativeSuccess "Frontend bootstrap"

    Write-Host "==> Run frontend quality gates"
    & $powerShellCommand.Source -NoProfile -ExecutionPolicy Bypass -File $frontendCheck
    Assert-NativeSuccess "Frontend quality gates"

    Set-Location -LiteralPath $frontendRoot

    Write-Host "==> Audit all frontend dependencies"
    & $npmCommand.Source audit --json
    Assert-NativeSuccess "Full frontend dependency audit"

    Write-Host "==> Audit frontend runtime dependencies"
    & $npmCommand.Source audit --omit=dev --json
    Assert-NativeSuccess "Runtime-only frontend dependency audit"

    Set-Location -LiteralPath $repositoryRoot

    Write-Host "==> Check repository whitespace"
    & $gitCommand.Source diff --check
    Assert-NativeSuccess "Repository whitespace check"

    Write-Host "==> Confirm no staged files"
    $stagedPaths = @(& $gitCommand.Source diff --cached --name-only)
    Assert-NativeSuccess "Staged-file query"
    $stagedPaths | ForEach-Object { Write-Host $_ }
    if ($stagedPaths.Count -ne 0) {
        throw "Integrated QA requires an empty index; found $($stagedPaths.Count) staged path(s)."
    }

    Write-Host "Integrated software QA completed successfully."
    Write-Host "The repository contains a limited verified calculation slice."
    Write-Host "Software QA does not establish general engineering validation or code coverage beyond the explicitly verified calculation families."
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Set-Location -LiteralPath $originalLocation.Path
}
