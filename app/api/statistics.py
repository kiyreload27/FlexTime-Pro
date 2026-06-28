"""Statistics routes — comprehensive analytics page."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.user import User
from app.services.calculation_service import CalculationService
from app.services.settings_service import SettingsService
from app.utils.time_parser import format_balance, format_hours
from app.utils.date_helpers import format_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/", response_class=HTMLResponse)
async def statistics_view(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the statistics page."""
    calc_service = CalculationService(db)
    settings_service = SettingsService(db)
    settings = settings_service.get_settings(user.id)

    stats = calc_service.get_statistics(user.id)
    running_balance = calc_service.get_running_balance(user.id)

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "stats": stats,
            "running_balance": running_balance,
            "csrf_token": csrf_token,
            "format_hours": format_hours,
            "format_balance": format_balance,
            "format_date": format_date,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response
