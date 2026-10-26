from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog, User, UserSession
from app.schemas import (
    AuthSessionResponse,
    LoginRequest,
    UserCreateRequest,
    UserResponse,
)
from app.security.auth import (
    create_user_session,
    get_current_user,
    get_session_and_user,
    hash_password,
    record_audit_log,
    require_roles,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Any:
    user = db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.username)
        )
    ).scalar_one_or_none()

    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    raw_token, session = create_user_session(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    record_audit_log(
        db=db,
        actor=user,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username, "role": user.role},
    )
    db.commit()

    response.set_cookie(
        key="techval_session",
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {
        "access_token": raw_token,
        "csrf_token": session.csrf_token,
        "expires_at": session.expires_at,
        "user": user,
    }


@router.post("/logout")
def logout(
    response: Response,
    session_user: Tuple[UserSession, User] = Depends(get_session_and_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    session, user = session_user
    session.revoked_at = datetime.now(timezone.utc)
    record_audit_log(
        db=db,
        actor=user,
        action="auth.logout",
        entity_type="user_session",
        entity_id=session.id,
    )
    db.commit()
    response.delete_cookie("techval_session")
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> Any:
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Any:
    return list(db.execute(select(User).order_by(User.created_at.asc())).scalars())


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Any:
    if payload.role not in ("admin", "analyst", "expert_reviewer"):
        raise HTTPException(status_code=400, detail="Invalid role.")
    exists = db.execute(
        select(User).where((User.username == payload.username) | (User.email == payload.email))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Username or email already exists.")

    new_user = User(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        preferred_language=payload.preferred_language,
        is_active=True,
    )
    db.add(new_user)
    db.flush()
    record_audit_log(
        db=db,
        actor=actor,
        action="user.create",
        entity_type="user",
        entity_id=new_user.id,
        details={"username": new_user.username, "role": new_user.role, "password": payload.password},
    )
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/audit-logs")
def list_audit_logs(
    user: User = Depends(require_roles("admin", "expert_reviewer")),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    logs = list(
        db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).scalars()
    )
    return [
        {
            "id": l.id,
            "actor_username": l.actor_username,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details_json,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
