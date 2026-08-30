class PredictiveScheduler:
    def __init__(self):
        self.queue = []

    def schedule(self, task, prediction=None):
        item = {"task": task, "prediction": prediction}
        self.queue.append(item)
        return item

    def plan(self):
        return self.queue
