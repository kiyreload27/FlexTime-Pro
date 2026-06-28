"""User settings model."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base, TimestampMixin


class UserSettings(Base, TimestampMixin):
    """Per-user application settings."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    weekly_target = Column(Float, default=40.0, nullable=False)
    daily_target = Column(Float, default=8.0, nullable=False)
    working_days = Column(
        String(50), default="1,2,3,4,5", nullable=False
    )  # comma-separated ISO weekday numbers (1=Mon, 7=Sun)
    lunch_deduction = Column(Float, default=0.0, nullable=False)  # minutes
    theme = Column(String(20), default="dark", nullable=False)
    date_format = Column(String(20), default="DD/MM/YYYY", nullable=False)
    time_format = Column(String(10), default="24h", nullable=False)
    first_day_of_week = Column(Integer, default=1, nullable=False)  # 1=Monday
    notification_enabled = Column(Integer, default=0, nullable=False)
    notification_time = Column(String(5), default="17:00", nullable=False)
    notification_settings = Column(Text, default="{}", nullable=False)  # JSON

    # Relationship
    user = relationship("User", back_populates="settings")

    def get_working_days_list(self) -> list[int]:
        """Return working days as a list of ISO weekday numbers."""
        return [int(d.strip()) for d in self.working_days.split(",") if d.strip()]

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id}, weekly_target={self.weekly_target})>"


DEFAULT_SETTINGS = {
    "weekly_target": 40.0,
    "daily_target": 8.0,
    "working_days": "1,2,3,4,5",
    "lunch_deduction": 0.0,
    "theme": "dark",
    "date_format": "DD/MM/YYYY",
    "time_format": "24h",
    "first_day_of_week": 1,
    "notification_enabled": 0,
    "notification_time": "17:00",
    "notification_settings": "{}",
}
