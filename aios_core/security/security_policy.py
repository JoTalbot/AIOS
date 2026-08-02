import os
from typing import Optional, Dict, Any, List
from pydantic import BaseSettings, Field
import html
import secrets
import re
from datetime import datetime, timedelta

class SecurityPolicyConfig(BaseSettings):
    """Конфигурация политики безопасности через Pydantic.

    Загружает параметры из переменных окружения с валидацией типов.
    Все поля имеют безопасные значения по умолчанию.

    Переменные окружения:
        SECURITY_POLICY_SECRET_KEY: Секретный ключ для подписи токенов (по умолчанию: случайный 64-символьный hex)
        CSRF_TOKEN_EXPIRY_MINUTES: Время жизни CSRF токена в минутах (по умолчанию: 30)
        SESSION_COOKIE_SECURE: Включить флаг Secure для сессионных cookies (по умолчанию: true)
        SESSION_COOKIE_HTTPONLY: Включить флаг HttpOnly для сессионных cookies (по умолчанию: true)
        SESSION_COOKIE_SAMESITE: Установить политику SameSite для сессионных cookies (по умолчанию: Lax)
    """
    secret_key: str = Field(
        default_factory=lambda: os.getenv('SECURITY_POLICY_SECRET_KEY', secrets.token_hex(32)),
        description="Секретный ключ для подписи токенов"
    )
    csrf_token_expiry_minutes: int = Field(
        default=int(os.getenv('CSRF_TOKEN_EXPIRY_MINUTES', '30')),
        description="Время жизни CSRF токена в минутах"
    )
    session_cookie_secure: bool = Field(
        default=os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true',
        description="Включить флаг Secure для сессионных cookies"
    )
    session_cookie_httponly: bool = Field(
        default=os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true',
        description="Включить флаг HttpOnly для сессионных cookies"
    )
    session_cookie_samesite: str = Field(
        default=os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'),
        description="Политика SameSite для сессионных cookies"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

security_policy_config = SecurityPolicyConfig()

class SecurityPolicy:
    """
    Политика безопасности для защиты от XSS, CSRF и утечек secrets.
    Обеспечивает безопасную обработку пользовательского ввода, валидацию CSRF токенов
    и защиту от несанкционированного доступа.

    Использует конфигурацию из SecurityPolicyConfig для всех параметров безопасности.

    Примеры использования:
        from aios_core.security.security_policy import SecurityPolicy

        # Защита от XSS
        user_input = "<script>alert('XSS')</script>"
        safe_input = SecurityPolicy.sanitize_input(user_input)
        print(safe_input)  # &lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;

        # Генерация и валидация CSRF токена
        token = SecurityPolicy.generate_csrf_token()
        is_valid = SecurityPolicy.validate_csrf_token(token)  # True
        is_invalid = SecurityPolicy.validate_csrf_token("invalid")  # False

        # Проверка заголовков запроса
        is_valid_request = SecurityPolicy.validate_request_headers(
            headers={"Origin": "https://trusted.com", "Referer": "https://trusted.com/page"}
        )
    """

    _csrf_tokens: Dict[str, datetime] = {}

    @staticmethod
    def sanitize_input(user_input: str) -> str:
        """
        Экранирует пользовательский ввод для защиты от XSS.

        Args:
            user_input: Неэкранированные пользовательские данные

        Returns:
            Экранированная строка, безопасная для вставки в HTML/JS

        Raises:
            ValueError: Если входные данные не являются строкой
        """
        if not isinstance(user_input, str):
            raise ValueError("User input must be a string")
        return html.escape(user_input)

    @staticmethod
    def sanitize_js_input(user_input: str) -> str:
        """
        Экранирует пользовательский ввод для безопасного использования в JavaScript.

        Args:
            user_input: Неэкранированные пользовательские данные

        Returns:
            Экранированная строка, безопасная для использования в JS
        """
        if not isinstance(user_input, str):
            raise ValueError("User input must be a string")
        return user_input.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

    @staticmethod
    def generate_csrf_token() -> str:
        """
        Генерирует токен для защиты от CSRF атак.

        Returns:
            Сгенерированный токен
        """
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(minutes=security_policy_config.csrf_token_expiry_minutes)
        SecurityPolicy._csrf_tokens[token] = expiry
        return token

    @staticmethod
    def validate_csrf_token(token: str) -> bool:
        """
        Валидирует CSRF токен с учётом времени жизни.

        Args:
            token: Пришедший токен

        Returns:
            True если токен валиден и не истёк, иначе False
        """
        if token not in SecurityPolicy._csrf_tokens:
            return False

        expiry = SecurityPolicy._csrf_tokens[token]
        if datetime.now() > expiry:
            del SecurityPolicy._csrf_tokens[token]
            return False

        del SecurityPolicy._csrf_tokens[token]
        return True

    @staticmethod
    def validate_request_headers(headers: Dict[str, str], allowed_domains: Optional[list[str]] = None) -> bool:
        """
        Валидирует заголовки запроса для защиты от CSRF.

        Args:
            headers: Словарь заголовков запроса
            allowed_domains: Список разрешённых доменов (по умолчанию: None)

        Returns:
            True если запрос валиден, иначе False
        """
        if allowed_domains is None:
            allowed_domains = []

        origin = headers.get('Origin', '')
        referer = headers.get('Referer', '')

        # Проверка Origin
        if origin:
            origin_domain = re.sub(r'^https?://', '', origin).split('/')[0]
            if origin_domain not in allowed_domains:
                return False

        # Проверка Referer
        if referer:
            referer_domain = re.sub(r'^https?://', '', referer).split('/')[0]
            if referer_domain not in allowed_domains:
                return False

        return True

    @staticmethod
    def get_session_cookie_attributes() -> Dict[str, Any]:
        """
        Возвращает безопасные атрибуты для сессионных cookies.

        Returns:
            Словарь с атрибутами cookies
        """
        return {
            'secure': security_policy_config.session_cookie_secure,
            'httponly': security_policy_config.session_cookie_httponly,
            'samesite': security_policy_config.session_cookie_samesite
        }

    @staticmethod
    def check_for_hardcoded_secrets(file_path: str) -> list[str]:
        """
        Проверяет файл на наличие hard-coded secrets.

        Args:
            file_path: Путь к файлу для проверки

        Returns:
            Список найденных потенциальных secrets
        """
        secrets_patterns = [
            r'password\s*=\s*[\'"].+?[\'"]',
            r'api_key\s*=\s*[\'"].+?[\'"]',
            r'secret\s*=\s*[\'"].+?[\'"]',
            r'token\s*=\s*[\'"].+?[\'"]',
            r'key\s*=\s*[\'"].{20,}[\'"]',
            r'pwd\s*=\s*[\'"].+?[\'"]',
            r'access_key\s*=\s*[\'"].+?[\'"]',
            r'private_key\s*=\s*[\'"].+?[\'"]'
        ]

        found_secrets = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern in secrets_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    found_secrets.append(match.group(0))
        except Exception:
            pass

        return found_secrets