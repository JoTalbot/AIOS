"""
LLM Swarm Debate Controller (Vector 2: ChromaDB Deep RAG Activated)
Интеграция реальных LLM-моделей и векторной памяти в процесс дебатов Роя.
"""
import os
import datetime
from typing import Dict, List
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

try:
    import chromadb
    chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "..", "chroma_db"))
    memory_collection = chroma_client.get_or_create_collection(name="swarm_global_memory")
    CHROMADB_AVAILABLE = True
except Exception as e:
    CHROMADB_AVAILABLE = False
    print(f"ChromaDB Init Error: {e}")

class SwarmAgent:
    def __init__(self, name: str, role: str, system_prompt: str, model: str = "gpt-3.5-turbo"):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.memory: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]

    def _query_rag(self, query: str) -> str:
        if not CHROMADB_AVAILABLE: return ""
        try:
            results = memory_collection.query(query_texts=[query], n_results=1)
            if results and results['documents'] and results['documents'][0]:
                return f"\n\n[RAG MEMORY RECALL]: Я помню прошлый опыт: {results['documents'][0][0]}"
        except Exception:
            pass
        return ""

    def _save_to_rag(self, content: str):
        if not CHROMADB_AVAILABLE: return
        doc_id = f"mem_{self.name}_{datetime.datetime.now().timestamp()}"
        memory_collection.add(documents=[content], metadatas=[{"role": self.role}], ids=[doc_id])

    def generate_response(self, context: str) -> str:
        rag_context = self._query_rag(context)
        full_context = context + rag_context
        self.memory.append({"role": "user", "content": full_context})
        
        if LITELLM_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            print(f"📡 [LLM Call -> {self.model}] Ожидание ответа от {self.name}...")
            response = completion(model=self.model, messages=self.memory)
            reply = response.choices[0].message.content
        else:
            print(f"⚠️ [Mock LLM] API Ключ не найден, использую заглушку для {self.name}...")
            if self.role == "Architect":
                reply = "Предлагаю использовать Selenium для сбора лидов."
            elif self.role == "Security":
                reply = "Selenium слишком тяжелый и палится капчей. Используем Playwright Stealth."
            else:
                reply = "Пишу код на Playwright с обходом Cloudflare."
                
        self.memory.append({"role": "assistant", "content": reply})
        self._save_to_rag(reply)
        return reply

class LLMSwarm:
    def __init__(self):
        self.agents = {
            "architect": SwarmAgent("Nexus", "Architect", "Ты Архитектор AIOS."),
            "security": SwarmAgent("Shield", "Security", "Ты Страж. Отклоняй небезопасное."),
            "developer": SwarmAgent("Coder", "Developer", "Ты Кодер.")
        }

    def start_debate(self, topic: str) -> str:
        print(f"\n💬 --- ЗАПУСК ДЕБАТОВ (С ПАМЯТЬЮ): {topic} ---\n")
        arch_idea = self.agents["architect"].generate_response(topic)
        print(f"🤖 [Architect] Nexus: {arch_idea}\n")
        sec_review = self.agents["security"].generate_response(f"Проверь идею: {arch_idea}")
        print(f"🤖 [Security] Shield: {sec_review}\n")
        dev_action = self.agents["developer"].generate_response(f"Сделай: {sec_review}")
        print(f"🤖 [Developer] Coder: {dev_action}\n")
        print("✅ --- КОНСЕНСУС ДОСТИГНУТ ---\n")
        return dev_action
