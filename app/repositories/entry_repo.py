"""Work entry repository — data access for WorkEntry model."""

import datetime
import logging
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.work_entry import WorkEntry

logger = logging.getLogger(__name__)


class EntryRepository:
    """Handles all database operations for work entries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, entry_id: int) -> Optional[WorkEntry]:
        """Get an entry by ID."""
        return (
            self.db.query(WorkEntry)
            .options(joinedload(WorkEntry.leave_type))
            .filter(WorkEntry.id == entry_id)
            .first()
        )

    def get_by_date(
        self, user_id: int, date: datetime.date
    ) -> Optional[WorkEntry]:
        """Get the entry for a specific user and date."""
        return (
            self.db.query(WorkEntry)
            .options(joinedload(WorkEntry.leave_type))
            .filter(
                and_(WorkEntry.user_id == user_id, WorkEntry.date == date)
            )
            .first()
        )

    def get_by_date_range(
        self,
        user_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[WorkEntry]:
        """Get all entries for a user within a date range (inclusive)."""
        return (
            self.db.query(WorkEntry)
            .options(joinedload(WorkEntry.leave_type))
            .filter(
                and_(
                    WorkEntry.user_id == user_id,
                    WorkEntry.date >= start_date,
                    WorkEntry.date <= end_date,
                )
            )
            .order_by(WorkEntry.date)
            .all()
        )

    def get_by_week(
        self, user_id: int, year: int, week: int, first_day: int = 1
    ) -> list[WorkEntry]:
        """Get all entries for a specific ISO week."""
        start_date = datetime.date.fromisocalendar(year, week, first_day)
        end_date = start_date + datetime.timedelta(days=6)
        return self.get_by_date_range(user_id, start_date, end_date)

    def get_by_month(
        self, user_id: int, year: int, month: int
    ) -> list[WorkEntry]:
        """Get all entries for a specific month."""
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        return self.get_by_date_range(user_id, start_date, end_date)

    def get_by_year(self, user_id: int, year: int) -> list[WorkEntry]:
        """Get all entries for a specific year."""
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)
        return self.get_by_date_range(user_id, start_date, end_date)

    def get_all(self, user_id: int) -> list[WorkEntry]:
        """Get all entries for a user, ordered by date."""
        return (
            self.db.query(WorkEntry)
            .options(joinedload(WorkEntry.leave_type))
            .filter(WorkEntry.user_id == user_id)
            .order_by(WorkEntry.date)
            .all()
        )

    def create_or_update(
        self,
        user_id: int,
        date: datetime.date,
        hours_worked: float = 0.0,
        start_time: Optional[datetime.time] = None,
        end_time: Optional[datetime.time] = None,
        break_minutes: int = 0,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        leave_type_id: Optional[int] = None,
    ) -> WorkEntry:
        """Create a new entry or update an existing one for the given date."""
        entry = self.get_by_date(user_id, date)

        if entry is None:
            entry = WorkEntry(
                user_id=user_id,
                date=date,
                hours_worked=hours_worked,
                start_time=start_time,
                end_time=end_time,
                break_minutes=break_minutes,
                notes=notes,
                tags=tags,
                leave_type_id=leave_type_id,
            )
            self.db.add(entry)
            logger.info("Created entry for user_id=%d, date=%s", user_id, date)
        else:
            entry.hours_worked = hours_worked
            entry.start_time = start_time
            entry.end_time = end_time
            entry.break_minutes = break_minutes
            entry.notes = notes
            entry.tags = tags
            entry.leave_type_id = leave_type_id
            logger.info("Updated entry for user_id=%d, date=%s", user_id, date)

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry_id: int) -> bool:
        """Delete an entry by ID. Returns True if deleted."""
        entry = self.get_by_id(entry_id)
        if entry:
            self.db.delete(entry)
            self.db.commit()
            logger.info("Deleted entry id=%d", entry_id)
            return True
        return False

    def search(
        self,
        user_id: int,
        query: str,
        limit: int = 50,
    ) -> list[WorkEntry]:
        """Search entries by notes or tags."""
        search_term = f"%{query}%"
        return (
            self.db.query(WorkEntry)
            .options(joinedload(WorkEntry.leave_type))
            .filter(
                and_(
                    WorkEntry.user_id == user_id,
                    (
                        WorkEntry.notes.ilike(search_term)
                        | WorkEntry.tags.ilike(search_term)
                    ),
                )
            )
            .order_by(WorkEntry.date.desc())
            .limit(limit)
            .all()
        )

    def get_first_entry_date(self, user_id: int) -> Optional[datetime.date]:
        """Get the date of the user's first entry."""
        result = (
            self.db.query(func.min(WorkEntry.date))
            .filter(WorkEntry.user_id == user_id)
            .scalar()
        )
        return result

    def get_weekly_hours_summary(
        self, user_id: int, start_date: datetime.date, end_date: datetime.date
    ) -> float:
        """Sum hours worked in a date range."""
        result = (
            self.db.query(func.coalesce(func.sum(WorkEntry.hours_worked), 0.0))
            .filter(
                and_(
                    WorkEntry.user_id == user_id,
                    WorkEntry.date >= start_date,
                    WorkEntry.date <= end_date,
                )
            )
            .scalar()
        )
        return float(result)
