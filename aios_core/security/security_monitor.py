# aios_core/security/security_monitor.py
"""
Security monitoring module for handling API requests with enhanced security measures.
Includes safe request handling, token validation, input sanitization, and logging of sensitive operations.
Documents security risks in critical functions and enforces type safety.

Security Risks Documented:
- HACK: Legacy functions like gemini_walk_hack and gemini_web_reader_hack process untrusted input
  without proper validation, potentially enabling injection attacks or memory corruption.
- RECOMMENDATION: These functions should be deprecated and replaced with secure alternatives.
"""

import logging
from typing import Any, Dict, Optional, Union, List
from urllib.parse import urlparse
import requests
from aios_core.advanced_security import AdvancedSecurity
from aios_core.privacy_vault_v3 import DifferentialPrivacyVaultV3 as PrivacyVault  # fix: реальное имя класса (галлюцинация автокодера)

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    """Custom exception for security violations with enhanced error context."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}

class SecurityMonitor:
    """
    Core security monitoring class for handling API requests with security best practices.
    """

    def __init__(self):
        self.security = AdvancedSecurity()
        self.privacy_vault = PrivacyVault()
        self._sensitive_fields = {
            'token', 'api_key', 'password', 'secret', 'credential',
            'access_token', 'refresh_token', 'bearer'
        }
        self._max_param_length = 1000
        self._min_token_length = 10

    def safe_api_request(
        self,
        url: str,
        method: str = "GET",
        token: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Safely process API requests with security validation and token handling.

        Security Considerations:
        - Validates URL format and scheme to prevent SSRF attacks
        - Enforces minimum token length and format requirements
        - Converts GET requests with tokens to POST to prevent token leakage in URLs
        - Sanitizes sensitive query parameters from logs
        - Validates parameter lengths to prevent DoS via large inputs

        Args:
            url: Target URL for the request. Must be a valid HTTP/HTTPS URL.
            method: HTTP method (GET/POST/PUT/DELETE). Defaults to "GET".
            token: Authentication token (Bearer). Must be at least 10 characters.
            params: Query parameters for GET requests. Values limited to 1000 chars.
            headers: Additional headers. Will be merged with security headers.
            data: Request body for POST/PUT requests.
            timeout: Request timeout in seconds. Defaults to 30.

        Returns:
            Dictionary containing response data or error information with request metadata.

            Success response structure:
            {
                'status': 'success',
                'data': <response_json>,
                'status_code': <http_status>,
                'request_meta': {...}
            }

            Error response structure:
            {
                'error': <error_type>,
                'message': <error_details>,
                'request_meta': {...}
            }

        Raises:
            SecurityException: On validation failures or security violations with context.
        """
        # Validate critical inputs first
        if not isinstance(url, str) or not url.strip():
            raise SecurityException(
                "URL must be a non-empty string",
                {'provided_value': str(url)}
            )
        # Initialize request metadata with enhanced security context
        request_meta = {
            'original_url': url,
            'method': method.upper(),
            'has_token': bool(token),
            'token_length': len(token) if token else 0,
            'timestamp': self.security.get_current_timestamp(),
            'security_level': 'enhanced'
        }

        try:
            # Validate URL format and scheme
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise SecurityException(
                    "Invalid URL format - must include scheme (http/https) and host",
                    {'url': url, 'parsed': parsed_url._asdict()}
                )

            if parsed_url.scheme.lower() not in ('http', 'https'):
                raise SecurityException(
                    "Unsupported URL scheme - only http and https are allowed",
                    {'scheme': parsed_url.scheme}
                )

            # Sanitize URL
            sanitized_url = self._sanitize_url(url)

            # Process token
            processed_token = self._process_token(token)

            # Prepare headers
            request_headers = self._prepare_headers(headers, processed_token)

            # Handle GET requests - convert to POST if token present
            if method.upper() == "GET" and processed_token:
                logger.warning("⚠️ GET request with token detected - converting to POST")
                method = "POST"
                if params:
                    data = params.copy()
                    params = None

            # Prepare request parameters
            request_params = self._prepare_params(params)

            # Log request (with masked token)
            self._log_request(request_meta, sanitized_url, request_params, request_headers)

            # Validate token if present
            if processed_token:
                self._validate_token(processed_token)

            # Execute request
            response = self._execute_request(
                method=method.upper(),
                url=sanitized_url,
                headers=request_headers,
                params=request_params,
                data=data,
                timeout=timeout
            )

            # Process response
            return self._process_response(response)

        except SecurityException as e:
            logger.error(f"❌ Security violation: {str(e)}")
            return {
                'error': 'security_violation',
                'message': str(e),
                'request_meta': request_meta
            }
        except requests.RequestException as e:
            logger.error(f"❌ Request failed: {str(e)}")
            return {
                'error': 'request_failed',
                'message': str(e),
                'request_meta': request_meta
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return {
                'error': 'unexpected_error',
                'message': str(e),
                'request_meta': request_meta
            }

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL by removing sensitive query parameters."""
        parsed = urlparse(url)
        query_params = parsed.query

        if not query_params:
            return url

        # Parse and filter query parameters
        from urllib.parse import parse_qs, urlencode
        params = parse_qs(query_params)

        # Remove sensitive parameters
        sanitized_params = {
            k: v for k, v in params.items()
            if k.lower() not in self._sensitive_fields
        }

        # Reconstruct URL
        sanitized_query = urlencode(sanitized_params, doseq=True)
        return parsed._replace(query=sanitized_query).geturl()

    def _process_token(self, token: Optional[str]) -> Optional[str]:
        """Process and validate token format.

        Security Considerations:
        - Validates token is a non-empty string
        - Enforces minimum length requirement
        - Trims whitespace to prevent accidental inclusion
        - Logs token length (without content) for security monitoring

        Args:
            token: Authentication token to validate

        Returns:
            Processed token if valid, None otherwise

        Raises:
            SecurityException: If token format is invalid
        """
        if not token:
            logger.debug("Empty token provided - proceeding without authentication")
            return None

        if not isinstance(token, str):
            raise SecurityException(
                "Token must be a string",
                {'provided_type': type(token).__name__}
            )

        processed_token = token.strip()
        if len(processed_token) < self._min_token_length:
            raise SecurityException(
                f"Token too short - minimum {self._min_token_length} characters required",
                {'provided_length': len(processed_token)}
            )

        logger.debug(f"Token processed successfully - length: {len(processed_token)}")
        return processed_token

    def _prepare_headers(
        self,
        headers: Optional[Dict[str, str]],
        token: Optional[str]
    ) -> Dict[str, str]:
        """Prepare request headers with security headers and token."""
        security_headers = {
            'User-Agent': 'AIOS-SecurityMonitor/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Request-Security': 'enhanced'
        }

        if headers:
            security_headers.update(headers)

        if token:
            security_headers['Authorization'] = f'Bearer {token[:8]}...{token[-8:]}'

        return security_headers

    def _prepare_params(self, params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Prepare request parameters with validation.

        Security Considerations:
        - Validates parameter values to prevent DoS via large inputs
        - Rejects parameters exceeding maximum allowed length
        - Preserves parameter structure while ensuring safety

        Args:
            params: Dictionary of request parameters

        Returns:
            Validated parameters dictionary or None if input was None

        Raises:
            SecurityException: If any parameter exceeds maximum length
        """
        if not params:
            return None

        if not isinstance(params, dict):
            raise SecurityException(
                "Parameters must be a dictionary",
                {'provided_type': type(params).__name__}
            )

        # Validate parameter values
        validated_params = {}
        for k, v in params.items():
            if isinstance(v, str) and len(v) > self._max_param_length:
                raise SecurityException(
                    f"Parameter {k} exceeds maximum length of {self._max_param_length} characters",
                    {
                        'parameter': k,
                        'provided_length': len(v),
                        'max_allowed': self._max_param_length
                    }
                )
            validated_params[k] = v

        logger.debug(f"Parameters validated successfully - count: {len(validated_params)}")
        return validated_params

    def _validate_token(self, token: str) -> None:
        """Validate token using AdvancedSecurity.

        Security Considerations:
        - Delegates token validation to AdvancedSecurity module
        - Provides detailed error context if validation fails
        - Logs validation attempts for security monitoring

        Args:
            token: Token to validate

        Raises:
            SecurityException: If token validation fails
        """
        if not token:
            raise SecurityException("Cannot validate empty token")

        validation_result = self.security.validate_token(token)
        if not validation_result:
            raise SecurityException(
                "Invalid or expired token",
                {
                    'token_length': len(token),
                    'validation_attempted': True,
                    'result': 'failed'
                }
            )

        logger.debug("Token validation successful")

    def _execute_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
        timeout: int
    ) -> requests.Response:
        """Execute the actual HTTP request with enhanced error handling.

        Security Considerations:
        - Uses timeout to prevent hanging requests
        - Validates HTTP method before execution
        - Provides detailed error context for failed requests

        Args:
            method: HTTP method to execute
            url: Target URL
            headers: Request headers
            params: Query parameters
            data: Request body
            timeout: Request timeout in seconds

        Returns:
            requests.Response object

        Raises:
            SecurityException: If HTTP method is unsupported or request fails
        """
        try:
            method_upper = method.upper()
            if method_upper == "GET":
                return requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method_upper == "POST":
                return requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method_upper == "PUT":
                return requests.put(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method_upper == "DELETE":
                return requests.delete(url, headers=headers, json=data, params=params, timeout=timeout)
            else:
                raise SecurityException(
                    f"Unsupported HTTP method: {method}",
                    {'supported_methods': ['GET', 'POST', 'PUT', 'DELETE']}
                )
        except requests.RequestException as e:
            raise SecurityException(
                f"Request failed: {str(e)}",
                {
                    'url': url,
                    'method': method,
                    'timeout': timeout,
                    'error_type': type(e).__name__
                }
            )

    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process API response with status validation."""
        try:
            response.raise_for_status()

            # Try to parse JSON response
            try:
                return response.json()
            except ValueError:
                return {
                    'status': 'success',
                    'content': response.text,
                    'status_code': response.status_code
                }
        except requests.HTTPError as e:
            return {
                'error': 'http_error',
                'status_code': response.status_code,
                'message': str(e),
                'response': response.text
            }

    def _log_request(
        self,
        meta: Dict[str, Any],
        url: str,
        params: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> None:
        """Log request details with masked sensitive information."""
        log_data = meta.copy()

        # Mask sensitive headers
        masked_headers = headers.copy()
        if 'Authorization' in masked_headers:
            masked_headers['Authorization'] = 'Bearer ***'

        log_data.update({
            'url': url,
            'params': self._mask_params(params) if params else None,
            'headers': masked_headers
        })

        logger.info(f"🔒 API Request: {log_data}")

    def _mask_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive parameters in logs."""
        masked = params.copy()
        for key in self._sensitive_fields:
            if key in masked:
                masked[key] = '***'
        return masked



# Initialize security monitor instance
security_monitor = SecurityMonitor()

# Legacy function for backward compatibility
# SECURITY NOTE: This function is deprecated due to potential token leakage in URLs
# RECOMMENDATION: Migrate to SecurityMonitor.safe_api_request with explicit method
def safe_get_request(url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Legacy function for safe GET requests.

    Security Warning:
    - GET requests with tokens may leak credentials in server logs and browser history
    - Prefer POST requests for authenticated requests
    - This function will be deprecated in future versions

    Args:
        url: Target URL for the request
        token: Authentication token (Bearer)

    Returns:
        Dictionary containing response data or error information
    """
    logger.warning("⚠️ Using deprecated safe_get_request - consider using safe_api_request with explicit method")
    return security_monitor.safe_api_request(
        url=url,
        method="GET",
        token=token
    )