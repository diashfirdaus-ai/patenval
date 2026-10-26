from pathlib import Path
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import (
    AnalysisRun,
    AssessmentRevision,
    EvidenceItem,
    ExpertReview,
    IndicatorScore,
    ReportSnapshot,
    ScientificReference,
    Technology,
    User,
    ValuationScenario,
    WeightSet,
)
from app.schemas import ReportGenerateRequest
from app.security.auth import get_current_user, record_audit_log
from app.services.pdf_report import generate_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{technology_id}")
def list_report_snapshots(
    technology_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    rows = list(
        db.execute(
            select(ReportSnapshot)
            .where(ReportSnapshot.technology_id == technology_id)
            .order_by(ReportSnapshot.created_at.desc())
        ).scalars()
    )
    return [
        {
            "id": r.id,
            "technology_id": r.technology_id,
            "assessment_revision_id": r.assessment_revision_id,
            "expert_review_id": r.expert_review_id,
            "language": r.language,
            "is_draft": r.is_draft,
            "watermark_text": r.watermark_text,
            "file_sha256": r.file_sha256,
            "provenance_json": r.provenance_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_report_endpoint(
    payload: ReportGenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tech = db.execute(select(Technology).where(Technology.id == payload.technology_id)).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found.")

    if payload.assessment_revision_id:
        rev = db.execute(
            select(AssessmentRevision).where(
                AssessmentRevision.id == payload.assessment_revision_id,
                AssessmentRevision.technology_id == tech.id,
            )
        ).scalar_one_or_none()
    else:
        rev = (
            db.execute(
                select(AssessmentRevision)
                .where(AssessmentRevision.technology_id == tech.id)
                .order_by(AssessmentRevision.revision_number.desc())
            )
            .scalars()
            .first()
        )
    if not rev:
        raise HTTPException(status_code=400, detail="No assessment revision exists for this technology.")

    scores = list(
        db.execute(
            select(IndicatorScore)
            .where(IndicatorScore.assessment_revision_id == rev.id)
            .order_by(IndicatorScore.indicator_code.asc())
        ).scalars()
    )
    evs = list(
        db.execute(
            select(EvidenceItem).where(EvidenceItem.assessment_revision_id == rev.id)
        ).scalars()
    )
    val_scens = list(
        db.execute(
            select(ValuationScenario).where(ValuationScenario.assessment_revision_id == rev.id)
        ).scalars()
    )
    refs = list(
        db.execute(select(ScientificReference).order_by(ScientificReference.code.asc())).scalars()
    )

    # Check if there is an active non-stale approved ExpertReview bound to this exact revision
    active_review = (
        db.execute(
            select(ExpertReview)
            .where(
                ExpertReview.assessment_revision_id == rev.id,
                ExpertReview.status == "approved",
            )
            .order_by(ExpertReview.created_at.desc())
        )
        .scalars()
        .first()
    )

    run = None
    if rev.analysis_run_id:
        run = db.execute(select(AnalysisRun).where(AnalysisRun.id == rev.analysis_run_id)).scalar_one_or_none()

    ws = None
    if rev.weight_set_id:
        ws = db.execute(select(WeightSet).where(WeightSet.id == rev.weight_set_id)).scalar_one_or_none()

    provenance = {
        "app_version": run.app_version if run else settings.APP_VERSION,
        "requested_provider": run.requested_provider if run else "fixture",
        "actual_provider_returned": run.actual_provider_returned if run else "fixture",
        "requested_model": run.requested_model if run else "fixture-deterministic-v1",
        "actual_model_returned": run.actual_model_returned if run else "fixture-deterministic-v1",
        "prompt_hash": run.prompt_hash if run else "N/A",
        "run_config_hash": run.run_config_hash if run else "N/A",
        "rubric_version_tag": run.rubric_version_tag if run else "methodology_v1.0",
        "weight_set_version": ws.version_tag if ws else "provisional_equal_v1",
        "document_hashes": run.document_hashes_json if run else {},
        "revision_number": rev.revision_number,
        "expert_review_status": active_review.status if active_review else "unapproved_draft",
    }

    report_id = str(uuid.uuid4())
    lang = "id" if payload.language == "id" else "en"
    out_file = settings.report_path / f"report_{tech.code}_rev{rev.revision_number}_{lang}_{report_id[:8]}.pdf"

    pdf_out = generate_pdf_report(
        technology={
            "id": tech.id,
            "code": tech.code,
            "title_en": tech.title_en,
            "title_id": tech.title_id,
            "domain": tech.domain,
            "patent_status": tech.patent_status,
            "is_synthetic_demo": tech.is_synthetic_demo,
        },
        revision={
            "id": rev.id,
            "revision_number": rev.revision_number,
            "technology_assessment_score": rev.technology_assessment_score,
            "trl_score": rev.trl_score,
            "commercialization_readiness_score": rev.commercialization_readiness_score,
            "evidence_completeness_score": rev.evidence_completeness_score,
            "is_provisional": rev.is_provisional,
            "provisional_reasons_json": rev.provisional_reasons_json,
            "observed_indicator_count": rev.observed_indicator_count,
            "missing_indicator_count": rev.missing_indicator_count,
            "not_applicable_indicator_count": rev.not_applicable_indicator_count,
        },
        indicator_scores=[
            {
                "indicator_code": s.indicator_code,
                "dimension": s.dimension,
                "status": s.status,
                "raw_score": s.raw_score,
                "normalized_score": s.normalized_score,
                "base_weight": s.base_weight,
                "renormalized_weight": s.renormalized_weight,
                "rationale_en": s.rationale_en,
                "rationale_id": s.rationale_id,
            }
            for s in scores
        ],
        evidence_items=[
            {
                "indicator_code": e.indicator_code,
                "document_id": e.document_id,
                "location_ref": e.location_ref,
                "quoted_text": e.quoted_text,
                "resolution_status": e.resolution_status,
            }
            for e in evs
        ],
        valuation_scenarios=[
            {
                "scenario_name": vs.scenario_name,
                "approach": vs.approach,
                "scenario_case": vs.scenario_case,
                "attribution_mode": vs.attribution_mode,
                "attribution_factor": vs.attribution_factor,
                "risk_treatment_mode": vs.risk_treatment_mode,
                "indicative_value_idr": vs.indicative_value_idr,
                "wipo_reference_locator": vs.wipo_reference_locator,
            }
            for vs in val_scens
        ],
        references=[
            {
                "code": r.code,
                "authors": r.authors,
                "publication_year": r.publication_year,
                "title": r.title,
                "venue_or_publisher": r.venue_or_publisher,
                "bibliographic_status": r.bibliographic_status,
                "methodology_verification_status": r.methodology_verification_status,
                "verified_sections_pages": r.verified_sections_pages,
            }
            for r in refs
        ],
        provenance=provenance,
        expert_review=(
            {
                "id": active_review.id,
                "status": active_review.status,
                "assessment_revision_id": active_review.assessment_revision_id,
            }
            if active_review
            else None
        ),
        language=lang,
        output_file_path=out_file,
    )

    snapshot = ReportSnapshot(
        id=report_id,
        technology_id=tech.id,
        assessment_revision_id=rev.id,
        expert_review_id=active_review.id if active_review else None,
        language=lang,
        is_draft=pdf_out["is_draft"],
        watermark_text=pdf_out["watermark_text"],
        file_path=str(out_file),
        file_sha256=pdf_out["sha256_hash"],
        provenance_json=provenance,
        created_by=user.id,
    )
    db.add(snapshot)
    record_audit_log(
        db=db,
        actor=user,
        action="report.generate",
        entity_type="report_snapshot",
        entity_id=snapshot.id,
        details={
            "language": lang,
            "is_draft": snapshot.is_draft,
            "file_sha256": snapshot.file_sha256,
        },
    )
    db.commit()

    return {
        "id": snapshot.id,
        "technology_id": snapshot.technology_id,
        "assessment_revision_id": snapshot.assessment_revision_id,
        "language": snapshot.language,
        "is_draft": snapshot.is_draft,
        "watermark_text": snapshot.watermark_text,
        "file_sha256": snapshot.file_sha256,
        "provenance": snapshot.provenance_json,
        "created_at": snapshot.created_at.isoformat(),
    }


@router.get("/download/{report_id}")
def download_report_pdf(
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    snap = db.execute(select(ReportSnapshot).where(ReportSnapshot.id == report_id)).scalar_one_or_none()
    if not snap:
        raise HTTPException(status_code=404, detail="Report snapshot not found.")

    path = Path(snap.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing from storage.")

    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )
