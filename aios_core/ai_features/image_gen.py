import os
import httpx
from typing import Optional

class ImageGenerator:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.dalle_url = "https://api.openai.com/v1/images/generations"
    
    async def generate(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        if not self.api_key:
            return None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.dalle_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": "dall-e-3", "prompt": prompt, "size": size, "n": 1},
                    timeout=120.0
                )
                response.raise_for_status()
                return response.json()["data"][0]["url"]
        except Exception as e:
            print(f"[ImageGen] Error: {e}")
            return None

image_generator = ImageGenerator()
