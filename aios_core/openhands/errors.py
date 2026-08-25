"""Ошибки OpenHands-контура."""


class OpenHandsError(Exception):
    """Базовая ошибка клиента OpenHands."""


class OpenHandsAuthError(OpenHandsError):
    """Отсутствует/невалиден API-ключ (401/403 или пустая конфигурация)."""


class OpenHandsAPIError(OpenHandsError):
    """HTTP-ошибка Cloud API (кроме auth)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenHandsTimeoutError(OpenHandsError):
    """Превышен таймаут ожидания (start-task или execution)."""


class OpenHandsStartError(OpenHandsError):
    """Start-task завершился неудачно (ERROR/FAILED/CANCELLED)."""
