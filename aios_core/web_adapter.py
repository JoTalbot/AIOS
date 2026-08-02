# aios_core/web_adapter.py
from pydantic import BaseModel, field_validator, ValidationError, HttpUrl
from typing import Dict, Any, Optional, List
import re
import logging
import html
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SecurityHeaders:
    """Container for security headers with validation."""
    content_security_policy: Optional[str] = None
    x_content_type_options: Optional[str] = None
    x_frame_options: Optional[str] = None
    strict_transport_security: Optional[str] = None

class CSRFTokenSchema(BaseModel):
    """Pydantic model for CSRF token validation."""
    csrf_token: str
    required: bool = True

    @field_validator('csrf_token')
    @classmethod
    def validate_csrf_token(cls, v: str) -> str:
        """Validate CSRF token format and presence."""
        if not v or len(v) < 8:
            raise ValueError("Invalid CSRF token")
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
        "extra": "forbid"  # Prevent extra fields that could be malicious
    }

    headers: Dict[str, str]
    body: Dict[str, Any]
    query_params: Dict[str, str]
    csrf_token: Optional[str] = None

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
            'X-Frame-Options': str,
            'X-XSS-Protection': str
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

        # Validate X-XSS-Protection header
        if 'X-XSS-Protection' in v and '0' in v['X-XSS-Protection']:
            logger.warning("X-XSS-Protection header is disabled")
            raise ValueError("X-XSS-Protection header is disabled")

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

        # Sanitize all string values in body
        sanitized_body = {}
        for key, value in v.items():
            if isinstance(value, str):
                sanitized_body[key] = cls.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized_body[key] = cls.sanitize_nested_dict(value)
            elif isinstance(value, list):
                sanitized_body[key] = [cls.sanitize_text(item) if isinstance(item, str) else item for item in value]
            else:
                sanitized_body[key] = value
        return sanitized_body

    @staticmethod
    def sanitize_nested_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = WebRequestSchema.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = WebRequestSchema.sanitize_nested_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [WebRequestSchema.sanitize_text(item) if isinstance(item, str) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize plain text input to prevent XSS."""
        if not text:
            return text
        return html.escape(text)

    @staticmethod
    def sanitize_html(html_str: str) -> str:
        """
        Remove dangerous HTML tags and attributes, and escape HTML entities.

        Args:
            html_str: Raw HTML content to sanitize

        Returns:
            Sanitized HTML string
        """
        if not html_str:
            return html_str

        # Remove dangerous tags and their content
        dangerous_tags = [
            'script', 'iframe', 'frame', 'object', 'applet',
            'svg', 'math', 'embed', 'link', 'meta', 'base',
            'form', 'input', 'button', 'select', 'textarea'
        ]

        for tag in dangerous_tags:
            # Remove opening tags
            html_str = re.sub(
                fr'<{tag}[^>]*>',
                '',
                html_str,
                flags=re.IGNORECASE
            )
            # Remove closing tags
            html_str = re.sub(
                fr'</{tag}>',
                '',
                html_str,
                flags=re.IGNORECASE
            )
            # Remove any remaining self-closing tags
            html_str = re.sub(
                fr'<{tag}[^>]*/>',
                '',
                html_str,
                flags=re.IGNORECASE
            )

        # Remove dangerous attributes from remaining tags
        dangerous_attrs = [
            r'on\w+', 'javascript:', r'expression\(', 'behaviour:',
            'style=', 'formaction=', 'srcdoc=', 'dynsrc=', 'src=',
            'href=', 'action=', 'background=', 'cite=', 'data=',
            'longdesc=', 'profile=', 'usemap=', 'xmlns='
        ]

        for attr_pattern in dangerous_attrs:
            html_str = re.sub(
                fr'\s+{attr_pattern}[^>]*',
                '',
                html_str,
                flags=re.IGNORECASE
            )

        # Escape HTML entities
        html_str = html.escape(html_str)

        return html_str.strip()

class WebAdapter:
    """
    Web adapter for handling incoming HTTP requests with enhanced security validation.

    This class provides methods for processing web requests with strict security
    validation and sanitization.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_request(self, raw_headers: Dict[str, str],
                       raw_body: Dict[str, Any],
                       raw_query: Dict[str, str],
                       csrf_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Process and validate an incoming web request.

        Args:
            raw_headers: Raw HTTP headers from request
            raw_body: Raw request body
            raw_query: Raw query parameters
            csrf_token: CSRF token from request

        Returns:
            Processed and validated request data

        Raises:
            ValidationError: If request fails validation
            ValueError: If request contains security violations
        """
        try:
            # Prepare request data with CSRF token
            request_data = {
                'headers': raw_headers,
                'body': raw_body,
                'query_params': raw_query,
                'csrf_token': csrf_token
            }

            # Validate and sanitize the request
            validated_request = WebRequestSchema(**request_data)

            # Validate CSRF token if present
            if csrf_token:
                try:
                    CSRFTokenSchema(csrf_token=csrf_token)
                    self.logger.info("✅ CSRF token validated successfully")
                except ValueError as e:
                    self.logger.warning("⚠️ Invalid CSRF token detected",
                                      extra={'error': str(e)})
                    raise ValueError(f"CSRF token validation failed: {str(e)}")

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

    def validate_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize outgoing response data.

        Args:
            response_data: Data to be sent in response

        Returns:
            Sanitized response data
        """
        sanitized_response = response_data.copy()

        # Sanitize all HTML content in response
        if 'html_content' in sanitized_response and isinstance(sanitized_response['html_content'], str):
            sanitized_response['html_content'] = WebRequestSchema.sanitize_html(
                sanitized_response['html_content']
            )

        # Sanitize any other HTML-containing fields
        for key, value in sanitized_response.items():
            if isinstance(value, str):
                sanitized_response[key] = WebRequestSchema.sanitize_html(value)
            elif isinstance(value, dict):
                sanitized_response[key] = self._sanitize_response_dict(value)
            elif isinstance(value, list):
                sanitized_response[key] = [self._sanitize_response_item(item) for item in value]

        return sanitized_response

    def _sanitize_response_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary values in response."""
        sanitized = {}
        for key, value in data.items():
            sanitized[key] = self._sanitize_response_item(value)
        return sanitized

    def _sanitize_response_item(self, item: Any) -> Any:
        """Sanitize individual response items."""
        if isinstance(item, str):
            return WebRequestSchema.sanitize_html(item)
        elif isinstance(item, dict):
            return self._sanitize_response_dict(item)
        elif isinstance(item, list):
            return [self._sanitize_response_item(sub_item) for sub_item in item]
        return item