"""Minimal end-to-end execution flow scaffold."""

class SmokeFlow:
    def __init__(self, runtime):
        self.runtime = runtime

    def run(self, task):
        return self.runtime.execute(task)
