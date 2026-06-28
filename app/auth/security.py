"""Security utilities — CSRF tokens, session management, secure headers."""

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

logger = logging.getLogger(__name__)

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_FORM_FIELD = "csrf_token"
SESSION_COOKIE_NAME = "session_id"


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Set the CSRF token cookie on a response."""
    settings = get_settings()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # JS needs to read this for the double-submit pattern
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.SESSION_MAX_AGE,
        path="/",
    )


def validate_csrf_token(request: Request) -> bool:
    """Validate the CSRF token using the double-submit cookie pattern.

    Compares the token from the cookie with the token in the form data or header.
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        return False

    # Check form field first, then header
    form_token = None
    # Form data is async so we check headers and query params here
    header_token = request.headers.get(CSRF_HEADER_NAME)

    return header_token is not None and hmac.compare_digest(cookie_token, header_token)


async def validate_csrf_form(request: Request) -> bool:
    """Validate CSRF token from form submission."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        return False

    # Try form data
    try:
        form = await request.form()
        form_token = form.get(CSRF_FORM_FIELD)
        if form_token and hmac.compare_digest(cookie_token, form_token):
            return True
    except Exception:
        pass

    # Try header
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if header_token and hmac.compare_digest(cookie_token, header_token):
        return True

    return False


def create_session_id() -> str:
    """Create a new session identifier."""
    return secrets.token_urlsafe(48)


def set_session_cookie(
    response: Response, session_id: str, remember: bool = False
) -> None:
    """Set the session cookie on a response."""
    settings = get_settings()
    max_age = settings.SESSION_MAX_AGE if remember else None
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=max_age,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )


def get_client_ip(request: Request) -> str:
    """Extract the client IP from the request, respecting proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
