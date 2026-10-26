import base64
import hashlib
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "TechVal AI"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"

    DATABASE_URL: str = "postgresql+psycopg://postgres@localhost:5432/techval"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres@localhost:5432/techval_test"

    STORAGE_ENCRYPTION_KEY: str = "dGVjaHZhbC1haS1sb2NhbC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzIQ=="
    SESSION_SECRET_KEY: str = "techval-local-session-secret-change-in-production-2026"
    SESSION_TTL_HOURS: int = 24
    MAX_UPLOAD_SIZE_MB: int = 25

    RUNTIME_DIR: str = ".runtime"
    ENCRYPTED_VAULT_DIR: str = ".runtime/vault"
    REPORT_STORAGE_DIR: str = ".runtime/reports"
    CHECKPOINT_DIR: str = ".runtime/checkpoints"

    DEFAULT_AI_PROVIDER: str = "fixture"
    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_COMPATIBLE_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_COMPATIBLE_API_KEY: Optional[str] = ""
    OPENAI_COMPATIBLE_MODEL: str = "gpt-4o-mini"

    EPO_OPS_CONSUMER_KEY: Optional[str] = ""
    EPO_OPS_CONSUMER_SECRET: Optional[str] = ""

    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def runtime_path(self) -> Path:
        p = ROOT_DIR / self.RUNTIME_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def vault_path(self) -> Path:
        p = ROOT_DIR / self.ENCRYPTED_VAULT_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def report_path(self) -> Path:
        p = ROOT_DIR / self.REPORT_STORAGE_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def checkpoint_path(self) -> Path:
        p = ROOT_DIR / self.CHECKPOINT_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_fernet_key(self) -> bytes:
        raw = self.STORAGE_ENCRYPTION_KEY.strip().encode("utf-8")
        try:
            decoded = base64.urlsafe_b64decode(raw)
            if len(decoded) == 32:
                return raw
        except Exception:
            pass
        digest = hashlib.sha256(raw).digest()
        return base64.urlsafe_b64encode(digest)


settings = Settings()
