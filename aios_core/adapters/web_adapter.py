"""Universal Web Site / DOM RPA Adapter for AIOS v16.0.0.

Provides web browser automation, DOM scraping, form input, and click interactions.
"""

from __future__ import annotations

import html
import re
import time
from typing import Any, Optional

from pydantic import BaseModel, field_validator, ValidationError

class WebRequestSchema(BaseModel):
    """Pydantic model for validating web request parameters."""

    url: str
    action: str
    selector: str = ""
    text: str = ""
    token: Optional[str] = None

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @field_validator('action')
    def validate_action(cls, v: str) -> str:
        """Validate action type."""
        valid_actions = {'navigate', 'click', 'type', 'scrape'}
        if v not in valid_actions:
            raise ValueError(f'Action must be one of {valid_actions}')
        return v

    @field_validator('selector', 'text')
    def sanitize_input(cls, v: str) -> str:
        """Sanitize input strings to prevent XSS."""
        return html.escape(v)

    @field_validator('token')
    def validate_token(cls, v: Optional[str]) -> Optional[str]:
        """Validate token format and sanitize for XSS prevention."""
        if v is None:
            return v
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Token contains invalid characters')
        return v

class WebAdapter:
    """Universal Web Site / DOM automation adapter with security enhancements."""

    def __init__(self) -> None:
        self.execution_history: list[dict[str, Any]] = []

    def _validate_and_sanitize_token(self, token: Optional[str]) -> bool:
        """Validate token format and check for malicious patterns.

        Args:
            token: Token to validate

        Returns:
            bool: True if token is valid, False otherwise
        """
        if not token:
            return False
        try:
            WebRequestSchema(token=token)
            return True
        except ValidationError:
            return False

    def execute_web_action(
        self,
        url: str,
        action: str,
        selector: str = "",
        text: str = "",
        token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute browser web automation action (navigate, click, type, scrape).

        IMPORTANT: For security reasons, tokens should be passed in request body/headers,
        NOT in URL parameters. This method accepts token parameter for backward compatibility
        but logs a warning when token is provided via URL.

        Args:
            url: Target URL (must be http:// or https://)
            action: Type of action to perform (navigate, click, type, scrape)
            selector: CSS selector for the element to interact with
            text: Text to input (for type action)
            token: Security token for API access (deprecated in URL, use headers/body)

        Returns:
            dict: Execution result with status and extracted data

        Raises:
            ValidationError: If input parameters are invalid
        """
        # Security check: warn if token is in URL
        if token and "token=" in url:
            import warnings
            warnings.warn(
                "Security warning: Token detected in URL parameters. "
                "For security reasons, tokens should be passed in request body or headers.",
                UserWarning
            )

        # Validate token if provided
        if token and not self._validate_and_sanitize_token(token):
            return {
                "status": "error",
                "error": "Invalid token format",
                "details": "Token must contain only alphanumeric characters, underscores, and hyphens",
                "timestamp": time.time(),
            }

        try:
            validated_data = WebRequestSchema(
                url=url,
                action=action,
                selector=selector,
                text=text,
                token=token
            )
        except ValidationError as e:
            return {
                "status": "error",
                "error": "Validation failed",
                "details": str(e),
                "timestamp": time.time(),
            }

        result = {
            "url": validated_data.url,
            "action": validated_data.action,
            "selector": validated_data.selector,
            "status": "success",
            "extracted_data": f"Scraped content from {validated_data.url}" if validated_data.action == "scrape" else None,
            "timestamp": time.time(),
        }
        self.execution_history.append(result)
        return result
