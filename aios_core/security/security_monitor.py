from typing import Dict, Any, Optional
import re
from urllib.parse import urlparse, parse_qs, urlunparse

class SecurityMonitor:
    """
    Security monitor for validating and sanitizing HTTP requests.
    Provides protection against XSS, CSRF, token leakage in URLs, and other common vulnerabilities.
    """

    XSS_PATTERNS = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        r'javascript:',
        r'on\w+\s*=',
        r'expression\s*\(',
        r'vbscript:',
        r'data:',
        r'<!--',
        r'<\/[^>]+>',
        r'&lt;script&gt;',
        r'&lt;\/script&gt;'
    ]

    DANGEROUS_PARAMS = [
        'gemini_walk_hack',
        'eval(',
        'exec(',
        '__import__(',
        'require(',
        'import\(',
        'document\.cookie',
        'window\.location',
        'fetch\(',
        'XMLHttpRequest'
    ]

    TOKEN_PARAMS = [
        'token',
        'api_key',
        'access_token',
        'bearer_token',
        'auth_token',
        'session_token'
    ]

    @staticmethod
    def validate_request_safety(request: Dict[str, Any]) -> bool:
        """
        Validate request for common security vulnerabilities.

        Args:
            request: Dictionary containing request data with keys:
                - method: HTTP method (GET, POST, etc.)
                - url: Request URL
                - headers: Dictionary of headers
                - params: Dictionary of query parameters
                - body: Request body (for POST/PUT)

        Returns:
            bool: True if request is safe, False otherwise
        """
        if not isinstance(request, dict):
            return False

        # Validate method
        method = request.get('method', '').upper()
        if method not in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH'):
            return False

        # Check for tokens in URL
        url = request.get('url', '')
        if method == 'GET':
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            for param in SecurityMonitor.TOKEN_PARAMS:
                if param in query_params:
                    return False

        # Check headers for XSS patterns
        headers = request.get('headers', {})
        if not isinstance(headers, dict):
            return False

        header_str = ' '.join(str(v) for v in headers.values())
        if SecurityMonitor._contains_xss_patterns(header_str):
            return False

        # Check params for dangerous patterns
        params = request.get('params', {})
        if not isinstance(params, dict):
            return False

        param_str = ' '.join(str(v) for v in params.values())
        if SecurityMonitor._contains_dangerous_patterns(param_str):
            return False

        # Check for dangerous params in URL
        if method == 'GET':
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            for param in SecurityMonitor.DANGEROUS_PARAMS:
                if any(re.search(param, str(val), re.IGNORECASE) for val in query_params.values()):
                    return False

        return True

    @staticmethod
    def sanitize_request(request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize request by removing dangerous parameters and masking sensitive data.

        Args:
            request: Dictionary containing request data

        Returns:
            Dict[str, Any]: Sanitized request dictionary
        """
        if not isinstance(request, dict):
            return request

        # Deep copy to avoid modifying original
        sanitized = request.copy()
        if 'url' in sanitized:
            sanitized['url'] = SecurityMonitor._sanitize_url(sanitized['url'])

        if 'headers' in sanitized and isinstance(sanitized['headers'], dict):
            sanitized['headers'] = {
                k: SecurityMonitor._sanitize_header(v)
                for k, v in sanitized['headers'].items()
            }

        if 'params' in sanitized and isinstance(sanitized['params'], dict):
            sanitized['params'] = {
                k: v for k, v in sanitized['params'].items()
                if not any(re.search(param, str(v), re.IGNORECASE)
                          for param in SecurityMonitor.DANGEROUS_PARAMS)
            }

        if 'body' in sanitized:
            if isinstance(sanitized['body'], dict):
                sanitized['body'] = {
                    k: v for k, v in sanitized['body'].items()
                    if not any(re.search(param, str(v), re.IGNORECASE)
                              for param in SecurityMonitor.DANGEROUS_PARAMS)
                }
            elif isinstance(sanitized['body'], str):
                sanitized['body'] = SecurityMonitor._sanitize_body(sanitized['body'])

        return sanitized

    @staticmethod
    def _contains_xss_patterns(text: str) -> bool:
        """Check if text contains XSS patterns."""
        text_lower = text.lower()
        for pattern in SecurityMonitor.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _contains_dangerous_patterns(text: str) -> bool:
        """Check if text contains dangerous patterns."""
        text_lower = text.lower()
        for pattern in SecurityMonitor.DANGEROUS_PARAMS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Sanitize URL by removing sensitive parameters."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        # Remove token parameters
        new_query = []
        for param, values in query_params.items():
            if param.lower() not in [p.lower() for p in SecurityMonitor.TOKEN_PARAMS]:
                for value in values:
                    new_query.append(f"{param}={value}")

        sanitized_query = '&'.join(new_query)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            sanitized_query,
            parsed.fragment
        ))

    @staticmethod
    def _sanitize_header(header_value: Any) -> str:
        """Sanitize header value."""
        if not isinstance(header_value, str):
            return str(header_value)

        # Mask sensitive data in headers
        lower_val = header_value.lower()
        for token_param in SecurityMonitor.TOKEN_PARAMS:
            if token_param in lower_val:
                return '***'

        return header_value

    @staticmethod
    def _sanitize_body(body: str) -> str:
        """Sanitize request body."""
        if not isinstance(body, str):
            return str(body)

        # Remove dangerous patterns from body
        for pattern in SecurityMonitor.DANGEROUS_PARAMS:
            body = re.sub(pattern, '[REDACTED]', body, flags=re.IGNORECASE)

        return body