# aios_core/security/security_monitor.py
"""
Security monitoring module for handling API requests with enhanced security measures.
Includes safe request handling, token validation, and logging of sensitive operations.
"""

import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse
import requests
from aios_core.advanced_security import AdvancedSecurity
from aios_core.privacy_vault_v3 import DifferentialPrivacyVaultV3 as PrivacyVault  # fix: реальное имя класса (галлюцинация автокодера)

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """
    Core security monitoring class for handling API requests with security best practices.
    Features enhanced threat detection and response capabilities.
    """

    def __init__(self):
        self.security = AdvancedSecurity()
        self.privacy_vault = PrivacyVault()
        self._sensitive_fields = {
            'token', 'api_key', 'password', 'secret', 'credential',
            'access_token', 'refresh_token', 'bearer'
        }
        self._threat_types = {
            'xss', 'injection', 'csrf', 'ssrf', 'id-theft',
            'memory-leak', 'dos', 'brute-force', 'replay'
        }

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

        Args:
            url: Target URL for the request
            method: HTTP method (GET/POST/PUT/DELETE)
            token: Authentication token (Bearer)
            params: Query parameters for GET requests
            headers: Additional headers
            data: Request body for POST/PUT requests
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing response data or error information

        Raises:
            SecurityException: On validation failures or security violations
        """
        # Validate input parameters
        if not isinstance(url, str) or not url.strip():
            raise SecurityException("URL must be a non-empty string")

        if method.upper() not in ("GET", "POST", "PUT", "DELETE"):
            raise SecurityException(f"Unsupported HTTP method: {method}")

        if params is not None and not isinstance(params, dict):
            raise SecurityException("Params must be a dictionary or None")

        if headers is not None and not isinstance(headers, dict):
            raise SecurityException("Headers must be a dictionary or None")

        if data is not None and not isinstance(data, dict):
            raise SecurityException("Data must be a dictionary or None")
        # Initialize request metadata with enhanced security tracking
        request_meta = {
            'original_url': url,
            'method': method.upper(),
            'has_token': bool(token),
            'timestamp': self.security.get_current_timestamp(),
            'security_level': 'enhanced'
        }

        try:
            # Validate URL
            if not url or not isinstance(url, str):
                raise SecurityException("URL must be a non-empty string")

            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise SecurityException("Invalid URL format")

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
        """Process and validate token format."""
        if not token:
            return None

        # Basic token validation
        if not isinstance(token, str) or len(token.strip()) < 10:
            raise SecurityException("Invalid token format")

        return token.strip()

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
        """Prepare request parameters with validation."""
        if not params:
            return None

        # Validate parameter values
        validated_params = {}
        for k, v in params.items():
            if isinstance(v, str) and len(v) > 1000:
                raise SecurityException(f"Parameter {k} exceeds maximum length")
            validated_params[k] = v

        return validated_params

    def _validate_token(self, token: str) -> None:
        """Validate token using AdvancedSecurity."""
        if not self.security.validate_token(token):
            raise SecurityException("Invalid or expired token")

    def _execute_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
        timeout: int
    ) -> requests.Response:
        """Execute the actual HTTP request."""
        try:
            if method == "GET":
                return requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == "POST":
                return requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method == "PUT":
                return requests.put(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method == "DELETE":
                return requests.delete(url, headers=headers, json=data, params=params, timeout=timeout)
            else:
                raise SecurityException(f"Unsupported HTTP method: {method}")
        except requests.RequestException as e:
            raise SecurityException(f"Request failed: {str(e)}")

    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process API response with status validation and threat detection."""
        try:
            # Validate response status
            response.raise_for_status()

            # Try to parse JSON response
            try:
                json_data = response.json()
                logger.info(f"✅ Successfully processed response with status {response.status_code}")

                # Check for potential threats in response
                if isinstance(json_data, dict):
                    self._check_response_threats(json_data)

                return json_data
            except ValueError as e:
                logger.warning(f"⚠️ Non-JSON response received: {str(e)}")
                return {
                    'status': 'success',
                    'content': response.text,
                    'status_code': response.status_code
                }
        except requests.HTTPError as e:
            logger.error(f"❌ HTTP error occurred: {str(e)}")
            return {
                'error': 'http_error',
                'status_code': response.status_code,
                'message': str(e),
                'response': response.text
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error processing response: {str(e)}")
            raise SecurityException(f"Response processing failed: {str(e)}")

    def _log_request(
        self,
        meta: Dict[str, Any],
        url: str,
        params: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> None:
        """Log request details with masked sensitive information and security markers."""
        log_data = meta.copy()

        # Mask sensitive headers
        masked_headers = headers.copy()
        if 'Authorization' in masked_headers:
            masked_headers['Authorization'] = 'Bearer ***'

        log_data.update({
            'url': url,
            'params': self._mask_params(params) if params else None,
            'headers': masked_headers,
            'security_status': 'validated'
        })

        logger.info(f"🔒 API Request: {log_data}")

    def _check_response_threats(self, response_data: Dict[str, Any]) -> None:
        """Check response data for potential security threats."""
        if not isinstance(response_data, dict):
            return

        threats = response_data.get('threats', [])
        if not isinstance(threats, list):
            logger.warning(f"⚠️ Invalid threats format in response: {type(threats)}")
            return

        # Filter threats by allowed types and priority
        filtered_threats = [
            t for t in threats
            if isinstance(t, dict) and
            t.get('type') in self._threat_types and
            t.get('priority', 0) > 0
        ]

        if filtered_threats:
            logger.warning(f"⚠️ Detected {len(filtered_threats)} potential threats in response")
            for threat in filtered_threats:
                logger.warning(f"  - Threat type: {threat.get('type')}, priority: {threat.get('priority')}")

        # Check for memory-related issues
        if response_data.get('memory_usage') and response_data['memory_usage'] > 1000000:  # 1MB threshold
            logger.warning(f"⚠️ High memory usage detected: {response_data['memory_usage']} bytes")

    def _mask_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive parameters in logs."""
        masked = params.copy()
        for key in self._sensitive_fields:
            if key in masked:
                masked[key] = '***'
        return masked

class SecurityException(Exception):
    """Custom exception for security violations."""
    pass

# Initialize security monitor instance
security_monitor = SecurityMonitor()

# Legacy function for backward compatibility
def safe_get_request(url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Legacy function for safe GET requests.

    Deprecated: Use SecurityMonitor.safe_api_request instead.
    """
    return security_monitor.safe_api_request(
        url=url,
        method="GET",
        token=token
    )