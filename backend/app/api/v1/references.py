from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MethodologyConfig, ScientificReference, User
from app.schemas import (
    MethodologyConfigCreateRequest,
    ScientificReferenceCreateRequest,
)
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.seed import validate_methodology_attribution

router = APIRouter(prefix="/references", tags=["references"])


@router.get("")
def list_scientific_references(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    refs = list(
        db.execute(select(ScientificReference).order_by(ScientificReference.code.asc())).scalars()
    )
    return [
        {
            "id": r.id,
            "code": r.code,
            "authors": r.authors,
            "publication_year": r.publication_year,
            "title": r.title,
            "venue_or_publisher": r.venue_or_publisher,
            "doi_or_url": r.doi_or_url,
            "bibliographic_status": r.bibliographic_status,
            "methodology_verification_status": r.methodology_verification_status,
            "verified_sections_pages": r.verified_sections_pages,
            "domain_scope": r.domain_scope,
            "cross_domain_adaptation_notes": r.cross_domain_adaptation_notes,
            "summary_quote": r.summary_quote,
        }
        for r in refs
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_scientific_reference(
    payload: ScientificReferenceCreateRequest,
    user: User = Depends(require_roles("admin", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    existing = db.execute(
        select(ScientificReference).where(ScientificReference.code == payload.code)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Reference code '{payload.code}' already exists.")

    if (
        payload.methodology_verification_status == "verified_with_locator"
        and not (payload.verified_sections_pages or "").strip()
    ):
        raise HTTPException(
            status_code=400,
            detail="verified_sections_pages is required when methodology_verification_status is 'verified_with_locator'.",
        )

    ref = ScientificReference(**payload.model_dump())
    db.add(ref)
    db.flush()
    record_audit_log(
        db=db,
        actor=user,
        action="reference.create",
        entity_type="scientific_reference",
        entity_id=ref.id,
        details={"code": ref.code, "title": ref.title},
    )
    db.commit()
    db.refresh(ref)
    return {"id": ref.id, "code": ref.code, "title": ref.title}


@router.get("/methodology-configs")
def list_methodology_configs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    rows = list(
        db.execute(select(MethodologyConfig).order_by(MethodologyConfig.created_at.desc())).scalars()
    )
    return [
        {
            "id": m.id,
            "version_tag": m.version_tag,
            "name": m.name,
            "reference_id": m.reference_id,
            "origin_type": m.origin_type,
            "empirical_validation_status": m.empirical_validation_status,
            "attributed_section": m.attributed_section,
            "attributed_page": m.attributed_page,
            "normalization_formula": m.normalization_formula,
            "ahp_cr_threshold": m.ahp_cr_threshold,
            "rules_json": m.rules_json,
            "is_active": m.is_active,
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]


@router.post("/methodology-configs", status_code=status.HTTP_201_CREATED)
def create_methodology_config(
    payload: MethodologyConfigCreateRequest,
    user: User = Depends(require_roles("admin", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    ref = None
    if payload.reference_id:
        ref = db.execute(
            select(ScientificReference).where(ScientificReference.id == payload.reference_id)
        ).scalar_one_or_none()
        if not ref:
            raise HTTPException(status_code=404, detail="Referenced publication not found.")

    try:
        validate_methodology_attribution(
            reference=ref,
            origin_type=payload.origin_type,
            attributed_section=payload.attributed_section,
            attributed_page=payload.attributed_page,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    cfg = MethodologyConfig(
        version_tag=payload.version_tag,
        name=payload.name,
        reference_id=payload.reference_id,
        origin_type=payload.origin_type,
        empirical_validation_status=payload.empirical_validation_status,
        attributed_section=payload.attributed_section,
        attributed_page=payload.attributed_page,
        normalization_formula=payload.normalization_formula,
        ahp_cr_threshold=payload.ahp_cr_threshold,
        rules_json=payload.rules_json,
        is_active=True,
    )
    db.add(cfg)
    db.flush()
    record_audit_log(
        db=db,
        actor=user,
        action="methodology_config.create",
        entity_type="methodology_config",
        entity_id=cfg.id,
        details={"version_tag": cfg.version_tag, "origin_type": cfg.origin_type},
    )
    db.commit()
    db.refresh(cfg)
    return {"id": cfg.id, "version_tag": cfg.version_tag, "origin_type": cfg.origin_type}
