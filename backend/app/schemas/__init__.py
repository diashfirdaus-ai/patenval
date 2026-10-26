from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    email: str
    username: str
    full_name: str
    password: str
    role: str = "analyst"
    preferred_language: str = "en"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str
    preferred_language: str
    is_active: bool
    created_at: datetime


class AuthSessionResponse(BaseModel):
    access_token: str
    csrf_token: str
    expires_at: datetime
    user: UserResponse


class TechnologyCreateRequest(BaseModel):
    code: str
    title_en: str
    title_id: Optional[str] = None
    domain: str
    inventor_organization: str = "ITENAS Research Team"
    description_en: str
    description_id: Optional[str] = None
    claimed_trl: Optional[int] = Field(default=6, ge=1, le=9)
    patent_status: str = "granted"
    patent_application_number: Optional[str] = None
    patent_jurisdiction: Optional[str] = "ID"
    is_synthetic_demo: bool = False


class MarketComparableCreateRequest(BaseModel):
    evidence_category: str = "comparable_transaction"  # comparable_transaction | market_size_citation | patent_family_record
    title: str
    source_citation: str
    source_url_or_doi: Optional[str] = None
    jurisdiction: str = "ID"
    transaction_year: int = 2025
    unadjusted_value_idr: Optional[float] = None
    royalty_rate_percent: Optional[float] = None
    adjustment_factor: float = 1.0
    adjustment_rationale: str = "Direct market comparable"
    is_credible_verified: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ConsentPreviewRequest(BaseModel):
    technology_id: str
    provider: str = "fixture"  # gemini | openai_compatible | fixture
    model_name: str = "fixture-deterministic-v1"
    transmission_scope: str = "extracted_text_chunks"
    document_ids: List[str]
    config_options: Dict[str, Any] = Field(default_factory=dict)


class ConsentGrantRequest(BaseModel):
    technology_id: str
    provider: str
    model_name: str
    transmission_scope: str
    document_ids: List[str]
    consent_granted: bool
    config_options: Dict[str, Any] = Field(default_factory=dict)


class AnalysisRunCreateRequest(BaseModel):
    technology_id: str
    consent_record_id: str
    provider: str
    model_name: str
    weight_set_id: Optional[str] = None
    config_options: Dict[str, Any] = Field(default_factory=dict)
    execute_synchronously: bool = False


class ScientificReferenceCreateRequest(BaseModel):
    code: str
    authors: str
    publication_year: int
    title: str
    venue_or_publisher: str
    doi_or_url: str
    bibliographic_status: str = "verified"
    methodology_verification_status: str = "verified_with_locator"
    verified_sections_pages: Optional[str] = None
    domain_scope: str
    cross_domain_adaptation_notes: Optional[str] = None
    summary_quote: Optional[str] = None


class MethodologyConfigCreateRequest(BaseModel):
    version_tag: str
    name: str
    reference_id: Optional[str] = None
    origin_type: str = "adapted"  # directly_sourced | adapted | proposed | expert_validated
    empirical_validation_status: str = "not_empirically_validated"
    attributed_section: Optional[str] = None
    attributed_page: Optional[str] = None
    normalization_formula: str = "(score - 1) / 4"
    ahp_cr_threshold: float = 0.10
    rules_json: Dict[str, Any] = Field(default_factory=dict)


class AHPComputeAndSaveRequest(BaseModel):
    name: str
    version_tag: str
    tech_indicator_codes: List[str]
    tech_matrix: List[List[float]]
    comm_indicator_codes: List[str]
    comm_matrix: List[List[float]]
    activate_immediately: bool = True


class ValuationRevisionRequest(BaseModel):
    technology_id: str
    parent_revision_id: str
    change_reason: str
    approach: str = "dcf"  # dcf | cost | market_comparables | relief_from_royalty
    scenario_name: str = "Expert Revised DCF Base Scenario (IDR)"
    scenario_case: str = "base"
    inputs: Dict[str, Any]
    monte_carlo_seed: int = 202610
    monte_carlo_iterations: int = 1000
    monte_carlo_distributions: Optional[Dict[str, Dict[str, Any]]] = None


class IndicatorOverrideItem(BaseModel):
    indicator_code: str
    status: str  # observed | missing | not_applicable
    raw_score: Optional[int] = None
    expert_review_status: str = "approved"  # approved | rejected
    expert_review_reason: str


class AssessmentExpertRevisionRequest(BaseModel):
    technology_id: str
    parent_revision_id: str
    change_reason: str
    indicator_updates: List[IndicatorOverrideItem]


class ExpertSignOffRequest(BaseModel):
    technology_id: str
    assessment_revision_id: str
    status: str = "approved"  # approved | rejected | changes_requested
    overall_rationale: str
    methodology_verified: bool = True
    assumptions_verified: bool = True


class ReportGenerateRequest(BaseModel):
    technology_id: str
    assessment_revision_id: Optional[str] = None
    language: str = "en"  # en | id


class ExperimentRunCreateRequest(BaseModel):
    dataset_id: str
    name: str
