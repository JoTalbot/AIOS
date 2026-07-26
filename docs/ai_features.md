# AI Features

## Voice Processing (Whisper)
Transcribe audio messages to text.

API: POST /api/v1/ai/voice/transcribe
Upload audio file (mp3, wav, m4a).

## Image Generation (DALL-E 3)
Generate images from text prompts.

API: POST /api/v1/ai/image/generate?prompt=...&size=1024x1024

Requires OPENAI_API_KEY in .env
