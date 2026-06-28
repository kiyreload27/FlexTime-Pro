"""Notification service — manages reminder logic."""

import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.settings_repo import SettingsRepository
from app.services.calculation_service import CalculationService

logger = logging.getLogger(__name__)


class NotificationService:
    """Generates notification messages based on user data."""

    def __init__(self, db: Session):
        self.settings_repo = SettingsRepository(db)
        self.calc_service = CalculationService(db)

    def get_pending_notifications(self, user_id: int) -> list[dict]:
        """Check for any pending notifications for a user.

        Returns a list of notification dictionaries with 'type', 'title', 'message'.
        """
        settings = self.settings_repo.get_for_user(user_id)
        if not settings.notification_enabled:
            return []

        notifications = []

        # Check running balance
        balance = self.calc_service.get_running_balance(user_id)

        if balance >= 20:
            notifications.append({
                "type": "warning",
                "title": "High Overtime Balance",
                "message": f"Your flexitime balance is +{balance:.1f} hours. Consider taking time off.",
            })
        elif balance <= -10:
            notifications.append({
                "type": "danger",
                "title": "Negative Balance",
                "message": f"Your flexitime balance is {balance:.1f} hours. You may need to work extra.",
            })

        # Check if target reached this week
        today = datetime.date.today()
        iso = today.isocalendar()
        week_summary = self.calc_service.get_weekly_summary(user_id, iso[0], iso[1])

        if week_summary.hours_worked >= settings.weekly_target and today.isoweekday() <= 5:
            notifications.append({
                "type": "success",
                "title": "Weekly Target Reached!",
                "message": f"You've worked {week_summary.hours_worked:.1f}h this week. Target: {settings.weekly_target}h.",
            })

        return notifications
