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

try {
    $repositoryRoot = Split-Path -Parent $PSScriptRoot
    $frontendRoot = Join-Path $repositoryRoot "frontend"
    $packageManifest = Join-Path $frontendRoot "package.json"
    $packageLock = Join-Path $frontendRoot "package-lock.json"
    $nodeCommand = Get-Command node -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $npmCommand = Get-Command npm -ErrorAction Stop | Select-Object -First 1

    $nodeVersion = (& $nodeCommand.Source --version 2>&1 | Out-String).Trim()
    Assert-NativeSuccess "Node version check"
    if ($nodeVersion -ne "v24.18.0") {
        throw "The controlled frontend requires Node v24.18.0; found '$nodeVersion'."
    }

    $npmVersion = (& $npmCommand.Source --version 2>&1 | Out-String).Trim()
    Assert-NativeSuccess "npm version check"
    if ($npmVersion -ne "11.16.0") {
        throw "The controlled frontend requires npm 11.16.0; found '$npmVersion'."
    }

    if (-not (Test-Path -LiteralPath $packageManifest -PathType Leaf)) {
        throw "Required package manifest is missing: $packageManifest"
    }
    if (-not (Test-Path -LiteralPath $packageLock -PathType Leaf)) {
        throw "Required package lock is missing: $packageLock"
    }

    Write-Host "Node: $nodeVersion ($($nodeCommand.Source))"
    Write-Host "npm: $npmVersion ($($npmCommand.Source))"

    Push-Location -LiteralPath $frontendRoot
    try {
        & $npmCommand.Source ci
        Assert-NativeSuccess "Clean frontend dependency installation"

        & $npmCommand.Source ls --all
        Assert-NativeSuccess "Frontend dependency-tree validation"

        & $nodeCommand.Source -e @'
const { readFileSync } = require('node:fs');
const packages = [
  ['React', 'react'],
  ['React DOM', 'react-dom'],
  ['TypeScript', 'typescript'],
  ['Vite', 'vite'],
  ['Vitest', 'vitest'],
  ['ESLint', 'eslint'],
  ['Three.js', 'three'],
  ['React Three Fiber', '@react-three/fiber'],
  ['Three.js types', '@types/three'],
];
for (const [label, packageName] of packages) {
  const packageJson = JSON.parse(readFileSync(`node_modules/${packageName}/package.json`, 'utf8'));
  console.log(`${label} ${packageJson.version}`);
}
'@
        Assert-NativeSuccess "Frontend direct-version report"
    }
    finally {
        Pop-Location
    }

    Write-Host "Frontend environment is ready: $frontendRoot"
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
