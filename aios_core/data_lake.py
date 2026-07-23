"""Data Lake for AIOS Analytics"""

import json
import os
from typing import Any, Dict, List


class DataLake:
    """Simple data lake for storing analytics events."""

    def __init__(self, path: str = "data_lake"):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def ingest(self, event: Dict[str, Any]):
        date = event.get("timestamp", "unknown")[:10]
        filepath = os.path.join(self.path, f"{date}.jsonl")
        with open(filepath, "a") as f:
            f.write(json.dumps(event) + "\n")

    def query(self, date: str = None) -> List[Dict]:
        results = []
        if date:
            filepath = os.path.join(self.path, f"{date}.jsonl")
            if os.path.exists(filepath):
                with open(filepath) as f:
                    for line in f:
                        results.append(json.loads(line))
        return results

    def stats(self) -> dict:
        files = os.listdir(self.path)
        return {"files": len(files), "path": self.path}
