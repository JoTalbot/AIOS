from typing import List
from .base import BaseAgent, AgentState
from .sales_agent import SalesAgent
from .support_agent import SupportAgent
from .analytics_agent import AnalyticsAgent
from aios_core.analytics.engine import AnalyticsEngine

class MultiAgentOrchestrator:
    def __init__(self, analytics_engine: AnalyticsEngine):
        self.agents = {
            "sales": SalesAgent(),
            "support": SupportAgent(),
            "analytics": AnalyticsAgent(analytics_engine)
        }

    async def route(self, state: AgentState) -> str:
        msg = state.messages[-1].lower() if state.messages else ""
        if any(kw in msg for kw in ["цена", "купить", "скидка"]):
            return "sales"
        elif any(kw in msg for kw in ["проблема", "не работает", "возврат"]):
            return "support"
        elif any(kw in msg for kw in ["статистика", "отчет", "метрики"]):
            return "analytics"
        return "support"

    async def process(self, messages: List[str], context: dict) -> dict:
        state = AgentState(messages=messages, context=context, current_agent="router")
        next_agent = await self.route(state)
        agent = self.agents[next_agent]
        state = await agent.process(state)
        return {
            "agent": state.current_agent,
            "result": state.result,
            "messages": state.messages
        }
