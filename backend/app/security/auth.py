from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Callable, Dict, Optional, Tuple
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import AuditLog, User, UserSession


SECRET_KEY_PATTERNS = ("password", "secret", "api_key", "apikey", "token", "private_key", "authorization")


def redact_secrets(data: Any) -> Any:
    """Recursively redact sensitive keys from dictionaries and lists for audit logs."""
    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(pat in key_lower for pat in SECRET_KEY_PATTERNS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_secrets(v)
        return cleaned
    if isinstance(data, list):
        return [redact_secrets(item) for item in data]
    if isinstance(data, str):
        # Redact accidental inline API keys such as sk-... or AIza...
        if data.startswith(("sk-", "AIza")) and len(data) > 12:
            return "[REDACTED_KEY]"
    return data


def record_audit_log(
    db: Session,
    actor: Optional[User],
    action: str,
    entity_type: str,
    entity_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_username=actor.username if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=redact_secrets(details or {}),
    )
    db.add(entry)
    db.flush()
    return entry


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256$200000${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iter_str, salt, hex_digest = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(
        f"{settings.SESSION_SECRET_KEY}:{raw_token}".encode("utf-8")
    ).hexdigest()


def create_user_session(
    db: Session,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[str, UserSession]:
    raw_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        csrf_token=csrf_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return raw_token, session


def get_session_and_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_csrf_token: Optional[str] = Header(default=None),
) -> Tuple[UserSession, User]:
    raw_token: Optional[str] = None
    used_cookie = False

    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ", 1)[1].strip()
    elif "techval_session" in request.cookies:
        raw_token = request.cookies.get("techval_session")
        used_cookie = True

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid session token.",
        )

    token_hash = hash_session_token(raw_token)
    session = db.execute(
        select(UserSession).where(UserSession.token_hash == token_hash)
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not session or session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked session.",
        )

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired.",
        )

    # Enforce CSRF protection for state-mutating methods when cookie auth is used
    # or when X-CSRF-Token is supplied for verification
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if used_cookie or x_csrf_token is not None:
            if not x_csrf_token or not hmac.compare_digest(x_csrf_token, session.csrf_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token missing or invalid.",
                )

    user = db.execute(select(User).where(User.id == session.user_id)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or missing.",
        )

    return session, user


def get_current_user(
    session_user: Tuple[UserSession, User] = Depends(get_session_and_user),
) -> User:
    return session_user[1]


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized. Required one of: {', '.join(allowed_roles)}.",
            )
        return user

    return dependency
