"""Report routes — generate and download reports."""

import datetime
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.user import User
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService
from app.utils.date_helpers import get_current_week

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the reports page."""
    settings_service = SettingsService(db)
    settings = settings_service.get_settings(user.id)
    today = datetime.date.today()
    current_year, current_week = get_current_week()

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "current_year": current_year,
            "current_week": current_week,
            "current_month": today.month,
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.get("/export/{report_type}/{fmt}")
async def export_report(
    report_type: str,
    fmt: str,
    request: Request,
    year: int = None,
    week: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate and download a report."""
    today = datetime.date.today()
    report_service = ReportService(db)

    if year is None:
        year = today.year

    try:
        if report_type == "weekly":
            if week is None:
                _, week = get_current_week()
            buffer, content_type, filename = report_service.generate_weekly_report(
                user.id, year, week, fmt
            )
        elif report_type == "monthly":
            if month is None:
                month = today.month
            buffer, content_type, filename = report_service.generate_monthly_report(
                user.id, year, month, fmt
            )
        elif report_type == "yearly":
            buffer, content_type, filename = report_service.generate_yearly_report(
                user.id, year, fmt
            )
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Invalid report type"}, status_code=400)

        # Clean filename
        filename = filename.replace(" ", "_").replace(",", "")

        return StreamingResponse(
            buffer,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            },
        )
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(exc)}, status_code=500)
