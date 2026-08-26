class ContinuousLearning:
    def __init__(self, adaptive_engine, replay=None):
        self.adaptive_engine = adaptive_engine
        self.replay = replay

    def process(self, experience):
        if self.replay:
            self.replay.add(experience)
        return self.adaptive_engine.learn(experience)
