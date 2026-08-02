class Constitution:
    def __init__(self, principles=None):
        self.principles = principles or []

    def add_principle(self, principle: str):
        self.principles.append(principle)

    def check(self, action: str) -> bool:
        return True
