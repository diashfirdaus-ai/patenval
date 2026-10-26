from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    AnalysisRun,
    AssessmentRevision,
    Document,
    ExpertReview,
    MarketComparable,
    Technology,
    User,
    ValuationScenario,
)
from app.schemas import MarketComparableCreateRequest, TechnologyCreateRequest
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.patent_ops import EPOOPSAdapter
from app.services.valuation import format_idr

router = APIRouter(prefix="/technologies", tags=["technologies"])


def _serialize_technology(db: Session, tech: Technology) -> Dict[str, Any]:
    latest_rev = (
        db.execute(
            select(AssessmentRevision)
            .where(AssessmentRevision.technology_id == tech.id)
            .order_by(AssessmentRevision.revision_number.desc())
        )
        .scalars()
        .first()
    )
    docs_count = len(
        list(
            db.execute(
                select(Document.id).where(
                    Document.technology_id == tech.id, Document.is_deleted.is_(False)
                )
            ).scalars()
        )
    )
    primary_val = None
    latest_review = None
    if latest_rev:
        primary_val = (
            db.execute(
                select(ValuationScenario).where(
                    ValuationScenario.assessment_revision_id == latest_rev.id,
                    ValuationScenario.approach == "dcf",
                    ValuationScenario.scenario_case == "base",
                )
            )
            .scalars()
            .first()
        )
        latest_review = (
            db.execute(
                select(ExpertReview)
                .where(ExpertReview.assessment_revision_id == latest_rev.id)
                .order_by(ExpertReview.created_at.desc())
            )
            .scalars()
            .first()
        )

    return {
        "id": tech.id,
        "code": tech.code,
        "title_en": tech.title_en,
        "title_id": tech.title_id,
        "domain": tech.domain,
        "inventor_organization": tech.inventor_organization,
        "description_en": tech.description_en,
        "description_id": tech.description_id,
        "claimed_trl": tech.claimed_trl,
        "patent_status": tech.patent_status,
        "patent_application_number": tech.patent_Application_number,
        "patent_jurisdiction": tech.patent_jurisdiction,
        "status": tech.status,
        "is_synthetic_demo": tech.is_synthetic_demo,
        "active_document_count": docs_count,
        "created_at": tech.created_at.isoformat(),
        "updated_at": tech.updated_at.isoformat(),
        "four_separate_outputs": {
            "technology_assessment": {
                "normalized_score": latest_rev.technology_assessment_score if latest_rev else None,
                "trl_native_1_to_9": latest_rev.trl_score if latest_rev else tech.claimed_trl,
                "is_provisional": latest_rev.is_provisional if latest_rev else True,
            },
            "commercialization_readiness": {
                "normalized_score": latest_rev.commercialization_readiness_score if latest_rev else None,
                "is_provisional": latest_rev.is_provisional if latest_rev else True,
            },
            "economic_valuation": {
                "currency": "IDR",
                "dcf_base_indicative_idr": primary_val.indicative_value_idr if primary_val else None,
                "dcf_base_formatted": format_idr(primary_val.indicative_value_idr) if primary_val else "Unavailable",
                "score_conversion_prohibited": True,
            },
            "evidence_completeness": {
                "weighted_completeness_score": latest_rev.evidence_completeness_score if latest_rev else 0.0,
                "observed_count": latest_rev.observed_indicator_count if latest_rev else 0,
                "missing_count": latest_rev.missing_indicator_count if latest_rev else 0,
                "not_applicable_count": latest_rev.not_applicable_indicator_count if latest_rev else 0,
            },
        },
        "latest_revision_id": latest_rev.id if latest_rev else None,
        "latest_revision_number": latest_rev.revision_number if latest_rev else 0,
        "expert_review_status": latest_review.status if latest_review else "unapproved_draft",
    }


@router.get("")
def list_technologies(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    techs = list(db.execute(select(Technology).order_by(Technology.created_at.desc())).scalars())
    return [_serialize_technology(db, t) for t in techs]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_technology(
    payload: TechnologyCreateRequest,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    existing = db.execute(select(Technology).where(Technology.code == payload.code)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Technology code '{payload.code}' already exists.")

    tech = Technology(
        code=payload.code,
        title_en=payload.title_en,
        title_id=payload.title_id or payload.title_en,
        domain=payload.domain,
        inventor_organization=payload.inventor_organization,
        description_en=payload.description_en,
        description_id=payload.description_id or payload.description_en,
        claimed_trl=payload.claimed_trl,
        patent_status=payload.patent_status,
        patent_Application_number=payload.patent_application_number,
        patent_jurisdiction=payload.patent_jurisdiction,
        is_synthetic_demo=payload.is_synthetic_demo,
        status="draft",
        created_by=user.id,
    )
    db.add(tech)
    db.flush()
    record_audit_log(
        db=db,
        actor=user,
        action="technology.create",
        entity_type="technology",
        entity_id=tech.id,
        details={"code": tech.code, "title_en": tech.title_en},
    )
    db.commit()
    db.refresh(tech)
    return _serialize_technology(db, tech)


@router.get("/{technology_id}")
def get_technology(
    technology_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tech = db.execute(select(Technology).where(Technology.id == technology_id)).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found.")
    return _serialize_technology(db, tech)


@router.get("/{technology_id}/comparables")
def list_market_comparables(
    technology_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    rows = list(
        db.execute(
            select(MarketComparable)
            .where(MarketComparable.technology_id == technology_id)
            .order_by(MarketComparable.created_at.desc())
        ).scalars()
    )
    return [
        {
            "id": r.id,
            "technology_id": r.technology_id,
            "evidence_category": r.evidence_category,
            "title": r.title,
            "source_citation": r.source_citation,
            "source_url_or_doi": r.source_url_or_doi,
            "jurisdiction": r.jurisdiction,
            "transaction_year": r.transaction_year,
            "unadjusted_value_idr": r.unadjusted_value_idr,
            "royalty_rate_percent": r.royalty_rate_percent,
            "adjustment_factor": r.adjustment_factor,
            "adjusted_indication_idr": (r.unadjusted_value_idr * r.adjustment_factor)
            if r.unadjusted_value_idr is not None
            else None,
            "adjustment_rationale": r.adjustment_rationale,
            "is_credible_verified": r.is_credible_verified,
            "metadata_json": r.metadata_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/{technology_id}/comparables", status_code=status.HTTP_201_CREATED)
def add_market_comparable(
    technology_id: str,
    payload: MarketComparableCreateRequest,
    user: User = Depends(require_roles("admin", "analyst", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tech = db.execute(select(Technology).where(Technology.id == technology_id)).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found.")
    if len(payload.source_citation.strip()) < 10:
        raise HTTPException(status_code=400, detail="Source citation must be at least 10 characters.")

    comp = MarketComparable(
        technology_id=technology_id,
        evidence_category=payload.evidence_category,
        title=payload.title,
        source_citation=payload.source_citation,
        source_url_or_doi=payload.source_url_or_doi,
        jurisdiction=payload.jurisdiction,
        transaction_year=payload.transaction_year,
        unadjusted_value_idr=payload.unadjusted_value_idr,
        royalty_rate_percent=payload.royalty_rate_percent,
        adjustment_factor=payload.adjustment_factor,
        adjustment_rationale=payload.adjustment_rationale,
        is_credible_verified=payload.is_credible_verified,
        metadata_json=payload.metadata_json,
        created_by=user.id,
    )
    db.add(comp)
    db.flush()
    record_audit_log(
        db=db,
        actor=user,
        action="comparable.create",
        entity_type="market_comparable",
        entity_id=comp.id,
        details={"technology_id": technology_id, "category": comp.evidence_category, "title": comp.title},
    )
    db.commit()
    db.refresh(comp)
    return {
        "id": comp.id,
        "title": comp.title,
        "evidence_category": comp.evidence_category,
        "source_citation": comp.source_citation,
        "unadjusted_value_idr": comp.unadjusted_value_idr,
        "adjustment_factor": comp.adjustment_factor,
        "adjusted_indication_idr": (comp.unadjusted_value_idr * comp.adjustment_factor)
        if comp.unadjusted_value_idr is not None
        else None,
    }


@router.get("/{technology_id}/patent-ops-check")
def check_epo_ops_for_technology(
    technology_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tech = db.execute(select(Technology).where(Technology.id == technology_id)).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found.")
    adapter = EPOOPSAdapter()
    return adapter.fetch_patent_record(tech.patent_Application_number or "IDP000089421")
