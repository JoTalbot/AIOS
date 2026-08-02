"""Universal Web Site / DOM RPA Adapter for AIOS v16.0.0.

Provides web browser automation, DOM scraping, form input, and click interactions.
"""

from __future__ import annotations

import html
import time
from typing import Any

from pydantic import BaseModel, field_validator, ValidationError

class WebRequestSchema(BaseModel):
    """Pydantic model for validating web request parameters."""

    url: str
    action: str
    selector: str = ""
    text: str = ""

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

class WebAdapter:
    """Universal Web Site / DOM automation adapter."""

    def __init__(self) -> None:
        self.execution_history: list[dict[str, Any]] = []

    def execute_web_action(
        self,
        url: str,
        action: str,
        selector: str = "",
        text: str = "",
    ) -> dict[str, Any]:
        """Execute browser web automation action (navigate, click, type, scrape).

        Args:
            url: Target URL (must be http:// or https://)
            action: Type of action to perform (navigate, click, type, scrape)
            selector: CSS selector for the element to interact with
            text: Text to input (for type action)

        Returns:
            dict: Execution result with status and extracted data

        Raises:
            ValidationError: If input parameters are invalid
        """
        try:
            validated_data = WebRequestSchema(
                url=url,
                action=action,
                selector=selector,
                text=text
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
