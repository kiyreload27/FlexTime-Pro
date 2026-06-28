"""Calendar view routes — monthly calendar with colour-coded days."""

import datetime
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.leave_type import LeaveType
from app.models.user import User
from app.repositories.entry_repo import EntryRepository
from app.services.settings_service import SettingsService
from app.utils.date_helpers import get_calendar_grid, get_month_date_range, format_date
from app.utils.time_parser import format_hours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/", response_class=HTMLResponse)
async def current_month(request: Request):
    """Redirect to current month calendar."""
    today = datetime.date.today()
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/calendar/{today.year}/{today.month}", status_code=303)


@router.get("/{year}/{month}", response_class=HTMLResponse)
async def calendar_view(
    year: int,
    month: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the monthly calendar view."""
    settings_service = SettingsService(db)
    settings = settings_service.get_settings(user.id)
    entry_repo = EntryRepository(db)

    # Build calendar grid
    grid = get_calendar_grid(year, month, settings.first_day_of_week)

    # Get all entries for the month
    start, end = get_month_date_range(year, month)
    entries = entry_repo.get_by_date_range(user.id, start, end)
    entries_by_date = {e.date: e for e in entries}

    # Get leave types for the entry form
    leave_types = db.query(LeaveType).filter(LeaveType.is_active.is_(True)).order_by(LeaveType.sort_order).all()

    # Build calendar day data
    working_days = settings.get_working_days_list()
    calendar_data = []
    for week_row in grid:
        week_data = []
        for day in week_row:
            if day is None:
                week_data.append(None)
                continue

            entry = entries_by_date.get(day)
            is_working_day = day.isoweekday() in working_days
            is_future = day > datetime.date.today()
            is_today = day == datetime.date.today()

            # Determine colour status
            if entry and entry.leave_type and entry.leave_type.code != "WORK":
                status = "leave"
            elif entry and entry.hours_worked >= settings.daily_target:
                status = "overtime" if entry.hours_worked > settings.daily_target else "target_met"
            elif entry and entry.hours_worked > 0:
                status = "under_target"
            elif is_future or not is_working_day:
                status = "none"
            elif is_working_day and day < datetime.date.today():
                status = "missing"
            else:
                status = "none"

            week_data.append({
                "date": day,
                "entry": entry,
                "status": status,
                "is_today": is_today,
                "is_future": is_future,
                "is_working_day": is_working_day,
            })
        calendar_data.append(week_data)

    # Navigation
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "year": year,
            "month": month,
            "month_name": month_names[month],
            "calendar_data": calendar_data,
            "leave_types": leave_types,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "csrf_token": csrf_token,
            "format_hours": format_hours,
            "format_date": format_date,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response
