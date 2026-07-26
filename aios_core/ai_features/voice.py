import os
import httpx
from typing import Optional

class VoiceProcessor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.whisper_url = "https://api.openai.com/v1/audio/transcriptions"
    
    async def transcribe(self, audio_file_path: str, language: str = "uk") -> Optional[str]:
        if not self.api_key:
            return None
        try:
            with open(audio_file_path, "rb") as f:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.whisper_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data={"model": "whisper-1", "language": language},
                        files={"file": f},
                        timeout=60.0
                    )
                    response.raise_for_status()
                    return response.json()["text"]
        except Exception as e:
            print(f"[Voice] Error: {e}")
            return None

voice_processor = VoiceProcessor()
