#!/usr/bin/env python3
"""
AIOS - Загрузка моделей/файлов на Google Диск через прямой Drive REST API.
Обходит rate-limit общего client_id rclone (который делится всеми пользователями).
Токен берётся из rclone конфига (gdrive remote).

Использование:
    python upload_gdrive.py --dir /root/AIOS/data/quant/models \
                            --folder "AIOS_colab_models"
"""
import json
import os
import re
import sys
import time
import uuid
import urllib.parse
import urllib.request
import urllib.error
import argparse

RCLONE_CONF = os.path.expanduser("/root/.config/rclone/rclone.conf")
FOLDER_ID_CACHE = os.path.expanduser("/root/AIOS/data/.gdrive_folder_ids.json")


def load_token():
    cfg = open(RCLONE_CONF).read()
    m = re.search(r"\[gdrive\](.*?)(?:\n\[|\Z)", cfg, re.S)
    if not m:
        raise RuntimeError("gdrive remote not found in rclone config")
    blk = m.group(1)
    t = re.search(r"token = (\{.*\})", blk)
    if not t:
        raise RuntimeError("token not found in gdrive config")
    return json.loads(t.group(1))


def api(access, method, url, body=None, headers=None, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", "Bearer " + access)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            return urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode()
            except Exception:
                pass
            # 403/429 с rate-limit или временной недоступностью -> повторить с паузой
            low = err_body.lower()
            is_rate = e.code in (429, 403) and ("ratelimit" in low or "quota" in low or "limit" in low)
            is_5xx = 500 <= e.code <= 599
            if is_rate or is_5xx:
                wait = 20 * (attempt + 1)
                print(f"  ⏳ лимит/ошибка {e.code}, ждём {wait}с...", flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {err_body[:200]}")
    raise RuntimeError("лимиты не обойдены")


def find_folder_id(access, name):
    # кэш
    cache = {}
    if os.path.exists(FOLDER_ID_CACHE):
        cache = json.load(open(FOLDER_ID_CACHE))
    if name in cache:
        return cache[name]
    q = urllib.parse.quote(
        f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    url = "https://www.googleapis.com/drive/v3/files?q=" + q + "&fields=files(id,name)"
    data = json.loads(api(access, "GET", url))
    if not data.get("files"):
        raise RuntimeError(f"папка '{name}' не найдена на диске")
    fid = data["files"][0]["id"]
    cache[name] = fid
    json.dump(cache, open(FOLDER_ID_CACHE, "w"))
    return fid


def upload_file(access, folder_id, path, fname):
    data = open(path, "rb").read()
    # есть ли файл с таким именем в папке?
    q = urllib.parse.quote(f"'{folder_id}' in parents and name = '{fname}' and trashed = false")
    url = "https://www.googleapis.com/drive/v3/files?q=" + q + "&fields=files(id)"
    files = json.loads(api(access, "GET", url)).get("files", [])
    if files:
        # обновить существующий
        file_id = files[0]["id"]
        url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
        api(access, "PATCH", url, body=data, headers={"Content-Type": "application/octet-stream"})
        return f"updated {fname} ({len(data)} Б)"
    else:
        # создать новый
        boundary = "----aios" + uuid.uuid4().hex
        meta = json.dumps({"name": fname, "parents": [folder_id]})
        body = (
            f"--{boundary}\r\nContent-Type: application/json\r\n\r\n{meta}\r\n".encode()
            + f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
            + data
            + f"\r\n--{boundary}--\r\n".encode()
        )
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id"
        api(access, "POST", url, body=body,
            headers={"Content-Type": "multipart/related; boundary=" + boundary})
        return f"created {fname} ({len(data)} Б)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="локальная папка с файлами")
    ap.add_argument("--folder", default="AIOS_colab_models", help="папка на Google Диске")
    ap.add_argument("--ext", default="", help="фильтр по расширению, напр. .cbm")
    args = ap.parse_args()

    tok = load_token()
    access = tok["access_token"]
    print(f"📦 Папка на диске: {args.folder}")
    folder_id = find_folder_id(access, args.folder)
    print(f"   folder_id={folder_id}")

    files = sorted(f for f in os.listdir(args.dir)
                   if os.path.isfile(os.path.join(args.dir, f)))
    if args.ext:
        files = [f for f in files if f.endswith(args.ext)]
    if not files:
        print("ℹ️ Файлов для загрузки нет")
        return
    print(f"Загружаю {len(files)} файлов:")
    for f in files:
        r = upload_file(access, folder_id, os.path.join(args.dir, f), f)
        print(f"  ✅ {r}", flush=True)
        time.sleep(1)  # небольшой шаг между запросами против лимитов
    print("🎉 Готово: все файлы на Google Диске")


if __name__ == "__main__":
    main()
