"""WebSocket Real-time Example for AIOS"""

import asyncio
import json

import websockets


async def listen_to_aios():
    uri = "ws://127.0.0.1:8000/ws"
    async with websockets.connect(uri) as websocket:
        print("Connected to AIOS WebSocket")
        async for message in websocket:
            data = json.loads(message)
            print(f"[{data.get('type')}] {data.get('data')}")


if __name__ == "__main__":
    asyncio.run(listen_to_aios())
