"""Audit log model for tracking changes."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database.base import Base


class AuditLog(Base):
    """Records changes to data for audit trail."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type = Column(String(50), nullable=True)  # WorkEntry, User, Settings, etc.
    entity_id = Column(Integer, nullable=True)
    old_value = Column(Text, nullable=True)  # JSON
    new_value = Column(Text, nullable=True)  # JSON
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    from sqlalchemy.orm import relationship
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"entity_type='{self.entity_type}')>"
        )
