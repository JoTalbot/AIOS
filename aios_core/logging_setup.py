import logging
import os
import sys

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
            ],
            traces_sample_rate=1.0,
            environment=os.getenv("ENVIRONMENT", "development")
        )
        print("[INFO] Sentry initialized")
    else:
        print("[INFO] SENTRY_DSN not set, skipping Sentry")
except ImportError:
    print("[INFO] sentry-sdk not installed, skipping")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout
)
