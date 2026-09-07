$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Python launcher 'py' was not found. Install Python 3.11 (64-bit) first."
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

if (-not (Test-Path ".venv")) {
  py -3.11 -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
New-Item -ItemType File -Path ".venv\.dependencies_installed" -Force | Out-Null

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run: .\\scripts\\run_dev.ps1"
Write-Host "SQLite database will be created automatically on first server start."
