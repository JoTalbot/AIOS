"""AIOS v22.8 Adaptive Workflow Optimizer foundation.

Provides a minimal optimization layer for improving workflows based on
execution feedback and performance signals.
"""


class AdaptiveWorkflowOptimizer:
    def __init__(self):
        self.metrics = []

    def record(self, workflow_id, score):
        self.metrics.append({"workflow_id": workflow_id, "score": score})

    def best_workflow(self):
        if not self.metrics:
            return None
        return max(self.metrics, key=lambda item: item["score"])

    def health(self):
        return {"status": "ok", "samples": len(self.metrics)}
