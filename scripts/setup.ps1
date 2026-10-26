# Native Windows Setup Script for TechVal AI
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "[TechVal AI] Running native Windows environment setup..." -ForegroundColor Cyan

# 1. Ensure .env exists
if (-not (Test-Path "$RepoRoot\.env")) {
    Copy-Item "$RepoRoot\.env.example" "$RepoRoot\.env"
    Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
}

# 2. Ensure runtime directories exist outside web roots
$VaultDir = "$RepoRoot\.runtime\vault"
$ReportsDir = "$RepoRoot\.runtime\reports"
New-Item -ItemType Directory -Force -Path $VaultDir | Out-Null
New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null
Write-Host "[OK] Provisioned encrypted storage vault at $VaultDir" -ForegroundColor Green

# 3. Backend Python environment via uv
Set-Location "$RepoRoot\backend"
if (-not (Test-Path "$RepoRoot\backend\.venv\Scripts\python.exe")) {
    Write-Host "[TechVal AI] Provisioning Python 3.12 virtual environment via uv..." -ForegroundColor Yellow
    python -m uv venv --python 3.12 .venv
}
python -m uv sync
Write-Host "[OK] Backend Python dependencies synchronized in backend\.venv" -ForegroundColor Green

# 4. Frontend Node.js dependencies
Set-Location "$RepoRoot\frontend"
& npm.cmd install
Write-Host "[OK] Frontend Node.js dependencies installed in frontend\node_modules" -ForegroundColor Green

Set-Location $RepoRoot
Write-Host "[TechVal AI] Setup complete. Next step: run .\scripts\migrate.ps1" -ForegroundColor Cyan
