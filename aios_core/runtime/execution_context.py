from dataclasses import dataclass, field

@dataclass
class ExecutionContext:
    task_id: str
    metadata: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def add_event(self, event):
        self.history.append(event)
