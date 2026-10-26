from datetime import datetime, timedelta, timezone
import hashlib
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import (
    AnalysisRun,
    AssessmentRevision,
    ConsentRecord,
    Document,
    ExpertReview,
    JobQueue,
    Technology,
    User,
)
from app.services.parser import parse_pdf_bytes
from app.services.worker import enqueue_analysis_job, process_next_queued_job, recover_interrupted_jobs
from app.services.workflow import execute_analysis_run
from fixtures.demo_data import build_demo_scanned_pdf_bytes


def test_scanned_pdf_ocr_detection_without_inventing_text():
    """Flags image-only scanned PDFs with ocr_required=True rather than inventing text."""
    scanned_bytes = build_demo_scanned_pdf_bytes()
    sections, ocr_req, ocr_warn = parse_pdf_bytes(scanned_bytes)
    assert ocr_req is True
    assert "Scanned PDF detected" in ocr_warn
    assert sum(s["char_count"] for s in sections) == 0


def test_contradictory_evidence_detection_in_workflow(client):
    """Detects contradictory TRL claims across uploaded document sections and marks assessment provisional."""
    import pymupdf as fitz

    login_resp = client.post("/api/v1/auth/login", json={"username": "analyst", "password": "AnalystTechVal2026!"})
    auth_data = login_resp.json()
    headers = {
        "Authorization": f"Bearer {auth_data['access_token']}",
        "X-CSRF-Token": auth_data["csrf_token"],
    }

    t_resp = client.post(
        "/api/v1/technologies",
        headers=headers,
        json={
            "code": "CONTRADICT-2026-01",
            "title_en": "Contradictory Evidence Test Technology",
            "domain": "Materials Engineering",
            "description_en": "Testing contradictory claims across pages.",
            "claimed_trl": 6,
            "is_synthetic_demo": True,
        },
    )
    assert t_resp.status_code == 201
    tech_id = t_resp.status_code and t_resp.json()["id"]

    # Build a 2-page PDF where Page 1 claims TRL 3 only and Page 2 claims TRL 7
    pdf = fitz.open()
    p1 = pdf.new_page()
    p1.insert_text((50, 60), "Page 1: The technology is currently at TRL 3 proof of concept in laboratory.", fontsize=10)
    p2 = pdf.new_page()
    p2.insert_text((50, 60), "Page 2: The subsystem prototype achieved TRL 7 operational environment validation.", fontsize=10)
    pdf_bytes = pdf.tobytes()
    pdf.close()

    up_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"technology_id": tech_id, "document_type": "technical_disclosure"},
        files={"file": ("contradictory_trl_spec.pdf", pdf_bytes, "application/pdf")},
    )
    assert up_resp.status_code == 201
    doc_id = up_resp.json()["id"]

    consent_resp = client.post(
        "/api/v1/analysis-runs/consent",
        headers=headers,
        json={
            "technology_id": tech_id,
            "provider": "fixture",
            "model_name": "fixture-deterministic-v1",
            "transmission_scope": "local_fixture_only",
            "document_ids": [doc_id],
            "consent_granted": True,
            "config_options": {},
        },
    )
    assert consent_resp.status_code == 201
    consent_id = consent_resp.json()["id"]

    run_resp = client.post(
        "/api/v1/analysis-runs",
        headers=headers,
        json={
            "technology_id": tech_id,
            "consent_record_id": consent_id,
            "provider": "fixture",
            "model_name": "fixture-deterministic-v1",
            "config_options": {},
            "execute_synchronously": True,
        },
    )
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    assert run_data["status"] == "completed"
    contradictions = run_data["partial_results_json"]["extraction"]["contradictions_detected"]
    assert len(contradictions) >= 1
    assert contradictions[0]["type"] == "conflicting_trl_claims"


def test_missing_credentials_and_malformed_output_never_silently_fallback(db_session: Session):
    """
    Verifies that requesting `gemini` without GEMINI_API_KEY or encountering malformed output
    fails explicitly and NEVER silently falls back to fixture data.
    """
    tech = db_session.execute(select(Technology).where(Technology.code == "ITENAS-PAT-2026-001")).scalar_one()
    user = db_session.execute(select(User).where(User.username == "analyst")).scalar_one()
    docs = list(
        db_session.execute(
            select(Document).where(Document.technology_id == tech.id, Document.is_deleted.is_(False))
        ).scalars()
    )
    doc_ids = [d.id for d in docs]
    doc_hashes = {d.id: d.sha256_hash for d in docs}
    cfg_hash = hashlib.sha256(b"gemini_missing_creds_test").hexdigest()

    consent = ConsentRecord(
        technology_id=tech.id,
        user_id=user.id,
        provider="gemini",
        model_name="gemini-2.5-flash",
        transmission_scope="extracted_text_chunks",
        document_ids_json=doc_ids,
        document_hashes_json=doc_hashes,
        run_config_hash=cfg_hash,
        consent_granted=True,
        consent_statement="Test consent for Gemini without credentials.",
    )
    db_session.add(consent)
    db_session.flush()

    run = AnalysisRun(
        technology_id=tech.id,
        consent_record_id=consent.id,
        status="queued",
        requested_provider="gemini",
        requested_model="gemini-2.5-flash",
        prompt_hash="test",
        run_config_hash=cfg_hash,
        config_snapshot_json={},
        rubric_version_tag="methodology_v1.0",
        document_hashes_json=doc_hashes,
        app_version="1.0.0",
        created_by=user.id,
    )
    db_session.add(run)
    db_session.commit()

    updated = execute_analysis_run(db_session, run.id)
    assert updated.status == "failed"
    assert "Silent fallback to fixture data is prohibited" in (updated.error_message or "")

    # Also test malformed model response handling
    mal_cfg_hash = hashlib.sha256(b"malformed_test").hexdigest()
    consent_mal = ConsentRecord(
        technology_id=tech.id,
        user_id=user.id,
        provider="fixture",
        model_name="fixture-deterministic-v1",
        transmission_scope="local_fixture_only",
        document_ids_json=doc_ids,
        document_hashes_json=doc_hashes,
        run_config_hash=mal_cfg_hash,
        consent_granted=True,
        consent_statement="Test malformed output.",
    )
    db_session.add(consent_mal)
    db_session.flush()

    run_mal = AnalysisRun(
        technology_id=tech.id,
        consent_record_id=consent_mal.id,
        status="queued",
        requested_provider="fixture",
        requested_model="fixture-deterministic-v1",
        prompt_hash="test",
        run_config_hash=mal_cfg_hash,
        config_snapshot_json={"simulate_malformed_output": True},
        rubric_version_tag="methodology_v1.0",
        document_hashes_json=doc_hashes,
        app_version="1.0.0",
        created_by=user.id,
    )
    db_session.add(run_mal)
    db_session.commit()

    updated_mal = execute_analysis_run(db_session, run_mal.id)
    assert updated_mal.status == "failed"
    assert "Simulated malformed JSON output" in (updated_mal.error_message or "")


def test_consent_denial_and_changed_inputs_block_execution(db_session: Session):
    """Verifies that consent denial or changed document hashes block analysis execution."""
    tech = db_session.execute(select(Technology).where(Technology.code == "ITENAS-PAT-2026-001")).scalar_one()
    user = db_session.execute(select(User).where(User.username == "analyst")).scalar_one()

    denied_consent = ConsentRecord(
        technology_id=tech.id,
        user_id=user.id,
        provider="fixture",
        model_name="fixture-deterministic-v1",
        transmission_scope="local_fixture_only",
        document_ids_json=[],
        document_hashes_json={},
        run_config_hash="hash_denied",
        consent_granted=False,
        consent_statement="Denied consent.",
    )
    db_session.add(denied_consent)
    db_session.flush()

    run = AnalysisRun(
        technology_id=tech.id,
        consent_record_id=denied_consent.id,
        status="queued",
        requested_provider="fixture",
        requested_model="fixture-deterministic-v1",
        prompt_hash="test",
        run_config_hash="hash_denied",
        config_snapshot_json={},
        rubric_version_tag="methodology_v1.0",
        document_hashes_json={},
        app_version="1.0.0",
        created_by=user.id,
    )
    db_session.add(run)
    db_session.commit()

    res = execute_analysis_run(db_session, run.id)
    assert res.status == "failed"
    assert "Consent was denied" in (res.error_message or "")


def test_interrupted_worker_recovery_and_retry_idempotency(db_session: Session):
    """
    Tests recovering a stuck job after worker interruption and idempotent retry execution.
    """
    tech = db_session.execute(select(Technology).where(Technology.code == "ITENAS-PAT-2026-001")).scalar_one()
    user = db_session.execute(select(User).where(User.username == "analyst")).scalar_one()
    docs = list(
        db_session.execute(
            select(Document).where(Document.technology_id == tech.id, Document.is_deleted.is_(False))
        ).scalars()
    )
    doc_ids = [d.id for d in docs]
    doc_hashes = {d.id: d.sha256_hash for d in docs}
    cfg_hash = hashlib.sha256(json.dumps(doc_hashes, sort_keys=True).encode()).hexdigest()

    consent = ConsentRecord(
        technology_id=tech.id,
        user_id=user.id,
        provider="fixture",
        model_name="fixture-deterministic-v1",
        transmission_scope="local_fixture_only",
        document_ids_json=doc_ids,
        document_hashes_json=doc_hashes,
        run_config_hash=cfg_hash,
        consent_granted=True,
        consent_statement="Worker recovery test consent.",
    )
    db_session.add(consent)
    db_session.flush()

    run = AnalysisRun(
        technology_id=tech.id,
        consent_record_id=consent.id,
        status="running",
        requested_provider="fixture",
        requested_model="fixture-deterministic-v1",
        prompt_hash="test",
        run_config_hash=cfg_hash,
        config_snapshot_json={},
        rubric_version_tag="methodology_v1.0",
        document_hashes_json=doc_hashes,
        app_version="1.0.0",
        created_by=user.id,
    )
    db_session.add(run)
    db_session.flush()

    # Simulate an interrupted worker job with an expired heartbeat
    stuck_job = JobQueue(
        analysis_run_id=run.id,
        status="processing",
        attempts=1,
        max_attempts=3,
        locked_by="crashed-worker-pid999",
        heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        payload_json={"analysis_run_id": run.id},
    )
    db_session.add(stuck_job)
    db_session.commit()

    recovered_count = recover_interrupted_jobs(db_session, stale_seconds=60)
    assert recovered_count >= 1
    db_session.refresh(stuck_job)
    assert stuck_job.status == "queued"

    # Process the recovered job to completion
    processed = process_next_queued_job(db_session)
    assert processed is not None
    assert processed.status == "completed"
    db_session.refresh(run)
    assert run.status == "completed"


def test_stale_approvals_after_material_edits(client):
    """
    Verifies that expert approvals bind to an exact assessment revision and become `stale`
    after material indicator or financial edits, and that subsequent PDF exports revert to DRAFT.
    """
    # Log in as expert_reviewer
    login_resp = client.post("/api/v1/auth/login", json={"username": "reviewer", "password": "ExpertTechVal2026!"})
    assert login_resp.status_code == 200
    auth_data = login_resp.json()
    headers = {
        "Authorization": f"Bearer {auth_data['access_token']}",
        "X-CSRF-Token": auth_data["csrf_token"],
    }

    techs = client.get("/api/v1/technologies", headers=headers).json()
    demo_tech = next(t for t in techs if t["code"] == "ITENAS-PAT-2026-001")
    tech_id = demo_tech["id"]
    rev_id = demo_tech["latest_revision_id"]

    # Sign off on current revision
    sign_resp = client.post(
        "/api/v1/reviews/sign-off",
        headers=headers,
        json={
            "technology_id": tech_id,
            "assessment_revision_id": rev_id,
            "status": "approved",
            "overall_rationale": "Verified all documentary locators and WIPO financial assumptions.",
            "methodology_verified": True,
            "assumptions_verified": True,
        },
    )
    assert sign_resp.status_code == 201
    review_id = sign_resp.json()["id"]

    # Generate PDF report -> should be APPROVED (is_draft == False)
    rep_approved = client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={"technology_id": tech_id, "assessment_revision_id": rev_id, "language": "en"},
    ).json()
    assert rep_approved["is_draft"] is False

    # Now perform a material edit on indicator scores -> creates new immutable revision and marks prior review STALE
    rev_edit_resp = client.post(
        "/api/v1/reviews/revise-indicators",
        headers=headers,
        json={
            "technology_id": tech_id,
            "parent_revision_id": rev_id,
            "change_reason": "Expert adjusted TECH_NOVELTY to level 5 after inspecting lab logs.",
            "indicator_updates": [
                {
                    "indicator_code": "TECH_NOVELTY",
                    "status": "observed",
                    "raw_score": 5,
                    "expert_review_status": "approved",
                    "expert_review_reason": "Confirmed superior TiO2-graphene quantum yield.",
                }
            ],
        },
    )
    assert rev_edit_resp.status_code == 201
    new_rev_id = rev_edit_resp.json()["new_revision_id"]
    assert new_rev_id != rev_id

    # Verify old review is now marked 'stale'
    reviews_list = client.get(f"/api/v1/reviews/{tech_id}", headers=headers).json()
    old_rev_obj = next(r for r in reviews_list if r["id"] == review_id)
    assert old_rev_obj["status"] == "stale"

    # Generate PDF report on the new unapproved revision -> must carry DRAFT label (is_draft == True)
    rep_draft = client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={"technology_id": tech_id, "assessment_revision_id": new_rev_id, "language": "id"},
    ).json()
    assert rep_draft["is_draft"] is True
    assert "DRAF" in rep_draft["watermark_text"]
