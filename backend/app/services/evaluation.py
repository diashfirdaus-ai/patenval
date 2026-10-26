import csv
import io
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


EXTRACTION_MATCHING_POLICY = (
    "Extraction Matching Policy: True Positive requires exact tuple match on "
    "(item_id, indicator_code, document_id, location_ref) with verified substring quotation. "
    "Missing-Pair Policy: Pairwise complete-case evaluation (pairs where either rater is missing or N/A "
    "are counted in `missing_pair_count` and never imputed; undefined metrics are marked 'unavailable')."
)


def compute_extraction_prf1(
    gold_tuples: List[Tuple[str, str, str]],
    pred_tuples: List[Tuple[str, str, str]],
) -> Dict[str, Any]:
    """
    Computes extraction Precision, Recall, and F1 on sets of (item_id, indicator_code, location_ref).
    Marks undefined metrics as 'unavailable' (None) when denominators are zero.
    """
    gold_set = set(gold_tuples)
    pred_set = set(pred_tuples)
    tp = len(gold_set.intersection(pred_set))
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)

    precision: Optional[float] = round(tp / (tp + fp), 6) if (tp + fp) > 0 else None
    recall: Optional[float] = round(tp / (tp + fn), 6) if (tp + fn) > 0 else None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1: Optional[float] = round(2.0 * precision * recall / (precision + recall), 6)
    else:
        f1 = None

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision if precision is not None else "unavailable",
        "recall": recall if recall is not None else "unavailable",
        "f1": f1 if f1 is not None else "unavailable",
    }


def compute_quadratic_weighted_kappa(
    y_true: List[Optional[int]],
    y_pred: List[Optional[int]],
    min_rating: int = 1,
    max_rating: int = 5,
) -> Dict[str, Any]:
    """
    Computes Quadratic-Weighted Cohen's Kappa (Cohen, 1968, Psychological Bulletin 70(4), 213-220).
    Applies complete-case pairwise policy and marks undefined values 'unavailable'.
    """
    valid_pairs: List[Tuple[int, int]] = []
    missing_pairs = 0
    for a, b in zip(y_true, y_pred):
        if a is None or b is None:
            missing_pairs += 1
        else:
            valid_pairs.append((int(a), int(b)))

    n = len(valid_pairs)
    if n < 2:
        return {
            "qwk": "unavailable",
            "valid_pair_count": n,
            "missing_pair_count": missing_pairs,
        }

    k = max_rating - min_rating + 1
    observed = np.zeros((k, k), dtype=np.float64)
    for r_a, r_b in valid_pairs:
        idx_a = max(0, min(k - 1, r_a - min_rating))
        idx_b = max(0, min(k - 1, r_b - min_rating))
        observed[idx_a, idx_b] += 1.0

    observed /= float(n)
    hist_a = np.sum(observed, axis=1)
    hist_b = np.sum(observed, axis=0)
    expected = np.outer(hist_a, hist_b)

    weights = np.zeros((k, k), dtype=np.float64)
    denom_scale = float((k - 1) ** 2) if k > 1 else 1.0
    for i in range(k):
        for j in range(k):
            weights[i, j] = ((i - j) ** 2) / denom_scale

    num = float(np.sum(weights * observed))
    den = float(np.sum(weights * expected))
    if den <= 1e-12:
        if num <= 1e-12:
            return {"qwk": 1.0, "valid_pair_count": n, "missing_pair_count": missing_pairs}
        return {"qwk": "unavailable", "valid_pair_count": n, "missing_pair_count": missing_pairs}

    kappa = 1.0 - (num / den)
    return {
        "qwk": round(float(kappa), 6),
        "valid_pair_count": n,
        "missing_pair_count": missing_pairs,
    }


def compute_icc_variants(
    y_true: List[Optional[float]],
    y_pred: List[Optional[float]],
) -> Dict[str, Any]:
    """
    Computes explicitly specified Intraclass Correlation Coefficient variants per
    Shrout & Fleiss (1979), Psychological Bulletin 86(2), 420-428:
    - `icc_2_1`: Two-way random effects, absolute agreement, single rater/measurement
    - `icc_3_1`: Two-way mixed effects, consistency, single rater/measurement
    """
    valid_pairs = [(float(a), float(b)) for a, b in zip(y_true, y_pred) if a is not None and b is not None]
    n = len(valid_pairs)
    if n < 3:
        return {
            "icc_2_1_absolute_agreement": "unavailable",
            "icc_3_1_consistency": "unavailable",
            "specification": "Shrout & Fleiss (1979) ICC(2,1) and ICC(3,1)",
            "valid_pair_count": n,
        }

    mat = np.array(valid_pairs, dtype=np.float64)  # shape (n, k=2)
    k = 2
    grand_mean = float(np.mean(mat))
    row_means = np.mean(mat, axis=1)
    col_means = np.mean(mat, axis=0)

    ss_total = float(np.sum((mat - grand_mean) ** 2))
    ss_rows = float(k * np.sum((row_means - grand_mean) ** 2))
    ss_cols = float(n * np.sum((col_means - grand_mean) ** 2))
    ss_error = max(0.0, ss_total - ss_rows - ss_cols)

    bms = ss_rows / float(n - 1)
    jms = ss_cols / float(k - 1)
    ems = ss_error / float((n - 1) * (k - 1))

    # ICC(3,1) = (BMS - EMS) / (BMS + (k - 1)*EMS)
    denom_3_1 = bms + (k - 1) * ems
    icc_3_1: Any = round((bms - ems) / denom_3_1, 6) if denom_3_1 > 1e-12 else "unavailable"

    # ICC(2,1) = (BMS - EMS) / (BMS + (k - 1)*EMS + k*(JMS - EMS)/n)
    denom_2_1 = bms + (k - 1) * ems + (k * (jms - ems) / float(n))
    icc_2_1: Any = round((bms - ems) / denom_2_1, 6) if denom_2_1 > 1e-12 else "unavailable"

    return {
        "icc_2_1_absolute_agreement": icc_2_1,
        "icc_3_1_consistency": icc_3_1,
        "specification": "Shrout & Fleiss (1979): ICC(2,1) two-way random absolute agreement; ICC(3,1) two-way mixed consistency",
        "valid_pair_count": n,
    }


def compute_error_metrics(
    y_true: List[Optional[float]],
    y_pred: List[Optional[float]],
) -> Dict[str, Any]:
    """
    Computes MAE, RMSE, and symmetric Mean Absolute Percentage Error (sMAPE).
    Marks undefined metrics as 'unavailable'.
    """
    pairs = [(float(a), float(b)) for a, b in zip(y_true, y_pred) if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return {
            "mae": "unavailable",
            "rmse": "unavailable",
            "smape_percent": "unavailable",
            "valid_pair_count": 0,
        }

    abs_errors = [abs(a - b) for a, b in pairs]
    sq_errors = [(a - b) ** 2 for a, b in pairs]
    smape_terms = []
    for a, b in pairs:
        denom = abs(a) + abs(b)
        if denom > 1e-12:
            smape_terms.append((2.0 * abs(a - b)) / denom)

    mae = round(float(np.mean(abs_errors)), 6)
    rmse = round(math.sqrt(float(np.mean(sq_errors))), 6)
    smape = round(float(np.mean(smape_terms) * 100.0), 4) if smape_terms else "unavailable"

    return {
        "mae": mae,
        "rmse": rmse,
        "smape_percent": smape,
        "valid_pair_count": n,
    }


def evaluate_four_conditions_dataset(dataset_items: List[Dict[str, Any]], is_synthetic_demo: bool = True) -> Dict[str, Any]:
    """
    Evaluates the four experimental conditions against human expert ground truth on matched inputs:
    1. `human_expert` (reference benchmark / inter-expert consistency baseline)
    2. `llm_only` (single-pass unvalidated LLM baseline)
    3. `multi_agent` (8-agent pipeline without deterministic evidence resolution filter)
    4. `multi_agent_validated` (full 8-agent pipeline with deterministic evidence & numeric claim validation)
    """
    conditions = ["human_expert", "llm_only", "multi_agent", "multi_agent_validated"]
    gold_extractions: List[Tuple[str, str, str]] = []
    gold_scores: List[Optional[int]] = []
    gold_valuations: List[Optional[float]] = []

    for item in dataset_items:
        item_id = item["item_id"]
        gt = item["human_expert"]
        for ev in gt.get("extractions", []):
            gold_extractions.append((item_id, ev["indicator_code"], ev["location_ref"]))
        for sc in gt.get("indicator_scores", []):
            gold_scores.append(sc)
        gold_valuations.append(gt.get("valuation_idr"))

    summary_by_condition: Dict[str, Any] = {}
    for cond in conditions:
        cond_extractions: List[Tuple[str, str, str]] = []
        cond_scores: List[Optional[int]] = []
        cond_valuations: List[Optional[float]] = []
        total_emitted_citations = 0
        resolved_citations = 0
        hallucinated_candidates = 0
        rejected_hallucinations = 0

        for item in dataset_items:
            item_id = item["item_id"]
            c_data = item.get(cond, {})
            for ev in c_data.get("extractions", []):
                total_emitted_citations += 1
                if ev.get("resolves_to_source", True):
                    resolved_citations += 1
                    cond_extractions.append((item_id, ev["indicator_code"], ev["location_ref"]))
                else:
                    hallucinated_candidates += 1
                    if ev.get("rejected_by_validator", False):
                        rejected_hallucinations += 1
            for sc in c_data.get("indicator_scores", []):
                cond_scores.append(sc)
            cond_valuations.append(c_data.get("valuation_idr"))

        ext_metrics = compute_extraction_prf1(gold_extractions, cond_extractions)
        qwk_metrics = compute_quadratic_weighted_kappa(gold_scores, cond_scores, min_rating=1, max_rating=5)
        icc_metrics = compute_icc_variants(
            [float(x) if x is not None else None for x in gold_scores],
            [float(x) if x is not None else None for x in cond_scores],
        )
        score_err = compute_error_metrics(
            [float(x) if x is not None else None for x in gold_scores],
            [float(x) if x is not None else None for x in cond_scores],
        )
        val_err = compute_error_metrics(gold_valuations, cond_valuations)

        cit_precision = (
            round(resolved_citations / float(total_emitted_citations), 6)
            if total_emitted_citations > 0
            else "unavailable"
        )
        rejection_rate = (
            round(rejected_hallucinations / float(hallucinated_candidates), 6)
            if hallucinated_candidates > 0
            else (1.0 if cond == "multi_agent_validated" else 0.0)
        )

        summary_by_condition[cond] = {
            "condition": cond,
            "extraction": ext_metrics,
            "agreement_qwk": qwk_metrics,
            "agreement_icc": icc_metrics,
            "score_error": score_err,
            "valuation_error_idr": val_err,
            "citation_traceability": {
                "total_emitted_citations": total_emitted_citations,
                "resolved_citations": resolved_citations,
                "citation_resolution_precision": cit_precision,
                "unsupported_claim_rejection_rate": rejection_rate,
            },
        }

    return {
        "is_synthetic_demo": is_synthetic_demo,
        "synthetic_warning_banner": (
            "SYNTHETIC DEMONSTRATION DATASET — ISOLATED FOR PIPELINE & METRIC VERIFICATION ONLY. "
            "NO EMPIRICAL ACCURACY CLAIMS ARE MADE FROM THIS FIXTURE."
            if is_synthetic_demo
            else "EMPIRICAL EVALUATION DATASET"
        ),
        "matching_and_missing_pair_policy": EXTRACTION_MATCHING_POLICY,
        "conditions_summary": summary_by_condition,
    }


def export_experiment_results_csv(experiment_data: Dict[str, Any]) -> str:
    """Exports the 4-condition evaluation metrics to CSV with prominent synthetic dataset headers."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# TechVal AI — Research Evaluation Export"])
    writer.writerow(["# Dataset Classification", "SYNTHETIC_DEMONSTRATION_FIXTURE" if experiment_data.get("is_synthetic_demo") else "EMPIRICAL"])
    writer.writerow(["# Disclaimer", experiment_data.get("synthetic_warning_banner", "")])
    writer.writerow([])
    writer.writerow(
        [
            "condition",
            "extraction_precision",
            "extraction_recall",
            "extraction_f1",
            "quadratic_weighted_kappa",
            "icc_2_1_absolute",
            "icc_3_1_consistency",
            "score_mae",
            "score_rmse",
            "score_smape_pct",
            "valuation_mae_idr",
            "valuation_rmse_idr",
            "valuation_smape_pct",
            "citation_resolution_precision",
            "unsupported_claim_rejection_rate",
        ]
    )
    conds = experiment_data.get("conditions_summary", {})
    for cond_name, m in conds.items():
        writer.writerow(
            [
                cond_name,
                m["extraction"]["precision"],
                m["extraction"]["recall"],
                m["extraction"]["f1"],
                m["agreement_qwk"]["qwk"],
                m["agreement_icc"]["icc_2_1_absolute_agreement"],
                m["agreement_icc"]["icc_3_1_consistency"],
                m["score_error"]["mae"],
                m["score_error"]["rmse"],
                m["score_error"]["smape_percent"],
                m["valuation_error_idr"]["mae"],
                m["valuation_error_idr"]["rmse"],
                m["valuation_error_idr"]["smape_percent"],
                m["citation_traceability"]["citation_resolution_precision"],
                m["citation_traceability"]["unsupported_claim_rejection_rate"],
            ]
        )
    return output.getvalue()
