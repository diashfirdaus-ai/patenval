/**
 * Auto-aligned TypeScript API types corresponding to `/api/v1` OpenAPI 3.1 schema (`docs/openapi.json`).
 */

export type LanguageCode = "en" | "id";
export type UserRole = "admin" | "analyst" | "expert_reviewer";

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: UserRole;
  preferred_language: LanguageCode;
  is_active: boolean;
  created_at: string;
}

export interface AuthSessionResponse {
  access_token: string;
  csrf_token: string;
  expires_at: string;
  user: UserResponse;
}

export interface FourSeparateOutputsSummary {
  technology_assessment: {
    normalized_score: number | null;
    trl_native_1_to_9: number | null;
    is_provisional: boolean;
  };
  commercialization_readiness: {
    normalized_score: number | null;
    is_provisional: boolean;
  };
  economic_valuation: {
    currency: "IDR";
    dcf_base_indicative_idr: number | null;
    dcf_base_formatted: string;
    score_conversion_prohibited: true;
  };
  evidence_completeness: {
    weighted_completeness_score: number;
    observed_count: number;
    missing_count: number;
    not_applicable_count: number;
  };
}

export interface TechnologyItem {
  id: string;
  code: string;
  title_en: string;
  title_id?: string | null;
  domain: string;
  inventor_organization: string;
  description_en: string;
  description_id?: string | null;
  claimed_trl: number | null;
  patent_status: string;
  patent_application_number?: string | null;
  patent_jurisdiction?: string | null;
  status: string;
  is_synthetic_demo: boolean;
  active_document_count: number;
  created_at: string;
  updated_at: string;
  four_separate_outputs: FourSeparateOutputsSummary;
  latest_revision_id: string | null;
  latest_revision_number: number;
  expert_review_status: string;
}

export interface DocumentItem {
  id: string;
  technology_id: string;
  opaque_storage_id: string;
  original_filename: string;
  document_type: string;
  mime_type: string;
  file_extension: string;
  file_size_bytes: number;
  sha256_hash: string;
  signature_valid: boolean;
  encrypted_at_rest: boolean;
  ocr_required: boolean;
  ocr_warning_message: string | null;
  page_or_section_count: number;
  extracted_char_count: number;
  is_deleted: boolean;
  deleted_at: string | null;
  created_at: string;
}

export interface DocumentSectionItem {
  id: string;
  section_index: number;
  location_type: "page" | "paragraph" | "table";
  location_ref: string;
  heading: string | null;
  content_text: string;
  char_count: number;
}

export interface AgentExecutionItem {
  id: string;
  agent_name: string;
  status: string;
  provider_used: string;
  model_used: string;
  prompt_hash: string;
  latency_ms: number;
  output_summary: Record<string, any>;
}

export interface AnalysisRunItem {
  id: string;
  technology_id: string;
  consent_record_id: string | null;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  current_node: string | null;
  progress_percent: number;
  requested_provider: string;
  requested_model: string;
  actual_provider_returned: string | null;
  actual_model_returned: string | null;
  prompt_hash: string;
  run_config_hash: string;
  config_snapshot_json: Record<string, any>;
  rubric_version_tag: string;
  document_hashes_json: Record<string, string>;
  app_version: string;
  retry_count: number;
  max_retries: number;
  cancel_requested: boolean;
  error_message: string | null;
  partial_results_json: Record<string, any>;
  rejected_claims_json: Array<Record<string, any>>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  agent_executions: AgentExecutionItem[];
  checkpoints: Array<{
    step_index: number;
    node_name: string;
    created_at: string;
  }>;
}

export interface IndicatorDefinitionItem {
  id: string;
  code: string;
  dimension: "technology_assessment" | "commercialization_readiness";
  name_en: string;
  name_id: string;
  description_en: string;
  description_id: string;
  scale_type: "1-5" | "1-9_trl";
  min_score: number;
  max_score: number;
  is_patent_specific: boolean;
  origin_classification: "directly_sourced" | "adapted" | "proposed" | "expert_validated";
  reference_id: string | null;
  source_locator: string | null;
  cross_domain_note: string | null;
  rubric_levels: Record<string, string>;
  default_provisional_weight: number;
}

export interface IndicatorScoreItem {
  id: string;
  indicator_code: string;
  dimension: "technology_assessment" | "commercialization_readiness";
  status: "observed" | "missing" | "not_applicable";
  scale_type: "1-5" | "1-9_trl";
  raw_score: number | null;
  normalized_score: number | null;
  base_weight: number;
  renormalized_weight: number;
  rationale_en: string;
  rationale_id: string;
  expert_review_status: "pending" | "approved" | "rejected";
  expert_review_reason: string | null;
}

export interface EvidenceLinkItem {
  id: string;
  indicator_score_id: string | null;
  document_id: string | null;
  indicator_code: string;
  location_ref: string;
  quoted_text: string;
  claim_summary: string;
  resolution_status: string;
  rejection_reason: string | null;
}

export interface AssessmentRevisionItem {
  id: string;
  technology_id: string;
  analysis_run_id: string | null;
  parent_revision_id: string | null;
  weight_set_id: string | null;
  revision_number: number;
  actor_id: string | null;
  change_reason: string;
  previous_values_json: Record<string, any> | null;
  technology_assessment_score: number | null;
  trl_score: number | null;
  trl_exit_criteria_met_json: string[];
  commercialization_readiness_score: number | null;
  evidence_completeness_score: number;
  tech_completeness_score: number;
  comm_completeness_score: number;
  is_provisional: boolean;
  provisional_reasons_json: string[];
  applicable_indicator_count: number;
  observed_indicator_count: number;
  missing_indicator_count: number;
  not_applicable_indicator_count: number;
  ip_patent_signals_json: Record<string, any>;
  market_intelligence_json: Record<string, any>;
  commercialization_pathway_json: Record<string, any>;
  risk_matrix_json: Record<string, any>;
  created_at: string;
  indicator_scores: IndicatorScoreItem[];
  evidence_items: EvidenceLinkItem[];
}

export interface ValuationScenarioItem {
  id: string;
  scenario_name: string;
  scenario_case: "low" | "base" | "high";
  approach: "dcf" | "cost" | "market_comparables" | "relief_from_royalty";
  currency: "IDR";
  attribution_mode: "direct_cash_flows" | "documented_attribution_factor";
  attribution_factor: number | null;
  attribution_documentation: string | null;
  risk_treatment_mode: "in_cash_flows" | "in_discount_rate" | "both";
  double_counting_flagged: boolean;
  double_counting_warning: string | null;
  inputs_json: Record<string, any>;
  calculation_breakdown_json: Record<string, any>;
  indicative_value_idr: number | null;
  indicative_value_formatted: string;
  range_min_idr: number | null;
  range_max_idr: number | null;
  sensitivity_json: Array<Record<string, any>>;
  monte_carlo_seed: number | null;
  monte_carlo_json: Record<string, any> | null;
  wipo_reference_locator: string;
  created_at: string;
}

export interface ScientificReferenceItem {
  id: string;
  code: string;
  authors: string;
  publication_year: number;
  title: string;
  venue_or_publisher: string;
  doi_or_url: string;
  bibliographic_status: string;
  methodology_verification_status: string;
  verified_sections_pages: string | null;
  domain_scope: string;
  cross_domain_adaptation_notes: string | null;
  summary_quote: string | null;
}

export interface ExpertReviewItem {
  id: string;
  technology_id: string;
  assessment_revision_id: string;
  reviewer_id: string;
  status: "approved" | "rejected" | "changes_requested" | "stale";
  overall_rationale: string;
  methodology_verified: boolean;
  assumptions_verified: boolean;
  stale_reason: string | null;
  invalidated_at: string | null;
  created_at: string;
}

export interface ReportSnapshotItem {
  id: string;
  technology_id: string;
  assessment_revision_id: string;
  expert_review_id: string | null;
  language: LanguageCode;
  is_draft: boolean;
  watermark_text: string;
  file_sha256: string;
  provenance_json: Record<string, any>;
  created_at: string;
}
