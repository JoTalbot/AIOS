class RuntimeEnvironment:
    def __init__(self, name='production'):
        self.name = name

    def is_production(self):
        return self.name == 'production'
