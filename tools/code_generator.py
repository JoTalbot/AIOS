import time
from dataclasses import dataclass
from typing import Optional

__all__ = ['CodeGenerator']

@dataclass
class CodeGenerator:
    """Генератор кода с ограничением количества циклов в единицу времени."""
    max_cycles_per_second: int = 5
    """Максимальное количество циклов генерации кода в секунду."""
    sleep_time: Optional[float] = None
    """Время задержки между циклами генерации кода."""

    def __post_init__(self):
        if self.sleep_time is None:
            self.sleep_time = 1 / self.max_cycles_per_second

    def generate_code(self) -> str:
        """Генерирует код."""
        # Для примера, генерируем случайный код
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    def run(self, num_cycles: int) -> None:
        """Запускает генератор кода на указанное количество циклов."""
        for _ in range(num_cycles):
            code = self.generate_code()
            print(code)
            time.sleep(self.sleep_time)

if __name__ == '__main__':
    generator = CodeGenerator(max_cycles_per_second=2)
    generator.run(10)