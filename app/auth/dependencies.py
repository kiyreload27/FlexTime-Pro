"""Authentication dependencies for FastAPI routes."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.security import SESSION_COOKIE_NAME
from app.database.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# In-memory session store (for single-instance deployment)
# Maps session_id -> user_id
_sessions: dict[str, int] = {}


def store_session(session_id: str, user_id: int) -> None:
    """Store a session mapping."""
    _sessions[session_id] = user_id


def remove_session(session_id: str) -> None:
    """Remove a session mapping."""
    _sessions.pop(session_id, None)


def get_user_id_from_session(session_id: str) -> Optional[int]:
    """Look up a user ID from a session ID."""
    return _sessions.get(session_id)


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, None otherwise."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None

    user_id = get_user_id_from_session(session_id)
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    return user


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user or redirect to login.

    Used as a FastAPI dependency for protected routes.
    """
    user = get_current_user_optional(request, db)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that enforces authentication. Redirects to login if not authenticated."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    user_id = get_user_id_from_session(session_id)
    if user_id is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    return user


def require_admin(request: Request, user: User = Depends(get_current_user)) -> User:
    """Dependency that enforces admin privileges. Returns 403 or redirects if not admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

