import os

import httpx
from arq.connections import RedisSettings


async def process_competitor_prices(ctx, urls):
    return {"status": "completed", "count": len(urls)}

async def send_bulk_messages(ctx, platform, messages):
    return {"status": "completed", "count": len(messages)}

async def long_llm_request(ctx, prompt, context):
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60.0
        )
    return {"status": "completed", "response": r.json()["choices"][0]["message"]["content"]}

class WorkerSettings:
    functions = [process_competitor_prices, send_bulk_messages, long_llm_request, run_evolution_cycle, discover_new_intents, heal_rejected_template]
    redis_settings = RedisSettings(host=os.getenv("REDIS_HOST", "localhost"), port=6379)
    max_jobs = 10
    job_timeout = 300
