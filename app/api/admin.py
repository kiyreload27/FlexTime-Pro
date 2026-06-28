"""Admin routes — manage users."""

import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Note: All endpoints in this router require admin access.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the user management page."""
    user_repo = UserRepository(db)
    users = user_repo.get_all()

    saved = request.query_params.get("saved", "")
    error = request.query_params.get("error", "")

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "saved": saved,
            "error": error,
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/users/create")
async def create_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new user account."""
    form = await request.form()
    username = form.get("username", "").strip()
    display_name = form.get("display_name", "").strip()
    is_admin = form.get("is_admin") == "1"

    if not username:
        return RedirectResponse(url="/admin/users?error=Username+is+required", status_code=303)

    auth_service = AuthService(db)
    user_repo = UserRepository(db)

    if user_repo.get_by_username(username):
        return RedirectResponse(url="/admin/users?error=Username+already+exists", status_code=303)

    # Use a default password
    default_password = "changeme"

    try:
        auth_service.create_user(
            username=username,
            password=default_password,
            is_admin=is_admin,
            force_password_change=True,
            display_name=display_name if display_name else None,
        )
        return RedirectResponse(url="/admin/users?saved=User+created+successfully", status_code=303)
    except Exception as e:
        logger.error("Failed to create user: %s", e)
        return RedirectResponse(url="/admin/users?error=Failed+to+create+user", status_code=303)


@router.post("/users/{target_user_id}/toggle-status")
async def toggle_user_status(
    target_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """Activate or deactivate a user."""
    if target_user_id == current_admin.id:
        return RedirectResponse(url="/admin/users?error=Cannot+deactivate+yourself", status_code=303)

    user_repo = UserRepository(db)
    target_user = user_repo.get_by_id(target_user_id)
    
    if not target_user:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    # Toggle status
    target_user.is_active = not target_user.is_active
    db.commit()

    action = "activated" if target_user.is_active else "deactivated"
    return RedirectResponse(url=f"/admin/users?saved=User+{action}", status_code=303)


@router.post("/users/{target_user_id}/reset-password")
async def reset_user_password(
    target_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reset a user's password to a temporary default."""
    auth_service = AuthService(db)
    user_repo = UserRepository(db)
    
    target_user = user_repo.get_by_id(target_user_id)
    if not target_user:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    # Reset to default
    default_password = "changeme"
    auth_service.force_set_password(target_user_id, default_password)
    
    # Ensure they must change it again
    target_user.force_password_change = True
    db.commit()

    return RedirectResponse(url="/admin/users?saved=Password+reset+to+'changeme'", status_code=303)
