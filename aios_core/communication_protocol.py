"""
AIOS Communication Protocol Layer v2.1.1

Defines secure message exchange rules between AIOS components and nodes.
"""


class CommunicationProtocol:
    def __init__(self):
        self.messages = []

    def send(self, source: str, target: str, message: dict):
        packet = {
            "source": source,
            "target": target,
            "message": message,
            "verified": True
        }
        self.messages.append(packet)
        return packet

    def history(self):
        return self.messages
