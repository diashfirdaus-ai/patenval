from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AHPMatrix, User, WeightSet
from app.schemas import AHPComputeAndSaveRequest
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.ahp import SAATY_RI_SOURCE, SAATY_RI_TABLE, validate_and_solve_ahp

router = APIRouter(prefix="/weighting", tags=["weighting"])


@router.get("/weight-sets")
def list_weight_sets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    sets = list(db.execute(select(WeightSet).order_by(WeightSet.created_at.desc())).scalars())
    matrices = list(db.execute(select(AHPMatrix).order_by(AHPMatrix.created_at.desc())).scalars())
    return {
        "saaty_ri_table": SAATY_RI_TABLE,
        "saaty_ri_source": SAATY_RI_SOURCE,
        "cr_convention_threshold": 0.10,
        "weight_sets": [
            {
                "id": ws.id,
                "name": ws.name,
                "version_tag": ws.version_tag,
                "weighting_method": ws.weighting_method,
                "is_provisional": ws.is_provisional,
                "is_active": ws.is_active,
                "tech_consistency_ratio": ws.tech_consistency_ratio,
                "comm_consistency_ratio": ws.comm_consistency_ratio,
                "weights_json": ws.weights_json,
                "methodological_note": ws.methodological_note,
                "created_at": ws.created_at.isoformat(),
            }
            for ws in sets
        ],
        "ahp_matrices": [
            {
                "id": m.id,
                "weight_set_id": m.weight_set_id,
                "dimension": m.dimension,
                "indicator_codes": m.indicator_codes_json,
                "matrix": m.matrix_json,
                "eigenvector_weights": m.eigenvector_weights_json,
                "lambda_max": m.lambda_max,
                "consistency_index_ci": m.consistency_index_ci,
                "random_index_ri": m.random_index_ri,
                "ri_source_citation": m.ri_source_citation,
                "consistency_ratio_cr": m.consistency_ratio_cr,
                "is_consistent": m.is_consistent,
                "convention_note": m.convention_note,
            }
            for m in matrices
        ],
    }


@router.post("/ahp-preview")
def preview_ahp_matrix(
    payload: Dict[str, Any],
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    codes = payload.get("indicator_codes", [])
    matrix = payload.get("matrix", [])
    try:
        return validate_and_solve_ahp(codes, matrix)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ahp-save", status_code=status.HTTP_201_CREATED)
def save_and_optionally_activate_ahp_weights(
    payload: AHPComputeAndSaveRequest,
    user: User = Depends(require_roles("admin", "analyst", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    existing = db.execute(
        select(WeightSet).where(WeightSet.version_tag == payload.version_tag)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"WeightSet version '{payload.version_tag}' already exists.")

    try:
        tech_res = validate_and_solve_ahp(payload.tech_indicator_codes, payload.tech_matrix)
        comm_res = validate_and_solve_ahp(payload.comm_indicator_codes, payload.comm_matrix)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    both_consistent = bool(tech_res["is_consistent"] and comm_res["is_consistent"])

    if payload.activate_immediately and not both_consistent:
        raise HTTPException(
            status_code=422,
            detail=(
                f"AHP Consistency Ratio exceeds 0.10 methodological convention "
                f"(Tech CR={tech_res['consistency_ratio_cr']:.4f}, Comm CR={comm_res['consistency_ratio_cr']:.4f}). "
                "Activation is blocked until pairwise judgments are revised."
            ),
        )

    if payload.activate_immediately and both_consistent:
        for active_ws in db.execute(select(WeightSet).where(WeightSet.is_active.is_(True))).scalars():
            active_ws.is_active = False

    combined_weights = {**tech_res["weights"], **comm_res["weights"]}
    ws = WeightSet(
        name=payload.name,
        version_tag=payload.version_tag,
        weighting_method="ahp_eigenvector",
        is_provisional=not both_consistent,
        is_active=bool(payload.activate_immediately and both_consistent),
        tech_consistency_ratio=tech_res["consistency_ratio_cr"],
        comm_consistency_ratio=comm_res["consistency_ratio_cr"],
        weights_json=combined_weights,
        methodological_note=(
            "AHP principal right eigenvector weights derived from reciprocal pairwise matrices. "
            "CR <= 0.10 threshold enforced as a methodological convention (Saaty, 1980)."
        ),
        created_by=user.id,
    )
    db.add(ws)
    db.flush()

    m_tech = AHPMatrix(
        weight_set_id=ws.id,
        dimension="technology_assessment",
        indicator_codes_json=payload.tech_indicator_codes,
        matrix_json=payload.tech_matrix,
        eigenvector_weights_json=tech_res["weights"],
        lambda_max=tech_res["lambda_max"],
        consistency_index_ci=tech_res["consistency_index_ci"],
        random_index_ri=tech_res["random_index_ri"],
        ri_source_citation=tech_res["ri_source_citation"],
        consistency_ratio_cr=tech_res["consistency_ratio_cr"],
        is_consistent=tech_res["is_consistent"],
        convention_note=tech_res["convention_note"],
        created_by=user.id,
    )
    m_comm = AHPMatrix(
        weight_set_id=ws.id,
        dimension="commercialization_readiness",
        indicator_codes_json=payload.comm_indicator_codes,
        matrix_json=payload.comm_matrix,
        eigenvector_weights_json=comm_res["weights"],
        lambda_max=comm_res["lambda_max"],
        consistency_index_ci=comm_res["consistency_index_ci"],
        random_index_ri=comm_res["random_index_ri"],
        ri_source_citation=comm_res["ri_source_citation"],
        consistency_ratio_cr=comm_res["consistency_ratio_cr"],
        is_consistent=comm_res["is_consistent"],
        convention_note=comm_res["convention_note"],
        created_by=user.id,
    )
    db.add_all([m_tech, m_comm])
    record_audit_log(
        db=db,
        actor=user,
        action="weight_set.create_ahp",
        entity_type="weight_set",
        entity_id=ws.id,
        details={
            "version_tag": ws.version_tag,
            "tech_cr": ws.tech_consistency_ratio,
            "comm_cr": ws.comm_consistency_ratio,
            "is_active": ws.is_active,
        },
    )
    db.commit()
    return {
        "weight_set_id": ws.id,
        "version_tag": ws.version_tag,
        "is_active": ws.is_active,
        "tech_ahp": tech_res,
        "comm_ahp": comm_res,
    }


@router.post("/weight-sets/{weight_set_id}/activate")
def activate_weight_set(
    weight_set_id: str,
    user: User = Depends(require_roles("admin", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    ws = db.execute(select(WeightSet).where(WeightSet.id == weight_set_id)).scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="WeightSet not found.")

    if ws.weighting_method == "ahp_eigenvector":
        if (ws.tech_consistency_ratio or 0.0) > 0.10 or (ws.comm_consistency_ratio or 0.0) > 0.10:
            raise HTTPException(
                status_code=422,
                detail="Cannot activate an AHP weight set with Consistency Ratio > 0.10.",
            )

    for other in db.execute(select(WeightSet).where(WeightSet.is_active.is_(True))).scalars():
        other.is_active = False

    ws.is_active = True
    record_audit_log(
        db=db,
        actor=user,
        action="weight_set.activate",
        entity_type="weight_set",
        entity_id=ws.id,
        details={"version_tag": ws.version_tag},
    )
    db.commit()
    return {"id": ws.id, "version_tag": ws.version_tag, "is_active": ws.is_active}
