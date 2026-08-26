class MemoryConflictResolver:
    def resolve(self, versions):
        if not versions:
            return None

        return max(
            versions,
            key=lambda item: item["timestamp"]
        )
