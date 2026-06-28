"""Settings routes — user preferences and configuration."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the settings page."""
    settings_service = SettingsService(db)
    settings = settings_service.get_settings(user.id)

    change_password = request.query_params.get("change_password", "")
    saved = request.query_params.get("saved", "")
    error = request.query_params.get("error", "")

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "change_password": change_password,
            "saved": saved,
            "error": error,
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/")
async def update_settings(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update user settings."""
    form = await request.form()
    settings_service = SettingsService(db)

    try:
        # Collect working days from checkboxes
        working_days = []
        for d in range(1, 8):
            if form.get(f"working_day_{d}"):
                working_days.append(d)

        settings_service.update_settings(
            user.id,
            weekly_target=form.get("weekly_target"),
            daily_target=form.get("daily_target"),
            working_days=working_days if working_days else None,
            lunch_deduction=form.get("lunch_deduction"),
            theme=form.get("theme"),
            date_format=form.get("date_format"),
            time_format=form.get("time_format"),
            first_day_of_week=form.get("first_day_of_week"),
        )

        return RedirectResponse(url="/settings?saved=1", status_code=303)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/settings?error={exc}", status_code=303
        )


@router.post("/change-password")
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Change the user's password."""
    form = await request.form()
    current = form.get("current_password", "")
    new_pass = form.get("new_password", "")
    confirm = form.get("confirm_password", "")

    if new_pass != confirm:
        return RedirectResponse(
            url="/settings?error=Passwords+do+not+match&change_password=1",
            status_code=303,
        )

    if len(new_pass) < 8:
        return RedirectResponse(
            url="/settings?error=Password+must+be+at+least+8+characters&change_password=1",
            status_code=303,
        )

    auth_service = AuthService(db)

    # For forced password change, skip current password check
    if user.force_password_change:
        auth_service.force_set_password(user.id, new_pass)
        return RedirectResponse(url="/settings?saved=1", status_code=303)

    if auth_service.change_password(user.id, current, new_pass):
        return RedirectResponse(url="/settings?saved=1", status_code=303)
    else:
        return RedirectResponse(
            url="/settings?error=Current+password+is+incorrect&change_password=1",
            status_code=303,
        )


@router.post("/backup")
async def create_backup(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Create a database backup."""
    try:
        backup_service = BackupService()
        backup_path = backup_service.create_backup(label="manual")
        return RedirectResponse(url="/settings?saved=backup", status_code=303)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return RedirectResponse(
            url=f"/settings?error=Backup+failed:+{exc}", status_code=303
        )
