"""Execution trace identifiers."""

import uuid


def create_trace_id():
    return str(uuid.uuid4())
