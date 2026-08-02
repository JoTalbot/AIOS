import os
from datetime import datetime
from typing import Dict, Any

def validate_api_request_security(request: Dict[str, Any]) -> bool:
    """
    Валидирует безопасность API-запроса.

    Проверяет:
    1. Отсутствие токенов в URL (GET-запросы)
    2. Использование POST-запросов с авторизацией через заголовки (Authorization: Bearer <token>)

    Args:
        request: Словарь с параметрами запроса (method, url, headers, etc.)

    Returns:
        bool: True, если запрос безопасен, иначе False
    """
    method = request.get('method', '').upper()
    url = request.get('url', '')
    headers = request.get('headers', {})

    # Проверка на наличие токена в URL (GET-запрос)
    if method == 'GET' and 'token=' in url.lower():
        log_security_violation(f"GET-запрос с токеном в URL: {url}")
        return False

    # Проверка на наличие токена в заголовках (POST-запрос)
    if method == 'POST':
        auth_header = headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            log_security_violation(f"POST-запрос без авторизации в заголовках: {url}")
            return False

    return True

def log_security_violation(message: str) -> None:
    """
    Логирует нарушение безопасности в файл `security_audit.log`.

    Args:
        message: Сообщение о нарушении безопасности
    """
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'security_audit.log')

    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"[{timestamp}] {message}\n")