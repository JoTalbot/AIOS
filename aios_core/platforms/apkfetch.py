"""ApkFetch — автоматическое получение APK платформенного приложения.

Пайплайн bootup начинается с APK; ApkFetch снимает ручной шаг
«найди и скачай файл»: обёртка над `apkeep
<https://github.com/EFForg/apkeep>`_ — стандартным OSS-загрузчиком
(APKPure / Google Play / F-Droid без аккаунта):

.. code-block:: bash

    cargo install apkeep   # или бинарь из релизов EFForg/apkeep
    aios platforms fetch-apk com.instagram.android

Контракт как у ``inspect_apk`` (aapt): внешняя зависимость, инъецировать
``runner`` в тестах, честные ``ValueError`` при отсутствии инструмента.
Скачанные APK попадают в ``apks/`` (в ``.gitignore`` через ``*.apk``).
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Dict, Optional

DEFAULT_APK_DIR = "apks"


def _apkeep(package: str, out_dir: str, source: str) -> Dict[str, object]:
    """Реальный вызов apkeep (требует установленный apkeep)."""
    import subprocess

    result = subprocess.run(
        f"apkeep -a '{package}' -d '{source}' '{out_dir}'",
        shell=True,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return {"code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def fetch_apk(
    package: str,
    out_dir=DEFAULT_APK_DIR,
    source: str = "apkpure",
    runner=None,
) -> str:
    """Скачивает APK пакета через apkeep и возвращает путь к файлу.

    Args:
        package: Android-пакет (``com.instagram.android``).
        out_dir: Каталог назначения (создаётся).
        source: Источник apkeep (``apkpure``/``google-play``/``f-droid``).
        runner: Инъекция вызова apkeep (тесты).

    Returns:
        Путь к скачанному ``*.apk``.

    Raises:
        ValueError: apkeep недоступен/вернул ошибку, либо APK не появился.
    """
    runner = runner or _apkeep
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = runner(str(package), str(out), source)
    if result.get("code") != 0:
        raise ValueError(
            "apkeep failed (install: cargo install apkeep; sources: "
            "apkpure/google-play/f-droid): "
            f"{(result.get('stderr') or 'no apkeep binary')[:200]}"
        )
    candidates = sorted(
        glob.glob(str(out / "*.apk")),
        key=os.path.getmtime,
        reverse=True,
    )
    if not candidates:
        raise ValueError(f"apkeep reported success but no .apk appeared in {out}")
    return candidates[0]


def resolve_apk(
    target: str,
    out_dir=DEFAULT_APK_DIR,
    fetch: bool = False,
    source: str = "apkpure",
    runner=None,
) -> str:
    """Резолвит вход bootup в путь APK.

    ``target`` — либо существующий ``*.apk``, либо имя пакета; пакет
    скачивается только при ``fetch=True`` (иначе честная ошибка с
    подсказкой). Файл, скачанный ранее в ``out_dir``, переиспользуется.

    Returns:
        Путь к APK.

    Raises:
        ValueError: Файл не найден и загрузка не разрешена/не удалась.
    """
    if str(target).endswith(".apk"):
        if Path(target).exists():
            return str(target)
        raise ValueError(f"apk not found: {target}")
    # target — имя пакета
    for candidate in glob.glob(str(Path(out_dir) / f"{target}*.apk")):
        return candidate  # уже скачан ранее
    if not fetch:
        raise ValueError(
            f"apk for '{target}' not cached in {out_dir} — " "run with --fetch or download manually"
        )
    return fetch_apk(target, out_dir=out_dir, source=source, runner=runner)
