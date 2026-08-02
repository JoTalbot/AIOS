import os
from typing import Optional, Dict, Any, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict  # v2: BaseSettings переехал (pydantic-settings 2.14)
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

    # v2-стиль; extra="ignore" — иначе чужие переменные из .env валят импорт (32 ошибки)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
            ValueError: Если входные данные не являются строкой или содержат недопустимые символы

        Examples:
            >>> SecurityPolicy.sanitize_input("<script>alert('XSS')</script>")
            '&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;'
            >>> SecurityPolicy.sanitize_input("Hello & goodbye")
            'Hello &amp; goodbye'
        """
        if not isinstance(user_input, str):
            raise ValueError("User input must be a string")

        if not user_input:
            return ""

        # Дополнительная валидация на наличие потенциально опасных паттернов
        dangerous_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
            r'on\w+\s*=\s*["\'][^"\']*["\']',
            r'javascript:',
            r'vbscript:',
            r'expression\('
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous input pattern detected: {pattern}")

        return html.escape(user_input)

    @staticmethod
    def sanitize_js_input(user_input: str) -> str:
        """
        Экранирует пользовательский ввод для безопасного использования в JavaScript.

        Args:
            user_input: Неэкранированные пользовательские данные

        Returns:
            Экранированная строка, безопасная для использования в JS

        Raises:
            ValueError: Если входные данные не являются строкой

        Examples:
            >>> SecurityPolicy.sanitize_js_input('He said "Hello"')
            'He said \\"Hello\\"'
            >>> SecurityPolicy.sanitize_js_input("Don't worry")
            'Don\\'t worry'
        """
        if not isinstance(user_input, str):
            raise ValueError("User input must be a string")

        if not user_input:
            return ""

        # Валидация на наличие потенциально опасных паттернов
        dangerous_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
            r'on\w+\s*=\s*["\'][^"\']*["\']',
            r'javascript:',
            r'vbscript:',
            r'expression\('
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous input pattern detected: {pattern}")

        return user_input.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

    @staticmethod
    def generate_csrf_token() -> str:
        """
        Генерирует токен для защиты от CSRF атак.

        Токен генерируется с использованием cryptographically secure метода и имеет
        установленное время жизни согласно конфигурации.

        Returns:
            Сгенерированный токен

        Examples:
            >>> token = SecurityPolicy.generate_csrf_token()
            >>> isinstance(token, str)
            True
            >>> len(token) > 32
            True
        """
        if not security_policy_config.csrf_token_expiry_minutes > 0:
            raise ValueError("CSRF token expiry must be greater than 0 minutes")

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

        Examples:
            >>> SecurityPolicy.validate_csrf_token("invalid_token")
            False
            >>> valid_token = SecurityPolicy.generate_csrf_token()
            >>> SecurityPolicy.validate_csrf_token(valid_token)
            True
        """
        if not token or not isinstance(token, str):
            return False

        # Валидация формата токена (alphanumeric + подчеркивания, длина 32-64)
        pattern = r'^[a-zA-Z0-9_-]{32,64}$'
        if not re.fullmatch(pattern, token):
            return False

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

        Raises:
            ValueError: Если headers не является словарем

        Examples:
            >>> SecurityPolicy.validate_request_headers({"Origin": "https://trusted.com"})
            False
            >>> SecurityPolicy.validate_request_headers(
            ...     {"Origin": "https://trusted.com"},
            ...     allowed_domains=["trusted.com"]
            ... )
            True
        """
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary")

        if allowed_domains is None:
            allowed_domains = []

        # Валидация входных данных
        if not isinstance(allowed_domains, list):
            raise ValueError("Allowed domains must be a list")

        origin = headers.get('Origin', '') if headers else ''
        referer = headers.get('Referer', '') if headers else ''

        # Проверка Origin
        if origin:
            try:
                origin_domain = re.sub(r'^https?://', '', origin).split('/')[0]
                if origin_domain not in allowed_domains:
                    return False
            except Exception:
                return False

        # Проверка Referer
        if referer:
            try:
                referer_domain = re.sub(r'^https?://', '', referer).split('/')[0]
                if referer_domain not in allowed_domains:
                    return False
            except Exception:
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

        Использует регулярные выражения для поиска потенциальных секретов в коде.
        Не является заменой специализированным инструментам безопасности.

        Args:
            file_path: Путь к файлу для проверки

        Returns:
            Список найденных потенциальных secrets

        Raises:
            ValueError: Если file_path не является строкой или файл не существует

        Examples:
            >>> SecurityPolicy.check_for_hardcoded_secrets("aios_core/security/security_policy.py")
            []
        """
        if not isinstance(file_path, str):
            raise ValueError("File path must be a string")

        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        secrets_patterns = [
            r'password\s*=\s*[\'"][^\'"]{8,}[\'"]',  # Пароли обычно длиннее 8 символов
            r'api_key\s*=\s*[\'"][^\'"]{16,}[\'"]',  # API ключи обычно длиннее 16 символов
            r'secret\s*=\s*[\'"][^\'"]{8,}[\'"]',
            r'token\s*=\s*[\'"][^\'"]{16,}[\'"]',    # Токены обычно длиннее 16 символов
            r'key\s*=\s*[\'"][^\'"]{20,}[\'"]',
            r'pwd\s*=\s*[\'"][^\'"]{8,}[\'"]',
            r'access_key\s*=\s*[\'"][^\'"]{16,}[\'"]',
            r'private_key\s*=\s*[\'"][^\'"]{32,}[\'"]',
            r'bearer\s+token\s*=\s*[\'"][^\'"]{16,}[\'"]',
            r'auth\s*=\s*[\'"][^\'"]{8,}[\'"]'
        ]

        found_secrets = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern in secrets_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    secret = match.group(0)
                    # Фильтрация слишком коротких или очевидных false positives
                    if len(secret) > 20:
                        found_secrets.append(secret)
        except Exception as e:
            raise ValueError(f"Error reading file: {e}")

        return found_secrets