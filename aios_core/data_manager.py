import json
import csv
import io
from typing import Dict, Any
from fastapi.responses import Response

class DataManager:
    def export_templates_json(self) -> str:
        return json.dumps([{"id": "1", "name": "Test", "intent": "greeting"}], indent=2)

    def export_templates_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "name", "intent"])
        writer.writeheader()
        writer.writerow({"id": "1", "name": "Test", "intent": "greeting"})
        return output.getvalue()

    def import_templates_json(self, data_str: str) -> Dict[str, Any]:
        try:
            templates = json.loads(data_str)
            return {"status": "success", "imported": len(templates)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

data_manager = DataManager()
