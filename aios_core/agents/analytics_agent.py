from .base import BaseAgent, AgentState
from aios_core.analytics.engine import AnalyticsEngine

class AnalyticsAgent(BaseAgent):
    def __init__(self, analytics_engine: AnalyticsEngine):
        super().__init__("analytics")
        self.engine = analytics_engine

    async def process(self, state: AgentState) -> AgentState:
        msg = state.messages[-1] if state.messages else ""
        if any(kw in msg.lower() for kw in ["статистика", "отчет", "метрики", "аналитика"]):
            report = self.engine.get_full_report()
            state.result = {"action": "provide_report", "data": report, "confidence": 0.95}
        else:
            state.result = {"action": "no_data", "confidence": 0.2}
        state.current_agent = "analytics"
        return state
