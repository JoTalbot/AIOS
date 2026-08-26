class AutonomousDemo:
    def __init__(self, planner=None, router=None):
        self.planner = planner
        self.router = router

    def run(self, goal):
        plan = self.planner.plan(goal) if self.planner else goal
        return self.router.route(plan) if self.router else plan
