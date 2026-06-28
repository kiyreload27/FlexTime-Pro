"""Authentication service — login, password hashing, session management."""

import logging
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


class AuthService:
    """Handles user authentication and password management."""

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password.

        Returns the User if credentials are valid, None otherwise.
        """
        user = self.user_repo.get_by_username(username)
        if user is None:
            # Run hash anyway to prevent timing attacks
            pwd_context.hash("dummy")
            return None

        if not user.is_active:
            logger.warning("Login attempt for inactive user: %s", username)
            return None

        if not pwd_context.verify(password, user.password_hash):
            logger.warning("Failed login for user: %s", username)
            return None

        logger.info("Successful login for user: %s", username)
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain, hashed)

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        is_admin: bool = False,
        force_password_change: bool = True,
    ) -> User:
        """Create a new user with a hashed password."""
        password_hash = self.hash_password(password)
        return self.user_repo.create(
            username=username,
            password_hash=password_hash,
            email=email,
            display_name=display_name,
            is_admin=is_admin,
            force_password_change=force_password_change,
        )

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """Change a user's password. Returns False if current password is wrong."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            return False

        if not pwd_context.verify(current_password, user.password_hash):
            return False

        new_hash = self.hash_password(new_password)
        self.user_repo.update_password(user_id, new_hash)
        logger.info("Password changed for user_id=%d", user_id)
        return True

    def force_set_password(self, user_id: int, new_password: str) -> None:
        """Set a new password without requiring the old one (admin use)."""
        new_hash = self.hash_password(new_password)
        self.user_repo.update_password(user_id, new_hash)
