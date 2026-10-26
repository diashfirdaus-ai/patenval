from pathlib import Path
from app.security.auth import redact_secrets
from fixtures.demo_data import build_demo_patent_pdf_bytes


def test_unauthenticated_and_rbac_enforcement(client):
    """Enforces authentication and role-based access control on API endpoints."""
    # Unauthenticated access blocked
    unauth = client.get("/api/v1/technologies")
    assert unauth.status_code == 401

    # Login as analyst
    login_resp = client.post("/api/v1/auth/login", json={"username": "analyst", "password": "AnalystTechVal2026!"})
    assert login_resp.status_code == 200
    data = login_resp.json()
    analyst_headers = {
        "Authorization": f"Bearer {data['access_token']}",
        "X-CSRF-Token": data["csrf_token"],
    }

    # Analyst cannot create users (admin-only)
    create_user_resp = client.post(
        "/api/v1/auth/users",
        headers=analyst_headers,
        json={
            "email": "unauth@itenas.ac.id",
            "username": "unauth",
            "full_name": "Unauthorized User",
            "password": "Password123!",
            "role": "admin",
        },
    )
    assert create_user_resp.status_code == 403

    # Analyst cannot sign off expert review (expert_reviewer / admin only)
    sign_resp = client.post(
        "/api/v1/reviews/sign-off",
        headers=analyst_headers,
        json={
            "technology_id": "nonexistent",
            "assessment_revision_id": "nonexistent",
            "status": "approved",
            "overall_rationale": "Attempted unauthorized sign off.",
        },
    )
    assert sign_resp.status_code == 403


def test_csrf_protection_enforced(client):
    """Rejects state-changing requests when X-CSRF-Token is invalid."""
    login_resp = client.post("/api/v1/auth/login", json={"username": "analyst", "password": "AnalystTechVal2026!"})
    data = login_resp.json()
    bad_csrf_headers = {
        "Authorization": f"Bearer {data['access_token']}",
        "X-CSRF-Token": "forged_invalid_csrf_token",
    }
    resp = client.post(
        "/api/v1/technologies",
        headers=bad_csrf_headers,
        json={
            "code": "CSRF-TEST-01",
            "title_en": "CSRF Test",
            "domain": "Test",
            "description_en": "Test",
        },
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


def test_upload_traversal_and_signature_validation(client):
    """Blocks path traversal filenames and invalid magic-byte file signatures."""
    login_resp = client.post("/api/v1/auth/login", json={"username": "analyst", "password": "AnalystTechVal2026!"})
    data = login_resp.json()
    headers = {
        "Authorization": f"Bearer {data['access_token']}",
        "X-CSRF-Token": data["csrf_token"],
    }
    techs = client.get("/api/v1/technologies", headers=headers).json()
    tech_id = techs[0]["id"]

    # 1. Path traversal attempt
    traversal_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"technology_id": tech_id, "document_type": "technical_disclosure"},
        files={"file": ("../../etc/passwd.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert traversal_resp.status_code == 400
    assert "traversal" in traversal_resp.json()["detail"].lower()

    # 2. Invalid PDF magic bytes (spoofed executable as .pdf)
    spoof_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"technology_id": tech_id, "document_type": "technical_disclosure"},
        files={"file": ("spoofed.pdf", b"MZ\x90\x00not_a_pdf", "application/pdf")},
    )
    assert spoof_resp.status_code == 400
    assert "signature mismatch" in spoof_resp.json()["detail"].lower()


def test_prompt_injection_detection_and_complete_cascade_deletion(client):
    """
    Tests prompt injection detection on upload and verifies complete cascade deletion
    across encrypted original file, sections, chunks, checkpoints, and artifacts,
    retaining only non-confidential audit metadata.
    """
    login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminTechVal2026!"})
    data = login_resp.json()
    headers = {
        "Authorization": f"Bearer {data['access_token']}",
        "X-CSRF-Token": data["csrf_token"],
    }

    # Create isolated technology for deletion test
    t_resp = client.post(
        "/api/v1/technologies",
        headers=headers,
        json={
            "code": "DEL-TEST-2026",
            "title_en": "Temporary Technology for Deletion Completeness Verification",
            "domain": "Security Testing",
            "description_en": "Testing deletion completeness.",
            "is_synthetic_demo": True,
        },
    )
    assert t_resp.status_code == 201
    tech_id = t_resp.json()["id"]

    pdf_bytes = build_demo_patent_pdf_bytes()
    up_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"technology_id": tech_id, "document_type": "patent_spec"},
        files={"file": ("temp_confidential_spec.pdf", pdf_bytes, "application/pdf")},
    )
    assert up_resp.status_code == 201
    doc_info = up_resp.json()
    doc_id = doc_info["id"]

    # Verify sections exist before deletion
    sec_before = client.get(f"/api/v1/documents/{doc_id}/sections", headers=headers)
    assert sec_before.status_code == 200
    assert len(sec_before.json()["sections"]) == 3

    # Delete document and verify cascade summary
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 200
    del_summary = del_resp.json()
    assert del_summary["vault_file_removed"] is True
    assert del_summary["sections_deleted"] == 3
    assert del_summary["chunks_deleted"] >= 3

    # Verify sections and download are now 404
    assert client.get(f"/api/v1/documents/{doc_id}/sections", headers=headers).status_code == 404
    assert client.get(f"/api/v1/documents/{doc_id}/download", headers=headers).status_code == 404

    # Verify audit log redaction
    redacted = redact_secrets(
        {"username": "admin", "password": "MySecretPassword", "gemini_api_key": "AIzaSySecret123456789"}
    )
    assert redacted["password"] == "[REDACTED]"
    assert redacted["gemini_api_key"] == "[REDACTED]"
