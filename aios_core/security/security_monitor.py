from typing import List, Dict, Any
import re
import os

class SecurityAudit:
    """
    Класс для аудита безопасности кода, выявления небезопасных GET-запросов
    с токенами в URL и других уязвимостей.
    """

    def __init__(self):
        """Инициализация паттернов для поиска уязвимостей."""
        self.vulnerable_patterns = [
            r'requests\.get\([^)]*token[^)]*\)',  # GET-запросы с токенами
            r'urllib\.request\.urlopen\([^)]*token[^)]*\)',  # urllib-запросы с токенами
            r'requests\.get\([^)]*api_key[^)]*\)',  # GET-запросы с API ключами
            r'urllib\.request\.urlopen\([^)]*api_key[^)]*\)',  # urllib-запросы с API ключами
            r'[&\?]token=',  # Токены в URL параметрах
            r'[&\?]api_key=',  # API ключи в URL параметрах
        ]

    def check_url_security(self, file_path: str) -> List[str]:
        """
        Сканирует файл на наличие небезопасных GET-запросов с токенами в URL.

        Args:
            file_path: Путь к файлу для сканирования

        Returns:
            Список найденных уязвимостей в формате строк
        """
        if not os.path.exists(file_path):
            return [f"Файл не найден: {file_path}"]

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return [f"Ошибка чтения файла {file_path}: {str(e)}"]

        issues = []
        for pattern in self.vulnerable_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                issues.append(
                    f"Найден небезопасный запрос в {file_path}: {match.group(0)}"
                )

        return issues

    def generate_security_report(self) -> Dict[str, Any]:
        """
        Генерирует отчёт о найденных уязвимостях в защищённых файлах.

        Returns:
            Словарь с отчётом о безопасности, содержащий:
            - total_issues: общее количество найденных проблем
            - issues: список всех найденных проблем
            - critical: список критических проблем
            - files_scanned: список просканированных файлов
        """
        report = {
            'total_issues': 0,
            'issues': [],
            'critical': [],
            'files_scanned': []
        }

        # Список защищённых файлов для сканирования
        protected_files = [
            'octopus_core/api_v2_batch.py',
            'aios_core/security/access_controller.py',
            'aios_core/privacy_vault_v3.py',
            'aios_core/orchestrator.py',
            'aios_core/code_refactorer.py',
        ]

        for file_path in protected_files:
            full_path = os.path.join(os.getcwd(), file_path)
            issues = self.check_url_security(full_path)
            report['files_scanned'].append(file_path)

            if issues:
                report['total_issues'] += len(issues)
                report['issues'].extend(issues)
                # Критическими считаем все найденные уязвимости в этом контексте
                report['critical'].extend(issues)

        return report

    def check_directory_security(self, directory: str) -> Dict[str, Any]:
        """
        Сканирует директорию на наличие уязвимостей.

        Args:
            directory: Путь к директории для сканирования

        Returns:
            Отчёт о безопасности аналогично generate_security_report
        """
        report = {
            'total_issues': 0,
            'issues': [],
            'critical': [],
            'files_scanned': []
        }

        if not os.path.exists(directory):
            report['issues'].append(f"Директория не найдена: {directory}")
            return report

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    issues = self.check_url_security(file_path)
                    if issues:
                        report['total_issues'] += len(issues)
                        report['issues'].extend(issues)
                        report['critical'].extend(issues)
                    report['files_scanned'].append(file_path)

        return report