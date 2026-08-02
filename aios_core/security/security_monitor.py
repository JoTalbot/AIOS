# aios_core/security/security_monitor.py

import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def scan_security_vulnerabilities(module_path: str) -> Dict:
    """
    Сканирует модуль на наличие уязвимостей безопасности: hard-coded secrets,
    XSS и CSRF уязвимости.

    Args:
        module_path: Путь к модулю для сканирования.

    Returns:
        dict: Отчёт о найденных уязвимостях.
            {
                "hardcoded_secrets": list[str],
                "xss_vulnerabilities": list[str],
                "csrf_vulnerabilities": list[str],
                "status": "success|failed"
            }
    """
    report = {
        "hardcoded_secrets": [],
        "xss_vulnerabilities": [],
        "csrf_vulnerabilities": [],
        "status": "success"
    }

    try:
        path = Path(module_path)
        if not path.exists():
            report["status"] = "failed"
            report["error"] = f"Module path not found: {module_path}"
            return report

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Поиск hard-coded secrets
        secret_patterns = [
            (r'(?i)api[_-]?key\s*[:=]\s*[\'"]?([^\s\'";]{10,})[\'"]?', 'API ключ'),
            (r'(?i)token\s*[:=]\s*[\'"]?([^\s\'";]{10,})[\'"]?', 'Токен'),
            (r'(?i)password\s*[:=]\s*[\'"]?([^\s\'";]{4,})[\'"]?', 'Пароль'),
            (r'(?i)secret\s*[:=]\s*[\'"]?([^\s\'";]{4,})[\'"]?', 'Секрет'),
            (r'(?i)aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*[\'"]?([A-Z0-9]{20})[\'"]?', 'AWS Access Key'),
            (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*[\'"]?([a-zA-Z0-9/+]{40})[\'"]?', 'AWS Secret Key'),
            (r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----', 'Приватный ключ'),
            (r'(?i)db[_-]?user\s*[:=]\s*[\'"]?([^\s\'";]+)[\'"]?', 'Имя пользователя БД'),
            (r'(?i)db[_-]?pass\s*[:=]\s*[\'"]?([^\s\'";]+)[\'"]?', 'Пароль БД'),
        ]

        for pattern, secret_type in secret_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                secret_value = match.group(1)
                if len(secret_value) > 4:  # Игнорировать слишком короткие совпадения
                    report["hardcoded_secrets"].append(
                        f"{secret_type} обнаружен: '{secret_value[:8]}...{secret_value[-4:]}' в {module_path}"
                    )

        # 2. Поиск XSS уязвимостей
        xss_patterns = [
            r'render_template_string\(',  # Jinja2 шаблоны
            r'render_template\(',         # Flask/Jinja2
            r'safe\s*=\s*True',           # Неэкранированный вывод
            r'\{\{\s*[^}]+\s*\}\}',       # Шаблонные переменные без экранирования
            r'html\.unescape\(',          # Небезопасное разворачивание HTML
            r'Markup\(',                  # Flask Markup
            r'javascript:',               # Встроенный JavaScript
            r'on\w+\s*=',                 # Обработчики событий (onclick и т.д.)
            r'<script\b',                 # Теги <script>
        ]

        for pattern in xss_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                report["xss_vulnerabilities"].append(
                    f"Возможная XSS уязвимость (паттерн: {pattern}) в {module_path}"
                )

        # 3. Поиск CSRF уязвимостей
        csrf_patterns = [
            r'<form[^>]*>',               # Формы без CSRF токена
            r'{%\s*form\s+',              # Django формы
            r'form\.action\s*=',          # Прямое указание action
            r'csrf_token\s*=\s*False',    # Отключение CSRF защиты
            r'csrf_exempt',               # Django декоратор отключения защиты
        ]

        for pattern in csrf_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                report["csrf_vulnerabilities"].append(
                    f"Возможная CSRF уязвимость (паттерн: {pattern}) в {module_path}"
                )

        # Дополнительная проверка AST для опасных шаблонных операций
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Name) and
                        node.func.id in ['render_template', 'render_template_string']):
                        report["xss_vulnerabilities"].append(
                            f"Потенциально опасный шаблонный рендеринг в {module_path}"
                        )
        except Exception as e:
            report["xss_vulnerabilities"].append(
                f"Ошибка анализа AST в {module_path}: {str(e)}"
            )

    except Exception as e:
        report["status"] = "failed"
        report["error"] = f"Ошибка сканирования: {str(e)}"

    return report

def check_hardcoded_secrets_in_repo(repo_path: str = ".") -> Dict:
    """
    Сканирует весь репозиторий на наличие hard-coded secrets.

    Args:
        repo_path: Путь к репозиторию.

    Returns:
        dict: Отчёт о найденных секретах по модулям.
    """
    report = {
        "total_files_scanned": 0,
        "files_with_secrets": [],
        "secrets_found": 0,
        "modules": {}
    }

    repo_path_obj = Path(repo_path)
    if not repo_path_obj.exists():
        report["error"] = f"Репозиторий не найден: {repo_path}"
        return report

    # Расширения файлов для сканирования
    scan_extensions = ['.py', '.js', '.html', '.yaml', '.yml', '.json', '.env']

    for file_path in repo_path_obj.rglob('*'):
        if file_path.is_file() and file_path.suffix in scan_extensions:
            module_report = scan_security_vulnerabilities(str(file_path))
            if module_report["hardcoded_secrets"]:
                report["files_with_secrets"].append(str(file_path))
                report["secrets_found"] += len(module_report["hardcoded_secrets"])
                report["modules"][str(file_path)] = {
                    "hardcoded_secrets": module_report["hardcoded_secrets"],
                    "xss_vulnerabilities": module_report["xss_vulnerabilities"],
                    "csrf_vulnerabilities": module_report["csrf_vulnerabilities"]
                }

    report["total_files_scanned"] = len(report["modules"])
    return report