# aios_core/security/security_monitor.py
"""Модуль мониторинга безопасности системы.

Отвечает за:
- Валидацию контекста TODO
- Обработку TODO-элементов в контексте безопасности
- Обнаружение и предотвращение утечек контекста
- Мониторинг безопасности обработки TODO
"""

from typing import Any, Dict, List, Optional
import re
from dataclasses import dataclass
from enum import Enum

from aios_core.code_refactorer import TodoItem as CoreTodoItem
from aios_core.task_graph_executor import TodoItem as ExecutorTodoItem

class TodoStatus(str, Enum):
    """Статусы TODO-элементов в контексте безопасности."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SECURITY_RISK = "security_risk"

@dataclass
class SecurityTodoItem:
    """Структура для безопасной обработки TODO-элементов в контексте безопасности.

    Расширяет базовый TodoItem с дополнительными полями для безопасности.
    """
    task_id: str
    description: str
    file_path: str
    status: TodoStatus
    security_level: int = 0  # Уровень критичности (0-10)
    validation_errors: List[str] = None

    def __post_init__(self) -> None:
        """Инициализация с валидацией."""
        if self.validation_errors is None:
            self.validation_errors = []
        self._validate()

    def _validate(self) -> None:
        """Валидация полей элемента TODO."""
        if not self.task_id or not isinstance(self.task_id, str):
            self.validation_errors.append("task_id должен быть непустой строкой")

        if not self.description or not isinstance(self.description, str):
            self.validation_errors.append("description должен быть непустой строкой")

        if not self.file_path or not isinstance(self.file_path, str):
            self.validation_errors.append("file_path должен быть непустой строкой")

        if self.status not in TodoStatus:
            self.validation_errors.append(f"status должен быть одним из: {list(TodoStatus)}")

        if not isinstance(self.security_level, int) or self.security_level < 0 or self.security_level > 10:
            self.validation_errors.append("security_level должен быть целым числом от 0 до 10")

    def is_valid(self) -> bool:
        """Проверка валидности элемента."""
        return len(self.validation_errors) == 0

def validate_todos_context(todos: Optional[List[Dict[str, Any]]]) -> List[SecurityTodoItem]:
    """Валидация и преобразование контекста TODO в безопасный формат.

    Args:
        todos: Список словарей с TODO-элементами или None

    Returns:
        Список безопасных SecurityTodoItem или пустой список

    Raises:
        ValueError: Если формат входных данных некорректен
    """
    if todos is None:
        return []

    if not isinstance(todos, list):
        raise ValueError("todos должен быть списком или None")

    validated_items = []

    for item in todos:
        if not isinstance(item, dict):
            continue

        try:
            # Конвертация из разных форматов в единый SecurityTodoItem
            if 'task_id' in item and 'description' in item:
                # Формат из task_graph_executor
                security_item = SecurityTodoItem(
                    task_id=str(item['task_id']),
                    description=str(item['description']),
                    file_path=str(item.get('file_path', '')),
                    status=TodoStatus(item.get('status', TodoStatus.PENDING)),
                    security_level=int(item.get('security_level', 0))
                )
            elif 'task_id' in item and 'text' in item:
                # Формат из todo_scanner
                security_item = SecurityTodoItem(
                    task_id=str(item['task_id']),
                    description=str(item['text']),
                    file_path=str(item.get('file_path', '')),
                    status=TodoStatus(item.get('status', TodoStatus.PENDING)),
                    security_level=int(item.get('security_level', 0))
                )
            else:
                # Попытка конвертации из CoreTodoItem
                core_item = CoreTodoItem(**item)
                security_item = SecurityTodoItem(
                    task_id=core_item.task_id,
                    description=core_item.description,
                    file_path=core_item.file_path,
                    status=TodoStatus(core_item.status),
                    security_level=0
                )

            if security_item.is_valid():
                validated_items.append(security_item)
            else:
                # Логирование ошибок валидации
                error_msg = f"Некорректный TODO-элемент: {security_item.validation_errors}"
                # В реальной реализации здесь должен быть логгер
                print(f"⚠️ {error_msg}")

        except (TypeError, ValueError) as e:
            error_msg = f"Ошибка обработки TODO-элемента: {str(e)}"
            print(f"❌ {error_msg}")
            continue

    return validated_items

def filter_security_todos(
    todos: List[SecurityTodoItem],
    file_path: Optional[str] = None,
    status: Optional[TodoStatus] = None,
    min_security_level: int = 0
) -> List[SecurityTodoItem]:
    """Фильтрация TODO-элементов по критериям безопасности.

    Args:
        todos: Список элементов для фильтрации
        file_path: Фильтр по пути файла (опционально)
        status: Фильтр по статусу (опционально)
        min_security_level: Минимальный уровень критичности (включительно)

    Returns:
        Отфильтрованный список элементов
    """
    if not todos:
        return []

    filtered = todos

    if file_path:
        filtered = [item for item in filtered if item.file_path == file_path]

    if status:
        filtered = [item for item in filtered if item.status == status]

    filtered = [item for item in filtered if item.security_level >= min_security_level]

    # Сортировка по уровню критичности (по убыванию)
    filtered.sort(key=lambda x: x.security_level, reverse=True)

    return filtered

def sanitize_todo_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Санитизация контекста TODO для предотвращения утечек информации.

    Удаляет потенциально опасные поля и нормализует структуру.

    Args:
        context: Исходный контекст

    Returns:
        Санитизированный контекст
    """
    if not isinstance(context, dict):
        return {}

    sanitized = context.copy()

    # Удаление потенциально опасных полей
    dangerous_keys = ['password', 'token', 'secret', 'api_key', 'credentials']
    for key in list(sanitized.keys()):
        if any(danger in key.lower() for danger in dangerous_keys):
            del sanitized[key]

    # Нормализация поля todos
    if 'todos' in sanitized:
        try:
            todos = validate_todos_context(sanitized['todos'])
            sanitized['todos'] = [item.__dict__ for item in todos]
        except Exception as e:
            print(f"❌ Ошибка санитизации todos: {str(e)}")
            sanitized['todos'] = []

    # Удаление вложенных словарей с потенциально опасными данными
    for key, value in list(sanitized.items()):
        if isinstance(value, dict):
            if any(danger in k.lower() for k in value.keys() for danger in dangerous_keys):
                del sanitized[key]

    return sanitized

def check_todo_security_risks(todos: List[SecurityTodoItem]) -> Dict[str, Any]:
    """Проверка TODO-элементов на наличие потенциальных уязвимостей.

    Args:
        todos: Список элементов для проверки

    Returns:
        Словарь с результатами анализа:
        - critical_issues: Список критических проблем
        - warnings: Список предупреждений
        - stats: Статистика
    """
    if not todos:
        return {
            'critical_issues': [],
            'warnings': [],
            'stats': {'total': 0, 'critical': 0, 'warnings': 0}
        }

    critical_issues = []
    warnings = []

    for item in todos:
        if not item.is_valid():
            critical_issues.append({
                'item': item.task_id,
                'errors': item.validation_errors,
                'severity': 'critical'
            })
            continue

        # Проверка на критичные статусы
        if item.status == TodoStatus.SECURITY_RISK:
            critical_issues.append({
                'item': item.task_id,
                'description': item.description,
                'severity': 'critical'
            })

        # Проверка на высокий уровень критичности
        if item.security_level >= 8:
            warnings.append({
                'item': item.task_id,
                'level': item.security_level,
                'description': item.description,
                'severity': 'high'
            })

        # Проверка на пустые описания
        if not item.description.strip():
            warnings.append({
                'item': item.task_id,
                'error': 'Пустое описание',
                'severity': 'medium'
            })

    return {
        'critical_issues': critical_issues,
        'warnings': warnings,
        'stats': {
            'total': len(todos),
            'critical': len(critical_issues),
            'warnings': len(warnings)
        }
    }

# Устаревшая функция (заменена на новые реализации)
def old_filter_todos(todos: List[Dict[str, Any]], file_path: str) -> List[Dict[str, Any]]:
    """⚠️ УСТАРЕЛО: Используйте validate_todos_context и filter_security_todos вместо этого.

    Фильтрация TODO по пути файла (устаревшая реализация).

    Args:
        todos: Список TODO-элементов
        file_path: Путь файла для фильтрации

    Returns:
        Отфильтрованный список
    """
    return [todo for todo in todos if todo.get('file_path') == file_path]