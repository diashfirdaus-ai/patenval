# Native Windows Database Migration & Seeding Script for TechVal AI
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location "$RepoRoot\backend"

Write-Host "[TechVal AI] Running Alembic migrations against PostgreSQL..." -ForegroundColor Cyan
& ".\.venv\Scripts\alembic.exe" upgrade head

Write-Host "[TechVal AI] Ensuring baseline methodology, references, and demo fixtures are seeded..." -ForegroundColor Cyan
$SeedPy = @'
from app.database import SessionLocal
from app.services.seed import seed_initial_data
with SessionLocal() as db:
    res = seed_initial_data(db)
    print(f"[OK] Seed result: {res}")
'@
$SeedPy | & ".\.venv\Scripts\python.exe" -

Set-Location $RepoRoot
Write-Host "[OK] Database schema migrated and seeded." -ForegroundColor Green
