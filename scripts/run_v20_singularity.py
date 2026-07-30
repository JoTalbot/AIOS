#!/usr/bin/env python3
"""
Master Execution Script for AIOS v20.0.0
Демонстрация всех 5 Векторов Экосистемной Сингулярности в одном процессе.
"""
import sys, os, time
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from aios_core.crypto_wallet import AIOSWallet
from aios_core.graph_memory import GraphMemory
from aios_mcp.voice_and_iot import VoiceInterface, IoTSensor
from aios_core.skill_marketplace import SkillMarketplace

def run_singularity():
    print("\n" + "="*50)
    print(" 🌌 ИНИЦИАЛИЗАЦИЯ AIOS v20.0.0 (ECOSYSTEM SINGULARITY)")
    print("="*50 + "\n")
    
    # 1. Financial Autonomy
    wallet = AIOSWallet()
    wallet.allocate_budget_for_llm()
    time.sleep(1)
    print("")
    
    # 2. Graph Knowledge
    graph = GraphMemory()
    graph.add_insight("AIOS", "analyzes", "Medical Images")
    graph.add_insight("Medical Images", "requires", "x-ray-analysis skill")
    graph.query_graph("AIOS")
    time.sleep(1)
    print("")
    
    # 3. P2P Marketplace
    market = SkillMarketplace()
    downloaded_code = market.request_skill("x-ray-analysis")
    market.install_skill("x-ray-analysis", downloaded_code, BASE_DIR)
    time.sleep(1)
    print("")
    
    # 4 & 5. Cyber-physical & Voice
    voice = VoiceInterface()
    iot = IoTSensor()
    voice.speak("Навык установлен. Запускаю медицинский сканер через IoT-протокол.")
    iot.trigger_robot_arm("ACTIVATE_XRAY_SENSOR")
    print("\n✅ Цикл Сингулярности v20.0.0 успешно завершен.")

if __name__ == "__main__":
    run_singularity()
