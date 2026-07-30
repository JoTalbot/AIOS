#!/usr/bin/env python3
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from aios_core.meta_cognitive_self_coder import MetaCognitiveCoder

def execute_autonomous_refactoring():
    coder = MetaCognitiveCoder()
    target_skill = os.path.join(BASE_DIR, "skills", "core", "legacy-test-skill", "code", "run.py")
    
    print("=== ЗАПУСК ВЕКТОРА Б (УГЛУБЛЕННЫЙ АНАЛИЗ И РЕФАКТОРИНГ AST) ===")
    
    # 1. Чтение и AST-Трансформация
    coder.refactor_skill_ast(target_skill)
    
    # 2. Выполнение рефакторенного кода для проверки
    print("\n[Система] Тестовый запуск обновленного скрипта:")
    with open(target_skill, "r") as f:
        print("-" * 40)
        print(f.read())
        print("-" * 40)
        
    # 3. Пуш в репозиторий
    coder.commit_and_push_changes(target_skill, BASE_DIR)

if __name__ == "__main__":
    execute_autonomous_refactoring()
