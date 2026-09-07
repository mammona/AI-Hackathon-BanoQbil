$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

if (-not (Test-Path ".venv")) {
  Write-Host "Creating Python 3.11 virtual environment..."
  py -3.11 -m venv .venv
}

.\.venv\Scripts\Activate.ps1

if (-not (Test-Path ".venv\.dependencies_installed")) {
  Write-Host "Installing Python dependencies (first run can take time because of PyTorch)..."
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  New-Item -ItemType File -Path ".venv\.dependencies_installed" -Force | Out-Null
}

Write-Host ""
Write-Host "Database: SQLite (fasal_guard.db). No Docker/PostgreSQL required."
Write-Host "API: http://127.0.0.1:8000"
Write-Host "Swagger: http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "Starting FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
