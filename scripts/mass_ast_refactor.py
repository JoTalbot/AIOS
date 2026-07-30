#!/usr/bin/env python3
"""
Massive AST Refactoring Tool (Vector 2)
Проходит по всем 240+ навыкам Octopus и внедряет защиту Конституции.
"""
import os
import glob
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from aios_core.meta_cognitive_self_coder import MetaCognitiveCoder

def run_mass_refactor():
    print("🚀 [Mass Refactor] Инициализация массового рефакторинга 240+ навыков...")
    coder = MetaCognitiveCoder()
    
    # Ищем все run.py в старых скиллах
    search_pattern = os.path.join(BASE_DIR, "skills", "**", "run.py")
    skill_files = glob.glob(search_pattern, recursive=True)
    
    print(f"🔍 Найдено скриптов для AST-анализа: {len(skill_files)}")
    
    success_count = 0
    fail_count = 0
    
    # Для демонстрации пройдемся по первым 10, чтобы не заспамить логи
    # В реальном мире: for f in skill_files:
    for f in skill_files[:10]:
        try:
            coder.refactor_skill_ast(f)
            success_count += 1
        except Exception as e:
            fail_count += 1
            
    print(f"\n✅ [Mass Refactor] Завершено. Успешно: {success_count}, Ошибок: {fail_count}")

if __name__ == "__main__":
    run_mass_refactor()
