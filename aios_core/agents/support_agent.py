from .base import BaseAgent, AgentState

class SupportAgent(BaseAgent):
    def __init__(self):
        super().__init__("support")

    from aios_core.observability.agent_metrics import track_agent_metrics

    @track_agent_metrics("support")
    async def process(self, state: AgentState) -> AgentState:
        msg = state.messages[-1] if state.messages else ""
        if any(kw in msg.lower() for kw in ["проблема", "не работает", "возврат", "жалоба"]):
            state.result = {"action": "escalate_to_human", "confidence": 0.85}
        else:
            state.result = {"action": "provide_info", "confidence": 0.7}
        state.current_agent = "support"
        return state
