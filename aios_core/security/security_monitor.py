from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl, constr, field_validator, ValidationError
from dataclasses import dataclass
import httpx
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class HttpMethod(str, Enum):
    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"

class RequestValidationModel(BaseModel):
    """Model for validating incoming API request data."""
    url: HttpUrl
    headers: dict[str, str]
    body: dict[str, Any]
    source: Optional[constr(min_length=1)] = None
    method: HttpMethod = HttpMethod.POST

    @field_validator('headers')
    @classmethod
    def validate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        """Ensure Content-Type is application/json if body is present."""
        if not v.get('Content-Type') and v.get('content-type'):
            v['Content-Type'] = v['content-type']
        if 'Content-Type' in v and v['Content-Type'] != 'application/json':
            raise ValueError("Content-Type must be application/json")
        return v

    @field_validator('body')
    @classmethod
    def validate_body(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Ensure body is a non-empty dictionary."""
        if not isinstance(v, dict) or not v:
            raise ValueError("Body must be a non-empty dictionary")
        return v

@dataclass
class Response:
    """Container for HTTP response data."""
    status_code: int
    body: dict[str, Any]
    headers: Optional[dict[str, str]] = None

class SecurityMonitor:
    """Security monitor for handling and validating API requests."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.client = httpx.Client(timeout=self.timeout)

    def validate_and_send_request(
        self,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        source: Optional[str] = None,
        method: HttpMethod = HttpMethod.POST
    ) -> Response:
        """
        Validate and safely send an HTTP request.

        Args:
            url: Target URL for the request
            headers: Request headers
            body: Request body payload
            source: Optional source identifier (e.g., IP, token)
            method: HTTP method to use

        Returns:
            Response object containing status and body
        """
        try:
            # Validate input using Pydantic model
            validated = RequestValidationModel(
                url=url,
                headers=headers,
                body=body,
                source=source,
                method=method
            )
        except ValidationError as e:
            logger.warning(
                f"Invalid request from source {source or 'unknown'}: {e}",
                extra={'source': source}
            )
            return Response(
                status_code=400,
                body={"error": "Invalid request data", "details": str(e)}
            )

        try:
            # Prepare request
            req_headers = validated.headers.copy()
            req_body = validated.body.copy()

            # Log the request attempt
            logger.info(
                f"Attempting {method.value} request to {url} from {source or 'unknown'}",
                extra={'source': source}
            )

            # Send request
            response = self.client.request(
                method=method.value,
                url=str(validated.url),
                headers=req_headers,
                json=req_body
            )

            # Process response
            try:
                response_body = response.json()
            except ValueError:
                response_body = {"raw": response.text}

            return Response(
                status_code=response.status_code,
                body=response_body,
                headers=dict(response.headers)
            )

        except httpx.HTTPError as e:
            logger.error(
                f"Network error during request to {url} from {source or 'unknown'}: {e}",
                extra={'source': source}
            )
            return Response(
                status_code=502,
                body={"error": "Network error", "details": str(e)}
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during request to {url} from {source or 'unknown'}: {e}",
                extra={'source': source}
            )
            return Response(
                status_code=500,
                body={"error": "Internal server error", "details": str(e)}
            )

    def close(self):
        """Clean up resources."""
        self.client.close()

# Example usage and test cases would be implemented in tests/test_security_monitor.py