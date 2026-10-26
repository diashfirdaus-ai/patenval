from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, DocumentChunk, DocumentSection, Technology, User
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.security.storage import (
    cascade_delete_document,
    read_decrypted_file,
    store_encrypted_file,
    validate_filename_and_signature,
)
from app.services.parser import (
    chunk_section_text,
    detect_prompt_injection_attempts,
    parse_docx_bytes,
    parse_pdf_bytes,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(
    technology_id: Optional[str] = None,
    include_deleted: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if technology_id:
        stmt = stmt.where(Document.technology_id == technology_id)
    if not include_deleted:
        stmt = stmt.where(Document.is_deleted.is_(False))
    docs = list(db.execute(stmt).scalars())
    return [
        {
            "id": d.id,
            "technology_id": d.technology_id,
            "opaque_storage_id": d.opaque_storage_id,
            "original_filename": d.original_filename,
            "document_type": d.document_type,
            "mime_type": d.mime_type,
            "file_extension": d.file_extension,
            "file_size_bytes": d.file_size_bytes,
            "sha256_hash": d.sha256_hash,
            "signature_valid": d.signature_valid,
            "encrypted_at_rest": d.encrypted_vault_path is not None,
            "ocr_required": d.ocr_required,
            "ocr_warning_message": d.ocr_warning_message,
            "page_or_section_count": d.page_or_section_count,
            "extracted_char_count": d.extracted_char_count,
            "is_deleted": d.is_deleted,
            "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    technology_id: str = Form(...),
    document_type: str = Form("technical_disclosure"),
    file: UploadFile = File(...),
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tech = db.execute(select(Technology).where(Technology.id == technology_id)).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found.")

    content = await file.read()
    safe_name, ext, mime_type = validate_filename_and_signature(file.filename or "", content)

    if ext == ".pdf":
        sections, ocr_req, ocr_warn = parse_pdf_bytes(content)
    else:
        sections, ocr_req, ocr_warn = parse_docx_bytes(content)

    opaque_id, sha256_hash, vault_path = store_encrypted_file(content)

    doc = Document(
        technology_id=technology_id,
        opaque_storage_id=opaque_id,
        original_filename=safe_name,
        document_type=document_type,
        mime_type=mime_type,
        file_extension=ext,
        file_size_bytes=len(content),
        sha256_hash=sha256_hash,
        encrypted_vault_path=str(vault_path),
        signature_valid=True,
        ocr_required=ocr_req,
        ocr_warning_message=ocr_warn or None,
        page_or_section_count=len(sections),
        extracted_char_count=sum(s["char_count"] for s in sections),
        uploaded_by=user.id,
    )
    db.add(doc)
    db.flush()

    injection_alerts: List[str] = []
    for sec in sections:
        inj = detect_prompt_injection_attempts(sec["content_text"])
        if inj:
            injection_alerts.extend(inj)
        sec_row = DocumentSection(document_id=doc.id, **sec)
        db.add(sec_row)
        db.flush()
        for ch in chunk_section_text(sec["location_ref"], sec["content_text"]):
            db.add(DocumentChunk(document_id=doc.id, section_id=sec_row.id, **ch))

    record_audit_log(
        db=db,
        actor=user,
        action="document.upload",
        entity_type="document",
        entity_id=doc.id,
        details={
            "technology_id": technology_id,
            "opaque_storage_id": opaque_id,
            "sha256_hash": sha256_hash,
            "ocr_required": ocr_req,
            "injection_alerts_detected": injection_alerts,
        },
    )
    db.commit()
    db.refresh(doc)

    return {
        "id": doc.id,
        "technology_id": doc.technology_id,
        "opaque_storage_id": doc.opaque_storage_id,
        "original_filename": doc.original_filename,
        "document_type": doc.document_type,
        "sha256_hash": doc.sha256_hash,
        "file_size_bytes": doc.file_size_bytes,
        "ocr_required": doc.ocr_required,
        "ocr_warning_message": doc.ocr_warning_message,
        "page_or_section_count": doc.page_or_section_count,
        "extracted_char_count": doc.extracted_char_count,
        "prompt_injection_alerts": injection_alerts,
    }


@router.get("/{document_id}/sections")
def get_document_sections(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    doc = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found or deleted.")
    sections = list(
        db.execute(
            select(DocumentSection)
            .where(DocumentSection.document_id == document_id)
            .order_by(DocumentSection.section_index.asc())
        ).scalars()
    )
    return {
        "document": {
            "id": doc.id,
            "original_filename": doc.original_filename,
            "sha256_hash": doc.sha256_hash,
            "ocr_required": doc.ocr_required,
            "ocr_warning_message": doc.ocr_warning_message,
        },
        "sections": [
            {
                "id": s.id,
                "section_index": s.section_index,
                "location_type": s.location_type,
                "location_ref": s.location_ref,
                "heading": s.heading,
                "content_text": s.content_text,
                "char_count": s.char_count,
            }
            for s in sections
        ],
    }


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    user: User = Depends(require_roles("admin", "analyst", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Response:
    doc = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found or deleted.")

    decrypted_bytes = read_decrypted_file(doc)
    record_audit_log(
        db=db,
        actor=user,
        action="document.download",
        entity_type="document",
        entity_id=doc.id,
        details={"opaque_storage_id": doc.opaque_storage_id},
    )
    db.commit()
    return Response(
        content=decrypted_bytes,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.delete("/{document_id}")
def delete_document_endpoint(
    document_id: str,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    doc = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.is_deleted:
        raise HTTPException(status_code=400, detail="Document is already deleted.")

    return cascade_delete_document(db, doc, user)
