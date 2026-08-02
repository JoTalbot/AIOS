from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from typing import List, Optional, Dict, Any
import logging
from logging import getLogger

logger = getLogger(__name__)

class SecurityContext(BaseModel):
    """
    Модель для безопасной валидации и обработки контекста безопасности.

    Attributes:
        todos: Список задач/заметок. Фильтруются для предотвращения disclosure.
        secrets: Список секретов. Автоматически маскируются в логах и ответах.
        raw_context: Исходный необработанный контекст (для внутреннего использования).
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    todos: Optional[List[str]] = None
    secrets: Optional[List[str]] = None
    raw_context: Optional[Dict[str, Any]] = None

    @field_validator('secrets')
    @classmethod
    def mask_secrets(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Маскировка секретов в выводе модели."""
        if v is None:
            return None
        return ['***' for _ in v]

    @field_validator('todos')
    @classmethod
    def filter_todos(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Фильтрация TODO-задач для предотвращения disclosure внутренних деталей."""
        if v is None:
            return None
        return [todo for todo in v if 'security_monitor' not in todo.lower()]

    @model_validator(mode='after')
    def validate_and_log(self) -> 'SecurityContext':
        """Пост-валидация и безопасное логирование."""
        if self.secrets and any(secret for secret in self.secrets if len(secret) > 4):
            logger.info("Processed security context with masked secrets")
        return self

def safe_process_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Безопасная обработка контекста безопасности с валидацией и маскировкой.

    Args:
        ctx: Входной контекст для обработки

    Returns:
        Dict[str, Any]: Валидированный и обработанный контекст

    Raises:
        ValueError: При невалидном контексте
    """
    try:
        validated = SecurityContext(**ctx, raw_context=ctx.copy())
        return validated.model_dump(exclude={'raw_context'})
    except Exception as e:
        logger.error(f"Security context processing failed: {str(e)[:100]}...", exc_info=False)
        raise ValueError("Invalid security context") from e

class SecurityMonitor:
    """
    Монитор безопасности с улучшенной обработкой контекста и защитой от disclosure.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SecurityMonitor")

    def process_security_context(self, raw_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка контекста безопасности с валидацией и безопасной фильтрацией.

        Args:
            raw_ctx: Исходный необработанный контекст

        Returns:
            Dict[str, Any]: Безопасный обработанный контекст
        """
        try:
            # Валидация входных данных
            if not isinstance(raw_ctx, dict):
                self.logger.error("Invalid context type provided")
                raise ValueError("Context must be a dictionary")

            # Безопасная обработка контекста
            safe_ctx = safe_process_context(raw_ctx)

            # Дополнительная проверка на наличие чувствительных данных
            if safe_ctx.get('secrets'):
                self.logger.warning("Security context contains secrets (masked in output)")

            return safe_ctx
        except ValueError as ve:
            self.logger.error(f"Security context validation failed: {str(ve)[:100]}...")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing security context: {str(e)[:100]}...", exc_info=False)
            raise ValueError("Failed to process security context") from e

    def check_security_issues(self, context: Dict[str, Any]) -> List[str]:
        """
        Проверка контекста на наличие потенциальных уязвимостей безопасности.

        Args:
            context: Контекст для проверки

        Returns:
            List[str]: Список найденных проблем
        """
        issues = []

        try:
            validated = SecurityContext(**context)

            # Проверка на наличие необработанных TODO
            if validated.todos and any('TODO' in todo.upper() for todo in validated.todos):
                issues.append("Found unprocessed TODO items in security context")

            # Проверка на наличие потенциальных секретов
            if validated.secrets:
                issues.append("Potential secrets detected in context (masked)")

            return issues
        except Exception as e:
            self.logger.error(f"Security check failed: {str(e)[:100]}...", exc_info=False)
            return ["Failed to perform security check"]