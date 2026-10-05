<#
Setup backend development virtual environment using Python 3.11.

This script attempts to find a Python 3.11 interpreter (via the py launcher or PATH),
creates a virtual environment at backend\.venv and installs requirements into it.

Usage (PowerShell):
  ./scripts/setup_backend.ps1

If Python 3.11 is not installed, the script will print instructions to install it.
#>

function Write-Err($msg){ Write-Host "ERROR: $msg" -ForegroundColor Red }
function Write-Ok($msg){ Write-Host "INFO: $msg" -ForegroundColor Green }

$pythonCmd = $null

Write-Host "Detecting Python 3.11..."
try {
	$exe = (& py -3.11 -c "import sys; print(sys.executable)") -join ""
	if ($exe) { $pythonCmd = $exe }
} catch { }

if (-not $pythonCmd) {
	try {
		$p = Get-Command python3.11 -ErrorAction Stop
		$pythonCmd = $p.Source
	} catch { }
}

if (-not $pythonCmd) {
	try {
		$p = Get-Command python -ErrorAction Stop
		$ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
		if ($ver.Trim() -eq '3.11') { $p2 = Get-Command python -ErrorAction Stop; $pythonCmd = $p2.Source }
	} catch { }
}

if (-not $pythonCmd) {
	Write-Err "Python 3.11 not found on PATH. Install Python 3.11 and re-run this script."
	Write-Host "Recommended: https://www.python.org/downloads/release/python-311x/"
	exit 1
}

Write-Ok "Using interpreter: $pythonCmd"

Push-Location "backend"
try {
	$venvPath = Join-Path (Get-Location) ".venv"
	if (-not (Test-Path $venvPath)) {
		Write-Host "Creating virtual environment at backend\.venv..."
		& $pythonCmd -m venv .venv
	} else {
		Write-Host "Virtual environment already exists at backend\.venv"
	}

	$pyExe = Join-Path $venvPath "Scripts\python.exe"
	if (-not (Test-Path $pyExe)) {
		Write-Err "Failed to find python executable in virtual environment: $pyExe"
		exit 1
	}

	Write-Host "Upgrading pip and installing backend requirements (this may take a while)..."
	& $pyExe -m pip install --upgrade pip
	& $pyExe -m pip install -r requirements.txt

	Write-Ok 'Dependencies installed into backend\.venv. To activate run: .\\backend\\.venv\\Scripts\\Activate.ps1'
} finally {
	Pop-Location
}
