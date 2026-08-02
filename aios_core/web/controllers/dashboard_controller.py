# aios_core/web/middleware/csrf.py
"""
CSRF protection middleware for web controllers.
Implements token generation and validation for POST requests.
"""

from flask import request, session
import secrets
from typing import Callable, Any
from functools import wraps
from aios_core.web.utils import log_security_event

def generate_csrf_token() -> str:
    """
    Generate and store CSRF token in session.

    Returns:
        str: CSRF token (hex encoded 32-byte random value)
    """
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

def csrf_protect(f: Callable) -> Callable:
    """
    Decorator to protect view functions from CSRF attacks.

    Validates CSRF token in either:
    - X-CSRF-Token header
    - csrf_token form field
    - csrfmiddlewaretoken form field

    Args:
        f: View function to protect

    Returns:
        Callable: Wrapped view function with CSRF validation

    Raises:
        ValueError: If CSRF token is missing or invalid
    """
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = request.headers.get('X-CSRF-Token') or \
                request.form.get('csrf_token') or \
                request.form.get('csrfmiddlewaretoken')

        if not token:
            log_security_event('CSRF_TOKEN_MISSING', request.path)
            return {'error': 'CSRF token missing'}, 403

        if token != session.get('csrf_token'):
            log_security_event('CSRF_TOKEN_INVALID', request.path)
            return {'error': 'Invalid CSRF token'}, 403

        return f(*args, **kwargs)
    return wrapper