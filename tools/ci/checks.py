import subprocess
from typing import Tuple

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