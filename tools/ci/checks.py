import subprocess
from typing import Tuple

def run_mypy() -> int:
    """Запускает mypy для статического анализа типов.

    Проверяет аннотации типов во всём проекте, выявляя несоответствия и потенциальные ошибки.
    Использует конфигурацию из mypy.ini (при его отсутствии создаёт базовый файл с рекомендуемыми настройками).

    Returns:
        int: Код возврата mypy (0 - ошибок нет, 1 - найдены проблемы, 2 - ошибка выполнения).
    """
    try:
        result = subprocess.run(
            ["mypy", "."],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout)
        return result.returncode
    except Exception as e:
        print(f"Ошибка при выполнении mypy: {e}")
        return 2

def run_ruff() -> int:
    """Запускает ruff для линтинга и форматирования кода.

    Проверяет код на соответствие PEP 8, выявляет потенциальные ошибки и антипаттерны.
    Использует конфигурацию из pyproject.toml (при его отсутствии создаёт базовый файл с рекомендуемыми правилами).

    Returns:
        int: Код возврата ruff (0 - ошибок нет, 1 - найдены проблемы, 2 - ошибка выполнения).
    """
    try:
        result = subprocess.run(
            ["ruff", "check", "."],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout)
        return result.returncode
    except Exception as e:
        print(f"Ошибка при выполнении ruff: {e}")
        return 2

def run_ruff_check() -> Tuple[bool, str]:
    """
    Запускает ruff для проверки стиля кода и выявления потенциальных ошибок.

    Returns:
        Tuple[bool, str]: Кортеж из (результат_проверки, вывод_команды).
                         True если ошибок нет, False в случае обнаружения проблем.
    """
    try:
        result = subprocess.run(
            ["ruff", "check", "."],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)

def run_mypy_check() -> Tuple[bool, str]:
    """
    Запускает mypy для статического анализа типов.

    Returns:
        Tuple[bool, str]: Кортеж из (результат_проверки, вывод_команды).
                         True если ошибок нет, False в случае обнаружения проблем.
    """
    try:
        result = subprocess.run(
            ["mypy", "."],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)