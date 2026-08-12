import coverage
import pytest
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def scan_coverage() -> Dict[str, float]:
    """
    Сканирует покрытие тестами для всех Python-файлов в aios_core/.

    Возвращает:
        Словарь с путями файлов и процентами покрытия.
    """
    try:
        cov = coverage.Coverage(source=["aios_core"])
        cov.start()
        pytest.main(["tests/", "-q"])
        cov.stop()
        cov.save()

        # Получаем отчёт по всем файлам
        report_data = cov.report(show_missing=True, omit=["*/tests/*"])

        # Форматируем данные в словарь
        coverage_data = {}
        for filename in cov.get_data().measured_files():
            if "aios_core" in filename:
                coverage_percent = cov.report(include=f"{filename}", show_missing=False)
                coverage_data[filename] = coverage_percent

        return coverage_data
    except Exception as e:
        logger.error(f"❌ Ошибка при сканировании покрытия: {e}")
        raise

def generate_coverage_report(output_dir: str = "coverage_report") -> None:
    """
    Генерирует отчёт о покрытии тестами в формате HTML и выводит в консоль.

    Args:
        output_dir: Директория для сохранения HTML-отчёта.
    """
    try:
        logger.info("🔍 Запуск сканирования покрытия тестами...")

        # Создаём директорию для отчётов
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Сканируем покрытие
        coverage_data = scan_coverage()

        # Выводим консольный отчёт
        logger.info("📊 Отчёт о покрытии тестами:")
        total_files = len(coverage_data)
        total_coverage = sum(coverage_data.values()) / total_files if total_files > 0 else 0

        for file, coverage_percent in coverage_data.items():
            status = "✅" if coverage_percent >= 80 else "⚠️" if coverage_percent >= 50 else "❌"
            logger.info(f"  {status} {file}: {coverage_percent:.2f}%")

        logger.info(f"📈 Общее покрытие: {total_coverage:.2f}%")

        # Генерируем HTML-отчёт
        cov = coverage.Coverage()
        cov.load()
        cov.html_report(directory=output_dir)

        logger.info(f"✅ HTML-отчёт сгенерирован в {output_dir}/index.html")
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации отчёта: {e}")
        raise

def get_untested_lines() -> Dict[str, List[int]]:
    """
    Возвращает список нетестированных строк для файлов с покрытием < 100%.

    Returns:
        Словарь с путями файлов и списками номеров нетестированных строк.
    """
    try:
        cov = coverage.Coverage()
        cov.load()

        untested_lines = {}
        for filename in cov.get_data().measured_files():
            if "aios_core" not in filename:
                continue

            analysis = cov._analyze(filename)
            if analysis.numbers.n_statements > 0 and analysis.numbers.n_missing > 0:
                untested_lines[filename] = analysis.missing

        return untested_lines
    except Exception as e:
        logger.error(f"❌ Ошибка при анализе нетестированных строк: {e}")
        raise

# Интеграция с pytest
def pytest_coverage_plugin():
    """Хук для pytest, который запускает генерацию отчёта после тестов."""
    import pytest

    def pytest_sessionfinish(session, exitstatus):
        if exitstatus == 0:
            generate_coverage_report()

    pytest.main.add_hook(pytest_sessionfinish)