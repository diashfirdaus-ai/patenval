param(
    [string]$Username = "admin_local",
    [string]$Email = "admin_local@techval.itenas.ac.id",
    [string]$Password = "AdminTechVal2026!",
    [string]$FullName = "Local Administrator",
    [string]$Role = "admin"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location "$RepoRoot\backend"

$PyScript = @"
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User
from app.security.auth import hash_password

with SessionLocal() as db:
    existing = db.execute(select(User).where(User.username == '$Username')).scalar_one_or_none()
    if existing:
        existing.password_hash = hash_password('$Password')
        existing.role = '$Role'
        existing.full_name = '$FullName'
        existing.email = '$Email'
        db.commit()
        print(f'[OK] Updated existing user: {existing.username} (role={existing.role})')
    else:
        user = User(
            username='$Username',
            email='$Email',
            password_hash=hash_password('$Password'),
            full_name='$FullName',
            role='$Role',
            preferred_language='id',
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f'[OK] Created user: {user.username} (role={user.role})')
"@

$PyScript | & ".\.venv\Scripts\python.exe" -
Set-Location $RepoRoot
