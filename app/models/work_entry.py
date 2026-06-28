"""Work entry model — the core data entity."""

from sqlalchemy import (
    Column, Date, Float, ForeignKey, Index, Integer, String, Text, Time,
)
from sqlalchemy.orm import relationship

from app.database.base import Base, TimestampMixin


class WorkEntry(Base, TimestampMixin):
    """A single day's work record for a user."""

    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    hours_worked = Column(Float, default=0.0, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    break_minutes = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    leave_type_id = Column(
        Integer, ForeignKey("leave_types.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="work_entries")
    leave_type = relationship("LeaveType", back_populates="work_entries")

    __table_args__ = (
        Index("ix_work_entries_user_date", "user_id", "date", unique=True),
        Index("ix_work_entries_user_date_range", "user_id", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkEntry(id={self.id}, user_id={self.user_id}, "
            f"date={self.date}, hours={self.hours_worked})>"
        )
