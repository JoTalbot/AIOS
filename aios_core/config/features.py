import os
from typing import Dict, Any

class FeatureFlags:
    DEFAULTS = {
        "LLM_ENABLED": False,
        "TELEGRAM_BOT_ENABLED": False,
        "EMAIL_NOTIFICATIONS": False,
        "SMS_NOTIFICATIONS": False,
        "DYNAMIC_PRICING": True,
        "SENTIMENT_ANALYSIS": True,
        "COMPLIANCE_GUARD": True,
        "MULTI_AGENT_SYSTEM": True,
        "REDIS_CACHE": True,
        "AUDIT_LOGGING": True,
        "PLATFORM_OLX": True,
        "PLATFORM_INSTAGRAM": True,
        "PLATFORM_PROM": True,
        "PLATFORM_FACEBOOK": True,
        "PLATFORM_VIBER": True,
        "PLATFORM_WHATSAPP": True,
    }

    def __init__(self):
        self._cache: Dict[str, bool] = {}

    def is_enabled(self, feature: str) -> bool:
        if feature in self._cache:
            return self._cache[feature]
        default = self.DEFAULTS.get(feature, False)
        env_val = os.getenv(f"FEATURE_{feature}", str(default)).lower()
        enabled = env_val in ("true", "1", "yes", "on")
        self._cache[feature] = enabled
        return enabled

    def require(self, feature: str):
        def decorator(func):
            from functools import wraps
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.is_enabled(feature):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=503, detail=f"Feature {feature} is disabled")
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def list_all(self) -> Dict[str, bool]:
        return {f: self.is_enabled(f) for f in self.DEFAULTS}

    def reload(self):
        self._cache.clear()

flags = FeatureFlags()
