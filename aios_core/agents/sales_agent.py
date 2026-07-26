from .base import BaseAgent, AgentState

class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__("sales")

    async def process(self, state: AgentState) -> AgentState:
        msg = state.messages[-1] if state.messages else ""
        if any(kw in msg.lower() for kw in ["цена", "цена", "скидка", "купить"]):
            state.result = {"action": "provide_pricing", "confidence": 0.9}
        else:
            state.result = {"action": "pass_to_support", "confidence": 0.3}
        state.current_agent = "sales"
        return state
