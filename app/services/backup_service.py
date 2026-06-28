"""Backup service — SQLite database backup management."""

import datetime
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class BackupService:
    """Handles automatic and manual database backups."""

    def __init__(self):
        self.settings = get_settings()
        self.backup_dir = self.settings.BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: Optional[str] = None) -> Path:
        """Create a backup of the SQLite database.

        Uses SQLite's online backup API for a safe, consistent backup.

        Args:
            label: Optional label for the backup file.

        Returns:
            Path to the created backup file.
        """
        db_url = self.settings.DATABASE_URL
        if not db_url.startswith("sqlite"):
            logger.warning("Backup only supported for SQLite databases")
            raise ValueError("Backup only supported for SQLite")

        db_path = db_url.replace("sqlite:///", "")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        backup_filename = f"flextime_backup_{timestamp}{suffix}.db"
        backup_path = self.backup_dir / backup_filename

        # Use SQLite backup API
        source = sqlite3.connect(db_path)
        try:
            dest = sqlite3.connect(str(backup_path))
            try:
                source.backup(dest)
                logger.info("Database backup created: %s", backup_path)
            finally:
                dest.close()
        finally:
            source.close()

        # Clean up old backups (keep last 30)
        self._cleanup_old_backups(keep=30)

        return backup_path

    def list_backups(self) -> list[dict]:
        """List all available backups."""
        backups = []
        for f in sorted(self.backup_dir.glob("flextime_backup_*.db"), reverse=True):
            stat = f.stat()
            backups.append({
                "filename": f.name,
                "path": str(f),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.datetime.fromtimestamp(stat.st_ctime),
            })
        return backups

    def _cleanup_old_backups(self, keep: int = 30) -> None:
        """Remove old backups, keeping only the most recent N."""
        backups = sorted(self.backup_dir.glob("flextime_backup_*.db"), reverse=True)
        for old_backup in backups[keep:]:
            old_backup.unlink()
            logger.info("Removed old backup: %s", old_backup.name)
