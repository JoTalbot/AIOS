class TaskRouter:
    def __init__(self, matcher=None, balancer=None):
        self.matcher = matcher
        self.balancer = balancer

    def route(self, task):
        candidates = self.matcher.match(task) if self.matcher else []
        if self.balancer:
            return self.balancer.select(candidates)
        return candidates[0] if candidates else None
