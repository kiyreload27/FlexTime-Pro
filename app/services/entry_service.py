"""Entry service — business logic for work entry CRUD operations."""

import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.leave_type import LeaveType
from app.models.work_entry import WorkEntry
from app.repositories.audit_repo import AuditRepository
from app.repositories.entry_repo import EntryRepository
from app.repositories.settings_repo import SettingsRepository
from app.utils.time_parser import ParsedTime, calculate_hours_from_times, parse_time_input

logger = logging.getLogger(__name__)


class EntryService:
    """Handles all business logic for work entries."""

    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = EntryRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.audit_repo = AuditRepository(db)

    def save_entry(
        self,
        user_id: int,
        date: datetime.date,
        hours_input: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        break_minutes: int = 0,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        leave_type_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> WorkEntry:
        """Save or update a work entry with intelligent input parsing.

        The user can provide either:
        - hours_input: A flexible string ("8", "8.5", "08:30", "08:30 - 17:00")
        - start_time + end_time: Separate start/end time strings

        The service will parse and calculate the hours automatically.
        """
        settings = self.settings_repo.get_for_user(user_id)
        parsed_start = None
        parsed_end = None
        hours_worked = 0.0

        # Handle leave types that auto-contribute hours
        if leave_type_id:
            leave_type = self.db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
            if leave_type and leave_type.contributes_hours and not hours_input and not start_time:
                hours_worked = leave_type.default_hours
                if hours_worked == 0:
                    hours_worked = settings.daily_target

        # Parse hours from flexible input
        if hours_input and hours_input.strip():
            total_break = break_minutes or int(settings.lunch_deduction)
            parsed = parse_time_input(hours_input.strip(), total_break)
            hours_worked = parsed.hours
            parsed_start = parsed.start_time
            parsed_end = parsed.end_time

        # Parse start/end times if provided separately
        elif start_time and end_time:
            try:
                st = datetime.datetime.strptime(start_time.strip(), "%H:%M").time()
                et = datetime.datetime.strptime(end_time.strip(), "%H:%M").time()
                total_break = break_minutes or int(settings.lunch_deduction)
                hours_worked = calculate_hours_from_times(st, et, total_break)
                parsed_start = st
                parsed_end = et
            except ValueError as exc:
                raise ValueError(f"Invalid time format: {exc}") from exc

        # Get old entry for audit
        old_entry = self.entry_repo.get_by_date(user_id, date)
        old_hours = old_entry.hours_worked if old_entry else None

        # Save
        entry = self.entry_repo.create_or_update(
            user_id=user_id,
            date=date,
            hours_worked=hours_worked,
            start_time=parsed_start,
            end_time=parsed_end,
            break_minutes=break_minutes,
            notes=notes,
            tags=tags,
            leave_type_id=leave_type_id,
        )

        # Audit log
        action = "UPDATE" if old_entry else "CREATE"
        self.audit_repo.log_action(
            action=action,
            user_id=user_id,
            entity_type="WorkEntry",
            entity_id=entry.id,
            old_value={"hours": old_hours} if old_hours is not None else None,
            new_value={"hours": entry.hours_worked, "date": str(date)},
            ip_address=ip_address,
        )

        return entry

    def delete_entry(
        self, user_id: int, entry_id: int, ip_address: Optional[str] = None
    ) -> bool:
        """Delete a work entry with audit logging."""
        entry = self.entry_repo.get_by_id(entry_id)
        if entry is None or entry.user_id != user_id:
            return False

        self.audit_repo.log_action(
            action="DELETE",
            user_id=user_id,
            entity_type="WorkEntry",
            entity_id=entry_id,
            old_value={
                "date": str(entry.date),
                "hours": entry.hours_worked,
                "notes": entry.notes,
            },
            ip_address=ip_address,
        )

        return self.entry_repo.delete(entry_id)

    def duplicate_week(
        self,
        user_id: int,
        source_year: int,
        source_week: int,
        target_year: int,
        target_week: int,
    ) -> list[WorkEntry]:
        """Copy all entries from one week to another."""
        settings = self.settings_repo.get_for_user(user_id)
        source_entries = self.entry_repo.get_by_week(
            user_id, source_year, source_week, settings.first_day_of_week
        )

        if not source_entries:
            return []

        source_start = datetime.date.fromisocalendar(
            source_year, source_week, settings.first_day_of_week
        )
        target_start = datetime.date.fromisocalendar(
            target_year, target_week, settings.first_day_of_week
        )

        created = []
        for entry in source_entries:
            day_offset = (entry.date - source_start).days
            target_date = target_start + datetime.timedelta(days=day_offset)

            new_entry = self.entry_repo.create_or_update(
                user_id=user_id,
                date=target_date,
                hours_worked=entry.hours_worked,
                start_time=entry.start_time,
                end_time=entry.end_time,
                break_minutes=entry.break_minutes,
                notes=entry.notes,
                tags=entry.tags,
                leave_type_id=entry.leave_type_id,
            )
            created.append(new_entry)

        logger.info(
            "Duplicated week %d/%d → %d/%d (%d entries)",
            source_year, source_week, target_year, target_week, len(created),
        )
        return created

    def copy_yesterday(self, user_id: int) -> Optional[WorkEntry]:
        """Copy yesterday's entry to today."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        yesterday_entry = self.entry_repo.get_by_date(user_id, yesterday)
        if yesterday_entry is None:
            return None

        return self.entry_repo.create_or_update(
            user_id=user_id,
            date=today,
            hours_worked=yesterday_entry.hours_worked,
            start_time=yesterday_entry.start_time,
            end_time=yesterday_entry.end_time,
            break_minutes=yesterday_entry.break_minutes,
            notes=yesterday_entry.notes,
            leave_type_id=yesterday_entry.leave_type_id,
        )
