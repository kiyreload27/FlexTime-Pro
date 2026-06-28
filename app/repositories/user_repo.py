"""User repository — data access for User model."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Handles all database operations for users."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by their ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by their username (case-insensitive)."""
        return (
            self.db.query(User)
            .filter(User.username.ilike(username))
            .first()
        )

    def get_all_active(self) -> list[User]:
        """Get all active users."""
        return self.db.query(User).filter(User.is_active.is_(True)).all()

    def get_all(self) -> list[User]:
        """Get all users (active and inactive)."""
        return self.db.query(User).order_by(User.id).all()

    def create(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        is_admin: bool = False,
        force_password_change: bool = True,
    ) -> User:
        """Create a new user."""
        user = User(
            username=username,
            password_hash=password_hash,
            email=email,
            display_name=display_name or username,
            is_admin=is_admin,
            force_password_change=force_password_change,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info("Created user: %s (id=%d)", username, user.id)
        return user

    def update_password(self, user_id: int, password_hash: str) -> None:
        """Update a user's password hash."""
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = password_hash
            user.force_password_change = False
            self.db.commit()
            logger.info("Password updated for user_id=%d", user_id)

    def update_profile(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        """Update user profile fields."""
        user = self.get_by_id(user_id)
        if user:
            if display_name is not None:
                user.display_name = display_name
            if email is not None:
                user.email = email
            self.db.commit()
            self.db.refresh(user)
        return user

    def count(self) -> int:
        """Count total users."""
        return self.db.query(User).count()
