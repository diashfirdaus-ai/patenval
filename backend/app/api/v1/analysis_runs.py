import asyncio
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from app.config import settings
from app.database import SessionLocal, get_db
from app.models import (
    AgentExecution,
    AnalysisRun,
    ConsentRecord,
    Document,
    JobQueue,
    LangGraphCheckpoint,
    MethodologyConfig,
    Technology,
    User,
    WeightSet,
)
from app.schemas import (
    AnalysisRunCreateRequest,
    ConsentGrantRequest,
    ConsentPreviewRequest,
)
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.worker import enqueue_analysis_job, process_next_queued_job

router = APIRouter(prefix="/analysis-runs", tags=["analysis_runs"])


def _compute_run_config_hash(
    provider: str,
    model_name: str,
    transmission_scope: str,
    doc_hashes: Dict[str, str],
    config_options: Dict[str, Any],
) -> str:
    payload = {
        "provider": provider,
        "model_name": model_name,
        "transmission_scope": transmission_scope,
        "doc_hashes": doc_hashes,
        "config_options": config_options,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _serialize_run(db: Session, run: AnalysisRun) -> Dict[str, Any]:
    execs = list(
        db.execute(
            select(AgentExecution)
            .where(AgentExecution.analysis_run_id == run.id)
            .order_by(AgentExecution.created_at.asc())
        ).scalars()
    )
    checkpoints = list(
        db.execute(
            select(LangGraphCheckpoint)
            .where(LangGraphCheckpoint.analysis_run_id == run.id)
            .order_by(LangGraphCheckpoint.step_index.asc())
        ).scalars()
    )
    return {
        "id": run.id,
        "technology_id": run.technology_id,
        "consent_record_id": run.consent_record_id,
        "status": run.status,
        "current_node": run.current_node,
        "progress_percent": run.progress_percent,
        "requested_provider": run.requested_provider,
        "requested_model": run.requested_model,
        "actual_provider_returned": run.actual_provider_returned,
        "actual_model_returned": run.actual_model_returned,
        "prompt_hash": run.prompt_hash,
        "run_config_hash": run.run_config_hash,
        "config_snapshot_json": run.config_snapshot_json,
        "rubric_version_tag": run.rubric_version_tag,
        "document_hashes_json": run.document_hashes_json,
        "app_version": run.app_version,
        "retry_count": run.retry_count,
        "max_retries": run.max_retries,
        "cancel_requested": run.cancel_requested,
        "error_message": run.error_message,
        "partial_results_json": run.partial_results_json,
        "rejected_claims_json": run.rejected_claims_json,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
        "agent_executions": [
            {
                "id": e.id,
                "agent_name": e.agent_name,
                "status": e.status,
                "provider_used": e.provider_used,
                "model_used": e.model_used,
                "prompt_hash": e.prompt_hash,
                "latency_ms": e.latency_ms,
                "output_summary": e.output_summary_json,
            }
            for e in execs
        ],
        "checkpoints": [
            {
                "step_index": c.step_index,
                "node_name": c.node_name,
                "created_at": c.created_at.isoformat(),
            }
            for c in checkpoints
        ],
    }


@router.post("/consent-preview")
def preview_consent_scope(
    payload: ConsentPreviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Before external transmission, displays the exact provider, model, selected documents,
    SHA-256 hashes, character counts, and transmission scope.
    """
    docs = list(
        db.execute(
            select(Document).where(
                Document.technology_id == payload.technology_id,
                Document.id.in_(payload.document_ids),
                Document.is_deleted.is_(False),
            )
        ).scalars()
    )
    if len(docs) != len(payload.document_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more selected documents do not exist or have been deleted.",
        )

    doc_hashes = {d.id: d.sha256_hash for d in docs}
    run_config_hash = _compute_run_config_hash(
        provider=payload.provider,
        model_name=payload.model_name,
        transmission_scope=payload.transmission_scope,
        doc_hashes=doc_hashes,
        config_options=payload.config_options,
    )

    is_external = payload.provider in ("gemini", "openai_compatible")
    return {
        "technology_id": payload.technology_id,
        "provider": payload.provider,
        "model_name": payload.model_name,
        "is_external_transmission": is_external,
        "transmission_scope": payload.transmission_scope,
        "selected_documents": [
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "sha256_hash": d.sha256_hash,
                "extracted_char_count": d.extracted_char_count,
                "ocr_required": d.ocr_required,
            }
            for d in docs
        ],
        "document_hashes": doc_hashes,
        "run_config_hash": run_config_hash,
        "consent_notice_en": (
            f"You are authorizing transmission of extracted text from {len(docs)} document(s) "
            f"(scope: {payload.transmission_scope}) to provider '{payload.provider}' (model: '{payload.model_name}'). "
            "This consent is cryptographically bound to the exact SHA-256 document hashes and run configuration."
        ),
        "consent_notice_id": (
            f"Anda memberikan persetujuan eksplisit pengiriman teks dari {len(docs)} dokumen "
            f"(cakupan: {payload.transmission_scope}) ke penyedia '{payload.provider}' (model: '{payload.model_name}'). "
            "Persetujuan ini terikat secara kriptografis pada hash SHA-256 dokumen dan konfigurasi analisis."
        ),
    }


@router.post("/consent", status_code=status.HTTP_201_CREATED)
def grant_or_deny_consent(
    payload: ConsentGrantRequest,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    docs = list(
        db.execute(
            select(Document).where(
                Document.technology_id == payload.technology_id,
                Document.id.in_(payload.document_ids),
                Document.is_deleted.is_(False),
            )
        ).scalars()
    )
    if len(docs) != len(payload.document_ids):
        raise HTTPException(status_code=400, detail="Selected documents are invalid or deleted.")

    doc_hashes = {d.id: d.sha256_hash for d in docs}
    run_config_hash = _compute_run_config_hash(
        provider=payload.provider,
        model_name=payload.model_name,
        transmission_scope=payload.transmission_scope,
        doc_hashes=doc_hashes,
        config_options=payload.config_options,
    )

    statement = (
        f"User {user.username} {'GRANTED' if payload.consent_granted else 'DENIED'} consent for "
        f"provider={payload.provider}, model={payload.model_name}, scope={payload.transmission_scope}, "
        f"run_config_hash={run_config_hash}"
    )

    rec = ConsentRecord(
        technology_id=payload.technology_id,
        user_id=user.id,
        provider=payload.provider,
        model_name=payload.model_name,
        transmission_scope=payload.transmission_scope,
        document_ids_json=payload.document_ids,
        document_hashes_json=doc_hashes,
        run_config_hash=run_config_hash,
        consent_granted=payload.consent_granted,
        consent_statement=statement,
    )
    db.add(rec)
    db.flush()

    record_audit_log(
        db=db,
        actor=user,
        action="consent.granted" if payload.consent_granted else "consent.denied",
        entity_type="consent_record",
        entity_id=rec.id,
        details={
            "provider": payload.provider,
            "model_name": payload.model_name,
            "document_hashes": doc_hashes,
            "run_config_hash": run_config_hash,
            "consent_granted": payload.consent_granted,
        },
    )
    db.commit()
    db.refresh(rec)

    return {
        "id": rec.id,
        "consent_granted": rec.consent_granted,
        "provider": rec.provider,
        "model_name": rec.model_name,
        "transmission_scope": rec.transmission_scope,
        "document_hashes": rec.document_hashes_json,
        "run_config_hash": rec.run_config_hash,
        "created_at": rec.created_at.isoformat(),
    }


@router.get("")
def list_analysis_runs(
    technology_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    stmt = select(AnalysisRun).order_by(AnalysisRun.created_at.desc())
    if technology_id:
        stmt = stmt.where(AnalysisRun.technology_id == technology_id)
    runs = list(db.execute(stmt.limit(50)).scalars())
    return [_serialize_run(db, r) for r in runs]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_analysis_run(
    payload: AnalysisRunCreateRequest,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Creates an AnalysisRun after verifying explicit consent bound to document hashes and
    run configuration. Returns the run identifier immediately and enqueues the job in the
    PostgreSQL-backed job queue.
    """
    tech = db.execute(select(Technology).where(Technology.id == payload.technology_id)).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found.")

    consent = db.execute(
        select(ConsentRecord).where(ConsentRecord.id == payload.consent_record_id)
    ).scalar_one_or_none()
    if not consent or consent.technology_id != payload.technology_id:
        raise HTTPException(status_code=400, detail="Valid consent record for this technology is required.")

    if not consent.consent_granted:
        raise HTTPException(
            status_code=403,
            detail="Consent was explicitly denied for this transmission. Analysis run cannot be started.",
        )

    if consent.provider != payload.provider or consent.model_name != payload.model_name:
        raise HTTPException(
            status_code=400,
            detail="Provider or model changed after consent was granted; renewed consent is required.",
        )

    docs = list(
        db.execute(
            select(Document).where(
                Document.technology_id == payload.technology_id,
                Document.id.in_(consent.document_ids_json or []),
                Document.is_deleted.is_(False),
            )
        ).scalars()
    )
    current_hashes = {d.id: d.sha256_hash for d in docs}
    if current_hashes != (consent.document_hashes_json or {}):
        raise HTTPException(
            status_code=409,
            detail="Document hashes or selection changed after consent was granted; renewed consent is required.",
        )

    expected_cfg_hash = _compute_run_config_hash(
        provider=payload.provider,
        model_name=payload.model_name,
        transmission_scope=consent.transmission_scope,
        doc_hashes=current_hashes,
        config_options=payload.config_options,
    )
    if expected_cfg_hash != consent.run_config_hash:
        raise HTTPException(
            status_code=409,
            detail="Run configuration changed after consent was granted; renewed consent is required.",
        )

    m_cfg = db.execute(select(MethodologyConfig).where(MethodologyConfig.is_active.is_(True))).scalars().first()
    ws = None
    if payload.weight_set_id:
        ws = db.execute(select(WeightSet).where(WeightSet.id == payload.weight_set_id)).scalar_one_or_none()
    if not ws:
        ws = db.execute(select(WeightSet).where(WeightSet.is_active.is_(True))).scalars().first()

    run = AnalysisRun(
        technology_id=payload.technology_id,
        consent_record_id=consent.id,
        methodology_config_id=m_cfg.id if m_cfg else None,
        weight_set_id=ws.id if ws else None,
        status="queued",
        current_node="queued",
        progress_percent=0,
        requested_provider=payload.provider,
        requested_model=payload.model_name,
        prompt_hash="pending_execution",
        run_config_hash=expected_cfg_hash,
        config_snapshot_json=payload.config_options,
        rubric_version_tag=m_cfg.version_tag if m_cfg else "methodology_v1.0",
        document_hashes_json=current_hashes,
        app_version=settings.APP_VERSION,
        created_by=user.id,
    )
    db.add(run)
    db.flush()

    enqueue_analysis_job(db, run.id, max_attempts=3)
    record_audit_log(
        db=db,
        actor=user,
        action="analysis_run.create",
        entity_type="analysis_run",
        entity_id=run.id,
        details={
            "technology_id": run.technology_id,
            "requested_provider": run.requested_provider,
            "requested_model": run.requested_model,
            "run_config_hash": run.run_config_hash,
        },
    )
    db.commit()

    if payload.execute_synchronously:
        process_next_queued_job(db)
        db.refresh(run)

    return _serialize_run(db, run)


@router.get("/{run_id}")
def get_analysis_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    run = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
    return _serialize_run(db, run)


@router.get("/{run_id}/events")
async def stream_analysis_run_events(
    run_id: str,
    user: User = Depends(get_current_user),
) -> EventSourceResponse:
    """
    Exposes real-time analysis run progress via Server-Sent Events (SSE).
    """

    async def event_generator():
        for _ in range(120):
            with SessionLocal() as db:
                run = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one_or_none()
                if not run:
                    yield {"event": "error", "data": json.dumps({"detail": "Run not found"})}
                    break
                payload = _serialize_run(db, run)
                yield {"event": "progress", "data": json.dumps(payload)}
                if run.status in ("completed", "failed", "cancelled"):
                    break
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.post("/{run_id}/cancel")
def cancel_analysis_run(
    run_id: str,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    run = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    run.cancel_requested = True
    if run.status in ("queued", "running"):
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc)

    jobs = list(db.execute(select(JobQueue).where(JobQueue.analysis_run_id == run_id)).scalars())
    for j in jobs:
        if j.status in ("queued", "processing"):
            j.status = "cancelled"

    record_audit_log(
        db=db,
        actor=user,
        action="analysis_run.cancel",
        entity_type="analysis_run",
        entity_id=run.id,
    )
    db.commit()
    db.refresh(run)
    return _serialize_run(db, run)


@router.post("/{run_id}/retry")
def retry_analysis_run(
    run_id: str,
    execute_synchronously: bool = False,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    run = db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    if run.retry_count >= run.max_retries:
        raise HTTPException(
            status_code=400,
            detail=f"Bounded retry limit reached ({run.retry_count}/{run.max_retries}).",
        )

    run.status = "queued"
    run.cancel_requested = False
    run.error_message = None
    run.retry_count += 1
    db.flush()

    enqueue_analysis_job(db, run.id, max_attempts=3)
    record_audit_log(
        db=db,
        actor=user,
        action="analysis_run.retry",
        entity_type="analysis_run",
        entity_id=run.id,
        details={"retry_count": run.retry_count},
    )
    db.commit()

    if execute_synchronously:
        process_next_queued_job(db)
        db.refresh(run)

    return _serialize_run(db, run)
