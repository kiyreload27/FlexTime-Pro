"""JSON REST API — for future mobile app and integrations."""

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.entry_repo import EntryRepository
from app.services.calculation_service import CalculationService
from app.utils.date_helpers import get_current_week

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])


@router.get("/status")
async def api_status():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


@router.get("/dashboard")
async def api_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard data as JSON."""
    calc = CalculationService(db)
    data = calc.get_dashboard_data(user.id)
    return {
        "current_week": {
            "hours_worked": data.current_week.hours_worked,
            "hours_remaining": data.current_week.hours_remaining,
            "overtime": data.current_week.overtime,
            "hours_owed": data.current_week.hours_owed,
            "target": data.current_week.target_hours,
            "difference": data.current_week.difference,
            "progress_percent": data.current_week.progress_percent,
        },
        "running_balance": data.running_balance,
        "monthly_hours": data.monthly_hours,
        "yearly_hours": data.yearly_hours,
        "avg_weekly_hours": data.avg_weekly_hours,
        "avg_daily_hours": data.avg_daily_hours,
    }


@router.get("/entries")
async def api_entries(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get work entries as JSON."""
    entry_repo = EntryRepository(db)

    if start_date and end_date:
        entries = entry_repo.get_by_date_range(
            user.id,
            datetime.date.fromisoformat(start_date),
            datetime.date.fromisoformat(end_date),
        )
    else:
        year, week = get_current_week()
        entries = entry_repo.get_by_week(user.id, year, week)

    return [
        {
            "id": e.id,
            "date": str(e.date),
            "hours_worked": e.hours_worked,
            "start_time": str(e.start_time) if e.start_time else None,
            "end_time": str(e.end_time) if e.end_time else None,
            "break_minutes": e.break_minutes,
            "notes": e.notes,
            "leave_type": e.leave_type.name if e.leave_type else None,
        }
        for e in entries
    ]


@router.get("/balance")
async def api_balance(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the current flexitime balance."""
    calc = CalculationService(db)
    return {"running_balance": calc.get_running_balance(user.id)}
