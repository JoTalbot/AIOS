"""
LLM Swarm Debate Controller (Vector 1: LiteLLM Activated)
Интеграция реальных LLM-моделей в процесс дебатов Роя.
"""
import os
from typing import Dict, List
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

class SwarmAgent:
    def __init__(self, name: str, role: str, system_prompt: str, model: str = "gpt-3.5-turbo"):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.memory: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]

    def generate_response(self, context: str) -> str:
        self.memory.append({"role": "user", "content": context})
        
        # Если есть API ключ - вызываем реальную модель, иначе fallback
        if LITELLM_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            print(f"📡 [LLM Call -> {self.model}] Ожидание ответа от {self.name}...")
            response = completion(model=self.model, messages=self.memory)
            reply = response.choices[0].message.content
        else:
            print(f"⚠️ [Mock LLM] API Ключ не найден, использую заглушку для {self.name}...")
            if self.role == "Architect":
                reply = "Предлагаю создать новую архитектуру для масштабирования GraphQL."
            elif self.role == "Security":
                reply = "Обнаружена уязвимость. Отклоняю без JWT."
            else:
                reply = "Я готов внедрить JWT валидацию и обновить GraphQL."
                
        self.memory.append({"role": "assistant", "content": reply})
        return reply

class LLMSwarm:
    def __init__(self):
        self.agents = {
            "architect": SwarmAgent("Nexus", "Architect", "Ты Архитектор AIOS. Придумывай фичи."),
            "security": SwarmAgent("Shield", "Security", "Ты Страж. Отклоняй небезопасное."),
            "developer": SwarmAgent("Coder", "Developer", "Ты Кодер. Решай задачу безопасно.")
        }

    def start_debate(self, topic: str):
        print(f"\n💬 --- ЗАПУСК ДЕБАТОВ: {topic} ---\n")
        arch_idea = self.agents["architect"].generate_response(topic)
        print(f"🤖 [Architect] Nexus: {arch_idea}\n")
        
        sec_review = self.agents["security"].generate_response(f"Проверь идею: {arch_idea}")
        print(f"🤖 [Security] Shield: {sec_review}\n")
        
        dev_action = self.agents["developer"].generate_response(f"Сделай: {sec_review}")
        print(f"🤖 [Developer] Coder: {dev_action}\n")
        print("✅ --- КОНСЕНСУС ДОСТИГНУТ ---\n")

if __name__ == "__main__":
    LLMSwarm().start_debate("Интеграция с API Binance")
