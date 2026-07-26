import os
import json
from typing import Dict, List

class FineTuningPipeline:
    def __init__(self):
        self.base_model = os.getenv("FT_BASE_MODEL", "meta-llama/Llama-3-8B")
        self.output_dir = "./data/fine_tuned_models"
    
    def prepare_dataset(self, conversations: List[Dict]) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = f"{self.output_dir}/dataset.jsonl"
        with open(path, "w") as f:
            for c in conversations:
                f.write(json.dumps({"messages": [{"role": c["role"], "content": c["content"]}]}) + "\n")
        return path
    
    def get_config(self) -> Dict:
        return {"model": self.base_model, "method": "qlora", "lora_r": 16, "epochs": 3}

fine_tuning_pipeline = FineTuningPipeline()
