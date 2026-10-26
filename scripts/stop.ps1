# Native Windows Stop Script for TechVal AI
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidFile = "$RepoRoot\.runtime\pids.json"

if (Test-Path $PidFile) {
    $Pids = Get-Content $PidFile | ConvertFrom-Json
    if ($Pids.backend_pid) {
        & taskkill.exe /PID $Pids.backend_pid /T /F 2>&1 | Out-Null
        Write-Host "[OK] Stopped Backend process tree (PID $($Pids.backend_pid))" -ForegroundColor Green
    }
    if ($Pids.frontend_pid) {
        & taskkill.exe /PID $Pids.frontend_pid /T /F 2>&1 | Out-Null
        Write-Host "[OK] Stopped Frontend process tree (PID $($Pids.frontend_pid))" -ForegroundColor Green
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[INFO] No .runtime\pids.json found." -ForegroundColor Yellow
}
