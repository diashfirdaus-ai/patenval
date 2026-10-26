# Native Windows Start Script for TechVal AI (Backend + Worker + Frontend)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

New-Item -ItemType Directory -Force -Path "$RepoRoot\.runtime" | Out-Null

# Ensure portable PostgreSQL is running if provisioned in Temp
$PortablePgCtl = "C:\Users\Diashfirdaus\AppData\Local\Temp\opencode\pgsql\pg16\bin\pg_ctl.exe"
$PortablePgData = "C:\Users\Diashfirdaus\AppData\Local\Temp\opencode\pgsql\data"
if (Test-Path $PortablePgCtl) {
    $statusOut = & $PortablePgCtl -D $PortablePgData status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[TechVal AI] Starting portable PostgreSQL 16 cluster..." -ForegroundColor Yellow
        & $PortablePgCtl -D $PortablePgData -l "C:\Users\Diashfirdaus\AppData\Local\Temp\opencode\pgsql\postgres.log" start
    }
}

Write-Host "[TechVal AI] Starting FastAPI Backend & LangGraph Worker on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$BackendProc = Start-Process -FilePath "$RepoRoot\backend\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory "$RepoRoot\backend" `
    -PassThru -WindowStyle Hidden

Write-Host "[TechVal AI] Starting Next.js Frontend on http://127.0.0.1:3000 ..." -ForegroundColor Cyan
$FrontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c npm.cmd run start" `
    -WorkingDirectory "$RepoRoot\frontend" `
    -PassThru -WindowStyle Hidden

$PidsObj = @{
    backend_pid  = $BackendProc.Id
    frontend_pid = $FrontendProc.Id
    started_at   = (Get-Date).ToString("o")
}
$PidsObj | ConvertTo-Json | Set-Content "$RepoRoot\.runtime\pids.json"

Write-Host "[OK] TechVal AI services started. PIDs saved to .runtime\pids.json" -ForegroundColor Green
Write-Host "  - Backend API & OpenAPI Docs: http://127.0.0.1:8000/docs"
Write-Host "  - Frontend Dashboard:         http://127.0.0.1:3000"
