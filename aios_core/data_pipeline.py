"""AIOS Data Pipeline"""

class DataPipeline:
    def __init__(self):
        self.steps = []

    def add_step(self, step):
        self.steps.append(step)

    def process(self, data):
        return data
