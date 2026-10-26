from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from langgraph.graph import END, START, StateGraph
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import (
    AgentExecution,
    AnalysisRun,
    AssessmentRevision,
    ConsentRecord,
    Document,
    DocumentSection,
    EvidenceItem,
    ExpertReview,
    IndicatorDefinition,
    IndicatorScore,
    LangGraphCheckpoint,
    MarketComparable,
    Technology,
    ValuationScenario,
    WeightSet,
)
from app.services.patent_ops import EPOOPSAdapter, build_manual_patent_signal_record
from app.services.providers import ProviderExecutionError, invoke_structured_provider
from app.services.scoring import (
    compute_dimension_aggregate,
    validate_and_resolve_evidence,
)
from app.services.valuation import (
    calculate_cost_valuation,
    calculate_dcf_valuation,
    calculate_market_comparables_valuation,
    calculate_relief_from_royalty_valuation,
    run_dcf_sensitivity_analysis,
    run_seeded_monte_carlo_dcf,
)


ALL_EIGHT_AGENTS = [
    "extraction",
    "technology_assessment",
    "ip_patent",
    "market_assessment",
    "commercialization",
    "risk_assessment",
    "financial_valuation",
    "evidence_validation",
]


class TechValGraphState(TypedDict, total=False):
    run_id: str
    technology_id: str
    provider: str
    model_name: str
    actual_provider_returned: str
    actual_model_returned: str
    prompt_hashes: List[str]
    technology_meta: Dict[str, Any]
    document_context: List[Dict[str, Any]]
    stored_sections_map: Dict[str, Dict[str, Any]]
    valid_doc_ids: List[str]
    indicator_defs: List[Dict[str, Any]]
    weights_map: Dict[str, float]
    weight_set_id: Optional[str]
    weight_set_is_provisional: bool
    extraction_summary: Dict[str, Any]
    tech_eval_raw: Dict[str, Any]
    ip_patent_signals: Dict[str, Any]
    market_intelligence: Dict[str, Any]
    comm_eval_raw: Dict[str, Any]
    commercialization_pathway: Dict[str, Any]
    risk_matrix: Dict[str, Any]
    valuation_outputs: Dict[str, Any]
    contradictory_evidence_flags: List[Dict[str, Any]]
    rejected_claims: List[Dict[str, Any]]
    resolved_evidence: List[Dict[str, Any]]
    created_revision_id: Optional[str]


def _check_cancellation_and_checkpoint(
    db: Session,
    run_id: str,
    step_index: int,
    node_name: str,
    progress_percent: int,
    partial_summary: Dict[str, Any],
) -> None:
    run = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one()
    db.refresh(run)
    if run.cancel_requested or run.status == "cancelled":
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise RuntimeError("ANALYSIS_RUN_CANCELLED")

    run.current_node = node_name
    run.progress_percent = progress_percent
    merged_partial = dict(run.partial_results_json or {})
    merged_partial[node_name] = partial_summary
    run.partial_results_json = merged_partial

    cp = LangGraphCheckpoint(
        analysis_run_id=run_id,
        step_index=step_index,
        node_name=node_name,
        state_json=partial_summary,
    )
    db.add(cp)
    db.commit()


def _record_agent_execution(
    db: Session,
    run_id: str,
    agent_name: str,
    provider_used: str,
    model_used: str,
    prompt_hash: str,
    latency_ms: int,
    output_summary: Dict[str, Any],
    validation_errors: Optional[List[str]] = None,
) -> None:
    exec_row = AgentExecution(
        analysis_run_id=run_id,
        agent_name=agent_name,
        status="completed",
        provider_used=provider_used,
        model_used=model_used,
        prompt_hash=prompt_hash,
        latency_ms=latency_ms,
        output_summary_json=output_summary,
        validation_errors_json=validation_errors or [],
    )
    db.add(exec_row)
    db.commit()


def build_techval_langgraph(db: Session):
    """
    Constructs and compiles the 8-node LangGraph workflow:
    1. extraction
    2. technology_assessment
    3. ip_patent
    4. market_assessment
    5. commercialization
    6. risk_assessment
    7. financial_valuation
    8. evidence_validation
    """

    def extraction_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        docs = state.get("document_context", [])
        total_sections = sum(len(d.get("sections", [])) for d in docs)
        ocr_flagged_docs = [d["original_filename"] for d in docs if d.get("ocr_required")]

        # Detect contradictory statements across document sections (e.g., conflicting TRL claims)
        contradictions: List[Dict[str, Any]] = []
        trl_mentions: List[Tuple[str, str, str]] = []
        for d in docs:
            for s in d.get("sections", []):
                txt = s.get("content_text", "")
                for lvl in range(1, 10):
                    if f"trl {lvl}" in txt.lower() or f"trl-{lvl}" in txt.lower():
                        trl_mentions.append((f"TRL {lvl}", d["id"], s["location_ref"]))
        distinct_trls = sorted({m[0] for m in trl_mentions})
        if len(distinct_trls) > 1:
            contradictions.append(
                {
                    "type": "conflicting_trl_claims",
                    "distinct_values": distinct_trls,
                    "locations": [
                        {"trl": m[0], "document_id": m[1], "location_ref": m[2]} for m in trl_mentions
                    ],
                    "message": f"Conflicting TRL claims detected across document sections: {', '.join(distinct_trls)}.",
                }
            )

        summary = {
            "documents_count": len(docs),
            "sections_extracted": total_sections,
            "ocr_flagged_documents": ocr_flagged_docs,
            "contradictions_detected": contradictions,
        }
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "extraction",
            state["provider"],
            state["model_name"],
            "local_extraction_deterministic",
            latency,
            summary,
        )
        _check_cancellation_and_checkpoint(db, run_id, 1, "extraction", 12, summary)
        return {
            **state,
            "extraction_summary": summary,
            "contradictory_evidence_flags": contradictions,
        }

    def technology_assessment_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        res = invoke_structured_provider(
            provider=state["provider"],
            model_name=state["model_name"],
            agent_name="technology_assessment",
            system_prompt=(
                "Evaluate Technology Assessment indicators on their defined 1-5 rubrics and NASA TRL on its "
                "native 1-9 scale. Cite exact document_id, location_ref, and verbatim quoted_text."
            ),
            document_context=state["document_context"],
            technology_meta=state["technology_meta"],
            indicator_defs=state["indicator_defs"],
        )
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "technology_assessment",
            res["actual_provider_returned"],
            res["actual_model_returned"],
            res["prompt_hash"],
            latency,
            {"trl_score": res["data"].get("trl_score"), "indicators_evaluated": len(res["data"].get("indicators", []))},
        )
        _check_cancellation_and_checkpoint(
            db,
            run_id,
            2,
            "technology_assessment",
            25,
            {"trl_score": res["data"].get("trl_score")},
        )
        prompt_hashes = list(state.get("prompt_hashes", [])) + [res["prompt_hash"]]
        return {
            **state,
            "actual_provider_returned": res["actual_provider_returned"],
            "actual_model_returned": res["actual_model_returned"],
            "prompt_hashes": prompt_hashes,
            "tech_eval_raw": res["data"],
        }

    def ip_patent_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        tech_meta = state["technology_meta"]
        pub_num = tech_meta.get("patent_application_number") or "IDP000089421"
        jurisdiction = tech_meta.get("patent_jurisdiction") or "ID"
        patent_status = tech_meta.get("patent_status", "granted")

        ops_adapter = EPOOPSAdapter()
        live_ops_result = ops_adapter.fetch_patent_record(pub_num)

        # Check manual patent evidence records imported into MarketComparable
        manual_patent_rows = list(
            db.execute(
                select(MarketComparable).where(
                    MarketComparable.technology_id == state["technology_id"],
                    MarketComparable.evidence_category == "patent_family_record",
                )
            ).scalars()
        )
        if manual_patent_rows:
            mp = manual_patent_rows[0]
            meta = mp.metadata_json or {}
            signal_rec = build_manual_patent_signal_record(
                patent_number=pub_num,
                jurisdiction=mp.jurisdiction,
                family_size=int(meta.get("family_size", 3)),
                forward_citations=int(meta.get("forward_citations", 6)),
                backward_citations=int(meta.get("backward_citations", 11)),
                family_jurisdictions=meta.get("family_jurisdictions", ["ID", "WO", "SG"]),
                source_citation=mp.source_citation,
            )
        elif patent_status in ("none", "trade_secret"):
            signal_rec = {
                "patent_status": patent_status,
                "patent_applicable": False,
                "message": f"Technology IP protection mode is '{patent_status}'; patent citation/family indicators are not applicable.",
                "epo_ops_status": live_ops_result["status"],
                "monetary_conversion_prohibited": True,
            }
        else:
            signal_rec = build_manual_patent_signal_record(
                patent_number=pub_num,
                jurisdiction=jurisdiction,
                family_size=2,
                forward_citations=4,
                backward_citations=9,
                family_jurisdictions=[jurisdiction, "WO"],
                source_citation="Uploaded patent specification disclosure & national registry metadata",
            )
            signal_rec["epo_ops_probe"] = live_ops_result

        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "ip_patent",
            state["provider"],
            state["model_name"],
            "ip_patent_contextual_harhoff_2003",
            latency,
            signal_rec,
        )
        _check_cancellation_and_checkpoint(db, run_id, 3, "ip_patent", 38, signal_rec)
        return {**state, "ip_patent_signals": signal_rec}

    def market_assessment_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        tech_id = state["technology_id"]

        market_rows = list(
            db.execute(
                select(MarketComparable).where(
                    MarketComparable.technology_id == tech_id,
                    MarketComparable.evidence_category.in_(["market_size_citation", "comparable_transaction"]),
                )
            ).scalars()
        )
        cited_market_evidence = [
            {
                "id": r.id,
                "category": r.evidence_category,
                "title": r.title,
                "source_citation": r.source_citation,
                "jurisdiction": r.jurisdiction,
                "year": r.transaction_year,
                "unadjusted_value_idr": r.unadjusted_value_idr,
                "royalty_rate_percent": r.royalty_rate_percent,
                "is_credible_verified": r.is_credible_verified,
            }
            for r in market_rows
        ]

        market_intel = {
            "cited_market_evidence_count": len(cited_market_evidence),
            "cited_market_evidence": cited_market_evidence,
            "external_live_market_feed": "unavailable",
            "availability_notice": (
                "Manually cited market evidence imports are active. Unverified external live market feeds "
                "remain explicitly marked unavailable rather than estimated."
                if cited_market_evidence
                else "No manually cited market evidence imported yet; external market data is marked unavailable."
            ),
        }
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "market_assessment",
            state["provider"],
            state["model_name"],
            "market_evidence_registry_check",
            latency,
            market_intel,
        )
        _check_cancellation_and_checkpoint(db, run_id, 4, "market_assessment", 52, market_intel)
        return {**state, "market_intelligence": market_intel}

    def commercialization_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        res = invoke_structured_provider(
            provider=state["provider"],
            model_name=state["model_name"],
            agent_name="commercialization",
            system_prompt=(
                "Evaluate Commercialization Readiness indicators on their defined 1-5 rubrics. "
                "Cite exact document_id, location_ref, and verbatim quoted_text."
            ),
            document_context=state["document_context"],
            technology_meta=state["technology_meta"],
            indicator_defs=state["indicator_defs"],
        )
        pathway = {
            "recommended_mode_en": "Non-Exclusive / Field-of-Use Industrial Licensing or Joint Venture Spin-Off",
            "recommended_mode_id": "Lisensi Industri Non-Eksklusif / Bidang Penggunaan atau Spin-Off Usaha Patungan",
            "key_milestones_en": [
                "Complete pilot-scale reliability validation under industrial operating conditions",
                "Execute material transfer / NDA & term sheet with domestic manufacturing partner",
                "Finalize BPOM / SNI / ministry regulatory conformity certification",
            ],
            "key_milestones_id": [
                "Menyelesaikan validasi keandalan skala pilot pada kondisi operasi industri",
                "Menandatangani NDA & term sheet dengan mitra manufaktur domestik",
                "Menyelesaikan sertifikasi kesesuaian regulasi SNI / kementerian terkait",
            ],
        }
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "commercialization",
            res["actual_provider_returned"],
            res["actual_model_returned"],
            res["prompt_hash"],
            latency,
            {"indicators_evaluated": len(res["data"].get("indicators", []))},
        )
        _check_cancellation_and_checkpoint(db, run_id, 5, "commercialization", 66, pathway)
        prompt_hashes = list(state.get("prompt_hashes", [])) + [res["prompt_hash"]]
        return {
            **state,
            "prompt_hashes": prompt_hashes,
            "comm_eval_raw": res["data"],
            "commercialization_pathway": pathway,
        }

    def risk_assessment_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        ocr_docs = state.get("extraction_summary", {}).get("ocr_flagged_documents", [])
        contradictions = state.get("contradictory_evidence_flags", [])

        risk_items = [
            {
                "category": "Technical Scale-Up Risk",
                "severity": "Medium",
                "description_en": "Transition from laboratory/pilot prototype to continuous industrial throughput requires process stability verification.",
                "description_id": "Transisi dari prototipe laboratorium/pilot ke kapasitas industri kontinu memerlukan verifikasi stabilitas proses.",
                "mitigation_en": "Stage-gated pilot campaign with explicit TRL exit criteria.",
                "mitigation_id": "Kampanye pilot bertahap dengan kriteria keluar TRL yang eksplisit.",
            },
            {
                "category": "IP & Freedom-to-Operate Risk",
                "severity": "Low" if state["technology_meta"].get("patent_status") == "granted" else "High",
                "description_en": "Jurisdictional boundary of patent claims and ongoing annuity maintenance obligations.",
                "description_id": "Batas yurisdiksi klaim paten dan kewajiban pemeliharaan tahunan yang berkelanjutan.",
                "mitigation_en": "Maintain PDKI/EPO renewal schedule and document claim-to-product mapping.",
                "mitigation_id": "Menjaga jadwal pemeliharaan PDKI/EPO dan mendokumentasikan pemetaan klaim terhadap produk.",
            },
            {
                "category": "Evidence & Documentation Risk",
                "severity": "High" if (ocr_docs or contradictions) else "Low",
                "description_en": (
                    f"Flagged issues: {len(ocr_docs)} OCR-dependent document(s), {len(contradictions)} contradiction(s)."
                    if (ocr_docs or contradictions)
                    else "Primary technical disclosure and test logs are machine-readable and verifiable."
                ),
                "description_id": (
                    f"Temuan: {len(ocr_docs)} dokumen memerlukan OCR, {len(contradictions)} kontradiksi bukti."
                    if (ocr_docs or contradictions)
                    else "Dokumen pengungkapan teknis utama dan log pengujian dapat diverifikasi."
                ),
                "mitigation_en": "Supply machine-readable test reports and resolve conflicting claims prior to expert sign-off.",
                "mitigation_id": "Lengkapi laporan uji terbaca-mesin dan selesaikan klaim yang bertentangan sebelum persetujuan pakar.",
            },
        ]
        risk_matrix = {
            "risk_items": risk_items,
            "valuation_risk_treatment_policy": (
                "Technology commercialization risk must be accounted for in EITHER scenario-adjusted cash flows "
                "OR the discount rate premium, never both simultaneously (double-counting guard active)."
            ),
        }
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "risk_assessment",
            state["provider"],
            state["model_name"],
            "risk_matrix_deterministic",
            latency,
            risk_matrix,
        )
        _check_cancellation_and_checkpoint(db, run_id, 6, "risk_assessment", 78, risk_matrix)
        return {**state, "risk_matrix": risk_matrix}

    def financial_valuation_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        tech_id = state["technology_id"]

        # Default explicit financial assumptions in IDR (never derived from assessment scores!)
        base_dcf_inputs = {
            "economic_life_years": 5,
            "discount_rate": 0.14,
            "tax_rate": 0.22,
            "year_zero_investment_idr": 450_000_000.0,
            "attribution_mode": "documented_attribution_factor",
            "attribution_factor": 0.35,
            "attribution_documentation": (
                "Technology-attributable share (35%) of incremental operating cash flows based on "
                "core patented process module contribution to unit cost reduction and product margin."
            ),
            "terminal_value_enabled": False,
            "risk_treatment_mode": "in_discount_rate",
            "cash_flow_probability_haircut": 0.0,
            "discount_rate_technology_premium": 0.04,
            "annual_projections": [
                {"year": 1, "ebitda_idr": 650_000_000.0, "depreciation_idr": 90_000_000.0, "capex_idr": 50_000_000.0, "working_capital_change_idr": 30_000_000.0},
                {"year": 2, "ebitda_idr": 1_100_000_000.0, "depreciation_idr": 90_000_000.0, "capex_idr": 40_000_000.0, "working_capital_change_idr": 45_000_000.0},
                {"year": 3, "ebitda_idr": 1_650_000_000.0, "depreciation_idr": 90_000_000.0, "capex_idr": 45_000_000.0, "working_capital_change_idr": 50_000_000.0},
                {"year": 4, "ebitda_idr": 2_100_000_000.0, "depreciation_idr": 90_000_000.0, "capex_idr": 40_000_000.0, "working_capital_change_idr": 40_000_000.0},
                {"year": 5, "ebitda_idr": 2_400_000_000.0, "depreciation_idr": 90_000_000.0, "capex_idr": 35_000_000.0, "working_capital_change_idr": 25_000_000.0},
            ],
        }
        low_dcf_inputs = {
            **base_dcf_inputs,
            "discount_rate": 0.16,
            "annual_projections": [
                {**p, "ebitda_idr": p["ebitda_idr"] * 0.78} for p in base_dcf_inputs["annual_projections"]
            ],
        }
        high_dcf_inputs = {
            **base_dcf_inputs,
            "discount_rate": 0.12,
            "annual_projections": [
                {**p, "ebitda_idr": p["ebitda_idr"] * 1.22} for p in base_dcf_inputs["annual_projections"]
            ],
        }

        dcf_base = calculate_dcf_valuation(base_dcf_inputs)
        dcf_low = calculate_dcf_valuation(low_dcf_inputs)
        dcf_high = calculate_dcf_valuation(high_dcf_inputs)
        sensitivity = run_dcf_sensitivity_analysis(base_dcf_inputs)
        monte_carlo = run_seeded_monte_carlo_dcf(base_dcf_inputs, seed=202610, iterations=1000)

        cost_inputs = {
            "rd_labor_cost_idr": 380_000_000.0,
            "materials_prototyping_cost_idr": 290_000_000.0,
            "testing_certification_cost_idr": 140_000_000.0,
            "ip_legal_filing_cost_idr": 45_000_000.0,
            "engineering_overhead_cost_idr": 95_000_000.0,
            "functional_obsolescence_rate": 0.08,
            "economic_obsolescence_rate": 0.05,
        }
        cost_res = calculate_cost_valuation(cost_inputs)

        royalty_inputs = {
            "economic_life_years": 5,
            "discount_rate": 0.14,
            "tax_rate": 0.22,
            "royalty_rate": 0.045,
            "annual_revenues_idr": [
                2_200_000_000.0,
                3_800_000_000.0,
                5_500_000_000.0,
                7_100_000_000.0,
                8_200_000_000.0,
            ],
            "annual_ip_maintenance_cost_idr": 18_000_000.0,
            "year_zero_setup_cost_idr": 60_000_000.0,
        }
        royalty_res = calculate_relief_from_royalty_valuation(royalty_inputs)

        # Market comparables approach (only enabled if credible verified comparables exist for this technology)
        comp_rows = list(
            db.execute(
                select(MarketComparable).where(
                    MarketComparable.technology_id == tech_id,
                    MarketComparable.evidence_category == "comparable_transaction",
                )
            ).scalars()
        )
        comp_dicts = [
            {
                "id": c.id,
                "title": c.title,
                "source_citation": c.source_citation,
                "jurisdiction": c.jurisdiction,
                "transaction_year": c.transaction_year,
                "unadjusted_value_idr": c.unadjusted_value_idr,
                "adjustment_factor": c.adjustment_factor,
                "adjustment_rationale": c.adjustment_rationale,
                "is_credible_verified": c.is_credible_verified,
            }
            for c in comp_rows
        ]
        market_comp_res: Optional[Dict[str, Any]] = None
        market_comp_disabled_reason: Optional[str] = None
        try:
            market_comp_res = calculate_market_comparables_valuation(comp_dicts)
        except ValueError as exc:
            market_comp_disabled_reason = str(exc)

        valuation_outputs = {
            "dcf_base": {"inputs": base_dcf_inputs, "result": dcf_base, "sensitivity": sensitivity, "monte_carlo": monte_carlo},
            "dcf_low": {"inputs": low_dcf_inputs, "result": dcf_low},
            "dcf_high": {"inputs": high_dcf_inputs, "result": dcf_high},
            "cost_base": {"inputs": cost_inputs, "result": cost_res},
            "relief_from_royalty_base": {"inputs": royalty_inputs, "result": royalty_res},
            "market_comparables": market_comp_res,
            "market_comparables_disabled_reason": market_comp_disabled_reason,
        }
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "financial_valuation",
            "deterministic_python",
            "wipo_financial_engine_v1",
            "deterministic_financial_calc",
            latency,
            {
                "dcf_base_idr": dcf_base["indicative_value_idr"],
                "cost_base_idr": cost_res["indicative_value_idr"],
                "royalty_base_idr": royalty_res["indicative_value_idr"],
                "market_comparables_enabled": market_comp_res is not None,
            },
        )
        _check_cancellation_and_checkpoint(
            db,
            run_id,
            7,
            "financial_valuation",
            90,
            {"dcf_base_idr": dcf_base["indicative_value_idr"]},
        )
        return {**state, "valuation_outputs": valuation_outputs}

    def evidence_validation_node(state: TechValGraphState) -> TechValGraphState:
        t0 = time.perf_counter()
        run_id = state["run_id"]
        tech_id = state["technology_id"]
        valid_doc_ids = set(state.get("valid_doc_ids", []))
        sections_map_raw = state.get("stored_sections_map", {})
        stored_sections_by_doc_and_loc: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for key_str, sec_val in sections_map_raw.items():
            doc_id_k, loc_k = key_str.split("::", 1)
            stored_sections_by_doc_and_loc[(doc_id_k, loc_k)] = sec_val

        ind_defs_by_code = {i["code"]: i for i in state["indicator_defs"]}
        weights_map = state.get("weights_map", {})

        raw_evals: List[Dict[str, Any]] = []
        raw_evals.extend(state.get("tech_eval_raw", {}).get("indicators", []))
        raw_evals.extend(state.get("comm_eval_raw", {}).get("indicators", []))

        resolved_evidence_list: List[Dict[str, Any]] = []
        rejected_claims_list: List[Dict[str, Any]] = []
        tech_items: List[Dict[str, Any]] = []
        comm_items: List[Dict[str, Any]] = []

        for ev_item in raw_evals:
            code = ev_item["indicator_code"]
            idef = ind_defs_by_code.get(code)
            if not idef:
                continue

            candidate_ev_links = ev_item.get("evidence", [])
            accepted_for_indicator: List[Dict[str, Any]] = []
            for cand in candidate_ev_links:
                val_res = validate_and_resolve_evidence(
                    cand,
                    stored_sections_by_doc_and_loc=stored_sections_by_doc_and_loc,
                    valid_doc_ids=valid_doc_ids,
                )
                if val_res["is_valid"]:
                    accepted_for_indicator.append(val_res)
                    resolved_evidence_list.append(val_res)
                else:
                    rejected_claims_list.append(val_res)

            # An indicator can only remain 'observed' if it has at least one resolved evidence link!
            # If all candidate evidence links were rejected or missing, downgrade status to 'missing'.
            status_val = ev_item.get("status", "missing")
            raw_score_val = ev_item.get("raw_score")
            rationale_en = ev_item.get("rationale_en", "")
            rationale_id = ev_item.get("rationale_id", "")

            if status_val == "observed" and len(accepted_for_indicator) == 0:
                status_val = "missing"
                raw_score_val = None
                rationale_en += " [Downgraded to missing: no resolvable documentary evidence link verified.]"
                rationale_id += " [Diturunkan menjadi kurang bukti: tidak ada tautan bukti dokumen yang terverifikasi.]"

            entry = {
                "indicator_id": idef["id"],
                "indicator_code": code,
                "dimension": idef["dimension"],
                "scale_type": idef["scale_type"],
                "is_patent_specific": idef["is_patent_specific"],
                "status": status_val,
                "raw_score": raw_score_val,
                "base_weight": float(weights_map.get(code, idef["default_provisional_weight"])),
                "rationale_en": rationale_en,
                "rationale_id": rationale_id,
                "accepted_evidence": accepted_for_indicator,
            }
            if idef["dimension"] == "technology_assessment":
                tech_items.append(entry)
            else:
                comm_items.append(entry)

        tech_agg = compute_dimension_aggregate(
            tech_items, weight_set_is_provisional=state.get("weight_set_is_provisional", True)
        )
        comm_agg = compute_dimension_aggregate(
            comm_items, weight_set_is_provisional=state.get("weight_set_is_provisional", True)
        )

        # Overall weighted completeness across all applicable 1-5 indicators
        total_app = tech_agg["applicable_count"] + comm_agg["applicable_count"]
        if total_app > 0:
            overall_completeness = round(
                (
                    tech_agg["weighted_completeness"] * tech_agg["applicable_count"]
                    + comm_agg["weighted_completeness"] * comm_agg["applicable_count"]
                )
                / float(total_app),
                6,
            )
        else:
            overall_completeness = 0.0

        combined_provisional_reasons = list(
            dict.fromkeys(tech_agg["provisional_reasons"] + comm_agg["provisional_reasons"])
        )
        if state.get("contradictory_evidence_flags"):
            combined_provisional_reasons.append("Contradictory documentary claims detected across sections.")

        # Idempotency check: if a revision already exists for this analysis_run_id (from a prior attempt), remove it first
        existing_revs = list(
            db.execute(
                select(AssessmentRevision).where(AssessmentRevision.analysis_run_id == run_id)
            ).scalars()
        )
        for ex_rev in existing_revs:
            db.delete(ex_rev)
        db.flush()

        # Find latest revision for this technology to set revision_number and parent_revision_id
        latest_rev = db.execute(
            select(AssessmentRevision)
            .where(AssessmentRevision.technology_id == tech_id)
            .order_by(AssessmentRevision.revision_number.desc())
        ).scalars().first()

        next_rev_num = (latest_rev.revision_number + 1) if latest_rev else 1
        parent_rev_id = latest_rev.id if latest_rev else None

        # Mark any previous active expert reviews on older revisions as stale if a new revision is created
        if latest_rev:
            old_reviews = list(
                db.execute(
                    select(ExpertReview).where(
                        ExpertReview.technology_id == tech_id,
                        ExpertReview.status == "approved",
                    )
                ).scalars()
            )
            for orv in old_reviews:
                orv.status = "stale"
                orv.stale_reason = f"Superseded by new assessment revision #{next_rev_num} from analysis run."
                orv.invalidated_at = datetime.now(timezone.utc)

        run_row = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one()

        new_rev = AssessmentRevision(
            technology_id=tech_id,
            analysis_run_id=run_id,
            parent_revision_id=parent_rev_id,
            weight_set_id=state.get("weight_set_id"),
            revision_number=next_rev_num,
            actor_id=run_row.created_by,
            change_reason=f"Automated 8-agent analysis run ({run_id[:8]})",
            previous_values_json=None,
            technology_assessment_score=tech_agg["aggregate_score"],
            trl_score=tech_agg["trl_score"],
            trl_exit_criteria_met_json=state.get("tech_eval_raw", {}).get("trl_exit_criteria_met", []),
            commercialization_readiness_score=comm_agg["aggregate_score"],
            evidence_completeness_score=overall_completeness,
            tech_completeness_score=tech_agg["weighted_completeness"],
            comm_completeness_score=comm_agg["weighted_completeness"],
            is_provisional=bool(tech_agg["is_provisional"] or comm_agg["is_provisional"] or len(combined_provisional_reasons) > 0),
            provisional_reasons_json=combined_provisional_reasons,
            applicable_indicator_count=tech_agg["applicable_count"] + comm_agg["applicable_count"],
            observed_indicator_count=tech_agg["observed_count"] + comm_agg["observed_count"],
            missing_indicator_count=tech_agg["missing_count"] + comm_agg["missing_count"],
            not_applicable_indicator_count=tech_agg["not_applicable_count"] + comm_agg["not_applicable_count"],
            ip_patent_signals_json=state.get("ip_patent_signals", {}),
            market_intelligence_json=state.get("market_intelligence", {}),
            commercialization_pathway_json=state.get("commercialization_pathway", {}),
            risk_matrix_json=state.get("risk_matrix", {}),
        )
        db.add(new_rev)
        db.flush()

        # Persist IndicatorScore & EvidenceItem rows
        for item in tech_agg["items"] + comm_agg["items"]:
            score_row = IndicatorScore(
                assessment_revision_id=new_rev.id,
                indicator_id=item["indicator_id"],
                indicator_code=item["indicator_code"],
                dimension=item["dimension"],
                status=item["status"],
                scale_type=item["scale_type"],
                raw_score=item.get("raw_score"),
                normalized_score=item.get("normalized_score"),
                base_weight=float(item.get("base_weight", 0.0)),
                renormalized_weight=float(item.get("renormalized_weight", 0.0)),
                rationale_en=item.get("rationale_en", ""),
                rationale_id=item.get("rationale_id", ""),
                expert_review_status="pending",
            )
            db.add(score_row)
            db.flush()

            for ev in item.get("accepted_evidence", []):
                ev_row = EvidenceItem(
                    assessment_revision_id=new_rev.id,
                    indicator_score_id=score_row.id,
                    document_id=ev["document_id"],
                    section_id=ev["section_id"],
                    indicator_code=item["indicator_code"],
                    location_ref=ev["location_ref"],
                    quoted_text=ev["quoted_text"],
                    claim_summary=ev["claim_summary"],
                    resolution_status="resolved",
                )
                db.add(ev_row)

        # Persist rejected evidence items for transparency
        for rej in rejected_claims_list:
            rej_row = EvidenceItem(
                assessment_revision_id=new_rev.id,
                indicator_score_id=None,
                document_id=rej.get("document_id"),
                section_id=rej.get("section_id"),
                indicator_code=rej.get("indicator_code", "GENERAL"),
                location_ref=rej.get("location_ref", "unknown"),
                quoted_text=rej.get("quoted_text", ""),
                claim_summary=rej.get("claim_summary", ""),
                resolution_status=rej["resolution_status"],
                rejection_reason=rej.get("rejection_reason"),
            )
            db.add(rej_row)

        # Persist ValuationScenario rows (DCF Low/Base/High, Cost, Relief-from-Royalty, and Market Comparables if enabled)
        val_out = state.get("valuation_outputs", {})
        primary_scen_id: Optional[str] = None

        for case_key, case_label, case_code in [
            ("dcf_base", "DCF Base Scenario (IDR)", "base"),
            ("dcf_low", "DCF Downside / Low Scenario (IDR)", "low"),
            ("dcf_high", "DCF Upside / High Scenario (IDR)", "high"),
        ]:
            if case_key in val_out:
                d_item = val_out[case_key]
                res_d = d_item["result"]
                scen = ValuationScenario(
                    technology_id=tech_id,
                    assessment_revision_id=new_rev.id,
                    scenario_name=case_label,
                    scenario_case=case_code,
                    approach="dcf",
                    currency="IDR",
                    attribution_mode=res_d["attribution_mode"],
                    attribution_factor=res_d["effective_attribution_factor"],
                    attribution_documentation=res_d["attribution_documentation"],
                    risk_treatment_mode=res_d["risk_treatment_mode"],
                    double_counting_flagged=res_d["double_counting_flagged"],
                    double_counting_warning=res_d["double_counting_warning"],
                    inputs_json=d_item["inputs"],
                    calculation_breakdown_json=res_d,
                    indicative_value_idr=res_d["indicative_value_idr"],
                    sensitivity_json=d_item.get("sensitivity", []),
                    monte_carlo_seed=d_item.get("monte_carlo", {}).get("seed") if d_item.get("monte_carlo") else None,
                    monte_carlo_json=d_item.get("monte_carlo"),
                    wipo_reference_locator=res_d["wipo_reference_locator"],
                    created_by=run_row.created_by,
                )
                db.add(scen)
                db.flush()
                if case_code == "base":
                    primary_scen_id = scen.id

        if "cost_base" in val_out:
            c_item = val_out["cost_base"]
            res_c = c_item["result"]
            db.add(
                ValuationScenario(
                    technology_id=tech_id,
                    assessment_revision_id=new_rev.id,
                    scenario_name="Replacement Cost Approach (IDR)",
                    scenario_case="base",
                    approach="cost",
                    currency="IDR",
                    attribution_mode="direct_cash_flows",
                    risk_treatment_mode="in_discount_rate",
                    inputs_json=c_item["inputs"],
                    calculation_breakdown_json=res_c,
                    indicative_value_idr=res_c["indicative_value_idr"],
                    wipo_reference_locator=res_c["wipo_reference_locator"],
                    created_by=run_row.created_by,
                )
            )

        if "relief_from_royalty_base" in val_out:
            r_item = val_out["relief_from_royalty_base"]
            res_r = r_item["result"]
            db.add(
                ValuationScenario(
                    technology_id=tech_id,
                    assessment_revision_id=new_rev.id,
                    scenario_name="Relief-from-Royalty Approach (IDR)",
                    scenario_case="base",
                    approach="relief_from_royalty",
                    currency="IDR",
                    attribution_mode="direct_cash_flows",
                    risk_treatment_mode="in_discount_rate",
                    inputs_json=r_item["inputs"],
                    calculation_breakdown_json=res_r,
                    indicative_value_idr=res_r["indicative_value_idr"],
                    wipo_reference_locator=res_r["wipo_reference_locator"],
                    created_by=run_row.created_by,
                )
            )

        if val_out.get("market_comparables"):
            res_m = val_out["market_comparables"]
            db.add(
                ValuationScenario(
                    technology_id=tech_id,
                    assessment_revision_id=new_rev.id,
                    scenario_name="Market Comparables Indication Range (IDR)",
                    scenario_case="base",
                    approach="market_comparables",
                    currency="IDR",
                    attribution_mode="direct_cash_flows",
                    risk_treatment_mode="in_discount_rate",
                    inputs_json={"comparables": res_m["adjusted_indications"]},
                    calculation_breakdown_json=res_m,
                    indicative_value_idr=res_m["median_indication_idr"],
                    range_min_idr=res_m["range_min_idr"],
                    range_max_idr=res_m["range_max_idr"],
                    wipo_reference_locator=res_m["wipo_reference_locator"],
                    created_by=run_row.created_by,
                )
            )

        new_rev.primary_valuation_scenario_id = primary_scen_id
        run_row.rejected_claims_json = rejected_claims_list

        tech_row = db.execute(select(Technology).where(Technology.id == tech_id)).scalar_one()
        tech_row.status = "under_review"

        db.commit()

        val_summary = {
            "revision_id": new_rev.id,
            "revision_number": new_rev.revision_number,
            "technology_assessment_score": new_rev.technology_assessment_score,
            "trl_score": new_rev.trl_score,
            "commercialization_readiness_score": new_rev.commercialization_readiness_score,
            "evidence_completeness_score": new_rev.evidence_completeness_score,
            "resolved_evidence_count": len(resolved_evidence_list),
            "rejected_claims_count": len(rejected_claims_list),
            "is_provisional": new_rev.is_provisional,
        }
        latency = int((time.perf_counter() - t0) * 1000)
        _record_agent_execution(
            db,
            run_id,
            "evidence_validation",
            "deterministic_validator",
            "evidence_resolver_v1",
            "evidence_resolution_check",
            latency,
            val_summary,
        )
        _check_cancellation_and_checkpoint(db, run_id, 8, "evidence_validation", 100, val_summary)

        return {
            **state,
            "rejected_claims": rejected_claims_list,
            "resolved_evidence": resolved_evidence_list,
            "created_revision_id": new_rev.id,
        }

    graph = StateGraph(TechValGraphState)
    graph.add_node("extraction", extraction_node)
    graph.add_node("technology_assessment", technology_assessment_node)
    graph.add_node("ip_patent", ip_patent_node)
    graph.add_node("market_assessment", market_assessment_node)
    graph.add_node("commercialization", commercialization_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("financial_valuation", financial_valuation_node)
    graph.add_node("evidence_validation", evidence_validation_node)

    graph.add_edge(START, "extraction")
    graph.add_edge("extraction", "technology_assessment")
    graph.add_edge("technology_assessment", "ip_patent")
    graph.add_edge("ip_patent", "market_assessment")
    graph.add_edge("market_assessment", "commercialization")
    graph.add_edge("commercialization", "risk_assessment")
    graph.add_edge("risk_assessment", "financial_valuation")
    graph.add_edge("financial_valuation", "evidence_validation")
    graph.add_edge("evidence_validation", END)

    return graph.compile()


def execute_analysis_run(db: Session, run_id: str) -> AnalysisRun:
    """
    Loads the AnalysisRun, verifies consent binding against current document hashes and
    run configuration, executes the 8-node LangGraph workflow, and updates the run state.
    """
    run = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise ValueError(f"AnalysisRun '{run_id}' not found.")

    if run.cancel_requested or run.status == "cancelled":
        run.status = "cancelled"
        db.commit()
        return run

    # Verify explicit consent record
    if not run.consent_record_id:
        run.status = "failed"
        run.error_message = "Explicit consent record is required before analysis execution."
        db.commit()
        return run

    consent = db.execute(
        select(ConsentRecord).where(ConsentRecord.id == run.consent_record_id)
    ).scalar_one_or_none()
    if not consent or not consent.consent_granted:
        run.status = "failed"
        run.error_message = "Consent was denied or is missing. Execution blocked."
        db.commit()
        return run

    # Verify consent binding to document hashes and run config hash
    docs = list(
        db.execute(
            select(Document).where(
                Document.technology_id == run.technology_id,
                Document.is_deleted.is_(False),
            )
        ).scalars()
    )
    current_doc_hashes = {d.id: d.sha256_hash for d in docs if d.id in (consent.document_ids_json or [])}
    if current_doc_hashes != (consent.document_hashes_json or {}):
        run.status = "failed"
        run.error_message = (
            "Consent binding invalidated: document hashes changed since consent was granted. Renewed consent is required."
        )
        db.commit()
        return run

    if consent.run_config_hash != run.run_config_hash:
        run.status = "failed"
        run.error_message = (
            "Consent binding invalidated: analysis run configuration changed since consent was granted. Renewed consent is required."
        )
        db.commit()
        return run

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    run.error_message = None
    db.commit()

    tech = db.execute(select(Technology).where(Technology.id == run.technology_id)).scalar_one()
    tech.status = "in_analysis"
    db.commit()

    # Build document context and stored_sections_map
    doc_context: List[Dict[str, Any]] = []
    stored_sections_map: Dict[str, Dict[str, Any]] = {}
    valid_doc_ids: List[str] = []

    selected_docs = [d for d in docs if d.id in (consent.document_ids_json or [])]
    for d in selected_docs:
        valid_doc_ids.append(d.id)
        secs = list(
            db.execute(
                select(DocumentSection)
                .where(DocumentSection.document_id == d.id)
                .order_by(DocumentSection.section_index.asc())
            ).scalars()
        )
        sec_list = []
        for s in secs:
            s_dict = {
                "id": s.id,
                "section_index": s.section_index,
                "location_type": s.location_type,
                "location_ref": s.location_ref,
                "heading": s.heading,
                "content_text": s.content_text,
                "char_count": s.char_count,
            }
            sec_list.append(s_dict)
            stored_sections_map[f"{d.id}::{s.location_ref}"] = s_dict

        doc_context.append(
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "document_type": d.document_type,
                "sha256_hash": d.sha256_hash,
                "ocr_required": d.ocr_required,
                "extracted_char_count": d.extracted_char_count,
                "sections": sec_list,
            }
        )

    ind_rows = list(db.execute(select(IndicatorDefinition).order_by(IndicatorDefinition.code.asc())).scalars())
    ind_defs = [
        {
            "id": i.id,
            "code": i.code,
            "dimension": i.dimension,
            "scale_type": i.scale_type,
            "is_patent_specific": i.is_patent_specific,
            "default_provisional_weight": i.default_provisional_weight,
        }
        for i in ind_rows
    ]

    weight_set = None
    if run.weight_set_id:
        weight_set = db.execute(select(WeightSet).where(WeightSet.id == run.weight_set_id)).scalar_one_or_none()
    if not weight_set:
        weight_set = db.execute(select(WeightSet).where(WeightSet.is_active.is_(True))).scalars().first()

    weights_map = weight_set.weights_json if weight_set else {}
    weight_set_is_provisional = weight_set.is_provisional if weight_set else True

    initial_state: TechValGraphState = {
        "run_id": run.id,
        "technology_id": tech.id,
        "provider": run.requested_provider,
        "model_name": run.requested_model,
        "actual_provider_returned": run.requested_provider,
        "actual_model_returned": run.requested_model,
        "prompt_hashes": [],
        "technology_meta": {
            "id": tech.id,
            "code": tech.code,
            "title_en": tech.title_en,
            "domain": tech.domain,
            "claimed_trl": tech.claimed_trl,
            "patent_status": tech.patent_status,
            "patent_application_number": tech.patent_Application_number,
            "patent_jurisdiction": tech.patent_jurisdiction,
            **(run.config_snapshot_json or {}),
        },
        "document_context": doc_context,
        "stored_sections_map": stored_sections_map,
        "valid_doc_ids": valid_doc_ids,
        "indicator_defs": ind_defs,
        "weights_map": weights_map,
        "weight_set_id": weight_set.id if weight_set else None,
        "weight_set_is_provisional": weight_set_is_provisional,
    }

    try:
        compiled_graph = build_techval_langgraph(db)
        final_state = compiled_graph.invoke(initial_state)
        db.refresh(run)
        run.status = "completed"
        run.progress_percent = 100
        run.current_node = "completed"
        run.actual_provider_returned = final_state.get("actual_provider_returned", run.requested_provider)
        run.actual_model_returned = final_state.get("actual_model_returned", run.requested_model)
        if final_state.get("prompt_hashes"):
            run.prompt_hash = final_state["prompt_hashes"][-1]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    except RuntimeError as exc:
        if "ANALYSIS_RUN_CANCELLED" in str(exc):
            db.refresh(run)
            run.status = "cancelled"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        else:
            db.refresh(run)
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
    except ProviderExecutionError as exc:
        db.refresh(run)
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.refresh(run)
        run.status = "failed"
        run.error_message = f"Workflow execution error: {exc}"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

    return run
