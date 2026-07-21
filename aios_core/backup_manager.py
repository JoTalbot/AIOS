"""AIOS Backup Manager"""

import shutil
import os
from datetime import datetime
from typing import Optional


class BackupManager:
    """Simple backup manager for SQLite database."""

    def __init__(self, db_path: str = "aios.sqlite"):
        self.db_path = db_path

    def create_backup(self, backup_dir: str = "backups") -> str:
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"aios_backup_{timestamp}.sqlite")
        shutil.copy2(self.db_path, backup_file)
        return backup_file

    def restore_backup(self, backup_file: str) -> bool:
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, self.db_path)
            return True
        return False

    def list_backups(self, backup_dir: str = "backups") -> list:
        if not os.path.exists(backup_dir):
            return []
        return sorted([f for f in os.listdir(backup_dir) if f.endswith(".sqlite")])