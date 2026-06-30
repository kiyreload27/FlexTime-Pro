"""Leave type model."""

from sqlalchemy import Boolean, Column, Float, Integer, String
from sqlalchemy.orm import relationship

from app.database.base import Base, TimestampMixin


class LeaveType(Base, TimestampMixin):
    """Defines a type of leave (holiday, sick, training, etc.)."""

    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    colour = Column(String(7), default="#6B7280", nullable=False)  # hex colour
    contributes_hours = Column(Boolean, default=False, nullable=False)
    default_hours = Column(Float, default=0.0, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    work_entries = relationship("WorkEntry", back_populates="leave_type", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<LeaveType(id={self.id}, name='{self.name}')>"


# Default leave types seeded on first run
DEFAULT_LEAVE_TYPES = [
    {"name": "Normal Work", "code": "WORK", "colour": "#10B981", "contributes_hours": False, "default_hours": 0, "is_system": True, "sort_order": 0},
    {"name": "Holiday", "code": "HOLIDAY", "colour": "#6366F1", "contributes_hours": True, "default_hours": 8.0, "is_system": True, "sort_order": 1},
    {"name": "Annual Leave", "code": "ANNUAL", "colour": "#8B5CF6", "contributes_hours": True, "default_hours": 8.0, "is_system": True, "sort_order": 2},
    {"name": "Sick Leave", "code": "SICK", "colour": "#EF4444", "contributes_hours": True, "default_hours": 8.0, "is_system": True, "sort_order": 3},
    {"name": "Training", "code": "TRAINING", "colour": "#F59E0B", "contributes_hours": True, "default_hours": 8.0, "is_system": True, "sort_order": 4},
    {"name": "Bank Holiday", "code": "BANK_HOL", "colour": "#06B6D4", "contributes_hours": True, "default_hours": 8.0, "is_system": True, "sort_order": 5},
    {"name": "Work From Home", "code": "WFH", "colour": "#14B8A6", "contributes_hours": False, "default_hours": 0, "is_system": True, "sort_order": 6},
    {"name": "Unpaid Leave", "code": "UNPAID", "colour": "#9CA3AF", "contributes_hours": False, "default_hours": 0, "is_system": True, "sort_order": 7},
    {"name": "Custom", "code": "CUSTOM", "colour": "#A855F7", "contributes_hours": False, "default_hours": 0, "is_system": False, "sort_order": 8},
    {"name": "Day Off", "code": "DAY_OFF", "colour": "#94A3B8", "contributes_hours": False, "default_hours": 0, "is_system": True, "sort_order": 9},
]
