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
    IndicatorDefinition,
    IndicatorScore,
    Technology,
    User,
    ValuationScenario,
    WeightSet,
)
from app.schemas import AssessmentExpertRevisionRequest, ExpertSignOffRequest
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.scoring import compute_dimension_aggregate

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/{technology_id}")
def list_expert_reviews(
    technology_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    rows = list(
        db.execute(
            select(ExpertReview)
            .where(ExpertReview.technology_id == technology_id)
            .order_by(ExpertReview.created_at.desc())
        ).scalars()
    )
    return [
        {
            "id": r.id,
            "technology_id": r.technology_id,
            "assessment_revision_id": r.assessment_revision_id,
            "reviewer_id": r.reviewer_id,
            "status": r.status,
            "overall_rationale": r.overall_rationale,
            "methodology_verified": r.methodology_verified,
            "assumptions_verified": r.assumptions_verified,
            "stale_reason": r.stale_reason,
            "invalidated_at": r.invalidated_at.isoformat() if r.invalidated_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/revise-indicators", status_code=status.HTTP_201_CREATED)
def expert_revise_indicators(
    payload: AssessmentExpertRevisionRequest,
    user: User = Depends(require_roles("admin", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Allows expert reviewers to approve/reject indicators and revise scores/status with reasons.
    Preserves immutable assessment revisions: creates a new AssessmentRevision with actor,
    timestamp, reason, and previous_values_json.
    Marks any existing approved ExpertReviews as `stale`.
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

    parent_scores = list(
        db.execute(
            select(IndicatorScore).where(IndicatorScore.assessment_revision_id == parent_rev.id)
        ).scalars()
    )
    ind_defs = {
        i.code: i
        for i in db.execute(select(IndicatorDefinition)).scalars()
    }
    updates_by_code = {u.indicator_code: u for u in payload.indicator_updates}

    prev_snapshot_items: List[Dict[str, Any]] = []
    tech_items: List[Dict[str, Any]] = []
    comm_items: List[Dict[str, Any]] = []

    for ps in parent_scores:
        idef = ind_defs.get(ps.indicator_code)
        upd = updates_by_code.get(ps.indicator_code)
        if upd:
            if len(upd.expert_review_reason.strip()) < 3:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reason required for indicator '{ps.indicator_code}' override.",
                )
            prev_snapshot_items.append(
                {
                    "indicator_code": ps.indicator_code,
                    "previous_status": ps.status,
                    "previous_raw_score": ps.raw_score,
                    "new_status": upd.status,
                    "new_raw_score": upd.raw_score,
                    "expert_review_status": upd.expert_review_status,
                    "expert_review_reason": upd.expert_review_reason,
                }
            )
            status_val = upd.status
            raw_score_val = upd.raw_score
            exp_status = upd.expert_review_status
            exp_reason = upd.expert_review_reason
            rev_by = user.id
        else:
            status_val = ps.status
            raw_score_val = ps.raw_score
            exp_status = ps.expert_review_status
            exp_reason = ps.expert_review_reason
            rev_by = ps.reviewed_by

        entry = {
            "parent_score_id": ps.id,
            "indicator_id": ps.indicator_id,
            "indicator_code": ps.indicator_code,
            "dimension": ps.dimension,
            "scale_type": ps.scale_type,
            "is_patent_specific": idef.is_patent_specific if idef else False,
            "status": status_val,
            "raw_score": raw_score_val,
            "base_weight": ps.base_weight,
            "rationale_en": ps.rationale_en,
            "rationale_id": ps.rationale_id,
            "expert_review_status": exp_status,
            "expert_review_reason": exp_reason,
            "reviewed_by": rev_by,
        }
        if ps.dimension == "technology_assessment":
            tech_items.append(entry)
        else:
            comm_items.append(entry)

    ws = None
    if parent_rev.weight_set_id:
        ws = db.execute(select(WeightSet).where(WeightSet.id == parent_rev.weight_set_id)).scalar_one_or_none()
    ws_provisional = ws.is_provisional if ws else True

    try:
        tech_agg = compute_dimension_aggregate(tech_items, weight_set_is_provisional=ws_provisional)
        comm_agg = compute_dimension_aggregate(comm_items, weight_set_is_provisional=ws_provisional)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    total_app = tech_agg["applicable_count"] + comm_agg["applicable_count"]
    overall_completeness = (
        round(
            (
                tech_agg["weighted_completeness"] * tech_agg["applicable_count"]
                + comm_agg["weighted_completeness"] * comm_agg["applicable_count"]
            )
            / float(total_app),
            6,
        )
        if total_app > 0
        else 0.0
    )

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

    # Invalidate prior approvals (mark stale)
    active_reviews = list(
        db.execute(
            select(ExpertReview).where(
                ExpertReview.technology_id == payload.technology_id,
                ExpertReview.status == "approved",
            )
        ).scalars()
    )
    for ar in active_reviews:
        ar.status = "stale"
        ar.stale_reason = f"Superseded by expert indicator revision #{next_rev_num}: {payload.change_reason}"
        ar.invalidated_at = datetime.now(timezone.utc)

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
        previous_values_json={
            "parent_revision_id": parent_rev.id,
            "parent_revision_number": parent_rev.revision_number,
            "previous_tech_score": parent_rev.technology_assessment_score,
            "previous_comm_score": parent_rev.commercialization_readiness_score,
            "previous_completeness": parent_rev.evidence_completeness_score,
            "indicator_changes": prev_snapshot_items,
        },
        technology_assessment_score=tech_agg["aggregate_score"],
        trl_score=tech_agg["trl_score"],
        trl_exit_criteria_met_json=parent_rev.trl_exit_criteria_met_json,
        commercialization_readiness_score=comm_agg["aggregate_score"],
        evidence_completeness_score=overall_completeness,
        tech_completeness_score=tech_agg["weighted_completeness"],
        comm_completeness_score=comm_agg["weighted_completeness"],
        is_provisional=bool(tech_agg["is_provisional"] or comm_agg["is_provisional"]),
        provisional_reasons_json=list(
            dict.fromkeys(tech_agg["provisional_reasons"] + comm_agg["provisional_reasons"])
        ),
        applicable_indicator_count=tech_agg["applicable_count"] + comm_agg["applicable_count"],
        observed_indicator_count=tech_agg["observed_count"] + comm_agg["observed_count"],
        missing_indicator_count=tech_agg["missing_count"] + comm_agg["missing_count"],
        not_applicable_indicator_count=tech_agg["not_applicable_count"] + comm_agg["not_applicable_count"],
        ip_patent_signals_json=parent_rev.ip_patent_signals_json,
        market_intelligence_json=parent_rev.market_intelligence_json,
        commercialization_pathway_json=parent_rev.commercialization_pathway_json,
        risk_matrix_json=parent_rev.risk_matrix_json,
    )
    db.add(new_rev)
    db.flush()

    score_id_map: Dict[str, str] = {}
    for item in tech_agg["items"] + comm_agg["items"]:
        ns = IndicatorScore(
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
            rationale_en=item["rationale_en"],
            rationale_id=item["rationale_id"],
            expert_review_status=item["expert_review_status"],
            expert_review_reason=item["expert_review_reason"],
            reviewed_by=item["reviewed_by"],
        )
        db.add(ns)
        db.flush()
        score_id_map[item["parent_score_id"]] = ns.id

    # Copy EvidenceItem and ValuationScenario rows to new revision
    for pev in db.execute(
        select(EvidenceItem).where(EvidenceItem.assessment_revision_id == parent_rev.id)
    ).scalars():
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

    for pscen in db.execute(
        select(ValuationScenario).where(ValuationScenario.assessment_revision_id == parent_rev.id)
    ).scalars():
        copied_scen = ValuationScenario(
            technology_id=payload.technology_id,
            assessment_revision_id=new_rev.id,
            scenario_name=pscen.scenario_name,
            scenario_case=pscen.scenario_case,
            approach=pscen.approach,
            currency=pscen.currency,
            attribution_mode=pscen.attribution_mode,
            attribution_factor=pscen.attribution_factor,
            attribution_documentation=pscen.attribution_documentation,
            risk_treatment_mode=pscen.risk_treatment_mode,
            double_counting_flagged=pscen.double_counting_flagged,
            double_counting_warning=pscen.double_counting_warning,
            inputs_json=pscen.inputs_json,
            calculation_breakdown_json=pscen.calculation_breakdown_json,
            indicative_value_idr=pscen.indicative_value_idr,
            range_min_idr=pscen.range_min_idr,
            range_max_idr=pscen.range_max_idr,
            sensitivity_json=pscen.sensitivity_json,
            monte_carlo_seed=pscen.monte_carlo_seed,
            monte_carlo_json=pscen.monte_carlo_json,
            wipo_reference_locator=pscen.wipo_reference_locator,
            created_by=pscen.created_by,
        )
        db.add(copied_scen)
        db.flush()
        if copied_scen.approach == "dcf" and copied_scen.scenario_case == "base":
            new_rev.primary_valuation_scenario_id = copied_scen.id

    record_audit_log(
        db=db,
        actor=user,
        action="assessment.expert_revise",
        entity_type="assessment_revision",
        entity_id=new_rev.id,
        details={
            "parent_revision_id": parent_rev.id,
            "new_revision_number": new_rev.revision_number,
            "change_reason": payload.change_reason,
            "indicator_changes_count": len(prev_snapshot_items),
        },
    )
    db.commit()

    return {
        "new_revision_id": new_rev.id,
        "new_revision_number": new_rev.revision_number,
        "parent_revision_id": parent_rev.id,
        "technology_assessment_score": new_rev.technology_assessment_score,
        "commercialization_readiness_score": new_rev.commercialization_readiness_score,
        "evidence_completeness_score": new_rev.evidence_completeness_score,
        "previous_values_json": new_rev.previous_values_json,
    }


@router.post("/sign-off", status_code=status.HTTP_201_CREATED)
def expert_sign_off_revision(
    payload: ExpertSignOffRequest,
    user: User = Depends(require_roles("admin", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Binds an expert approval/rejection to an exact AssessmentRevision.
    """
    rev = db.execute(
        select(AssessmentRevision).where(
            AssessmentRevision.id == payload.assessment_revision_id,
            AssessmentRevision.technology_id == payload.technology_id,
        )
    ).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Assessment revision not found.")

    if len(payload.overall_rationale.strip()) < 10:
        raise HTTPException(status_code=400, detail="overall_rationale must be at least 10 characters.")

    review = ExpertReview(
        technology_id=payload.technology_id,
        assessment_revision_id=rev.id,
        reviewer_id=user.id,
        status=payload.status,
        overall_rationale=payload.overall_rationale,
        methodology_verified=payload.methodology_verified,
        assumptions_verified=payload.assumptions_verified,
    )
    db.add(review)

    tech = db.execute(select(Technology).where(Technology.id == payload.technology_id)).scalar_one()
    if payload.status == "approved":
        tech.status = "approved"
    else:
        tech.status = "under_review"

    record_audit_log(
        db=db,
        actor=user,
        action="expert_review.sign_off",
        entity_type="expert_review",
        entity_id=rev.id,
        details={"status": payload.status, "revision_number": rev.revision_number},
    )
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "technology_id": review.technology_id,
        "assessment_revision_id": review.assessment_revision_id,
        "status": review.status,
        "overall_rationale": review.overall_rationale,
        "created_at": review.created_at.isoformat(),
    }
