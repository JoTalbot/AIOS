import os
from typing import Dict, Any, Optional
import httpx

class VoiceAIAgent:
    def __init__(self):
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.openai_key = os.getenv("OPENAI_API_KEY")
    
    async def process_voice_call(self, call_sid: str, recording_url: str) -> Dict[str, Any]:
        """Обрабатывает голосовое сообщение/звонок через Whisper."""
        if not self.openai_key or not recording_url:
            return {"status": "error", "message": "Missing credentials or URL"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(recording_url)
                audio_data = response.content
            
            headers = {"Authorization": f"Bearer {self.openai_key}"}
            files = {"file": ("audio.mp3", audio_data, "audio/mpeg")}
            data = {"model": "whisper-1"}
            
            async with httpx.AsyncClient() as client:
                whisper_resp = await client.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
                whisper_resp.raise_for_status()
                text = whisper_resp.json()["text"]
            
            return {
                "status": "success",
                "call_sid": call_sid,
                "transcription": text,
                "action": "forward_to_text_agent"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

voice_agent = VoiceAIAgent()
