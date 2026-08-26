class ExecutionSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.state = {}

    def update(self, key, value):
        self.state[key] = value
