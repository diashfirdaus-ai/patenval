# TechVal AI — Native Windows Setup, PostgreSQL & Operations Guide

## 1. Native Windows Architecture (No Docker Required)

TechVal AI runs natively on Windows 10/11 without Docker or Redis:
- **Backend**: Python 3.12 (`backend/.venv` managed by `uv`), FastAPI `/api/v1`, SQLAlchemy 2.0, Alembic, LangGraph, NumPy/SciPy, PyMuPDF, `python-docx`, ReportLab, and `cryptography` (Fernet).
- **Database & Job Queue**: Native Windows PostgreSQL 16 (`localhost:5432`, database `techval`) with `SELECT ... FOR UPDATE SKIP LOCKED` asynchronous worker polling and `EmbeddingVector` hybrid `pgvector` / JSON vector storage.
- **Frontend**: Next.js 15 / React 19 / TypeScript (`frontend/`), Tailwind CSS, Recharts, and bilingual (`en` / `id`) state management.
- **Encrypted Storage Vault**: `.runtime/vault/` located outside both backend static paths and the Next.js public root, encrypted at rest using Fernet (`AES-128-CBC + HMAC-SHA256`).

---

## 2. PowerShell Operational Scripts (`scripts/`)

Run all scripts from the repository root (`T:\Belajar Kuliah\ITENAS\patenval`):

```powershell
# 1. Provision Python 3.12 venv, install Node packages, and initialize .env + .runtime/vault
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

# 2. Apply Alembic migrations (26 tables) and seed baseline methodology, references, and demo fixtures
powershell -ExecutionPolicy Bypass -File .\scripts\migrate.ps1

# 3. Create or update a local RBAC administrator account
powershell -ExecutionPolicy Bypass -File .\scripts\create-admin.ps1 -Username "admin_local" -Password "AdminTechVal2026!"

# 4. Run full stack diagnostics (Python, Node, PostgreSQL, Alembic head, Vault encryption)
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose.ps1

# 5. Start FastAPI backend (port 8000) + LangGraph worker + Next.js frontend (port 3000)
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1

# 6. Stop running services cleanly
powershell -ExecutionPolicy Bypass -File .\scripts\stop.ps1
```

---

## 3. Default Local RBAC Accounts (Seeded for Testing & Review)

| Role | Username | Email | Password | Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **`admin`** | `admin` | `admin@techval.itenas.ac.id` | `AdminTechVal2026!` | Full system administration, user provisioning, all analyst & reviewer actions |
| **`analyst`** | `analyst` | `analyst@techval.itenas.ac.id` | `AnalystTechVal2026!` | Technology intake, document vault upload/delete, consent & pipeline runs, score revisions, IDR valuation, PDF reports |
| **`expert_reviewer`** | `reviewer` | `reviewer@techval.itenas.ac.id` | `ReviewerTechVal2026!` | Per-indicator review, revision-bound overall approval (`approved` / `rejected` / `changes_requested`), AHP calibration |

---

## 4. Provider Modes & Zero-Silent-Fallback Policy

TechVal AI supports four provider modes configured per run with mandatory explicit consent (`consent_records` table):
1. **`fixture` (`fixture-deterministic-v1`)**: Explicit deterministic local demo/testing mode. All outputs and datasets generated in this mode are clearly badged as **Synthetic / Demo Data**.
2. **`ollama` (e.g., `qwen2.5:7b-instruct`)**: Local inference via `OLLAMA_BASE_URL` (`http://localhost:11434`). Zero external network transmission.
3. **`openai`**: External cloud inference via `OPENAI_API_KEY`.
4. **`anthropic`**: External cloud inference via `ANTHROPIC_API_KEY`.

**Strict Zero-Silent-Fallback Rule**: If a user selects `ollama`, `openai`, or `anthropic` and the server/key is unavailable, the run transitions immediately to `status = "failed"` with a transparent diagnostic message and **never** substitutes `fixture` data.
