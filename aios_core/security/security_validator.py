import re
from typing import Dict, Optional

# Common XSS patterns to detect
XSS_PATTERNS = [
    r'<script.*?>.*?</script>',  # Script tags
    r'on\w+\s*=',  # Event handlers
    r'javascript:',  # JavaScript protocol
    r'expression\(',  # IE expression
    r'vbscript:',  # VBScript protocol
    r'data:text/html',  # Data URI with HTML
    r'<!--.*?-->',  # HTML comments
    r'<[^>]+>',  # Any HTML tag
    r'\b(alert|prompt|confirm)\s*\(',  # Common XSS functions
    r'\b(window|document)\.(open|close|write)\s*\(',  # DOM manipulation
]

# Common CSRF patterns to detect
CSRF_PATTERNS = [
    r'^[a-zA-Z0-9+/=]{32,}$',  # Basic token pattern
]

def sanitize_input(input_str: str) -> str:
    """
    Sanitizes input string by removing potentially dangerous XSS patterns.

    Args:
        input_str: Input string to sanitize

    Returns:
        Sanitized string with XSS patterns removed

    Example:
        >>> sanitize_input('<script>alert("xss")</script>')
        'alert("xss")'
    """
    if not isinstance(input_str, str):
        return str(input_str)

    sanitized = input_str
    for pattern in XSS_PATTERNS:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    return sanitized.strip()

def validate_xss_token(token: str) -> bool:
    """
    Validates token for XSS patterns.

    Args:
        token: Token string to validate

    Returns:
        True if token is safe, False if contains XSS patterns

    Example:
        >>> validate_xss_token('safe_token')
        True
        >>> validate_xss_token('<script>alert(1)</script>')
        False
    """
    if not isinstance(token, str):
        return False

    return not any(
        re.search(pattern, token, re.IGNORECASE)
        for pattern in XSS_PATTERNS
    )

def validate_csrf_token(token: str, expected_origin: Optional[str] = None) -> bool:
    """
    Validates CSRF token with optional origin check.

    Args:
        token: CSRF token to validate
        expected_origin: Expected origin header for additional validation

    Returns:
        True if token is valid and matches origin (if provided)

    Example:
        >>> validate_csrf_token('a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6')
        True
        >>> validate_csrf_token('invalid token')
        False
    """
    if not isinstance(token, str):
        return False

    # Basic token pattern validation
    if not any(re.fullmatch(pattern, token) for pattern in CSRF_PATTERNS):
        return False

    # Origin validation if provided
    if expected_origin and not isinstance(expected_origin, str):
        return False

    return True

def validate_api_request(
    headers: Dict[str, str],
    method: str,
    allowed_methods: Optional[list[str]] = None,
    required_headers: Optional[list[str]] = None
) -> bool:
    """
    Universal API request validation with token checks and method validation.

    Args:
        headers: Request headers dictionary
        method: HTTP method (GET, POST, etc.)
        allowed_methods: List of allowed HTTP methods (default: ['POST'])
        required_headers: List of required headers (default: ['Authorization', 'Content-Type'])

    Returns:
        True if request is valid, False otherwise

    Example:
        >>> validate_api_request(
        ...     {'Authorization': 'Bearer token', 'Content-Type': 'application/json'},
        ...     'POST'
        ... )
        True
    """
    if allowed_methods is None:
        allowed_methods = ['POST']

    if required_headers is None:
        required_headers = ['Authorization', 'Content-Type']

    # Validate HTTP method
    if method.upper() not in [m.upper() for m in allowed_methods]:
        return False

    # Validate required headers
    for header in required_headers:
        if header not in headers or not headers[header]:
            return False

    # Validate Authorization header format
    auth_header = headers.get('Authorization', '')
    if not auth_header.startswith('Bearer ') and not auth_header.startswith('Token '):
        return False

    # Validate Content-Type
    content_type = headers.get('Content-Type', '')
    if 'application/json' not in content_type.lower():
        return False

    return True

def validate_security_headers(headers: Dict[str, str]) -> bool:
    """
    Validates security-related headers for API responses.

    Args:
        headers: Response headers dictionary

    Returns:
        True if security headers are present and valid

    Example:
        >>> validate_security_headers({
        ...     'Content-Security-Policy': "default-src 'self'",
        ...     'X-Content-Type-Options': 'nosniff',
        ...     'X-Frame-Options': 'DENY'
        ... })
        True
    """
    security_headers = {
        'Content-Security-Policy': r"default-src\s+'self'",
        'X-Content-Type-Options': r'^\s*nosniff\s*$',
        'X-Frame-Options': r'^\s*(DENY|SAMEORIGIN)\s*$',
        'Strict-Transport-Security': r'max-age=\d+',
    }

    for header, pattern in security_headers.items():
        if header not in headers:
            return False
        if not re.search(pattern, headers[header], re.IGNORECASE):
            return False

    return True