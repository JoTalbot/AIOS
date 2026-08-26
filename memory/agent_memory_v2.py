class MemoryRecord:
    def __init__(self, key: str, value: object, context: dict | None = None):
        self.key = key
        self.value = value
        self.context = context or {}


class AgentMemoryV2:
    def __init__(self):
        self.records = {}

    def store(self, key: str, value: object, context: dict | None = None):
        self.records[key] = MemoryRecord(key, value, context)

    def recall(self, key: str):
        record = self.records.get(key)
        return record.value if record else None

    def get_context(self, key: str):
        record = self.records.get(key)
        return record.context if record else {}
