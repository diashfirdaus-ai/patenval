import hashlib
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from app.config import settings
from app.services.valuation import format_idr


REPORT_I18N: Dict[str, Dict[str, str]] = {
    "en": {
        "report_title": "TechVal AI — Scientific Technology Assessment & Economic Valuation Report",
        "draft_watermark": "DRAFT — UNAPPROVED (PROVISIONAL)",
        "approved_badge": "EXPERT APPROVED — REVISION VERIFIED",
        "synthetic_banner": "SYNTHETIC DEMONSTRATION RECORD — FOR SYSTEM VERIFICATION ONLY (NO ACCURACY CLAIMS)",
        "sec_overview": "1. Executive Summary & Four Independent Outputs",
        "sec_provenance": "2. Run Provenance, Consent & Reproducibility Manifest",
        "sec_indicators": "3. Technology Assessment & Commercialization Readiness Rubrics",
        "sec_evidence": "4. Resolved Documentary Evidence & Original Source Quotations",
        "sec_valuation": "5. Deterministic Economic Valuation (IDR) & Financial Assumptions",
        "sec_limitations": "6. Methodological Conventions, Limitations & Scientific References",
        "out_tech": "Output 1 — Technology Assessment (Normalized 0–1 & Native TRL 1–9)",
        "out_comm": "Output 2 — Commercialization Readiness (Normalized 0–1)",
        "out_val": "Output 3 — Economic Valuation Indication (IDR)",
        "out_comp": "Output 4 — Weighted Evidence Completeness",
        "separation_notice": (
            "SCIENTIFIC SEPARATION PRINCIPLE: Technology assessment, commercialization readiness, economic "
            "valuation, and evidence completeness are maintained as four strictly separate outputs. Assessment "
            "and TRL scores are never converted into monetary values or financial discount/tax parameters."
        ),
    },
    "id": {
        "report_title": "TechVal AI — Laporan Penilaian Teknologi Ilmiah & Valuasi Ekonomi",
        "draft_watermark": "DRAF — BELUM DISETUJUI PAKAR (PROVISIONAL)",
        "approved_badge": "DISETUJUI PAKAR — REVISI TERVERIFIKASI",
        "synthetic_banner": "DATA DEMONSTRASI SINTETIS — HANYA UNTUK VERIFIKASI SISTEM (TANPA KLAIM AKURASI)",
        "sec_overview": "1. Ringkasan Eksekutif & Empat Luaran Independen",
        "sec_provenance": "2. Provenans Analisis, Persetujuan & Manifes Reprodusibilitas",
        "sec_indicators": "3. Rubrik Penilaian Teknologi & Kesiapan Komersialisasi",
        "sec_evidence": "4. Bukti Dokumen Terverifikasi & Kutipan Sumber Asli",
        "sec_valuation": "5. Valuasi Ekonomi Deterministik (IDR) & Asumsi Keuangan",
        "sec_limitations": "6. Konvensi Metodologi, Keterbatasan & Referensi Ilmiah",
        "out_tech": "Luaran 1 — Penilaian Teknologi (Normalisasi 0–1 & Skala Asli TRL 1–9)",
        "out_comm": "Luaran 2 — Kesiapan Komersialisasi (Normalisasi 0–1)",
        "out_val": "Luaran 3 — Indikasi Valuasi Ekonomi (IDR)",
        "out_comp": "Luaran 4 — Kelengkapan Bukti Tertimbang",
        "separation_notice": (
            "PRINSIP PEMISAHAN ILMIAH: Penilaian teknologi, kesiapan komersialisasi, valuasi ekonomi, dan "
            "kelengkapan bukti dipertahankan sebagai empat luaran terpisah. Skor penilaian dan TRL tidak pernah "
            "dikonversi menjadi nilai moneter ataupun parameter tingkat diskonto/pajak."
        ),
    },
}


def generate_pdf_report(
    technology: Dict[str, Any],
    revision: Dict[str, Any],
    indicator_scores: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
    valuation_scenarios: List[Dict[str, Any]],
    references: List[Dict[str, Any]],
    provenance: Dict[str, Any],
    expert_review: Optional[Dict[str, Any]],
    language: str = "en",
    output_file_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Generates a reproducible bilingual (EN/ID) PDF report using ReportLab.
    Retains original source quotations (`quoted_text`) and original publication titles (`title`).
    """
    lang = "id" if language == "id" else "en"
    tr = REPORT_I18N[lang]

    is_approved = bool(
        expert_review
        and expert_review.get("status") == "approved"
        and expert_review.get("assessment_revision_id") == revision["id"]
    )
    is_draft = not is_approved
    watermark_text = tr["draft_watermark"] if is_draft else tr["approved_badge"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=tr["report_title"],
        author="TechVal AI Reproducible Report Engine",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TechValTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "TechValH2",
        parent=styles["Heading2"],
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "TechValBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#1E293B"),
    )
    small_style = ParagraphStyle(
        "TechValSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#334155"),
    )
    banner_style = ParagraphStyle(
        "TechValBanner",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#991B1B"),
        backColor=colors.HexColor("#FEF2F2"),
        borderPadding=5,
    )

    story: List[Any] = []

    # Header & Status Banner
    story.append(Paragraph(tr["report_title"], title_style))
    status_color = "#B91C1C" if is_draft else "#15803D"
    story.append(
        Paragraph(
            f"<b>Status:</b> <font color='{status_color}'>{watermark_text}</font> | "
            f"<b>Technology Code:</b> {technology.get('code')} | "
            f"<b>Revision:</b> #{revision.get('revision_number')}",
            body_style,
        )
    )
    story.append(Spacer(1, 4 * mm))

    if technology.get("is_synthetic_demo"):
        story.append(Paragraph(f"<b>{tr['synthetic_banner']}</b>", banner_style))
        story.append(Spacer(1, 3 * mm))

    tech_title = (
        technology.get("title_id") or technology.get("title_en")
        if lang == "id"
        else technology.get("title_en")
    )
    story.append(Paragraph(f"<b>Technology Title:</b> {tech_title}", body_style))
    story.append(Paragraph(f"<b>Domain:</b> {technology.get('domain')} | <b>IP Status:</b> {technology.get('patent_status')}", body_style))
    story.append(Spacer(1, 3 * mm))

    # Section 1: Four Strictly Separate Outputs
    story.append(Paragraph(tr["sec_overview"], h2_style))
    story.append(Paragraph(tr["separation_notice"], small_style))
    story.append(Spacer(1, 2 * mm))

    tech_score_str = (
        f"{revision['technology_assessment_score'] * 100:.1f}% (0–1: {revision['technology_assessment_score']:.4f})"
        if revision.get("technology_assessment_score") is not None
        else "Unavailable (No eligible observations)"
    )
    trl_str = f"TRL {revision['trl_score']} / 9 (Native NASA Scale)" if revision.get("trl_score") else "Missing"
    comm_score_str = (
        f"{revision['commercialization_readiness_score'] * 100:.1f}% (0–1: {revision['commercialization_readiness_score']:.4f})"
        if revision.get("commercialization_readiness_score") is not None
        else "Unavailable (No eligible observations)"
    )
    comp_score_str = f"{revision.get('evidence_completeness_score', 0.0) * 100:.1f}%"

    primary_dcf = next(
        (s for s in valuation_scenarios if s.get("approach") == "dcf" and s.get("scenario_case") == "base"),
        valuation_scenarios[0] if valuation_scenarios else None,
    )
    val_str = (
        f"{format_idr(primary_dcf.get('indicative_value_idr'))} ({primary_dcf.get('scenario_name')})"
        if primary_dcf
        else "Unavailable"
    )

    summary_table_data = [
        [Paragraph(f"<b>{tr['out_tech']}</b>", small_style), Paragraph(f"{tech_score_str} | {trl_str}", small_style)],
        [Paragraph(f"<b>{tr['out_comm']}</b>", small_style), Paragraph(comm_score_str, small_style)],
        [Paragraph(f"<b>{tr['out_val']}</b>", small_style), Paragraph(val_str, small_style)],
        [
            Paragraph(f"<b>{tr['out_comp']}</b>", small_style),
            Paragraph(
                f"{comp_score_str} (Observed: {revision.get('observed_indicator_count', 0)}, "
                f"Missing: {revision.get('missing_indicator_count', 0)}, "
                f"N/A: {revision.get('not_applicable_indicator_count', 0)})",
                small_style,
            ),
        ],
    ]
    t_sum = Table(summary_table_data, colWidths=[75 * mm, 95 * mm])
    t_sum.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_sum)

    if revision.get("is_provisional"):
        reasons = "; ".join(revision.get("provisional_reasons_json", []))
        story.append(Spacer(1, 2 * mm))
        story.append(
            Paragraph(
                f"<b>Provisional Status Notice:</b> Aggregate assessment is labeled PROVISIONAL ({reasons})",
                small_style,
            )
        )

    # Section 2: Provenance
    story.append(Paragraph(tr["sec_provenance"], h2_style))
    prov_rows = [
        ["App Version", str(provenance.get("app_version", settings.APP_VERSION))],
        ["Requested / Actual Provider", f"{provenance.get('requested_provider')} / {provenance.get('actual_provider_returned')}"],
        ["Requested / Actual Model", f"{provenance.get('requested_model')} / {provenance.get('actual_model_returned')}"],
        ["Prompt Hash (SHA-256)", str(provenance.get("prompt_hash", "N/A"))[:48]],
        ["Run Config Hash", str(provenance.get("run_config_hash", "N/A"))[:48]],
        ["Rubric & Weight Version", f"{provenance.get('rubric_version_tag', 'v1.0')} | {provenance.get('weight_set_version', 'provisional_equal_v1')}"],
        ["Document Hashes (SHA-256)", ", ".join(f"{k[:8]}:{v[:12]}..." for k, v in (provenance.get("document_hashes") or {}).items()) or "None"],
    ]
    t_prov = Table(
        [[Paragraph(f"<b>{r[0]}</b>", small_style), Paragraph(str(r[1]), small_style)] for r in prov_rows],
        colWidths=[55 * mm, 115 * mm],
    )
    t_prov.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_prov)

    # Section 3: Indicators Table
    story.append(Paragraph(tr["sec_indicators"], h2_style))
    ind_header = [
        Paragraph("<b>Code</b>", small_style),
        Paragraph("<b>Dimension</b>", small_style),
        Paragraph("<b>Status</b>", small_style),
        Paragraph("<b>Raw / Norm</b>", small_style),
        Paragraph("<b>Weight (Renorm)</b>", small_style),
        Paragraph("<b>Rationale</b>", small_style),
    ]
    ind_table_rows = [ind_header]
    for sc in indicator_scores:
        raw_s = str(sc.get("raw_score")) if sc.get("raw_score") is not None else "-"
        norm_s = f"{sc['normalized_score']:.2f}" if sc.get("normalized_score") is not None else "Native"
        w_str = f"{sc.get('base_weight', 0.0):.2f} ({sc.get('renormalized_weight', 0.0):.2f})"
        rat = sc.get("rationale_id") if lang == "id" and sc.get("rationale_id") else sc.get("rationale_en", "")
        ind_table_rows.append(
            [
                Paragraph(str(sc.get("indicator_code")), small_style),
                Paragraph(str(sc.get("dimension")), small_style),
                Paragraph(str(sc.get("status")), small_style),
                Paragraph(f"{raw_s} / {norm_s}", small_style),
                Paragraph(w_str, small_style),
                Paragraph(rat[:180], small_style),
            ]
        )
    t_ind = Table(ind_table_rows, colWidths=[20 * mm, 32 * mm, 20 * mm, 20 * mm, 24 * mm, 54 * mm])
    t_ind.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    story.append(t_ind)

    # Section 4: Original Source Quotations (Always retained in original language!)
    story.append(Paragraph(tr["sec_evidence"], h2_style))
    if evidence_items:
        for ev in evidence_items:
            story.append(
                Paragraph(
                    f"• <b>[{ev.get('indicator_code')}]</b> Doc: {(ev.get('document_id') or 'N/A')[:8]} | "
                    f"Locator: <b>{ev.get('location_ref')}</b> | Status: <b>{ev.get('resolution_status')}</b><br/>"
                    f"<i>Original Source Quotation:</i> \"{ev.get('quoted_text')}\"",
                    small_style,
                )
            )
            story.append(Spacer(1, 1.5 * mm))
    else:
        story.append(Paragraph("No resolved documentary evidence items recorded.", small_style))

    # Section 5: Deterministic Economic Valuation (IDR)
    story.append(Paragraph(tr["sec_valuation"], h2_style))
    val_rows = [
        [
            Paragraph("<b>Scenario & Approach</b>", small_style),
            Paragraph("<b>Attribution / Risk</b>", small_style),
            Paragraph("<b>Indicative Value (IDR)</b>", small_style),
            Paragraph("<b>WIPO Method Locator</b>", small_style),
        ]
    ]
    for vs in valuation_scenarios:
        attr_info = f"{vs.get('attribution_mode')} ({vs.get('attribution_factor') or 1.0}) | {vs.get('risk_treatment_mode')}"
        val_rows.append(
            [
                Paragraph(f"{vs.get('scenario_name')} [{vs.get('approach')}]", small_style),
                Paragraph(attr_info, small_style),
                Paragraph(f"<b>{format_idr(vs.get('indicative_value_idr'))}</b>", small_style),
                Paragraph(str(vs.get("wipo_reference_locator", "")), small_style),
            ]
        )
    t_val = Table(val_rows, colWidths=[48 * mm, 42 * mm, 38 * mm, 42 * mm])
    t_val.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_val)

    # Section 6: Methodological Conventions, Limitations & Scientific References (Retaining original publication titles!)
    story.append(Paragraph(tr["sec_limitations"], h2_style))
    story.append(
        Paragraph(
            "• Normalization Formula: 1–5 rubrics normalized via (score - 1) / 4; TRL retained on native 1–9 scale.<br/>"
            "• AHP Convention: Consistency Ratio CR <= 0.10 enforced as a methodological convention (Saaty, 1980).<br/>"
            "• Patent Indicators: Forward citations and family size treated strictly as contextual signals (Harhoff et al., 2003).<br/>"
            "• Valuation Separation: Different valuation approaches (DCF, Cost, Comparables, Royalty) are presented separately and never averaged automatically.",
            small_style,
        )
    )
    story.append(Spacer(1, 2 * mm))
    for ref in references:
        story.append(
            Paragraph(
                f"• <b>[{ref.get('code')}]</b> {ref.get('authors')} ({ref.get('publication_year')}). "
                f"<i>{ref.get('title')}</i>. {ref.get('venue_or_publisher')}. "
                f"[Bib: {ref.get('bibliographic_status')} | Method: {ref.get('methodology_verification_status')} | "
                f"Locator: {ref.get('verified_sections_pages') or 'Unverified'}]",
                small_style,
            )
        )

    def _draw_page_overlay(canvas: Any, doc_obj: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(18 * mm, 10 * mm, f"TechVal AI v{settings.APP_VERSION} — {watermark_text}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc_obj.page}")

        if is_draft:
            canvas.setFont("Helvetica-Bold", 34)
            canvas.setFillColor(colors.Color(0.85, 0.15, 0.15, alpha=0.12))
            canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
            canvas.rotate(38)
            canvas.drawCentredString(0, 0, watermark_text)
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_page_overlay, onLaterPages=_draw_page_overlay)
    pdf_bytes = buffer.getvalue()
    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

    if output_file_path:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_bytes(pdf_bytes)

    return {
        "pdf_bytes": pdf_bytes,
        "sha256_hash": sha256_hash,
        "is_draft": is_draft,
        "watermark_text": watermark_text,
        "language": lang,
    }
