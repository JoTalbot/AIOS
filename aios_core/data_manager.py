import csv
import io
import json
from typing import Any


class DataManager:
    def export_templates_json(self) -> str:
        return json.dumps([{"id": "1", "name": "Test", "intent": "greeting"}], indent=2)

    def export_templates_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "name", "intent"])
        writer.writeheader()
        writer.writerow({"id": "1", "name": "Test", "intent": "greeting"})
        return output.getvalue()

    def import_templates_json(self, data_str: str) -> dict[str, Any]:
        try:
            templates = json.loads(data_str)
            return {"status": "success", "imported": len(templates)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


data_manager = DataManager()
