import os

from arq import create_pool
from arq.connections import RedisSettings


async def get_queue():
    return await create_pool(RedisSettings(host=os.getenv("REDIS_HOST", "localhost"), port=6379))

async def enqueue_competitor_pricing(urls):
    q = await get_queue()
    return (await q.enqueue_job("process_competitor_prices", urls)).job_id

async def enqueue_bulk_messages(platform, messages):
    q = await get_queue()
    return (await q.enqueue_job("send_bulk_messages", platform, messages)).job_id

async def enqueue_llm_request(prompt, context):
    q = await get_queue()
    return (await q.enqueue_job("long_llm_request", prompt, context)).job_id
