"""Settings repository — data access for UserSettings model."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.settings import DEFAULT_SETTINGS, UserSettings

logger = logging.getLogger(__name__)


class SettingsRepository:
    """Handles all database operations for user settings."""

    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: int) -> UserSettings:
        """Get settings for a user, creating defaults if they don't exist."""
        settings = (
            self.db.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )
        if settings is None:
            settings = self._create_defaults(user_id)
        return settings

    def _create_defaults(self, user_id: int) -> UserSettings:
        """Create default settings for a new user."""
        settings = UserSettings(user_id=user_id, **DEFAULT_SETTINGS)
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        logger.info("Created default settings for user_id=%d", user_id)
        return settings

    def update(self, user_id: int, **kwargs) -> UserSettings:
        """Update settings for a user. Only updates provided fields."""
        settings = self.get_for_user(user_id)
        valid_fields = {
            "weekly_target", "daily_target", "working_days",
            "lunch_deduction", "theme", "date_format", "time_format",
            "first_day_of_week", "notification_enabled",
            "notification_time", "notification_settings",
        }
        for key, value in kwargs.items():
            if key in valid_fields and value is not None:
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        logger.info("Updated settings for user_id=%d", user_id)
        return settings
