import hashlib
import io
import math
import re
from typing import Any, Dict, List, Tuple
import pymupdf as fitz  # PyMuPDF
import docx  # python-docx


PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?rules", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+an?\s+unrestricted", re.IGNORECASE),
    re.compile(r"execute\s+(shell|command|tool)", re.IGNORECASE),
    re.compile(r"invent\s+source\s+identifiers", re.IGNORECASE),
]


def detect_prompt_injection_attempts(text: str) -> List[str]:
    """Detects untrusted prompt-injection phrases inside uploaded documents."""
    findings: List[str] = []
    for pat in PROMPT_INJECTION_PATTERNS:
        match = pat.search(text)
        if match:
            findings.append(match.group(0))
    return findings


def compute_text_embedding(text: str, dim: int = 64) -> List[float]:
    """
    Computes a deterministic, normalized `dim`-dimensional feature embedding
    from token bigrams and character trigrams for local vector search in pgvector.
    """
    vec = [0.0] * dim
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    if not tokens:
        return vec
    for i, tok in enumerate(tokens):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign
        if i + 1 < len(tokens):
            bigram = f"{tok}_{tokens[i+1]}"
            hb = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
            vec[hb % dim] += 0.5 if ((hb >> 8) & 1) == 0 else -0.5

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-9:
        vec = [round(v / norm, 6) for v in vec]
    return vec


def parse_pdf_bytes(content: bytes) -> Tuple[List[Dict[str, Any]], bool, str]:
    """
    Parses a PDF using PyMuPDF (`fitz`).
    Preserves exact page locations (`page:1`, `page:2`, ...).
    Flags scanned PDFs requiring OCR rather than inventing text.
    Returns (sections, ocr_required, ocr_warning_message).
    """
    sections: List[Dict[str, Any]] = []
    total_chars = 0
    pages_with_images_only = 0

    with fitz.open(stream=content, filetype="pdf") as pdf_doc:
        page_count = len(pdf_doc)
        for idx, page in enumerate(pdf_doc):
            page_num = idx + 1
            raw_text = page.get_text("text") or ""
            cleaned_text = raw_text.strip()
            char_len = len(cleaned_text)
            total_chars += char_len

            images = page.get_images(full=False)
            if char_len < 15 and len(images) > 0:
                pages_with_images_only += 1

            sections.append(
                {
                    "section_index": page_num,
                    "location_type": "page",
                    "location_ref": f"page:{page_num}",
                    "heading": f"Page {page_num}",
                    "content_text": cleaned_text,
                    "char_count": char_len,
                }
            )

    ocr_required = False
    ocr_warning = ""
    if page_count > 0 and (total_chars < 25 or pages_with_images_only == page_count):
        ocr_required = True
        ocr_warning = (
            f"Scanned PDF detected ({page_count} page(s), {total_chars} extractable characters). "
            "External OCR preprocessing is required; no text was invented."
        )
    elif pages_with_images_only > 0:
        ocr_required = True
        ocr_warning = (
            f"Partial scanned content detected on {pages_with_images_only} of {page_count} page(s). "
            "Image-only pages require OCR."
        )

    return sections, ocr_required, ocr_warning


def parse_docx_bytes(content: bytes) -> Tuple[List[Dict[str, Any]], bool, str]:
    """
    Parses a DOCX file using `python-docx`.
    Preserves exact paragraph locations (`para:1`, `para:2`, ...) and table locations (`table:1`, ...).
    """
    doc = docx.Document(io.BytesIO(content))
    sections: List[Dict[str, Any]] = []
    sec_idx = 0
    para_counter = 0

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if not text:
            continue
        para_counter += 1
        sec_idx += 1
        style_name = para.style.name if para.style else "Paragraph"
        sections.append(
            {
                "section_index": sec_idx,
                "location_type": "paragraph",
                "location_ref": f"para:{para_counter}",
                "heading": f"Paragraph {para_counter} ({style_name})",
                "content_text": text,
                "char_count": len(text),
            }
        )

    table_counter = 0
    for table in doc.tables:
        rows_text: List[str] = []
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(cells):
                rows_text.append(" | ".join(cells))
        joined_table = "\n".join(rows_text).strip()
        if not joined_table:
            continue
        table_counter += 1
        sec_idx += 1
        sections.append(
            {
                "section_index": sec_idx,
                "location_type": "table",
                "location_ref": f"table:{table_counter}",
                "heading": f"Table {table_counter}",
                "content_text": joined_table,
                "char_count": len(joined_table),
            }
        )

    total_chars = sum(s["char_count"] for s in sections)
    ocr_required = total_chars == 0
    ocr_warning = (
        "DOCX contains no extractable paragraphs or tables (may contain embedded images only requiring OCR)."
        if ocr_required
        else ""
    )
    return sections, ocr_required, ocr_warning


def chunk_section_text(location_ref: str, text: str, max_chunk_chars: int = 800) -> List[Dict[str, Any]]:
    """Splits a section's text into chunks while preserving the exact location_ref."""
    cleaned = text.strip()
    if not cleaned:
        return []
    chunks: List[Dict[str, Any]] = []
    start = 0
    idx = 0
    while start < len(cleaned):
        piece = cleaned[start : start + max_chunk_chars]
        idx += 1
        chunks.append(
            {
                "chunk_index": idx,
                "location_ref": location_ref,
                "chunk_text": piece,
                "embedding": compute_text_embedding(piece),
            }
        )
        start += max_chunk_chars
    return chunks
