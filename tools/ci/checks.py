import subprocess
from typing import Tuple, List, Optional

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

def run_combined_checks() -> Tuple[bool, str]:
    """
    Запускает последовательно ruff и mypy для комплексного анализа кода.

    Returns:
        Tuple[bool, str]: Кортеж из (результат_проверки, вывод_команд).
                         True если оба анализатора не нашли ошибок, False в противном случае.
    """
    ruff_success, ruff_output = run_ruff_check()
    mypy_success, mypy_output = run_mypy_check()

    combined_output = f"=== RUFF OUTPUT ===\n{ruff_output}\n\n=== MYPY OUTPUT ===\n{mypy_output}"

    return ruff_success and mypy_success, combined_output

def get_required_checks() -> List[str]:
    """
    Возвращает список обязательных проверок для CI pipeline.

    Returns:
        List[str]: Список имен проверок, которые должны выполняться в CI.
    """
    return ["ruff", "mypy"]

def run_check_by_name(check_name: str) -> Tuple[bool, str]:
    """
    Запускает указанную проверку по имени.

    Args:
        check_name: Имя проверки (ruff или mypy)

    Returns:
        Tuple[bool, str]: Результат выполнения проверки

    Raises:
        ValueError: Если указано неизвестное имя проверки
    """
    check_mapping = {
        "ruff": run_ruff_check,
        "mypy": run_mypy_check,
    }

    if check_name not in check_mapping:
        raise ValueError(f"Unknown check name: {check_name}. Available: {list(check_mapping.keys())}")

    return check_mapping[check_name]()