"""AIOS Configuration Manager v10.8.0.

Manages configuration from files and environment
variables with schema validation, watchers, layered
config, deep merging, type coercion, and change
notification.

Classes:
    ConfigLayer    — configuration layer (file/env/override)
    ConfigManager  — full configuration management engine
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Try yaml import
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Try json as fallback
import json


@dataclass
class ConfigLayer:
    """Configuration layer with source tracking."""

    name: str
    source: str  # "file", "env", "override", "default"
    config: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # higher = more important
    loaded_at: float = field(default_factory=time.time)


class ConfigManager:
    """Full configuration management engine.

    Features:
    - YAML/JSON file loading
    - Environment variable override
    - Layered configuration (multiple sources with priorities)
    - Deep merging of configs
    - Schema validation (basic type checking)
    - Type coercion (strings → ints/floats/bools)
    - Change notification callbacks
    - Config watching (file reload)
    - Override management
    """

    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.layers: list[ConfigLayer] = []
        self._watchers: list[Callable] = []
        self._schema: dict[str, type] = {}
        self._defaults: dict[str, Any] = {}

    # ── Loading ────────────────────────────────────────────────────

    def load(self) -> None:
        """Load configuration from file and environment (backward-compatible)."""
        # Add default layer
        self._add_layer("defaults", "default", self._defaults, priority=0)

        # Add file layer
        file_config = self._load_file(self.config_path)
        self._add_layer("file", "file", file_config, priority=10)

        # Override with environment variables
        env_config = self._load_env()
        self._add_layer("env", "env", env_config, priority=20)

        # Merge all layers
        self._merge_layers()

    def _load_file(self, path: str) -> dict[str, Any]:
        """Load configuration from a YAML or JSON file."""
        if not os.path.exists(path):
            return {}

        if (HAS_YAML and path.endswith(".yaml")) or path.endswith(".yml"):
            with open(path) as f:
                return yaml.safe_load(f) or {}
        else:
            try:
                with open(path) as f:
                    if path.endswith(".json"):
                        return json.load(f)
                    elif HAS_YAML:
                        return yaml.safe_load(f) or {}
                    else:
                        return json.load(f)
            except Exception:
                return {}

    def _load_env(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        prefix = "AIOS_"
        for key in os.environ:
            if key.startswith(prefix):
                config_key = key[len(prefix) :].lower()
                env_config[config_key] = self._coerce_value(os.environ[key])
        return env_config

    def _coerce_value(self, value: str) -> Any:
        """Coerce string value to appropriate type."""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    # ── Layer Management ────────────────────────────────────────────

    def _add_layer(
        self, name: str, source: str, config: dict[str, Any], priority: int = 0
    ) -> ConfigLayer:
        """Add a configuration layer."""
        layer = ConfigLayer(name=name, source=source, config=config, priority=priority)
        self.layers.append(layer)
        self.layers.sort(key=lambda l: l.priority, reverse=True)
        return layer

    def _merge_layers(self) -> None:
        """Deep merge all layers (highest priority wins)."""
        merged = {}
        for layer in sorted(self.layers, key=lambda l: l.priority):
            merged = self._deep_merge(merged, layer.config)
        self.config = merged

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def add_override(self, overrides: dict[str, Any], priority: int = 30) -> None:
        """Add an override layer."""
        self._add_layer("override", "override", overrides, priority=priority)
        self._merge_layers()
        self._notify_watchers()

    # ── Access ──────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value (backward-compatible)."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value (creates override layer)."""
        self.add_override({key: value})

    def get_nested(self, dotted_key: str, default: Any = None) -> Any:
        """Get nested config value using dot notation (e.g., 'server.port')."""
        keys = dotted_key.split(".")
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    # ── Schema Validation ──────────────────────────────────────────

    def set_schema(self, schema: dict[str, type]) -> None:
        """Set validation schema (key → expected type)."""
        self._schema = schema

    def validate(self) -> dict[str, Any]:
        """Validate config against schema."""
        errors = {}
        for key, expected_type in self._schema.items():
            value = self.config.get(key)
            if value is not None and not isinstance(value, expected_type):
                errors[key] = (
                    f"Expected {expected_type.__name__}, got {type(value).__name__}"
                )
        return {"valid": len(errors) == 0, "errors": errors}

    # ── Defaults ────────────────────────────────────────────────────

    def set_default(self, key: str, value: Any) -> None:
        """Set a default value."""
        self._defaults[key] = value

    def set_defaults(self, defaults: dict[str, Any]) -> None:
        """Set multiple default values."""
        self._defaults.update(defaults)

    # ── Saving ──────────────────────────────────────────────────────

    def save(self) -> None:
        """Save configuration to file (backward-compatible)."""
        if HAS_YAML and (
            self.config_path.endswith(".yaml") or self.config_path.endswith(".yml")
        ):
            with open(self.config_path, "w") as f:
                yaml.dump(self.config, f)
        else:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)

    # ── Watchers ────────────────────────────────────────────────────

    def add_watcher(self, callback: Callable) -> None:
        """Add a callback to be notified on config changes."""
        self._watchers.append(callback)

    def _notify_watchers(self) -> None:
        """Notify all watchers of a config change."""
        for watcher in self._watchers:
            try:
                watcher(self.config)
            except Exception as e:
                logger.warning(f"Config watcher error: {e}")

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "keys": len(self.config),
            "source": self.config_path,
            "layers": len(self.layers),
            "has_yaml": HAS_YAML,
            "schema_size": len(self._schema),
            "watchers": len(self._watchers),
        }
