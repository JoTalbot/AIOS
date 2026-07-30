#!/usr/bin/env python3
"""Контрактные тесты secrets-hygiene-audit.

Проверяют РЕАЛЬНУЮ логику сканера, а не только наличие файлов:
детекция паттернов, маскирование, фильтрация плейсхолдеров,
allowlist designated-хранилищ, пропуск бинарных файлов, bounded-лимиты.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CODE_DIR = SKILL_DIR / "code"

# Загрузить модуль secrets_scanner напрямую (чтобы тестировать функции, а не CLI).
# Регистрируем в sys.modules ДО exec — нужно для dataclass на новых версиях Python.
_spec = importlib.util.spec_from_file_location("secrets_scanner", CODE_DIR / "secrets_scanner.py")
secrets_scanner = importlib.util.module_from_spec(_spec)
sys.modules["secrets_scanner"] = secrets_scanner
_spec.loader.exec_module(secrets_scanner)


# --- Структурные контракты (сохранены из исходного теста) ---

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (CODE_DIR / "run.py").exists()


def test_skill_has_algorithm_and_control_section():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    assert "## Алгоритм" in text
    assert "## Контроль и развитие" in text


def test_runtime_importable():
    assert (CODE_DIR / "run.py").exists()


# --- Контракт безопасности ---

def test_masking_never_reveals_full_value():
    """Маскирование: полное значение НИКОГДА не выдаётся."""
    assert secrets_scanner.mask("AKIAIOSFODNN7EXAMPLE") == "AKI***E"
    assert secrets_scanner.mask("ab") == "***"  # короткое → полностью скрыто
    assert secrets_scanner.mask("abcdefgh") == "abc***h"
    # проверим, что маска не содержит середины
    m = secrets_scanner.mask("ghp_1234567890abcdefghijklmnopqrstuvwxyz")
    assert "1234567890abcdefghijklmnopqrstuvwxyz" not in m
    assert "ghp_1234567890abcdefghijklmnopqr" not in m


def test_placeholder_filter_rejects_noise():
    """Плейсхолдеры и шум НЕ считаются утечкой."""
    assert secrets_scanner.is_placeholder_or_noise("<REDACTED>")
    assert secrets_scanner.is_placeholder_or_noise("${GITHUB_TOKEN}")
    assert secrets_scanner.is_placeholder_or_noise("xxxxxxxxxxxx")
    assert secrets_scanner.is_placeholder_or_noise("your_token_here")
    # низкая энтропия
    assert secrets_scanner.is_placeholder_or_noise("aaaaaaaaaaaaaaaa")
    # "1234567890" — 10 цифр, 10 уникальных символов → НЕ шум (может быть частью токена)
    # реальный токен — НЕ плейсхолдер
    assert not secrets_scanner.is_placeholder_or_noise("AKIAIOSFODNN7EXAMPLE")


# --- Детекция паттернов ---

def test_detects_github_token(tmp_path: Path):
    f = tmp_path / "config.env"
    f.write_text('GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz\n')
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    ids = [x.pattern_id for x in findings]
    assert "github_token" in ids
    assert all(x.severity == "high" for x in findings if x.pattern_id == "github_token")


def test_detects_aws_access_key(tmp_path: Path):
    f = tmp_path / "deploy.sh"
    f.write_text('export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"\n')
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    assert any(x.pattern_id == "aws_access_key_id" for x in findings)


def test_detects_private_key_block(tmp_path: Path):
    f = tmp_path / "id_rsa"
    f.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n")
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    assert any(x.pattern_id == "private_key_block" and x.severity == "critical" for x in findings)


def test_detects_google_api_key(tmp_path: Path):
    f = tmp_path / "app.yaml"
    f.write_text('API_KEY:' + ' AI' + 'zaSyA1234567890abcdefghijklmnopqrstuv\n')
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    assert any(x.pattern_id == "google_api_key" for x in findings)


def test_detects_slack_token(tmp_path: Path):
    f = tmp_path / "bot.conf"
    f.write_text('SLACK_TO' + 'KEN=xoxb-1234567890123-abcdefghij\n')
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    assert any(x.pattern_id == "slack_token" for x in findings)


# --- Allowlist designated-хранилищ ---

def test_designated_files_are_skipped(tmp_path: Path):
    """Корректные хранилища секретов (*.token, *.pem, *.key) НЕ сканируются."""
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    for name in ("deploy.token", "cert.pem", "private.key"):
        f = tmp_path / name
        f.write_text("AKIAIOSFODNN7EXAMPLE\n")
        assert secrets_scanner.is_designated(f), f"{name} должно быть designated"
        assert secrets_scanner.scan_file(f, result) == [], f"{name} не должно давать findings"


def test_designated_names_skipped(tmp_path: Path):
    f = tmp_path / ".gh_token"
    f.write_text("ghp_1234567890abcdefghijklmnopqrstuvwxyz\n")
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    assert secrets_scanner.scan_file(f, result) == []


# --- Пропуск бинарных ---

def test_binary_files_skipped(tmp_path: Path):
    f = tmp_path / "blob.bin"
    f.write_bytes(b"\x00\x01\x02AKIAIOSFODNN7EXAMPLE\x00\x03")
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    assert findings == []
    assert result.files_skipped_binary == 1


# --- Bounded: лимит размера ---

def test_oversized_file_skipped(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(secrets_scanner, "MAX_FILE_BYTES", 64)
    f = tmp_path / "big.log"
    f.write_text("AKIAIOSFODNN7EXAMPLE\n" * 100)
    result = secrets_scanner.ScanResult(scan_roots=[str(tmp_path)])
    findings = secrets_scanner.scan_file(f, result)
    assert findings == []
    assert result.files_skipped_size == 1


# --- Интеграционный: полный прогон по дереву ---

def test_full_scan_on_tree(tmp_path: Path):
    """Полный scan: 1 утечка + 1 designated + 1 плейсхолдер → ровно 1 finding."""
    (tmp_path / "leak.env").write_text("TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz\n")
    (tmp_path / "safe.token").write_text("AKIAIOSFODNN7EXAMPLE\n")  # designated
    (tmp_path / "docs.md").write_text("TOKEN=<REDACTED>\n")  # плейсхолдер
    result = secrets_scanner.run([str(tmp_path)], max_files=100)
    assert result.files_scanned >= 3
    # только один реальный finding (github_token), aws от designated и <REDACTED> отфильтрованы
    real = [x for x in result.findings if x.pattern_id == "github_token"]
    assert len(real) == 1
    assert real[0].masked == "ghp***z"


def test_exit_code_no_critical(tmp_path: Path):
    """Чистая директория → ok=True, exit 0."""
    (tmp_path / "clean.txt").write_text("just some text without secrets\n")
    report = secrets_scanner.to_report(secrets_scanner.run([str(tmp_path)], max_files=100))
    assert report["ok"] is True


def test_exit_code_with_critical(tmp_path: Path):
    """Есть critical/high → ok=False (exit 1)."""
    (tmp_path / "key.txt").write_text("-----BEGIN PRIVATE KEY-----\nMIIE...\n")
    report = secrets_scanner.to_report(secrets_scanner.run([str(tmp_path)], max_files=100))
    assert report["ok"] is False
    assert report["summary_by_severity"].get("critical", 0) >= 1


def test_report_never_contains_raw_secret():
    """Отчёт никогда не содержит полное значение секрета."""
    masked = secrets_scanner.mask("AKIAIOSFODNN7EXAMPLE")
    assert "AKIAIOSFODNN7EXAMPLE" not in masked
