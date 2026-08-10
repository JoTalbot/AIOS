#!/usr/bin/env python3
"""
AIOS Colab Farm - Cloudflare R2 хранилище для обмена файлами VPS <-> Colab

Colab загружает обученные модели / индексы / результаты скрапинга в R2,
VPS скачивает их (и наоборот). Ключи читаются из .env.

Переменные .env:
  CLOUDFLARE_R2_ACCESS_KEY_ID
  CLOUDFLARE_R2_SECRET_ACCESS_KEY
  CLOUDFLARE_R2_ENDPOINT
  CLOUDFLARE_R2_BUCKET   (если не задан, используется 'aios-colab-farm')

Использование (VPS):
    from aios_core.colab.cloud_store import CloudStore
    cs = CloudStore()
    cs.upload("data/quant/models/catboost_price_dir.cbm", "models/catboost_price_dir.cbm")
    cs.download("models/catboost_price_dir.cbm", "data/quant/models/catboost_price_dir.cbm")
    cs.list_objects("models/")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"

LOG_TAG = "[CloudStore]"

DEFAULT_BUCKET = "aios-colab-farm"


def _read_env(name: str) -> str:
    """Прочитать переменную из .env файла (значения могут быть в кавычках)."""
    if name in os.environ:
        return os.environ[name].strip().strip("'\"")
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            m = re.match(rf"{re.escape(name)}=(.*)", line)
            if m:
                return m.group(1).strip().strip("'\"")
    except Exception:
        pass
    return ""


class CloudStore:
    """Обёртка над S3-совместимым API Cloudflare R2."""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        self.access_key = access_key or _read_env("CLOUDFLARE_R2_ACCESS_KEY_ID")
        self.secret_key = secret_key or _read_env("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        self.endpoint = endpoint or _read_env("CLOUDFLARE_R2_ENDPOINT")
        self.bucket = bucket or _read_env("CLOUDFLARE_R2_BUCKET") or DEFAULT_BUCKET
        self._client = None

    @property
    def configured(self) -> bool:
        return bool(self.access_key and self.secret_key and self.endpoint)

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name="auto",
            )
        return self._client

    def upload(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> bool:
        if not self.configured:
            print(f"{LOG_TAG} R2 не сконфигурирован (нет ключей)")
            return False
        cl = self._get_client()
        extra = {"ContentType": content_type} if content_type else {}
        try:
            cl.upload_file(str(local_path), self.bucket, object_key, ExtraArgs=extra or None)
            print(f"{LOG_TAG} ✅ Uploaded {object_key} ({Path(local_path).stat().st_size} байт)")
            return True
        except Exception as e:
            print(f"{LOG_TAG} [WARN] Upload {object_key}: {e}")
            return False

    def download(self, object_key: str, local_path: str) -> bool:
        if not self.configured:
            return False
        cl = self._get_client()
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            cl.download_file(self.bucket, object_key, str(local_path))
            print(f"{LOG_TAG} ✅ Downloaded {object_key} -> {local_path}")
            return True
        except Exception as e:
            print(f"{LOG_TAG} [WARN] Download {object_key}: {e}")
            return False

    def list_objects(self, prefix: str = "") -> list[str]:
        if not self.configured:
            return []
        cl = self._get_client()
        try:
            resp = cl.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [o["Key"] for o in resp.get("Contents", [])]
        except Exception as e:
            print(f"{LOG_TAG} [WARN] List: {e}")
            return []

    def delete(self, object_key: str) -> bool:
        if not self.configured:
            return False
        cl = self._get_client()
        try:
            cl.delete_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception as e:
            print(f"{LOG_TAG} [WARN] Delete {object_key}: {e}")
            return False

    def exists(self, object_key: str) -> bool:
        return object_key in self.list_objects(object_key)


# Singleton
cloud_store = CloudStore()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="AIOS R2 CloudStore CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pu = sub.add_parser("upload"); pu.add_argument("local"); pu.add_argument("key")
    pd = sub.add_parser("download"); pd.add_argument("key"); pd.add_argument("local")
    pl = sub.add_parser("list"); pl.add_argument("--prefix", default="")
    pt = sub.add_parser("test")

    args = ap.parse_args()
    cs = CloudStore()
    if not cs.configured:
        print("R2 не сконфигурирован. Проверьте CLOUDFLARE_R2_* в .env")
        raise SystemExit(1)

    if args.cmd == "upload":
        print("upload:", cs.upload(args.local, args.key))
    elif args.cmd == "download":
        print("download:", cs.download(args.key, args.local))
    elif args.cmd == "list":
        print(cs.list_objects(args.prefix))
    elif args.cmd == "test":
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".txt"))
        tmp.write_text("aios-r2-test")
        ok = cs.upload(str(tmp), "test/hello.txt")
        print("test upload:", ok)
        print("list:", cs.list_objects("test/"))
        cs.delete("test/hello.txt")
        tmp.unlink()
