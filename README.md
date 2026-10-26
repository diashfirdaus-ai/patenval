# TechVal AI — Scientific Technology Assessment & WIPO Economic Valuation Platform

**TechVal AI** is a complete four-phase scientific technology assessment, commercialization readiness, WIPO-grounded deterministic economic valuation (in Indonesian Rupiah, `IDR`), evidence completeness, and research evaluation platform designed for native Windows operation.

---

## Core Architectural Principles

1. **Strict Four-Output Separation (No Score-to-IDR Conversion)**:
   - **Output 1 — `technology_assessment`**: Normalized $[0, 1]$ composite score from 1–5 ordinal rubrics ($(s-1)/4$) alongside the **native NASA TRL 1–9 integer scale** (`https://esto.nasa.gov/trl/`).
   - **Output 2 — `commercialization_readiness`**: Normalized $[0, 1]$ composite score across Market Demand, Competitive Position, Regulatory Compliance, Supply Chain, and IP Licensing Readiness.
   - **Output 3 — `economic_valuation` (`IDR`)**: Pure financial calculators grounded in WIPO's *Intellectual Property Valuation Basics for Technology Transfer Professionals* (`https://www.wipo.int/web-publications/intellectual-property-valuation-basics-for-technology-transfer-professionals/en/index.html`) — Cost Approach, Market Comparables, Discounted Cash Flow (DCF), and Relief-from-Royalty in `IDR`, with sensitivity and seeded Monte Carlo simulation. Assessment and TRL scores are **never** converted into monetary values, royalty rates, or discount rates.
   - **Output 4 — `evidence_completeness`**: Weighted coverage ratio $C_d = \sum_{i \in O_d} w_i / \sum_{k \in A_d} w_k$ separating `observed`, `missing`, and `not_applicable` indicators (e.g., patent indicators for non-patent IP per Harhoff et al. 2003, `https://www.sciencedirect.com/science/article/abs/pii/S0048733302001245`).

2. **Source Location Resolution & Scientific Provenance**:
   - Every evidence item resolves to an exact `page:N`, `para:N`, or `table:N` locator in the uploaded document with a verified verbatim quote and numeric claim check.
   - Scientific references are explicitly classified as `methodology_verified` (with exact verified section/page locators) or `bibliographically_verified_only`.
   - Indicator definitions are explicitly classified as `directly_sourced`, `adapted`, `proposed`, or `expert_validated`.

3. **Security, Governance & Revision-Bound Approval**:
   - Local RBAC (`admin`, `analyst`, `expert_reviewer`) with server-side sessions and CSRF protection.
   - Encrypted document vault outside web roots (`.runtime/vault`, Fernet `AES-128-CBC + HMAC-SHA256`), magic-byte file verification, scanned PDF (`ocr_required`) detection, and complete cascade deletion.
   - Explicit consent bound to exact document SHA-256 hashes and run configuration hash; zero silent fallback to fixture data.
   - Immutable `AssessmentRevision` lineage; any material edit to scores, weights, valuations, or documents automatically invalidates prior `approved` expert reviews to `stale`.

---

## Repository Structure

```text
patenval/
├── backend/                  # FastAPI (/api/v1), SQLAlchemy 2.0 (26 tables), Alembic, LangGraph 8-agent workflow
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/v1/           # 9 REST routers (44 endpoints)
│   │   ├── models/           # 17 core + 9 supporting SQLAlchemy 2.0 models
│   │   ├── security/         # PBKDF2-SHA256 auth, CSRF, Fernet encrypted vault
│   │   └── services/         # Scoring, Saaty AHP, WIPO IDR valuation, EPO OPS, LangGraph, PDF report, Evaluation
│   ├── fixtures/             # Clearly badged synthetic/demo fixtures & sample documents
│   └── tests/                # 21 automated scientific, financial, security, and workflow tests
├── frontend/                 # Next.js 15 / TypeScript / Tailwind / Recharts bilingual (EN/ID) frontend
│   └── src/app/              # 10 specialized scientific & financial dashboard views
├── scripts/                  # Native Windows PowerShell scripts (setup, migrate, create-admin, start, stop, diagnose)
├── docs/                     # OpenAPI 3.1 spec, Methodology, Source Mappings, API Docs, Setup Guide, Sample PDFs
└── outputs/                  # Packaged deliverables, evaluation benchmarks, and sample reports
```

---

## Quick Start — 100% Web via `npm` Only

You can run the entire full-stack **TechVal AI** website (both the 10 dashboard pages and the built-in `/api/v1` scientific & WIPO valuation backend) using **`npm` alone** from the root folder (`T:\Belajar Kuliah\ITENAS\patenval`):

```powershell
# 1. Start development server on http://localhost:3000
npm.cmd run dev

# OR build and run production server on http://localhost:3000
npm.cmd run build
npm.cmd start
```

Open **`http://localhost:3000`** in your browser. All data is persisted locally in `.runtime/nextjs_web_state.json` and encrypted files are stored in `.runtime/vault/`.

---

## Optional Advanced PowerShell & Python/PostgreSQL Scripts

```powershell
# 1. Verify environment and dependencies
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

# 2. Run Alembic PostgreSQL migrations and seed baseline data
powershell -ExecutionPolicy Bypass -File .\scripts\migrate.ps1

# 3. Run full stack diagnostics
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose.ps1

# 4. Run backend automated test suite (21 tests)
cd backend
.\.venv\Scripts\pytest.exe -v
cd ..

# 5. Start Backend (http://127.0.0.1:8000) and Frontend (http://127.0.0.1:3000)
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

---

## Documentation & Sample Deliverables

- [`docs/METHODOLOGY.md`](./docs/METHODOLOGY.md) — Formal mathematical specifications & WIPO/NASA/Saaty/Harhoff grounding
- [`docs/SOURCE_MAPPINGS.md`](./docs/SOURCE_MAPPINGS.md) — Literature verification registry & indicator origin matrix
- [`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md) — `/api/v1` REST API reference
- [`docs/openapi.json`](./docs/openapi.json) — Machine-readable OpenAPI 3.1 schema (44 endpoints)
- [`docs/SETUP_AND_OPERATIONS.md`](./docs/SETUP_AND_OPERATIONS.md) — Native Windows PostgreSQL & operations guide
- [`docs/sample_reports/`](./docs/sample_reports/) — Generated English (`EN`) and Bahasa Indonesia (`ID`) Draft & Approved PDF reports
