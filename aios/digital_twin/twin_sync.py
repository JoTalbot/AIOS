class TwinSync:
    def __init__(self):
        self.history = []

    def sync(self, runtime_state):
        self.history.append(runtime_state)
        return runtime_state

    def history_log(self):
        return self.history
