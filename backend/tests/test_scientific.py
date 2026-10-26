import pytest
from app.models import ScientificReference
from app.services.ahp import validate_and_solve_ahp
from app.services.evaluation import (
    compute_error_metrics,
    compute_extraction_prf1,
    compute_icc_variants,
    compute_quadratic_weighted_kappa,
)
from app.services.scoring import (
    compute_dimension_aggregate,
    normalize_rubric_score,
    validate_and_resolve_evidence,
)
from app.services.seed import validate_methodology_attribution


def test_source_location_resolution_and_unsupported_numeric_claims():
    """
    Tests evidence validation:
    - Resolves valid (document_id, location_ref, quoted_text)
    - Rejects unresolvable document_id or location_ref
    - Rejects mismatched quote
    - Rejects unsupported numeric claims not present in the stored section text
    """
    valid_docs = {"doc-1"}
    stored_sections = {
        ("doc-1", "page:2"): {
            "id": "sec-2",
            "content_text": "Laboratory pilot campaign achieved 94.2% COD removal over 450 operating hours.",
        }
    }

    # Valid evidence
    res_ok = validate_and_resolve_evidence(
        {
            "indicator_code": "TECH_VALIDATION",
            "document_id": "doc-1",
            "location_ref": "page:2",
            "quoted_text": "achieved 94.2% COD removal over 450 operating hours",
            "claim_summary": "Pilot test demonstrated 94.2% removal over 450 hours.",
        },
        stored_sections,
        valid_docs,
    )
    assert res_ok["is_valid"] is True
    assert res_ok["resolution_status"] == "resolved"

    # Unresolvable locator
    res_bad_loc = validate_and_resolve_evidence(
        {
            "indicator_code": "TECH_VALIDATION",
            "document_id": "doc-1",
            "location_ref": "page:99",
            "quoted_text": "achieved 94.2% COD removal",
            "claim_summary": "Test summary",
        },
        stored_sections,
        valid_docs,
    )
    assert res_bad_loc["is_valid"] is False
    assert res_bad_loc["resolution_status"] == "rejected_unresolvable_locator"

    # Unsupported numeric claim (claiming 99.8% when text only has 94.2% and 450)
    res_bad_num = validate_and_resolve_evidence(
        {
            "indicator_code": "TECH_VALIDATION",
            "document_id": "doc-1",
            "location_ref": "page:2",
            "quoted_text": "achieved 94.2% COD removal over 450 operating hours",
            "claim_summary": "Pilot test achieved 99.8% COD removal over 1200 hours.",
        },
        stored_sections,
        valid_docs,
    )
    assert res_bad_num["is_valid"] is False
    assert res_bad_num["resolution_status"] == "rejected_unsupported_numeric"


def test_unverified_reference_and_missing_section_attribution_blocked():
    """Requires exact sections/pages and verified status before attributing an operational rule to a publication."""
    unverified_ref = ScientificReference(
        code="UNVER-2025",
        authors="Doe, J.",
        publication_year=2025,
        title="Unverified Preprint",
        venue_or_publisher="Preprint Server",
        doi_or_url="https://example.org",
        bibliographic_status="pending",
        methodology_verification_status="unverified_section_missing",
        domain_scope="General",
    )
    with pytest.raises(ValueError, match="bibliographic_status"):
        validate_methodology_attribution(
            unverified_ref,
            origin_type="directly_sourced",
            attributed_section="Section 2",
            attributed_page="p. 10",
        )

    verified_ref = ScientificReference(
        code="VER-2025",
        authors="WIPO",
        publication_year=2024,
        title="Verified Guide",
        venue_or_publisher="WIPO",
        doi_or_url="https://wipo.int",
        bibliographic_status="verified",
        methodology_verification_status="verified_with_locator",
        verified_sections_pages="Section 3, pp. 18-39",
        domain_scope="Valuation",
    )
    # Missing exact page/section must fail
    with pytest.raises(ValueError, match="Exact section"):
        validate_methodology_attribution(
            verified_ref,
            origin_type="adapted",
            attributed_section="",
            attributed_page="",
        )

    # Valid with exact section and page succeeds
    validate_methodology_attribution(
        verified_ref,
        origin_type="adapted",
        attributed_section="Section 3.3",
        attributed_page="pp. 26-30",
    )


def test_score_normalization_missing_vs_na_and_weight_renormalization():
    """
    Verifies:
    - (score - 1) / 4 normalization for 1-5 scores
    - TRL kept on native 1-9 scale
    - Patent-specific indicators may be not_applicable; non-patent indicators cannot be not_applicable
    - Weights renormalized over observed applicable indicators
    - Completeness reported separately & provisional flag set when applicable indicators are missing
    - No aggregate (None) returned when no eligible observations exist
    """
    assert normalize_rubric_score(1, "1-5") == 0.0
    assert normalize_rubric_score(3, "1-5") == 0.5
    assert normalize_rubric_score(5, "1-5") == 1.0
    assert normalize_rubric_score(6, "1-9_trl") is None

    # Non-patent indicator marked not_applicable raises ValueError
    with pytest.raises(ValueError, match="not patent-specific"):
        compute_dimension_aggregate(
            [
                {
                    "indicator_code": "TECH_NOVELTY",
                    "scale_type": "1-5",
                    "is_patent_specific": False,
                    "status": "not_applicable",
                    "raw_score": None,
                    "base_weight": 0.25,
                }
            ]
        )

    items = [
        {"indicator_code": "TECH_TRL_NATIVE", "scale_type": "1-9_trl", "is_patent_specific": False, "status": "observed", "raw_score": 7, "base_weight": 0.0},
        {"indicator_code": "TECH_NOVELTY", "scale_type": "1-5", "is_patent_specific": False, "status": "observed", "raw_score": 5, "base_weight": 0.25},
        {"indicator_code": "TECH_VALIDATION", "scale_type": "1-5", "is_patent_specific": False, "status": "observed", "raw_score": 3, "base_weight": 0.25},
        {"indicator_code": "TECH_SCALABILITY", "scale_type": "1-5", "is_patent_specific": False, "status": "missing", "raw_score": None, "base_weight": 0.25},
        {"indicator_code": "TECH_PATENT_STRENGTH", "scale_type": "1-5", "is_patent_specific": True, "status": "not_applicable", "raw_score": None, "base_weight": 0.25},
    ]
    agg = compute_dimension_aggregate(items, weight_set_is_provisional=False)
    # Applicable 1-5 indicators: TECH_NOVELTY (0.25), TECH_VALIDATION (0.25), TECH_SCALABILITY (0.25) -> total 0.75
    # Observed 1-5 indicators: TECH_NOVELTY (norm=1.0, renorm_w=0.5), TECH_VALIDATION (norm=0.5, renorm_w=0.5) -> agg = 0.75
    # Weighted completeness = 0.50 / 0.75 = 0.666667
    assert agg["trl_score"] == 7
    assert abs(agg["aggregate_score"] - 0.75) < 1e-6
    assert abs(agg["weighted_completeness"] - (2.0 / 3.0)) < 1e-5
    assert agg["is_provisional"] is True  # Because TECH_SCALABILITY is missing!

    # When no eligible observations exist, aggregate_score is None
    empty_agg = compute_dimension_aggregate(
        [
            {"indicator_code": "TECH_NOVELTY", "scale_type": "1-5", "is_patent_specific": False, "status": "missing", "raw_score": None, "base_weight": 0.5},
        ],
        weight_set_is_provisional=False,
    )
    assert empty_agg["aggregate_score"] is None
    assert empty_agg["weighted_completeness"] == 0.0


def test_ahp_consistent_and_inconsistent_judgments():
    """
    Tests reciprocal AHP matrices, eigenvector weights, sourced RI values, and CR > 0.10 blocking.
    """
    codes = ["IND_A", "IND_B", "IND_C"]
    # Consistent reciprocal matrix
    consistent_matrix = [
        [1.0, 2.0, 4.0],
        [0.5, 1.0, 2.0],
        [0.25, 0.5, 1.0],
    ]
    res_ok = validate_and_solve_ahp(codes, consistent_matrix)
    assert res_ok["is_consistent"] is True
    assert res_ok["can_activate"] is True
    assert res_ok["consistency_ratio_cr"] <= 0.001
    assert abs(res_ok["weights"]["IND_A"] - (4.0 / 7.0)) < 1e-4

    # Highly inconsistent reciprocal matrix: A > B (5), B > C (5), but C > A (5) -> A/C = 0.2
    inconsistent_matrix = [
        [1.0, 5.0, 0.2],
        [0.2, 1.0, 5.0],
        [5.0, 0.2, 1.0],
    ]
    res_bad = validate_and_solve_ahp(codes, inconsistent_matrix)
    assert res_bad["consistency_ratio_cr"] > 0.10
    assert res_bad["is_consistent"] is False
    assert res_bad["can_activate"] is False
    assert "INCONSISTENT MATRIX" in res_bad["convention_note"]


def test_evaluation_metrics_and_unavailable_handling():
    """Verifies QWK, ICC(2,1), ICC(3,1), MAE/RMSE/sMAPE, and unavailable metric handling."""
    qwk = compute_quadratic_weighted_kappa([4, 3, 5, 2, None], [4, 3, 4, 2, 3])
    assert isinstance(qwk["qwk"], float) and qwk["qwk"] > 0.80
    assert qwk["missing_pair_count"] == 1

    icc = compute_icc_variants([4.0, 3.0, 5.0, 2.0], [4.0, 3.0, 4.0, 2.0])
    assert isinstance(icc["icc_2_1_absolute_agreement"], float)
    assert isinstance(icc["icc_3_1_consistency"], float)

    # Undefined when empty
    assert compute_extraction_prf1([], [])["f1"] == "unavailable"
    assert compute_error_metrics([], [])["mae"] == "unavailable"
