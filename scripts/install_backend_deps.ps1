<#
Install backend dependencies using the current python interpreter only if it is compatible.

This script runs backend/ensure_python_compat.py to verify the interpreter is Python 3.11.
If the check passes it installs requirements into the current interpreter (not into a venv).
Prefer using scripts/setup_backend.ps1 which creates a dedicated venv instead.

Usage (PowerShell):
  ./scripts/install_backend_deps.ps1
#>

function Write-Err($msg){ Write-Host "ERROR: $msg" -ForegroundColor Red }
function Write-Ok($msg){ Write-Host "INFO: $msg" -ForegroundColor Green }

$root = Resolve-Path -Path .
$check = Join-Path $root 'backend\ensure_python_compat.py'

if (-not (Test-Path $check)){
	Write-Err "Missing $check"
	exit 1
}

Write-Host "Running python preinstall compatibility check..."
& python $check
if ($LASTEXITCODE -ne 0) {
	Write-Err "Python interpreter not compatible. Install Python 3.11 or use scripts/setup_backend.ps1"
	exit 1
}

Write-Ok "Compatibility check passed. Installing requirements into current interpreter..."
& python -m pip install --upgrade pip
& python -m pip install -r backend/requirements.txt

if ($LASTEXITCODE -eq 0) { Write-Ok "Dependencies installed." } else { Write-Err "pip install failed."; exit 1 }
