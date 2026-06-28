"""Work entry routes — CRUD operations for daily time entries."""

import datetime
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, get_client_ip, set_csrf_cookie
from app.database.session import get_db
from app.models.leave_type import LeaveType
from app.models.user import User
from app.services.calculation_service import CalculationService
from app.services.entry_service import EntryService
from app.services.settings_service import SettingsService
from app.utils.date_helpers import (
    get_current_week,
    get_next_week,
    get_previous_week,
    get_week_date_range,
    format_date,
)
from app.utils.time_parser import format_balance, format_hours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("/", response_class=HTMLResponse)
async def current_week_view(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Redirect to the current week view."""
    year, week = get_current_week()
    return RedirectResponse(url=f"/entries/week/{year}/{week}", status_code=303)


@router.get("/week/{year}/{week}", response_class=HTMLResponse)
async def weekly_entry_view(
    year: int,
    week: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the weekly entry form — the main data entry page."""
    settings_service = SettingsService(db)
    calc_service = CalculationService(db)
    settings = settings_service.get_settings(user.id)

    summary = calc_service.get_weekly_summary(user.id, year, week)
    running_balance = calc_service.get_running_balance(user.id)

    start_date, end_date = get_week_date_range(year, week, settings.first_day_of_week)
    prev_year, prev_week = get_previous_week(year, week)
    next_year, next_week = get_next_week(year, week)

    # Build day-by-day data
    leave_types = db.query(LeaveType).filter(LeaveType.is_active.is_(True)).order_by(LeaveType.sort_order).all()

    days = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current = start_date
    for i in range(7):
        day_date = start_date + datetime.timedelta(days=i)
        entry = next((e for e in summary.entries if e.date == day_date), None)
        is_working_day = day_date.isoweekday() in settings.get_working_days_list()
        days.append({
            "date": day_date,
            "name": day_names[day_date.weekday()],
            "short_name": day_names[day_date.weekday()][:3],
            "entry": entry,
            "is_working_day": is_working_day,
            "is_today": day_date == datetime.date.today(),
            "is_future": day_date > datetime.date.today(),
        })

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "weekly.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "year": year,
            "week": week,
            "summary": summary,
            "running_balance": running_balance,
            "days": days,
            "leave_types": leave_types,
            "prev_year": prev_year,
            "prev_week": prev_week,
            "next_year": next_year,
            "next_week": next_week,
            "csrf_token": csrf_token,
            "format_hours": format_hours,
            "format_balance": format_balance,
            "format_date": format_date,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/save")
async def save_entry(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save or update a work entry."""
    form = await request.form()
    date_str = form.get("date", "")
    hours_input = form.get("hours_input", "")
    start_time = form.get("start_time", "")
    end_time = form.get("end_time", "")
    break_minutes_str = form.get("break_minutes", "0")
    notes = form.get("notes", "")
    tags = form.get("tags", "")
    leave_type_id_str = form.get("leave_type_id", "")
    return_url = form.get("return_url", "")

    try:
        date = datetime.date.fromisoformat(date_str)
        break_minutes = int(break_minutes_str) if break_minutes_str else 0
        leave_type_id = int(leave_type_id_str) if leave_type_id_str else None

        entry_service = EntryService(db)
        entry_service.save_entry(
            user_id=user.id,
            date=date,
            hours_input=hours_input if hours_input else None,
            start_time=start_time if start_time else None,
            end_time=end_time if end_time else None,
            break_minutes=break_minutes,
            notes=notes if notes else None,
            tags=tags if tags else None,
            leave_type_id=leave_type_id,
            ip_address=get_client_ip(request),
        )

        # Determine redirect
        if return_url:
            return RedirectResponse(url=return_url, status_code=303)

        iso = date.isocalendar()
        return RedirectResponse(
            url=f"/entries/week/{iso[0]}/{iso[1]}?saved={date_str}",
            status_code=303,
        )
    except (ValueError, TypeError) as exc:
        logger.error("Error saving entry: %s", exc)
        return JSONResponse(
            {"error": str(exc)}, status_code=400
        )


@router.post("/delete/{entry_id}")
async def delete_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a work entry."""
    entry_service = EntryService(db)
    success = entry_service.delete_entry(
        user.id, entry_id, ip_address=get_client_ip(request)
    )

    form = await request.form()
    return_url = form.get("return_url", "/entries/")
    return RedirectResponse(url=return_url, status_code=303)


@router.post("/quick-add")
async def quick_add(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Quick add hours for today."""
    form = await request.form()
    hours_input = form.get("hours", "")

    if not hours_input:
        return RedirectResponse(url="/", status_code=303)

    entry_service = EntryService(db)
    entry_service.save_entry(
        user_id=user.id,
        date=datetime.date.today(),
        hours_input=hours_input,
        ip_address=get_client_ip(request),
    )

    return RedirectResponse(url="/?quick_saved=1", status_code=303)


@router.post("/copy-yesterday")
async def copy_yesterday(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Copy yesterday's hours to today."""
    entry_service = EntryService(db)
    result = entry_service.copy_yesterday(user.id)

    if result:
        return RedirectResponse(url="/?copied=1", status_code=303)
    return RedirectResponse(url="/?no_yesterday=1", status_code=303)


@router.post("/duplicate-week")
async def duplicate_week(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Duplicate a week's entries to another week."""
    form = await request.form()
    source_year = int(form.get("source_year", 0))
    source_week = int(form.get("source_week", 0))
    target_year = int(form.get("target_year", 0))
    target_week = int(form.get("target_week", 0))

    entry_service = EntryService(db)
    entry_service.duplicate_week(
        user.id, source_year, source_week, target_year, target_week
    )

    return RedirectResponse(
        url=f"/entries/week/{target_year}/{target_week}?duplicated=1",
        status_code=303,
    )
