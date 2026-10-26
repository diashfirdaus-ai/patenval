from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    AssessmentRevision,
    EvidenceItem,
    ExpertReview,
    IndicatorScore,
    MarketComparable,
    Technology,
    User,
    ValuationScenario,
)
from app.schemas import ValuationRevisionRequest
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.valuation import (
    calculate_cost_valuation,
    calculate_dcf_valuation,
    calculate_market_comparables_valuation,
    calculate_relief_from_royalty_valuation,
    format_idr,
    run_dcf_sensitivity_analysis,
    run_seeded_monte_carlo_dcf,
)

router = APIRouter(prefix="/valuation", tags=["valuation"])


@router.get("/scenarios/{technology_id}")
def list_valuation_scenarios(
    technology_id: str,
    revision_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not revision_id:
        latest_rev = (
            db.execute(
                select(AssessmentRevision)
                .where(AssessmentRevision.technology_id == technology_id)
                .order_by(AssessmentRevision.revision_number.desc())
            )
            .scalars()
            .first()
        )
        revision_id = latest_rev.id if latest_rev else None

    if not revision_id:
        return {"revision_id": None, "scenarios": [], "separation_notice": "No assessment revision exists yet."}

    scenarios = list(
        db.execute(
            select(ValuationScenario)
            .where(ValuationScenario.assessment_revision_id == revision_id)
            .order_by(ValuationScenario.created_at.asc())
        ).scalars()
    )
    return {
        "technology_id": technology_id,
        "assessment_revision_id": revision_id,
        "methodological_note": (
            "Each valuation approach (DCF, Cost, Market Comparables, Relief-from-Royalty) is presented "
            "separately and never averaged automatically. Assessment scores are never converted into monetary values."
        ),
        "scenarios": [
            {
                "id": s.id,
                "scenario_name": s.scenario_name,
                "scenario_case": s.scenario_case,
                "approach": s.approach,
                "currency": s.currency,
                "attribution_mode": s.attribution_mode,
                "attribution_factor": s.attribution_factor,
                "attribution_documentation": s.attribution_documentation,
                "risk_treatment_mode": s.risk_treatment_mode,
                "double_counting_flagged": s.double_counting_flagged,
                "double_counting_warning": s.double_counting_warning,
                "inputs_json": s.inputs_json,
                "calculation_breakdown_json": s.calculation_breakdown_json,
                "indicative_value_idr": s.indicative_value_idr,
                "indicative_value_formatted": format_idr(s.indicative_value_idr),
                "range_min_idr": s.range_min_idr,
                "range_max_idr": s.range_max_idr,
                "sensitivity_json": s.sensitivity_json,
                "monte_carlo_seed": s.monte_carlo_seed,
                "monte_carlo_json": s.monte_carlo_json,
                "wipo_reference_locator": s.wipo_reference_locator,
                "created_at": s.created_at.isoformat(),
            }
            for s in scenarios
        ],
    }


@router.post("/calculate-preview")
def preview_valuation_calculation(
    payload: Dict[str, Any],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    approach = payload.get("approach", "dcf")
    inputs = payload.get("inputs", {})
    try:
        if approach == "dcf":
            res = calculate_dcf_valuation(inputs)
            sens = run_dcf_sensitivity_analysis(inputs)
            mc = run_seeded_monte_carlo_dcf(
                inputs,
                seed=int(payload.get("monte_carlo_seed", 42)),
                iterations=int(payload.get("monte_carlo_iterations", 500)),
                distributions=payload.get("monte_carlo_distributions"),
            )
            return {"result": res, "sensitivity": sens, "monte_carlo": mc}
        if approach == "cost":
            return {"result": calculate_cost_valuation(inputs)}
        if approach == "relief_from_royalty":
            return {"result": calculate_relief_from_royalty_valuation(inputs)}
        if approach == "market_comparables":
            comparables = inputs.get("comparables", [])
            return {"result": calculate_market_comparables_valuation(comparables)}
        raise ValueError(f"Unsupported valuation approach: {approach}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/revise", status_code=status.HTTP_201_CREATED)
def revise_valuation_and_create_immutable_revision(
    payload: ValuationRevisionRequest,
    user: User = Depends(require_roles("admin", "analyst", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Revises financial assumptions and creates a new immutable AssessmentRevision preserving
    actor, timestamp, change_reason, and previous_values_json.
    Marks any prior approved ExpertReviews on the technology as `stale`.
    """
    if len(payload.change_reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="change_reason is required (at least 5 characters).")

    parent_rev = db.execute(
        select(AssessmentRevision).where(
            AssessmentRevision.id == payload.parent_revision_id,
            AssessmentRevision.technology_id == payload.technology_id,
        )
    ).scalar_one_or_none()
    if not parent_rev:
        raise HTTPException(status_code=404, detail="Parent assessment revision not found.")

    try:
        if payload.approach == "dcf":
            calc_res = calculate_dcf_valuation(payload.inputs)
            sens = run_dcf_sensitivity_analysis(payload.inputs)
            mc = run_seeded_monte_carlo_dcf(
                payload.inputs,
                seed=payload.monte_carlo_seed,
                iterations=payload.monte_carlo_iterations,
                distributions=payload.monte_carlo_distributions,
            )
        elif payload.approach == "cost":
            calc_res = calculate_cost_valuation(payload.inputs)
            sens = []
            mc = None
        elif payload.approach == "relief_from_royalty":
            calc_res = calculate_relief_from_royalty_valuation(payload.inputs)
            sens = []
            mc = None
        elif payload.approach == "market_comparables":
            comp_rows = list(
                db.execute(
                    select(MarketComparable).where(
                        MarketComparable.technology_id == payload.technology_id,
                        MarketComparable.evidence_category == "comparable_transaction",
                    )
                ).scalars()
            )
            comp_dicts = payload.inputs.get("comparables") or [
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
            calc_res = calculate_market_comparables_valuation(comp_dicts)
            sens = []
            mc = None
        else:
            raise ValueError(f"Unsupported valuation approach: {payload.approach}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    latest_rev = (
        db.execute(
            select(AssessmentRevision)
            .where(AssessmentRevision.technology_id == payload.technology_id)
            .order_by(AssessmentRevision.revision_number.desc())
        )
        .scalars()
        .first()
    )
    next_rev_num = (latest_rev.revision_number + 1) if latest_rev else 1

    old_scenarios = list(
        db.execute(
            select(ValuationScenario).where(ValuationScenario.assessment_revision_id == parent_rev.id)
        ).scalars()
    )
    prev_val_snapshot = {
        "parent_revision_id": parent_rev.id,
        "parent_revision_number": parent_rev.revision_number,
        "revised_approach": payload.approach,
        "previous_scenarios": [
            {
                "scenario_name": s.scenario_name,
                "approach": s.approach,
                "scenario_case": s.scenario_case,
                "indicative_value_idr": s.indicative_value_idr,
                "inputs_json": s.inputs_json,
            }
            for s in old_scenarios
            if s.approach == payload.approach and s.scenario_case == payload.scenario_case
        ],
    }

    # Invalidate any active ExpertReviews (mark stale after material edits)
    active_reviews = list(
        db.execute(
            select(ExpertReview).where(
                ExpertReview.technology_id == payload.technology_id,
                ExpertReview.status == "approved",
            )
        ).scalars()
    )
    for rev_row in active_reviews:
        rev_row.status = "stale"
        rev_row.stale_reason = (
            f"Approval invalidated due to material financial assumption edit in Revision #{next_rev_num}: "
            f"{payload.change_reason}"
        )
        rev_row.invalidated_at = datetime.now(timezone.utc)

    tech = db.execute(select(Technology).where(Technology.id == payload.technology_id)).scalar_one()
    tech.status = "under_review"

    new_rev = AssessmentRevision(
        technology_id=payload.technology_id,
        analysis_run_id=parent_rev.analysis_run_id,
        parent_revision_id=parent_rev.id,
        weight_set_id=parent_rev.weight_set_id,
        revision_number=next_rev_num,
        actor_id=user.id,
        change_reason=payload.change_reason,
        previous_values_json=prev_val_snapshot,
        technology_assessment_score=parent_rev.technology_assessment_score,
        trl_score=parent_rev.trl_score,
        trl_exit_criteria_met_json=parent_rev.trl_exit_criteria_met_json,
        commercialization_readiness_score=parent_rev.commercialization_readiness_score,
        evidence_completeness_score=parent_rev.evidence_completeness_score,
        tech_completeness_score=parent_rev.tech_completeness_score,
        comm_completeness_score=parent_rev.comm_completeness_score,
        is_provisional=parent_rev.is_provisional,
        provisional_reasons_json=parent_rev.provisional_reasons_json,
        applicable_indicator_count=parent_rev.applicable_indicator_count,
        observed_indicator_count=parent_rev.observed_indicator_count,
        missing_indicator_count=parent_rev.missing_indicator_count,
        not_applicable_indicator_count=parent_rev.not_applicable_indicator_count,
        ip_patent_signals_json=parent_rev.ip_patent_signals_json,
        market_intelligence_json=parent_rev.market_intelligence_json,
        commercialization_pathway_json=parent_rev.commercialization_pathway_json,
        risk_matrix_json=parent_rev.risk_matrix_json,
    )
    db.add(new_rev)
    db.flush()

    # Copy IndicatorScore and EvidenceItem rows to the new immutable revision
    parent_scores = list(
        db.execute(
            select(IndicatorScore).where(IndicatorScore.assessment_revision_id == parent_rev.id)
        ).scalars()
    )
    score_id_map: Dict[str, str] = {}
    for ps in parent_scores:
        ns = IndicatorScore(
            assessment_revision_id=new_rev.id,
            indicator_id=ps.indicator_id,
            indicator_code=ps.indicator_code,
            dimension=ps.dimension,
            status=ps.status,
            scale_type=ps.scale_type,
            raw_score=ps.raw_score,
            normalized_score=ps.normalized_score,
            base_weight=ps.base_weight,
            renormalized_weight=ps.renormalized_weight,
            rationale_en=ps.rationale_en,
            rationale_id=ps.rationale_id,
            expert_review_status=ps.expert_review_status,
            expert_review_reason=ps.expert_review_reason,
            reviewed_by=ps.reviewed_by,
        )
        db.add(ns)
        db.flush()
        score_id_map[ps.id] = ns.id

    parent_evs = list(
        db.execute(
            select(EvidenceItem).where(EvidenceItem.assessment_revision_id == parent_rev.id)
        ).scalars()
    )
    for pev in parent_evs:
        db.add(
            EvidenceItem(
                assessment_revision_id=new_rev.id,
                indicator_score_id=score_id_map.get(pev.indicator_score_id) if pev.indicator_score_id else None,
                document_id=pev.document_id,
                section_id=pev.section_id,
                indicator_code=pev.indicator_code,
                location_ref=pev.location_ref,
                quoted_text=pev.quoted_text,
                claim_summary=pev.claim_summary,
                resolution_status=pev.resolution_status,
                rejection_reason=pev.rejection_reason,
            )
        )

    # Copy unchanged scenarios and insert the newly revised scenario
    replaced = False
    primary_scen_id = None
    for os_row in old_scenarios:
        if os_row.approach == payload.approach and os_row.scenario_case == payload.scenario_case and not replaced:
            new_scen = ValuationScenario(
                technology_id=payload.technology_id,
                assessment_revision_id=new_rev.id,
                scenario_name=payload.scenario_name,
                scenario_case=payload.scenario_case,
                approach=payload.approach,
                currency="IDR",
                attribution_mode=calc_res.get("attribution_mode", "direct_cash_flows"),
                attribution_factor=calc_res.get("effective_attribution_factor"),
                attribution_documentation=calc_res.get("attribution_documentation"),
                risk_treatment_mode=calc_res.get("risk_treatment_mode", "in_discount_rate"),
                double_counting_flagged=bool(calc_res.get("double_counting_flagged", False)),
                double_counting_warning=calc_res.get("double_counting_warning"),
                inputs_json=payload.inputs,
                calculation_breakdown_json=calc_res,
                indicative_value_idr=calc_res["indicative_value_idr"],
                range_min_idr=calc_res.get("range_min_idr"),
                range_max_idr=calc_res.get("range_max_idr"),
                sensitivity_json=sens,
                monte_carlo_seed=payload.monte_carlo_seed if mc else None,
                monte_carlo_json=mc,
                wipo_reference_locator=calc_res["wipo_reference_locator"],
                created_by=user.id,
            )
            db.add(new_scen)
            db.flush()
            replaced = True
            if new_scen.approach == "dcf" and new_scen.scenario_case == "base":
                primary_scen_id = new_scen.id
        else:
            copied_scen = ValuationScenario(
                technology_id=payload.technology_id,
                assessment_revision_id=new_rev.id,
                scenario_name=os_row.scenario_name,
                scenario_case=os_row.scenario_case,
                approach=os_row.approach,
                currency=os_row.currency,
                attribution_mode=os_row.attribution_mode,
                attribution_factor=os_row.attribution_factor,
                attribution_documentation=os_row.attribution_documentation,
                risk_treatment_mode=os_row.risk_treatment_mode,
                double_counting_flagged=os_row.double_counting_flagged,
                double_counting_warning=os_row.double_counting_warning,
                inputs_json=os_row.inputs_json,
                calculation_breakdown_json=os_row.calculation_breakdown_json,
                indicative_value_idr=os_row.indicative_value_idr,
                range_min_idr=os_row.range_min_idr,
                range_max_idr=os_row.range_max_idr,
                sensitivity_json=os_row.sensitivity_json,
                monte_carlo_seed=os_row.monte_carlo_seed,
                monte_carlo_json=os_row.monte_carlo_json,
                wipo_reference_locator=os_row.wipo_reference_locator,
                created_by=os_row.created_by,
            )
            db.add(copied_scen)
            db.flush()
            if copied_scen.approach == "dcf" and copied_scen.scenario_case == "base":
                primary_scen_id = copied_scen.id

    if not replaced:
        new_scen = ValuationScenario(
            technology_id=payload.technology_id,
            assessment_revision_id=new_rev.id,
            scenario_name=payload.scenario_name,
            scenario_case=payload.scenario_case,
            approach=payload.approach,
            currency="IDR",
            attribution_mode=calc_res.get("attribution_mode", "direct_cash_flows"),
            attribution_factor=calc_res.get("effective_attribution_factor"),
            attribution_documentation=calc_res.get("attribution_documentation"),
            risk_treatment_mode=calc_res.get("risk_treatment_mode", "in_discount_rate"),
            double_counting_flagged=bool(calc_res.get("double_counting_flagged", False)),
            double_counting_warning=calc_res.get("double_counting_warning"),
            inputs_json=payload.inputs,
            calculation_breakdown_json=calc_res,
            indicative_value_idr=calc_res["indicative_value_idr"],
            range_min_idr=calc_res.get("range_min_idr"),
            range_max_idr=calc_res.get("range_max_idr"),
            sensitivity_json=sens,
            monte_carlo_seed=payload.monte_carlo_seed if mc else None,
            monte_carlo_json=mc,
            wipo_reference_locator=calc_res["wipo_reference_locator"],
            created_by=user.id,
        )
        db.add(new_scen)
        db.flush()
        if not primary_scen_id:
            primary_scen_id = new_scen.id

    new_rev.primary_valuation_scenario_id = primary_scen_id

    record_audit_log(
        db=db,
        actor=user,
        action="valuation.revise",
        entity_type="assessment_revision",
        entity_id=new_rev.id,
        details={
            "parent_revision_id": parent_rev.id,
            "new_revision_number": new_rev.revision_number,
            "change_reason": payload.change_reason,
            "approach": payload.approach,
            "indicative_value_idr": calc_res["indicative_value_idr"],
            "stale_reviews_count": len(active_reviews),
        },
    )
    db.commit()

    return {
        "new_revision_id": new_rev.id,
        "new_revision_number": new_rev.revision_number,
        "parent_revision_id": parent_rev.id,
        "change_reason": new_rev.change_reason,
        "previous_values_json": new_rev.previous_values_json,
        "stale_reviews_invalidated": len(active_reviews),
        "updated_valuation": calc_res,
    }
