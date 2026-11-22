
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from core.security import settings


bearer_scheme = HTTPBearer(auto_error=False)


# =====================================
# 1. VERIFY JWT AND GET CURRENT USER
# =====================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db)
) -> User:

    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if credentials is None:
        raise authentication_error

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "type"]}
        )

        # Only JWT access tokens are accepted.
        if payload.get("type") != "access":
            raise authentication_error

        user_id = UUID(payload["sub"])

    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise authentication_error

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise authentication_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    return user


# =====================================
# 2. ALLOW ONLY MEMBERS
# =====================================

def require_member(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role != "MEMBER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member access required"
        )

    return current_user


# =====================================
# 3. ALLOW ONLY LIBRARIANS
# =====================================

def require_librarian(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role != "LIBRARIAN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Librarian access required"
        )

    return current_user
