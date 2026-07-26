from typing import Dict, Any, List
from enum import Enum

class NegotiationState(Enum):
    INITIAL_OFFER = "initial_offer"
    COUNTER_OFFER = "counter_offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ESCALATE_TO_HUMAN = "escalate_to_human"

class NegotiationAgent:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def process_message(self, session_id: str, user_message: str, guardrails: Dict) -> Dict[str, Any]:
        session = self.sessions.get(session_id, {"state": NegotiationState.INITIAL_OFFER, "history": []})
        session["history"].append({"role": "user", "text": user_message})
        
        state = session["state"]
        response = ""
        
        if state == NegotiationState.INITIAL_OFFER:
            if "согласен" in user_message.lower() or "ок" in user_message.lower():
                session["state"] = NegotiationState.ACCEPTED
                response = "Отлично! Договорились. Оформляем?"
            elif "дорого" in user_message.lower() or "скидка" in user_message.lower():
                session["state"] = NegotiationState.COUNTER_OFFER
                discount = guardrails.get("max_discount", 10)
                response = f"Понимаю. Могу предложить специальную скидку {discount}% при заказе сегодня."
            else:
                session["state"] = NegotiationState.ESCALATE_TO_HUMAN
                response = "Передаю ваш запрос менеджеру для уточнения деталей."
        
        elif state == NegotiationState.COUNTER_OFFER:
            if "согласен" in user_message.lower() or "беру" in user_message.lower():
                session["state"] = NegotiationState.ACCEPTED
                response = "Супер! Скидка применена. Переходим к оформлению."
            else:
                session["state"] = NegotiationState.ESCALATE_TO_HUMAN
                response = "Вижу, что условия все еще обсуждаются. Подключаю старшего менеджера."
        
        session["history"].append({"role": "agent", "text": response})
        self.sessions[session_id] = session
        
        return {
            "session_id": session_id,
            "state": session["state"].value,
            "response": response,
            "requires_human": session["state"] in [NegotiationState.ESCALATE_TO_HUMAN, NegotiationState.ACCEPTED]
        }

negotiation_agent = NegotiationAgent()
