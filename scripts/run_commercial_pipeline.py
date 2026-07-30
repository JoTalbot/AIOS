#!/usr/bin/env python3
import sys, os, time
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Dynamically import runner without loading the whole aios_mcp package
import importlib.util
spec = importlib.util.spec_from_file_location("mcp_runner", os.path.join(BASE_DIR, "aios_mcp", "mcp_runner.py"))
mcp_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_runner)

from aios_core.llm_swarm_debate import LLMSwarm

def execute_commercial_mission():
    print("💼 [Commercial Pipeline] Инициализация боевой миссии...")
    browser = mcp_runner.BrowserVisionSensor()
    tg = mcp_runner.TelegramControlSensor()
    swarm = LLMSwarm()
    
    target_url = "https://freelance.platform/jobs?query=python+ai"
    print(f"\n[Phase 1] Сканирование {target_url} через BrowserVision...")
    raw_data = browser.scan_url(target_url)
    time.sleep(1)
    
    print("\n[Phase 2] Передача данных Рою для оценки лидов...")
    topic = f"Проанализируй эти сырые данные лидов и выбери самый дорогой контракт: {raw_data['content']}"
    swarm_decision = swarm.start_debate(topic)
    
    print("\n[Phase 3] Отправка результатов оператору...")
    # Пытаемся отправить по юзернейму (работает для публичных каналов)
    result = tg.send_message("@FainaBaru", f"Нашёлся отличный проект! Вердикт роя: {swarm_decision}")
    
    # Если это приватный юзер, Telegram API выдаст ошибку (нужен numeric chat_id).
    # Берем ID из последних сообщений боту как запасной вариант.
    if result.get("status") == "failed":
        print("⚠️ Отправка по юзернейму не удалась. Поиск числового Chat ID...")
        chat_id = tg.get_latest_chat_id()
        if chat_id:
            tg.send_message(chat_id, f"Нашёлся отличный проект! Вердикт роя: {swarm_decision}")
        else:
            print("❌ Chat ID не найден. Напишите боту @AIOScontrol_bot 'Привет', чтобы он вас запомнил!")
            
    print("\n✅ Миссия успешно завершена. Рой ожидает новых приказов.")

if __name__ == "__main__":
    execute_commercial_mission()
