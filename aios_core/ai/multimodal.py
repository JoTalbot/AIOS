import os

import httpx


class MultiModalAI:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
    
    async def analyze_image(self, image_url: str, prompt: str = "Describe") -> str | None:
        if not self.api_key:
            return "No API key"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": "gpt-4o", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_url}}]}], "max_tokens": 500},
                    timeout=30.0
                )
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return str(e)

multimodal_ai = MultiModalAI()
