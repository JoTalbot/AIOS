"""AIOS Version Manager"""

class VersionManager:
    def __init__(self):
        self.versions = []

    def register(self, version):
        self.versions.append(version)

    def history(self):
        return self.versions
