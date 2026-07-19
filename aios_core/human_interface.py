"""
AIOS Human Interface Layer v2.1.1

Handles human interaction requests.
"""


class HumanInterface:
    def __init__(self):
        self.requests = []

    def receive(self, request: dict):
        self.requests.append(request)
        return request

    def history(self):
        return self.requests
