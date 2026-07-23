"""APK Function & User API Profile Converter for AIOS.

Extracts components, intents, and exported capabilities from Android APK files,
converting them into registered AIOS Capability instances, RBAC User API profiles,
and REST execution routes.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .autonomy_manager import AutonomyLevel
from .capability_engine import Capability, CapabilityEngine

__all__ = ["APKFunctionConverter"]


class APKFunctionConverter:
    """Converts Android APK component signatures into AIOS User API Profiles."""

    def __init__(self, capability_engine: Optional[CapabilityEngine] = None):
        self.capability_engine = capability_engine
        self.converted_profiles: Dict[str, dict[str, Any]] = {}

    def convert_apk_functions_to_api_profile(
        self,
        apk_name: str,
        package_name: str,
        exported_components: List[dict[str, Any]],
        target_user_id: str = "default_user",
    ) -> dict[str, Any]:
        """Convert APK components (Activities, Services, Receivers) into AIOS User API Capabilities and Profile."""
        start_time = time.time()
        converted_capabilities: List[dict[str, Any]] = []

        for comp in exported_components:
            comp_name = comp.get("name", "UnknownComponent")
            comp_type = comp.get(
                "type", "activity"
            )  # "activity", "service", "receiver", "provider"
            intent_filter = comp.get("intent_filter", "android.intent.action.MAIN")

            # Formulate AIOS Capability name and API route
            cap_id = f"apk_{package_name.replace('.', '_')}_{comp_name.replace('.', '_')}".lower()
            api_route = f"/api/v1/users/profiles/{target_user_id}/apk/{package_name}/{comp_name}"

            cap_entry = {
                "capability_id": cap_id,
                "name": f"APK:{package_name}:{comp_name}",
                "component_type": comp_type,
                "intent_action": intent_filter,
                "api_endpoint": api_route,
                "required_autonomy_level": AutonomyLevel.LEVEL_2_SUPERVISED.value,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "intent_extras": {"type": "object"},
                        "flags": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "status": "active",
            }

            converted_capabilities.append(cap_entry)

            # Register into capability engine if connected
            if self.capability_engine:
                try:
                    self.capability_engine.register_capability(
                        name=cap_entry["name"],
                        capability_type=f"apk_{comp_type}",
                        description=f"Automated APK conversion for component {comp_name}",
                        input_schema=cap_entry["input_schema"],
                    )
                except Exception:
                    pass  # Skip malformed capability entries during conversion

        profile_id = f"profile_apk_{package_name.replace('.', '_')}"
        user_api_profile = {
            "profile_id": profile_id,
            "user_id": target_user_id,
            "apk_name": apk_name,
            "package_name": package_name,
            "total_converted_capabilities": len(converted_capabilities),
            "converted_capabilities": converted_capabilities,
            "created_at": time.time(),
            "conversion_latency_ms": round((time.time() - start_time) * 1000.0, 3),
        }

        self.converted_profiles[profile_id] = user_api_profile
        return user_api_profile

    def get_user_profiles(self, user_id: str) -> List[dict[str, Any]]:
        """Retrieve all converted APK API profiles for a specific user."""
        return [p for p in self.converted_profiles.values() if p["user_id"] == user_id]

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        total_caps = sum(
            p["total_converted_capabilities"] for p in self.converted_profiles.values()
        )
        return {
            "total_profiles": len(self.converted_profiles),
            "total_converted_capabilities": total_caps,
        }
