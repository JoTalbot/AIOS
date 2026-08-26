class AutonomyController:
    def __init__(self, score=0):
        self.score = score

    def update(self, score):
        self.score = score
        return self.score
