from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base, EmbeddingVector


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# 1. users
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="analyst")  # admin | analyst | expert_reviewer
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")  # en | id
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 2. user_sessions (supporting table)
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 3. technologies
class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title_en: Mapped[str] = mapped_column(String(500), nullable=False)
    title_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    domain: Mapped[str] = mapped_column(String(120), nullable=False)
    inventor_organization: Mapped[str] = mapped_column(String(255), nullable=False, default="ITENAS Research Team")
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claimed_trl: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    patent_status: Mapped[str] = mapped_column(String(64), nullable=False, default="granted")  # granted | pending | trade_secret | none
    patent_Application_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    patent_jurisdiction: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default="ID")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")  # draft | in_analysis | under_review | approved
    is_synthetic_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# 4. documents
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True)
    opaque_storage_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, default="technical_disclosure")  # patent_spec | technical_disclosure | lab_test_report | market_study | financial_projection
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    encrypted_vault_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ocr_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_warning_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    page_or_section_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted_char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 5. document_sections
class DocumentSection(Base):
    __tablename__ = "document_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False)  # page | paragraph | table
    location_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # e.g., page:1, para:4, table:1
    heading: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 6. document_chunks (supporting table with pgvector / EmbeddingVector)
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    location_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(EmbeddingVector(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 7. consent_records (supporting table)
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # gemini | openai_compatible | fixture
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    transmission_scope: Mapped[str] = mapped_column(String(255), nullable=False)  # extracted_text_chunks | full_sections | local_fixture_only
    document_ids_json: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    document_hashes_json: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    run_config_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    consent_granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    consent_statement: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 8. scientific_references
class ScientificReference(Base):
    __tablename__ = "scientific_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    authors: Mapped[str] = mapped_column(String(512), nullable=False)
    publication_year: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)  # Retain original publication title
    venue_or_publisher: Mapped[str] = mapped_column(String(512), nullable=False)
    doi_or_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    bibliographic_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="verified"
    )  # verified | pending | incomplete
    methodology_verification_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="verified_with_locator"
    )  # verified_with_locator | unverified_section_missing | contextual_only
    verified_sections_pages: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    domain_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    cross_domain_adaptation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 9. methodology_configs (versioned configurations)
class MethodologyConfig(Base):
    __tablename__ = "methodology_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    version_tag: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("scientific_references.id", ondelete="SET NULL"), nullable=True)
    origin_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # directly_sourced | adapted | proposed | expert_validated
    empirical_validation_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not_empirically_validated"
    )  # not_empirically_validated | benchmark_evaluated
    attributed_section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attributed_page: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    normalization_formula: Mapped[str] = mapped_column(String(128), nullable=False, default="(score - 1) / 4")
    ahp_cr_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.10)
    rules_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 10. indicator_definitions
class IndicatorDefinition(Base):
    __tablename__ = "indicator_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    dimension: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # technology_assessment | commercialization_readiness
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_id: Mapped[str] = mapped_column(String(255), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_id: Mapped[str] = mapped_column(Text, nullable=False)
    scale_type: Mapped[str] = mapped_column(String(32), nullable=False, default="1-5")  # 1-5 | 1-9_trl
    min_score: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    is_patent_specific: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origin_classification: Mapped[str] = mapped_column(
        String(64), nullable=False, default="proposed"
    )  # directly_sourced | adapted | proposed | expert_validated
    reference_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("scientific_references.id", ondelete="SET NULL"), nullable=True)
    source_locator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cross_domain_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric_levels_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    default_provisional_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 11. weight_sets
class WeightSet(Base):
    __tablename__ = "weight_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    weighting_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="provisional_equal"
    )  # provisional_equal | ahp_eigenvector
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tech_consistency_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comm_consistency_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weights_json: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    methodological_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 12. ahp_matrices (supporting table)
class AHPMatrix(Base):
    __tablename__ = "ahp_matrices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    weight_set_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("weight_sets.id", ondelete="CASCADE"), nullable=True)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)  # technology_assessment | commercialization_readiness
    indicator_codes_json: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    matrix_json: Mapped[List[List[float]]] = mapped_column(JSON, nullable=False)
    eigenvector_weights_json: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    lambda_max: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_index_ci: Mapped[float] = mapped_column(Float, nullable=False)
    random_index_ri: Mapped[float] = mapped_column(Float, nullable=False)
    ri_source_citation: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Saaty (1980), The Analytic Hierarchy Process, Table 1.5, p. 21"
    )
    consistency_ratio_cr: Mapped[float] = mapped_column(Float, nullable=False)
    is_consistent: Mapped[bool] = mapped_column(Boolean, nullable=False)  # CR <= 0.10 convention
    convention_note: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="CR <= 0.10 threshold is enforced as a methodological convention following Saaty (1980).",
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 13. analysis_runs
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_record_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("consent_records.id", ondelete="SET NULL"), nullable=True)
    methodology_config_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("methodology_configs.id", ondelete="SET NULL"), nullable=True)
    weight_set_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("weight_sets.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="queued", index=True
    )  # queued | running | completed | failed | cancelled
    current_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_model: Mapped[str] = mapped_column(String(128), nullable=False)
    actual_provider_returned: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    actual_model_returned: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    run_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    config_snapshot_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rubric_version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    document_hashes_json: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    app_version: Mapped[str] = mapped_column(String(32), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    partial_results_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rejected_claims_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 14. agent_executions
class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # extraction | technology_assessment | market_assessment | ip_patent | commercialization | risk_assessment | financial_valuation | evidence_validation
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")  # running | completed | failed
    provider_used: Mapped[str] = mapped_column(String(64), nullable=False)
    model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_summary_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    validation_errors_json: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 15. job_queue (supporting table for PostgreSQL background jobs)
class JobQueue(Base):
    __tablename__ = "job_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="langgraph_analysis")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)  # queued | processing | completed | failed | cancelled
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    locked_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# 16. langgraph_checkpoints (supporting table for LangGraph persistence)
class LangGraphCheckpoint(Base):
    __tablename__ = "langgraph_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    state_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 17. assessment_revisions (immutable assessment revisions preserving the 4 separate outputs)
class AssessmentRevision(Base):
    __tablename__ = "assessment_revisions"
    __table_args__ = (UniqueConstraint("technology_id", "revision_number", name="uq_tech_revision_num"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True)
    parent_revision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assessment_revisions.id", ondelete="SET NULL"), nullable=True)
    weight_set_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("weight_sets.id", ondelete="SET NULL"), nullable=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False, default="Initial analysis revision")
    previous_values_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Output 1: Technology Assessment (normalized 0..1 aggregate & native 1..9 TRL)
    technology_assessment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trl_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Native 1-9 scale
    trl_exit_criteria_met_json: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    # Output 2: Commercialization Readiness (normalized 0..1 aggregate)
    commercialization_readiness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Output 3: Economic Valuation is linked via ValuationScenario records (never derived from scores!)
    primary_valuation_scenario_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Output 4: Evidence Completeness (weighted completeness 0..1 across applicable indicators)
    evidence_completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tech_completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    comm_completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    is_provisional: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provisional_reasons_json: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    applicable_indicator_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observed_indicator_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_indicator_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_applicable_indicator_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Contextual outputs from specialized agents
    ip_patent_signals_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    market_intelligence_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    commercialization_pathway_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    risk_matrix_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 18. indicator_scores
class IndicatorScore(Base):
    __tablename__ = "indicator_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    assessment_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("indicator_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="observed"
    )  # observed | missing | not_applicable
    scale_type: Mapped[str] = mapped_column(String(32), nullable=False, default="1-5")
    raw_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    normalized_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # (score - 1) / 4 for 1-5; None for TRL 1-9
    base_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    renormalized_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rationale_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rationale_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expert_review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | approved | rejected
    expert_review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 19. evidence_items
class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    assessment_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_score_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("indicator_scores.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    section_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_sections.id", ondelete="CASCADE"), nullable=True
    )
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    location_ref: Mapped[str] = mapped_column(String(128), nullable=False)  # page:2, para:5, table:1, manual_citation
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)  # Retain original source quotation
    claim_summary: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="resolved"
    )  # resolved | rejected_unresolvable_locator | rejected_quote_mismatch | rejected_unsupported_numeric | manual_import
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 20. market_comparables (supporting table for comparables & manual market/patent evidence imports)
class MarketComparable(Base):
    __tablename__ = "market_comparables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="comparable_transaction"
    )  # comparable_transaction | market_size_citation | patent_family_record
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)
    source_url_or_doi: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(64), nullable=False, default="ID")
    transaction_year: Mapped[int] = mapped_column(Integer, nullable=False, default=2025)
    unadjusted_value_idr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    royalty_rate_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjustment_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    adjustment_rationale: Mapped[str] = mapped_column(Text, nullable=False, default="Direct market comparable")
    is_credible_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 21. valuation_scenarios
class ValuationScenario(Base):
    __tablename__ = "valuation_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_case: Mapped[str] = mapped_column(String(32), nullable=False, default="base")  # low | base | high
    approach: Mapped[str] = mapped_column(
        String(64), nullable=False, default="dcf"
    )  # dcf | cost | market_comparables | relief_from_royalty
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="IDR")
    attribution_mode: Mapped[str] = mapped_column(
        String(64), nullable=False, default="direct_cash_flows"
    )  # direct_cash_flows | documented_attribution_factor
    attribution_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attribution_documentation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_treatment_mode: Mapped[str] = mapped_column(
        String(64), nullable=False, default="in_discount_rate"
    )  # in_cash_flows | in_discount_rate | both
    double_counting_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    double_counting_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inputs_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    calculation_breakdown_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    indicative_value_idr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    range_min_idr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    range_max_idr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sensitivity_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    monte_carlo_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monte_carlo_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    wipo_reference_locator: Mapped[str] = mapped_column(
        String(255), nullable=False, default="WIPO IP Valuation Basics Guide, Section 3 (Valuation Methods), pp. 18-39"
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 22. expert_reviews
class ExpertReview(Base):
    __tablename__ = "expert_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="approved"
    )  # approved | rejected | changes_requested | stale
    overall_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    methodology_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assumptions_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stale_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 23. report_snapshots (supporting table)
class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    technology_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expert_review_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expert_reviews.id", ondelete="SET NULL"), nullable=True
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")  # en | id
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    watermark_text: Mapped[str] = mapped_column(String(128), nullable=False, default="DRAFT — UNAPPROVED")
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 24. experiment_datasets (supporting table)
class ExperimentDataset(Base):
    __tablename__ = "experiment_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_synthetic_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    access_roles_json: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=lambda: ["admin", "analyst", "expert_reviewer"])
    items_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 25. experiments
class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiment_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_synthetic_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conditions_compared_json: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["human_expert", "llm_only", "multi_agent", "multi_agent_validated"],
    )
    manifest_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    metrics_summary_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    per_condition_results_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    matching_policy_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# 26. audit_logs
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    actor_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
