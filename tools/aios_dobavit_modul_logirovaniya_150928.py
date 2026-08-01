"""
Модуль логирования и мониторинга для run_coder_orchestrator.py.
Использует библиотеку logging для логирования и мониторинга.
"""

import logging
from dataclasses import dataclass
from typing import Optional

# Настройки логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@dataclass
class LoggerConfig:
    """Настройки логирования."""
    log_file: Optional[str] = None
    log_level: int = logging.INFO

def configure_logger(config: LoggerConfig) -> logging.Logger:
    """
    Настройка логгера.

    Args:
    config (LoggerConfig): Настройки логирования.

    Returns:
    logging.Logger: Настроенный логгер.
    """
    logger = logging.getLogger('aios_coder_logger')
    logger.setLevel(config.log_level)

    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setLevel(config.log_level)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.log_level)
    logger.addHandler(console_handler)

    return logger

def write_log(logger: logging.Logger, message: str, level: int = logging.INFO) -> None:
    """
    Запись логов в файл и в консоль.

    Args:
    logger (logging.Logger): Настроенный логгер.
    message (str): Сообщение для записи.
    level (int, optional): Уровень логирования. Defaults to logging.INFO.
    """
    logger.log(level, message)

def main() -> None:
    """
    Тестовая функция для проверки логирования.
    """
    config = LoggerConfig(log_file='log.txt')
    logger = configure_logger(config)

    write_log(logger, 'Тестовый лог')
    write_log(logger, 'Тестовый лог с уровнем DEBUG', logging.DEBUG)

if __name__ == '__main__':
    main()