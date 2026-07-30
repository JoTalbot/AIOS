#!/usr/bin/env python3
"""Загрузчик golden tasks с поддержкой расширенного корпуса."""

import json
from pathlib import Path
from typing import List, Dict

BASE = Path("/mnt/agents/-Octopus")
EVAL = BASE / "skills" / "eval"

class GoldenTasksLoader:
    def __init__(self):
        self.tasks: List[Dict] = []

    def load(self, source: str = "legacy") -> List[Dict]:
        """Загрузить задачи из источника."""
        if source == "legacy":
            return self._load_legacy()
        elif source == "expanded":
            return self._load_expanded()
        elif source == "all":
            legacy = self._load_legacy()
            expanded = self._load_expanded()
            return legacy + expanded
        return self._load_legacy()

    def _load_legacy(self) -> List[Dict]:
        """Загрузить legacy golden tasks."""
        legacy_dir = EVAL / "golden"
        if not legacy_dir.exists():
            return []

        tasks = []
        for f in legacy_dir.glob("*.json"):
            if f.name.startswith("golden_"):
                continue  # legacy format
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    tasks.extend(data)
                else:
                    tasks.append(data)
            except Exception:
                continue
        return tasks

    def _load_expanded(self) -> List[Dict]:
        """Загрузить расширенный корпус (20+ задач)."""
        expanded_file = EVAL / "golden" / "new_golden_tasks.json"
        if not expanded_file.exists():
            return []

        try:
            data = json.loads(expanded_file.read_text())
            return data.get("tasks", [])
        except Exception:
            return []

    def get_by_vector(self, vector: str = None) -> List[Dict]:
        """Фильтровать задачи по вектору."""
        all_tasks = self.load("all")
        if vector:
            return [t for t in all_tasks if t.get("vector") == vector]
        return all_tasks

    def get_summary(self) -> Dict:
        """Возвращает сводку по корпусу задач."""
        all_tasks = self.load("all")

        summary = {
            "total": len(all_tasks),
            "by_vector": {},
            "by_test_type": {},
        }

        for task in all_tasks:
            vec = task.get("vector", "unknown")
            test_type = task.get("test_type", "unknown")

            summary["by_vector"][vec] = summary["by_vector"].get(vec, 0) + 1
            summary["by_test_type"][test_type] = summary["by_test_type"].get(test_type, 0) + 1

        return summary

if __name__ == "__main__":
    loader = GoldenTasksLoader()

    print("📊 Golden Corpus Summary:")
    summary = loader.get_summary()
    print(f"  Total tasks: {summary['total']}")
    print("  By vector:")
    for vec, count in summary["by_vector"].items():
        print(f"    {vec}: {count}")
    print("  By test type:")
    for ttype, count in summary["by_test_type"].items():
        print(f"    {ttype}: {count}")

    print("\n🧪 Legacy tasks:", len(loader.load("legacy")))
    print("🧪 Expanded tasks:", len(loader.load("expanded")))
    print("🧪 All tasks:", len(loader.load("all")))
