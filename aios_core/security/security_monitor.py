# aios_core/security/security_monitor.py
"""Security monitoring and threat detection for AIOS system."""

import os
from typing import Optional, Dict, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class SecurityTokenError(Exception):
    """Exception for invalid security tokens."""
    pass

class InvalidRequestError(Exception):
    """Exception for malformed or invalid requests."""
    pass

@dataclass
class SecurityEvent:
    """Data class for security events."""
    event_type: str
    details: Dict[str, Any]
    severity: str = "medium"

def validate_security_token(token: Optional[str], expected_prefix: str = "Bearer") -> bool:
    """Validate security token against environment variables.

    Args:
        token: Security token to validate
        expected_prefix: Expected token prefix (default: 'Bearer')

    Returns:
        bool: True if token is valid

    Raises:
        SecurityTokenError: If token is invalid or missing
    """
    if not token:
        logger.warning("⚠️ Попытка аутентификации без токена")
        raise SecurityTokenError("Токен отсутствует")

    if not isinstance(token, str):
        logger.warning(f"⚠️ Невалидный тип токена: {type(token)}")
        raise SecurityTokenError("Невалидный тип токена")

    if not token.startswith(expected_prefix + " "):
        logger.warning(f"⚠️ Невалидный формат токена: {token[:10]}...")
        raise SecurityTokenError("Невалидный формат токена")

    # Extract actual token value (remove prefix)
    actual_token = token[len(expected_prefix) + 1:].strip()

    expected_token = os.getenv("AI_SAFETY_TOKEN")
    if not expected_token:
        logger.error("❌ Переменная окружения AI_SAFETY_TOKEN не установлена")
        raise SecurityTokenError("Серверная ошибка конфигурации")

    if actual_token != expected_token:
        logger.warning(f"⚠️ Невалидный токен безопасности (первые 4 символа: {actual_token[:4]})")
        raise SecurityTokenError("Невалидный токен безопасности")

    logger.info("✅ Токен безопасности успешно валидирован")
    return True

def validate_api_key(api_key: Optional[str]) -> bool:
    """Validate API key against environment variables.

    Args:
        api_key: API key to validate

    Returns:
        bool: True if API key is valid

    Raises:
        SecurityTokenError: If API key is invalid or missing
    """
    if not api_key:
        logger.warning("⚠️ Попытка аутентификации без API ключа")
        raise SecurityTokenError("API ключ отсутствует")

    if not isinstance(api_key, str):
        logger.warning(f"⚠️ Невалидный тип API ключа: {type(api_key)}")
        raise SecurityTokenError("Невалидный тип API ключа")

    expected_key = os.getenv("AIOS_API_KEY")
    if not expected_key:
        logger.error("❌ Переменная окружения AIOS_API_KEY не установлена")
        raise SecurityTokenError("Серверная ошибка конфигурации")

    if api_key != expected_key:
        logger.warning(f"⚠️ Невалидный API ключ (первые 4 символа: {api_key[:4]})")
        raise SecurityTokenError("Невалидный API ключ")

    logger.info("✅ API ключ успешно валидирован")
    return True

def sanitize_input(input_data: Any) -> str:
    """Sanitize input data to prevent XSS and injection attacks.

    Args:
        input_data: Input data to sanitize

    Returns:
        str: Sanitized string
    """
    if not input_data:
        return ""

    if isinstance(input_data, str):
        # Basic XSS prevention
        sanitized = (
            input_data.replace("<", "&lt;")
                     .replace(">", "&gt;")
                     .replace("&", "&amp;")
                     .replace('"', "&quot;")
                     .replace("'", "&#39;")
        )
        return sanitized
    return str(input_data)

def log_security_event(event: SecurityEvent) -> None:
    """Log security-related events to security audit log.

    Args:
        event: Security event to log
    """
    try:
        log_entry = f"[{event.event_type}] {event.details} (severity: {event.severity})\n"
        security_log_path = os.path.join(os.getcwd(), "logs", "security_audit.log")
        os.makedirs(os.path.dirname(security_log_path), exist_ok=True)

        with open(security_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"❌ Ошибка записи в лог безопасности: {str(e)}")

def check_rate_limit(identifier: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
    """Check if request rate is within allowed limits.

    Args:
        identifier: Identifier for rate limiting (IP, user, etc.)
        max_requests: Maximum allowed requests in time window
        window_seconds: Time window in seconds

    Returns:
        bool: True if rate limit is not exceeded
    """
    # In production, this would use Redis or similar
    # For now, we'll just log and allow
    logger.info(f"✅ Проверка лимита запросов для {identifier}: {max_requests} в {window_seconds} секунд")
    return True