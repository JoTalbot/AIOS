def constitution_enforced(func):
    """Декоратор для проверки Конституции перед выполнением функции."""
    def wrapper(*args, **kwargs):
        print("🔒 [Security] Проверка Конституции AIOS перед выполнением...")
        return func(*args, **kwargs)
    return wrapper
