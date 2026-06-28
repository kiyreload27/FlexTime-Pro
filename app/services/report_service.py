"""Report service — generates exportable reports."""

import datetime
import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.repositories.entry_repo import EntryRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.calculation_service import CalculationService
from app.utils.date_helpers import (
    format_date,
    get_month_date_range,
    get_week_date_range,
    get_year_date_range,
)
from app.utils.export import export_to_csv, export_to_excel, export_to_pdf
from app.utils.time_parser import format_balance

logger = logging.getLogger(__name__)

ReportFormat = Literal["csv", "excel", "pdf"]
ReportType = Literal["weekly", "monthly", "yearly"]


class ReportService:
    """Generates and exports reports."""

    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = EntryRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.calc_service = CalculationService(db)

    def generate_weekly_report(
        self, user_id: int, year: int, week: int, fmt: ReportFormat
    ):
        """Generate a weekly report in the requested format."""
        settings = self.settings_repo.get_for_user(user_id)
        start, end = get_week_date_range(year, week, settings.first_day_of_week)
        entries = self.entry_repo.get_by_date_range(user_id, start, end)
        summary = self.calc_service.get_weekly_summary(user_id, year, week)

        title = f"Weekly Report - Week {week}, {year}"
        subtitle = f"{format_date(start, settings.date_format)} - {format_date(end, settings.date_format)}"

        headers = ["Date", "Day", "Hours", "Start", "End", "Break (min)", "Leave", "Notes"]
        rows = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        current = start
        while current <= end:
            entry = next((e for e in entries if e.date == current), None)
            rows.append([
                format_date(current, settings.date_format),
                day_names[current.weekday()],
                entry.hours_worked if entry else "",
                entry.start_time.strftime("%H:%M") if entry and entry.start_time else "",
                entry.end_time.strftime("%H:%M") if entry and entry.end_time else "",
                entry.break_minutes if entry else "",
                entry.leave_type.name if entry and entry.leave_type else "",
                entry.notes or "" if entry else "",
            ])
            current += datetime.timedelta(days=1)

        # Summary row
        rows.append([])
        rows.append(["Total", "", summary.hours_worked, "", "", "", "", ""])
        rows.append(["Target", "", summary.target_hours, "", "", "", "", ""])
        rows.append(["Difference", "", format_balance(summary.difference), "", "", "", "", ""])

        return self._export(headers, rows, title, subtitle, fmt)

    def generate_monthly_report(
        self, user_id: int, year: int, month: int, fmt: ReportFormat
    ):
        """Generate a monthly report."""
        settings = self.settings_repo.get_for_user(user_id)
        summary = self.calc_service.get_monthly_summary(user_id, year, month)

        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        title = f"Monthly Report - {month_names[month]} {year}"

        headers = ["Week", "Date Range", "Hours Worked", "Target", "Difference"]
        rows = []

        start, end = get_month_date_range(year, month)
        current = start
        while current <= end:
            iso = current.isocalendar()
            ws = self.calc_service.get_weekly_summary(user_id, iso[0], iso[1])
            rows.append([
                f"W{iso[1]}",
                f"{format_date(ws.start_date, settings.date_format)} - {format_date(ws.end_date, settings.date_format)}",
                ws.hours_worked,
                ws.target_hours,
                format_balance(ws.difference),
            ])
            current = ws.end_date + datetime.timedelta(days=1)

        rows.append([])
        rows.append(["Total", "", summary.hours_worked, summary.target_hours, format_balance(summary.difference)])

        return self._export(headers, rows, title, "", fmt)

    def generate_yearly_report(
        self, user_id: int, year: int, fmt: ReportFormat
    ):
        """Generate a yearly report."""
        settings = self.settings_repo.get_for_user(user_id)
        title = f"Yearly Report - {year}"

        headers = ["Month", "Hours Worked", "Target", "Difference", "Running Balance"]
        rows = []
        running = 0.0
        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        for m in range(1, 13):
            summary = self.calc_service.get_monthly_summary(user_id, year, m)
            running += summary.difference
            rows.append([
                month_names[m],
                summary.hours_worked,
                summary.target_hours,
                format_balance(summary.difference),
                format_balance(running),
            ])

        year_summary = self.calc_service.get_yearly_summary(user_id, year)
        rows.append([])
        rows.append([
            "Total", year_summary.hours_worked, year_summary.target_hours,
            format_balance(year_summary.difference), format_balance(running),
        ])

        return self._export(headers, rows, title, "", fmt)

    def _export(self, headers, rows, title, subtitle, fmt: ReportFormat):
        """Export data in the requested format."""
        if fmt == "csv":
            return export_to_csv(headers, rows, title), "text/csv", f"{title}.csv"
        elif fmt == "excel":
            return (
                export_to_excel(headers, rows, title),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"{title}.xlsx",
            )
        elif fmt == "pdf":
            return (
                export_to_pdf(headers, rows, title, subtitle),
                "application/pdf",
                f"{title}.pdf",
            )
        else:
            raise ValueError(f"Unsupported format: {fmt}")
