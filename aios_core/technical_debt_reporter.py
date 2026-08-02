# aios_core/technical_debt_reporter.py
import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

from aios_core.logging_config import get_logger

logger = get_logger(__name__)

class DebtType(Enum):
    """Типы технического долга."""
    TODO = "TODO"
    FIXME = "FIXME"
    DEPRECATED = "DEPRECATED"
    HARDCODED_SECRET = "HARDCODED_SECRET"
    OBSOLETE_FUNCTION = "OBSOLETE_FUNCTION"

class DebtPriority(Enum):
    """Приоритеты технического долга."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class DebtItem:
    """Единица технического долга."""
    file_path: str
    line_number: int
    debt_type: DebtType
    priority: DebtPriority
    message: str
    status: str = "open"

class TechnicalDebtReporter:
    """
    Класс для сканирования и отчётности по техническому долгу в проекте.

    Пример использования:
    >>> reporter = TechnicalDebtReporter()
    >>> reporter.scan_project()
    >>> report = reporter.generate_report()
    >>> reporter.export_report()
    """

    def __init__(self, root_path: str = None):
        """
        Инициализация сканера технического долга.

        Args:
            root_path: Корневой путь проекта. По умолчанию - текущая директория.
        """
        self.root_path = Path(root_path or os.getcwd())
        self.debt_items: List[DebtItem] = []
        self._scan_patterns = {
            DebtType.TODO: re.compile(r'#\s*TODO[:]?\s*(.*)', re.IGNORECASE),
            DebtType.FIXME: re.compile(r'#\s*FIXME[:]?\s*(.*)', re.IGNORECASE),
            DebtType.DEPRECATED: re.compile(r'@deprecated', re.IGNORECASE),
            DebtType.HARDCODED_SECRET: re.compile(
                r'(password|secret|token|api_key|apiKey)\s*[:=]\s*[\'"].+?[\'"]',
                re.IGNORECASE
            ),
            DebtType.OBSOLETE_FUNCTION: re.compile(
                r'def\s+(old_|legacy_|deprecated_)',
                re.IGNORECASE
            ),
        }
        self._priority_keywords = {
            "high": ["critical", "urgent", "high priority", "todo: high"],
            "medium": ["medium", "normal", "todo", "fixme"],
            "low": ["low", "minor", "nice to have"]
        }

    def _determine_priority(self, message: str) -> DebtPriority:
        """
        Определяет приоритет технического долга на основе сообщения.

        Args:
            message: Сообщение, описывающее долг.

        Returns:
            Приоритет долга.
        """
        message_lower = message.lower()
        for priority, keywords in self._priority_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return DebtPriority(priority)
        return DebtPriority.MEDIUM

    def _scan_file(self, file_path: Path) -> List[DebtItem]:
        """
        Сканирует отдельный файл на наличие технического долга.

        Args:
            file_path: Путь к файлу для сканирования.

        Returns:
            Список найденных единиц технического долга.
        """
        items = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line_stripped = line.strip()

                    # Пропускаем пустые строки и комментарии
                    if not line_stripped or line_stripped.startswith('#') and not any(
                        pattern.search(line) for pattern in self._scan_patterns.values()
                    ):
                        continue

                    # Поиск TODO/FIXME
                    for debt_type in [DebtType.TODO, DebtType.FIXME]:
                        match = self._scan_patterns[debt_type].search(line)
                        if match:
                            message = match.group(1).strip() if match.group(1) else "Не указано"
                            priority = self._determine_priority(message)
                            items.append(DebtItem(
                                file_path=str(file_path),
                                line_number=line_num,
                                debt_type=debt_type,
                                priority=priority,
                                message=message
                            ))
                            break

                    # Поиск устаревших функций
                    if DebtType.OBSOLETE_FUNCTION.value in line_stripped.lower():
                        items.append(DebtItem(
                            file_path=str(file_path),
                            line_number=line_num,
                            debt_type=DebtType.OBSOLETE_FUNCTION,
                            priority=DebtPriority.MEDIUM,
                            message="Обнаружена устаревшая функция"
                        ))

                    # Поиск hard-coded secrets
                    if self._scan_patterns[DebtType.HARDCODED_SECRET].search(line):
                        items.append(DebtItem(
                            file_path=str(file_path),
                            line_number=line_num,
                            debt_type=DebtType.HARDCODED_SECRET,
                            priority=DebtPriority.HIGH,
                            message="Обнаружен hard-coded secret"
                        ))

                    # Поиск декораторов @deprecated
                    if DebtType.DEPRECATED.value in line_stripped.lower():
                        items.append(DebtItem(
                            file_path=str(file_path),
                            line_number=line_num,
                            debt_type=DebtType.DEPRECATED,
                            priority=DebtPriority.MEDIUM,
                            message="Обнаружен декоратор @deprecated"
                        ))

        except (UnicodeDecodeError, PermissionError) as e:
            logger.warning(f"Не удалось прочитать файл {file_path}: {e}")

        return items

    def scan_project(self) -> List[DebtItem]:
        """
        Сканирует весь проект на наличие технического долга.

        Returns:
            Список всех найденных единиц технического долга.
        """
        self.debt_items = []
        logger.info(f"Начато сканирование проекта в {self.root_path}")

        # Игнорируемые директории и файлы
        ignore_dirs = {'.git', '.venv', '__pycache__', 'venv', 'node_modules'}
        ignore_files = {'*.pyc', '*.pyo', '*.pyd'}

        for root, dirs, files in os.walk(self.root_path):
            # Удаляем игнорируемые директории
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                file_path = Path(root) / file

                # Проверяем расширение файла
                if file_path.suffix == '.py':
                    items = self._scan_file(file_path)
                    self.debt_items.extend(items)
                    if items:
                        logger.debug(f"Найдено {len(items)} единиц долга в {file_path}")

        logger.info(f"Сканирование завершено. Найдено {len(self.debt_items)} единиц технического долга.")
        return self.debt_items

    def generate_report(self) -> Dict:
        """
        Генерирует структурированный отчёт по техническому долгу.

        Returns:
            Структурированный отчёт в формате словаря.
        """
        report = {
            "metadata": {
                "project_path": str(self.root_path),
                "scan_timestamp": str(datetime.datetime.now()),
                "total_debt_items": len(self.debt_items),
            },
            "summary": {
                "by_type": {},
                "by_priority": {},
                "by_status": {"open": 0, "closed": 0}
            },
            "items": []
        }

        # Статистика по типам
        type_counts = {}
        priority_counts = {p.value: 0 for p in DebtPriority}
        status_counts = {"open": 0, "closed": 0}

        for item in self.debt_items:
            # Статистика по типам
            type_key = item.debt_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

            # Статистика по приоритету
            priority_counts[item.priority.value] += 1

            # Статистика по статусу
            status_counts[item.status] += 1

            # Формирование записи в отчёте
            report_item = {
                "file_path": item.file_path,
                "line_number": item.line_number,
                "debt_type": item.debt_type.value,
                "priority": item.priority.value,
                "message": item.message,
                "status": item.status,
                "suggested_action": self._get_suggested_action(item)
            }
            report["items"].append(report_item)

        report["summary"]["by_type"] = type_counts
        report["summary"]["by_priority"] = priority_counts
        report["summary"]["by_status"] = status_counts

        return report

    def _get_suggested_action(self, item: DebtItem) -> str:
        """
        Генерирует рекомендации по устранению долга.

        Args:
            item: Единица технического долга.

        Returns:
            Рекомендация по устранению.
        """
        actions = {
            DebtType.TODO.value: "Добавить задачу в бэклог или issue tracker",
            DebtType.FIXME.value: "Исправить проблему или добавить комментарий с объяснением",
            DebtType.DEPRECATED.value: "Заменить на современную альтернативу или удалить",
            DebtType.HARDCODED_SECRET.value: "Вынести в конфигурационный файл или переменные окружения",
            DebtType.OBSOLETE_FUNCTION.value: "Удалить или заменить на актуальную реализацию"
        }
        return actions.get(item.debt_type.value, "Проверить и принять решение по устранению")

    def export_report(self, output_path: str = None) -> str:
        """
        Экспортирует отчёт в файл JSON.

        Args:
            output_path: Путь для сохранения отчёта. По умолчанию - technical_debt_report.json в корне проекта.

        Returns:
            Абсолютный путь к сохранённому файлу.
        """
        output_path = output_path or self.root_path / "technical_debt_report.json"
        report = self.generate_report()

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"Отчёт экспортирован в {output_path}")
            return str(output_path.absolute())
        except Exception as e:
            logger.error(f"Не удалось экспортировать отчёт: {e}")
            raise

def main():
    """Основная функция для запуска сканирования и генерации отчёта."""
    import datetime

    reporter = TechnicalDebtReporter()
    reporter.scan_project()
    report_path = reporter.export_report()

    logger.info(f"Технический долг успешно проанализирован. Отчёт сохранён в {report_path}")

if __name__ == "__main__":
    import datetime
    main()