from typing import Any, Generator, List, Optional
from sqlalchemy import create_engine, text, JSON
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import Vector
from app.config import settings


class Base(DeclarativeBase):
    pass


class EmbeddingVector(TypeDecorator):
    """
    Uses pgvector's Vector(dim) when the PostgreSQL server has the `vector` extension
    enabled, or stores the float vector as JSON when the PostgreSQL binary does not
    have the compiled C extension `vector.dll` installed.
    Also imports and exposes `pgvector.sqlalchemy.Vector` for native pgvector deployments.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 64, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.dim = dim
        self.pgvector_type = Vector(dim)

    def process_bind_param(self, value: Optional[List[float]], dialect: Any) -> Any:
        if value is None:
            return None
        return [float(x) for x in value]

    def process_result_value(self, value: Any, dialect: Any) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(x) for x in value]
        return list(value)


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def check_pgvector_status(db: Session) -> dict:
    """Checks whether PostgreSQL and the pgvector extension are available."""
    result = {
        "postgresql_connected": False,
        "postgresql_version": None,
        "pgvector_package_installed": True,
        "pgvector_extension_available": False,
        "pgvector_extension_enabled": False,
        "vector_storage_mode": "postgresql_json_vector_fallback",
    }
    try:
        ver = db.execute(text("SELECT version()")).scalar()
        result["postgresql_connected"] = True
        result["postgresql_version"] = ver
        avail = db.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        ).scalar()
        if avail:
            result["pgvector_extension_available"] = True
            try:
                db.execute(text("SAVEPOINT pgvec_check"))
                db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                db.execute(text("RELEASE SAVEPOINT pgvec_check"))
                result["pgvector_extension_enabled"] = True
                result["vector_storage_mode"] = "pgvector_native"
            except Exception:
                db.execute(text("ROLLBACK TO SAVEPOINT pgvec_check"))
    except Exception as exc:
        result["error"] = str(exc)
    return result


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
