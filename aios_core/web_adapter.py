# aios_core/web_adapter.py
from pydantic import BaseModel, field_validator, ValidationError
from typing import Dict, Any, Optional
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SecurityHeaders:
    """Container for security headers with validation."""
    content_security_policy: Optional[str] = None
    x_content_type_options: Optional[str] = None
    x_frame_options: Optional[str] = None
    strict_transport_security: Optional[str] = None

class WebRequestSchema(BaseModel):
    """
    Pydantic model for validating incoming web requests.

    Validates security headers, sanitizes HTML content in body,
    and ensures query parameters are properly structured.
    """
    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True
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

        # Remove dangerous tags and their content
        dangerous_tags = [
            'script', 'iframe', 'frame', 'object', 'applet',
            'svg', 'math', 'embed', 'link', 'meta'
        ]

        for tag in dangerous_tags:
            # Remove opening tags
            html = re.sub(
                fr'<{tag}[^>]*>',
                '',
                html,
                flags=re.IGNORECASE
            )
            # Remove closing tags
            html = re.sub(
                fr'</{tag}>',
                '',
                html,
                flags=re.IGNORECASE
            )
            # Remove any remaining self-closing tags
            html = re.sub(
                fr'<{tag}[^>]*/>',
                '',
                html,
                flags=re.IGNORECASE
            )

        # Remove dangerous attributes from remaining tags
        dangerous_attrs = [
            r'on\w+', 'javascript:', r'expression\(', 'behaviour:',
            'style=', 'formaction=', 'srcdoc=', 'dynsrc='
        ]

        for attr_pattern in dangerous_attrs:
            html = re.sub(
                fr'\s+{attr_pattern}[^>]*',
                '',
                html,
                flags=re.IGNORECASE
            )

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
    validation and sanitization.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

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

        return response_data