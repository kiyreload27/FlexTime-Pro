"""Intelligent time input parser.

Supports these formats:
    8        → 8.0 hours
    8.5      → 8.5 hours
    8,5      → 8.5 hours (European decimal)
    08:30    → 8.5 hours (as duration)
    8h30m    → 8.5 hours
    8h 30m   → 8.5 hours
    08:30 - 17:00  → calculated from start/end
    08:30-17:00    → calculated from start/end
"""

import datetime
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedTime:
    """Result of parsing a time input string."""
    hours: float
    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None
    break_minutes: Optional[int] = None


def parse_time_input(
    value: str, break_minutes: int = 0
) -> ParsedTime:
    """Parse a flexible time input string into hours.

    Args:
        value: The user's time input string.
        break_minutes: Minutes to deduct for breaks (only for start-end ranges).

    Returns:
        ParsedTime with calculated hours and optional start/end times.

    Raises:
        ValueError: If the input cannot be parsed.
    """
    if not value or not value.strip():
        raise ValueError("Empty time input")

    value = value.strip()

    # Try each parser in order of specificity
    for parser in [
        _parse_range,
        _parse_hours_minutes_notation,
        _parse_hhmm_duration,
        _parse_decimal,
    ]:
        result = parser(value, break_minutes)
        if result is not None:
            return result

    raise ValueError(f"Cannot parse time input: '{value}'")


def _parse_range(value: str, break_minutes: int) -> Optional[ParsedTime]:
    """Parse '08:30 - 17:00' or multiple ranges like '09:00-13:00, 16:00-20:00' format."""
    parts = [p.strip() for p in value.split(",")]
    pattern = r"^(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})$"
    
    total_worked_minutes = 0
    global_start_minutes = None
    global_end_minutes = None
    
    for part in parts:
        match = re.match(pattern, part)
        if not match:
            return None

        start_h, start_m = int(match.group(1)), int(match.group(2))
        end_h, end_m = int(match.group(3)), int(match.group(4))

        if not (0 <= start_h <= 23 and 0 <= start_m <= 59):
            raise ValueError(f"Invalid start time: {start_h}:{start_m:02d}")
        if not (0 <= end_h <= 23 and 0 <= end_m <= 59):
            raise ValueError(f"Invalid end time: {end_h}:{end_m:02d}")

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # Handle overnight shifts for the segment
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
            
        if global_start_minutes is None or start_minutes < global_start_minutes:
            global_start_minutes = start_minutes
            
        if global_end_minutes is None or end_minutes > global_end_minutes:
            global_end_minutes = end_minutes
            
        total_worked_minutes += (end_minutes - start_minutes)

    if global_start_minutes is None:
        return None

    # Calculate break time
    # If there are multiple shifts, break time is the gap between the overall start and end, minus worked time.
    # If there's only one shift, we subtract the requested break_minutes from worked time.
    if len(parts) > 1:
        computed_break = global_end_minutes - global_start_minutes - total_worked_minutes
        if computed_break < 0:
            computed_break = 0
    else:
        computed_break = break_minutes
        total_worked_minutes -= computed_break
        if total_worked_minutes < 0:
            total_worked_minutes = 0

    hours = round(total_worked_minutes / 60, 2)
    start_time = datetime.time((global_start_minutes // 60) % 24, global_start_minutes % 60)
    end_time = datetime.time((global_end_minutes // 60) % 24, global_end_minutes % 60)
    
    return ParsedTime(
        hours=hours, 
        start_time=start_time, 
        end_time=end_time, 
        break_minutes=computed_break
    )


def _parse_hours_minutes_notation(
    value: str, break_minutes: int
) -> Optional[ParsedTime]:
    """Parse '8h30m', '8h 30m', '8h', '30m' format."""
    pattern = r"^(\d+)\s*h(?:\s*(\d+)\s*m)?$|^(\d+)\s*m$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        return None

    if match.group(3):
        # Only minutes: '30m'
        minutes = int(match.group(3))
        hours = round(minutes / 60, 2)
    else:
        h = int(match.group(1))
        m = int(match.group(2)) if match.group(2) else 0
        hours = round(h + m / 60, 2)

    return ParsedTime(hours=hours)


def _parse_hhmm_duration(
    value: str, break_minutes: int
) -> Optional[ParsedTime]:
    """Parse 'HH:MM' as a duration (not a time of day)."""
    pattern = r"^(\d{1,2}):(\d{2})$"
    match = re.match(pattern, value)
    if not match:
        return None

    h, m = int(match.group(1)), int(match.group(2))
    if m > 59:
        raise ValueError(f"Invalid minutes: {m}")

    hours = round(h + m / 60, 2)
    return ParsedTime(hours=hours)


def _parse_decimal(value: str, break_minutes: int) -> Optional[ParsedTime]:
    """Parse '8', '8.5', '8,5' as decimal hours."""
    cleaned = value.replace(",", ".")
    try:
        hours = float(cleaned)
        if hours < 0 or hours > 24:
            raise ValueError(f"Hours out of range: {hours}")
        return ParsedTime(hours=round(hours, 2))
    except ValueError:
        return None


def calculate_hours_from_times(
    start_time: datetime.time,
    end_time: datetime.time,
    break_minutes: int = 0,
) -> float:
    """Calculate working hours between two times, minus break."""
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    if end_minutes <= start_minutes:
        end_minutes += 24 * 60

    total_minutes = end_minutes - start_minutes - break_minutes
    return round(max(0, total_minutes / 60), 2)


def format_hours(hours: float) -> str:
    """Format hours as 'Xh Ym' for display."""
    if hours == 0:
        return "0h"
    h = int(hours)
    m = round((hours - h) * 60)
    if m == 0:
        return f"{h}h"
    if h == 0:
        return f"{m}m"
    return f"{h}h {m}m"


def format_balance(hours: float) -> str:
    """Format a balance with +/- sign."""
    sign = "+" if hours >= 0 else ""
    return f"{sign}{format_hours(abs(hours))}"
