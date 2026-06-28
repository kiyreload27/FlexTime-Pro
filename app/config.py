"""Application configuration via environment variables."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "FlexTime Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    SESSION_MAX_AGE: int = 86400 * 30  # 30 days
    CSRF_SECRET: str = "change-me-csrf-secret-key"

    # Database
    DATABASE_URL: str = "sqlite:///data/flextime.db"

    # Default admin user (created on first run)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme"

    # Paths
    DATA_DIR: Path = Path("data")
    BACKUP_DIR: Path = Path("data/backups")

    # Rate Limiting
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Timezone
    TZ: str = "UTC"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
