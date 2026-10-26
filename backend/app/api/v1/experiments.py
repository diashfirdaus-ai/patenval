import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Experiment, ExperimentDataset, User
from app.schemas import ExperimentRunCreateRequest
from app.security.auth import get_current_user, record_audit_log, require_roles
from app.services.evaluation import (
    EXTRACTION_MATCHING_POLICY,
    evaluate_four_conditions_dataset,
    export_experiment_results_csv,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/datasets")
def list_experiment_datasets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    datasets = list(
        db.execute(select(ExperimentDataset).order_by(ExperimentDataset.created_at.desc())).scalars()
    )
    visible: List[Dict[str, Any]] = []
    for ds in datasets:
        allowed_roles = ds.access_roles_json or ["admin", "analyst", "expert_reviewer"]
        if user.role not in allowed_roles:
            continue
        visible.append(
            {
                "id": ds.id,
                "code": ds.code,
                "name": ds.name,
                "version_tag": ds.version_tag,
                "description": ds.description,
                "is_synthetic_demo": ds.is_synthetic_demo,
                "manifest_hash": ds.manifest_hash,
                "access_roles": allowed_roles,
                "item_count": len(ds.items_json or []),
                "created_at": ds.created_at.isoformat(),
            }
        )
    return visible


@router.get("")
def list_experiments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    exps = list(db.execute(select(Experiment).order_by(Experiment.created_at.desc())).scalars())
    return [
        {
            "id": e.id,
            "dataset_id": e.dataset_id,
            "name": e.name,
            "is_synthetic_demo": e.is_synthetic_demo,
            "conditions_compared": e.conditions_compared_json,
            "manifest": e.manifest_json,
            "metrics_summary": e.metrics_summary_json,
            "per_condition_results": e.per_condition_results_json,
            "matching_policy_note": e.matching_policy_note,
            "created_at": e.created_at.isoformat(),
        }
        for e in exps
    ]


@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_experiment_benchmark(
    payload: ExperimentRunCreateRequest,
    user: User = Depends(require_roles("admin", "analyst", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    ds = db.execute(
        select(ExperimentDataset).where(ExperimentDataset.id == payload.dataset_id)
    ).scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Experiment dataset not found.")

    if user.role not in (ds.access_roles_json or []):
        raise HTTPException(status_code=403, detail="Not authorized to access this experiment dataset.")

    eval_out = evaluate_four_conditions_dataset(ds.items_json, is_synthetic_demo=ds.is_synthetic_demo)
    exp = Experiment(
        dataset_id=ds.id,
        name=payload.name,
        is_synthetic_demo=ds.is_synthetic_demo,
        conditions_compared_json=["human_expert", "llm_only", "multi_agent", "multi_agent_validated"],
        manifest_json={
            "dataset_code": ds.code,
            "dataset_version": ds.version_tag,
            "manifest_hash": ds.manifest_hash,
            "app_version": settings.APP_VERSION,
            "is_synthetic_demo": ds.is_synthetic_demo,
        },
        metrics_summary_json=eval_out,
        per_condition_results_json=eval_out["conditions_summary"],
        matching_policy_note=EXTRACTION_MATCHING_POLICY,
        created_by=user.id,
    )
    db.add(exp)
    db.flush()
    record_audit_log(
        db=db,
        actor=user,
        action="experiment.run",
        entity_type="experiment",
        entity_id=exp.id,
        details={"dataset_code": ds.code, "is_synthetic_demo": ds.is_synthetic_demo},
    )
    db.commit()
    db.refresh(exp)

    return {
        "id": exp.id,
        "name": exp.name,
        "is_synthetic_demo": exp.is_synthetic_demo,
        "metrics_summary": exp.metrics_summary_json,
    }


@router.get("/{experiment_id}/export/json")
def export_experiment_json(
    experiment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    exp = db.execute(select(Experiment).where(Experiment.id == experiment_id)).scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    payload = {
        "experiment_id": exp.id,
        "name": exp.name,
        "is_synthetic_demo": exp.is_synthetic_demo,
        "synthetic_disclaimer": (
            "SYNTHETIC DEMONSTRATION DATASET — NO EMPIRICAL ACCURACY CLAIMS PERMITTED"
            if exp.is_synthetic_demo
            else "EMPIRICAL DATASET"
        ),
        "manifest": exp.manifest_json,
        "matching_policy_note": exp.matching_policy_note,
        "results": exp.metrics_summary_json,
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="experiment_{exp.id[:8]}.json"'},
    )


@router.get("/{experiment_id}/export/csv")
def export_experiment_csv(
    experiment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    exp = db.execute(select(Experiment).where(Experiment.id == experiment_id)).scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    csv_text = export_experiment_results_csv(exp.metrics_summary_json)
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="experiment_{exp.id[:8]}.csv"'},
    )
