import logging
import time
from typing import Optional

__all__ = ['log_error', 'log_performance', 'configure_logging']

def configure_logging(log_file: Optional[str] = None, log_level: int = logging.INFO) -> None:
    """
    Configure logging module.

    Args:
    - log_file (str): Path to log file. If None, log to console.
    - log_level (int): Logging level.
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=log_level,
        handlers=handlers
    )

def log_error(message: str) -> None:
    """
    Log error message.

    Args:
    - message (str): Error message.
    """
    logging.error(message)

def log_performance(message: str, execution_time: float) -> None:
    """
    Log performance information.

    Args:
    - message (str): Performance message.
    - execution_time (float): Execution time in seconds.
    """
    logging.info('%s за %s секунд', message, execution_time)

if __name__ == '__main__':
    configure_logging(log_file='monitoring.log')
    start_time = time.time()
    # Simulate some work
    time.sleep(1)
    execution_time = time.time() - start_time
    
    log_error('Ошибка в цикле генерации кода')
    log_performance('Цикл генерации кода завершен', execution_time)