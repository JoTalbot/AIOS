#!/usr/bin/env python3
"""Полный аудит репозитория на hard-coded secrets.

Использует SecurityPolicy.check_for_hardcoded_secrets (regex-сканер) по всему
дереву, фильтрует очевидные плейсхолдеры/тестовые значения, маскирует находки и
пишет отчёт в data/security_secrets_scan_YYYYMMDD.md (data/ в .gitignore —
сырые значения в git не попадают, отчёт только с масками).

Exit: 0 — критичных находок нет, 1 — есть подозрительные значения.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aios_core.security.security_policy import SecurityPolicy  # noqa: E402

SCAN_EXTS = (".py", ".env", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".sh", ".md")
SKIP_DIRS = {".git", "backups", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
PLACEHOLDER_MARKERS = (
    "your-", "your_", "xxxx", "...", "os.getenv", "environ", "example", "sample",
    "dummy", "fake", "test", "placeholder", "changeme", "insert_", "none", "null",
    "redacted", "masked", "****", "abcd", "1234",
)
VALUE_RE = re.compile(r"[\'\"](.+?)[\'\"]")


def extract_value(match: str) -> str | None:
    m = VALUE_RE.search(match)
    return m.group(1) if m else None


def is_suspicious(value: str) -> bool:
    v = value.strip()
    if len(v) < 16:
        return False
    low = v.lower()
    if any(p in low for p in PLACEHOLDER_MARKERS):
        return False
    if re.fullmatch(r"[x*\'\-_=.\s]+", v, flags=re.IGNORECASE):
        return False  # маски/звёздочки из тестов
    if "{" in v or "}" in v:
        return False  # шаблоны
    return True


def mask(value: str) -> str:
    return f"{value[:4]}…{value[-4:]} (len={len(value)})" if len(value) > 12 else "***"


def main() -> int:
    scanned = 0
    findings: dict[str, list[tuple[str, str]]] = {}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(SCAN_EXTS):
                continue
            p = os.path.join(root, f)
            parts = p.split(os.sep)
            if len(parts) > 2 and parts[1] == "data":
                continue  # data/ — рантайм-ключи и бэклоги, не код
            try:
                raw = SecurityPolicy.check_for_hardcoded_secrets(p)
            except Exception:
                continue
            scanned += 1
            for match_text in raw:
                value = extract_value(match_text)
                if value and is_suspicious(value):
                    var = match_text.split("=")[0].strip()
                    findings.setdefault(p, []).append((var, mask(value)))

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_path = f"data/security_secrets_scan_{ts}.md"
    lines = [
        f"# Аудит hard-coded secrets — {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Файлов просканировано: {scanned}",
        f"- Подозрительных находок: {sum(len(v) for v in findings.values())} в {len(findings)} файлах",
        "",
    ]
    for p, items in sorted(findings.items()):
        lines.append(f"## {p}")
        for var, masked in items[:10]:
            lines.append(f"- `{var}` = {masked}")
        lines.append("")
    open(report_path, "w", encoding="utf-8").write("\n".join(lines))
    print(json.dumps({"scanned": scanned, "files_with_findings": len(findings),
                      "findings": sum(len(v) for v in findings.values()),
                      "report": report_path}, ensure_ascii=False))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
