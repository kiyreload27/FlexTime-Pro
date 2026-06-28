"""Audit log repository — data access for AuditLog model."""

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditRepository:
    """Handles audit log database operations."""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        action: str,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Record an action in the audit log."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            ip_address=ip_address,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_recent(
        self, user_id: Optional[int] = None, limit: int = 50
    ) -> list[AuditLog]:
        """Get recent audit log entries."""
        query = self.db.query(AuditLog)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
