-- =============================================================================
-- TechVal AI — PostgreSQL Schema for Vercel / Supabase / Neon / Railway / Local
-- Note: The Next.js backend (frontend/src/server/engine.ts) automatically runs
-- this schema initialization on startup when DATABASE_URL or POSTGRES_URL is set.
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_state_store (
    state_key TEXT PRIMARY KEY,
    state_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS technologies (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    title_en TEXT NOT NULL,
    title_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    claimed_trl INTEGER,
    expert_review_status TEXT NOT NULL,
    four_separate_outputs JSONB NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    document_type TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    encrypted_at_rest BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    sections_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_vault_blobs (
    opaque_storage_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    encrypted_bytes BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment_revisions (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    technology_assessment_score DOUBLE PRECISION,
    trl_score INTEGER,
    commercialization_readiness_score DOUBLE PRECISION,
    evidence_completeness_score DOUBLE PRECISION NOT NULL,
    is_provisional BOOLEAN NOT NULL DEFAULT TRUE,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_provider TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    actual_provider_returned TEXT,
    actual_model_returned TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS valuation_scenarios (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL,
    approach TEXT NOT NULL,
    scenario_case TEXT NOT NULL,
    indicative_value_idr BIGINT NOT NULL,
    indicative_value_formatted TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expert_reviews (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL,
    assessment_revision_id TEXT NOT NULL,
    status TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_snapshots (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL,
    language TEXT NOT NULL,
    is_draft BOOLEAN NOT NULL DEFAULT TRUE,
    watermark_text TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
