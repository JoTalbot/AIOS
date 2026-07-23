"""AIOS Python SDK v4.2.0 — Official async/sync client library.

Install::

    pip install aios-client

Usage::

    from aios_sdk import AIOSClient
    client = AIOSClient("http://localhost:8000", api_key="...")
    stats = await client.stats()
"""

from sdk.aios_sdk import AIOSClient, AIOSSyncClient  # noqa: F401

__all__ = ["AIOSClient", "AIOSSyncClient"]
__version__ = "4.2.0"
