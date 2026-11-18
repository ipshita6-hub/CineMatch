"""Registration, login, logout and the current-user endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import User, UserPreference, UserSession
from app.schemas.models import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def _issue_token(db: Session, user: User) -> TokenResponse:
    token, expires = create_access_token(str(user.id))
    db.add(UserSession(user_id=user.id, token_id=uuid.uuid4().hex, expires_at=expires))
    db.commit()
    return TokenResponse(access_token=token, expires_at=expires,
                         user=UserResponse.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(
        or_(User.username == payload.username, User.email == payload.email)
    ).first()
    if existing is not None:
        field = "username" if existing.username == payload.username else "email"
        raise HTTPException(status.HTTP_409_CONFLICT, f"That {field} is already registered")

    user = User(username=payload.username, email=payload.email,
                hashed_password=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(UserPreference(user_id=user.id, preferred_genres="", default_model="neumf"))
    db.commit()
    db.refresh(user)
    return _issue_token(db, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(
        or_(User.username == payload.username, User.email == payload.username)
    ).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled")
    return _issue_token(db, user)


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
           user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    revoked = (db.query(UserSession)
               .filter(UserSession.user_id == user.id, UserSession.revoked.is_(False),
                       UserSession.expires_at > now)
               .update({"revoked": True}, synchronize_session=False))
    db.commit()
    return {"status": "logged out", "sessions_revoked": int(revoked)}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
