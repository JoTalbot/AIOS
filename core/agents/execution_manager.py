class AgentExecutionManager:
    def __init__(self):
        self.active = {}

    def begin(self, execution_id, context):
        self.active[execution_id] = context

    def end(self, execution_id):
        return self.active.pop(execution_id, None)
