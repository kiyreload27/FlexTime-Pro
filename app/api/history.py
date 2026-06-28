"""History routes — view all recorded weeks with search/filter/sort."""

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_csrf_token, set_csrf_cookie
from app.database.session import get_db
from app.models.user import User
from app.repositories.entry_repo import EntryRepository
from app.services.calculation_service import CalculationService
from app.services.settings_service import SettingsService
from app.utils.date_helpers import (
    format_date,
    format_date_range,
    get_week_date_range,
    get_weeks_in_range,
)
from app.utils.time_parser import format_balance, format_hours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/", response_class=HTMLResponse)
async def history_view(
    request: Request,
    search: Optional[str] = Query(None),
    sort: str = Query("desc"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render the history page showing all recorded weeks."""
    calc_service = CalculationService(db)
    settings_service = SettingsService(db)
    entry_repo = EntryRepository(db)

    settings = settings_service.get_settings(user.id)
    first_date = entry_repo.get_first_entry_date(user.id)

    weeks_data = []
    running_balance = 0.0

    if first_date:
        today = datetime.date.today()
        all_weeks = get_weeks_in_range(first_date, today)

        for yr, wk in all_weeks:
            summary = calc_service.get_weekly_summary(user.id, yr, wk)
            running_balance += summary.difference

            # Filter by search term
            if search:
                search_lower = search.lower()
                notes_match = any(
                    e.notes and search_lower in e.notes.lower()
                    for e in summary.entries
                )
                week_match = str(wk) in search or str(yr) in search
                if not notes_match and not week_match:
                    continue

            weeks_data.append({
                "year": yr,
                "week": wk,
                "start_date": summary.start_date,
                "end_date": summary.end_date,
                "date_range": format_date_range(
                    summary.start_date, summary.end_date, settings.date_format
                ),
                "hours_worked": summary.hours_worked,
                "target": summary.target_hours,
                "difference": summary.difference,
                "running_balance": round(running_balance, 2),
                "entries_count": len(summary.entries),
            })

    # Sort
    if sort == "desc":
        weeks_data.reverse()

    csrf_token = generate_csrf_token()
    response = request.app.state.templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
            "weeks": weeks_data,
            "search": search or "",
            "sort": sort,
            "csrf_token": csrf_token,
            "format_hours": format_hours,
            "format_balance": format_balance,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response
