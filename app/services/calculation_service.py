"""Calculation service — the core flexitime calculation engine.

This service answers the primary questions:
- How many hours have I worked this week?
- How many hours do I still need to work?
- How many overtime hours have I earned?
- How many hours do I owe?
- What is my overall flexitime balance?
"""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.models.settings import UserSettings
from app.models.work_entry import WorkEntry
from app.repositories.entry_repo import EntryRepository
from app.repositories.settings_repo import SettingsRepository
from app.utils.date_helpers import (
    get_current_week,
    get_month_date_range,
    get_week_date_range,
    get_weeks_in_range,
    get_year_date_range,
)

logger = logging.getLogger(__name__)


@dataclass
class WeeklySummary:
    """Summary of a single week's work."""
    year: int
    week: int
    start_date: datetime.date
    end_date: datetime.date
    hours_worked: float = 0.0
    target_hours: float = 0.0
    difference: float = 0.0
    entries: list = field(default_factory=list)

    @property
    def hours_remaining(self) -> float:
        """Hours still needed to meet the target (0 if already met)."""
        return max(0, self.target_hours - self.hours_worked)

    @property
    def overtime(self) -> float:
        """Hours worked over the target (0 if under)."""
        return max(0, self.hours_worked - self.target_hours)

    @property
    def hours_owed(self) -> float:
        """Hours under the target (0 if met or exceeded)."""
        return max(0, self.target_hours - self.hours_worked)

    @property
    def progress_percent(self) -> float:
        """Progress toward weekly target as a percentage."""
        if self.target_hours == 0:
            return 100.0
        return min(100.0, round((self.hours_worked / self.target_hours) * 100, 1))


@dataclass
class MonthlySummary:
    """Summary of a month's work."""
    year: int
    month: int
    hours_worked: float = 0.0
    target_hours: float = 0.0
    difference: float = 0.0
    working_days_count: int = 0
    entries_count: int = 0


@dataclass
class YearlySummary:
    """Summary of a year's work."""
    year: int
    hours_worked: float = 0.0
    target_hours: float = 0.0
    difference: float = 0.0
    weeks_worked: int = 0
    avg_weekly_hours: float = 0.0


@dataclass
class DashboardData:
    """All data needed to render the dashboard."""
    # Current week
    current_week: WeeklySummary
    # Running balance
    running_balance: float = 0.0
    # Monthly
    monthly_hours: float = 0.0
    monthly_target: float = 0.0
    # Yearly
    yearly_hours: float = 0.0
    yearly_target: float = 0.0
    # Averages
    avg_weekly_hours: float = 0.0
    avg_daily_hours: float = 0.0
    # Chart data
    weekly_chart_data: dict = field(default_factory=dict)
    monthly_chart_data: dict = field(default_factory=dict)
    balance_chart_data: dict = field(default_factory=dict)


class CalculationService:
    """Core calculation engine for flexitime tracking."""

    def __init__(self, db: Session):
        self.entry_repo = EntryRepository(db)
        self.settings_repo = SettingsRepository(db)

    def _get_prorated_target(self, start_date: datetime.date, end_date: datetime.date, settings) -> float:
        """Calculate the target for a date range using Capped Daily Accumulation.
        
        For each week that overlaps the range, we accrue `daily_target` for each day
        from the start of the week, capping at `weekly_target`.
        We only sum the target accrued on days that fall strictly within the requested date range.
        This target is only calculated up to `today` (future days contribute 0).
        """
        total_target = 0.0
        today = datetime.date.today()
        
        effective_end = end_date
        if end_date > today:
            effective_end = today
            
        if start_date > effective_end:
            return 0.0
            
        current = start_date
        while current <= effective_end:
            day_offset = (current.isoweekday() - settings.first_day_of_week) % 7
            days_passed = day_offset + 1
            
            target_up_to_today = min(settings.weekly_target, days_passed * settings.daily_target)
            target_up_to_yesterday = min(settings.weekly_target, (days_passed - 1) * settings.daily_target)
            
            daily_contribution = target_up_to_today - target_up_to_yesterday
            total_target += daily_contribution
            
            current += datetime.timedelta(days=1)
            
        return total_target

    def get_weekly_summary(
        self, user_id: int, year: int, week: int
    ) -> WeeklySummary:
        """Calculate the complete summary for a specific week."""
        settings = self.settings_repo.get_for_user(user_id)
        start_date, end_date = get_week_date_range(
            year, week, settings.first_day_of_week
        )

        entries = self.entry_repo.get_by_date_range(user_id, start_date, end_date)
        hours_worked = sum(e.hours_worked for e in entries)

        target = self._get_prorated_target(start_date, end_date, settings)

        summary = WeeklySummary(
            year=year,
            week=week,
            start_date=start_date,
            end_date=end_date,
            hours_worked=round(hours_worked, 2),
            target_hours=target,
            difference=round(hours_worked - target, 2),
            entries=entries,
        )
        return summary

    def get_running_balance(self, user_id: int) -> float:
        """Calculate the cumulative flexitime balance from the first entry to now.

        The running balance is the sum of (hours_worked - weekly_target)
        for every week from the user's first entry to the current week.
        """
        settings = self.settings_repo.get_for_user(user_id)
        first_date = self.entry_repo.get_first_entry_date(user_id)

        if first_date is None:
            return 0.0

        today = datetime.date.today()

        today = datetime.date.today()

        # Calculate total worked hours
        all_entries = self.entry_repo.get_all(user_id)
        hours_worked = sum(e.hours_worked for e in all_entries if e.date <= today)

        # Calculate target up to today
        target = self._get_prorated_target(first_date, today, settings)
        
        total_balance = hours_worked - target

        return round(total_balance, 2)

    def get_monthly_summary(
        self, user_id: int, year: int, month: int
    ) -> MonthlySummary:
        """Calculate the summary for a specific month."""
        settings = self.settings_repo.get_for_user(user_id)
        start_date, end_date = get_month_date_range(year, month)
        entries = self.entry_repo.get_by_date_range(user_id, start_date, end_date)

        hours_worked = sum(e.hours_worked for e in entries)

        target = self._get_prorated_target(start_date, end_date, settings)

        # Estimate working days for the response (using a standard 5 day week for averages)
        working_days_count = len([1 for i in range((end_date - start_date).days + 1) if (start_date + datetime.timedelta(days=i)).isoweekday() <= 5])

        return MonthlySummary(
            year=year,
            month=month,
            hours_worked=round(hours_worked, 2),
            target_hours=round(target, 2),
            difference=round(hours_worked - target, 2),
            working_days_count=working_days_count,
            entries_count=len(entries),
        )

    def get_yearly_summary(self, user_id: int, year: int) -> YearlySummary:
        """Calculate the summary for a specific year."""
        settings = self.settings_repo.get_for_user(user_id)
        entries = self.entry_repo.get_by_year(user_id, year)
        hours_worked = sum(e.hours_worked for e in entries)

        # Calculate target up to today
        start_date, end_date = get_year_date_range(year)
        today = datetime.date.today()
        first_date = self.entry_repo.get_first_entry_date(user_id)
        if first_date and first_date > start_date:
            calc_start = first_date
        else:
            calc_start = start_date
            
        target = self._get_prorated_target(calc_start, end_date, settings)
        
        # Approximate weeks worked for averages
        weeks_count = round(target / settings.weekly_target, 1) if settings.weekly_target > 0 else 1
        avg_weekly = round(hours_worked / max(1, weeks_count), 2)

        return YearlySummary(
            year=year,
            hours_worked=round(hours_worked, 2),
            target_hours=round(target, 2),
            difference=round(hours_worked - target, 2),
            weeks_worked=weeks_count,
            avg_weekly_hours=avg_weekly,
        )

    def get_dashboard_data(self, user_id: int) -> DashboardData:
        """Compute all dashboard metrics in a single call."""
        today = datetime.date.today()
        current_year, current_week = get_current_week()

        # Current week
        week_summary = self.get_weekly_summary(user_id, current_year, current_week)

        # Running balance
        running_balance = self.get_running_balance(user_id)

        # Current month
        month_summary = self.get_monthly_summary(user_id, today.year, today.month)

        # Current year
        year_summary = self.get_yearly_summary(user_id, today.year)

        # Average daily hours (based on all entries ever)
        all_entries = self.entry_repo.get_all(user_id)
        total_hours = sum(e.hours_worked for e in all_entries)
        days_with_entries = len([e for e in all_entries if e.hours_worked > 0])
        avg_daily = round(total_hours / max(1, days_with_entries), 2)

        # Chart data: last 8 weeks
        weekly_chart = self._build_weekly_chart_data(user_id, current_year, current_week, 8)

        # Chart data: last 6 months
        monthly_chart = self._build_monthly_chart_data(user_id, today.year, today.month, 6)

        # Chart data: running balance over last 12 weeks
        balance_chart = self._build_balance_chart_data(user_id, current_year, current_week, 12)

        return DashboardData(
            current_week=week_summary,
            running_balance=running_balance,
            monthly_hours=month_summary.hours_worked,
            monthly_target=month_summary.target_hours,
            yearly_hours=year_summary.hours_worked,
            yearly_target=year_summary.target_hours,
            avg_weekly_hours=year_summary.avg_weekly_hours,
            avg_daily_hours=avg_daily,
            weekly_chart_data=weekly_chart,
            monthly_chart_data=monthly_chart,
            balance_chart_data=balance_chart,
        )

    def _build_weekly_chart_data(
        self, user_id: int, year: int, week: int, num_weeks: int
    ) -> dict:
        """Build chart data for the last N weeks."""
        settings = self.settings_repo.get_for_user(user_id)
        labels = []
        hours = []
        targets = []

        current_date = datetime.date.fromisocalendar(year, week, 1)
        for i in range(num_weeks - 1, -1, -1):
            d = current_date - datetime.timedelta(weeks=i)
            iso = d.isocalendar()
            start, end = get_week_date_range(iso[0], iso[1], settings.first_day_of_week)
            h = self.entry_repo.get_weekly_hours_summary(user_id, start, end)
            labels.append(f"W{iso[1]}")
            hours.append(round(h, 1))
            targets.append(settings.weekly_target)

        return {"labels": labels, "hours": hours, "targets": targets}

    def _build_monthly_chart_data(
        self, user_id: int, year: int, month: int, num_months: int
    ) -> dict:
        """Build chart data for the last N months."""
        labels = []
        hours = []
        month_names = [
            "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]

        for i in range(num_months - 1, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            summary = self.get_monthly_summary(user_id, y, m)
            labels.append(f"{month_names[m]} {y}")
            hours.append(summary.hours_worked)

        return {"labels": labels, "hours": hours}

    def _build_balance_chart_data(
        self, user_id: int, year: int, week: int, num_weeks: int
    ) -> dict:
        """Build running balance chart data over the last N weeks."""
        settings = self.settings_repo.get_for_user(user_id)
        labels = []
        balances = []

        # We need to compute running balance up to each week
        first_date = self.entry_repo.get_first_entry_date(user_id)
        if first_date is None:
            return {"labels": [], "balances": []}

        current_date = datetime.date.fromisocalendar(year, week, 1)
        cumulative = 0.0

        # Get all weeks from first entry
        all_weeks = get_weeks_in_range(first_date, current_date)
        weekly_diffs = {}

        for yr, wk in all_weeks:
            start, end = get_week_date_range(yr, wk, settings.first_day_of_week)
            h = self.entry_repo.get_weekly_hours_summary(user_id, start, end)
            
            target = self._get_prorated_target(start, end, settings)
            weekly_diffs[(yr, wk)] = h - target

        # Now build chart for last N weeks
        cumulative = sum(
            diff for (yr, wk), diff in weekly_diffs.items()
            if datetime.date.fromisocalendar(yr, wk, 1) < current_date - datetime.timedelta(weeks=num_weeks)
        )

        for i in range(num_weeks - 1, -1, -1):
            d = current_date - datetime.timedelta(weeks=i)
            iso = d.isocalendar()
            key = (iso[0], iso[1])
            if key in weekly_diffs:
                cumulative += weekly_diffs[key]
            labels.append(f"W{iso[1]}")
            balances.append(round(cumulative, 1))

        return {"labels": labels, "balances": balances}

    def get_statistics(self, user_id: int) -> dict:
        """Compute all statistics for the statistics page."""
        settings = self.settings_repo.get_for_user(user_id)
        all_entries = self.entry_repo.get_all(user_id)

        if not all_entries:
            return {
                "avg_daily_hours": 0, "avg_weekly_hours": 0, "avg_monthly_hours": 0,
                "most_overtime_month": None, "least_overtime_month": None,
                "longest_day": None, "shortest_day": None,
                "total_entries": 0, "total_hours": 0,
            }

        work_entries = [e for e in all_entries if e.hours_worked > 0]
        total_hours = sum(e.hours_worked for e in all_entries)
        days_with_work = len(work_entries)

        # Average daily
        avg_daily = round(total_hours / max(1, days_with_work), 2)

        # Average weekly (by ISO weeks)
        weeks_set = set()
        for e in all_entries:
            iso = e.date.isocalendar()
            weeks_set.add((iso[0], iso[1]))
        avg_weekly = round(total_hours / max(1, len(weeks_set)), 2)

        # Average monthly
        months_set = set()
        for e in all_entries:
            months_set.add((e.date.year, e.date.month))
        avg_monthly = round(total_hours / max(1, len(months_set)), 2)

        # Monthly overtime analysis
        monthly_diffs = {}
        for yr, mo in months_set:
            summary = self.get_monthly_summary(user_id, yr, mo)
            month_names = [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ]
            label = f"{month_names[mo]} {yr}"
            monthly_diffs[label] = summary.difference

        most_overtime = max(monthly_diffs, key=monthly_diffs.get) if monthly_diffs else None
        least_overtime = min(monthly_diffs, key=monthly_diffs.get) if monthly_diffs else None

        # Longest/shortest working day
        longest_entry = max(work_entries, key=lambda e: e.hours_worked) if work_entries else None
        shortest_entry = min(work_entries, key=lambda e: e.hours_worked) if work_entries else None

        return {
            "avg_daily_hours": avg_daily,
            "avg_weekly_hours": avg_weekly,
            "avg_monthly_hours": avg_monthly,
            "most_overtime_month": most_overtime,
            "most_overtime_value": round(monthly_diffs.get(most_overtime, 0), 2) if most_overtime else 0,
            "least_overtime_month": least_overtime,
            "least_overtime_value": round(monthly_diffs.get(least_overtime, 0), 2) if least_overtime else 0,
            "longest_day": longest_entry,
            "shortest_day": shortest_entry,
            "total_entries": len(all_entries),
            "total_hours": round(total_hours, 2),
            "total_weeks": len(weeks_set),
            "total_months": len(months_set),
        }
