import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.add(conn)
        self.active_connections -= disconnected


manager = ConnectionManager()


async def metrics_broadcast_loop(get_metrics_func):
    while True:
        try:
            metrics = get_metrics_func()
            await manager.broadcast({"type": "metrics_update", "data": metrics})
        except Exception as e:
            print(f"WS broadcast error: {e}")
        await asyncio.sleep(5)
