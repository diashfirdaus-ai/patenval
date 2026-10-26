import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_rubric_score(raw_score: Optional[int], scale_type: str = "1-5") -> Optional[float]:
    """
    Normalizes a 1-5 rubric score using `(score - 1) / 4`.
    Keeps TRL on its native 1-9 scale (returns None for normalized_score so TRL is never conflated with 0..1).
    """
    if raw_score is None:
        return None
    if scale_type == "1-9_trl":
        if not (1 <= int(raw_score) <= 9):
            raise ValueError(f"TRL score must be on its native 1-9 scale, got {raw_score}")
        return None
    if scale_type == "1-5":
        if not (1 <= int(raw_score) <= 5):
            raise ValueError(f"Rubric 1-5 score must be between 1 and 5, got {raw_score}")
        return round((float(raw_score) - 1.0) / 4.0, 6)
    raise ValueError(f"Unsupported scale_type: {scale_type}")


def compute_dimension_aggregate(
    indicator_items: List[Dict[str, Any]],
    weight_set_is_provisional: bool = True,
) -> Dict[str, Any]:
    """
    Computes the normalized aggregate score and weighted completeness for a single dimension
    (`technology_assessment` or `commercialization_readiness`).

    Rules:
    - TRL (`1-9_trl`) is reported on its native 1-9 scale and not folded into 1-5 normalized averages.
    - Patent-specific indicators may be `not_applicable` (excluded from denominator of applicable weight).
    - Missing information remains `missing` (included in applicable weight denominator for completeness,
      excluded from observed weight sum, and causes the aggregate to be labeled provisional).
    - Renormalizes weights over observed applicable indicators.
    - Returns `aggregate_score = None` when no eligible observations exist.
    """
    applicable_items: List[Dict[str, Any]] = []
    observed_items: List[Dict[str, Any]] = []
    missing_codes: List[str] = []
    na_codes: List[str] = []
    trl_score: Optional[int] = None

    for item in indicator_items:
        code = item["indicator_code"]
        scale_type = item.get("scale_type", "1-5")
        status = item.get("status", "missing")  # observed | missing | not_applicable
        is_patent_specific = bool(item.get("is_patent_specific", False))
        raw_score = item.get("raw_score")

        if status == "not_applicable" and not is_patent_specific:
            raise ValueError(
                f"Indicator '{code}' is not patent-specific and cannot be marked 'not_applicable'; "
                "missing information must remain 'missing'."
            )

        if scale_type == "1-9_trl":
            if status == "observed" and raw_score is not None:
                if not (1 <= int(raw_score) <= 9):
                    raise ValueError(f"TRL must be between 1 and 9, got {raw_score}")
                trl_score = int(raw_score)
            elif status == "missing":
                missing_codes.append(code)
            continue

        if status == "not_applicable":
            na_codes.append(code)
            item["normalized_score"] = None
            item["renormalized_weight"] = 0.0
            continue

        applicable_items.append(item)
        if status == "observed" and raw_score is not None:
            item["normalized_score"] = normalize_rubric_score(int(raw_score), scale_type="1-5")
            observed_items.append(item)
        else:
            item["status"] = "missing"
            item["normalized_score"] = None
            item["renormalized_weight"] = 0.0
            missing_codes.append(code)

    total_applicable_weight = sum(float(i.get("base_weight", 0.0)) for i in applicable_items)
    total_observed_weight = sum(float(i.get("base_weight", 0.0)) for i in observed_items)

    if total_applicable_weight > 0:
        weighted_completeness = round(total_observed_weight / total_applicable_weight, 6)
    else:
        weighted_completeness = 0.0

    provisional_reasons: List[str] = []
    if weight_set_is_provisional:
        provisional_reasons.append("Provisional equal weighting set is active.")
    if len(missing_codes) > 0:
        provisional_reasons.append(
            f"Missing applicable indicator(s): {', '.join(missing_codes)}."
        )

    if len(observed_items) == 0 or total_observed_weight <= 0:
        for item in observed_items:
            item["renormalized_weight"] = 0.0
        provisional_reasons.append("No eligible observed indicators available.")
        return {
            "aggregate_score": None,
            "trl_score": trl_score,
            "weighted_completeness": weighted_completeness,
            "is_provisional": True,
            "provisional_reasons": provisional_reasons,
            "applicable_count": len(applicable_items),
            "observed_count": 0,
            "missing_count": len(missing_codes),
            "not_applicable_count": len(na_codes),
            "items": indicator_items,
        }

    aggregate = 0.0
    for item in observed_items:
        renorm_w = float(item.get("base_weight", 0.0)) / total_observed_weight
        item["renormalized_weight"] = round(renorm_w, 6)
        aggregate += renorm_w * float(item["normalized_score"])

    return {
        "aggregate_score": round(aggregate, 6),
        "trl_score": trl_score,
        "weighted_completeness": weighted_completeness,
        "is_provisional": len(provisional_reasons) > 0,
        "provisional_reasons": provisional_reasons,
        "applicable_count": len(applicable_items),
        "observed_count": len(observed_items),
        "missing_count": len(missing_codes),
        "not_applicable_count": len(na_codes),
        "items": indicator_items,
    }


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()


def _extract_numeric_tokens(s: str) -> List[str]:
    # Extract distinct numbers (e.g. percentages, decimals, quantities >= 2 digits or with decimals)
    raw_nums = re.findall(r"\b\d+(?:\.\d+)?%?\b", s)
    # Ignore single-digit rubric levels 1..9 unless percentage
    return [n for n in raw_nums if len(n) >= 2 or "." in n or "%" in n]


def validate_and_resolve_evidence(
    candidate_evidence: Dict[str, Any],
    stored_sections_by_doc_and_loc: Dict[Tuple[str, str], Dict[str, Any]],
    valid_doc_ids: set,
) -> Dict[str, Any]:
    """
    Validates a candidate evidence link against stored document sections.
    Accepts evidence links ONLY when:
    1. `document_id` exists in `valid_doc_ids`
    2. `(document_id, location_ref)` exists in `stored_sections_by_doc_and_loc`
    3. `quoted_text` is non-empty and resolves as a substring of the stored section content
    4. Any specific numeric claims in `claim_summary` that purport to quote metrics from the
       evidence are supported by numbers present in the stored section text.
    """
    doc_id = str(candidate_evidence.get("document_id") or "").strip()
    loc_ref = str(candidate_evidence.get("location_ref") or "").strip()
    quoted = str(candidate_evidence.get("quoted_text") or "").strip()
    claim = str(candidate_evidence.get("claim_summary") or "").strip()
    indicator_code = str(candidate_evidence.get("indicator_code") or "GENERAL").strip()

    if doc_id not in valid_doc_ids:
        return {
            "is_valid": False,
            "resolution_status": "rejected_unresolvable_locator",
            "rejection_reason": f"Document ID '{doc_id}' does not exist in the technology vault.",
            "section_id": None,
            "indicator_code": indicator_code,
            "document_id": None,
            "location_ref": loc_ref,
            "quoted_text": quoted,
            "claim_summary": claim,
        }

    section = stored_sections_by_doc_and_loc.get((doc_id, loc_ref))
    if not section:
        return {
            "is_valid": False,
            "resolution_status": "rejected_unresolvable_locator",
            "rejection_reason": f"Location '{loc_ref}' was not found in document '{doc_id}'.",
            "section_id": None,
            "indicator_code": indicator_code,
            "document_id": doc_id,
            "location_ref": loc_ref,
            "quoted_text": quoted,
            "claim_summary": claim,
        }

    stored_text = section.get("content_text", "")
    if not quoted or len(quoted) < 5:
        return {
            "is_valid": False,
            "resolution_status": "rejected_quote_mismatch",
            "rejection_reason": "Supporting quotation is empty or too short to verify.",
            "section_id": section.get("id"),
            "indicator_code": indicator_code,
            "document_id": doc_id,
            "location_ref": loc_ref,
            "quoted_text": quoted,
            "claim_summary": claim,
        }

    if _normalize_whitespace(quoted) not in _normalize_whitespace(stored_text):
        return {
            "is_valid": False,
            "resolution_status": "rejected_quote_mismatch",
            "rejection_reason": f"Quoted text does not match stored text at {loc_ref}.",
            "section_id": section.get("id"),
            "indicator_code": indicator_code,
            "document_id": doc_id,
            "location_ref": loc_ref,
            "quoted_text": quoted,
            "claim_summary": claim,
        }

    # Check numeric claims in claim_summary against numbers in the stored section text
    claim_nums = _extract_numeric_tokens(claim)
    if claim_nums:
        section_nums = set(_extract_numeric_tokens(stored_text))
        unsupported = [n for n in claim_nums if n not in section_nums]
        if unsupported:
            return {
                "is_valid": False,
                "resolution_status": "rejected_unsupported_numeric",
                "rejection_reason": (
                    f"Unsupported numeric claim(s) {unsupported} in claim summary not present at {loc_ref}."
                ),
                "section_id": section.get("id"),
                "indicator_code": indicator_code,
                "document_id": doc_id,
                "location_ref": loc_ref,
                "quoted_text": quoted,
                "claim_summary": claim,
            }

    return {
        "is_valid": True,
        "resolution_status": "resolved",
        "rejection_reason": None,
        "section_id": section.get("id"),
        "indicator_code": indicator_code,
        "document_id": doc_id,
        "location_ref": loc_ref,
        "quoted_text": quoted,
        "claim_summary": claim,
    }
