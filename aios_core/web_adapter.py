# aios_core/web_adapter.py
from pydantic import BaseModel, field_validator, ValidationError
from typing import Dict, Any, Optional, List
import re
import logging
from dataclasses import dataclass
from fastapi import Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

@dataclass
class SecurityHeaders:
    """Container for security headers with validation and default secure values."""
    content_security_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
    x_content_type_options: str = "nosniff"
    x_frame_options: str = "DENY"
    strict_transport_security: str = "max-age=31536000; includeSubDomains; preload"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"

class WebhookRequest(BaseModel):
    """
    Pydantic model for validating webhook requests with token in body.

    Args:
        token: Authentication token
        payload: Request payload data
    """
    token: str
    payload: Dict[str, Any]

    @field_validator('token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate token format and length."""
        if len(v) < 8:
            raise ValueError("Token must be at least 8 characters long")
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Token contains invalid characters")
        return v

class WebRequestSchema(BaseModel):
    """
    Pydantic model for validating incoming web requests.

    Validates security headers, sanitizes HTML content in body,
    ensures query parameters are properly structured, and validates CSRF tokens.
    """
    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [{
                "headers": {
                    "Content-Security-Policy": "default-src 'self'",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY"
                },
                "body": {"data": "value"},
                "query_params": {"param": "value"}
            }]
        }
    }

    headers: Dict[str, str]
    body: Dict[str, Any]
    query_params: Dict[str, str]

    @field_validator('headers')
    @classmethod
    def validate_security_headers(cls, v: Dict[str, str]) -> Dict[str, str]:
        """
        Validate presence and basic format of security headers.

        Args:
            v: Dictionary of HTTP headers

        Returns:
            Validated headers dictionary

        Raises:
            ValueError: If required security headers are missing or malformed
        """
        required_headers = {
            'Content-Security-Policy': str,
            'X-Content-Type-Options': str,
            'X-Frame-Options': str
        }

        for header, expected_type in required_headers.items():
            if header not in v:
                logger.warning(f"Missing security header: {header}")
                raise ValueError(f'Missing required security header: {header}')

            if not isinstance(v[header], expected_type):
                logger.warning(f"Invalid type for header {header}: expected {expected_type}, got {type(v[header])}")
                raise ValueError(f'Invalid type for header {header}')

        # Additional validation for specific headers
        if 'Content-Security-Policy' in v:
            csp = v['Content-Security-Policy']
            if not any(directive in csp.lower() for directive in ['default-src', 'script-src', 'style-src']):
                logger.warning("Content-Security-Policy header appears malformed")
                raise ValueError("Content-Security-Policy header appears malformed")

        return v

    @field_validator('body')
    @classmethod
    def sanitize_body(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize HTML content in request body.

        Args:
            v: Request body dictionary

        Returns:
            Sanitized body dictionary
        """
        if 'html_content' in v and isinstance(v['html_content'], str):
            v['html_content'] = cls.sanitize_html(v['html_content'])
        if 'token' in v:
            v['token'] = cls.sanitize_token(v['token'])
        return v

    @staticmethod
    def sanitize_token(token: str) -> str:
        """Sanitize authentication token."""
        return re.sub(r'[^a-zA-Z0-9_\-]', '', token)

    @field_validator('query_params')
    @classmethod
    def validate_csrf_token(cls, v: Dict[str, str]) -> Dict[str, str]:
        """
        Validate CSRF token in query parameters.

        Args:
            v: Query parameters dictionary

        Returns:
            Validated query parameters

        Raises:
            ValueError: If CSRF token is missing or invalid
        """
        csrf_token = v.get("csrf_token") or v.get("csrfmiddlewaretoken")
        if not csrf_token:
            logger.warning("Missing CSRF token in query parameters")
            raise ValueError("Missing CSRF token")

        if len(csrf_token) < 8:
            logger.warning(f"Invalid CSRF token format: {csrf_token}")
            raise ValueError("Invalid CSRF token format")

        return v

    @field_validator('headers')
    @classmethod
    def validate_security_headers(cls, v: Dict[str, str]) -> Dict[str, str]:
        """
        Validate presence and basic format of security headers.

        Args:
            v: Dictionary of HTTP headers

        Returns:
            Validated headers dictionary

        Raises:
            ValueError: If required security headers are missing or malformed
        """
        required_headers = {
            'Content-Security-Policy': str,
            'X-Content-Type-Options': str,
            'X-Frame-Options': str
        }

        for header, expected_type in required_headers.items():
            if header not in v:
                logger.warning(f"Missing security header: {header}")
                raise ValueError(f'Missing required security header: {header}')

            if not isinstance(v[header], expected_type):
                logger.warning(f"Invalid type for header {header}: expected {expected_type}, got {type(v[header])}")
                raise ValueError(f'Invalid type for header {header}')

        # Additional validation for specific headers
        if 'Content-Security-Policy' in v:
            csp = v['Content-Security-Policy']
            if not any(directive in csp.lower() for directive in ['default-src', 'script-src', 'style-src']):
                logger.warning("Content-Security-Policy header appears malformed")
                raise ValueError("Content-Security-Policy header appears malformed")

        return v

    @field_validator('body')
    @classmethod
    def sanitize_body(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize HTML content in request body.

        Args:
            v: Request body dictionary

        Returns:
            Sanitized body dictionary
        """
        if 'html_content' in v and isinstance(v['html_content'], str):
            v['html_content'] = cls.sanitize_html(v['html_content'])
        return v

    @staticmethod
    def sanitize_html(html: str) -> str:
        """
        Remove dangerous HTML tags and attributes, and escape HTML entities.

        Args:
            html: Raw HTML content to sanitize

        Returns:
            Sanitized HTML string
        """
        if not html:
            return html

        # Define dangerous tags and attributes
        dangerous_tags = [
            'script', 'iframe', 'frame', 'object', 'applet',
            'svg', 'math', 'embed', 'link', 'meta', 'base'
        ]

        dangerous_attrs = [
            r'on\w+', 'javascript:', r'expression\(', 'behaviour:',
            'style=', 'formaction=', 'srcdoc=', 'dynsrc=', 'src=',
            'href=', 'action=', 'background=', 'cite=', 'data='
        ]

        # Remove dangerous tags and their content
        for tag in dangerous_tags:
            html = re.sub(
                fr'<{tag}[^>]*>',
                '',
                html,
                flags=re.IGNORECASE
            )
            html = re.sub(
                fr'</{tag}>',
                '',
                html,
                flags=re.IGNORECASE
            )
            html = re.sub(
                fr'<{tag}[^>]*/>',
                '',
                html,
                flags=re.IGNORECASE
            )

        # Remove dangerous attributes from remaining tags
        for attr_pattern in dangerous_attrs:
            html = re.sub(
                fr'\s+{attr_pattern}[^>]*',
                '',
                html,
                flags=re.IGNORECASE
            )

        # Normalize whitespace
        html = re.sub(r'\s+', ' ', html)

        # Escape HTML entities
        html = html.replace('&', '&amp;') \
                   .replace('<', '&lt;') \
                   .replace('>', '&gt;') \
                   .replace('"', '&quot;') \
                   .replace("'", '&#39;')

        return html.strip()

class WebAdapter:
    """
    Web adapter for handling incoming HTTP requests with enhanced security validation.

    This class provides methods for processing web requests with strict security
    validation, sanitization, and CSRF/token protection.

    Features:
    - Request validation with Pydantic models
    - HTML sanitization
    - Security header enforcement
    - CSRF token validation
    - Token-based authentication
    - Response sanitization
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.security_headers = SecurityHeaders()
        self.token_scheme = HTTPBearer()

    async def process_webhook_request(self, request: Request) -> Dict[str, Any]:
        """
        Process and validate a webhook request with token in request body.

        Args:
            request: FastAPI Request object

        Returns:
            Processed and validated request data

        Raises:
            ValidationError: If request fails validation
            ValueError: If request contains security violations
        """
        try:
            # Parse request body
            body = await request.json()
            token = body.get("token")

            if not token:
                self.logger.warning("⚠️ Missing token in webhook request")
                raise ValueError("Missing authentication token")

            # Validate token
            validated_token = WebhookRequest(token=token, payload=body).token

            # Log successful validation
            self.logger.info("✅ Webhook request validated successfully",
                           extra={'token_prefix': validated_token[:4]})

            return {
                'status': 'valid',
                'authenticated': True,
                'token': validated_token,
                'payload': body
            }

        except Exception as e:
            self.logger.warning("⚠️ Webhook request validation failed",
                              extra={'error': str(e)})
            raise ValueError(f"Webhook validation failed: {str(e)}")

    def process_request(self, raw_headers: Dict[str, str],
                       raw_body: Dict[str, Any],
                       raw_query: Dict[str, str]) -> Dict[str, Any]:
        """
        Process and validate an incoming web request.

        Args:
            raw_headers: Raw HTTP headers from request
            raw_body: Raw request body
            raw_query: Raw query parameters

        Returns:
            Processed and validated request data

        Raises:
            ValidationError: If request fails validation
            ValueError: If request contains security violations
        """
        try:
            # Validate and sanitize the request
            validated_request = WebRequestSchema(
                headers=raw_headers,
                body=raw_body,
                query_params=raw_query
            )

            # Log successful validation
            self.logger.info("✅ Request validated successfully",
                           extra={'headers': validated_request.headers})

            return {
                'status': 'valid',
                'data': validated_request.model_dump(),
                'sanitized': True
            }

        except ValidationError as e:
            error_details = {
                'status': 'invalid',
                'errors': str(e),
                'sanitized': False
            }
            self.logger.warning("⚠️ Request validation failed",
                              extra={'errors': str(e)})
            raise ValueError(f"Request validation failed: {str(e)}")

        except ValueError as e:
            error_details = {
                'status': 'invalid',
                'errors': str(e),
                'sanitized': False
            }
            self.logger.warning("⚠️ Security violation detected",
                              extra={'error': str(e)})
            raise

    def add_security_headers(self, response: Response) -> Response:
        """
        Add security headers to HTTP response.

        Args:
            response: FastAPI Response object

        Returns:
            Response with added security headers
        """
        response.headers.update({
            "Content-Security-Policy": self.security_headers.content_security_policy,
            "X-Content-Type-Options": self.security_headers.x_content_type_options,
            "X-Frame-Options": self.security_headers.x_frame_options,
            "Strict-Transport-Security": self.security_headers.strict_transport_security,
            "Referrer-Policy": self.security_headers.referrer_policy,
            "Permissions-Policy": self.security_headers.permissions_policy,
            "X-XSS-Protection": "1; mode=block",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
        return response

    def validate_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize outgoing response data.

        Args:
            response_data: Data to be sent in response

        Returns:
            Sanitized response data
        """
        if 'html_content' in response_data and isinstance(response_data['html_content'], str):
            response_data['html_content'] = WebRequestSchema.sanitize_html(
                response_data['html_content']
            )

        # Sanitize any other potentially dangerous content
        for key, value in response_data.items():
            if isinstance(value, str):
                response_data[key] = WebRequestSchema.s