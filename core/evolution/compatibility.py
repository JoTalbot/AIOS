class VersionCompatibilityManager:

    def __init__(self):
        self.versions = []

    def register(self, version):
        self.versions.append(version)

    def compatible(self, version):
        return version in self.versions
