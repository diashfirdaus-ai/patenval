# TechVal AI — `/api/v1` REST API Documentation

The complete machine-readable OpenAPI 3.1 specification is exported at [`docs/openapi.json`](./openapi.json) and served live at `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/openapi.json`.

---

## 1. Authentication, RBAC & CSRF Security

- **Session Authentication**: `POST /api/v1/auth/login` issues a server-side `UserSession` (`user_sessions` table) with an opaque `access_token` and a cryptographic `csrf_token`.
- **State-Changing Requests**: All `POST`, `PUT`, `PATCH`, and `DELETE` requests require both `Authorization: Bearer <access_token>` (or `techval_session` HttpOnly cookie) and `X-CSRF-Token: <csrf_token>`.
- **Role-Based Access Control (RBAC)**:
  - `admin`: Full system administration, user creation (`POST /api/v1/auth/users`), and all analyst/reviewer operations.
  - `analyst`: Create technologies, upload/delete vault documents, record explicit consent, execute 8-agent analysis runs, edit indicator scores (creating new immutable revisions), run WIPO IDR valuations, and generate bilingual PDF reports.
  - `expert_reviewer`: Approve/reject individual indicators (`POST /api/v1/reviews/indicator`), submit revision-bound overall sign-offs (`POST /api/v1/reviews`), and calibrate AHP weight sets.

---

## 2. Endpoint Summary (44 Paths Across 9 Routers)

### 2.1 System Health (`/api/v1/health`)
- `GET /api/v1/health`: Returns PostgreSQL status, `pgvector` extension status, encrypted vault path, and separation-of-outputs architecture flags.

### 2.2 Authentication & RBAC (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Authenticate with username/email and password.
- `POST /api/v1/auth/logout`: Revoke current server-side session.
- `GET /api/v1/auth/me`: Inspect current user and CSRF token.
- `GET /api/v1/auth/users`: List registered accounts (`admin` only).
- `POST /api/v1/auth/users`: Create a new local user account (`admin` only).

### 2.3 Technology Portfolio (`/api/v1/technologies`)
- `GET /api/v1/technologies`: List all technologies with their four strictly separate outputs (`technology_assessment`, `commercialization_readiness`, `economic_valuation`, `evidence_completeness`).
- `POST /api/v1/technologies`: Register a new technology disclosure.
- `GET /api/v1/technologies/{tech_id}`: Retrieve full portfolio summary for one technology.
- `PATCH /api/v1/technologies/{tech_id}`: Update metadata and log an immutable audit event.

### 2.4 Encrypted Document Vault (`/api/v1/documents`)
- `POST /api/v1/documents/upload`: Validate extension + magic bytes (`.pdf`, `.docx`, `.txt`, `.md`), encrypt with Fernet (`AES-128-CBC + HMAC-SHA256`) outside web root (`.runtime/vault`), parse canonical locators (`page:N`, `para:N`, `table:N`), detect scanned PDFs (`ocr_required = True`), and chunk embeddings.
- `GET /api/v1/documents/technology/{tech_id}`: List vault documents and SHA-256 hashes.
- `GET /api/v1/documents/{doc_id}/sections`: Inspect parsed sections and locators.
- `GET /api/v1/documents/{doc_id}/download`: Stream decrypted document bytes (`RBAC`-protected).
- `DELETE /api/v1/documents/{doc_id}`: Complete cascade deletion across encrypted vault file, `document_sections`, `embedding_chunks`, and active `evidence_items`, automatically marking prior approvals `stale`.

### 2.5 Explicit Consent & 8-Agent LangGraph Workflow (`/api/v1/analysis-runs`)
- `POST /api/v1/analysis-runs/consent`: Record explicit consent bound to exact document SHA-256 hashes, provider, model, and transmission scope.
- `POST /api/v1/analysis-runs`: Execute or enqueue the 8-agent LangGraph pipeline (`intake_validation`, `evidence_extraction`, `ip_patent_analysis`, `market_intelligence`, `technical_trl_assessment`, `commercialization_pathway`, `risk_synthesis`, `report_compilation`). Never falls back silently to fixture data if an external/local provider fails.
- `GET /api/v1/analysis-runs/technology/{tech_id}`: List runs for a technology.
- `GET /api/v1/analysis-runs/{run_id}`: Inspect run status, checkpoints, agent execution trace, contradictions, and rejected unsupported claims.
- `POST /api/v1/analysis-runs/{run_id}/cancel`: Request cancellation.
- `POST /api/v1/analysis-runs/{run_id}/retry`: Retry a failed or cancelled run.

### 2.6 Assessments, NASA TRL, AHP & Patent Signals (`/api/v1/assessments`)
- `GET /api/v1/assessments/indicators`: List all 11 indicator definitions with origin classifications and source locators.
- `GET /api/v1/assessments/weight-sets`: List provisional and AHP-calibrated weight sets.
- `GET /api/v1/assessments/technology/{tech_id}/revisions`: List immutable assessment revisions.
- `GET /api/v1/assessments/technology/{tech_id}/latest`: Get latest revision with indicator scores and source-resolved evidence items.
- `POST /api/v1/assessments/technology/{tech_id}/revisions`: Create a new immutable `AssessmentRevision` with actor, timestamp, change reason, and `previous_values_json`, invalidating prior approvals to `stale`.
- `POST /api/v1/assessments/ahp/compute`: Validate reciprocal pairwise matrix, compute principal eigenvector weights, and enforce $CR \le 0.10$.
- `POST /api/v1/assessments/patent-signals/lookup`: Query EPO Open Patent Services (OPS) with graceful fallback to manual/disclosed contextual patent signals.

### 2.7 Deterministic WIPO Economic Valuation in IDR (`/api/v1/valuations`)
- `GET /api/v1/valuations/technology/{tech_id}`: List valuation scenarios.
- `POST /api/v1/valuations/dcf`: Deterministic WIPO DCF calculator in IDR with attribution mode, double-counting guard, sensitivity, and seeded Monte Carlo simulation.
- `POST /api/v1/valuations/cost`: Deterministic WIPO Cost Approach calculator in IDR.
- `POST /api/v1/valuations/market-comparables`: Deterministic WIPO Market Comparables calculator in IDR.
- `POST /api/v1/valuations/relief-from-royalty`: Deterministic WIPO Relief-from-Royalty calculator in IDR.

### 2.8 Expert Review & Governance (`/api/v1/reviews`)
- `GET /api/v1/reviews/technology/{tech_id}`: List revision-bound expert reviews.
- `POST /api/v1/reviews`: Submit an expert review (`approved`, `rejected`, `changes_requested`) bound to a specific `assessment_revision_id`.
- `POST /api/v1/reviews/indicator`: Approve or reject an individual indicator score.
- `GET /api/v1/reviews/audit-logs`: Retrieve immutable audit logs.

### 2.9 Bilingual PDF Reports & Phase 4 Evaluation (`/api/v1/reports`, `/api/v1/evaluation`, `/api/v1/methodology`)
- `POST /api/v1/reports/generate`: Generate English (`en`) or Bahasa Indonesia (`id`) PDF report with automatic draft watermark and cryptographic provenance manifest.
- `GET /api/v1/reports/{report_id}/download`: Download generated PDF report.
- `POST /api/v1/evaluation/run`: Execute Phase 4 Research Evaluation Suite (IE Precision/Recall/F1, QWK, ICC(2,1)/ICC(3,1) with 95% bootstrap CIs, Financial MAE/RMSE/sMAPE, and Ablation Study).
- `GET /api/v1/evaluation/export/{format}`: Export Phase 4 evaluation results as `csv` or `json`.
