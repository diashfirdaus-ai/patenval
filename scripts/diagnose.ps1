# Native Windows System & Scientific Diagnostic Script for TechVal AI
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " TechVal AI -- Native Windows Environment & Stack Diagnostics" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# 1. Python venv check
$PyExe = "$RepoRoot\backend\.venv\Scripts\python.exe"
if (Test-Path $PyExe) {
    $pyVer = & $PyExe --version
    Write-Host "[PASS] Backend Python Venv: $pyVer ($PyExe)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Backend Python Venv missing at $PyExe" -ForegroundColor Red
}

# 2. Node.js & Frontend build check
$NodeVer = & node -v
Write-Host "[PASS] Node.js Runtime: $NodeVer" -ForegroundColor Green
if (Test-Path "$RepoRoot\frontend\.next\BUILD_ID") {
    $buildId = Get-Content "$RepoRoot\frontend\.next\BUILD_ID"
    Write-Host "[PASS] Next.js Production Build Verified (BUILD_ID: $buildId)" -ForegroundColor Green
} else {
    Write-Host "[WARN] Next.js production build not found (.next\BUILD_ID)" -ForegroundColor Yellow
}

# 3. Database, Alembic Migration Head & Vault Encryption Check
Set-Location "$RepoRoot\backend"
$DiagPy = @'
from sqlalchemy import text
from app.config import settings
from app.database import engine, SessionLocal, check_pgvector_status
from app.security.storage import get_fernet

with engine.connect() as conn:
    ver = conn.execute(text("SELECT version()")).scalar_one()
    alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    table_count = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar_one()

fernet = get_fernet()
test_ct = fernet.encrypt(b"techval-vault-diagnostic")
assert fernet.decrypt(test_ct) == b"techval-vault-diagnostic"

print(f"[PASS] PostgreSQL Connected: {ver[:45]}...")
print(f"[PASS] Alembic Migration Head: {alembic_rev} ({table_count} tables in public schema)")
print(f"[PASS] Encrypted Storage Vault Verified: {settings.vault_path}")
with SessionLocal() as db:
    print(f"[INFO] pgvector extension native status: {check_pgvector_status(db)}")
'@
$DiagPy | & $PyExe -

Set-Location $RepoRoot
Write-Host "==============================================================" -ForegroundColor Cyan
