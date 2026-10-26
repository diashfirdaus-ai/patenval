from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    AssessmentRevision,
    EvidenceItem,
    IndicatorDefinition,
    IndicatorScore,
    User,
)
from app.security.auth import get_current_user

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("")
def list_indicator_definitions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    inds = list(
        db.execute(select(IndicatorDefinition).order_by(IndicatorDefinition.code.asc())).scalars()
    )
    return [
        {
            "id": i.id,
            "code": i.code,
            "dimension": i.dimension,
            "name_en": i.name_en,
            "name_id": i.name_id,
            "description_en": i.description_en,
            "description_id": i.description_id,
            "scale_type": i.scale_type,
            "min_score": i.min_score,
            "max_score": i.max_score,
            "is_patent_specific": i.is_patent_specific,
            "origin_classification": i.origin_classification,
            "reference_id": i.reference_id,
            "source_locator": i.source_locator,
            "cross_domain_note": i.cross_domain_note,
            "rubric_levels": i.rubric_levels_json,
            "default_provisional_weight": i.default_provisional_weight,
        }
        for i in inds
    ]


@router.get("/revisions/{technology_id}")
def list_assessment_revisions_for_technology(
    technology_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    revs = list(
        db.execute(
            select(AssessmentRevision)
            .where(AssessmentRevision.technology_id == technology_id)
            .order_by(AssessmentRevision.revision_number.desc())
        ).scalars()
    )
    result: List[Dict[str, Any]] = []
    for rev in revs:
        scores = list(
            db.execute(
                select(IndicatorScore)
                .where(IndicatorScore.assessment_revision_id == rev.id)
                .order_by(IndicatorScore.indicator_code.asc())
            ).scalars()
        )
        ev_items = list(
            db.execute(
                select(EvidenceItem).where(EvidenceItem.assessment_revision_id == rev.id)
            ).scalars()
        )
        result.append(
            {
                "id": rev.id,
                "technology_id": rev.technology_id,
                "analysis_run_id": rev.analysis_run_id,
                "parent_revision_id": rev.parent_revision_id,
                "weight_set_id": rev.weight_set_id,
                "revision_number": rev.revision_number,
                "actor_id": rev.actor_id,
                "change_reason": rev.change_reason,
                "previous_values_json": rev.previous_values_json,
                "technology_assessment_score": rev.technology_assessment_score,
                "trl_score": rev.trl_score,
                "trl_exit_criteria_met_json": rev.trl_exit_criteria_met_json,
                "commercialization_readiness_score": rev.commercialization_readiness_score,
                "evidence_completeness_score": rev.evidence_completeness_score,
                "tech_completeness_score": rev.tech_completeness_score,
                "comm_completeness_score": rev.comm_completeness_score,
                "is_provisional": rev.is_provisional,
                "provisional_reasons_json": rev.provisional_reasons_json,
                "applicable_indicator_count": rev.applicable_indicator_count,
                "observed_indicator_count": rev.observed_indicator_count,
                "missing_indicator_count": rev.missing_indicator_count,
                "not_applicable_indicator_count": rev.not_applicable_indicator_count,
                "ip_patent_signals_json": rev.ip_patent_signals_json,
                "market_intelligence_json": rev.market_intelligence_json,
                "commercialization_pathway_json": rev.commercialization_pathway_json,
                "risk_matrix_json": rev.risk_matrix_json,
                "created_at": rev.created_at.isoformat(),
                "indicator_scores": [
                    {
                        "id": s.id,
                        "indicator_code": s.indicator_code,
                        "dimension": s.dimension,
                        "status": s.status,
                        "scale_type": s.scale_type,
                        "raw_score": s.raw_score,
                        "normalized_score": s.normalized_score,
                        "base_weight": s.base_weight,
                        "renormalized_weight": s.renormalized_weight,
                        "rationale_en": s.rationale_en,
                        "rationale_id": s.rationale_id,
                        "expert_review_status": s.expert_review_status,
                        "expert_review_reason": s.expert_review_reason,
                    }
                    for s in scores
                ],
                "evidence_items": [
                    {
                        "id": ev.id,
                        "indicator_score_id": ev.indicator_score_id,
                        "document_id": ev.document_id,
                        "indicator_code": ev.indicator_code,
                        "location_ref": ev.location_ref,
                        "quoted_text": ev.quoted_text,
                        "claim_summary": ev.claim_summary,
                        "resolution_status": ev.resolution_status,
                        "rejection_reason": ev.rejection_reason,
                    }
                    for ev in ev_items
                ],
            }
        )
    return result
