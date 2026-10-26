from typing import Any, Dict, List
import numpy as np


# Sourced Random Index (RI) values from:
# Saaty, T. L. (1980). The Analytic Hierarchy Process: Planning, Priority Setting,
# Resource Allocation. McGraw-Hill, New York, Table 1.5, p. 21.
SAATY_RI_TABLE: Dict[int, float] = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}

SAATY_RI_SOURCE = "Saaty, T. L. (1980), The Analytic Hierarchy Process, McGraw-Hill, Table 1.5, p. 21"
AHP_CR_CONVENTION_THRESHOLD = 0.10


def validate_and_solve_ahp(
    indicator_codes: List[str],
    matrix: List[List[float]],
    cr_threshold: float = AHP_CR_CONVENTION_THRESHOLD,
) -> Dict[str, Any]:
    """
    Validates a reciprocal AHP pairwise comparison matrix, computes the principal right
    eigenvector weights, Consistency Index (CI), Random Index (RI), and Consistency Ratio (CR).
    Flags CR > 0.10 and prevents activation until corrected (documented as a methodological convention).
    """
    n = len(indicator_codes)
    if n < 1 or n > 10:
        raise ValueError(f"AHP indicator count must be between 1 and 10, got {n}.")
    if len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError(f"AHP matrix dimensions must be {n}x{n}.")

    arr = np.array(matrix, dtype=np.float64)
    if np.any(arr <= 0) or np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError("All AHP pairwise entries must be positive finite numbers.")

    # Verify diagonal = 1 and reciprocity a_ij * a_ji == 1
    for i in range(n):
        if abs(arr[i, i] - 1.0) > 1e-4:
            raise ValueError(f"Diagonal entry ({i},{i}) must equal 1.0, got {arr[i, i]}.")
        for j in range(i + 1, n):
            prod = arr[i, j] * arr[j, i]
            if abs(prod - 1.0) > 1e-2:
                raise ValueError(
                    f"Matrix is not reciprocal at ({i},{j}): {arr[i, j]} * {arr[j, i]} = {prod:.4f} != 1.0."
                )

    # Compute principal right eigenvector
    eigenvalues, eigenvectors = np.linalg.eig(arr)
    max_idx = int(np.argmax(eigenvalues.real))
    lambda_max = float(eigenvalues[max_idx].real)
    principal_vec = np.abs(eigenvectors[:, max_idx].real)
    vec_sum = float(np.sum(principal_vec))
    if vec_sum <= 0:
        raise ValueError("Failed to compute positive principal eigenvector.")
    weights_arr = principal_vec / vec_sum

    if n <= 2:
        ci = 0.0
        ri = SAATY_RI_TABLE[n]
        cr = 0.0
    else:
        ci = max(0.0, (lambda_max - float(n)) / float(n - 1))
        ri = SAATY_RI_TABLE[n]
        cr = ci / ri if ri > 0 else 0.0

    is_consistent = bool(cr <= cr_threshold + 1e-9)
    weights_dict = {
        code: round(float(weights_arr[idx]), 6) for idx, code in enumerate(indicator_codes)
    }

    return {
        "indicator_codes": indicator_codes,
        "n": n,
        "weights": weights_dict,
        "lambda_max": round(lambda_max, 6),
        "consistency_index_ci": round(ci, 6),
        "random_index_ri": ri,
        "ri_source_citation": SAATY_RI_SOURCE,
        "consistency_ratio_cr": round(cr, 6),
        "cr_threshold": cr_threshold,
        "is_consistent": is_consistent,
        "can_activate": is_consistent,
        "convention_note": (
            f"Consistency Ratio CR = {cr:.4f} (threshold <= {cr_threshold:.2f} per Saaty 1980 methodological convention). "
            + (
                "Matrix is consistent and eligible for activation."
                if is_consistent
                else "INCONSISTENT MATRIX: CR exceeds 0.10 convention; activation is blocked until judgments are revised."
            )
        ),
    }
