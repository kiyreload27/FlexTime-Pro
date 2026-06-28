"""Date helper functions for week/month/year calculations."""

import datetime
from typing import Tuple


def get_week_date_range(
    year: int, week: int, first_day: int = 1
) -> Tuple[datetime.date, datetime.date]:
    """Get the start and end date of an ISO week.

    Args:
        year: ISO year.
        week: ISO week number.
        first_day: ISO weekday for the first day (1=Monday).

    Returns:
        (start_date, end_date) tuple.
    """
    start = datetime.date.fromisocalendar(year, week, first_day)
    end = start + datetime.timedelta(days=6)
    return start, end


def get_current_week() -> Tuple[int, int]:
    """Get the current ISO year and week number."""
    today = datetime.date.today()
    iso = today.isocalendar()
    return iso[0], iso[1]


def get_month_date_range(
    year: int, month: int
) -> Tuple[datetime.date, datetime.date]:
    """Get the first and last date of a month."""
    start = datetime.date(year, month, 1)
    if month == 12:
        end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    return start, end


def get_year_date_range(year: int) -> Tuple[datetime.date, datetime.date]:
    """Get the first and last date of a year."""
    return datetime.date(year, 1, 1), datetime.date(year, 12, 31)


def get_weeks_in_range(
    start_date: datetime.date, end_date: datetime.date
) -> list[Tuple[int, int]]:
    """Get a list of (year, week) tuples covering a date range."""
    weeks = []
    current = start_date
    while current <= end_date:
        iso = current.isocalendar()
        week_tuple = (iso[0], iso[1])
        if not weeks or weeks[-1] != week_tuple:
            weeks.append(week_tuple)
        current += datetime.timedelta(days=7)
    return weeks


def get_working_days_in_week(
    year: int,
    week: int,
    working_days: list[int],
    first_day: int = 1,
) -> list[datetime.date]:
    """Get the working day dates for a given week.

    Args:
        year: ISO year.
        week: ISO week number.
        working_days: List of ISO weekday numbers that are working days.
        first_day: First day of the week (1=Monday).

    Returns:
        List of dates that are working days in the given week.
    """
    start = datetime.date.fromisocalendar(year, week, first_day)
    result = []
    for i in range(7):
        day = start + datetime.timedelta(days=i)
        if day.isoweekday() in working_days:
            result.append(day)
    return result


def get_calendar_grid(
    year: int, month: int, first_day: int = 1
) -> list[list[datetime.date | None]]:
    """Generate a 6-row calendar grid for a month.

    Each row is a week (7 days). Days outside the month are None.
    The grid starts on the configured first day of week.

    Args:
        year: Calendar year.
        month: Calendar month (1-12).
        first_day: ISO weekday for the first column (1=Monday, 7=Sunday).

    Returns:
        List of 6 lists, each containing 7 elements (date or None).
    """
    month_start, month_end = get_month_date_range(year, month)

    # Find the first day to show in the grid
    start_weekday = month_start.isoweekday()
    offset = (start_weekday - first_day) % 7
    grid_start = month_start - datetime.timedelta(days=offset)

    grid = []
    current = grid_start
    for _ in range(6):
        week = []
        for _ in range(7):
            if current.month == month and current.year == year:
                week.append(current)
            else:
                week.append(None)
            current += datetime.timedelta(days=1)
        grid.append(week)

    return grid


def format_date(date: datetime.date, fmt: str = "DD/MM/YYYY") -> str:
    """Format a date using the configured format string."""
    format_map = {
        "DD/MM/YYYY": "%d/%m/%Y",
        "MM/DD/YYYY": "%m/%d/%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD.MM.YYYY": "%d.%m.%Y",
    }
    py_fmt = format_map.get(fmt, "%d/%m/%Y")
    return date.strftime(py_fmt)


def format_date_range(
    start: datetime.date, end: datetime.date, fmt: str = "DD/MM/YYYY"
) -> str:
    """Format a date range as 'start – end'."""
    return f"{format_date(start, fmt)} – {format_date(end, fmt)}"


def get_previous_week(
    year: int, week: int
) -> Tuple[int, int]:
    """Get the previous ISO week."""
    date = datetime.date.fromisocalendar(year, week, 1)
    prev = date - datetime.timedelta(weeks=1)
    iso = prev.isocalendar()
    return iso[0], iso[1]


def get_next_week(year: int, week: int) -> Tuple[int, int]:
    """Get the next ISO week."""
    date = datetime.date.fromisocalendar(year, week, 1)
    nxt = date + datetime.timedelta(weeks=1)
    iso = nxt.isocalendar()
    return iso[0], iso[1]
