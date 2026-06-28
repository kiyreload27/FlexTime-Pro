"""Rate limiter for login attempts."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AttemptRecord:
    """Tracks login attempts for a given key."""
    attempts: list[float] = field(default_factory=list)


class RateLimiter:
    """In-memory rate limiter for login attempts.

    Tracks by IP + username combination. Blocks after max_attempts
    within the lockout window.
    """

    def __init__(self):
        settings = get_settings()
        self.max_attempts = settings.LOGIN_MAX_ATTEMPTS
        self.lockout_seconds = settings.LOGIN_LOCKOUT_MINUTES * 60
        self._records: dict[str, AttemptRecord] = defaultdict(AttemptRecord)

    def _make_key(self, ip: str, username: str) -> str:
        """Create a rate limit key from IP and username."""
        return f"{ip}:{username.lower()}"

    def is_blocked(self, ip: str, username: str) -> bool:
        """Check if further attempts are blocked."""
        key = self._make_key(ip, username)
        record = self._records.get(key)
        if record is None:
            return False

        now = time.time()
        # Clean old attempts outside the window
        record.attempts = [
            t for t in record.attempts if now - t < self.lockout_seconds
        ]

        if len(record.attempts) >= self.max_attempts:
            remaining = int(self.lockout_seconds - (now - record.attempts[0]))
            logger.warning(
                "Rate limited: ip=%s, username=%s, remaining=%ds",
                ip, username, remaining,
            )
            return True

        return False

    def record_attempt(self, ip: str, username: str) -> None:
        """Record a failed login attempt."""
        key = self._make_key(ip, username)
        self._records[key].attempts.append(time.time())

    def reset(self, ip: str, username: str) -> None:
        """Reset attempts after a successful login."""
        key = self._make_key(ip, username)
        self._records.pop(key, None)

    def get_remaining_attempts(self, ip: str, username: str) -> int:
        """Get the number of attempts remaining before lockout."""
        key = self._make_key(ip, username)
        record = self._records.get(key)
        if record is None:
            return self.max_attempts

        now = time.time()
        recent = [t for t in record.attempts if now - t < self.lockout_seconds]
        return max(0, self.max_attempts - len(recent))


# Singleton instance
rate_limiter = RateLimiter()
