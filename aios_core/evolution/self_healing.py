
import json
import os
from typing import Any

import httpx


class SelfHealing:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    async def heal(self, template: str, reason: str, original: str) -> dict[str, Any]:
        if not self.api_key: return {"status": "no_api_key"}
        
        prompt = f"""Улучши шаблон ответа.
Оригинал клиента: {original}
Текущий шаблон: {template}
Причина отклонения: {reason}
Верни JSON: {{"improved": "...", "explanation": "..."}}"""
        
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                    timeout=30.0)
                r.raise_for_status()
                return json.loads(r.json()["choices"][0]["message"]["content"])
        except Exception as e:
            return {"status": "error", "error": str(e)}

self_healing = SelfHealing()
