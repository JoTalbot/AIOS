"""Uvicorn entrypoint for the AIOS control plane.

Set AIOS_OPERATOR_TOKEN to enable the operator boundary. The application
factory remains injectable for tests and embedding.
"""

import os

from .app import create_app


def operator_validator(request):
    expected = os.getenv("AIOS_OPERATOR_TOKEN")
    if not expected:
        return False
    return request.headers.get("authorization") == f"Bearer {expected}"


app = create_app(operator_validator=operator_validator)
