"""Dashboard routes — main landing page with all key metrics."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.user import User
from app.services.calculation_service import CalculationService
from app.services.notification_service import NotificationService
from app.services.settings_service import SettingsService
from app.utils.time_parser import format_balance, format_hours

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the dashboard with all key metrics and charts."""
    calc_service = CalculationService(db)
    settings_service = SettingsService(db)
    notification_service = NotificationService(db)

    settings = settings_service.get_settings(user.id)
    dashboard_data = calc_service.get_dashboard_data(user.id)
    notifications = notification_service.get_pending_notifications(user.id)

    csrf_token = generate_csrf_token()

    import json
    response = request.app.state.templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "data": dashboard_data,
            "notifications": notifications,
            "csrf_token": csrf_token,
            "format_hours": format_hours,
            "format_balance": format_balance,
            "weekly_chart_json": json.dumps(dashboard_data.weekly_chart_data),
            "monthly_chart_json": json.dumps(dashboard_data.monthly_chart_data),
            "balance_chart_json": json.dumps(dashboard_data.balance_chart_data),
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response
