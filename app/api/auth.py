"""Authentication routes — login, logout, password change."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user_optional,
    remove_session,
    store_session,
)
from app.auth.rate_limiter import rate_limiter
from app.auth.security import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_session_id,
    generate_csrf_token,
    get_client_ip,
    set_csrf_cookie,
    set_session_cookie,
)
from app.database.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Render the login page."""
    # Redirect to dashboard if already authenticated
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/", status_code=303)

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "csrf_token": csrf_token,
            "error": None,
            "register_mode": request.query_params.get("register") == "1",
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/login")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    """Process login form submission."""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    remember = form.get("remember", "") == "on"

    ip = get_client_ip(request)

    # Rate limiting
    if rate_limiter.is_blocked(ip, username):
        csrf_token = generate_csrf_token()
        response = request.app.state.templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Too many login attempts. Please try again later.",
                "username": username,
            },
        )
        set_csrf_cookie(response, csrf_token)
        return response

    # Authenticate
    auth_service = AuthService(db)
    user = auth_service.authenticate(username, password)

    if user is None:
        rate_limiter.record_attempt(ip, username)
        remaining = rate_limiter.get_remaining_attempts(ip, username)
        csrf_token = generate_csrf_token()
        response = request.app.state.templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": f"Invalid username or password. {remaining} attempts remaining.",
                "username": username,
            },
        )
        set_csrf_cookie(response, csrf_token)
        return response

    # Success
    rate_limiter.reset(ip, username)
    session_id = create_session_id()
    store_session(session_id, user.id)

    # Always redirect to dashboard, we will prompt for password change in the UI
    redirect_url = "/"
    response = RedirectResponse(url=redirect_url, status_code=303)
    set_session_cookie(response, session_id, remember)
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)

    logger.info("User '%s' logged in from %s", username, ip)
    return response


@router.post("/register")
async def register_submit(request: Request, db: Session = Depends(get_db)):
    """Process registration form submission."""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    display_name = form.get("display_name", "").strip() or None

    ip = get_client_ip(request)
    
    if len(password) < 8:
        csrf_token = generate_csrf_token()
        response = request.app.state.templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Password must be at least 8 characters long.",
                "reg_username": username,
                "reg_display_name": display_name or "",
                "register_mode": True,
            },
        )
        set_csrf_cookie(response, csrf_token)
        return response

    auth_service = AuthService(db)
    existing_user = auth_service.user_repo.get_by_username(username)
    
    if existing_user:
        csrf_token = generate_csrf_token()
        response = request.app.state.templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Username is already taken.",
                "reg_username": username,
                "reg_display_name": display_name or "",
                "register_mode": True,
            },
        )
        set_csrf_cookie(response, csrf_token)
        return response

    # Create new user
    user = auth_service.create_user(
        username=username,
        password=password,
        display_name=display_name,
        is_admin=False,
        force_password_change=False,
    )
    
    # Initialize their default settings
    from app.repositories.settings_repo import SettingsRepository
    settings_repo = SettingsRepository(db)
    settings_repo.get_for_user(user.id)
    
    logger.info("New user registered: '%s' from %s", username, ip)

    # Automatically log them in
    session_id = create_session_id()
    store_session(session_id, user.id)

    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, session_id, False)
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/logout")
async def logout(request: Request):
    """Log the user out."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        remove_session(session_id)

    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response


@router.get("/logout")
async def logout_get(request: Request):
    """Handle GET logout (convenience for links)."""
    return await logout(request)
