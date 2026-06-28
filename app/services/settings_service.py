"""Settings service — manages user preferences."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.settings import UserSettings
from app.repositories.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)


class SettingsService:
    """Handles user settings management and validation."""

    VALID_THEMES = {"dark", "light"}
    VALID_DATE_FORMATS = {"DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD", "DD.MM.YYYY"}
    VALID_TIME_FORMATS = {"12h", "24h"}
    VALID_FIRST_DAYS = {1, 6, 7}  # Monday, Saturday, Sunday

    def __init__(self, db: Session):
        self.settings_repo = SettingsRepository(db)

    def get_settings(self, user_id: int) -> UserSettings:
        """Get settings for a user (creates defaults if needed)."""
        return self.settings_repo.get_for_user(user_id)

    def update_settings(self, user_id: int, **kwargs: Any) -> UserSettings:
        """Update settings with validation."""
        # Validate theme
        if "theme" in kwargs and kwargs["theme"] not in self.VALID_THEMES:
            raise ValueError(f"Invalid theme: {kwargs['theme']}")

        # Validate date format
        if "date_format" in kwargs and kwargs["date_format"] not in self.VALID_DATE_FORMATS:
            raise ValueError(f"Invalid date format: {kwargs['date_format']}")

        # Validate time format
        if "time_format" in kwargs and kwargs["time_format"] not in self.VALID_TIME_FORMATS:
            raise ValueError(f"Invalid time format: {kwargs['time_format']}")

        # Validate first day of week
        if "first_day_of_week" in kwargs:
            fd = int(kwargs["first_day_of_week"])
            if fd not in self.VALID_FIRST_DAYS:
                raise ValueError(f"Invalid first day: {fd}")
            kwargs["first_day_of_week"] = fd

        # Validate weekly target
        if "weekly_target" in kwargs:
            wt = float(kwargs["weekly_target"])
            if wt < 0 or wt > 168:  # Max hours in a week
                raise ValueError(f"Weekly target out of range: {wt}")
            kwargs["weekly_target"] = wt

        # Validate daily target
        if "daily_target" in kwargs:
            dt = float(kwargs["daily_target"])
            if dt < 0 or dt > 24:
                raise ValueError(f"Daily target out of range: {dt}")
            kwargs["daily_target"] = dt

        # Validate working days
        if "working_days" in kwargs:
            days = kwargs["working_days"]
            if isinstance(days, list):
                days = ",".join(str(d) for d in days)
            # Validate each day is 1-7
            for d in days.split(","):
                d = d.strip()
                if d and int(d) not in range(1, 8):
                    raise ValueError(f"Invalid working day: {d}")
            kwargs["working_days"] = days

        return self.settings_repo.update(user_id, **kwargs)
