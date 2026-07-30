#!/usr/bin/env python3
"""Реальная реализация skills-hygiene-audit по алгоритму из SKILL.md.

Bounded read-only сканер plaintext-секретов в инструкциях, конфигах, логах и коде.
Реализует инструкцию №51 (Secrets Hygiene). Ничего не пишет/не удаляет.

Контракт безопасности (см. SKILL.md «Контракт безопасности»):
- read_only: true
- secret_values_emitted: false  (все совпадения маскируются: первые3 + *** + последний)
- bounded: MAX_FILES, MAX_FILE_BYTES, пропуск бинарных и шумовых директорий
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Лимиты (bounded) ---
MAX_FILES = int(os.environ.get("SHA_MAX_FILES", "2000"))
MAX_FILE_BYTES = int(os.environ.get("SHA_MAX_FILE_BYTES", str(512 * 1024)))  # 512 KB
BINARY_CHECK_BYTES = 1024

# --- Scan roots по умолчанию ---
DEFAULT_ROOTS = ["/mnt/agents", "/etc/octopus"]

# --- Корректные места для секретов (allowlist) — НЕ считаются утечкой ---
DESIGNATED_STORES = {
    "/etc/octopus/secrets.env",
}
DESIGNATED_SUFFIXES = (".token", ".pem", ".key")
DESIGNATED_NAMES = {".gh_token", ".railway_token"}

# --- Шумовые/сгенерированные директории — пропускаются ---
SKIP_DIRS = {
    ".git", "__pycache__", "_reorg_backups", "_backup", "_archived_dupes",
    "_en", "node_modules", ".venv", ".pytest_cache", "archive",
}

# --- Паттерны секретов (id, regex, severity) ---
PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "critical"),
    ("github_token", re.compile(r"\b(ghp_|gho_|ghs_|ghr_)[A-Za-z0-9]{36}\b"), "high"),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "high"),
    ("aws_secret_access_key", re.compile(r"(?i)aws(.{0,20})?(secret|sk)[^\n]{0,20}([A-Za-z0-9/+=]{40})\b"), "high"),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "high"),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "high"),
    ("bearer_token_long", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{40,}\b"), "medium"),
    ("generic_long_hex_token", re.compile(r"\b[A-Fa-f0-9]{64}\b"), "medium"),
]

# --- Плейсхолдеры — НЕ считаются утечкой ---
# Плейсхолдеры: полное значение (с опциональным =) выглядит как шаблон-заглушка.
# Важно: matcher'ы привязаны к границам значения, чтобы не вырезать подстроку
# 'example' из реального токена (например AKIA...EXAMPLE).
PLACEHOLDER_FULL_RE = re.compile(
    r"^=?\s*(<[A-Z_]+>|<REDACTED>|\$\{[A-Z_]+\}|xxx+|your[_\w-]*token[_\w-]*|placeholder|changeme)\s*$",
    re.I,
)
# Низкоэнтропийное значение: одни и те же символы / очевидный пример-маркер целиком.
MIN_VALUE_LEN = 8


@dataclass
class Finding:
    pattern_id: str
    severity: str
    path: str
    line: int
    masked: str
    context_masked: str


@dataclass
class ScanResult:
    scan_roots: list[str]
    files_scanned: int = 0
    files_skipped_binary: int = 0
    files_skipped_size: int = 0
    designated_present: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    truncated_by_file_limit: bool = False

    def summary(self) -> dict[str, int]:
        s: dict[str, int] = {}
        for f in self.findings:
            s[f.severity] = s.get(f.severity, 0) + 1
        return s


def mask(value: str) -> str:
    """Маскирование: первые3 + *** + последний. Полное значение НИКОГДА не выдаётся."""
    v = value.strip()
    if len(v) <= 4:
        return "***"
    return f"{v[:3]}***{v[-1]}"


def is_placeholder_or_noise(value: str) -> bool:
    """Отсев плейсхолдеров и низкоэнтропийных значений (избегаем ложных срабатываний).

    Важно: плейсхолдер-матчер привязан к полному значению, поэтому подстрока
    'EXAMPLE' внутри валидного AWS-ключа (AKIA...EXAMPLE) НЕ вызывает отсев.
    """
    if len(value) < MIN_VALUE_LEN:
        return True
    if PLACEHOLDER_FULL_RE.match(value):
        return True
    # низкая энтропия: одни и те же символы
    if len(set(value)) <= 2:
        return True
    return False


def is_designated(path: Path) -> bool:
    """Файл является корректным хранилищем секрета — пропускается."""
    name = path.name
    if name in DESIGNATED_NAMES:
        return True
    if str(path) in DESIGNATED_STORES:
        return True
    if name.endswith(DESIGNATED_SUFFIXES):
        return True
    return False


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(BINARY_CHECK_BYTES)
        return b"\x00" in chunk
    except OSError:
        return True


def iter_scan_files(roots: list[str], max_files: int):
    """Обход scan-roots с лимитами и пропусками. Yield (path, truncated_flag)."""
    count = 0
    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        if root_path.is_file():
            if count >= max_files:
                yield root_path, True
                return
            yield root_path, False
            count += 1
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            # пропускаем шумовые директории на месте
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in sorted(filenames):
                count += 1
                if count > max_files:
                    return
                yield Path(dirpath) / fname, False


def scan_file(path: Path, result: ScanResult) -> list[Finding]:
    """Сканирование одного файла. Read-only."""
    findings: list[Finding] = []
    if is_designated(path):
        return findings
    try:
        if path.is_dir():
            return findings
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            result.files_skipped_size += 1
            return findings
        if is_binary(path):
            result.files_skipped_binary += 1
            return findings
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pid, regex, severity in PATTERNS:
            for m in regex.finditer(line):
                value = m.group(0)
                # для bearer/hex берём само значение токена
                if pid == "bearer_token_long":
                    value = m.group(0).split(None, 1)[-1] if " " in m.group(0) else m.group(0)
                if is_placeholder_or_noise(value):
                    continue
                # маскируем контекст-строку (вырезаем совпадение, заменяем на mask)
                ctx = line.strip()
                ctx_masked = regex.sub(mask(value), ctx)
                findings.append(Finding(
                    pattern_id=pid,
                    severity=severity,
                    path=str(path),
                    line=line_no,
                    masked=mask(value),
                    context_masked=ctx_masked[:160],
                ))
    return findings


def check_designated_stores() -> dict[str, bool]:
    """Наличие корректных хранилищ секретов."""
    stores = {
        "secrets.env": Path("/etc/octopus/secrets.env").exists(),
        ".gh_token": Path.home().joinpath(".gh_token").exists(),
        ".railway_token": Path.home().joinpath(".railway_token").exists(),
    }
    return stores


def run(roots: list[str], max_files: int = MAX_FILES) -> ScanResult:
    result = ScanResult(scan_roots=roots, files_scanned=0, designated_present=check_designated_stores())
    seen: set[tuple[str, str, str]] = set()
    for path, _trunc in iter_scan_files(roots, max_files):
        if not path.is_file():
            continue
        result.files_scanned += 1
        for f in scan_file(path, result):
            key = (f.pattern_id, f.path, f.masked)
            if key in seen:
                continue
            seen.add(key)
            result.findings.append(f)
    return result


def to_report(result: ScanResult) -> dict[str, Any]:
    summary = result.summary()
    has_critical_or_high = (summary.get("critical", 0) + summary.get("high", 0)) > 0
    return {
        "ok": not has_critical_or_high,
        "skill": "secrets-hygiene-audit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "read_only": True,
            "secret_values_emitted": False,
            "bounded": True,
            "max_files": MAX_FILES,
            "max_file_bytes": MAX_FILE_BYTES,
        },
        "scan": {
            "roots": result.scan_roots,
            "files_scanned": result.files_scanned,
            "files_skipped_binary": result.files_skipped_binary,
            "files_skipped_size": result.files_skipped_size,
        },
        "designated_stores_present": result.designated_present,
        "summary_by_severity": summary,
        "findings": [
            {
                "pattern": f.pattern_id,
                "severity": f.severity,
                "path": f.path,
                "line": f.line,
                "masked": f.masked,
                "context": f.context_masked,
            }
            for f in sorted(result.findings, key=lambda x: ({"critical": 0, "high": 1, "medium": 2}.get(x.severity, 3), x.path, x.line))
        ],
        "recommendation": (
            "critical/high найдены — кандидаты на ротацию и перенос в designated-хранилище (см. инструкцию №51)."
            if has_critical_or_high
            else "critical/high не найдены."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Secrets hygiene audit (bounded read-only)")
    parser.add_argument("--root", action="append", default=None, help="scan root (можно多次; default: /mnt/agents /etc/octopus)")
    parser.add_argument("--max-files", type=int, default=MAX_FILES)
    parser.add_argument("--json", action="store_true", default=True)
    args = parser.parse_args(argv)
    roots = args.root or DEFAULT_ROOTS
    result = run(roots, max_files=args.max_files)
    report = to_report(result)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
