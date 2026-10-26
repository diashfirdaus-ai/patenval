from fastapi import APIRouter
from app.api.v1 import (
    analysis_runs,
    auth,
    documents,
    experiments,
    indicators,
    references,
    reports,
    reviews,
    technologies,
    valuation,
    weighting,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(technologies.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(analysis_runs.router)
api_v1_router.include_router(references.router)
api_v1_router.include_router(indicators.router)
api_v1_router.include_router(weighting.router)
api_v1_router.include_router(valuation.router)
api_v1_router.include_router(reviews.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(experiments.router)
