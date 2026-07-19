"""
AIOS Communication Bridge Layer v2.1.1

Connects AIOS with external interfaces.
"""


class CommunicationBridge:
    def __init__(self):
        self.channels = []

    def register_channel(self, channel: str):
        self.channels.append(channel)
        return channel

    def list_channels(self):
        return self.channels
