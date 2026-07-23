"""AIOS Configuration Manager"""

import os
import yaml
from typing import Any, Dict


class ConfigManager:
    """Manages configuration from files and environment variables."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f) or {}
        # Override with environment variables
        for key in list(self.config.keys()):
            env_val = os.getenv(key.upper())
            if env_val is not None:
                self.config[key] = env_val

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value

    def save(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f)

    def stats(self) -> dict:
        return {"keys": len(self.config), "source": self.config_path}
