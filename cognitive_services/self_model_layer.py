"""AIOS v26.2 Self Model Layer."""

class SelfModelLayer:
    def __init__(self):
        self.identity = {}

    def set_attribute(self, key, value):
        self.identity[key] = value

    def get_model(self):
        return dict(self.identity)
