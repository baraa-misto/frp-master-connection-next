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
    $backendRoot = Join-Path $repositoryRoot "backend"
    $virtualEnvironmentRoot = Join-Path $backendRoot ".venv"
    $virtualEnvironmentPython = Join-Path $virtualEnvironmentRoot "Scripts\python.exe"
    $lockFile = Join-Path $backendRoot "requirements\requirements-dev-py314.lock.txt"

    $basePython = Get-Command python -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $basePythonVersion = (& $basePython.Source --version 2>&1 | Out-String).Trim()
    Assert-NativeSuccess "Base Python version check"
    if ($basePythonVersion -ne "Python 3.14.6") {
        throw "Stage 0.2.2 requires Python 3.14.6; found '$basePythonVersion'."
    }
    Write-Host "Base interpreter: $($basePython.Source) ($basePythonVersion)"

    if (-not (Test-Path -LiteralPath $virtualEnvironmentPython -PathType Leaf)) {
        & $basePython.Source -m venv $virtualEnvironmentRoot
        Assert-NativeSuccess "Backend virtual-environment creation"
    }

    $environmentPythonVersion = (& $virtualEnvironmentPython --version 2>&1 | Out-String).Trim()
    Assert-NativeSuccess "Backend Python version check"
    if ($environmentPythonVersion -ne "Python 3.14.6") {
        throw "Backend environment requires Python 3.14.6; found '$environmentPythonVersion'."
    }

    $pipVersion = (& $virtualEnvironmentPython -m pip --version 2>&1 | Out-String).Trim()
    Assert-NativeSuccess "Backend pip version check"
    if ($pipVersion -notmatch '^pip 26\.1\.2(?:\s|$)') {
        throw "Stage 0.2.2 requires the environment-provided pip 26.1.2; found '$pipVersion'."
    }
    Write-Host "Backend interpreter: $virtualEnvironmentPython ($environmentPythonVersion)"
    Write-Host "Backend pip: $pipVersion"

    if (-not (Test-Path -LiteralPath $lockFile -PathType Leaf)) {
        throw "Required lock file is missing: $lockFile"
    }

    & $virtualEnvironmentPython -m pip install --require-hashes --only-binary=:all: --requirement $lockFile
    Assert-NativeSuccess "Hash-locked dependency installation"

    & $virtualEnvironmentPython -m pip install --no-deps --no-build-isolation --editable $backendRoot
    Assert-NativeSuccess "Editable backend installation"

    & $virtualEnvironmentPython -m pip check
    Assert-NativeSuccess "Installed dependency consistency check"

    & $virtualEnvironmentPython -c @'
from importlib.metadata import version

for distribution in (
    'frp-master-connection',
    'pip',
    'pip-tools',
    'setuptools',
    'wheel',
):
    print(f'{distribution}=={version(distribution)}')
'@
    Assert-NativeSuccess "Installed baseline version report"

    Write-Host "Backend environment is ready: $virtualEnvironmentRoot"
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
