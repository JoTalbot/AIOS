class EvolutionOrchestrator:
    def __init__(self, reflection=None, learning=None, evolution=None):
        self.reflection = reflection
        self.learning = learning
        self.evolution = evolution

    def process(self, result):
        reflection = self.reflection.analyze(result) if self.reflection else result
        if self.learning:
            self.learning.process(reflection)
        if self.evolution:
            return self.evolution.run(reflection)
        return reflection
