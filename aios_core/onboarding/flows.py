

class OnboardingFlow:
    def __init__(self):
        self.steps = [
            {"id": "connect_platform", "title": "Подключить первую платформу", "done": False},
            {"id": "create_template", "title": "Создать первый шаблон", "done": False},
            {"id": "approve_draft", "title": "Одобрить первый черновик", "done": False},
            {"id": "setup_billing", "title": "Настроить биллинг", "done": False}
        ]
    
    def get_progress(self, workspace_id: str) -> dict:
        done = sum(1 for s in self.steps if s["done"])
        return {"total": len(self.steps), "done": done, "percent": int(done / len(self.steps) * 100), "steps": self.steps}

    def complete_step(self, workspace_id: str, step_id: str):
        for s in self.steps:
            if s["id"] == step_id:
                s["done"] = True
                break

onboarding_flow = OnboardingFlow()
