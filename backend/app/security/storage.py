from datetime import datetime, timezone
import hashlib
import io
import os
from pathlib import Path
import re
import uuid
import zipfile
from typing import Dict, Any, Tuple
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import (
    AnalysisRun,
    AssessmentRevision,
    Document,
    DocumentChunk,
    DocumentSection,
    EvidenceItem,
    LangGraphCheckpoint,
    ReportSnapshot,
    User,
)
from app.security.auth import record_audit_log


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def get_fernet() -> Fernet:
    return Fernet(settings.get_fernet_key())


def validate_filename_and_signature(filename: str, content: bytes) -> Tuple[str, str, str]:
    """
    Validates upload filename against traversal attacks, enforces size limits,
    and checks magic-byte file signatures for PDF and DOCX.
    Returns (safe_filename, extension, mime_type).
    """
    if not filename or "\x00" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    # Reject path traversal sequences explicitly
    if ".." in filename or "/" in filename or "\\" in filename or ":" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal characters are not permitted in filenames.",
        )

    safe_name = re.sub(r"[^A-Za-z0-9._\- ()\[\]]", "_", os.path.basename(filename)).strip()
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Only .pdf and .docx are accepted.",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File signature mismatch: file does not begin with a valid %PDF- header.",
            )
        return safe_name, ".pdf", "application/pdf"

    if ext == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File signature mismatch: DOCX file does not begin with a valid ZIP header.",
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise ValueError("Missing word/document.xml")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File signature mismatch: archive is not a valid OpenXML DOCX document.",
            )
        return (
            safe_name,
            ".docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")


def store_encrypted_file(content: bytes) -> Tuple[str, str, Path]:
    """
    Encrypts file content using Fernet AES encryption at rest and writes it to the
    vault outside the web root using an opaque UUID storage identifier.
    Returns (opaque_storage_id, sha256_hash, encrypted_path).
    """
    sha256_hash = hashlib.sha256(content).hexdigest()
    opaque_id = f"vault_{uuid.uuid4().hex}"
    encrypted_bytes = get_fernet().encrypt(content)
    vault_file = settings.vault_path / f"{opaque_id}.enc"
    vault_file.write_bytes(encrypted_bytes)
    return opaque_id, sha256_hash, vault_file


def read_decrypted_file(doc: Document) -> bytes:
    if doc.is_deleted or not doc.encrypted_vault_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document original has been deleted.",
        )
    vault_file = Path(doc.encrypted_vault_path)
    if not vault_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encrypted storage file not found on disk.",
        )
    encrypted_bytes = vault_file.read_bytes()
    return get_fernet().decrypt(encrypted_bytes)


def cascade_delete_document(db: Session, doc: Document, actor: User) -> Dict[str, Any]:
    """
    Deletes a document across:
    1. Encrypted original file on disk
    2. Extracted text sections (`document_sections`)
    3. Embeddings & text chunks (`document_chunks`)
    4. Evidence items referencing this document (`evidence_items`)
    5. LangGraph checkpoints for runs of this technology (`langgraph_checkpoints`)
    6. Generated report snapshot PDF files for this technology (`report_snapshots`)
    Retains only minimal non-confidential audit metadata.
    """
    doc_id = doc.id
    tech_id = doc.technology_id
    opaque_id = doc.opaque_storage_id
    file_hash = doc.sha256_hash

    # 1. Remove encrypted original file from disk
    removed_vault_file = False
    if doc.encrypted_vault_path:
        vault_path = Path(doc.encrypted_vault_path)
        if vault_path.exists():
            vault_path.unlink()
            removed_vault_file = True

    # 2. Delete chunks & embeddings
    chunks_deleted = db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    ).rowcount or 0

    # 3. Delete extracted text sections
    sections_deleted = db.execute(
        delete(DocumentSection).where(DocumentSection.document_id == doc_id)
    ).rowcount or 0

    # 4. Delete evidence items linked to this document
    evidence_deleted = db.execute(
        delete(EvidenceItem).where(EvidenceItem.document_id == doc_id)
    ).rowcount or 0

    # 5. Delete LangGraph checkpoints for analysis runs on this technology
    run_ids = list(
        db.execute(
            select(AnalysisRun.id).where(AnalysisRun.technology_id == tech_id)
        ).scalars()
    )
    checkpoints_deleted = 0
    if run_ids:
        checkpoints_deleted = (
            db.execute(
                delete(LangGraphCheckpoint).where(LangGraphCheckpoint.analysis_run_id.in_(run_ids))
            ).rowcount
            or 0
        )
        # Clear any confidential partial_results_json in runs
        for run in db.execute(select(AnalysisRun).where(AnalysisRun.id.in_(run_ids))).scalars():
            run.partial_results_json = {"purged_due_to_document_deletion": True}

    # 6. Delete generated report PDF artifacts on disk and DB rows for this technology
    reports = list(
        db.execute(
            select(ReportSnapshot).where(ReportSnapshot.technology_id == tech_id)
        ).scalars()
    )
    reports_deleted = 0
    for rep in reports:
        rep_path = Path(rep.file_path)
        if rep_path.exists():
            rep_path.unlink()
        db.delete(rep)
        reports_deleted += 1

    # 7. Scrub confidential fields on the Document tombstone record
    doc.original_filename = "[DELETED_DOCUMENT]"
    doc.encrypted_vault_path = None
    doc.page_or_section_count = 0
    doc.extracted_char_count = 0
    doc.ocr_warning_message = None
    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)

    # 8. Record non-confidential minimal audit metadata
    summary = {
        "document_id": doc_id,
        "opaque_storage_id": opaque_id,
        "sha256_hash": file_hash,
        "vault_file_removed": removed_vault_file,
        "sections_deleted": sections_deleted,
        "chunks_deleted": chunks_deleted,
        "evidence_items_deleted": evidence_deleted,
        "checkpoints_deleted": checkpoints_deleted,
        "report_artifacts_deleted": reports_deleted,
    }
    record_audit_log(
        db=db,
        actor=actor,
        action="document.cascade_delete",
        entity_type="document",
        entity_id=doc_id,
        details=summary,
    )
    db.commit()
    return summary
