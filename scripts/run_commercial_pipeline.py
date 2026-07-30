#!/usr/bin/env python3
"""
Commercial RPA Pipeline (Vector 1)
Связывает BrowserVision, LLM Swarm и Telegram для реальной работы.
"""
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from aios_mcp.mcp_runner import BrowserVisionSensor, TelegramControlSensor
from aios_core.llm_swarm_debate import LLMSwarm

def execute_commercial_mission():
    print("💼 [Commercial Pipeline] Инициализация боевой миссии...")
    browser = BrowserVisionSensor()
    tg = TelegramControlSensor()
    swarm = LLMSwarm()
    
    # 1. Сбор данных
    target_url = "https://freelance.platform/jobs?query=python+ai"
    print(f"\n[Phase 1] Сканирование {target_url} через BrowserVision...")
    raw_data = browser.scan_url(target_url)
    time.sleep(1)
    
    # 2. Анализ Роем
    print("\n[Phase 2] Передача данных Рою для оценки лидов...")
    topic = f"Проанализируй эти сырые данные лидов и выбери самый дорогой контракт: {raw_data['content']}"
    swarm_decision = swarm.start_debate(topic)
    
    # 3. Уведомление
    print("\n[Phase 3] Отправка результатов оператору...")
    tg.send_message("@aios_operator", f"Нашёлся отличный проект! Вердикт роя: {swarm_decision}")
    
    print("\n✅ Миссия успешно завершена. Рой ожидает новых приказов.")

if __name__ == "__main__":
    execute_commercial_mission()
