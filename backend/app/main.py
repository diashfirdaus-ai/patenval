from contextlib import asynccontextmanager
import os
from typing import Any, Dict
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.api.v1 import api_v1_router
from app.config import settings
from app.database import Base, SessionLocal, check_pgvector_status, get_db
from app.services.patent_ops import EPOOPSAdapter
from app.services.seed import seed_initial_data
from app.services.worker import worker_daemon


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("TECHVAL_TESTING") != "1":
        with SessionLocal() as db:
            seed_initial_data(db)
        worker_daemon.start()
    yield
    if os.environ.get("TECHVAL_TESTING") != "1":
        worker_daemon.stop()


app = FastAPI(
    title="TechVal AI — Scientific Technology Assessment & Economic Valuation API",
    version=settings.APP_VERSION,
    description=(
        "Versioned REST API (/api/v1) maintaining four strictly separate outputs: "
        "Technology Assessment, Commercialization Readiness, Economic Valuation (IDR), "
        "and Evidence Completeness."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["system"])
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    pg_status = check_pgvector_status(db)
    ops_adapter = EPOOPSAdapter()
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "database": pg_status,
        "table_count": len(Base.metadata.tables),
        "tables": sorted(Base.metadata.tables.keys()),
        "providers": {
            "fixture": {"available": True, "mode": "explicit_deterministic_fixture"},
            "gemini": {
                "configured": bool((settings.GEMINI_API_KEY or "").strip()),
                "model": settings.GEMINI_MODEL,
                "live_verified": False,
            },
            "openai_compatible": {
                "configured": bool((settings.OPENAI_COMPATIBLE_API_KEY or "").strip()),
                "base_url": settings.OPENAI_COMPATIBLE_BASE_URL,
                "model": settings.OPENAI_COMPATIBLE_MODEL,
                "live_verified": False,
            },
            "epo_ops": {
                "configured": ops_adapter.is_configured,
                "live_verified": False,
                "status_note": (
                    "EPO OPS credentials configured"
                    if ops_adapter.is_configured
                    else "EPO OPS credentials not configured; manual structured patent import active"
                ),
            },
        },
    }


app.include_router(api_v1_router)
