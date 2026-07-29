import asyncio
from collections.abc import Callable
from enum import Enum
from typing import Any


class WorkflowState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStep:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func


class SalesWorkflow:
    def __init__(self):
        self.steps = []

    def add_step(self, name: str, func: Callable):
        self.steps.append(WorkflowStep(name, func))

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        state = WorkflowState.IN_PROGRESS
        history = []

        for step in self.steps:
            try:
                result = await step.func(context)
                history.append({"step": step.name, "status": "success", "result": result})
                context.update(result)
            except Exception as e:
                history.append({"step": step.name, "status": "failed", "error": str(e)})
                state = WorkflowState.FAILED
                break

        if state != WorkflowState.FAILED:
            state = WorkflowState.COMPLETED

        return {"state": state.value, "history": history, "final_context": context}


async def check_stock(context):
    await asyncio.sleep(0.1)
    return {"in_stock": True, "quantity": 15}


async def calc_discount(context):
    discount = 10 if context.get("in_stock") else 0
    return {"final_price": context.get("price", 100) * (1 - discount / 100), "discount_applied": discount}


async def create_draft(context):
    return {"draft_id": "draft_123", "text": f"Товар в наличии. Цена: {context['final_price']}"}


sales_workflow = SalesWorkflow()
sales_workflow.add_step("check_stock", check_stock)
sales_workflow.add_step("calc_discount", calc_discount)
sales_workflow.add_step("create_draft", create_draft)
