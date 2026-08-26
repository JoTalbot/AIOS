import asyncio
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    sender: str
    receiver: str
    payload: dict
    timestamp: str = datetime.utcnow().isoformat()


class AgentBus:
    def __init__(self):
        self.channels = {}

    def register(self, agent_id):
        self.channels[agent_id] = asyncio.Queue()

    async def send(self, message: Message):
        if message.receiver in self.channels:
            await self.channels[message.receiver].put(message)

    async def receive(self, agent_id):
        return await self.channels[agent_id].get()
