"""
AIOS Google Drive Auto-Sync Engine (v19.0.0)
Автоматическая синхронизация бэкапов, финансовых отчетов и фото с Google Диском.
"""
from __future__ import annotations

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("AIOS.GDriveSync")

RCLONE_CONF = Path("/root/.config/rclone/rclone.conf")
VAULT_FILE = Path("/root/AIOS/data/.gdrive_token.json")


class AIOSGoogleDriveSync:
    """Управление прямой загрузкой и синхронизацией файлов с Google Диском через REST API."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        self.data_dir = Path(data_dir)
        self.token_file = VAULT_FILE
        self._load_token_data()

    def _load_token_data(self):
        """Загрузка данных токена из rclone.conf или сейфа."""
        self.token_data = {}
        if self.token_file.exists():
            try:
                self.token_data = json.loads(self.token_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if not self.token_data and RCLONE_CONF.exists():
            try:
                import configparser
                cfg = configparser.ConfigParser()
                cfg.read(str(RCLONE_CONF))
                if "gdrive" in cfg and "token" in cfg["gdrive"]:
                    self.token_data = json.loads(cfg["gdrive"]["token"])
            except Exception:
                pass

    def get_access_token(self) -> str:
        """Возвращает действующий access_token."""
        return self.token_data.get("access_token", "")

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Поиск или создание папки на Google Диске."""
        token = self.get_access_token()
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        params = urllib.parse.urlencode({"q": query, "fields": "files(id, name)"})
        url = f"https://www.googleapis.com/drive/v3/files?{params}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                files = res.get("files", [])
                if files:
                    return files[0]["id"]
        except Exception as e:
            logger.warning(f"Поиск папки {folder_name}: {e}")

        # Создаем папку если не найдена
        meta = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            meta["parents"] = [parent_id]

        create_req = urllib.request.Request(
            "https://www.googleapis.com/drive/v3/files",
            data=json.dumps(meta).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(create_req, timeout=12) as resp:
                created = json.loads(resp.read().decode("utf-8"))
                return created.get("id", "")
        except Exception as e:
            logger.error(f"Не удалось создать папку {folder_name}: {e}")
            return ""

    def upload_file(self, local_path: str, remote_folder_id: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Загрузка файла на Google Диск через Multipart REST API."""
        p = Path(local_path)
        if not p.exists():
            return {"status": "error", "error": f"Файл не найден: {local_path}"}

        name = filename or p.name
        token = self.get_access_token()

        # Определяем MIME-тип
        mime = "application/octet-stream"
        if name.endswith(".xlsx"):
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif name.endswith(".jpg") or name.endswith(".jpeg"):
            mime = "image/jpeg"
        elif name.endswith(".png"):
            mime = "image/png"
        elif name.endswith(".tar.gz") or name.endswith(".tgz"):
            mime = "application/gzip"
        elif name.endswith(".sqlite") or name.endswith(".db"):
            mime = "application/x-sqlite3"

        file_bytes = p.read_bytes()
        metadata = {
            "name": name,
            "parents": [remote_folder_id]
        }

        boundary = "-------AIOSGoogleDriveSyncBoundary" + str(int(time.time()))
        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            + json.dumps(metadata) + "\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"📤 [GDriveSync] Загружен: {name} (ID: {data.get('id')})")
                time.sleep(1.0)
                return {
                    "status": "success",
                    "file_id": data.get("id"),
                    "name": data.get("name"),
                    "size_bytes": len(file_bytes)
                }
        except Exception as e:
            logger.error(f"Ошибка загрузки {name} на Google Диск: {e}")
            return {"status": "error", "error": str(e)}

    def sync_all(self) -> Dict[str, Any]:
        """Полный цикл синхронизации: финансовые отчеты + бэкапы + фотокаталог."""
        root_folder_id = self.get_or_create_folder("AIOS_Backups")
        if not root_folder_id:
            return {"status": "error", "error": "Не удалось инициализировать корневую папку AIOS_Backups"}

        fin_folder_id = self.get_or_create_folder("Financial_Reports", root_folder_id)
        bk_folder_id = self.get_or_create_folder("Database_Backups", root_folder_id)
        photos_folder_id = self.get_or_create_folder("Photos_Catalog", root_folder_id)

        uploaded_files = []

        # 1. Финансовый отчет Excel
        report_file = Path("/root/AIOS/data/aios_financial_report.xlsx")
        if report_file.exists():
            res = self.upload_file(str(report_file), fin_folder_id)
            if res.get("status") == "success":
                uploaded_files.append({"type": "finance", "file": report_file.name, "id": res.get("file_id")})

        # 2. Свежие бэкапы SQLite
        bk_dir = Path("/root/AIOS/backups/daily")
        if bk_dir.exists():
            now = time.time()
            for f in sorted(bk_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and (now - f.stat().st_mtime) < 86400:
                    if f.name.endswith(".sqlite") or (f.name.endswith(".tar.gz") and "secrets" in f.name):
                        res = self.upload_file(str(f), bk_folder_id)
                        if res.get("status") == "success":
                            uploaded_files.append({"type": "backup", "file": f.name, "id": res.get("file_id")})

        # 3. Фотокаталог
        photos_dir = Path("/root/AIOS/data/photos")
        if photos_dir.exists():
            for p in sorted(photos_dir.glob("*.jpg")):
                res = self.upload_file(str(p), photos_folder_id)
                if res.get("status") == "success":
                    uploaded_files.append({"type": "photo", "file": p.name, "id": res.get("file_id")})

        return {
            "status": "success",
            "google_drive_folder": "AIOS_Backups",
            "folder_id": root_folder_id,
            "uploaded_count": len(uploaded_files),
            "files": uploaded_files
        }
